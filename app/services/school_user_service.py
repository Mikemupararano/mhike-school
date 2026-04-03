from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


class SchoolUserService:
    @staticmethod
    async def list_users_by_school(db: AsyncSession, school_id: int):
        result = await db.execute(
            select(User).where(User.school_id == school_id).order_by(User.id)
        )
        return result.scalars().all()
