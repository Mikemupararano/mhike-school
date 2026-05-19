from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.parent_student import ParentStudent


class ParentStudentRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_link(
        self,
        parent_id: int,
        student_id: int,
    ) -> ParentStudent:
        link = ParentStudent(
            parent_id=parent_id,
            student_id=student_id,
        )

        self.db.add(link)

        await self.db.commit()
        await self.db.refresh(link)

        return link

    async def get_link(
        self,
        parent_id: int,
        student_id: int,
    ) -> ParentStudent | None:
        result = await self.db.execute(
            select(ParentStudent).where(
                ParentStudent.parent_id == parent_id,
                ParentStudent.student_id == student_id,
            )
        )

        return result.scalar_one_or_none()

    async def list_children_for_parent(
        self,
        parent_id: int,
    ) -> list[ParentStudent]:
        result = await self.db.execute(
            select(ParentStudent).where(
                ParentStudent.parent_id == parent_id,
            )
        )

        return list(result.scalars().all())

    async def list_parents_for_student(
        self,
        student_id: int,
    ) -> list[ParentStudent]:
        result = await self.db.execute(
            select(ParentStudent).where(
                ParentStudent.student_id == student_id,
            )
        )

        return list(result.scalars().all())

    async def delete_link(
        self,
        link: ParentStudent,
    ) -> None:
        await self.db.delete(link)
        await self.db.commit()
