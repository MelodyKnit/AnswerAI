from datetime import datetime, UTC
import logging
from time import perf_counter
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.core.config import settings
from app.core.response import success_response
from app.core.security import create_access_token, get_password_hash, verify_password
from app.models.academic import ClassRoom, ClassStudent
from app.models.user import AITask, User
from app.schemas.auth import ChangePasswordRequest, LoginRequest, ProfileUpdateRequest, RegisterRequest, UserFeedbackCreateRequest


router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/auth/register")
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    """
    处理 register 请求并返回结果。
    """
    existing = db.scalar(select(User).where(User.email == payload.email))
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="该邮箱已被注册")

    existing_username = db.scalar(select(User).where(User.username == payload.username))
    if existing_username:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="该用户名已被占用")

    if payload.role == "teacher":
        invite_code = (payload.teacher_invite_code or "").strip()
        # 教师邀请码为可选：仅当用户填写后才执行校验。
        if invite_code and invite_code != settings.teacher_invite_code:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="组织机构代码无效，请检查后重试")

    user = User(
        role=payload.role,
        name=payload.name,
        username=payload.username,
        email=payload.email,
        phone=payload.phone,
        password_hash=get_password_hash(payload.password),
        school_name=payload.school_name,
        grade_name=payload.grade_name,
        status="active",
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        message = str(exc).lower()
        if "users.email" in message or "email" in message:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="该邮箱已被注册")
        if "users.username" in message or "username" in message:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="该用户名已被占用")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="注册失败，请稍后重试")
    db.refresh(user)

    if payload.role == "student" and payload.class_code:
        classroom = db.scalar(select(ClassRoom).where(ClassRoom.invite_code == payload.class_code, ClassRoom.status == "active"))
        if classroom:
            relation = ClassStudent(
                class_id=classroom.id,
                student_id=user.id,
                teacher_id=classroom.teacher_id,
                status="active",
            )
            classroom.student_count += 1
            db.add(relation)
            db.commit()

    token = create_access_token(str(user.id))
    return success_response(
        {
            "access_token": token,
            "token_type": "bearer",
            "user": {"id": user.id, "role": user.role, "name": user.name, "username": user.username, "email": user.email},
        },
        "register success",
    )


@router.post("/auth/login")
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    """
    处理 login 请求并返回结果。
    """
    user = db.scalar(select(User).where((User.email == payload.login_id) | (User.username == payload.login_id)))
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="账号或密码错误")

    user.last_login_at = datetime.now(UTC)
    db.add(user)
    db.commit()

    return success_response(
        {
            "access_token": create_access_token(str(user.id)),
            "token_type": "bearer",
            "expires_in": 60 * 24 * 60,
            "user": {"id": user.id, "role": user.role, "name": user.name, "username": user.username, "email": user.email},
        }
    )


@router.get("/auth/me")
def me(current_user: User = Depends(get_current_user)):
    """
    处理 me 请求并返回结果。
    """
    started_at = perf_counter()
    payload = success_response({"user": _serialize_user(current_user)})
    elapsed_ms = int((perf_counter() - started_at) * 1000)
    logger.info("API perf path=/auth/me user_id=%s elapsed_ms=%d", current_user.id, elapsed_ms)
    return payload


@router.post("/users/profile/update")
def update_profile(payload: ProfileUpdateRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    更新已有的 profile 记录。
    """
    update_data = payload.model_dump(exclude_none=True)

    # 用户名一旦设置后不可修改。
    next_username = update_data.get("username")
    if next_username is not None and next_username != current_user.username:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="用户名一旦设置后不可修改")
    update_data.pop("username", None)

    # 学生只允许更新与个人身份直接相关的信息，禁止修改学校/年级。
    if current_user.role == "student":
        allowed_fields = {"name", "email", "phone", "avatar_url"}
        update_data = {key: value for key, value in update_data.items() if key in allowed_fields}

    next_email = update_data.get("email")
    if next_email and next_email != current_user.email:
        existing = db.scalar(select(User).where(User.email == next_email, User.id != current_user.id))
        if existing:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="该邮箱已被注册")

    for field, value in update_data.items():
        setattr(current_user, field, value)
    db.add(current_user)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        message = str(exc).lower()
        if "users.email" in message or "email" in message:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="该邮箱已被注册")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="更新失败，请稍后重试")
    db.refresh(current_user)
    return success_response({"user": _serialize_user(current_user)})


@router.post("/users/password/change")
def change_password(payload: ChangePasswordRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    处理 change password 请求并返回结果。
    """
    if not verify_password(payload.old_password, current_user.password_hash):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="旧密码不正确")
    current_user.password_hash = get_password_hash(payload.new_password)
    db.add(current_user)
    db.commit()
    return success_response({"success": True}, "password changed")


@router.post("/users/feedback/create")
def create_user_feedback(
    payload: UserFeedbackCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    创建用户反馈记录，支持文本与图片证据。
    """
    normalized_images: list[str] = []
    for raw in payload.images:
        item = str(raw or "").strip()
        if not item:
            continue
        if len(item) > 500:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="图片地址过长")
        normalized_images.append(item)

    if len(normalized_images) > 6:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="最多上传 6 张图片")

    feedback_task = AITask(
        task_id=f"feedback_{current_user.id}_{int(datetime.now(UTC).timestamp())}_{uuid4().hex[:8]}",
        type="user_feedback",
        status="submitted",
        progress=100,
        resource_type="user",
        resource_id=current_user.id,
        request_payload={
            "category": payload.category,
            "content": payload.content.strip(),
            "images": normalized_images,
            "page_path": (payload.page_path or "").strip() or None,
            "client_role": current_user.role,
            "client_name": current_user.name,
            "client_email": current_user.email,
        },
        created_by=current_user.id,
        finished_at=datetime.now(UTC),
    )

    db.add(feedback_task)
    db.commit()
    db.refresh(feedback_task)
    return success_response({"feedback_id": feedback_task.id, "status": feedback_task.status}, "feedback submitted")


def _serialize_user(user: User) -> dict:
    """
    序列化 user 对象为字典。
    """
    return {
        "id": user.id,
        "role": user.role,
        "name": user.name,
        "username": user.username,
        "email": user.email,
        "phone": user.phone,
        "avatar_url": user.avatar_url,
        "school_name": user.school_name,
        "grade_name": user.grade_name,
        "status": user.status,
        "created_at": user.created_at.isoformat(),
    }
