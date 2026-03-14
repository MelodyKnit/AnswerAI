from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import InvalidTokenError, get_subject_from_token
from app.db.session import SessionLocal
from app.models.user import User


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_bearer_token(authorization: str = Header(default="")) -> str:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")
    return authorization.replace("Bearer ", "", 1)


def get_current_user(token: str = Depends(get_bearer_token), db: Session = Depends(get_db)) -> User:
    try:
        subject = get_subject_from_token(token)
    except InvalidTokenError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc

    user = db.get(User, int(subject))
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


def require_role(*roles: str):
    def checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")
        return current_user

    return checker
