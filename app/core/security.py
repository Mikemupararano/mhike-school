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

    REQUIREMENTS:
    - school_id must ALWAYS be present
    """

    minutes = expires_minutes or settings.access_token_expire_minutes
    expire = datetime.now(timezone.utc) + timedelta(minutes=minutes)

    if data is not None:
        payload = data.copy()

        if "school_id" not in payload:
            raise ValueError("Token payload must include 'school_id'")

    elif subject is not None:
        if school_id is None:
            raise ValueError("school_id is required when using subject")

        payload = {
            "sub": subject,
            "school_id": school_id,
        }

    else:
        raise ValueError("Either 'data' or 'subject' must be provided")

    payload["exp"] = expire

    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)
