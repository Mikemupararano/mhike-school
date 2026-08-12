from __future__ import annotations

from decimal import Decimal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
)

from app.models.assessment import AssessmentStatus
from app.models.assessment_candidate import (
    AssessmentCandidateStatus,
    AssessmentScriptStatus,
)
from app.models.assessment_response import (
    AssessmentResponseStatus,
    MarkingDecisionStatus,
)

# ---------------------------------------------------------------------------
# Question-level result schemas
# ---------------------------------------------------------------------------


class AssessmentQuestionResultOut(BaseModel):
    """
    Derived result for one markable assessment question within one script.

    ``mark_awarded`` is sourced from the authoritative question-level
    MarkingDecision when one exists.

    A question remains present even when no response or marking decision
    exists so incomplete assessment work can be represented explicitly.
    """

    model_config = ConfigDict(
        from_attributes=True,
    )

    question_id: int
    question_number: str

    title: str | None = None

    maximum_mark: Decimal

    response_id: int | None = None
    response_status: AssessmentResponseStatus | None = None

    decision_id: int | None = None
    decision_status: MarkingDecisionStatus | None = None

    mark_awarded: Decimal | None = None
    percentage: Decimal | None = None

    is_marked: bool
    is_finalised: bool


# ---------------------------------------------------------------------------
# Script result schemas
# ---------------------------------------------------------------------------


class AssessmentScriptResultOut(BaseModel):
    """
    Complete derived result for one assessment script version.

    Three awarded-mark totals are exposed deliberately:

    ``mark_awarded``
        Includes every non-null question-level mark, including provisional
        in-progress marking.

    ``completed_mark_awarded``
        Includes MARKED, REVIEWED and FINALISED question decisions.

    ``finalised_mark_awarded``
        Includes FINALISED question decisions only.
    """

    model_config = ConfigDict(
        from_attributes=True,
    )

    assessment_id: int
    candidate_id: int
    student_id: int

    script_id: int
    script_version: int
    script_status: AssessmentScriptStatus

    maximum_mark: Decimal

    mark_awarded: Decimal
    completed_mark_awarded: Decimal
    finalised_mark_awarded: Decimal

    percentage: Decimal | None = None
    completed_percentage: Decimal | None = None
    finalised_percentage: Decimal | None = None

    markable_question_count: int = Field(
        ge=0,
    )

    response_count: int = Field(
        ge=0,
    )

    submitted_response_count: int = Field(
        ge=0,
    )

    decision_count: int = Field(
        ge=0,
    )

    marked_question_count: int = Field(
        ge=0,
    )

    finalised_question_count: int = Field(
        ge=0,
    )

    response_completion_percentage: Decimal | None = None
    marking_completion_percentage: Decimal | None = None
    finalisation_completion_percentage: Decimal | None = None

    is_fully_responded: bool
    is_fully_marked: bool
    is_fully_finalised: bool

    questions: list[AssessmentQuestionResultOut] = Field(
        default_factory=list,
    )


# ---------------------------------------------------------------------------
# Candidate result schemas
# ---------------------------------------------------------------------------


class AssessmentCandidateResultOut(BaseModel):
    """
    Derived results for one assessment candidate.

    All script versions remain visible. ``latest_script_result`` is a
    convenience view of the highest script version and does not discard
    earlier versions.
    """

    model_config = ConfigDict(
        from_attributes=True,
    )

    assessment_id: int

    candidate_id: int
    student_id: int

    candidate_number: str | None = None
    candidate_status: AssessmentCandidateStatus

    script_count: int = Field(
        ge=0,
    )

    scripts: list[AssessmentScriptResultOut] = Field(
        default_factory=list,
    )

    latest_script_result: AssessmentScriptResultOut | None = None


# ---------------------------------------------------------------------------
# Assessment result-grid schemas
# ---------------------------------------------------------------------------


class AssessmentResultGridScriptOut(BaseModel):
    """
    Compact script result used by assessment result-grid views.
    """

    model_config = ConfigDict(
        from_attributes=True,
    )

    script_id: int
    candidate_id: int

    version: int = Field(
        ge=1,
    )

    script_status: AssessmentScriptStatus

    response_count: int = Field(
        ge=0,
    )

    decision_count: int = Field(
        ge=0,
    )

    mark_awarded: Decimal
    maximum_mark: Decimal

    percentage: Decimal | None = None

    completed_decision_count: int = Field(
        ge=0,
    )

    finalised_decision_count: int = Field(
        ge=0,
    )

    marking_completion_percentage: Decimal | None = None
    finalisation_completion_percentage: Decimal | None = None

    is_fully_marked: bool
    is_fully_finalised: bool


class AssessmentResultGridOut(BaseModel):
    """
    Compact script-level result grid for one assessment.
    """

    model_config = ConfigDict(
        from_attributes=True,
    )

    assessment_id: int
    title: str
    status: AssessmentStatus

    maximum_mark: Decimal

    markable_question_count: int = Field(
        ge=0,
    )

    script_count: int = Field(
        ge=0,
    )

    scripts: list[AssessmentResultGridScriptOut] = Field(
        default_factory=list,
    )


# ---------------------------------------------------------------------------
# Assessment-wide summary schemas
# ---------------------------------------------------------------------------


class AssessmentResultsSummaryOut(BaseModel):
    """
    Assessment-wide derived marking and completion summary.

    Aggregate awarded marks are intentionally totals rather than candidate
    averages because multiple script versions remain valid historical
    records in the current assessment design.
    """

    model_config = ConfigDict(
        from_attributes=True,
    )

    assessment_id: int
    title: str
    status: AssessmentStatus

    maximum_mark: Decimal

    markable_question_count: int = Field(
        ge=0,
    )

    candidate_count: int = Field(
        ge=0,
    )

    script_count: int = Field(
        ge=0,
    )

    expected_question_decisions: int = Field(
        ge=0,
    )

    completed_decision_count: int = Field(
        ge=0,
    )

    finalised_decision_count: int = Field(
        ge=0,
    )

    marking_completion_percentage: Decimal | None = None
    finalisation_completion_percentage: Decimal | None = None

    total_awarded_marks: Decimal
    completed_awarded_marks: Decimal
    finalised_awarded_marks: Decimal


# ---------------------------------------------------------------------------
# Question-level analysis / QLA schemas
# ---------------------------------------------------------------------------


class AssessmentQuestionAnalysisOut(BaseModel):
    """
    Question-level analysis for one markable assessment question.
    """

    model_config = ConfigDict(
        from_attributes=True,
    )

    question_id: int
    question_number: str

    title: str | None = None

    maximum_mark: Decimal

    response_count: int = Field(
        ge=0,
    )

    marked_count: int = Field(
        ge=0,
    )

    mark_sum: Decimal

    mark_average: Decimal | None = None
    mark_minimum: Decimal | None = None
    mark_maximum: Decimal | None = None

    average_percentage: Decimal | None = None
    marking_completion_percentage: Decimal | None = None


class AssessmentQuestionAnalysisListOut(BaseModel):
    """
    Container for assessment question-level analysis results.
    """

    model_config = ConfigDict(
        from_attributes=True,
    )

    assessment_id: int

    completed_only: bool = True

    questions: list[AssessmentQuestionAnalysisOut] = Field(
        default_factory=list,
    )
