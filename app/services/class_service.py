from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.class_group import ClassGroup


class ClassService:
    @staticmethod
    async def list_classes_by_school(db: AsyncSession, school_id: int):
        result = await db.execute(
            select(ClassGroup)
            .where(ClassGroup.school_id == school_id)
            .order_by(ClassGroup.id)
        )
        return result.scalars().all()

    @staticmethod
    async def create_class(
        db: AsyncSession,
        payload,
        school_id: int,
    ):
        class_group = ClassGroup(
            name=payload.name,
            school_id=school_id,
        )
        db.add(class_group)
        await db.commit()
        await db.refresh(class_group)
        return class_group

    @staticmethod
    async def get_class_by_id(
        db: AsyncSession,
        class_id: int,
        school_id: int,
    ):
        result = await db.execute(
            select(ClassGroup).where(
                ClassGroup.id == class_id,
                ClassGroup.school_id == school_id,
            )
        )
        return result.scalar_one_or_none()
