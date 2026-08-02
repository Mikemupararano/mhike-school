from __future__ import annotations

from typing import Any

from sqlalchemy import Select, exists, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.parent_student import ParentStudent
from app.models.user import User


class ParentStudentRepository:
    """
    Repository for parent-student relationship persistence and lookup.

    The repository never commits or rolls back transactions. Transaction
    ownership remains with the calling service, endpoint, import processor,
    or background task.
    """

    def __init__(
        self,
        db: AsyncSession,
    ) -> None:
        self.db = db

    @staticmethod
    def _validate_positive_integer(
        value: int,
        field_name: str,
    ) -> None:
        """
        Require a positive integer identifier.
        """

        if not isinstance(value, int) or isinstance(value, bool) or value < 1:
            raise ValueError(
                f"{field_name} must be a positive integer.",
            )

    @staticmethod
    def _apply_relationship_loading(
        statement: Select[Any],
        *,
        include_relationships: bool,
    ) -> Select[Any]:
        """
        Apply standard parent and student relationship loading.
        """

        if not include_relationships:
            return statement

        return statement.options(
            selectinload(
                ParentStudent.parent,
            ),
            selectinload(
                ParentStudent.student,
            ),
        )

    async def get_by_id(
        self,
        link_id: int,
        *,
        include_relationships: bool = True,
    ) -> ParentStudent | None:
        """
        Return a parent-student link by its global identifier.
        """

        self._validate_positive_integer(
            link_id,
            "link_id",
        )

        statement = select(
            ParentStudent,
        ).where(
            ParentStudent.id == link_id,
        )

        statement = self._apply_relationship_loading(
            statement,
            include_relationships=include_relationships,
        )

        result = await self.db.execute(
            statement,
        )

        return result.scalar_one_or_none()

    async def get_link(
        self,
        parent_id: int,
        student_id: int,
        *,
        include_relationships: bool = True,
    ) -> ParentStudent | None:
        """
        Return the relationship linking one parent and one student.
        """

        self._validate_positive_integer(
            parent_id,
            "parent_id",
        )
        self._validate_positive_integer(
            student_id,
            "student_id",
        )

        statement = select(
            ParentStudent,
        ).where(
            ParentStudent.parent_id == parent_id,
            ParentStudent.student_id == student_id,
        )

        statement = self._apply_relationship_loading(
            statement,
            include_relationships=include_relationships,
        )

        result = await self.db.execute(
            statement,
        )

        return result.scalar_one_or_none()

    async def get_link_in_school(
        self,
        *,
        parent_id: int,
        student_id: int,
        school_id: int,
        include_relationships: bool = True,
    ) -> ParentStudent | None:
        """
        Return a parent-student link only when both users belong to the
        specified school.
        """

        self._validate_positive_integer(
            parent_id,
            "parent_id",
        )
        self._validate_positive_integer(
            student_id,
            "student_id",
        )
        self._validate_positive_integer(
            school_id,
            "school_id",
        )

        parent_user = User.__table__.alias(
            "parent_user",
        )
        student_user = User.__table__.alias(
            "student_user",
        )

        statement = (
            select(
                ParentStudent,
            )
            .join(
                parent_user,
                parent_user.c.id == ParentStudent.parent_id,
            )
            .join(
                student_user,
                student_user.c.id == ParentStudent.student_id,
            )
            .where(
                ParentStudent.parent_id == parent_id,
                ParentStudent.student_id == student_id,
                parent_user.c.school_id == school_id,
                student_user.c.school_id == school_id,
            )
        )

        statement = self._apply_relationship_loading(
            statement,
            include_relationships=include_relationships,
        )

        result = await self.db.execute(
            statement,
        )

        return result.scalar_one_or_none()

    async def exists(
        self,
        link_id: int,
    ) -> bool:
        """
        Return whether a parent-student link exists by global identifier.
        """

        self._validate_positive_integer(
            link_id,
            "link_id",
        )

        result = await self.db.execute(
            select(
                exists().where(
                    ParentStudent.id == link_id,
                ),
            ),
        )

        return bool(
            result.scalar_one(),
        )

    async def exists_for_parent_and_student(
        self,
        *,
        parent_id: int,
        student_id: int,
    ) -> bool:
        """
        Return whether a parent-student relationship already exists.
        """

        self._validate_positive_integer(
            parent_id,
            "parent_id",
        )
        self._validate_positive_integer(
            student_id,
            "student_id",
        )

        result = await self.db.execute(
            select(
                exists().where(
                    ParentStudent.parent_id == parent_id,
                    ParentStudent.student_id == student_id,
                ),
            ),
        )

        return bool(
            result.scalar_one(),
        )

    async def exists_in_school(
        self,
        *,
        school_id: int,
        link_id: int | None = None,
        parent_id: int | None = None,
        student_id: int | None = None,
    ) -> bool:
        """
        Return whether a school-scoped parent-student link exists.

        Supported lookups:

        - by ``link_id``;
        - by ``parent_id`` and ``student_id``.
        """

        self._validate_positive_integer(
            school_id,
            "school_id",
        )

        by_id = link_id is not None
        by_pair = parent_id is not None or student_id is not None

        if by_id and by_pair:
            raise ValueError(
                "Provide link_id or parent_id/student_id, not both.",
            )

        if not by_id and not by_pair:
            raise ValueError(
                "Provide link_id or both parent_id and student_id.",
            )

        if by_pair and (parent_id is None or student_id is None):
            raise ValueError(
                "parent_id and student_id must be provided together.",
            )

        parent_user = User.__table__.alias(
            "parent_user",
        )
        student_user = User.__table__.alias(
            "student_user",
        )

        exists_query = (
            select(
                ParentStudent.id,
            )
            .join(
                parent_user,
                parent_user.c.id == ParentStudent.parent_id,
            )
            .join(
                student_user,
                student_user.c.id == ParentStudent.student_id,
            )
            .where(
                parent_user.c.school_id == school_id,
                student_user.c.school_id == school_id,
            )
        )

        if link_id is not None:
            self._validate_positive_integer(
                link_id,
                "link_id",
            )

            exists_query = exists_query.where(
                ParentStudent.id == link_id,
            )
        else:
            assert parent_id is not None
            assert student_id is not None

            self._validate_positive_integer(
                parent_id,
                "parent_id",
            )
            self._validate_positive_integer(
                student_id,
                "student_id",
            )

            exists_query = exists_query.where(
                ParentStudent.parent_id == parent_id,
                ParentStudent.student_id == student_id,
            )

        result = await self.db.execute(
            select(
                exists(
                    exists_query,
                ),
            ),
        )

        return bool(
            result.scalar_one(),
        )

    async def list_children_for_parent(
        self,
        parent_id: int,
        *,
        school_id: int | None = None,
        include_relationships: bool = True,
    ) -> list[ParentStudent]:
        """
        Return all student links for one parent.

        Supplying ``school_id`` enforces that both parent and students belong
        to the same school.
        """

        self._validate_positive_integer(
            parent_id,
            "parent_id",
        )

        statement = select(
            ParentStudent,
        ).where(
            ParentStudent.parent_id == parent_id,
        )

        if school_id is not None:
            self._validate_positive_integer(
                school_id,
                "school_id",
            )

            parent_user = User.__table__.alias(
                "parent_user",
            )
            student_user = User.__table__.alias(
                "student_user",
            )

            statement = (
                statement.join(
                    parent_user,
                    parent_user.c.id == ParentStudent.parent_id,
                )
                .join(
                    student_user,
                    student_user.c.id == ParentStudent.student_id,
                )
                .where(
                    parent_user.c.school_id == school_id,
                    student_user.c.school_id == school_id,
                )
            )

        statement = self._apply_relationship_loading(
            statement,
            include_relationships=include_relationships,
        )

        statement = statement.order_by(
            ParentStudent.id.asc(),
        )

        result = await self.db.execute(
            statement,
        )

        return list(
            result.scalars().all(),
        )

    async def list_parents_for_student(
        self,
        student_id: int,
        *,
        school_id: int | None = None,
        include_relationships: bool = True,
    ) -> list[ParentStudent]:
        """
        Return all parent links for one student.

        Supplying ``school_id`` enforces that both student and parents belong
        to the same school.
        """

        self._validate_positive_integer(
            student_id,
            "student_id",
        )

        statement = select(
            ParentStudent,
        ).where(
            ParentStudent.student_id == student_id,
        )

        if school_id is not None:
            self._validate_positive_integer(
                school_id,
                "school_id",
            )

            parent_user = User.__table__.alias(
                "parent_user",
            )
            student_user = User.__table__.alias(
                "student_user",
            )

            statement = (
                statement.join(
                    parent_user,
                    parent_user.c.id == ParentStudent.parent_id,
                )
                .join(
                    student_user,
                    student_user.c.id == ParentStudent.student_id,
                )
                .where(
                    parent_user.c.school_id == school_id,
                    student_user.c.school_id == school_id,
                )
            )

        statement = self._apply_relationship_loading(
            statement,
            include_relationships=include_relationships,
        )

        statement = statement.order_by(
            ParentStudent.id.asc(),
        )

        result = await self.db.execute(
            statement,
        )

        return list(
            result.scalars().all(),
        )

    async def create_link(
        self,
        parent_id: int,
        student_id: int,
    ) -> ParentStudent:
        """
        Create and flush a parent-student relationship.

        This method intentionally does not commit.
        """

        self._validate_positive_integer(
            parent_id,
            "parent_id",
        )
        self._validate_positive_integer(
            student_id,
            "student_id",
        )

        link = ParentStudent(
            parent_id=parent_id,
            student_id=student_id,
        )

        self.db.add(
            link,
        )
        await self.db.flush()
        await self.db.refresh(
            link,
        )

        return link

    async def delete_link(
        self,
        link: ParentStudent,
    ) -> None:
        """
        Delete and flush a parent-student relationship.

        This method intentionally does not commit.
        """

        if link.id is None:
            raise ValueError(
                "Cannot delete a parent-student link without an ID.",
            )

        self._validate_positive_integer(
            link.id,
            "link.id",
        )

        await self.db.delete(
            link,
        )
        await self.db.flush()
