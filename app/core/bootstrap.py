from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User
from app.core.security import hash_password


async def bootstrap_admin(
    db: AsyncSession,
    enabled: bool,
    email: str | None,
    password: str | None,
) -> None:
    """
    Creates an admin user ONLY if:
    - bootstrapping is enabled
    - no admin exists
    - email/password provided
    """
    if not enabled:
        return
    if not email or not password:
        return

    # Is there already an admin?
    res = await db.execute(select(User).where(User.role == "admin"))
    admin = res.scalar_one_or_none()
    if admin:
        return

    # If user exists with same email, promote to admin (safe & convenient)
    ures = await db.execute(select(User).where(User.email == email))
    user = ures.scalar_one_or_none()
    if user:
        user.role = "admin"
        if not user.hashed_password:
            user.hashed_password = hash_password(password)
        await db.commit()
        return

    # Otherwise create new admin
    admin_user = User(
        email=email,
        hashed_password=hash_password(password),
        role="admin",
    )
    db.add(admin_user)
    await db.commit()
