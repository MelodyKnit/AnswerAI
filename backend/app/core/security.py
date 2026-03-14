from datetime import datetime, timedelta, UTC

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings


ALGORITHM = "HS256"
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(subject: str, expires_delta: timedelta | None = None) -> str:
    expire = datetime.now(UTC) + (expires_delta or timedelta(minutes=settings.access_token_expire_minutes))
    to_encode = {"sub": subject, "exp": expire}
    return jwt.encode(to_encode, settings.secret_key, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict:
    return jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])


class InvalidTokenError(Exception):
    pass


def get_subject_from_token(token: str) -> str:
    try:
        payload = decode_access_token(token)
    except JWTError as exc:
        raise InvalidTokenError("Could not validate credentials") from exc

    subject = payload.get("sub")
    if not subject:
        raise InvalidTokenError("Token subject is missing")
    return subject
