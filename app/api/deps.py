from fastapi import Depends, Header, HTTPException, status
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.security import ALGORITHM
from app.db.session import get_db
from app.models import User
from app.models.user import UserRole, UserStatus


def _raise_invalid_token() -> None:
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid token payload",
    )


def _normalise_token_roles(payload: dict) -> set[UserRole]:
    token_roles = payload.get("roles")
    token_role = payload.get("role")

    if token_roles is not None:
        if not isinstance(token_roles, list) or not token_roles:
            _raise_invalid_token()

        try:
            return {UserRole(role) for role in token_roles}
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload",
            ) from exc

    if token_role is not None:
        try:
            return {UserRole(token_role)}
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload",
            ) from exc

    _raise_invalid_token()


def _validate_token_school_rules(
    parsed_roles: set[UserRole],
    school_id: int | str | None,
) -> int | None:
    is_platform_admin = UserRole.PLATFORM_ADMIN in parsed_roles

    has_school_role = bool(
        parsed_roles.intersection(
            {
                UserRole.SCHOOL_ADMIN,
                UserRole.TEACHER,
                UserRole.STUDENT,
            }
        )
    )

    if is_platform_admin and has_school_role:
        _raise_invalid_token()

    if is_platform_admin:
        if school_id is not None:
            _raise_invalid_token()
        return None

    if school_id is None:
        _raise_invalid_token()

    try:
        return int(school_id)
    except (TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        ) from exc


async def get_current_user(
    db: AsyncSession = Depends(get_db),
    authorization: str | None = Header(default=None),
) -> User:
    authorization = authorization.strip() if authorization else None

    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header",
        )

    token = authorization.split(" ", 1)[1].strip()

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header",
        )

    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[ALGORITHM],
        )

        user_id = payload.get("sub")
        if user_id is None:
            _raise_invalid_token()

        try:
            user_id = int(user_id)
        except (TypeError, ValueError) as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload",
            ) from exc

        parsed_roles = _normalise_token_roles(payload)
        school_id = _validate_token_school_rules(
            parsed_roles=parsed_roles,
            school_id=payload.get("school_id"),
        )

    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        ) from exc

    query = (
        select(User)
        .options(
            selectinload(User.school),
            selectinload(User.user_roles),
        )
        .where(User.id == user_id)
    )

    if UserRole.PLATFORM_ADMIN in parsed_roles:
        query = query.where(User.school_id.is_(None))
    else:
        query = query.where(User.school_id == school_id)

    result = await db.execute(query)
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    if not user.is_active or user.status != UserStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive",
        )

    user_role_values = set(user.roles)
    token_role_values = {role.value for role in parsed_roles}

    if not token_role_values.issubset(user_role_values):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token role no longer valid for user",
        )

    return user


async def get_current_school_id(
    current_user: User = Depends(get_current_user),
) -> int:
    if current_user.school_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not assigned to a school",
        )

    return int(current_user.school_id)


def require_role(*roles: UserRole):
    async def _dep(current_user: User = Depends(get_current_user)) -> User:
        allowed_roles = {role.value for role in roles}
        current_roles = set(current_user.roles)

        if not current_roles.intersection(allowed_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden",
            )

        return current_user

    return _dep
