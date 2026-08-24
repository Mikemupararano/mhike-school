from __future__ import annotations

from decimal import Decimal, InvalidOperation

from sqlalchemy import exists, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.assessment import Assessment
from app.models.assessment_candidate import (
    AssessmentCandidate,
    AssessmentScript,
)
from app.models.assessment_question import AssessmentQuestion
from app.models.assessment_response import (
    AssessmentResponse,
    AssessmentResponseStatus,
    MarkingDecision,
    MarkingDecisionStatus,
)
from app.models.mark_scheme import (
    MarkScheme,
    MarkSchemeItem,
)
from app.models.mark_scheme_award import MarkSchemeItemAward
from app.models.marking_decision_revision import (
    MarkingDecisionRevision,
    MarkingDecisionRevisionChangeType,
    MarkingDecisionRevisionSource,
)


class AssessmentMarkingRepository:
    """
    Repository for assessment responses, marking decisions, and
    mark-scheme item awards.

    School scope is derived through:

        AssessmentResponse
            -> AssessmentScript
            -> AssessmentCandidate
            -> Assessment

    The repository never commits or rolls back transactions. Transaction
    ownership remains with the service or other calling workflow.

    Question-level marks remain authoritative on ``MarkingDecision``.
    Criterion-level ``MarkSchemeItemAward`` records provide supporting
    marking evidence.
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

        if not isinstance(value, int) or isinstance(value, bool) or value < 1:
            raise ValueError(
                f"{field_name} must be a positive integer.",
            )

    @staticmethod
    def _validate_non_negative_integer(
        value: int,
        field_name: str,
    ) -> None:
        """
        Require a non-negative integer.

        MarkingDecision revision zero represents a decision that has not yet
        acquired meaningful immutable marking history.
        """

        if (
            not isinstance(value, int)
            or isinstance(value, bool)
            or value < 0
        ):
            raise ValueError(
                f"{field_name} must be a non-negative integer.",
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

        Blank strings are normalised to ``None``.
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
    def _normalise_decimal(
        value: Decimal | int | float | str,
        *,
        field_name: str,
        allow_zero: bool = True,
    ) -> Decimal:
        """
        Return a validated Decimal value.
        """

        if isinstance(value, bool):
            raise ValueError(
                f"{field_name} must be numeric.",
            )

        try:
            decimal_value = Decimal(
                str(value),
            )
        except (
            InvalidOperation,
            TypeError,
            ValueError,
        ) as exc:
            raise ValueError(
                f"{field_name} must be numeric.",
            ) from exc

        if not decimal_value.is_finite():
            raise ValueError(
                f"{field_name} must be finite.",
            )

        minimum = Decimal("0")

        if allow_zero:
            if decimal_value < minimum:
                raise ValueError(
                    f"{field_name} cannot be negative.",
                )
        elif decimal_value <= minimum:
            raise ValueError(
                f"{field_name} must be greater than zero.",
            )

        return decimal_value

    @staticmethod
    def _normalise_response_status(
        value: AssessmentResponseStatus | str,
    ) -> AssessmentResponseStatus:
        """
        Return a valid AssessmentResponseStatus.
        """

        if isinstance(
            value,
            AssessmentResponseStatus,
        ):
            return value

        if not isinstance(value, str):
            raise ValueError(
                "Response status must be an " "AssessmentResponseStatus or string.",
            )

        try:
            return AssessmentResponseStatus(
                value.strip(),
            )
        except ValueError as exc:
            raise ValueError(
                f"Invalid assessment response status: {value!r}.",
            ) from exc

    @staticmethod
    def _normalise_decision_status(
        value: MarkingDecisionStatus | str,
    ) -> MarkingDecisionStatus:
        """
        Return a valid MarkingDecisionStatus.
        """

        if isinstance(
            value,
            MarkingDecisionStatus,
        ):
            return value

        if not isinstance(value, str):
            raise ValueError(
                "Marking decision status must be a " "MarkingDecisionStatus or string.",
            )

        try:
            return MarkingDecisionStatus(
                value.strip(),
            )
        except ValueError as exc:
            raise ValueError(
                f"Invalid marking decision status: {value!r}.",
            ) from exc

    # ------------------------------------------------------------------
    # Relationship loading
    # ------------------------------------------------------------------

    @staticmethod
    def _apply_response_relationship_loading(
        statement,
        *,
        include_relationships: bool,
    ):
        """
        Apply the standard response eager-loading graph.

        Loaded relationships:

        - script;
        - script candidate;
        - candidate assessment;
        - question;
        - question mark scheme;
        - mark-scheme items;
        - marking decision;
        - marker;
        - criterion awards;
        - each award's mark-scheme item;
        - each award's awarding user.

        ``populate_existing=True`` prevents stale identity-map relationship
        collections after marking records are created or changed in the same
        AsyncSession.
        """

        if not include_relationships:
            return statement

        return statement.execution_options(
            populate_existing=True,
        ).options(
            selectinload(
                AssessmentResponse.script,
            )
            .selectinload(
                AssessmentScript.candidate,
            )
            .selectinload(
                AssessmentCandidate.assessment,
            ),
            selectinload(
                AssessmentResponse.question,
            )
            .selectinload(
                AssessmentQuestion.mark_scheme,
            )
            .selectinload(
                MarkScheme.items,
            ),
            selectinload(
                AssessmentResponse.marking_decision,
            ).selectinload(
                MarkingDecision.marker,
            ),
            selectinload(
                AssessmentResponse.marking_decision,
            )
            .selectinload(
                MarkingDecision.item_awards,
            )
            .selectinload(
                MarkSchemeItemAward.mark_scheme_item,
            ),
            selectinload(
                AssessmentResponse.marking_decision,
            )
            .selectinload(
                MarkingDecision.item_awards,
            )
            .selectinload(
                MarkSchemeItemAward.awarded_by,
            ),
        )

    @staticmethod
    def _apply_decision_relationship_loading(
        statement,
        *,
        include_relationships: bool,
    ):
        """
        Apply the standard marking-decision eager-loading graph.
        """

        if not include_relationships:
            return statement

        return statement.execution_options(
            populate_existing=True,
        ).options(
            selectinload(
                MarkingDecision.response,
            )
            .selectinload(
                AssessmentResponse.script,
            )
            .selectinload(
                AssessmentScript.candidate,
            )
            .selectinload(
                AssessmentCandidate.assessment,
            ),
            selectinload(
                MarkingDecision.response,
            )
            .selectinload(
                AssessmentResponse.question,
            )
            .selectinload(
                AssessmentQuestion.mark_scheme,
            )
            .selectinload(
                MarkScheme.items,
            ),
            selectinload(
                MarkingDecision.response,
            ).selectinload(
                AssessmentResponse.question_snapshot,
            ),
            selectinload(
                MarkingDecision.marker,
            ),
            selectinload(
                MarkingDecision.item_awards,
            ).selectinload(
                MarkSchemeItemAward.mark_scheme_item,
            ),
            selectinload(
                MarkingDecision.item_awards,
            ).selectinload(
                MarkSchemeItemAward.awarded_by,
            ),
        )

    @staticmethod
    def _apply_award_relationship_loading(
        statement,
        *,
        include_relationships: bool,
    ):
        """
        Apply the standard criterion-award eager-loading graph.
        """

        if not include_relationships:
            return statement

        return statement.execution_options(
            populate_existing=True,
        ).options(
            selectinload(
                MarkSchemeItemAward.mark_scheme_item,
            ).selectinload(
                MarkSchemeItem.mark_scheme,
            ),
            selectinload(
                MarkSchemeItemAward.awarded_by,
            ),
            selectinload(
                MarkSchemeItemAward.marking_decision,
            )
            .selectinload(
                MarkingDecision.response,
            )
            .selectinload(
                AssessmentResponse.question,
            ),
        )

    # ------------------------------------------------------------------
    # Question and mark-scheme lookup
    # ------------------------------------------------------------------

    async def get_question_by_id(
        self,
        question_id: int,
        *,
        include_mark_scheme: bool = True,
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

        if include_mark_scheme:
            statement = statement.execution_options(
                populate_existing=True,
            ).options(
                selectinload(
                    AssessmentQuestion.mark_scheme,
                ).selectinload(
                    MarkScheme.items,
                ),
            )

        result = await self.db.execute(
            statement,
        )

        return result.scalar_one_or_none()

    async def get_mark_scheme_item_by_id(
        self,
        item_id: int,
        *,
        include_mark_scheme: bool = True,
    ) -> MarkSchemeItem | None:
        """
        Return one mark-scheme item by global identifier.
        """

        self._validate_positive_integer(
            item_id,
            "item_id",
        )

        statement = select(
            MarkSchemeItem,
        ).where(
            MarkSchemeItem.id == item_id,
        )

        if include_mark_scheme:
            statement = statement.options(
                selectinload(
                    MarkSchemeItem.mark_scheme,
                ),
            )

        result = await self.db.execute(
            statement,
        )

        return result.scalar_one_or_none()

    async def list_mark_scheme_items_for_question(
        self,
        question_id: int,
    ) -> list[MarkSchemeItem]:
        """
        Return mark-scheme items belonging to one question.
        """

        self._validate_positive_integer(
            question_id,
            "question_id",
        )

        statement = (
            select(
                MarkSchemeItem,
            )
            .join(
                MarkScheme,
                MarkScheme.id == MarkSchemeItem.mark_scheme_id,
            )
            .where(
                MarkScheme.question_id == question_id,
            )
            .order_by(
                MarkSchemeItem.order.asc(),
                MarkSchemeItem.id.asc(),
            )
        )

        result = await self.db.execute(
            statement,
        )

        return list(
            result.scalars().all(),
        )

    # ------------------------------------------------------------------
    # Response lookup
    # ------------------------------------------------------------------

    async def get_response_by_id(
        self,
        response_id: int,
        *,
        include_relationships: bool = True,
    ) -> AssessmentResponse | None:
        """
        Return a response by global identifier.
        """

        self._validate_positive_integer(
            response_id,
            "response_id",
        )

        statement = select(
            AssessmentResponse,
        ).where(
            AssessmentResponse.id == response_id,
        )

        statement = self._apply_response_relationship_loading(
            statement,
            include_relationships=include_relationships,
        )

        result = await self.db.execute(
            statement,
        )

        return result.scalar_one_or_none()

    async def get_response_by_id_and_school(
        self,
        response_id: int,
        school_id: int,
        *,
        include_relationships: bool = True,
    ) -> AssessmentResponse | None:
        """
        Return a response only when its script belongs to the school.
        """

        self._validate_positive_integer(
            response_id,
            "response_id",
        )
        self._validate_positive_integer(
            school_id,
            "school_id",
        )

        statement = (
            select(
                AssessmentResponse,
            )
            .join(
                AssessmentScript,
                AssessmentScript.id == AssessmentResponse.script_id,
            )
            .join(
                AssessmentCandidate,
                AssessmentCandidate.id == AssessmentScript.candidate_id,
            )
            .join(
                Assessment,
                Assessment.id == AssessmentCandidate.assessment_id,
            )
            .where(
                AssessmentResponse.id == response_id,
                Assessment.school_id == school_id,
            )
        )

        statement = self._apply_response_relationship_loading(
            statement,
            include_relationships=include_relationships,
        )

        result = await self.db.execute(
            statement,
        )

        return result.scalar_one_or_none()

    async def get_response_by_script_and_question(
        self,
        *,
        script_id: int,
        question_id: int,
        include_relationships: bool = True,
    ) -> AssessmentResponse | None:
        """
        Return the response for one script/question pair.
        """

        self._validate_positive_integer(
            script_id,
            "script_id",
        )
        self._validate_positive_integer(
            question_id,
            "question_id",
        )

        statement = select(
            AssessmentResponse,
        ).where(
            AssessmentResponse.script_id == script_id,
            AssessmentResponse.question_id == question_id,
        )

        statement = self._apply_response_relationship_loading(
            statement,
            include_relationships=include_relationships,
        )

        result = await self.db.execute(
            statement,
        )

        return result.scalar_one_or_none()

    async def response_exists(
        self,
        *,
        script_id: int,
        question_id: int,
    ) -> bool:
        """
        Return whether a response exists for the script/question pair.
        """

        self._validate_positive_integer(
            script_id,
            "script_id",
        )
        self._validate_positive_integer(
            question_id,
            "question_id",
        )

        result = await self.db.execute(
            select(
                exists().where(
                    AssessmentResponse.script_id == script_id,
                    AssessmentResponse.question_id == question_id,
                ),
            ),
        )

        return bool(
            result.scalar_one(),
        )

    # ------------------------------------------------------------------
    # Response collections
    # ------------------------------------------------------------------

    async def list_responses_by_script(
        self,
        script_id: int,
        *,
        status: AssessmentResponseStatus | str | None = None,
        include_relationships: bool = True,
    ) -> list[AssessmentResponse]:
        """
        Return responses belonging to one script.
        """

        self._validate_positive_integer(
            script_id,
            "script_id",
        )

        statement = (
            select(
                AssessmentResponse,
            )
            .join(
                AssessmentQuestion,
                AssessmentQuestion.id == AssessmentResponse.question_id,
            )
            .where(
                AssessmentResponse.script_id == script_id,
            )
        )

        if status is not None:
            normalised_status = self._normalise_response_status(
                status,
            )

            statement = statement.where(
                AssessmentResponse.status == normalised_status,
            )

        statement = statement.order_by(
            AssessmentQuestion.order.asc(),
            AssessmentQuestion.id.asc(),
            AssessmentResponse.id.asc(),
        )

        statement = self._apply_response_relationship_loading(
            statement,
            include_relationships=include_relationships,
        )

        result = await self.db.execute(
            statement,
        )

        return list(
            result.scalars().unique().all(),
        )

    async def list_responses_by_question(
        self,
        question_id: int,
        *,
        status: AssessmentResponseStatus | str | None = None,
        include_relationships: bool = True,
    ) -> list[AssessmentResponse]:
        """
        Return candidate responses to one assessment question.
        """

        self._validate_positive_integer(
            question_id,
            "question_id",
        )

        statement = select(
            AssessmentResponse,
        ).where(
            AssessmentResponse.question_id == question_id,
        )

        if status is not None:
            normalised_status = self._normalise_response_status(
                status,
            )

            statement = statement.where(
                AssessmentResponse.status == normalised_status,
            )

        statement = statement.order_by(
            AssessmentResponse.id.asc(),
        )

        statement = self._apply_response_relationship_loading(
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
    # Response persistence
    # ------------------------------------------------------------------

    async def create_response(
        self,
        response: AssessmentResponse,
    ) -> AssessmentResponse:
        """
        Add and flush a new assessment response.

        This method does not commit the transaction.
        """

        self._validate_positive_integer(
            response.script_id,
            "script_id",
        )
        self._validate_positive_integer(
            response.question_id,
            "question_id",
        )

        response.status = self._normalise_response_status(
            response.status,
        )

        response.response_text = self._normalise_optional_text(
            response.response_text,
            field_name="response_text",
        )

        response.response_data = self._normalise_optional_text(
            response.response_data,
            field_name="response_data",
        )

        response.source_reference = self._normalise_optional_text(
            response.source_reference,
            field_name="source_reference",
            max_length=1000,
        )

        self.db.add(
            response,
        )

        await self.db.flush()
        await self.db.refresh(
            response,
        )

        return response

    async def save_response(
        self,
        response: AssessmentResponse,
    ) -> AssessmentResponse:
        """
        Persist and flush an existing assessment response.
        """

        if response.id is None:
            raise ValueError(
                "Cannot save a response without an ID.",
            )

        self._validate_positive_integer(
            response.id,
            "response.id",
        )
        self._validate_positive_integer(
            response.script_id,
            "script_id",
        )
        self._validate_positive_integer(
            response.question_id,
            "question_id",
        )

        response.status = self._normalise_response_status(
            response.status,
        )

        response.response_text = self._normalise_optional_text(
            response.response_text,
            field_name="response_text",
        )

        response.response_data = self._normalise_optional_text(
            response.response_data,
            field_name="response_data",
        )

        response.source_reference = self._normalise_optional_text(
            response.source_reference,
            field_name="source_reference",
            max_length=1000,
        )

        self.db.add(
            response,
        )

        await self.db.flush()
        await self.db.refresh(
            response,
        )

        return response

    async def get_response_by_id_for_update(
        self,
        response_id: int,
    ) -> AssessmentResponse | None:
        """
        Return one assessment response while locking its database row.

        The lock is held until the surrounding transaction commits or
        rolls back. ``populate_existing`` refreshes any response already
        present in the session identity map so callers make retention
        and workflow decisions from the authoritative current state.

        Relationships are intentionally not eager-loaded here. The lock
        protects the authoritative AssessmentResponse row.
        """

        self._validate_positive_integer(
            response_id,
            "response_id",
        )

        statement = (
            select(
                AssessmentResponse,
            )
            .where(
                AssessmentResponse.id == response_id,
            )
            .with_for_update()
            .execution_options(
                populate_existing=True,
            )
        )

        result = await self.db.execute(
            statement,
        )

        return result.scalar_one_or_none()

    async def delete_response(
        self,
        response: AssessmentResponse,
    ) -> None:
        """
        Delete and flush an assessment response.
        """

        if response.id is None:
            raise ValueError(
                "Cannot delete a response without an ID.",
            )

        self._validate_positive_integer(
            response.id,
            "response.id",
        )

        await self.db.delete(
            response,
        )

        await self.db.flush()

    # ------------------------------------------------------------------
    # Marking-decision lookup
    # ------------------------------------------------------------------

    async def get_decision_by_id(
        self,
        decision_id: int,
        *,
        include_relationships: bool = True,
    ) -> MarkingDecision | None:
        """
        Return a marking decision by global identifier.
        """

        self._validate_positive_integer(
            decision_id,
            "decision_id",
        )

        statement = select(
            MarkingDecision,
        ).where(
            MarkingDecision.id == decision_id,
        )

        statement = self._apply_decision_relationship_loading(
            statement,
            include_relationships=include_relationships,
        )

        result = await self.db.execute(
            statement,
        )

        return result.scalar_one_or_none()

    async def get_decision_by_id_for_update(
        self,
        decision_id: int,
    ) -> MarkingDecision | None:
        """
        Return one marking decision while locking its database row.

        The lock is held until the surrounding transaction commits or
        rolls back. ``populate_existing`` refreshes any decision already
        present in the session identity map so callers compare against
        the authoritative current revision and status.

        Relationships are intentionally not eager-loaded here. This lock
        protects the authoritative MarkingDecision row only.
        """

        self._validate_positive_integer(
            decision_id,
            "decision_id",
        )

        statement = (
            select(
                MarkingDecision,
            )
            .where(
                MarkingDecision.id == decision_id,
            )
            .with_for_update()
            .execution_options(
                populate_existing=True,
            )
        )

        result = await self.db.execute(
            statement,
        )

        return result.scalar_one_or_none()

    async def get_decision_by_id_and_school(
        self,
        decision_id: int,
        school_id: int,
        *,
        include_relationships: bool = True,
    ) -> MarkingDecision | None:
        """
        Return a marking decision only when its response belongs to the school.
        """

        self._validate_positive_integer(
            decision_id,
            "decision_id",
        )
        self._validate_positive_integer(
            school_id,
            "school_id",
        )

        statement = (
            select(
                MarkingDecision,
            )
            .join(
                AssessmentResponse,
                AssessmentResponse.id == MarkingDecision.response_id,
            )
            .join(
                AssessmentScript,
                AssessmentScript.id == AssessmentResponse.script_id,
            )
            .join(
                AssessmentCandidate,
                AssessmentCandidate.id == AssessmentScript.candidate_id,
            )
            .join(
                Assessment,
                Assessment.id == AssessmentCandidate.assessment_id,
            )
            .where(
                MarkingDecision.id == decision_id,
                Assessment.school_id == school_id,
            )
        )

        statement = self._apply_decision_relationship_loading(
            statement,
            include_relationships=include_relationships,
        )

        result = await self.db.execute(
            statement,
        )

        return result.scalar_one_or_none()

    async def get_decision_by_response(
        self,
        response_id: int,
        *,
        include_relationships: bool = True,
    ) -> MarkingDecision | None:
        """
        Return the marking decision for one response.
        """

        self._validate_positive_integer(
            response_id,
            "response_id",
        )

        statement = select(
            MarkingDecision,
        ).where(
            MarkingDecision.response_id == response_id,
        )

        statement = self._apply_decision_relationship_loading(
            statement,
            include_relationships=include_relationships,
        )

        result = await self.db.execute(
            statement,
        )

        return result.scalar_one_or_none()

    async def decision_exists_for_response(
        self,
        response_id: int,
    ) -> bool:
        """
        Return whether a marking decision already exists for a response.
        """

        self._validate_positive_integer(
            response_id,
            "response_id",
        )

        result = await self.db.execute(
            select(
                exists().where(
                    MarkingDecision.response_id == response_id,
                ),
            ),
        )

        return bool(
            result.scalar_one(),
        )

    # ------------------------------------------------------------------
    # Marking-decision collections
    # ------------------------------------------------------------------

    async def list_decisions_by_script(
        self,
        script_id: int,
        *,
        status: MarkingDecisionStatus | str | None = None,
        include_relationships: bool = True,
    ) -> list[MarkingDecision]:
        """
        Return marking decisions for one assessment script.
        """

        self._validate_positive_integer(
            script_id,
            "script_id",
        )

        statement = (
            select(
                MarkingDecision,
            )
            .join(
                AssessmentResponse,
                AssessmentResponse.id == MarkingDecision.response_id,
            )
            .join(
                AssessmentQuestion,
                AssessmentQuestion.id == AssessmentResponse.question_id,
            )
            .where(
                AssessmentResponse.script_id == script_id,
            )
        )

        if status is not None:
            normalised_status = self._normalise_decision_status(
                status,
            )

            statement = statement.where(
                MarkingDecision.status == normalised_status,
            )

        statement = statement.order_by(
            AssessmentQuestion.order.asc(),
            AssessmentQuestion.id.asc(),
            MarkingDecision.id.asc(),
        )

        statement = self._apply_decision_relationship_loading(
            statement,
            include_relationships=include_relationships,
        )

        result = await self.db.execute(
            statement,
        )

        return list(
            result.scalars().unique().all(),
        )

    async def list_decisions_by_marker(
        self,
        marker_id: int,
        *,
        status: MarkingDecisionStatus | str | None = None,
        include_relationships: bool = True,
    ) -> list[MarkingDecision]:
        """
        Return marking decisions allocated to one marker.
        """

        self._validate_positive_integer(
            marker_id,
            "marker_id",
        )

        statement = select(
            MarkingDecision,
        ).where(
            MarkingDecision.marker_id == marker_id,
        )

        if status is not None:
            normalised_status = self._normalise_decision_status(
                status,
            )

            statement = statement.where(
                MarkingDecision.status == normalised_status,
            )

        statement = statement.order_by(
            MarkingDecision.id.asc(),
        )

        statement = self._apply_decision_relationship_loading(
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
    # Marking-decision persistence
    # ------------------------------------------------------------------

    async def create_decision(
        self,
        decision: MarkingDecision,
    ) -> MarkingDecision:
        """
        Add and flush a new marking decision.
        """

        self._validate_positive_integer(
            decision.response_id,
            "response_id",
        )

        if decision.marker_id is not None:
            self._validate_positive_integer(
                decision.marker_id,
                "marker_id",
            )

        decision.status = self._normalise_decision_status(
            decision.status,
        )

        if decision.mark_awarded is not None:
            decision.mark_awarded = self._normalise_decimal(
                decision.mark_awarded,
                field_name="mark_awarded",
            )

        decision.marker_comment = self._normalise_optional_text(
            decision.marker_comment,
            field_name="marker_comment",
        )

        decision.moderation_comment = self._normalise_optional_text(
            decision.moderation_comment,
            field_name="moderation_comment",
        )

        self.db.add(
            decision,
        )

        await self.db.flush()
        await self.db.refresh(
            decision,
        )

        return decision

    async def list_decision_revisions(
        self,
        decision_id: int,
    ) -> list[MarkingDecisionRevision]:
        """
        Return immutable history for one marking decision.

        Revisions are returned oldest first so callers receive the
        authoritative marking history in chronological revision order.
        """

        self._validate_positive_integer(
            decision_id,
            "decision_id",
        )

        statement = (
            select(
                MarkingDecisionRevision,
            )
            .where(
                MarkingDecisionRevision.marking_decision_id == decision_id,
            )
            .order_by(
                MarkingDecisionRevision.revision.asc(),
            )
        )

        result = await self.db.execute(
            statement,
        )

        return list(
            result.scalars().all(),
        )

    async def update_decision_with_revision(
        self,
        decision_id: int,
        expected_revision: int,
        *,
        values: dict,
        changed_by_id: int,
        change_type: MarkingDecisionRevisionChangeType | str,
        source: MarkingDecisionRevisionSource | str,
    ) -> MarkingDecisionRevision | None:
        """
        Atomically update a marking decision and append immutable history.

        The update succeeds only when ``expected_revision`` still matches the
        authoritative live decision. A ``None`` result means the decision did
        not exist or another request changed it first.

        The revision snapshot is built from the values returned by PostgreSQL
        after the successful update, so history reflects the exact persisted
        authoritative state.

        This method flushes but does not commit. Transaction ownership remains
        with the calling service.
        """

        self._validate_positive_integer(
            decision_id,
            "decision_id",
        )
        self._validate_non_negative_integer(
            expected_revision,
            "expected_revision",
        )
        self._validate_positive_integer(
            changed_by_id,
            "changed_by_id",
        )

        try:
            normalised_change_type = MarkingDecisionRevisionChangeType(
                change_type,
            )
        except (TypeError, ValueError) as exc:
            raise ValueError(
                "change_type is not a valid marking decision revision "
                "change type.",
            ) from exc

        try:
            normalised_source = MarkingDecisionRevisionSource(
                source,
            )
        except (TypeError, ValueError) as exc:
            raise ValueError(
                "source is not a valid marking decision revision source.",
            ) from exc

        allowed_fields = {
            "marker_id",
            "status",
            "mark_awarded",
            "marker_comment",
            "moderation_comment",
            "marked_at",
            "reviewed_at",
            "finalised_at",
        }

        unexpected_fields = set(values) - allowed_fields

        if unexpected_fields:
            raise ValueError(
                "Unsupported marking decision update fields: "
                + ", ".join(
                    sorted(unexpected_fields),
                ),
            )

        safe_values = dict(
            values,
        )

        if "marker_id" in safe_values:
            marker_id = safe_values["marker_id"]

            if marker_id is not None:
                self._validate_positive_integer(
                    marker_id,
                    "marker_id",
                )

        if "status" in safe_values:
            safe_values["status"] = self._normalise_decision_status(
                safe_values["status"],
            )

        if (
            "mark_awarded" in safe_values
            and safe_values["mark_awarded"] is not None
        ):
            safe_values["mark_awarded"] = self._normalise_decimal(
                safe_values["mark_awarded"],
                field_name="mark_awarded",
            )

        if "marker_comment" in safe_values:
            safe_values["marker_comment"] = self._normalise_optional_text(
                safe_values["marker_comment"],
                field_name="marker_comment",
            )

        if "moderation_comment" in safe_values:
            safe_values["moderation_comment"] = (
                self._normalise_optional_text(
                    safe_values["moderation_comment"],
                    field_name="moderation_comment",
                )
            )

        next_revision = expected_revision + 1

        safe_values["revision"] = next_revision

        statement = (
            update(
                MarkingDecision,
            )
            .where(
                MarkingDecision.id == decision_id,
                MarkingDecision.revision == expected_revision,
            )
            .values(
                **safe_values,
            )
            .returning(
                MarkingDecision.id,
                MarkingDecision.response_id,
                MarkingDecision.marker_id,
                MarkingDecision.status,
                MarkingDecision.mark_awarded,
                MarkingDecision.marker_comment,
                MarkingDecision.moderation_comment,
                MarkingDecision.marked_at,
                MarkingDecision.reviewed_at,
                MarkingDecision.finalised_at,
                MarkingDecision.revision,
            )
        )

        result = await self.db.execute(
            statement,
        )

        updated = result.mappings().one_or_none()

        if updated is None:
            return None

        revision = MarkingDecisionRevision(
            marking_decision_id=updated["id"],
            response_id=updated["response_id"],
            revision=updated["revision"],
            changed_by_id=changed_by_id,
            change_type=normalised_change_type,
            source=normalised_source,
            marker_id=updated["marker_id"],
            status=updated["status"],
            mark_awarded=updated["mark_awarded"],
            marker_comment=updated["marker_comment"],
            moderation_comment=updated["moderation_comment"],
            marked_at=updated["marked_at"],
            reviewed_at=updated["reviewed_at"],
            finalised_at=updated["finalised_at"],
        )

        self.db.add(
            revision,
        )

        await self.db.flush()
        await self.db.refresh(
            revision,
        )

        return revision

    async def delete_decision(
        self,
        decision: MarkingDecision,
    ) -> None:
        """
        Delete and flush a marking decision.
        """

        if decision.id is None:
            raise ValueError(
                "Cannot delete a marking decision without an ID.",
            )

        self._validate_positive_integer(
            decision.id,
            "decision.id",
        )

        await self.db.delete(
            decision,
        )

        await self.db.flush()

    # ------------------------------------------------------------------
    # Criterion-award lookup
    # ------------------------------------------------------------------

    async def get_award_by_id(
        self,
        award_id: int,
        *,
        include_relationships: bool = True,
    ) -> MarkSchemeItemAward | None:
        """
        Return one criterion award by identifier.
        """

        self._validate_positive_integer(
            award_id,
            "award_id",
        )

        statement = select(
            MarkSchemeItemAward,
        ).where(
            MarkSchemeItemAward.id == award_id,
        )

        statement = self._apply_award_relationship_loading(
            statement,
            include_relationships=include_relationships,
        )

        result = await self.db.execute(
            statement,
        )

        return result.scalar_one_or_none()

    async def get_award_by_decision_and_item(
        self,
        *,
        decision_id: int,
        mark_scheme_item_id: int,
        include_relationships: bool = True,
    ) -> MarkSchemeItemAward | None:
        """
        Return one criterion award for a decision/item pair.
        """

        self._validate_positive_integer(
            decision_id,
            "decision_id",
        )
        self._validate_positive_integer(
            mark_scheme_item_id,
            "mark_scheme_item_id",
        )

        statement = select(
            MarkSchemeItemAward,
        ).where(
            MarkSchemeItemAward.marking_decision_id == decision_id,
            MarkSchemeItemAward.mark_scheme_item_id == mark_scheme_item_id,
        )

        statement = self._apply_award_relationship_loading(
            statement,
            include_relationships=include_relationships,
        )

        result = await self.db.execute(
            statement,
        )

        return result.scalar_one_or_none()

    async def award_exists(
        self,
        *,
        decision_id: int,
        mark_scheme_item_id: int,
    ) -> bool:
        """
        Return whether a criterion award already exists.
        """

        self._validate_positive_integer(
            decision_id,
            "decision_id",
        )
        self._validate_positive_integer(
            mark_scheme_item_id,
            "mark_scheme_item_id",
        )

        result = await self.db.execute(
            select(
                exists().where(
                    MarkSchemeItemAward.marking_decision_id == decision_id,
                    MarkSchemeItemAward.mark_scheme_item_id == mark_scheme_item_id,
                ),
            ),
        )

        return bool(
            result.scalar_one(),
        )

    async def list_awards_by_decision(
        self,
        decision_id: int,
        *,
        include_relationships: bool = True,
    ) -> list[MarkSchemeItemAward]:
        """
        Return criterion-level awards for one marking decision.
        """

        self._validate_positive_integer(
            decision_id,
            "decision_id",
        )

        statement = (
            select(
                MarkSchemeItemAward,
            )
            .join(
                MarkSchemeItem,
                MarkSchemeItem.id == MarkSchemeItemAward.mark_scheme_item_id,
            )
            .where(
                MarkSchemeItemAward.marking_decision_id == decision_id,
            )
            .order_by(
                MarkSchemeItem.order.asc(),
                MarkSchemeItem.id.asc(),
                MarkSchemeItemAward.id.asc(),
            )
        )

        statement = self._apply_award_relationship_loading(
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
    # Criterion-award persistence
    # ------------------------------------------------------------------

    async def create_award(
        self,
        award: MarkSchemeItemAward,
    ) -> MarkSchemeItemAward:
        """
        Add and flush a new mark-scheme item award.
        """

        self._validate_positive_integer(
            award.marking_decision_id,
            "marking_decision_id",
        )
        self._validate_positive_integer(
            award.mark_scheme_item_id,
            "mark_scheme_item_id",
        )

        if award.awarded_by_id is not None:
            self._validate_positive_integer(
                award.awarded_by_id,
                "awarded_by_id",
            )

        award.marks_awarded = self._normalise_decimal(
            award.marks_awarded,
            field_name="marks_awarded",
        )

        award.marker_note = self._normalise_optional_text(
            award.marker_note,
            field_name="marker_note",
        )

        self.db.add(
            award,
        )

        await self.db.flush()
        await self.db.refresh(
            award,
        )

        return award

    async def save_award(
        self,
        award: MarkSchemeItemAward,
    ) -> MarkSchemeItemAward:
        """
        Persist and flush an existing mark-scheme item award.
        """

        if award.id is None:
            raise ValueError(
                "Cannot save a mark-scheme item award without an ID.",
            )

        self._validate_positive_integer(
            award.id,
            "award.id",
        )
        self._validate_positive_integer(
            award.marking_decision_id,
            "marking_decision_id",
        )
        self._validate_positive_integer(
            award.mark_scheme_item_id,
            "mark_scheme_item_id",
        )

        if award.awarded_by_id is not None:
            self._validate_positive_integer(
                award.awarded_by_id,
                "awarded_by_id",
            )

        award.marks_awarded = self._normalise_decimal(
            award.marks_awarded,
            field_name="marks_awarded",
        )

        award.marker_note = self._normalise_optional_text(
            award.marker_note,
            field_name="marker_note",
        )

        self.db.add(
            award,
        )

        await self.db.flush()
        await self.db.refresh(
            award,
        )

        return award

    async def delete_award(
        self,
        award: MarkSchemeItemAward,
    ) -> None:
        """
        Delete and flush a criterion-level award.
        """

        if award.id is None:
            raise ValueError(
                "Cannot delete a mark-scheme item award without an ID.",
            )

        self._validate_positive_integer(
            award.id,
            "award.id",
        )

        await self.db.delete(
            award,
        )

        await self.db.flush()
