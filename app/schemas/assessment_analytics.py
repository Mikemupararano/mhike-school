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

    This mirrors the existing assessment-results question-analysis service
    rather than introducing a second question-statistics contract.
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
    One grade bucket in an assessment grade distribution.
    """

    grade: str

    minimum_value: Decimal | None = None
    grade_points: Decimal | None = None
    is_pass: bool | None = None

    count: int
    percentage: Decimal | None = None


class AssessmentGradeDistributionOut(BaseModel):
    """
    Compact grade-distribution view for one assessment.
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
    One candidate's formal analytics row.

    The analytics service uses the candidate's latest script version and
    includes the row only when that latest script is fully finalised.
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
    Compact cohort analytics suitable for dashboards and list views.
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

    The cohort statistics use latest fully-finalised candidate scripts only.
    Earlier script versions remain available through the assessment-results
    subsystem but do not contribute simultaneously to formal analytics.
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
