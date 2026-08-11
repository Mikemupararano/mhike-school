from __future__ import annotations

from decimal import Decimal

from sqlalchemy import (
    case,
    func,
    select,
)
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


class AssessmentResultsRepository:
    """
    Read-oriented repository for assessment results and marking analytics.

    Result data is derived from authoritative assessment structures rather
    than duplicated onto Assessment or AssessmentScript.

    Key rules:

    - AssessmentQuestion.maximum_mark is the available mark for one question.
    - Every question with is_markable=True contributes to the assessment
      maximum.
    - MarkingDecision.mark_awarded is the authoritative awarded question mark.
    - A response is unique per script/question.
    - A marking decision is unique per response.
    - Results remain derivable at any stage of marking.

    This repository does not commit or roll back transactions.
    """

    COMPLETED_MARKING_STATUSES = {
        MarkingDecisionStatus.MARKED,
        MarkingDecisionStatus.REVIEWED,
        MarkingDecisionStatus.FINALISED,
    }

    FINAL_MARKING_STATUSES = {
        MarkingDecisionStatus.FINALISED,
    }

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

        if not isinstance(value, int) or isinstance(value, bool) or value < 1:
            raise ValueError(
                f"{field_name} must be a positive integer.",
            )

    @staticmethod
    def _normalise_decision_status(
        value: MarkingDecisionStatus | str,
    ) -> MarkingDecisionStatus:
        """
        Return a valid marking-decision status.
        """

        if isinstance(
            value,
            MarkingDecisionStatus,
        ):
            return value

        if not isinstance(value, str):
            raise ValueError(
                "status must be a MarkingDecisionStatus or string.",
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
    def _apply_script_result_loading(
        statement,
    ):
        """
        Apply relationships needed for one script result.

        Loaded graph:

        script
            -> candidate
                -> assessment
                    -> questions

        script
            -> responses
                -> question
                -> marking_decision
        """

        return statement.execution_options(
            populate_existing=True,
        ).options(
            selectinload(
                AssessmentScript.candidate,
            )
            .selectinload(
                AssessmentCandidate.assessment,
            )
            .selectinload(
                Assessment.questions,
            ),
            selectinload(
                AssessmentScript.responses,
            ).selectinload(
                AssessmentResponse.question,
            ),
            selectinload(
                AssessmentScript.responses,
            ).selectinload(
                AssessmentResponse.marking_decision,
            ),
        )

    @staticmethod
    def _apply_candidate_result_loading(
        statement,
    ):
        """
        Apply relationships needed for candidate-result inspection.
        """

        return statement.execution_options(
            populate_existing=True,
        ).options(
            selectinload(
                AssessmentCandidate.assessment,
            ).selectinload(
                Assessment.questions,
            ),
            selectinload(
                AssessmentCandidate.scripts,
            )
            .selectinload(
                AssessmentScript.responses,
            )
            .selectinload(
                AssessmentResponse.question,
            ),
            selectinload(
                AssessmentCandidate.scripts,
            )
            .selectinload(
                AssessmentScript.responses,
            )
            .selectinload(
                AssessmentResponse.marking_decision,
            ),
        )

    @staticmethod
    def _apply_assessment_result_loading(
        statement,
    ):
        """
        Apply relationships needed for assessment-wide results.
        """

        return statement.execution_options(
            populate_existing=True,
        ).options(
            selectinload(
                Assessment.questions,
            ),
            selectinload(
                Assessment.candidates,
            )
            .selectinload(
                AssessmentCandidate.scripts,
            )
            .selectinload(
                AssessmentScript.responses,
            )
            .selectinload(
                AssessmentResponse.question,
            ),
            selectinload(
                Assessment.candidates,
            )
            .selectinload(
                AssessmentCandidate.scripts,
            )
            .selectinload(
                AssessmentScript.responses,
            )
            .selectinload(
                AssessmentResponse.marking_decision,
            ),
        )

    # ------------------------------------------------------------------
    # Core entity lookup
    # ------------------------------------------------------------------

    async def get_assessment_by_id(
        self,
        assessment_id: int,
        *,
        include_results: bool = True,
    ) -> Assessment | None:
        """
        Return an assessment by identifier.
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

        if include_results:
            statement = self._apply_assessment_result_loading(
                statement,
            )

        result = await self.db.execute(
            statement,
        )

        return result.scalar_one_or_none()

    async def get_candidate_by_id(
        self,
        candidate_id: int,
        *,
        include_results: bool = True,
    ) -> AssessmentCandidate | None:
        """
        Return an assessment candidate by identifier.
        """

        self._validate_positive_integer(
            candidate_id,
            "candidate_id",
        )

        statement = select(
            AssessmentCandidate,
        ).where(
            AssessmentCandidate.id == candidate_id,
        )

        if include_results:
            statement = self._apply_candidate_result_loading(
                statement,
            )

        result = await self.db.execute(
            statement,
        )

        return result.scalar_one_or_none()

    async def get_script_by_id(
        self,
        script_id: int,
        *,
        include_results: bool = True,
    ) -> AssessmentScript | None:
        """
        Return one assessment script by identifier.
        """

        self._validate_positive_integer(
            script_id,
            "script_id",
        )

        statement = select(
            AssessmentScript,
        ).where(
            AssessmentScript.id == script_id,
        )

        if include_results:
            statement = self._apply_script_result_loading(
                statement,
            )

        result = await self.db.execute(
            statement,
        )

        return result.scalar_one_or_none()

    # ------------------------------------------------------------------
    # Markable question queries
    # ------------------------------------------------------------------

    async def list_markable_questions(
        self,
        assessment_id: int,
    ) -> list[AssessmentQuestion]:
        """
        Return all questions that contribute to the assessment maximum.

        Nesting does not alter the rule. A parent or child contributes when
        and only when its own is_markable flag is True.
        """

        self._validate_positive_integer(
            assessment_id,
            "assessment_id",
        )

        result = await self.db.execute(
            select(
                AssessmentQuestion,
            )
            .where(
                AssessmentQuestion.assessment_id == assessment_id,
                AssessmentQuestion.is_markable.is_(True),
            )
            .order_by(
                AssessmentQuestion.order.asc(),
                AssessmentQuestion.id.asc(),
            ),
        )

        return list(
            result.scalars().all(),
        )

    async def get_assessment_maximum_mark(
        self,
        assessment_id: int,
    ) -> Decimal:
        """
        Return the sum of maximum marks for all markable questions.
        """

        self._validate_positive_integer(
            assessment_id,
            "assessment_id",
        )

        result = await self.db.execute(
            select(
                func.coalesce(
                    func.sum(
                        AssessmentQuestion.maximum_mark,
                    ),
                    Decimal("0"),
                ),
            ).where(
                AssessmentQuestion.assessment_id == assessment_id,
                AssessmentQuestion.is_markable.is_(True),
            ),
        )

        value = result.scalar_one()

        return Decimal(
            str(value),
        )

    async def count_markable_questions(
        self,
        assessment_id: int,
    ) -> int:
        """
        Return the number of markable questions in an assessment.
        """

        self._validate_positive_integer(
            assessment_id,
            "assessment_id",
        )

        result = await self.db.execute(
            select(
                func.count(
                    AssessmentQuestion.id,
                ),
            ).where(
                AssessmentQuestion.assessment_id == assessment_id,
                AssessmentQuestion.is_markable.is_(True),
            ),
        )

        return int(
            result.scalar_one(),
        )

    # ------------------------------------------------------------------
    # Script response counts
    # ------------------------------------------------------------------

    async def count_script_responses(
        self,
        script_id: int,
        *,
        exclude_void: bool = True,
    ) -> int:
        """
        Return the number of responses recorded for a script.

        VOID responses are excluded by default.
        """

        self._validate_positive_integer(
            script_id,
            "script_id",
        )

        statement = select(
            func.count(
                AssessmentResponse.id,
            ),
        ).where(
            AssessmentResponse.script_id == script_id,
        )

        if exclude_void:
            statement = statement.where(
                AssessmentResponse.status != AssessmentResponseStatus.VOID,
            )

        result = await self.db.execute(
            statement,
        )

        return int(
            result.scalar_one(),
        )

    async def count_script_submitted_responses(
        self,
        script_id: int,
    ) -> int:
        """
        Return the number of submitted responses for a script.
        """

        self._validate_positive_integer(
            script_id,
            "script_id",
        )

        result = await self.db.execute(
            select(
                func.count(
                    AssessmentResponse.id,
                ),
            ).where(
                AssessmentResponse.script_id == script_id,
                AssessmentResponse.status == AssessmentResponseStatus.SUBMITTED,
            ),
        )

        return int(
            result.scalar_one(),
        )

    # ------------------------------------------------------------------
    # Script marking counts
    # ------------------------------------------------------------------

    async def count_script_decisions(
        self,
        script_id: int,
    ) -> int:
        """
        Return the number of marking decisions for a script.
        """

        self._validate_positive_integer(
            script_id,
            "script_id",
        )

        result = await self.db.execute(
            select(
                func.count(
                    MarkingDecision.id,
                ),
            )
            .join(
                AssessmentResponse,
                AssessmentResponse.id == MarkingDecision.response_id,
            )
            .where(
                AssessmentResponse.script_id == script_id,
            ),
        )

        return int(
            result.scalar_one(),
        )

    async def count_script_decisions_by_status(
        self,
        script_id: int,
        statuses: set[MarkingDecisionStatus | str],
    ) -> int:
        """
        Return the number of script decisions in the supplied statuses.
        """

        self._validate_positive_integer(
            script_id,
            "script_id",
        )

        if not statuses:
            return 0

        normalised_statuses = {
            self._normalise_decision_status(
                value,
            )
            for value in statuses
        }

        result = await self.db.execute(
            select(
                func.count(
                    MarkingDecision.id,
                ),
            )
            .join(
                AssessmentResponse,
                AssessmentResponse.id == MarkingDecision.response_id,
            )
            .where(
                AssessmentResponse.script_id == script_id,
                MarkingDecision.status.in_(
                    normalised_statuses,
                ),
            ),
        )

        return int(
            result.scalar_one(),
        )

    async def count_script_completed_decisions(
        self,
        script_id: int,
    ) -> int:
        """
        Return decisions where primary marking is complete or beyond.
        """

        return await self.count_script_decisions_by_status(
            script_id,
            self.COMPLETED_MARKING_STATUSES,
        )

    async def count_script_finalised_decisions(
        self,
        script_id: int,
    ) -> int:
        """
        Return finalised marking decisions for a script.
        """

        return await self.count_script_decisions_by_status(
            script_id,
            self.FINAL_MARKING_STATUSES,
        )

    # ------------------------------------------------------------------
    # Script awarded marks
    # ------------------------------------------------------------------

    async def get_script_mark_awarded(
        self,
        script_id: int,
        *,
        completed_only: bool = False,
        finalised_only: bool = False,
    ) -> Decimal:
        """
        Return the sum of authoritative question-level marks for a script.

        By default, any non-null mark_awarded contributes, including
        provisional IN_PROGRESS marking.

        ``completed_only=True`` restricts the result to MARKED, REVIEWED,
        and FINALISED decisions.

        ``finalised_only=True`` restricts the result to FINALISED decisions.
        """

        self._validate_positive_integer(
            script_id,
            "script_id",
        )

        statement = (
            select(
                func.coalesce(
                    func.sum(
                        MarkingDecision.mark_awarded,
                    ),
                    Decimal("0"),
                ),
            )
            .join(
                AssessmentResponse,
                AssessmentResponse.id == MarkingDecision.response_id,
            )
            .where(
                AssessmentResponse.script_id == script_id,
                MarkingDecision.mark_awarded.is_not(None),
            )
        )

        if finalised_only:
            statement = statement.where(
                MarkingDecision.status == MarkingDecisionStatus.FINALISED,
            )

        elif completed_only:
            statement = statement.where(
                MarkingDecision.status.in_(
                    self.COMPLETED_MARKING_STATUSES,
                ),
            )

        result = await self.db.execute(
            statement,
        )

        value = result.scalar_one()

        return Decimal(
            str(value),
        )

    # ------------------------------------------------------------------
    # Question-level script results
    # ------------------------------------------------------------------

    async def list_script_question_results(
        self,
        script_id: int,
    ) -> list[
        tuple[
            AssessmentQuestion,
            AssessmentResponse | None,
            MarkingDecision | None,
        ]
    ]:
        """
        Return one result row for every markable assessment question.

        Questions without responses or marking decisions are retained so the
        caller can distinguish:

        - no response;
        - response captured but not marked;
        - provisional marking;
        - completed marking;
        - finalised marking.
        """

        self._validate_positive_integer(
            script_id,
            "script_id",
        )

        script = await self.get_script_by_id(
            script_id,
            include_results=False,
        )

        if script is None:
            return []

        candidate = await self.get_candidate_by_id(
            script.candidate_id,
            include_results=False,
        )

        if candidate is None:
            return []

        statement = (
            select(
                AssessmentQuestion,
                AssessmentResponse,
                MarkingDecision,
            )
            .outerjoin(
                AssessmentResponse,
                (AssessmentResponse.question_id == AssessmentQuestion.id)
                & (AssessmentResponse.script_id == script_id),
            )
            .outerjoin(
                MarkingDecision,
                MarkingDecision.response_id == AssessmentResponse.id,
            )
            .where(
                AssessmentQuestion.assessment_id == candidate.assessment_id,
                AssessmentQuestion.is_markable.is_(True),
            )
            .order_by(
                AssessmentQuestion.order.asc(),
                AssessmentQuestion.id.asc(),
            )
        )

        result = await self.db.execute(
            statement,
        )

        return [
            (
                row[0],
                row[1],
                row[2],
            )
            for row in result.all()
        ]

    # ------------------------------------------------------------------
    # Assessment-wide marking summaries
    # ------------------------------------------------------------------

    async def count_assessment_candidates(
        self,
        assessment_id: int,
    ) -> int:
        """
        Return the number of allocated candidates for an assessment.
        """

        self._validate_positive_integer(
            assessment_id,
            "assessment_id",
        )

        result = await self.db.execute(
            select(
                func.count(
                    AssessmentCandidate.id,
                ),
            ).where(
                AssessmentCandidate.assessment_id == assessment_id,
            ),
        )

        return int(
            result.scalar_one(),
        )

    async def count_assessment_scripts(
        self,
        assessment_id: int,
    ) -> int:
        """
        Return the number of script versions belonging to an assessment.
        """

        self._validate_positive_integer(
            assessment_id,
            "assessment_id",
        )

        result = await self.db.execute(
            select(
                func.count(
                    AssessmentScript.id,
                ),
            )
            .join(
                AssessmentCandidate,
                AssessmentCandidate.id == AssessmentScript.candidate_id,
            )
            .where(
                AssessmentCandidate.assessment_id == assessment_id,
            ),
        )

        return int(
            result.scalar_one(),
        )

    async def count_assessment_decisions_by_status(
        self,
        assessment_id: int,
        statuses: set[MarkingDecisionStatus | str],
    ) -> int:
        """
        Count assessment marking decisions in selected lifecycle states.
        """

        self._validate_positive_integer(
            assessment_id,
            "assessment_id",
        )

        if not statuses:
            return 0

        normalised_statuses = {
            self._normalise_decision_status(
                value,
            )
            for value in statuses
        }

        result = await self.db.execute(
            select(
                func.count(
                    MarkingDecision.id,
                ),
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
            .where(
                AssessmentCandidate.assessment_id == assessment_id,
                MarkingDecision.status.in_(
                    normalised_statuses,
                ),
            ),
        )

        return int(
            result.scalar_one(),
        )

    async def get_assessment_total_awarded_marks(
        self,
        assessment_id: int,
        *,
        completed_only: bool = False,
        finalised_only: bool = False,
    ) -> Decimal:
        """
        Return aggregate awarded marks across all scripts in an assessment.

        This is useful for aggregate analytics but is not itself an average.
        """

        self._validate_positive_integer(
            assessment_id,
            "assessment_id",
        )

        statement = (
            select(
                func.coalesce(
                    func.sum(
                        MarkingDecision.mark_awarded,
                    ),
                    Decimal("0"),
                ),
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
            .where(
                AssessmentCandidate.assessment_id == assessment_id,
                MarkingDecision.mark_awarded.is_not(None),
            )
        )

        if finalised_only:
            statement = statement.where(
                MarkingDecision.status == MarkingDecisionStatus.FINALISED,
            )

        elif completed_only:
            statement = statement.where(
                MarkingDecision.status.in_(
                    self.COMPLETED_MARKING_STATUSES,
                ),
            )

        result = await self.db.execute(
            statement,
        )

        return Decimal(
            str(
                result.scalar_one(),
            ),
        )

    # ------------------------------------------------------------------
    # Question-level assessment analytics
    # ------------------------------------------------------------------

    async def get_question_mark_statistics(
        self,
        question_id: int,
        *,
        completed_only: bool = True,
    ) -> dict[str, Decimal | int | None]:
        """
        Return aggregate marking statistics for one question.

        Returned keys:

        - response_count
        - marked_count
        - mark_sum
        - mark_average
        - mark_minimum
        - mark_maximum

        By default only MARKED, REVIEWED, and FINALISED decisions contribute
        to mark statistics.
        """

        self._validate_positive_integer(
            question_id,
            "question_id",
        )

        statement = (
            select(
                func.count(
                    AssessmentResponse.id,
                ).label(
                    "response_count",
                ),
                func.count(
                    MarkingDecision.id,
                ).label(
                    "marked_count",
                ),
                func.coalesce(
                    func.sum(
                        MarkingDecision.mark_awarded,
                    ),
                    Decimal("0"),
                ).label(
                    "mark_sum",
                ),
                func.avg(
                    MarkingDecision.mark_awarded,
                ).label(
                    "mark_average",
                ),
                func.min(
                    MarkingDecision.mark_awarded,
                ).label(
                    "mark_minimum",
                ),
                func.max(
                    MarkingDecision.mark_awarded,
                ).label(
                    "mark_maximum",
                ),
            )
            .select_from(
                AssessmentResponse,
            )
            .outerjoin(
                MarkingDecision,
                MarkingDecision.response_id == AssessmentResponse.id,
            )
            .where(
                AssessmentResponse.question_id == question_id,
                AssessmentResponse.status != AssessmentResponseStatus.VOID,
            )
        )

        if completed_only:
            statement = statement.where(
                (MarkingDecision.id.is_(None))
                | (
                    MarkingDecision.status.in_(
                        self.COMPLETED_MARKING_STATUSES,
                    )
                ),
            )

        result = await self.db.execute(
            statement,
        )

        row = result.one()

        def decimal_or_none(
            value,
        ) -> Decimal | None:
            if value is None:
                return None

            return Decimal(
                str(value),
            )

        return {
            "response_count": int(
                row.response_count or 0,
            ),
            "marked_count": int(
                row.marked_count or 0,
            ),
            "mark_sum": Decimal(
                str(
                    row.mark_sum or 0,
                ),
            ),
            "mark_average": decimal_or_none(
                row.mark_average,
            ),
            "mark_minimum": decimal_or_none(
                row.mark_minimum,
            ),
            "mark_maximum": decimal_or_none(
                row.mark_maximum,
            ),
        }

    async def list_assessment_question_statistics(
        self,
        assessment_id: int,
        *,
        completed_only: bool = True,
    ) -> list[dict[str, object]]:
        """
        Return aggregate statistics for every markable assessment question.
        """

        self._validate_positive_integer(
            assessment_id,
            "assessment_id",
        )

        questions = await self.list_markable_questions(
            assessment_id,
        )

        output: list[dict[str, object]] = []

        for question in questions:
            statistics = await self.get_question_mark_statistics(
                question.id,
                completed_only=completed_only,
            )

            output.append(
                {
                    "question": question,
                    **statistics,
                }
            )

        return output

    # ------------------------------------------------------------------
    # Bulk per-script summary query
    # ------------------------------------------------------------------

    async def list_assessment_script_mark_summaries(
        self,
        assessment_id: int,
    ) -> list[dict[str, object]]:
        """
        Return compact marking aggregates for every script in an assessment.

        This query is intended for result grids and analytics screens where
        loading the entire response graph for every script would be wasteful.
        """

        self._validate_positive_integer(
            assessment_id,
            "assessment_id",
        )

        statement = (
            select(
                AssessmentScript.id.label(
                    "script_id",
                ),
                AssessmentScript.candidate_id.label(
                    "candidate_id",
                ),
                AssessmentScript.version.label(
                    "version",
                ),
                AssessmentScript.status.label(
                    "script_status",
                ),
                func.count(
                    AssessmentResponse.id,
                ).label(
                    "response_count",
                ),
                func.count(
                    MarkingDecision.id,
                ).label(
                    "decision_count",
                ),
                func.coalesce(
                    func.sum(
                        MarkingDecision.mark_awarded,
                    ),
                    Decimal("0"),
                ).label(
                    "mark_awarded",
                ),
                func.sum(
                    case(
                        (
                            MarkingDecision.status.in_(
                                self.COMPLETED_MARKING_STATUSES,
                            ),
                            1,
                        ),
                        else_=0,
                    ),
                ).label(
                    "completed_decision_count",
                ),
                func.sum(
                    case(
                        (
                            MarkingDecision.status == MarkingDecisionStatus.FINALISED,
                            1,
                        ),
                        else_=0,
                    ),
                ).label(
                    "finalised_decision_count",
                ),
            )
            .join(
                AssessmentCandidate,
                AssessmentCandidate.id == AssessmentScript.candidate_id,
            )
            .outerjoin(
                AssessmentResponse,
                AssessmentResponse.script_id == AssessmentScript.id,
            )
            .outerjoin(
                MarkingDecision,
                MarkingDecision.response_id == AssessmentResponse.id,
            )
            .where(
                AssessmentCandidate.assessment_id == assessment_id,
            )
            .group_by(
                AssessmentScript.id,
                AssessmentScript.candidate_id,
                AssessmentScript.version,
                AssessmentScript.status,
            )
            .order_by(
                AssessmentScript.candidate_id.asc(),
                AssessmentScript.version.asc(),
                AssessmentScript.id.asc(),
            )
        )

        result = await self.db.execute(
            statement,
        )

        return [
            {
                "script_id": int(
                    row.script_id,
                ),
                "candidate_id": int(
                    row.candidate_id,
                ),
                "version": int(
                    row.version,
                ),
                "script_status": row.script_status,
                "response_count": int(
                    row.response_count or 0,
                ),
                "decision_count": int(
                    row.decision_count or 0,
                ),
                "mark_awarded": Decimal(
                    str(
                        row.mark_awarded or 0,
                    ),
                ),
                "completed_decision_count": int(
                    row.completed_decision_count or 0,
                ),
                "finalised_decision_count": int(
                    row.finalised_decision_count or 0,
                ),
            }
            for row in result.all()
        ]
