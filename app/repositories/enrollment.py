from __future__ import annotations

from typing import Any

from sqlalchemy import Select, exists, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.class_group import ClassGroup
from app.models.enrollment import Enrollment
from app.models.user import User


class EnrollmentRepository:
    """
    Repository for class-enrolment persistence and lookup.

    The repository does not commit or roll back transactions. Transaction
    ownership remains with the calling service, import processor, endpoint,
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
        Apply the standard enrolment relationship-loading strategy.
        """

        if not include_relationships:
            return statement

        return statement.options(
            selectinload(
                Enrollment.user,
            ),
            selectinload(
                Enrollment.class_group,
            ),
        )

    async def get_by_id(
        self,
        enrollment_id: int,
        *,
        include_relationships: bool = True,
    ) -> Enrollment | None:
        """
        Return an enrolment by its global identifier.
        """

        self._validate_positive_integer(
            enrollment_id,
            "enrollment_id",
        )

        statement = select(
            Enrollment,
        ).where(
            Enrollment.id == enrollment_id,
        )

        statement = self._apply_relationship_loading(
            statement,
            include_relationships=include_relationships,
        )

        result = await self.db.execute(
            statement,
        )

        return result.scalar_one_or_none()

    async def get_by_id_and_school(
        self,
        enrollment_id: int,
        school_id: int,
        *,
        include_relationships: bool = True,
    ) -> Enrollment | None:
        """
        Return an enrolment only when both its student and class belong to
        the specified school.
        """

        self._validate_positive_integer(
            enrollment_id,
            "enrollment_id",
        )
        self._validate_positive_integer(
            school_id,
            "school_id",
        )

        statement = (
            select(
                Enrollment,
            )
            .join(
                User,
                User.id == Enrollment.user_id,
            )
            .join(
                ClassGroup,
                ClassGroup.id == Enrollment.class_id,
            )
            .where(
                Enrollment.id == enrollment_id,
                User.school_id == school_id,
                ClassGroup.school_id == school_id,
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

    async def get_by_student_and_class(
        self,
        *,
        student_id: int,
        class_id: int,
        include_relationships: bool = True,
    ) -> Enrollment | None:
        """
        Return the enrolment linking one student and one class.
        """

        self._validate_positive_integer(
            student_id,
            "student_id",
        )
        self._validate_positive_integer(
            class_id,
            "class_id",
        )

        statement = select(
            Enrollment,
        ).where(
            Enrollment.user_id == student_id,
            Enrollment.class_id == class_id,
        )

        statement = self._apply_relationship_loading(
            statement,
            include_relationships=include_relationships,
        )

        result = await self.db.execute(
            statement,
        )

        return result.scalar_one_or_none()

    async def get_by_student_and_class_in_school(
        self,
        *,
        student_id: int,
        class_id: int,
        school_id: int,
        include_relationships: bool = True,
    ) -> Enrollment | None:
        """
        Return the student-class enrolment only when both entities belong to
        the specified school.
        """

        self._validate_positive_integer(
            student_id,
            "student_id",
        )
        self._validate_positive_integer(
            class_id,
            "class_id",
        )
        self._validate_positive_integer(
            school_id,
            "school_id",
        )

        statement = (
            select(
                Enrollment,
            )
            .join(
                User,
                User.id == Enrollment.user_id,
            )
            .join(
                ClassGroup,
                ClassGroup.id == Enrollment.class_id,
            )
            .where(
                Enrollment.user_id == student_id,
                Enrollment.class_id == class_id,
                User.school_id == school_id,
                ClassGroup.school_id == school_id,
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
        enrollment_id: int,
    ) -> bool:
        """
        Return whether an enrolment exists by global identifier.
        """

        self._validate_positive_integer(
            enrollment_id,
            "enrollment_id",
        )

        result = await self.db.execute(
            select(
                exists().where(
                    Enrollment.id == enrollment_id,
                ),
            ),
        )

        return bool(
            result.scalar_one(),
        )

    async def exists_for_student_and_class(
        self,
        *,
        student_id: int,
        class_id: int,
    ) -> bool:
        """
        Return whether a student-class enrolment already exists.
        """

        self._validate_positive_integer(
            student_id,
            "student_id",
        )
        self._validate_positive_integer(
            class_id,
            "class_id",
        )

        result = await self.db.execute(
            select(
                exists().where(
                    Enrollment.user_id == student_id,
                    Enrollment.class_id == class_id,
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
        enrollment_id: int | None = None,
        student_id: int | None = None,
        class_id: int | None = None,
    ) -> bool:
        """
        Return whether a school-scoped enrolment exists.

        Supported lookups:

        - by ``enrollment_id``;
        - by ``student_id`` and ``class_id``.

        The query is expressed as ``exists(select(...))`` rather than
        ``select(exists()).select_from(...)`` so it compiles correctly across
        SQLite and PostgreSQL.
        """

        self._validate_positive_integer(
            school_id,
            "school_id",
        )

        by_id = enrollment_id is not None
        by_pair = student_id is not None or class_id is not None

        if by_id and by_pair:
            raise ValueError(
                "Provide enrollment_id or student_id/class_id, not both.",
            )

        if not by_id and not by_pair:
            raise ValueError(
                "Provide enrollment_id or both student_id and class_id.",
            )

        if by_pair and (student_id is None or class_id is None):
            raise ValueError(
                "student_id and class_id must be provided together.",
            )

        exists_query = (
            select(
                Enrollment.id,
            )
            .join(
                User,
                User.id == Enrollment.user_id,
            )
            .join(
                ClassGroup,
                ClassGroup.id == Enrollment.class_id,
            )
            .where(
                User.school_id == school_id,
                ClassGroup.school_id == school_id,
            )
        )

        if enrollment_id is not None:
            self._validate_positive_integer(
                enrollment_id,
                "enrollment_id",
            )

            exists_query = exists_query.where(
                Enrollment.id == enrollment_id,
            )
        else:
            assert student_id is not None
            assert class_id is not None

            self._validate_positive_integer(
                student_id,
                "student_id",
            )
            self._validate_positive_integer(
                class_id,
                "class_id",
            )

            exists_query = exists_query.where(
                Enrollment.user_id == student_id,
                Enrollment.class_id == class_id,
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

    async def list_by_class(
        self,
        class_id: int,
        *,
        school_id: int | None = None,
    ) -> list[Enrollment]:
        """
        Return enrolments for one class.

        Supplying ``school_id`` is recommended for school-facing workflows.
        """

        self._validate_positive_integer(
            class_id,
            "class_id",
        )

        statement = (
            select(
                Enrollment,
            )
            .options(
                selectinload(
                    Enrollment.user,
                ),
                selectinload(
                    Enrollment.class_group,
                ),
            )
            .where(
                Enrollment.class_id == class_id,
            )
        )

        if school_id is not None:
            self._validate_positive_integer(
                school_id,
                "school_id",
            )

            statement = (
                statement.join(
                    User,
                    User.id == Enrollment.user_id,
                )
                .join(
                    ClassGroup,
                    ClassGroup.id == Enrollment.class_id,
                )
                .where(
                    User.school_id == school_id,
                    ClassGroup.school_id == school_id,
                )
            )

        statement = statement.order_by(
            Enrollment.created_at.desc(),
            Enrollment.id.desc(),
        )

        result = await self.db.execute(
            statement,
        )

        return list(
            result.scalars().all(),
        )

    async def list_by_student(
        self,
        student_id: int,
        *,
        school_id: int | None = None,
    ) -> list[Enrollment]:
        """
        Return enrolments for one student.

        Supplying ``school_id`` is recommended for school-facing workflows.
        """

        self._validate_positive_integer(
            student_id,
            "student_id",
        )

        statement = (
            select(
                Enrollment,
            )
            .options(
                selectinload(
                    Enrollment.user,
                ),
                selectinload(
                    Enrollment.class_group,
                ),
            )
            .where(
                Enrollment.user_id == student_id,
            )
        )

        if school_id is not None:
            self._validate_positive_integer(
                school_id,
                "school_id",
            )

            statement = (
                statement.join(
                    User,
                    User.id == Enrollment.user_id,
                )
                .join(
                    ClassGroup,
                    ClassGroup.id == Enrollment.class_id,
                )
                .where(
                    User.school_id == school_id,
                    ClassGroup.school_id == school_id,
                )
            )

        statement = statement.order_by(
            Enrollment.created_at.desc(),
            Enrollment.id.desc(),
        )

        result = await self.db.execute(
            statement,
        )

        return list(
            result.scalars().all(),
        )

    async def create(
        self,
        enrollment: Enrollment,
    ) -> Enrollment:
        """
        Add and flush a new enrolment.
        """

        self._validate_positive_integer(
            enrollment.user_id,
            "user_id",
        )
        self._validate_positive_integer(
            enrollment.class_id,
            "class_id",
        )

        self.db.add(
            enrollment,
        )
        await self.db.flush()
        await self.db.refresh(
            enrollment,
        )

        return enrollment

    async def delete(
        self,
        enrollment: Enrollment,
    ) -> None:
        """
        Delete and flush an enrolment.
        """

        if enrollment.id is None:
            raise ValueError(
                "Cannot delete an enrolment without an ID.",
            )

        self._validate_positive_integer(
            enrollment.id,
            "enrollment.id",
        )

        await self.db.delete(
            enrollment,
        )
        await self.db.flush()
