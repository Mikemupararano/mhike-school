from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

ALGORITHM = getattr(settings, "algorithm", "HS256")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def get_password_hash(password: str) -> str:
    return hash_password(password)


def verify_password(password: str, hashed_password: str) -> bool:
    return pwd_context.verify(password, hashed_password)


def create_access_token(
    *,
    data: dict[str, Any] | None = None,
    subject: str | int | None = None,
    school_id: int | None = None,
    role: str | None = None,
    roles: list[str] | None = None,
    expires_minutes: int | None = None,
) -> str:
    """
    Create an access token.

    Phase 1 supports both:
    - legacy role: "teacher"
    - new roles: ["school_admin", "teacher"]
    """
    minutes = expires_minutes or settings.access_token_expire_minutes
    expire = datetime.now(timezone.utc) + timedelta(minutes=minutes)

    if data is not None:
        payload = data.copy()

        if "sub" not in payload:
            raise ValueError("Token payload must include 'sub'")

    elif subject is not None:
        payload = {
            "sub": str(subject),
            "school_id": school_id,
        }

        if role is not None:
            payload["role"] = role

        if roles is not None:
            payload["roles"] = roles

    else:
        raise ValueError("Either 'data' or 'subject' must be provided")

    if "roles" not in payload and "role" in payload:
        payload["roles"] = [payload["role"]]

    if "role" not in payload and payload.get("roles"):
        payload["role"] = payload["roles"][0]

    payload["sub"] = str(payload["sub"])
    payload["exp"] = expire

    return jwt.encode(
        payload,
        settings.secret_key,
        algorithm=ALGORITHM,
    )


def decode_access_token(token: str) -> dict[str, Any]:
    try:
        return jwt.decode(
            token,
            settings.secret_key,
            algorithms=[ALGORITHM],
        )
    except JWTError as exc:
        raise ValueError("Invalid token") from exc
