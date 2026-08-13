from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import (
    BaseModel,
    ConfigDict,
)

# ---------------------------------------------------------------------------
# Scope
# ---------------------------------------------------------------------------


class AssessmentCohortPerformanceScopeOut(BaseModel):
    """
    Filters and scope applied to comparative assessment performance.
    """

    school_id: int | None = None
    course_id: int | None = None
    subject_id: int | None = None
    teacher_id: int | None = None

    academic_year: str | None = None
    term: str | None = None


# ---------------------------------------------------------------------------
# Grade distribution
# ---------------------------------------------------------------------------


class AssessmentCohortGradeDistributionItemOut(BaseModel):
    """
    One grade-label bucket aggregated across multiple assessments.

    Boundary metadata is intentionally not included because different
    assessments may use different grading schemes and thresholds.
    """

    grade: str
    count: int
    percentage: Decimal | None = None


# ---------------------------------------------------------------------------
# Assessment comparison row
# ---------------------------------------------------------------------------


class AssessmentCohortAssessmentOut(BaseModel):
    """
    Compact comparative performance row for one assessment.
    """

    model_config = ConfigDict(
        extra="allow",
    )

    assessment_id: int
    assessment_title: str
    assessment_type: str | None = None

    academic_year: str | None = None
    term: str | None = None
    scheduled_at: datetime | None = None

    course_id: int
    course_title: str | None = None

    teacher_id: int | None = None

    subject_id: int | None = None
    subject_name: str | None = None

    candidate_count: int
    included_candidate_count: int
    excluded_incomplete_candidate_count: int

    mean_percentage: Decimal | None = None
    median_percentage: Decimal | None = None
    lowest_percentage: Decimal | None = None
    highest_percentage: Decimal | None = None

    graded_candidate_count: int
    ungraded_candidate_count: int

    pass_count: int
    fail_count: int
    pass_percentage: Decimal | None = None


# ---------------------------------------------------------------------------
# Main comparative payload
# ---------------------------------------------------------------------------


class AssessmentCohortPerformanceOut(BaseModel):
    """
    Comparative formal assessment performance across multiple assessments.

    Candidate statistics are derived from each assessment's existing formal
    analytics, using latest fully-finalised script results only.
    """

    scope: AssessmentCohortPerformanceScopeOut

    result_stage: str
    script_selection: str

    selected_assessment_count: int
    assessments_with_results: int
    assessments_without_results: int

    candidate_allocation_count: int
    included_result_count: int
    excluded_incomplete_result_count: int

    unique_student_count: int

    candidate_inclusion_percentage: Decimal | None = None

    mean_percentage: Decimal | None = None
    median_percentage: Decimal | None = None
    lowest_percentage: Decimal | None = None
    highest_percentage: Decimal | None = None

    graded_result_count: int
    ungraded_result_count: int

    pass_count: int
    fail_count: int
    pass_percentage: Decimal | None = None

    grade_distribution: list[AssessmentCohortGradeDistributionItemOut]

    assessments: list[AssessmentCohortAssessmentOut]
