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
        payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])

        user_id = payload.get("sub")
        school_id = payload.get("school_id")

        # Transitional support:
        # - legacy tokens may contain a single "role"
        # - newer tokens may contain "roles"
        token_role = payload.get("role")
        token_roles = payload.get("roles")

        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload",
            )

        try:
            user_id = int(user_id)
        except (TypeError, ValueError) as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload",
            ) from exc

        parsed_roles: set[UserRole] = set()

        if token_roles is not None:
            if not isinstance(token_roles, list) or not token_roles:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token payload",
                )
            try:
                parsed_roles = {UserRole(role) for role in token_roles}
            except ValueError as exc:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token payload",
                ) from exc
        elif token_role is not None:
            try:
                parsed_roles = {UserRole(token_role)}
            except ValueError as exc:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token payload",
                ) from exc
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload",
            )

        is_platform_admin_token = UserRole.PLATFORM_ADMIN in parsed_roles

        if is_platform_admin_token:
            if school_id is not None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token payload",
                )
        else:
            if school_id is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token payload",
                )
            try:
                school_id = int(school_id)
            except (TypeError, ValueError) as exc:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token payload",
                ) from exc

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

    if is_platform_admin_token:
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

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive",
        )

    if user.status in {UserStatus.DEACTIVATED, UserStatus.ANONYMISED}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive",
        )

    user_role_values = {
        role.value if isinstance(role, UserRole) else str(role) for role in user.roles
    }
    token_role_values = {role.value for role in parsed_roles}

    if not token_role_values.intersection(user_role_values):
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
        current_roles = {
            role.value if isinstance(role, UserRole) else str(role)
            for role in current_user.roles
        }

        if not current_roles.intersection(allowed_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden",
            )
        return current_user

    return _dep
