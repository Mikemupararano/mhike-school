from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
ALGORITHM = getattr(settings, "algorithm", "HS256")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def get_password_hash(password: str) -> str:
    return hash_password(password)


def verify_password(password: str, hashed: str) -> bool:
    return pwd_context.verify(password, hashed)


def create_access_token(
    *,
    data: Optional[Dict[str, Any]] = None,
    subject: Optional[str] = None,
    school_id: Optional[int] = None,
    role: Optional[str] = None,
    expires_minutes: Optional[int] = None,
) -> str:
    """
    Multi-tenant safe token creation.

    Rules:
    - either `data` or `subject` must be provided
    - school-scoped users should include `school_id`
    - platform admins may have `school_id=None`
    - including `role` is recommended for downstream auth checks
    """

    minutes = expires_minutes or settings.access_token_expire_minutes
    expire = datetime.now(timezone.utc) + timedelta(minutes=minutes)

    if data is not None:
        payload = data.copy()

        if "sub" not in payload:
            raise ValueError("Token payload must include 'sub'")

    elif subject is not None:
        payload = {
            "sub": subject,
            "school_id": school_id,
        }

        if role is not None:
            payload["role"] = role

    else:
        raise ValueError("Either 'data' or 'subject' must be provided")

    payload["exp"] = expire

    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def decode_access_token(token: str) -> Dict[str, Any]:
    try:
        return jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
    except JWTError as exc:
        raise ValueError("Invalid token") from exc
