from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.assignment_submission import AssignmentSubmission


class AssignmentSubmissionRepository:
    """
    Repository for school-scoped assignment submission persistence and lookup.

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
    def _normalise_optional_text(
        value: str | None,
    ) -> str | None:
        """
        Trim an optional text value.

        Blank strings are normalised to ``None``.
        """

        if value is None:
            return None

        normalised_value = value.strip()

        return normalised_value or None

    @staticmethod
    def _normalise_status(
        value: str,
    ) -> str:
        """
        Return a validated, trimmed submission status.
        """

        normalised_status = value.strip().lower()

        if not normalised_status:
            raise ValueError(
                "Assignment submission status cannot be blank.",
            )

        return normalised_status

    @staticmethod
    def _apply_relationship_loading(
        statement,
        *,
        include_relationships: bool,
    ):
        """
        Apply the standard submission relationship-loading strategy.
        """

        if not include_relationships:
            return statement

        return statement.options(
            selectinload(
                AssignmentSubmission.assignment,
            ),
            selectinload(
                AssignmentSubmission.student,
            ),
            selectinload(
                AssignmentSubmission.school,
            ),
            selectinload(
                AssignmentSubmission.grader,
            ),
        )

    async def get_by_id(
        self,
        submission_id: int,
        *,
        include_relationships: bool = True,
    ) -> AssignmentSubmission | None:
        """
        Return a submission by its global identifier.

        Prefer ``get_by_id_and_school`` for school-facing workflows.
        """

        self._validate_positive_integer(
            submission_id,
            "submission_id",
        )

        statement = select(
            AssignmentSubmission,
        ).where(
            AssignmentSubmission.id == submission_id,
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
        submission_id: int,
        school_id: int,
        *,
        include_relationships: bool = True,
    ) -> AssignmentSubmission | None:
        """
        Return a submission only when it belongs to the specified school.
        """

        self._validate_positive_integer(
            submission_id,
            "submission_id",
        )
        self._validate_positive_integer(
            school_id,
            "school_id",
        )

        statement = select(
            AssignmentSubmission,
        ).where(
            AssignmentSubmission.id == submission_id,
            AssignmentSubmission.school_id == school_id,
        )

        statement = self._apply_relationship_loading(
            statement,
            include_relationships=include_relationships,
        )

        result = await self.db.execute(
            statement,
        )

        return result.scalar_one_or_none()

    async def get_by_assignment_and_student(
        self,
        *,
        assignment_id: int,
        student_id: int,
        school_id: int,
        include_relationships: bool = True,
    ) -> AssignmentSubmission | None:
        """
        Return one student's submission for an assignment in a school.
        """

        self._validate_positive_integer(
            assignment_id,
            "assignment_id",
        )
        self._validate_positive_integer(
            student_id,
            "student_id",
        )
        self._validate_positive_integer(
            school_id,
            "school_id",
        )

        statement = select(
            AssignmentSubmission,
        ).where(
            AssignmentSubmission.assignment_id == assignment_id,
            AssignmentSubmission.student_id == student_id,
            AssignmentSubmission.school_id == school_id,
        )

        statement = self._apply_relationship_loading(
            statement,
            include_relationships=include_relationships,
        )

        result = await self.db.execute(
            statement,
        )

        return result.scalar_one_or_none()

    async def list_by_assignment(
        self,
        assignment_id: int,
        *,
        school_id: int | None = None,
        include_relationships: bool = True,
    ) -> list[AssignmentSubmission]:
        """
        Return submissions belonging to one assignment.
        """

        self._validate_positive_integer(
            assignment_id,
            "assignment_id",
        )

        statement = select(
            AssignmentSubmission,
        ).where(
            AssignmentSubmission.assignment_id == assignment_id,
        )

        if school_id is not None:
            self._validate_positive_integer(
                school_id,
                "school_id",
            )

            statement = statement.where(
                AssignmentSubmission.school_id == school_id,
            )

        statement = self._apply_relationship_loading(
            statement,
            include_relationships=include_relationships,
        )

        statement = statement.order_by(
            AssignmentSubmission.submitted_at.desc(),
            AssignmentSubmission.id.desc(),
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
        include_relationships: bool = True,
    ) -> list[AssignmentSubmission]:
        """
        Return submissions belonging to one student.
        """

        self._validate_positive_integer(
            student_id,
            "student_id",
        )

        statement = select(
            AssignmentSubmission,
        ).where(
            AssignmentSubmission.student_id == student_id,
        )

        if school_id is not None:
            self._validate_positive_integer(
                school_id,
                "school_id",
            )

            statement = statement.where(
                AssignmentSubmission.school_id == school_id,
            )

        statement = self._apply_relationship_loading(
            statement,
            include_relationships=include_relationships,
        )

        statement = statement.order_by(
            AssignmentSubmission.submitted_at.desc(),
            AssignmentSubmission.id.desc(),
        )

        result = await self.db.execute(
            statement,
        )

        return list(
            result.scalars().all(),
        )

    async def create(
        self,
        submission: AssignmentSubmission,
    ) -> AssignmentSubmission:
        """
        Add and flush a new assignment submission.
        """

        self._validate_positive_integer(
            submission.assignment_id,
            "assignment_id",
        )
        self._validate_positive_integer(
            submission.student_id,
            "student_id",
        )
        self._validate_positive_integer(
            submission.school_id,
            "school_id",
        )

        if submission.graded_by is not None:
            self._validate_positive_integer(
                submission.graded_by,
                "graded_by",
            )

        submission.submission_text = self._normalise_optional_text(
            submission.submission_text,
        )
        submission.attachment_url = self._normalise_optional_text(
            submission.attachment_url,
        )
        submission.feedback = self._normalise_optional_text(
            submission.feedback,
        )
        submission.status = self._normalise_status(
            submission.status,
        )

        self.db.add(
            submission,
        )
        await self.db.flush()
        await self.db.refresh(
            submission,
        )

        return submission

    async def save(
        self,
        submission: AssignmentSubmission,
    ) -> AssignmentSubmission:
        """
        Persist and flush an existing assignment submission.
        """

        if submission.id is None:
            raise ValueError(
                "Cannot save an assignment submission without an ID.",
            )

        self._validate_positive_integer(
            submission.id,
            "submission.id",
        )
        self._validate_positive_integer(
            submission.assignment_id,
            "assignment_id",
        )
        self._validate_positive_integer(
            submission.student_id,
            "student_id",
        )
        self._validate_positive_integer(
            submission.school_id,
            "school_id",
        )

        if submission.graded_by is not None:
            self._validate_positive_integer(
                submission.graded_by,
                "graded_by",
            )

        submission.submission_text = self._normalise_optional_text(
            submission.submission_text,
        )
        submission.attachment_url = self._normalise_optional_text(
            submission.attachment_url,
        )
        submission.feedback = self._normalise_optional_text(
            submission.feedback,
        )
        submission.status = self._normalise_status(
            submission.status,
        )

        self.db.add(
            submission,
        )
        await self.db.flush()
        await self.db.refresh(
            submission,
        )

        return submission

    async def delete(
        self,
        submission: AssignmentSubmission,
    ) -> None:
        """
        Delete and flush an assignment submission.
        """

        if submission.id is None:
            raise ValueError(
                "Cannot delete an assignment submission without an ID.",
            )

        self._validate_positive_integer(
            submission.id,
            "submission.id",
        )

        await self.db.delete(
            submission,
        )
        await self.db.flush()
