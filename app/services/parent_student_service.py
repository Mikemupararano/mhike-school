from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.parent_student import ParentStudent
from app.repositories.parent_student import (
    ParentStudentRepository,
)
from app.schemas.parent_student import (
    ParentStudentCreate,
)


class ParentStudentService:
    def __init__(self, db: AsyncSession):
        self.repo = ParentStudentRepository(db)

    async def create_link(
        self,
        data: ParentStudentCreate,
    ) -> ParentStudent:
        existing = await self.repo.get_link(
            parent_id=data.parent_id,
            student_id=data.student_id,
        )

        if existing is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=("Parent/student relationship already exists."),
            )

        return await self.repo.create_link(
            parent_id=data.parent_id,
            student_id=data.student_id,
        )

    async def list_children_for_parent(
        self,
        parent_id: int,
    ) -> list[ParentStudent]:
        return await self.repo.list_children_for_parent(
            parent_id=parent_id,
        )

    async def list_parents_for_student(
        self,
        student_id: int,
    ) -> list[ParentStudent]:
        return await self.repo.list_parents_for_student(
            student_id=student_id,
        )

    async def validate_parent_access(
        self,
        parent_id: int,
        student_id: int,
    ) -> None:
        link = await self.repo.get_link(
            parent_id=parent_id,
            student_id=student_id,
        )

        if link is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=("Parent does not have access to this student."),
            )

    async def remove_link(
        self,
        parent_id: int,
        student_id: int,
    ) -> None:
        link = await self.repo.get_link(
            parent_id=parent_id,
            student_id=student_id,
        )

        if link is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Parent/student relationship not found.",
            )

        await self.repo.delete_link(link)
