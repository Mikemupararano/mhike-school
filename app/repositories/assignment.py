from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.assignment import Assignment


class AssignmentRepository:
    """
    Repository for school-scoped assignment persistence and lookup.

    This repository never commits or rolls back transactions. Transaction
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
        Require a positive integer value.
        """

        if not isinstance(value, int) or isinstance(value, bool) or value < 1:
            raise ValueError(
                f"{field_name} must be a positive integer.",
            )

    @staticmethod
    def _normalise_title(
        title: str,
    ) -> str:
        """
        Return a validated and trimmed assignment title.
        """

        normalised_title = title.strip()

        if not normalised_title:
            raise ValueError(
                "Assignment title cannot be blank.",
            )

        if len(normalised_title) > 255:
            raise ValueError(
                "Assignment title cannot exceed 255 characters.",
            )

        return normalised_title

    @staticmethod
    def _normalise_description(
        description: str | None,
    ) -> str | None:
        """
        Return a trimmed optional assignment description.
        """

        if description is None:
            return None

        normalised_description = description.strip()

        if not normalised_description:
            return None

        return normalised_description

    @staticmethod
    def _apply_relationship_loading(
        statement,
        *,
        include_relationships: bool,
    ):
        """
        Apply the standard assignment relationship loading strategy.
        """

        if not include_relationships:
            return statement

        return statement.options(
            selectinload(
                Assignment.course,
            ),
            selectinload(
                Assignment.school,
            ),
            selectinload(
                Assignment.creator,
            ),
        )

    async def get_by_id(
        self,
        assignment_id: int,
        *,
        include_relationships: bool = True,
    ) -> Assignment | None:
        """
        Return an assignment by its global identifier.

        Prefer ``get_by_id_and_school`` for school-facing workflows.
        """

        self._validate_positive_integer(
            assignment_id,
            "assignment_id",
        )

        statement = select(
            Assignment,
        ).where(
            Assignment.id == assignment_id,
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
        assignment_id: int,
        school_id: int,
        *,
        include_relationships: bool = True,
    ) -> Assignment | None:
        """
        Return an assignment only when it belongs to the specified school.
        """

        self._validate_positive_integer(
            assignment_id,
            "assignment_id",
        )
        self._validate_positive_integer(
            school_id,
            "school_id",
        )

        statement = select(
            Assignment,
        ).where(
            Assignment.id == assignment_id,
            Assignment.school_id == school_id,
        )

        statement = self._apply_relationship_loading(
            statement,
            include_relationships=include_relationships,
        )

        result = await self.db.execute(
            statement,
        )

        return result.scalar_one_or_none()

    async def get_by_title_and_course(
        self,
        *,
        title: str,
        course_id: int,
        school_id: int,
        include_relationships: bool = True,
    ) -> Assignment | None:
        """
        Return an assignment matching title, course, and school.

        The Assignment model does not currently enforce a uniqueness
        constraint for this identity, so callers should use this consistently
        for import upserts.
        """

        normalised_title = self._normalise_title(
            title,
        )

        self._validate_positive_integer(
            course_id,
            "course_id",
        )
        self._validate_positive_integer(
            school_id,
            "school_id",
        )

        statement = select(
            Assignment,
        ).where(
            Assignment.title == normalised_title,
            Assignment.course_id == course_id,
            Assignment.school_id == school_id,
        )

        statement = self._apply_relationship_loading(
            statement,
            include_relationships=include_relationships,
        )

        result = await self.db.execute(
            statement,
        )

        return result.scalar_one_or_none()

    async def list_all(
        self,
        *,
        include_relationships: bool = True,
    ) -> list[Assignment]:
        """
        Return every assignment across all schools.

        Intended for platform-administrator workflows.
        """

        statement = select(
            Assignment,
        )

        statement = self._apply_relationship_loading(
            statement,
            include_relationships=include_relationships,
        )

        statement = statement.order_by(
            Assignment.created_at.desc(),
            Assignment.id.desc(),
        )

        result = await self.db.execute(
            statement,
        )

        return list(
            result.scalars().all(),
        )

    async def list_by_school(
        self,
        school_id: int,
        *,
        course_id: int | None = None,
        created_by: int | None = None,
        is_published: bool | None = None,
        include_relationships: bool = True,
    ) -> list[Assignment]:
        """
        Return assignments belonging to one school.
        """

        self._validate_positive_integer(
            school_id,
            "school_id",
        )

        statement = select(
            Assignment,
        ).where(
            Assignment.school_id == school_id,
        )

        if course_id is not None:
            self._validate_positive_integer(
                course_id,
                "course_id",
            )
            statement = statement.where(
                Assignment.course_id == course_id,
            )

        if created_by is not None:
            self._validate_positive_integer(
                created_by,
                "created_by",
            )
            statement = statement.where(
                Assignment.created_by == created_by,
            )

        if is_published is not None:
            statement = statement.where(
                Assignment.is_published.is_(
                    is_published,
                ),
            )

        statement = self._apply_relationship_loading(
            statement,
            include_relationships=include_relationships,
        )

        statement = statement.order_by(
            Assignment.created_at.desc(),
            Assignment.id.desc(),
        )

        result = await self.db.execute(
            statement,
        )

        return list(
            result.scalars().all(),
        )

    async def list_by_creator(
        self,
        created_by: int,
        *,
        school_id: int | None = None,
        include_relationships: bool = True,
    ) -> list[Assignment]:
        """
        Return assignments created by one user.
        """

        self._validate_positive_integer(
            created_by,
            "created_by",
        )

        statement = select(
            Assignment,
        ).where(
            Assignment.created_by == created_by,
        )

        if school_id is not None:
            self._validate_positive_integer(
                school_id,
                "school_id",
            )
            statement = statement.where(
                Assignment.school_id == school_id,
            )

        statement = self._apply_relationship_loading(
            statement,
            include_relationships=include_relationships,
        )

        statement = statement.order_by(
            Assignment.created_at.desc(),
            Assignment.id.desc(),
        )

        result = await self.db.execute(
            statement,
        )

        return list(
            result.scalars().all(),
        )

    async def list_published_for_school(
        self,
        school_id: int,
        *,
        include_relationships: bool = True,
    ) -> list[Assignment]:
        """
        Return published assignments for one school.
        """

        return await self.list_by_school(
            school_id,
            is_published=True,
            include_relationships=include_relationships,
        )

    async def create(
        self,
        assignment: Assignment,
    ) -> Assignment:
        """
        Add and flush a new assignment.
        """

        assignment.title = self._normalise_title(
            assignment.title,
        )
        assignment.description = self._normalise_description(
            assignment.description,
        )

        self._validate_positive_integer(
            assignment.course_id,
            "course_id",
        )
        self._validate_positive_integer(
            assignment.school_id,
            "school_id",
        )
        self._validate_positive_integer(
            assignment.created_by,
            "created_by",
        )
        self._validate_positive_integer(
            assignment.max_score,
            "max_score",
        )

        self.db.add(
            assignment,
        )
        await self.db.flush()
        await self.db.refresh(
            assignment,
        )

        return assignment

    async def save(
        self,
        assignment: Assignment,
    ) -> Assignment:
        """
        Persist and flush an existing assignment.
        """

        if assignment.id is None:
            raise ValueError(
                "Cannot save an assignment without an ID.",
            )

        self._validate_positive_integer(
            assignment.id,
            "assignment.id",
        )

        assignment.title = self._normalise_title(
            assignment.title,
        )
        assignment.description = self._normalise_description(
            assignment.description,
        )

        self._validate_positive_integer(
            assignment.course_id,
            "course_id",
        )
        self._validate_positive_integer(
            assignment.school_id,
            "school_id",
        )
        self._validate_positive_integer(
            assignment.created_by,
            "created_by",
        )
        self._validate_positive_integer(
            assignment.max_score,
            "max_score",
        )

        self.db.add(
            assignment,
        )
        await self.db.flush()
        await self.db.refresh(
            assignment,
        )

        return assignment

    async def delete(
        self,
        assignment: Assignment,
    ) -> None:
        """
        Delete and flush an assignment.
        """

        if assignment.id is None:
            raise ValueError(
                "Cannot delete an assignment without an ID.",
            )

        self._validate_positive_integer(
            assignment.id,
            "assignment.id",
        )

        await self.db.delete(
            assignment,
        )
        await self.db.flush()
