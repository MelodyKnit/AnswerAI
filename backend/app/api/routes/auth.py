from datetime import datetime, UTC

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.core.response import success_response
from app.core.security import create_access_token, get_password_hash, verify_password
from app.models.academic import ClassRoom, ClassStudent
from app.models.user import User
from app.schemas.auth import ChangePasswordRequest, LoginRequest, ProfileUpdateRequest, RegisterRequest


router = APIRouter()


@router.post("/auth/register")
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    existing = db.scalar(select(User).where(User.email == payload.email))
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    user = User(
        role=payload.role,
        name=payload.name,
        email=payload.email,
        phone=payload.phone,
        password_hash=get_password_hash(payload.password),
        school_name=payload.school_name,
        grade_name=payload.grade_name,
        status="active",
    )
    db.add(user)
    db.commit()
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
            "user": {"id": user.id, "role": user.role, "name": user.name, "email": user.email},
        },
        "register success",
    )


@router.post("/auth/login")
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == payload.email))
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password")

    user.last_login_at = datetime.now(UTC)
    db.add(user)
    db.commit()

    return success_response(
        {
            "access_token": create_access_token(str(user.id)),
            "token_type": "bearer",
            "expires_in": 60 * 24 * 60,
            "user": {"id": user.id, "role": user.role, "name": user.name, "email": user.email},
        }
    )


@router.get("/auth/me")
def me(current_user: User = Depends(get_current_user)):
    return success_response({"user": _serialize_user(current_user)})


@router.post("/users/profile/update")
def update_profile(payload: ProfileUpdateRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(current_user, field, value)
    db.add(current_user)
    db.commit()
    db.refresh(current_user)
    return success_response({"user": _serialize_user(current_user)})


@router.post("/users/password/change")
def change_password(payload: ChangePasswordRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not verify_password(payload.old_password, current_user.password_hash):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Old password is incorrect")
    current_user.password_hash = get_password_hash(payload.new_password)
    db.add(current_user)
    db.commit()
    return success_response({"success": True}, "password changed")


def _serialize_user(user: User) -> dict:
    return {
        "id": user.id,
        "role": user.role,
        "name": user.name,
        "email": user.email,
        "phone": user.phone,
        "avatar_url": user.avatar_url,
        "school_name": user.school_name,
        "grade_name": user.grade_name,
        "status": user.status,
        "created_at": user.created_at.isoformat(),
    }
