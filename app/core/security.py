from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from jose import jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    return pwd_context.verify(password, hashed)


def create_access_token(
    *,
    data: Optional[Dict[str, Any]] = None,
    subject: Optional[str] = None,
    school_id: Optional[int] = None,
    expires_minutes: Optional[int] = None,
) -> str:
    """
    Multi-tenant safe token creation.

    Supports:
    - create_access_token(data={...})
    - create_access_token(subject="user_id", school_id=1)
    """

    minutes = expires_minutes or settings.access_token_expire_minutes
    expire = datetime.now(timezone.utc) + timedelta(minutes=minutes)

    if data is not None:
        payload = data.copy()
    elif subject is not None:
        payload = {
            "sub": subject,
            "school_id": school_id,
        }
    else:
        raise ValueError("Either 'data' or 'subject' must be provided")

    payload["exp"] = expire

    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)
