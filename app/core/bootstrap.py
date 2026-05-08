from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.security import hash_password
from app.models import User
from app.models.user import UserRole, UserStatus
from app.models.user_role import UserRoleAssignment


async def bootstrap_admin(
    db: AsyncSession,
    enabled: bool,
    email: str | None,
    password: str | None,
) -> None:
    """
    Ensure the configured platform admin user exists.

    Behaviour:
    - If bootstrapping disabled → do nothing
    - If email/password missing → do nothing
    - If user with this email exists → promote to platform_admin
    - If user does not exist → create platform_admin
    """

    if not enabled or not email or not password:
        return

    normalized_email = email.strip().lower()

    res = await db.execute(
        select(User)
        .options(selectinload(User.user_roles))
        .where(User.email == normalized_email)
    )
    user = res.scalars().first()

    if user:
        updated = False

        if not user.has_role(UserRole.PLATFORM_ADMIN):
            db.add(
                UserRoleAssignment(
                    user_id=user.id,
                    role=UserRole.PLATFORM_ADMIN,
                )
            )
            updated = True

        # Legacy compatibility column
        if user.role != UserRole.PLATFORM_ADMIN:
            user.role = UserRole.PLATFORM_ADMIN
            updated = True

        if user.school_id is not None:
            user.school_id = None
            updated = True

        if user.status != UserStatus.ACTIVE:
            user.status = UserStatus.ACTIVE
            updated = True

        if not user.is_active:
            user.is_active = True
            updated = True

        if not user.hashed_password:
            user.hashed_password = hash_password(password)
            updated = True

        if updated:
            await db.commit()

        return

    admin_user = User(
        email=normalized_email,
        hashed_password=hash_password(password),
        role=UserRole.PLATFORM_ADMIN,
        status=UserStatus.ACTIVE,
        is_active=True,
        school_id=None,
    )

    db.add(admin_user)
    await db.flush()

    db.add(
        UserRoleAssignment(
            user_id=admin_user.id,
            role=UserRole.PLATFORM_ADMIN,
        )
    )

    await db.commit()
