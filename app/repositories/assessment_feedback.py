from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.assessment_feedback import (
    AssessmentFeedback,
    AssessmentFeedbackStatus,
    AssessmentQuestionFeedback,
)

_UNSET = object()


class AssessmentFeedbackRepository:
    """
    Repository for structured assessment feedback persistence.

    This repository manages both:

    - overall script-level feedback;
    - individual response/question feedback.

    All school-facing lookups may be explicitly school-scoped.

    Transaction ownership remains outside the repository. Methods therefore
    do not commit or roll back database transactions.
    """

    def __init__(
        self,
        db: AsyncSession,
    ) -> None:
        self.db = db

    # ------------------------------------------------------------------
    # Validation helpers
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
    ) -> str | None:
        """
        Trim optional text and convert blank strings to None.
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

        return cleaned

    @staticmethod
    def _normalise_bool(
        value: bool,
        *,
        field_name: str,
    ) -> bool:
        """
        Validate a strict boolean value.
        """

        if not isinstance(
            value,
            bool,
        ):
            raise ValueError(
                f"{field_name} must be a boolean.",
            )

        return value

    @staticmethod
    def _normalise_status(
        value: AssessmentFeedbackStatus | str,
    ) -> AssessmentFeedbackStatus:
        """
        Return a validated assessment feedback status.
        """

        if isinstance(
            value,
            AssessmentFeedbackStatus,
        ):
            return value

        if not isinstance(
            value,
            str,
        ):
            raise ValueError(
                "status must be a valid assessment feedback status.",
            )

        cleaned = value.strip().lower()

        try:
            return AssessmentFeedbackStatus(
                cleaned,
            )
        except ValueError as exc:
            raise ValueError(
                "status must be one of: draft, finalised, archived.",
            ) from exc

    # ------------------------------------------------------------------
    # Overall feedback relationship loading
    # ------------------------------------------------------------------

    @staticmethod
    def _apply_feedback_relationship_loading(
        statement,
        *,
        include_relationships: bool,
    ):
        """
        Apply eager loading for overall feedback.
        """

        if not include_relationships:
            return statement

        return statement.options(
            selectinload(
                AssessmentFeedback.school,
            ),
            selectinload(
                AssessmentFeedback.script,
            ),
            selectinload(
                AssessmentFeedback.created_by,
            ),
            selectinload(
                AssessmentFeedback.updated_by,
            ),
            selectinload(
                AssessmentFeedback.finalised_by,
            ),
        )

    # ------------------------------------------------------------------
    # Question feedback relationship loading
    # ------------------------------------------------------------------

    @staticmethod
    def _apply_question_relationship_loading(
        statement,
        *,
        include_relationships: bool,
    ):
        """
        Apply eager loading for response/question feedback.
        """

        if not include_relationships:
            return statement

        return statement.options(
            selectinload(
                AssessmentQuestionFeedback.school,
            ),
            selectinload(
                AssessmentQuestionFeedback.response,
            ),
            selectinload(
                AssessmentQuestionFeedback.created_by,
            ),
            selectinload(
                AssessmentQuestionFeedback.updated_by,
            ),
        )

    # ------------------------------------------------------------------
    # Overall feedback lookup
    # ------------------------------------------------------------------

    async def get_feedback_by_id(
        self,
        feedback_id: int,
        *,
        include_relationships: bool = True,
    ) -> AssessmentFeedback | None:
        """
        Return overall assessment feedback by identifier.
        """

        self._validate_positive_integer(
            feedback_id,
            "feedback_id",
        )

        statement = select(
            AssessmentFeedback,
        ).where(
            AssessmentFeedback.id == feedback_id,
        )

        statement = self._apply_feedback_relationship_loading(
            statement,
            include_relationships=include_relationships,
        )

        result = await self.db.execute(
            statement,
        )

        return result.scalar_one_or_none()

    async def get_feedback_by_id_and_school(
        self,
        feedback_id: int,
        school_id: int,
        *,
        include_relationships: bool = True,
    ) -> AssessmentFeedback | None:
        """
        Return overall feedback only when it belongs to the supplied school.
        """

        self._validate_positive_integer(
            feedback_id,
            "feedback_id",
        )

        self._validate_positive_integer(
            school_id,
            "school_id",
        )

        statement = select(
            AssessmentFeedback,
        ).where(
            AssessmentFeedback.id == feedback_id,
            AssessmentFeedback.school_id == school_id,
        )

        statement = self._apply_feedback_relationship_loading(
            statement,
            include_relationships=include_relationships,
        )

        result = await self.db.execute(
            statement,
        )

        return result.scalar_one_or_none()

    async def get_feedback_by_script(
        self,
        script_id: int,
        *,
        school_id: int | None = None,
        include_relationships: bool = True,
    ) -> AssessmentFeedback | None:
        """
        Return the overall feedback record for one script.
        """

        self._validate_positive_integer(
            script_id,
            "script_id",
        )

        if school_id is not None:
            self._validate_positive_integer(
                school_id,
                "school_id",
            )

        statement = select(
            AssessmentFeedback,
        ).where(
            AssessmentFeedback.script_id == script_id,
        )

        if school_id is not None:
            statement = statement.where(
                AssessmentFeedback.school_id == school_id,
            )

        statement = self._apply_feedback_relationship_loading(
            statement,
            include_relationships=include_relationships,
        )

        result = await self.db.execute(
            statement,
        )

        return result.scalar_one_or_none()

    async def list_feedback_by_school(
        self,
        school_id: int,
        *,
        status: AssessmentFeedbackStatus | str | None = None,
        created_by_id: int | None = None,
        include_with_result: bool | None = None,
        include_relationships: bool = True,
    ) -> list[AssessmentFeedback]:
        """
        Return overall feedback records for one school.
        """

        self._validate_positive_integer(
            school_id,
            "school_id",
        )

        if created_by_id is not None:
            self._validate_positive_integer(
                created_by_id,
                "created_by_id",
            )

        clean_status = (
            self._normalise_status(
                status,
            )
            if status is not None
            else None
        )

        if include_with_result is not None:
            self._normalise_bool(
                include_with_result,
                field_name="include_with_result",
            )

        statement = select(
            AssessmentFeedback,
        ).where(
            AssessmentFeedback.school_id == school_id,
        )

        if clean_status is not None:
            statement = statement.where(
                AssessmentFeedback.status == clean_status,
            )

        if created_by_id is not None:
            statement = statement.where(
                AssessmentFeedback.created_by_id == created_by_id,
            )

        if include_with_result is not None:
            statement = statement.where(
                AssessmentFeedback.include_with_result == include_with_result,
            )

        statement = statement.order_by(
            AssessmentFeedback.updated_at.desc(),
            AssessmentFeedback.id.desc(),
        )

        statement = self._apply_feedback_relationship_loading(
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
    # Overall feedback persistence
    # ------------------------------------------------------------------

    async def create_feedback(
        self,
        *,
        school_id: int,
        script_id: int,
        created_by_id: int,
        overall_comment: str | None = None,
        strengths: str | None = None,
        areas_for_improvement: str | None = None,
        next_steps: str | None = None,
        include_with_result: bool = True,
        status: AssessmentFeedbackStatus | str = (AssessmentFeedbackStatus.DRAFT),
    ) -> AssessmentFeedback:
        """
        Add an overall feedback record to the session.

        This method does not flush or commit.
        """

        self._validate_positive_integer(
            school_id,
            "school_id",
        )

        self._validate_positive_integer(
            script_id,
            "script_id",
        )

        self._validate_positive_integer(
            created_by_id,
            "created_by_id",
        )

        clean_status = self._normalise_status(
            status,
        )

        clean_include_with_result = self._normalise_bool(
            include_with_result,
            field_name="include_with_result",
        )

        feedback = AssessmentFeedback(
            school_id=school_id,
            script_id=script_id,
            overall_comment=self._normalise_optional_text(
                overall_comment,
                field_name="overall_comment",
            ),
            strengths=self._normalise_optional_text(
                strengths,
                field_name="strengths",
            ),
            areas_for_improvement=self._normalise_optional_text(
                areas_for_improvement,
                field_name="areas_for_improvement",
            ),
            next_steps=self._normalise_optional_text(
                next_steps,
                field_name="next_steps",
            ),
            status=clean_status,
            include_with_result=clean_include_with_result,
            created_by_id=created_by_id,
        )

        self.db.add(
            feedback,
        )

        return feedback

    async def update_feedback(
        self,
        feedback: AssessmentFeedback,
        *,
        overall_comment: str | None | object = _UNSET,
        strengths: str | None | object = _UNSET,
        areas_for_improvement: str | None | object = _UNSET,
        next_steps: str | None | object = _UNSET,
        include_with_result: bool | object = _UNSET,
        status: AssessmentFeedbackStatus | str | object = _UNSET,
        updated_by_id: int | None | object = _UNSET,
        finalised_at: Any = _UNSET,
        finalised_by_id: int | None | object = _UNSET,
    ) -> AssessmentFeedback:
        """
        Update mutable overall feedback fields.

        `_UNSET` means leave unchanged.

        Nullable fields may be explicitly cleared with None.

        This method does not flush or commit.
        """

        if overall_comment is not _UNSET:
            feedback.overall_comment = self._normalise_optional_text(
                overall_comment,
                field_name="overall_comment",
            )

        if strengths is not _UNSET:
            feedback.strengths = self._normalise_optional_text(
                strengths,
                field_name="strengths",
            )

        if areas_for_improvement is not _UNSET:
            feedback.areas_for_improvement = self._normalise_optional_text(
                areas_for_improvement,
                field_name="areas_for_improvement",
            )

        if next_steps is not _UNSET:
            feedback.next_steps = self._normalise_optional_text(
                next_steps,
                field_name="next_steps",
            )

        if include_with_result is not _UNSET:
            feedback.include_with_result = self._normalise_bool(
                include_with_result,
                field_name="include_with_result",
            )

        if status is not _UNSET:
            feedback.status = self._normalise_status(
                status,
            )

        if updated_by_id is not _UNSET:
            if updated_by_id is not None:
                self._validate_positive_integer(
                    updated_by_id,
                    "updated_by_id",
                )

            feedback.updated_by_id = updated_by_id

        if finalised_at is not _UNSET:
            feedback.finalised_at = finalised_at

        if finalised_by_id is not _UNSET:
            if finalised_by_id is not None:
                self._validate_positive_integer(
                    finalised_by_id,
                    "finalised_by_id",
                )

            feedback.finalised_by_id = finalised_by_id

        return feedback

    async def delete_feedback(
        self,
        feedback: AssessmentFeedback,
    ) -> None:
        """
        Mark overall feedback for deletion.

        This method does not commit.
        """

        await self.db.delete(
            feedback,
        )

    # ------------------------------------------------------------------
    # Question feedback lookup
    # ------------------------------------------------------------------

    async def get_question_feedback_by_id(
        self,
        question_feedback_id: int,
        *,
        include_relationships: bool = True,
    ) -> AssessmentQuestionFeedback | None:
        """
        Return question feedback by identifier.
        """

        self._validate_positive_integer(
            question_feedback_id,
            "question_feedback_id",
        )

        statement = select(
            AssessmentQuestionFeedback,
        ).where(
            AssessmentQuestionFeedback.id == question_feedback_id,
        )

        statement = self._apply_question_relationship_loading(
            statement,
            include_relationships=include_relationships,
        )

        result = await self.db.execute(
            statement,
        )

        return result.scalar_one_or_none()

    async def get_question_feedback_by_id_and_school(
        self,
        question_feedback_id: int,
        school_id: int,
        *,
        include_relationships: bool = True,
    ) -> AssessmentQuestionFeedback | None:
        """
        Return question feedback only when it belongs to the supplied school.
        """

        self._validate_positive_integer(
            question_feedback_id,
            "question_feedback_id",
        )

        self._validate_positive_integer(
            school_id,
            "school_id",
        )

        statement = select(
            AssessmentQuestionFeedback,
        ).where(
            AssessmentQuestionFeedback.id == question_feedback_id,
            AssessmentQuestionFeedback.school_id == school_id,
        )

        statement = self._apply_question_relationship_loading(
            statement,
            include_relationships=include_relationships,
        )

        result = await self.db.execute(
            statement,
        )

        return result.scalar_one_or_none()

    async def get_question_feedback_by_response(
        self,
        response_id: int,
        *,
        school_id: int | None = None,
        include_relationships: bool = True,
    ) -> AssessmentQuestionFeedback | None:
        """
        Return the question-feedback record for one response.
        """

        self._validate_positive_integer(
            response_id,
            "response_id",
        )

        if school_id is not None:
            self._validate_positive_integer(
                school_id,
                "school_id",
            )

        statement = select(
            AssessmentQuestionFeedback,
        ).where(
            AssessmentQuestionFeedback.response_id == response_id,
        )

        if school_id is not None:
            statement = statement.where(
                AssessmentQuestionFeedback.school_id == school_id,
            )

        statement = self._apply_question_relationship_loading(
            statement,
            include_relationships=include_relationships,
        )

        result = await self.db.execute(
            statement,
        )

        return result.scalar_one_or_none()

    async def list_question_feedback_by_school(
        self,
        school_id: int,
        *,
        created_by_id: int | None = None,
        include_with_result: bool | None = None,
        include_relationships: bool = True,
    ) -> list[AssessmentQuestionFeedback]:
        """
        Return question feedback records for one school.
        """

        self._validate_positive_integer(
            school_id,
            "school_id",
        )

        if created_by_id is not None:
            self._validate_positive_integer(
                created_by_id,
                "created_by_id",
            )

        if include_with_result is not None:
            self._normalise_bool(
                include_with_result,
                field_name="include_with_result",
            )

        statement = select(
            AssessmentQuestionFeedback,
        ).where(
            AssessmentQuestionFeedback.school_id == school_id,
        )

        if created_by_id is not None:
            statement = statement.where(
                AssessmentQuestionFeedback.created_by_id == created_by_id,
            )

        if include_with_result is not None:
            statement = statement.where(
                AssessmentQuestionFeedback.include_with_result == include_with_result,
            )

        statement = statement.order_by(
            AssessmentQuestionFeedback.updated_at.desc(),
            AssessmentQuestionFeedback.id.desc(),
        )

        statement = self._apply_question_relationship_loading(
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
    # Question feedback persistence
    # ------------------------------------------------------------------

    async def create_question_feedback(
        self,
        *,
        school_id: int,
        response_id: int,
        created_by_id: int,
        feedback_text: str | None = None,
        strength: str | None = None,
        improvement: str | None = None,
        include_with_result: bool = True,
    ) -> AssessmentQuestionFeedback:
        """
        Add a question-feedback record to the session.

        This method does not flush or commit.
        """

        self._validate_positive_integer(
            school_id,
            "school_id",
        )

        self._validate_positive_integer(
            response_id,
            "response_id",
        )

        self._validate_positive_integer(
            created_by_id,
            "created_by_id",
        )

        clean_include_with_result = self._normalise_bool(
            include_with_result,
            field_name="include_with_result",
        )

        feedback = AssessmentQuestionFeedback(
            school_id=school_id,
            response_id=response_id,
            feedback_text=self._normalise_optional_text(
                feedback_text,
                field_name="feedback_text",
            ),
            strength=self._normalise_optional_text(
                strength,
                field_name="strength",
            ),
            improvement=self._normalise_optional_text(
                improvement,
                field_name="improvement",
            ),
            include_with_result=clean_include_with_result,
            created_by_id=created_by_id,
        )

        self.db.add(
            feedback,
        )

        return feedback

    async def update_question_feedback(
        self,
        feedback: AssessmentQuestionFeedback,
        *,
        feedback_text: str | None | object = _UNSET,
        strength: str | None | object = _UNSET,
        improvement: str | None | object = _UNSET,
        include_with_result: bool | object = _UNSET,
        updated_by_id: int | None | object = _UNSET,
    ) -> AssessmentQuestionFeedback:
        """
        Update mutable question-feedback fields.

        `_UNSET` means leave unchanged.

        Nullable text fields may be explicitly cleared with None.

        This method does not flush or commit.
        """

        if feedback_text is not _UNSET:
            feedback.feedback_text = self._normalise_optional_text(
                feedback_text,
                field_name="feedback_text",
            )

        if strength is not _UNSET:
            feedback.strength = self._normalise_optional_text(
                strength,
                field_name="strength",
            )

        if improvement is not _UNSET:
            feedback.improvement = self._normalise_optional_text(
                improvement,
                field_name="improvement",
            )

        if include_with_result is not _UNSET:
            feedback.include_with_result = self._normalise_bool(
                include_with_result,
                field_name="include_with_result",
            )

        if updated_by_id is not _UNSET:
            if updated_by_id is not None:
                self._validate_positive_integer(
                    updated_by_id,
                    "updated_by_id",
                )

            feedback.updated_by_id = updated_by_id

        return feedback

    async def delete_question_feedback(
        self,
        feedback: AssessmentQuestionFeedback,
    ) -> None:
        """
        Mark question feedback for deletion.

        This method does not commit.
        """

        await self.db.delete(
            feedback,
        )
