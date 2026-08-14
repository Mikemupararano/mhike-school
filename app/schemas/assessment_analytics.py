from __future__ import annotations

from decimal import Decimal
from typing import Any

from pydantic import (
    BaseModel,
    ConfigDict,
)

# ---------------------------------------------------------------------------
# Question analytics
# ---------------------------------------------------------------------------


class AssessmentQuestionAnalyticsOut(BaseModel):
    """
    Question-level assessment performance analytics.

    These values currently describe the live/current marking dataset.

    Candidate-level formal analytics are sourced from authoritative result
    outcomes, while immutable question-level historical snapshots are not yet
    part of AssessmentResultOutcome.
    """

    model_config = ConfigDict(
        extra="allow",
    )

    question_id: int
    question_number: str | None = None
    title: str | None = None

    maximum_mark: Decimal

    response_count: int
    marked_count: int

    mark_sum: Decimal

    mark_average: Decimal | None = None
    mark_minimum: Decimal | None = None
    mark_maximum: Decimal | None = None

    average_percentage: Decimal | None = None


# ---------------------------------------------------------------------------
# Grade distribution
# ---------------------------------------------------------------------------


class AssessmentGradeDistributionItemOut(BaseModel):
    """
    One authoritative grade bucket in an assessment grade distribution.

    Grade labels, points and pass/fail values come from immutable
    AssessmentResultOutcome snapshots.

    ``minimum_value`` remains optional because the historical boundary minimum
    is not currently snapshotted in AssessmentResultOutcome.
    """

    grade: str

    minimum_value: Decimal | None = None
    grade_points: Decimal | None = None
    is_pass: bool | None = None

    count: int
    percentage: Decimal | None = None


class AssessmentGradeDistributionOut(BaseModel):
    """
    Compact authoritative grade-distribution view for one assessment.
    """

    assessment_id: int

    graded_candidate_count: int
    ungraded_candidate_count: int

    pass_count: int
    fail_count: int

    pass_percentage: Decimal | None = None

    grades: list[AssessmentGradeDistributionItemOut]


# ---------------------------------------------------------------------------
# Candidate ranking
# ---------------------------------------------------------------------------


class AssessmentCandidateRankingOut(BaseModel):
    """
    One candidate's formal authoritative analytics row.

    Marks, percentages, grades and official script identity come from the
    candidate's current authoritative AssessmentResultOutcome.

    A newer script, retake, remark or correction does not alter this row until
    its corresponding result outcome becomes authoritative.
    """

    candidate_id: int
    student_id: int

    candidate_number: str | None = None
    candidate_status: str | None = None

    script_id: int | None = None
    script_version: int | None = None

    mark_awarded: Decimal
    maximum_mark: Decimal | None = None
    percentage: Decimal

    grade: str | None = None
    grade_points: Decimal | None = None
    is_pass: bool | None = None

    rank: int


# ---------------------------------------------------------------------------
# Compact summary
# ---------------------------------------------------------------------------


class AssessmentAnalyticsSummaryOut(BaseModel):
    """
    Compact authoritative cohort analytics suitable for dashboards and lists.

    Formal result statistics use authoritative AssessmentResultOutcome
    snapshots.

    Current marking-completion counters remain operational metrics and may
    therefore describe a newer script than the official authoritative result.
    """

    assessment_id: int
    title: str
    status: str

    result_stage: str
    script_selection: str

    maximum_mark: Decimal | None = None
    markable_question_count: int

    candidate_count: int
    script_count: int

    candidates_with_script: int
    candidates_without_script: int

    fully_marked_candidate_count: int
    fully_finalised_candidate_count: int

    included_candidate_count: int
    excluded_incomplete_candidate_count: int

    candidates_without_authoritative_result: int

    candidate_inclusion_percentage: Decimal | None = None

    marking_completion_percentage: Decimal | None = None
    finalisation_completion_percentage: Decimal | None = None

    mean_mark: Decimal | None = None
    median_mark: Decimal | None = None
    lowest_mark: Decimal | None = None
    highest_mark: Decimal | None = None

    mean_percentage: Decimal | None = None
    median_percentage: Decimal | None = None
    lowest_percentage: Decimal | None = None
    highest_percentage: Decimal | None = None

    graded_candidate_count: int
    ungraded_candidate_count: int

    pass_count: int
    fail_count: int

    pass_percentage: Decimal | None = None

    grade_distribution: list[AssessmentGradeDistributionItemOut]


# ---------------------------------------------------------------------------
# Full analytics
# ---------------------------------------------------------------------------


class AssessmentAnalyticsOut(
    AssessmentAnalyticsSummaryOut,
):
    """
    Full assessment analytics payload.

    Candidate-level formal statistics use authoritative result outcomes.

    Latest scripts continue to inform operational completion metrics, while
    question-level analytics currently describe the live/current marking
    dataset until immutable question-level result history is introduced.
    """

    ranking: list[AssessmentCandidateRankingOut]

    questions: list[AssessmentQuestionAnalyticsOut]


# ---------------------------------------------------------------------------
# Generic compatibility model
# ---------------------------------------------------------------------------


class AssessmentAnalyticsRawOut(BaseModel):
    """
    Flexible analytics representation for diagnostic or transitional use.

    This is intentionally not used by the primary API endpoints but gives
    internal callers a validation option when analytics are expanded with
    additional fields in future.
    """

    model_config = ConfigDict(
        extra="allow",
    )

    assessment_id: int

    data: (
        dict[
            str,
            Any,
        ]
        | None
    ) = None
