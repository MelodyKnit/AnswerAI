from datetime import datetime, timedelta, UTC

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings


ALGORITHM = "HS256"
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    处理 verify password 请求并返回结果。
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    获取 password hash 相关数据。
    """
    return pwd_context.hash(password)


def create_access_token(subject: str, expires_delta: timedelta | None = None) -> str:
    """
    创建新的 access token 记录。
    """
    expire = datetime.now(UTC) + (expires_delta or timedelta(minutes=settings.access_token_expire_minutes))
    to_encode = {"sub": subject, "exp": expire}
    return jwt.encode(to_encode, settings.secret_key, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict:
    """
    处理 decode access token 请求并返回结果。
    """
    return jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])


class InvalidTokenError(Exception):
    pass


def get_subject_from_token(token: str) -> str:
    """
    获取 subject from token 相关数据。
    """
    try:
        payload = decode_access_token(token)
    except JWTError as exc:
        raise InvalidTokenError("Could not validate credentials") from exc

    subject = payload.get("sub")
    if not subject:
        raise InvalidTokenError("Token subject is missing")
    return subject
