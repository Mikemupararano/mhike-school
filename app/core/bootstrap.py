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
    Ensure the configured admin user exists.

    Behaviour:
    - If bootstrapping disabled → do nothing
    - If email/password missing → do nothing
    - If user with this email exists → promote to admin
    - If user does not exist → create admin
    """

    if not enabled or not email or not password:
        return

    # Check if the configured admin email already exists
    res = await db.execute(select(User).where(User.email == email))
    user = res.scalars().first()

    # Promote existing user to admin
    if user:
        updated = False

        if user.role != "admin":
            user.role = "admin"
            updated = True

        if not user.hashed_password:
            user.hashed_password = hash_password(password)
            updated = True

        if updated:
            await db.commit()

        return

    # Otherwise create new admin user
    admin_user = User(
        email=email,
        hashed_password=hash_password(password),
        role="admin",
    )

    db.add(admin_user)
    await db.commit()
