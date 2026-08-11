from __future__ import annotations

from sqlalchemy import exists, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.assessment import Assessment, AssessmentStatus
from app.models.assessment_candidate import AssessmentCandidate
from app.models.assessment_question import AssessmentQuestion
from app.models.mark_scheme import MarkScheme


class AssessmentRepository:
    """
    Repository for school-scoped assessment persistence and lookup.

    This repository never commits or rolls back transactions. Transaction
    ownership remains with the calling service, endpoint, background task,
    import processor, or other application workflow.

    Assessment relationship loading is centralised so callers may choose
    between lightweight internal lookups and fully hydrated assessment
    objects for service/API workflows.
    """

    def __init__(
        self,
        db: AsyncSession,
    ) -> None:
        self.db = db

    # ------------------------------------------------------------------
    # Validation and normalisation
    # ------------------------------------------------------------------

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
    def _normalise_title(
        title: str,
    ) -> str:
        """
        Return a validated and trimmed assessment title.
        """

        if not isinstance(title, str):
            raise ValueError(
                "Assessment title must be a string.",
            )

        normalised_title = title.strip()

        if not normalised_title:
            raise ValueError(
                "Assessment title cannot be blank.",
            )

        if len(normalised_title) > 255:
            raise ValueError(
                "Assessment title cannot exceed 255 characters.",
            )

        return normalised_title

    @staticmethod
    def _normalise_optional_text(
        value: str | None,
        *,
        field_name: str,
        max_length: int | None = None,
    ) -> str | None:
        """
        Return a trimmed optional text value.

        Blank strings are normalised to ``None``.
        """

        if value is None:
            return None

        if not isinstance(value, str):
            raise ValueError(
                f"{field_name} must be a string or None.",
            )

        normalised_value = value.strip()

        if not normalised_value:
            return None

        if max_length is not None and len(normalised_value) > max_length:
            raise ValueError(
                f"{field_name} cannot exceed {max_length} characters.",
            )

        return normalised_value

    @staticmethod
    def _normalise_status(
        value: AssessmentStatus | str,
    ) -> AssessmentStatus:
        """
        Return a valid AssessmentStatus value.
        """

        if isinstance(value, AssessmentStatus):
            return value

        if not isinstance(value, str):
            raise ValueError(
                "Assessment status must be an AssessmentStatus or string.",
            )

        try:
            return AssessmentStatus(
                value.strip(),
            )
        except ValueError as exc:
            raise ValueError(
                f"Invalid assessment status: {value!r}.",
            ) from exc

    @staticmethod
    def _apply_relationship_loading(
        statement,
        *,
        include_relationships: bool,
    ):
        """
        Apply the standard assessment eager-loading configuration.

        When enabled, returned Assessment objects include:

        - school;
        - course;
        - creator;
        - sections;
        - questions;
        - each question's mark scheme;
        - mark-scheme items;
        - assessment candidates;
        - candidate scripts.

        ``populate_existing=True`` is intentional. Assessment workflows may
        modify related records in the same AsyncSession before reloading an
        assessment. Without refreshing existing ORM state, SQLAlchemy's
        identity map can retain a previously loaded relationship collection,
        such as an empty ``assessment.questions`` collection, even though new
        rows have since been persisted.

        Deep response and marking data is intentionally not loaded here.
        Candidate responses, marking decisions and mark-scheme item awards
        may become large datasets and should be loaded through dedicated
        marking repositories/workflows.
        """

        if not include_relationships:
            return statement

        return statement.execution_options(
            populate_existing=True,
        ).options(
            selectinload(
                Assessment.school,
            ),
            selectinload(
                Assessment.course,
            ),
            selectinload(
                Assessment.creator,
            ),
            selectinload(
                Assessment.sections,
            ),
            selectinload(
                Assessment.questions,
            )
            .selectinload(
                AssessmentQuestion.mark_scheme,
            )
            .selectinload(
                MarkScheme.items,
            ),
            selectinload(
                Assessment.candidates,
            ).selectinload(
                AssessmentCandidate.scripts,
            ),
        )

    # ------------------------------------------------------------------
    # Single-record lookup
    # ------------------------------------------------------------------

    async def get_by_id(
        self,
        assessment_id: int,
        *,
        include_relationships: bool = True,
    ) -> Assessment | None:
        """
        Return an assessment by its global identifier.

        Prefer ``get_by_id_and_school`` in school-facing workflows.
        """

        self._validate_positive_integer(
            assessment_id,
            "assessment_id",
        )

        statement = select(
            Assessment,
        ).where(
            Assessment.id == assessment_id,
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
        assessment_id: int,
        school_id: int,
        *,
        include_relationships: bool = True,
    ) -> Assessment | None:
        """
        Return an assessment only when it belongs to the specified school.
        """

        self._validate_positive_integer(
            assessment_id,
            "assessment_id",
        )

        self._validate_positive_integer(
            school_id,
            "school_id",
        )

        statement = select(
            Assessment,
        ).where(
            Assessment.id == assessment_id,
            Assessment.school_id == school_id,
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
    ) -> Assessment | None:
        """
        Return an assessment matching title, course, and school.

        The current Assessment model does not enforce uniqueness for this
        combination, so callers should use this lookup consistently where
        title/course matching is required.
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
            Assessment,
        ).where(
            Assessment.title == normalised_title,
            Assessment.course_id == course_id,
            Assessment.school_id == school_id,
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
    # Collection lookup
    # ------------------------------------------------------------------

    async def list_all(
        self,
        *,
        status: AssessmentStatus | str | None = None,
        include_relationships: bool = True,
    ) -> list[Assessment]:
        """
        Return assessments across all schools.

        Intended primarily for platform-administrator workflows.
        """

        statement = select(
            Assessment,
        )

        if status is not None:
            normalised_status = self._normalise_status(
                status,
            )

            statement = statement.where(
                Assessment.status == normalised_status,
            )

        statement = statement.order_by(
            Assessment.created_at.desc(),
            Assessment.id.desc(),
        )

        statement = self._apply_relationship_loading(
            statement,
            include_relationships=include_relationships,
        )

        result = await self.db.execute(
            statement,
        )

        return list(
            result.scalars().unique().all(),
        )

    async def list_by_school(
        self,
        school_id: int,
        *,
        course_id: int | None = None,
        created_by_id: int | None = None,
        status: AssessmentStatus | str | None = None,
        academic_year: str | None = None,
        term: str | None = None,
        include_relationships: bool = True,
    ) -> list[Assessment]:
        """
        Return assessments belonging to one school.

        Optional filters may restrict results by course, creator, status,
        academic year, or term.
        """

        self._validate_positive_integer(
            school_id,
            "school_id",
        )

        statement = select(
            Assessment,
        ).where(
            Assessment.school_id == school_id,
        )

        if course_id is not None:
            self._validate_positive_integer(
                course_id,
                "course_id",
            )

            statement = statement.where(
                Assessment.course_id == course_id,
            )

        if created_by_id is not None:
            self._validate_positive_integer(
                created_by_id,
                "created_by_id",
            )

            statement = statement.where(
                Assessment.created_by_id == created_by_id,
            )

        if status is not None:
            normalised_status = self._normalise_status(
                status,
            )

            statement = statement.where(
                Assessment.status == normalised_status,
            )

        if academic_year is not None:
            normalised_academic_year = self._normalise_optional_text(
                academic_year,
                field_name="academic_year",
                max_length=50,
            )

            if normalised_academic_year is not None:
                statement = statement.where(
                    Assessment.academic_year == normalised_academic_year,
                )

        if term is not None:
            normalised_term = self._normalise_optional_text(
                term,
                field_name="term",
                max_length=100,
            )

            if normalised_term is not None:
                statement = statement.where(
                    Assessment.term == normalised_term,
                )

        statement = statement.order_by(
            Assessment.created_at.desc(),
            Assessment.id.desc(),
        )

        statement = self._apply_relationship_loading(
            statement,
            include_relationships=include_relationships,
        )

        result = await self.db.execute(
            statement,
        )

        return list(
            result.scalars().unique().all(),
        )

    async def list_by_course(
        self,
        course_id: int,
        *,
        school_id: int | None = None,
        status: AssessmentStatus | str | None = None,
        include_relationships: bool = True,
    ) -> list[Assessment]:
        """
        Return assessments belonging to one course.

        Supplying ``school_id`` is recommended in school-facing workflows.
        """

        self._validate_positive_integer(
            course_id,
            "course_id",
        )

        statement = select(
            Assessment,
        ).where(
            Assessment.course_id == course_id,
        )

        if school_id is not None:
            self._validate_positive_integer(
                school_id,
                "school_id",
            )

            statement = statement.where(
                Assessment.school_id == school_id,
            )

        if status is not None:
            normalised_status = self._normalise_status(
                status,
            )

            statement = statement.where(
                Assessment.status == normalised_status,
            )

        statement = statement.order_by(
            Assessment.created_at.desc(),
            Assessment.id.desc(),
        )

        statement = self._apply_relationship_loading(
            statement,
            include_relationships=include_relationships,
        )

        result = await self.db.execute(
            statement,
        )

        return list(
            result.scalars().unique().all(),
        )

    async def list_by_creator(
        self,
        created_by_id: int,
        *,
        school_id: int | None = None,
        status: AssessmentStatus | str | None = None,
        include_relationships: bool = True,
    ) -> list[Assessment]:
        """
        Return assessments created by one user.
        """

        self._validate_positive_integer(
            created_by_id,
            "created_by_id",
        )

        statement = select(
            Assessment,
        ).where(
            Assessment.created_by_id == created_by_id,
        )

        if school_id is not None:
            self._validate_positive_integer(
                school_id,
                "school_id",
            )

            statement = statement.where(
                Assessment.school_id == school_id,
            )

        if status is not None:
            normalised_status = self._normalise_status(
                status,
            )

            statement = statement.where(
                Assessment.status == normalised_status,
            )

        statement = statement.order_by(
            Assessment.created_at.desc(),
            Assessment.id.desc(),
        )

        statement = self._apply_relationship_loading(
            statement,
            include_relationships=include_relationships,
        )

        result = await self.db.execute(
            statement,
        )

        return list(
            result.scalars().unique().all(),
        )

    # ------------------------------------------------------------------
    # Existence checks
    # ------------------------------------------------------------------

    async def exists(
        self,
        assessment_id: int,
    ) -> bool:
        """
        Return whether an assessment exists by global identifier.
        """

        self._validate_positive_integer(
            assessment_id,
            "assessment_id",
        )

        result = await self.db.execute(
            select(
                exists().where(
                    Assessment.id == assessment_id,
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
        assessment_id: int | None = None,
        title: str | None = None,
        course_id: int | None = None,
        exclude_assessment_id: int | None = None,
    ) -> bool:
        """
        Return whether a matching assessment exists within one school.

        Supported matching strategies:

        - by ``assessment_id``;
        - by ``title``;
        - by ``title`` and ``course_id``.

        ``exclude_assessment_id`` supports update validation.
        """

        self._validate_positive_integer(
            school_id,
            "school_id",
        )

        if assessment_id is None and title is None:
            raise ValueError(
                "Either assessment_id or title must be provided.",
            )

        if assessment_id is not None and title is not None:
            raise ValueError(
                "Provide either assessment_id or title, not both.",
            )

        if course_id is not None and title is None:
            raise ValueError(
                "course_id can only be used with title.",
            )

        if exclude_assessment_id is not None:
            self._validate_positive_integer(
                exclude_assessment_id,
                "exclude_assessment_id",
            )

        conditions = [
            Assessment.school_id == school_id,
        ]

        if assessment_id is not None:
            self._validate_positive_integer(
                assessment_id,
                "assessment_id",
            )

            conditions.append(
                Assessment.id == assessment_id,
            )

        else:
            normalised_title = self._normalise_title(
                title or "",
            )

            conditions.append(
                Assessment.title == normalised_title,
            )

            if course_id is not None:
                self._validate_positive_integer(
                    course_id,
                    "course_id",
                )

                conditions.append(
                    Assessment.course_id == course_id,
                )

        if exclude_assessment_id is not None:
            conditions.append(
                Assessment.id != exclude_assessment_id,
            )

        result = await self.db.execute(
            select(
                exists().where(
                    *conditions,
                ),
            ),
        )

        return bool(
            result.scalar_one(),
        )

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    async def create(
        self,
        assessment: Assessment,
    ) -> Assessment:
        """
        Add and flush a new assessment.

        This method does not commit the transaction.
        """

        assessment.title = self._normalise_title(
            assessment.title,
        )

        assessment.description = self._normalise_optional_text(
            assessment.description,
            field_name="description",
        )

        assessment.assessment_type = self._normalise_optional_text(
            assessment.assessment_type,
            field_name="assessment_type",
            max_length=100,
        )

        assessment.academic_year = self._normalise_optional_text(
            assessment.academic_year,
            field_name="academic_year",
            max_length=50,
        )

        assessment.term = self._normalise_optional_text(
            assessment.term,
            field_name="term",
            max_length=100,
        )

        assessment.status = self._normalise_status(
            assessment.status,
        )

        self._validate_positive_integer(
            assessment.school_id,
            "school_id",
        )

        self._validate_positive_integer(
            assessment.course_id,
            "course_id",
        )

        self._validate_positive_integer(
            assessment.created_by_id,
            "created_by_id",
        )

        self.db.add(
            assessment,
        )

        await self.db.flush()

        await self.db.refresh(
            assessment,
        )

        return assessment

    async def save(
        self,
        assessment: Assessment,
    ) -> Assessment:
        """
        Persist and flush an existing assessment.

        This method does not commit the transaction.
        """

        if assessment.id is None:
            raise ValueError(
                "Cannot save an assessment without an ID.",
            )

        self._validate_positive_integer(
            assessment.id,
            "assessment.id",
        )

        assessment.title = self._normalise_title(
            assessment.title,
        )

        assessment.description = self._normalise_optional_text(
            assessment.description,
            field_name="description",
        )

        assessment.assessment_type = self._normalise_optional_text(
            assessment.assessment_type,
            field_name="assessment_type",
            max_length=100,
        )

        assessment.academic_year = self._normalise_optional_text(
            assessment.academic_year,
            field_name="academic_year",
            max_length=50,
        )

        assessment.term = self._normalise_optional_text(
            assessment.term,
            field_name="term",
            max_length=100,
        )

        assessment.status = self._normalise_status(
            assessment.status,
        )

        self._validate_positive_integer(
            assessment.school_id,
            "school_id",
        )

        self._validate_positive_integer(
            assessment.course_id,
            "course_id",
        )

        self._validate_positive_integer(
            assessment.created_by_id,
            "created_by_id",
        )

        self.db.add(
            assessment,
        )

        await self.db.flush()

        await self.db.refresh(
            assessment,
        )

        return assessment

    async def delete(
        self,
        assessment: Assessment,
    ) -> None:
        """
        Delete and flush an assessment.

        Database and ORM cascade rules remove dependent assessment records.
        """

        if assessment.id is None:
            raise ValueError(
                "Cannot delete an assessment without an ID.",
            )

        self._validate_positive_integer(
            assessment.id,
            "assessment.id",
        )

        await self.db.delete(
            assessment,
        )

        await self.db.flush()
