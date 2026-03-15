from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import InvalidTokenError, get_subject_from_token
from app.db.session import SessionLocal
from app.models.user import User


def get_db():
    """
    获取 db 相关数据。
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_bearer_token(authorization: str = Header(default="")) -> str:
    """
    获取 bearer token 相关数据。
    """
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")
    return authorization.replace("Bearer ", "", 1)


def get_current_user(token: str = Depends(get_bearer_token), db: Session = Depends(get_db)) -> User:
    """
    获取 current user 相关数据。
    """
    try:
        subject = get_subject_from_token(token)
    except InvalidTokenError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc

    user = db.get(User, int(subject))
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


def require_role(*roles: str):
    """
    处理 require role 请求并返回结果。
    """
    def checker(current_user: User = Depends(get_current_user)) -> User:
        """
        处理 checker 请求并返回结果。
        """
        if current_user.role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")
        return current_user

    return checker
