from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.school import School


class SchoolService:
    @staticmethod
    async def list_schools(db: AsyncSession):
        result = await db.execute(select(School).order_by(School.id))
        return result.scalars().all()
