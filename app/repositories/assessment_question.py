from __future__ import annotations

from decimal import Decimal, InvalidOperation

from sqlalchemy import exists, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import load_only, raiseload, selectinload

from app.models.assessment import Assessment
from app.models.assessment_question import (
    AssessmentQuestion,
    AssessmentQuestionAsset,
    AssessmentQuestionOption,
    AssessmentSection,
)


class AssessmentQuestionRepository:
    """
    Repository for assessment sections and questions.

    School scope is derived through the owning Assessment rather than
    duplicated on section or question records.

    This repository never commits or rolls back transactions. Transaction
    ownership remains with the calling service, endpoint, or workflow.
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
    def _normalise_required_text(
        value: str,
        *,
        field_name: str,
        max_length: int,
    ) -> str:
        """
        Return a validated, trimmed required string.
        """

        if not isinstance(value, str):
            raise ValueError(
                f"{field_name} must be a string.",
            )

        cleaned = value.strip()

        if not cleaned:
            raise ValueError(
                f"{field_name} cannot be blank.",
            )

        if len(cleaned) > max_length:
            raise ValueError(
                f"{field_name} cannot exceed {max_length} characters.",
            )

        return cleaned

    @staticmethod
    def _normalise_optional_text(
        value: str | None,
        *,
        field_name: str,
        max_length: int | None = None,
    ) -> str | None:
        """
        Return a trimmed optional text value.

        Blank strings are normalised to None.
        """

        if value is None:
            return None

        if not isinstance(value, str):
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
    def _normalise_order(
        value: int,
        field_name: str,
    ) -> int:
        """
        Require a positive display/order position.
        """

        if not isinstance(value, int) or isinstance(value, bool) or value < 1:
            raise ValueError(
                f"{field_name} must be a positive integer.",
            )

        return value

    @staticmethod
    def _normalise_maximum_mark(
        value: Decimal | int | float | str,
    ) -> Decimal:
        """
        Return a non-negative Decimal maximum mark.
        """

        if isinstance(value, bool):
            raise ValueError(
                "maximum_mark must be a valid non-negative number.",
            )

        try:
            cleaned = Decimal(
                str(value),
            )
        except (
            InvalidOperation,
            TypeError,
            ValueError,
        ) as exc:
            raise ValueError(
                "maximum_mark must be a valid non-negative number.",
            ) from exc

        if not cleaned.is_finite():
            raise ValueError(
                "maximum_mark must be a finite number.",
            )

        if cleaned < Decimal("0"):
            raise ValueError(
                "maximum_mark cannot be negative.",
            )

        if cleaned > Decimal("999999.99"):
            raise ValueError(
                "maximum_mark cannot exceed 999999.99.",
            )

        return cleaned

    # ------------------------------------------------------------------
    # Relationship loading
    # ------------------------------------------------------------------

    @staticmethod
    def _apply_section_relationship_loading(
        statement,
        *,
        include_relationships: bool,
    ):
        """
        Optionally eager-load an assessment section's questions.
        """

        if not include_relationships:
            return statement

        return statement.execution_options(
            populate_existing=True,
        ).options(
            selectinload(
                AssessmentSection.questions,
            ),
        )

    @staticmethod
    def _apply_question_relationship_loading(
        statement,
        *,
        include_relationships: bool,
    ):
        """
        Optionally eager-load lightweight question relationships.
        """

        if not include_relationships:
            return statement

        return statement.execution_options(
            populate_existing=True,
        ).options(
            selectinload(
                AssessmentQuestion.section,
            ),
            selectinload(
                AssessmentQuestion.parent_question,
            ),
            selectinload(
                AssessmentQuestion.child_questions,
            ),
        )

    # ------------------------------------------------------------------
    # Section lookup
    # ------------------------------------------------------------------

    async def get_section_by_id(
        self,
        section_id: int,
        *,
        include_relationships: bool = True,
    ) -> AssessmentSection | None:
        """
        Return an assessment section by global identifier.
        """

        self._validate_positive_integer(
            section_id,
            "section_id",
        )

        statement = select(
            AssessmentSection,
        ).where(
            AssessmentSection.id == section_id,
        )

        statement = self._apply_section_relationship_loading(
            statement,
            include_relationships=include_relationships,
        )

        result = await self.db.execute(
            statement,
        )

        return result.scalar_one_or_none()

    async def get_section_by_id_and_assessment(
        self,
        *,
        section_id: int,
        assessment_id: int,
        include_relationships: bool = True,
    ) -> AssessmentSection | None:
        """
        Return a section only when it belongs to the assessment.
        """

        self._validate_positive_integer(
            section_id,
            "section_id",
        )
        self._validate_positive_integer(
            assessment_id,
            "assessment_id",
        )

        statement = select(
            AssessmentSection,
        ).where(
            AssessmentSection.id == section_id,
            AssessmentSection.assessment_id == assessment_id,
        )

        statement = self._apply_section_relationship_loading(
            statement,
            include_relationships=include_relationships,
        )

        result = await self.db.execute(
            statement,
        )

        return result.scalar_one_or_none()

    async def get_section_by_id_and_school(
        self,
        *,
        section_id: int,
        school_id: int,
        include_relationships: bool = True,
    ) -> AssessmentSection | None:
        """
        Return a section only when its assessment belongs to the school.
        """

        self._validate_positive_integer(
            section_id,
            "section_id",
        )
        self._validate_positive_integer(
            school_id,
            "school_id",
        )

        statement = (
            select(
                AssessmentSection,
            )
            .join(
                Assessment,
                Assessment.id == AssessmentSection.assessment_id,
            )
            .where(
                AssessmentSection.id == section_id,
                Assessment.school_id == school_id,
            )
        )

        statement = self._apply_section_relationship_loading(
            statement,
            include_relationships=include_relationships,
        )

        result = await self.db.execute(
            statement,
        )

        return result.scalar_one_or_none()

    # ------------------------------------------------------------------
    # Section collections
    # ------------------------------------------------------------------

    async def list_sections_by_assessment(
        self,
        assessment_id: int,
        *,
        include_relationships: bool = True,
    ) -> list[AssessmentSection]:
        """
        Return sections belonging to one assessment in display order.
        """

        self._validate_positive_integer(
            assessment_id,
            "assessment_id",
        )

        statement = (
            select(
                AssessmentSection,
            )
            .where(
                AssessmentSection.assessment_id == assessment_id,
            )
            .order_by(
                AssessmentSection.order.asc(),
                AssessmentSection.id.asc(),
            )
        )

        statement = self._apply_section_relationship_loading(
            statement,
            include_relationships=include_relationships,
        )

        result = await self.db.execute(
            statement,
        )

        return list(
            result.scalars().unique().all(),
        )

    async def list_sections_by_assessment_and_school(
        self,
        *,
        assessment_id: int,
        school_id: int,
        include_relationships: bool = True,
    ) -> list[AssessmentSection]:
        """
        Return assessment sections within one school.
        """

        self._validate_positive_integer(
            assessment_id,
            "assessment_id",
        )
        self._validate_positive_integer(
            school_id,
            "school_id",
        )

        statement = (
            select(
                AssessmentSection,
            )
            .join(
                Assessment,
                Assessment.id == AssessmentSection.assessment_id,
            )
            .where(
                AssessmentSection.assessment_id == assessment_id,
                Assessment.school_id == school_id,
            )
            .order_by(
                AssessmentSection.order.asc(),
                AssessmentSection.id.asc(),
            )
        )

        statement = self._apply_section_relationship_loading(
            statement,
            include_relationships=include_relationships,
        )

        result = await self.db.execute(
            statement,
        )

        return list(
            result.scalars().unique().all(),
        )

    async def section_order_exists(
        self,
        *,
        assessment_id: int,
        order: int,
        exclude_section_id: int | None = None,
    ) -> bool:
        """
        Return whether an assessment already uses the section order.
        """

        self._validate_positive_integer(
            assessment_id,
            "assessment_id",
        )

        clean_order = self._normalise_order(
            order,
            "order",
        )

        conditions = [
            AssessmentSection.assessment_id == assessment_id,
            AssessmentSection.order == clean_order,
        ]

        if exclude_section_id is not None:
            self._validate_positive_integer(
                exclude_section_id,
                "exclude_section_id",
            )

            conditions.append(
                AssessmentSection.id != exclude_section_id,
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
    # Section persistence
    # ------------------------------------------------------------------

    async def create_section(
        self,
        section: AssessmentSection,
    ) -> AssessmentSection:
        """
        Add and flush a new assessment section.
        """

        self._validate_positive_integer(
            section.assessment_id,
            "assessment_id",
        )

        section.title = self._normalise_required_text(
            section.title,
            field_name="title",
            max_length=255,
        )

        section.description = self._normalise_optional_text(
            section.description,
            field_name="description",
        )

        section.order = self._normalise_order(
            section.order,
            "order",
        )

        if not isinstance(
            section.is_optional,
            bool,
        ):
            raise ValueError(
                "is_optional must be a boolean.",
            )

        self.db.add(
            section,
        )

        await self.db.flush()
        await self.db.refresh(
            section,
        )

        return section

    async def save_section(
        self,
        section: AssessmentSection,
    ) -> AssessmentSection:
        """
        Persist and flush an existing assessment section.
        """

        if section.id is None:
            raise ValueError(
                "Cannot save an assessment section without an ID.",
            )

        self._validate_positive_integer(
            section.id,
            "section.id",
        )
        self._validate_positive_integer(
            section.assessment_id,
            "assessment_id",
        )

        section.title = self._normalise_required_text(
            section.title,
            field_name="title",
            max_length=255,
        )

        section.description = self._normalise_optional_text(
            section.description,
            field_name="description",
        )

        section.order = self._normalise_order(
            section.order,
            "order",
        )

        if not isinstance(
            section.is_optional,
            bool,
        ):
            raise ValueError(
                "is_optional must be a boolean.",
            )

        self.db.add(
            section,
        )

        await self.db.flush()
        await self.db.refresh(
            section,
        )

        return section

    async def delete_section(
        self,
        section: AssessmentSection,
    ) -> None:
        """
        Delete and flush a section.

        Database foreign-key behaviour leaves its questions unsectioned.
        """

        if section.id is None:
            raise ValueError(
                "Cannot delete an assessment section without an ID.",
            )

        self._validate_positive_integer(
            section.id,
            "section.id",
        )

        await self.db.delete(
            section,
        )

        await self.db.flush()

    # ------------------------------------------------------------------
    # Question lookup
    # ------------------------------------------------------------------

    async def get_question_by_id(
        self,
        question_id: int,
        *,
        include_relationships: bool = True,
    ) -> AssessmentQuestion | None:
        """
        Return an assessment question by global identifier.
        """

        self._validate_positive_integer(
            question_id,
            "question_id",
        )

        statement = select(
            AssessmentQuestion,
        ).where(
            AssessmentQuestion.id == question_id,
        )

        statement = self._apply_question_relationship_loading(
            statement,
            include_relationships=include_relationships,
        )

        result = await self.db.execute(
            statement,
        )

        return result.scalar_one_or_none()

    async def get_question_by_id_and_assessment(
        self,
        *,
        question_id: int,
        assessment_id: int,
        include_relationships: bool = True,
    ) -> AssessmentQuestion | None:
        """
        Return a question only when it belongs to the assessment.
        """

        self._validate_positive_integer(
            question_id,
            "question_id",
        )
        self._validate_positive_integer(
            assessment_id,
            "assessment_id",
        )

        statement = select(
            AssessmentQuestion,
        ).where(
            AssessmentQuestion.id == question_id,
            AssessmentQuestion.assessment_id == assessment_id,
        )

        statement = self._apply_question_relationship_loading(
            statement,
            include_relationships=include_relationships,
        )

        result = await self.db.execute(
            statement,
        )

        return result.scalar_one_or_none()

    async def get_question_by_id_and_school(
        self,
        *,
        question_id: int,
        school_id: int,
        include_relationships: bool = True,
    ) -> AssessmentQuestion | None:
        """
        Return a question only when its assessment belongs to the school.
        """

        self._validate_positive_integer(
            question_id,
            "question_id",
        )
        self._validate_positive_integer(
            school_id,
            "school_id",
        )

        statement = (
            select(
                AssessmentQuestion,
            )
            .join(
                Assessment,
                Assessment.id == AssessmentQuestion.assessment_id,
            )
            .where(
                AssessmentQuestion.id == question_id,
                Assessment.school_id == school_id,
            )
        )

        statement = self._apply_question_relationship_loading(
            statement,
            include_relationships=include_relationships,
        )

        result = await self.db.execute(
            statement,
        )

        return result.scalar_one_or_none()

    async def get_candidate_visible_question_by_assessment_and_school(
        self,
        *,
        question_id: int,
        assessment_id: int,
        school_id: int,
    ) -> AssessmentQuestion | None:
        """
        Return one learner-safe question within an assessment and school.

        This is the single-question counterpart to
        ``list_candidate_visible_questions_by_assessment_and_school`` and is
        intended for high-frequency candidate workflows such as autosave.

        It deliberately loads only learner-visible question fields, including
        the candidate-safe interaction configuration, safe option fields, and
        candidate-visible asset metadata. Mark schemes, responses,
        correctness/feedback metadata, storage paths, provenance and unrelated
        relationships remain unavailable.
        """

        self._validate_positive_integer(
            question_id,
            "question_id",
        )
        self._validate_positive_integer(
            assessment_id,
            "assessment_id",
        )
        self._validate_positive_integer(
            school_id,
            "school_id",
        )

        statement = (
            select(
                AssessmentQuestion,
            )
            .join(
                Assessment,
                Assessment.id == AssessmentQuestion.assessment_id,
            )
            .where(
                AssessmentQuestion.id == question_id,
                AssessmentQuestion.assessment_id == assessment_id,
                Assessment.school_id == school_id,
            )
            .execution_options(
                populate_existing=True,
            )
            .options(
                raiseload("*"),
                load_only(
                    AssessmentQuestion.id,
                    AssessmentQuestion.assessment_id,
                    AssessmentQuestion.section_id,
                    AssessmentQuestion.parent_question_id,
                    AssessmentQuestion.question_number,
                    AssessmentQuestion.title,
                    AssessmentQuestion.prompt,
                    AssessmentQuestion.question_type,
                    AssessmentQuestion.interaction_config,
                    AssessmentQuestion.maximum_mark,
                    AssessmentQuestion.order,
                    AssessmentQuestion.is_markable,
                    AssessmentQuestion.source_page_number,
                ),
                selectinload(
                    AssessmentQuestion.section,
                ).load_only(
                    AssessmentSection.id,
                    AssessmentSection.assessment_id,
                    AssessmentSection.title,
                    AssessmentSection.description,
                    AssessmentSection.order,
                    AssessmentSection.is_optional,
                ),
                selectinload(
                    AssessmentQuestion.options,
                ).load_only(
                    AssessmentQuestionOption.id,
                    AssessmentQuestionOption.question_id,
                    AssessmentQuestionOption.text,
                    AssessmentQuestionOption.order,
                ),
                selectinload(
                    AssessmentQuestion.assets.and_(
                        AssessmentQuestionAsset.candidate_visible.is_(True),
                    ),
                ).load_only(
                    AssessmentQuestionAsset.id,
                    AssessmentQuestionAsset.question_id,
                    AssessmentQuestionAsset.asset_type,
                    AssessmentQuestionAsset.alt_text,
                    AssessmentQuestionAsset.caption,
                    AssessmentQuestionAsset.order,
                    AssessmentQuestionAsset.candidate_visible,
                ),
            )
        )

        result = await self.db.execute(
            statement,
        )

        return result.scalar_one_or_none()

    async def get_candidate_visible_asset_by_question_assessment_and_school(
        self,
        *,
        asset_id: int,
        question_id: int,
        assessment_id: int,
        school_id: int,
    ) -> AssessmentQuestionAsset | None:
        """
        Return one candidate-visible asset within a question, assessment and school.

        This lookup exists specifically for authorised candidate asset delivery.

        Unlike the learner-facing question loaders, it deliberately includes the
        server-side storage fields required to resolve and serve the file. Those
        fields remain internal to the service/endpoint layer and must never be
        serialised into candidate JSON responses.

        The query is scoped simultaneously by:

        - asset id;
        - question id;
        - assessment id;
        - school id;
        - candidate_visible=True.

        ORM relationships remain unavailable through ``raiseload("*")``.
        """

        self._validate_positive_integer(
            asset_id,
            "asset_id",
        )
        self._validate_positive_integer(
            question_id,
            "question_id",
        )
        self._validate_positive_integer(
            assessment_id,
            "assessment_id",
        )
        self._validate_positive_integer(
            school_id,
            "school_id",
        )

        statement = (
            select(
                AssessmentQuestionAsset,
            )
            .join(
                AssessmentQuestion,
                AssessmentQuestion.id == AssessmentQuestionAsset.question_id,
            )
            .join(
                Assessment,
                Assessment.id == AssessmentQuestion.assessment_id,
            )
            .where(
                AssessmentQuestionAsset.id == asset_id,
                AssessmentQuestionAsset.question_id == question_id,
                AssessmentQuestion.id == question_id,
                AssessmentQuestion.assessment_id == assessment_id,
                Assessment.school_id == school_id,
                AssessmentQuestionAsset.candidate_visible.is_(True),
            )
            .execution_options(
                populate_existing=True,
            )
            .options(
                raiseload("*"),
                load_only(
                    AssessmentQuestionAsset.id,
                    AssessmentQuestionAsset.question_id,
                    AssessmentQuestionAsset.asset_type,
                    AssessmentQuestionAsset.storage_path,
                    AssessmentQuestionAsset.original_filename,
                    AssessmentQuestionAsset.mime_type,
                    AssessmentQuestionAsset.file_size_bytes,
                    AssessmentQuestionAsset.alt_text,
                    AssessmentQuestionAsset.caption,
                    AssessmentQuestionAsset.order,
                    AssessmentQuestionAsset.candidate_visible,
                    AssessmentQuestionAsset.source_document_id,
                ),
            )
        )

        result = await self.db.execute(
            statement,
        )

        return result.scalar_one_or_none()

    async def list_candidate_visible_assets_by_assessment_and_school(
        self,
        *,
        assessment_id: int,
        school_id: int,
    ) -> list[AssessmentQuestionAsset]:
        """
        Return server-side metadata for every candidate-visible asset in one
        assessment and school.

        This bulk lookup exists for trusted server workflows such as immutable
        attempt snapshot creation. Unlike learner-facing question loaders, it
        deliberately includes storage metadata required to identify and verify
        the underlying files.

        Storage paths and related internal fields returned here must never be
        serialised directly into candidate-facing API responses.

        ORM relationships remain unavailable through ``raiseload("*")``.
        """

        self._validate_positive_integer(
            assessment_id,
            "assessment_id",
        )
        self._validate_positive_integer(
            school_id,
            "school_id",
        )

        statement = (
            select(
                AssessmentQuestionAsset,
            )
            .join(
                AssessmentQuestion,
                AssessmentQuestion.id == AssessmentQuestionAsset.question_id,
            )
            .join(
                Assessment,
                Assessment.id == AssessmentQuestion.assessment_id,
            )
            .where(
                AssessmentQuestion.assessment_id == assessment_id,
                Assessment.school_id == school_id,
                AssessmentQuestionAsset.candidate_visible.is_(True),
            )
            .order_by(
                AssessmentQuestionAsset.question_id.asc(),
                AssessmentQuestionAsset.order.asc(),
                AssessmentQuestionAsset.id.asc(),
            )
            .options(
                raiseload("*"),
                load_only(
                    AssessmentQuestionAsset.id,
                    AssessmentQuestionAsset.question_id,
                    AssessmentQuestionAsset.asset_type,
                    AssessmentQuestionAsset.storage_path,
                    AssessmentQuestionAsset.original_filename,
                    AssessmentQuestionAsset.mime_type,
                    AssessmentQuestionAsset.file_size_bytes,
                    AssessmentQuestionAsset.alt_text,
                    AssessmentQuestionAsset.caption,
                    AssessmentQuestionAsset.order,
                    AssessmentQuestionAsset.candidate_visible,
                ),
            )
        )

        result = await self.db.execute(
            statement,
        )

        return list(
            result.scalars().all(),
        )

    async def list_candidate_visible_questions_by_assessment_and_school(
        self,
        *,
        assessment_id: int,
        school_id: int,
    ) -> list[AssessmentQuestion]:
        """
        Return learner-safe questions for one assessment within one school.

        This lookup is deliberately separate from ordinary staff question
        retrieval. It applies a restrictive loader policy so candidate-facing
        workflows do not hydrate mark schemes, responses, source documents, or
        unrelated ORM relationships.

        Loaded data is limited to:

        - the canonical question fields required by the learner UI, including
          the candidate-safe interaction configuration;
        - the owning section;
        - structured answer options, but only their learner-safe fields;
        - candidate-visible question assets, but only learner-safe metadata.

        Correct-option flags, option feedback, asset storage paths, extraction
        provenance, mark schemes, responses, and other relationships are not
        loaded by this method.
        """

        self._validate_positive_integer(
            assessment_id,
            "assessment_id",
        )
        self._validate_positive_integer(
            school_id,
            "school_id",
        )

        statement = (
            select(
                AssessmentQuestion,
            )
            .join(
                Assessment,
                Assessment.id == AssessmentQuestion.assessment_id,
            )
            .where(
                AssessmentQuestion.assessment_id == assessment_id,
                Assessment.school_id == school_id,
            )
            .order_by(
                AssessmentQuestion.order.asc(),
                AssessmentQuestion.id.asc(),
            )
            .execution_options(
                populate_existing=True,
            )
            .options(
                raiseload("*"),
                load_only(
                    AssessmentQuestion.id,
                    AssessmentQuestion.assessment_id,
                    AssessmentQuestion.section_id,
                    AssessmentQuestion.parent_question_id,
                    AssessmentQuestion.question_number,
                    AssessmentQuestion.title,
                    AssessmentQuestion.prompt,
                    AssessmentQuestion.question_type,
                    AssessmentQuestion.interaction_config,
                    AssessmentQuestion.maximum_mark,
                    AssessmentQuestion.order,
                    AssessmentQuestion.is_markable,
                    AssessmentQuestion.source_page_number,
                ),
                selectinload(
                    AssessmentQuestion.section,
                ).load_only(
                    AssessmentSection.id,
                    AssessmentSection.assessment_id,
                    AssessmentSection.title,
                    AssessmentSection.description,
                    AssessmentSection.order,
                    AssessmentSection.is_optional,
                ),
                selectinload(
                    AssessmentQuestion.options,
                ).load_only(
                    AssessmentQuestionOption.id,
                    AssessmentQuestionOption.question_id,
                    AssessmentQuestionOption.text,
                    AssessmentQuestionOption.order,
                ),
                selectinload(
                    AssessmentQuestion.assets.and_(
                        AssessmentQuestionAsset.candidate_visible.is_(True),
                    ),
                ).load_only(
                    AssessmentQuestionAsset.id,
                    AssessmentQuestionAsset.question_id,
                    AssessmentQuestionAsset.asset_type,
                    AssessmentQuestionAsset.alt_text,
                    AssessmentQuestionAsset.caption,
                    AssessmentQuestionAsset.order,
                    AssessmentQuestionAsset.candidate_visible,
                ),
            )
        )

        result = await self.db.execute(
            statement,
        )

        return list(
            result.scalars().unique().all(),
        )

    # ------------------------------------------------------------------
    # Question collections
    # ------------------------------------------------------------------

    async def list_questions_by_assessment(
        self,
        assessment_id: int,
        *,
        include_relationships: bool = True,
    ) -> list[AssessmentQuestion]:
        """
        Return questions belonging to one assessment in display order.
        """

        self._validate_positive_integer(
            assessment_id,
            "assessment_id",
        )

        statement = (
            select(
                AssessmentQuestion,
            )
            .where(
                AssessmentQuestion.assessment_id == assessment_id,
            )
            .order_by(
                AssessmentQuestion.order.asc(),
                AssessmentQuestion.id.asc(),
            )
        )

        statement = self._apply_question_relationship_loading(
            statement,
            include_relationships=include_relationships,
        )

        result = await self.db.execute(
            statement,
        )

        return list(
            result.scalars().unique().all(),
        )

    async def list_questions_by_assessment_and_school(
        self,
        *,
        assessment_id: int,
        school_id: int,
        include_relationships: bool = True,
    ) -> list[AssessmentQuestion]:
        """
        Return assessment questions within one school.
        """

        self._validate_positive_integer(
            assessment_id,
            "assessment_id",
        )
        self._validate_positive_integer(
            school_id,
            "school_id",
        )

        statement = (
            select(
                AssessmentQuestion,
            )
            .join(
                Assessment,
                Assessment.id == AssessmentQuestion.assessment_id,
            )
            .where(
                AssessmentQuestion.assessment_id == assessment_id,
                Assessment.school_id == school_id,
            )
            .order_by(
                AssessmentQuestion.order.asc(),
                AssessmentQuestion.id.asc(),
            )
        )

        statement = self._apply_question_relationship_loading(
            statement,
            include_relationships=include_relationships,
        )

        result = await self.db.execute(
            statement,
        )

        return list(
            result.scalars().unique().all(),
        )

    async def question_number_exists(
        self,
        *,
        assessment_id: int,
        question_number: str,
        exclude_question_id: int | None = None,
    ) -> bool:
        """
        Return whether a question number already exists in an assessment.
        """

        self._validate_positive_integer(
            assessment_id,
            "assessment_id",
        )

        clean_number = self._normalise_required_text(
            question_number,
            field_name="question_number",
            max_length=50,
        )

        conditions = [
            AssessmentQuestion.assessment_id == assessment_id,
            AssessmentQuestion.question_number == clean_number,
        ]

        if exclude_question_id is not None:
            self._validate_positive_integer(
                exclude_question_id,
                "exclude_question_id",
            )

            conditions.append(
                AssessmentQuestion.id != exclude_question_id,
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
    # Question persistence
    # ------------------------------------------------------------------

    async def create_question(
        self,
        question: AssessmentQuestion,
    ) -> AssessmentQuestion:
        """
        Add and flush a new assessment question.
        """

        self._validate_question(
            question,
        )

        self.db.add(
            question,
        )

        await self.db.flush()
        await self.db.refresh(
            question,
        )

        return question

    async def save_question(
        self,
        question: AssessmentQuestion,
    ) -> AssessmentQuestion:
        """
        Persist and flush an existing assessment question.
        """

        if question.id is None:
            raise ValueError(
                "Cannot save an assessment question without an ID.",
            )

        self._validate_positive_integer(
            question.id,
            "question.id",
        )

        self._validate_question(
            question,
        )

        self.db.add(
            question,
        )

        await self.db.flush()
        await self.db.refresh(
            question,
        )

        return question

    async def delete_question(
        self,
        question: AssessmentQuestion,
    ) -> None:
        """
        Delete and flush a question.

        ORM/database cascade behaviour removes subordinate child questions.
        """

        if question.id is None:
            raise ValueError(
                "Cannot delete an assessment question without an ID.",
            )

        self._validate_positive_integer(
            question.id,
            "question.id",
        )

        await self.db.delete(
            question,
        )

        await self.db.flush()

    def _validate_question(
        self,
        question: AssessmentQuestion,
    ) -> None:
        """
        Validate and normalise a question before persistence.
        """

        self._validate_positive_integer(
            question.assessment_id,
            "assessment_id",
        )

        if question.section_id is not None:
            self._validate_positive_integer(
                question.section_id,
                "section_id",
            )

        if question.parent_question_id is not None:
            self._validate_positive_integer(
                question.parent_question_id,
                "parent_question_id",
            )

        question.question_number = self._normalise_required_text(
            question.question_number,
            field_name="question_number",
            max_length=50,
        )

        question.title = self._normalise_optional_text(
            question.title,
            field_name="title",
            max_length=255,
        )

        question.prompt = self._normalise_optional_text(
            question.prompt,
            field_name="prompt",
        )

        question.maximum_mark = self._normalise_maximum_mark(
            question.maximum_mark,
        )

        question.order = self._normalise_order(
            question.order,
            "order",
        )

        if not isinstance(
            question.is_markable,
            bool,
        ):
            raise ValueError(
                "is_markable must be a boolean.",
            )


