import asyncio
from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.models.user import User
from app.core.security import verify_password, get_password_hash


async def main():
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.email == "mhuck@kent.co.uk"))
        user = result.scalar_one_or_none()

        if not user:
            print("NOT FOUND")
            return

        print("FOUND")
        print("id:", user.id)
        print("email:", user.email)
        print("school_id:", user.school_id)
        print("role:", user.role)
        print("status:", user.status)
        print("is_active:", user.is_active)

        # 🔍 Check password
        print("\nChecking password...")
        is_valid = verify_password("test123", user.hashed_password)
        print("Password valid:", is_valid)

        # 🔥 Fix if wrong
        if not is_valid:
            print("\nResetting password to test123...")
            user.hashed_password = get_password_hash("test123")
            await db.commit()
            print("Password reset complete!")


asyncio.run(main())
