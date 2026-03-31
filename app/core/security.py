from datetime import datetime, timedelta, timezone
from jose import jwt
from passlib.context import CryptContext
from typing import Any, Dict, Optional

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    return pwd_context.verify(password, hashed)


def create_access_token(
    data: Optional[Dict[str, Any]] = None,
    subject: Optional[str] = None,
    expires_minutes: Optional[int] = None,
) -> str:
    """
    Multi-tenant safe token creation.

    Supports:
    - new usage: create_access_token(data={...})
    - old usage: create_access_token(subject="email")
    """

    minutes = expires_minutes or settings.access_token_expire_minutes
    expire = datetime.now(timezone.utc) + timedelta(minutes=minutes)

    if data:
        payload = data.copy()
    elif subject:
        payload = {"sub": subject}
    else:
        raise ValueError("Either 'data' or 'subject' must be provided")

    payload.update({"exp": expire})

    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)
