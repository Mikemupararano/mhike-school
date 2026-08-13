from __future__ import annotations

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.assessment_target import AssessmentTarget

_UNSET = object()


class AssessmentTargetRepository:
    """
    Repository for school-scoped assessment target persistence and lookup.

    Assessment targets are unique per student/course pair.

    The repository never commits or rolls back transactions. Transaction
    ownership remains with the calling service, endpoint, background task,
    import workflow, or other application layer.
    """

    def __init__(
        self,
        db: AsyncSession,
    ) -> None:
        self.db = db

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    @staticmethod
    def _validate_positive_integer(
        value: int,
        field_name: str,
    ) -> None:
        """
        Require a positive integer identifier.
        """

        if (
            not isinstance(
                value,
                int,
            )
            or isinstance(
                value,
                bool,
            )
            or value < 1
        ):
            raise ValueError(
                f"{field_name} must be a positive integer.",
            )

    @staticmethod
    def _normalise_optional_text(
        value: str | None,
        *,
        field_name: str,
        max_length: int | None = None,
    ) -> str | None:
        """
        Return trimmed optional text.

        Blank strings are normalised to None.
        """

        if value is None:
            return None

        if not isinstance(
            value,
            str,
        ):
            raise ValueError(
                f"{field_name} must be a string or None.",
            )

        cleaned = value.strip()

        if not cleaned:
            return None

        if max_length is not None and len(cleaned) > max_length:
            raise ValueError(
                f"{field_name} cannot exceed {max_length} characters.",
            )

        return cleaned

    @staticmethod
    def _normalise_grade_label(
        value: str,
    ) -> str:
        """
        Return a validated target grade label.
        """

        if not isinstance(
            value,
            str,
        ):
            raise ValueError(
                "grade_label must be a string.",
            )

        cleaned = value.strip()

        if not cleaned:
            raise ValueError(
                "grade_label cannot be blank.",
            )

        if len(cleaned) > 100:
            raise ValueError(
                "grade_label cannot exceed 100 characters.",
            )

        return cleaned

    @staticmethod
    def _normalise_grade_points(
        value: Decimal | int | float | str | None,
    ) -> Decimal | None:
        """
        Return validated optional grade points.
        """

        if value is None:
            return None

        try:
            cleaned = Decimal(
                str(value),
            )
        except Exception as exc:
            raise ValueError(
                "grade_points must be numeric or None.",
            ) from exc

        if cleaned < Decimal("0"):
            raise ValueError(
                "grade_points cannot be negative.",
            )

        return cleaned

    # ------------------------------------------------------------------
    # Relationship loading
    # ------------------------------------------------------------------

    @staticmethod
    def _apply_relationship_loading(
        statement,
        *,
        include_relationships: bool,
    ):
        """
        Apply the standard eager-loading configuration.

        When enabled, returned AssessmentTarget objects include:

        - school;
        - student;
        - course;
        - user who set the target.
        """

        if not include_relationships:
            return statement

        return statement.options(
            selectinload(
                AssessmentTarget.school,
            ),
            selectinload(
                AssessmentTarget.student,
            ),
            selectinload(
                AssessmentTarget.course,
            ),
            selectinload(
                AssessmentTarget.set_by,
            ),
        )

    # ------------------------------------------------------------------
    # Single-record lookup
    # ------------------------------------------------------------------

    async def get_by_id(
        self,
        target_id: int,
        *,
        include_relationships: bool = True,
    ) -> AssessmentTarget | None:
        """
        Return an assessment target by global identifier.

        Prefer ``get_by_id_and_school`` in school-facing workflows.
        """

        self._validate_positive_integer(
            target_id,
            "target_id",
        )

        statement = select(
            AssessmentTarget,
        ).where(
            AssessmentTarget.id == target_id,
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
        target_id: int,
        school_id: int,
        *,
        include_relationships: bool = True,
    ) -> AssessmentTarget | None:
        """
        Return a target only when it belongs to the supplied school.
        """

        self._validate_positive_integer(
            target_id,
            "target_id",
        )

        self._validate_positive_integer(
            school_id,
            "school_id",
        )

        statement = select(
            AssessmentTarget,
        ).where(
            AssessmentTarget.id == target_id,
            AssessmentTarget.school_id == school_id,
        )

        statement = self._apply_relationship_loading(
            statement,
            include_relationships=include_relationships,
        )

        result = await self.db.execute(
            statement,
        )

        return result.scalar_one_or_none()

    async def get_by_student_and_course(
        self,
        *,
        student_id: int,
        course_id: int,
        school_id: int | None = None,
        include_relationships: bool = True,
    ) -> AssessmentTarget | None:
        """
        Return the current target for one student/course pair.

        ``school_id`` should normally be supplied in school-facing workflows.
        """

        self._validate_positive_integer(
            student_id,
            "student_id",
        )

        self._validate_positive_integer(
            course_id,
            "course_id",
        )

        if school_id is not None:
            self._validate_positive_integer(
                school_id,
                "school_id",
            )

        statement = select(
            AssessmentTarget,
        ).where(
            AssessmentTarget.student_id == student_id,
            AssessmentTarget.course_id == course_id,
        )

        if school_id is not None:
            statement = statement.where(
                AssessmentTarget.school_id == school_id,
            )

        statement = self._apply_relationship_loading(
            statement,
            include_relationships=include_relationships,
        )

        result = await self.db.execute(
            statement,
        )

        return result.scalar_one_or_none()

    # ------------------------------------------------------------------
    # Listing
    # ------------------------------------------------------------------

    async def list_by_school(
        self,
        school_id: int,
        *,
        student_id: int | None = None,
        course_id: int | None = None,
        set_by_id: int | None = None,
        academic_year: str | None = None,
        include_relationships: bool = True,
    ) -> list[AssessmentTarget]:
        """
        Return targets belonging to one school.

        Optional filters may restrict results by student, course, setter or
        academic year.

        Results are ordered by newest update first, then identifier.
        """

        self._validate_positive_integer(
            school_id,
            "school_id",
        )

        if student_id is not None:
            self._validate_positive_integer(
                student_id,
                "student_id",
            )

        if course_id is not None:
            self._validate_positive_integer(
                course_id,
                "course_id",
            )

        if set_by_id is not None:
            self._validate_positive_integer(
                set_by_id,
                "set_by_id",
            )

        clean_academic_year = self._normalise_optional_text(
            academic_year,
            field_name="academic_year",
            max_length=50,
        )

        statement = select(
            AssessmentTarget,
        ).where(
            AssessmentTarget.school_id == school_id,
        )

        if student_id is not None:
            statement = statement.where(
                AssessmentTarget.student_id == student_id,
            )

        if course_id is not None:
            statement = statement.where(
                AssessmentTarget.course_id == course_id,
            )

        if set_by_id is not None:
            statement = statement.where(
                AssessmentTarget.set_by_id == set_by_id,
            )

        if clean_academic_year is not None:
            statement = statement.where(
                AssessmentTarget.academic_year == clean_academic_year,
            )

        statement = statement.order_by(
            AssessmentTarget.updated_at.desc(),
            AssessmentTarget.id.desc(),
        )

        statement = self._apply_relationship_loading(
            statement,
            include_relationships=include_relationships,
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
        academic_year: str | None = None,
        include_relationships: bool = True,
    ) -> list[AssessmentTarget]:
        """
        Return all course targets for one student.
        """

        self._validate_positive_integer(
            student_id,
            "student_id",
        )

        if school_id is not None:
            self._validate_positive_integer(
                school_id,
                "school_id",
            )

        clean_academic_year = self._normalise_optional_text(
            academic_year,
            field_name="academic_year",
            max_length=50,
        )

        statement = select(
            AssessmentTarget,
        ).where(
            AssessmentTarget.student_id == student_id,
        )

        if school_id is not None:
            statement = statement.where(
                AssessmentTarget.school_id == school_id,
            )

        if clean_academic_year is not None:
            statement = statement.where(
                AssessmentTarget.academic_year == clean_academic_year,
            )

        statement = statement.order_by(
            AssessmentTarget.updated_at.desc(),
            AssessmentTarget.id.desc(),
        )

        statement = self._apply_relationship_loading(
            statement,
            include_relationships=include_relationships,
        )

        result = await self.db.execute(
            statement,
        )

        return list(
            result.scalars().all(),
        )

    async def list_by_course(
        self,
        course_id: int,
        *,
        school_id: int | None = None,
        academic_year: str | None = None,
        include_relationships: bool = True,
    ) -> list[AssessmentTarget]:
        """
        Return all student targets for one course.
        """

        self._validate_positive_integer(
            course_id,
            "course_id",
        )

        if school_id is not None:
            self._validate_positive_integer(
                school_id,
                "school_id",
            )

        clean_academic_year = self._normalise_optional_text(
            academic_year,
            field_name="academic_year",
            max_length=50,
        )

        statement = select(
            AssessmentTarget,
        ).where(
            AssessmentTarget.course_id == course_id,
        )

        if school_id is not None:
            statement = statement.where(
                AssessmentTarget.school_id == school_id,
            )

        if clean_academic_year is not None:
            statement = statement.where(
                AssessmentTarget.academic_year == clean_academic_year,
            )

        statement = statement.order_by(
            AssessmentTarget.updated_at.desc(),
            AssessmentTarget.id.desc(),
        )

        statement = self._apply_relationship_loading(
            statement,
            include_relationships=include_relationships,
        )

        result = await self.db.execute(
            statement,
        )

        return list(
            result.scalars().all(),
        )

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    async def create(
        self,
        *,
        school_id: int,
        student_id: int,
        course_id: int,
        grade_label: str,
        set_by_id: int,
        grade_points: Decimal | int | float | str | None = None,
        academic_year: str | None = None,
        notes: str | None = None,
    ) -> AssessmentTarget:
        """
        Add a new assessment target to the session.

        This method does not flush or commit.
        """

        self._validate_positive_integer(
            school_id,
            "school_id",
        )

        self._validate_positive_integer(
            student_id,
            "student_id",
        )

        self._validate_positive_integer(
            course_id,
            "course_id",
        )

        self._validate_positive_integer(
            set_by_id,
            "set_by_id",
        )

        clean_grade_label = self._normalise_grade_label(
            grade_label,
        )

        clean_grade_points = self._normalise_grade_points(
            grade_points,
        )

        clean_academic_year = self._normalise_optional_text(
            academic_year,
            field_name="academic_year",
            max_length=50,
        )

        clean_notes = self._normalise_optional_text(
            notes,
            field_name="notes",
        )

        target = AssessmentTarget(
            school_id=school_id,
            student_id=student_id,
            course_id=course_id,
            grade_label=clean_grade_label,
            grade_points=clean_grade_points,
            academic_year=clean_academic_year,
            notes=clean_notes,
            set_by_id=set_by_id,
        )

        self.db.add(
            target,
        )

        return target

    async def update(
        self,
        target: AssessmentTarget,
        *,
        grade_label: str | object = _UNSET,
        grade_points: Decimal | int | float | str | None | object = _UNSET,
        academic_year: str | None | object = _UNSET,
        notes: str | None | object = _UNSET,
        set_by_id: int | object = _UNSET,
    ) -> AssessmentTarget:
        """
        Update mutable target fields.

        ``_UNSET`` means that a field was not supplied and must remain
        unchanged.

        Passing ``None`` explicitly clears nullable fields:

        - grade_points;
        - academic_year;
        - notes.

        ``grade_label`` and ``set_by_id`` are not nullable and therefore must
        receive valid values whenever explicitly supplied.

        This method does not flush or commit.
        """

        if grade_label is not _UNSET:
            target.grade_label = self._normalise_grade_label(
                grade_label,
            )

        if grade_points is not _UNSET:
            target.grade_points = self._normalise_grade_points(
                grade_points,
            )

        if academic_year is not _UNSET:
            target.academic_year = self._normalise_optional_text(
                academic_year,
                field_name="academic_year",
                max_length=50,
            )

        if notes is not _UNSET:
            target.notes = self._normalise_optional_text(
                notes,
                field_name="notes",
            )

        if set_by_id is not _UNSET:
            self._validate_positive_integer(
                set_by_id,
                "set_by_id",
            )

            target.set_by_id = set_by_id

        return target

    async def delete(
        self,
        target: AssessmentTarget,
    ) -> None:
        """
        Mark an assessment target for deletion.

        This method does not flush or commit.
        """

        await self.db.delete(
            target,
        )
