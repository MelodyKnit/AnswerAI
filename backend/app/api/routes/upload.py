from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from app.api.deps import require_role
from app.core.response import success_response
from app.models.user import User

router = APIRouter()

BASE_DIR = Path(__file__).resolve().parents[3]
UPLOAD_DIR = BASE_DIR / "data" / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_CONTENT_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif",
}


@router.post("/upload/image")
async def upload_image(
    file: UploadFile = File(...),
    current_user: User = Depends(require_role("teacher", "student")),
):
    """
    处理图片上传请求
    
    允许教师和学生上传图片内容（如：题目插图、问题反馈截图）。
    支持格式：jpg/png/webp/gif，最大不能超过 8MB。
    返回上传成功后的文件名、类型、大小以及访问URL。
    """
    del current_user

    content_type = file.content_type or ""
    if content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="仅支持 jpg/png/webp/gif 图片")

    ext = ALLOWED_CONTENT_TYPES[content_type]
    filename = f"{uuid4().hex}{ext}"
    file_path = UPLOAD_DIR / filename

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="上传文件为空")

    if len(file_bytes) > 8 * 1024 * 1024:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="图片大小不能超过 8MB")

    file_path.write_bytes(file_bytes)

    return success_response(
        {
            "file_name": filename,
            "content_type": content_type,
            "size": len(file_bytes),
            "url": f"/uploads/{filename}",
        },
        "upload success",
    )
