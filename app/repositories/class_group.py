from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.class_group import ClassGroup


class ClassGroupRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    # =========================
    # Get by ID
    # =========================
    async def get_by_id(self, class_id: int) -> ClassGroup | None:
        result = await self.db.execute(
            select(ClassGroup)
            .options(
                selectinload(ClassGroup.teacher),
                selectinload(ClassGroup.school),
            )
            .where(ClassGroup.id == class_id)
        )
        return result.scalar_one_or_none()

    # =========================
    # List by school
    # =========================
    async def list_by_school(self, school_id: int) -> list[ClassGroup]:
        result = await self.db.execute(
            select(ClassGroup)
            .options(
                selectinload(ClassGroup.teacher),
            )
            .where(ClassGroup.school_id == school_id)
            .order_by(ClassGroup.created_at.desc())
        )
        return list(result.scalars().all())

    # =========================
    # List by teacher
    # =========================
    async def list_by_teacher(self, teacher_id: int) -> list[ClassGroup]:
        result = await self.db.execute(
            select(ClassGroup)
            .where(ClassGroup.teacher_id == teacher_id)
            .order_by(ClassGroup.created_at.desc())
        )
        return list(result.scalars().all())

    # =========================
    # Create
    # =========================
    async def create(self, class_group: ClassGroup) -> ClassGroup:
        self.db.add(class_group)
        await self.db.flush()
        await self.db.refresh(class_group)
        return class_group

    # =========================
    # Save (update)
    # =========================
    async def save(self, class_group: ClassGroup) -> ClassGroup:
        self.db.add(class_group)
        await self.db.flush()
        await self.db.refresh(class_group)
        return class_group

    # =========================
    # Delete
    # =========================
    async def delete(self, class_group: ClassGroup) -> None:
        await self.db.delete(class_group)
        await self.db.flush()
