from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

AssessmentResultChangeTypeValue = Literal[
    "initial",
    "retake",
    "remark",
    "correction",
    "moderation",
    "administrative",
]

AssessmentResultOutcomeStatusValue = Literal[
    "draft",
    "authoritative",
    "superseded",
    "withdrawn",
]


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------


class AssessmentResultOutcomeCreate(BaseModel):
    """
    Create a new immutable result snapshot.

    ``make_authoritative`` controls whether the new outcome remains a draft
    or immediately becomes the candidate's official result.
    """

    script_id: int = Field(
        ge=1,
    )

    change_type: AssessmentResultChangeTypeValue

    reason: str | None = None

    notes: str | None = None

    effective_at: datetime | None = None

    make_authoritative: bool = False


# ---------------------------------------------------------------------------
# Draft PATCH
# ---------------------------------------------------------------------------


class AssessmentResultOutcomeUpdate(BaseModel):
    """
    PATCH metadata on a draft result outcome.

    Result snapshot fields themselves are deliberately immutable.

    Omitted fields remain unchanged.
    Explicit null clears nullable metadata where business rules allow it.
    """

    reason: str | None = None

    notes: str | None = None

    effective_at: datetime | None = None


# ---------------------------------------------------------------------------
# Withdrawal
# ---------------------------------------------------------------------------


class AssessmentResultOutcomeWithdraw(BaseModel):
    """
    Withdraw a historical result outcome.
    """

    withdrawal_reason: str = Field(
        min_length=1,
    )


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------


class AssessmentResultOutcomeOut(BaseModel):
    """
    Complete historical assessment-result outcome.
    """

    model_config = ConfigDict(
        from_attributes=True,
    )

    id: int

    school_id: int

    assessment_id: int

    candidate_id: int

    script_id: int

    version: int

    status: AssessmentResultOutcomeStatusValue

    change_type: AssessmentResultChangeTypeValue

    supersedes_id: int | None = None

    is_authoritative: bool

    # ------------------------------------------------------------------
    # Result snapshot
    # ------------------------------------------------------------------

    mark_awarded_snapshot: Decimal

    maximum_mark_snapshot: Decimal

    percentage_snapshot: Decimal | None = None

    # ------------------------------------------------------------------
    # Grading snapshot
    # ------------------------------------------------------------------

    grading_scheme_id_snapshot: int | None = None

    grading_scheme_name_snapshot: str | None = None

    grading_basis_snapshot: str | None = None

    grade_boundary_id_snapshot: int | None = None

    grade_label_snapshot: str | None = None

    grade_points_snapshot: Decimal | None = None

    is_pass_snapshot: bool | None = None

    # ------------------------------------------------------------------
    # Script / reason metadata
    # ------------------------------------------------------------------

    script_version_snapshot: int

    reason: str | None = None

    notes: str | None = None

    # ------------------------------------------------------------------
    # Authority audit
    # ------------------------------------------------------------------

    effective_at: datetime

    recorded_by_id: int

    recorded_by_name: str | None = None

    recorded_at: datetime

    # ------------------------------------------------------------------
    # Withdrawal audit
    # ------------------------------------------------------------------

    withdrawn_at: datetime | None = None

    withdrawn_by_id: int | None = None

    withdrawn_by_name: str | None = None

    withdrawal_reason: str | None = None


# ---------------------------------------------------------------------------
# Candidate history
# ---------------------------------------------------------------------------


class AssessmentResultOutcomeHistoryOut(BaseModel):
    """
    Full result history for one assessment candidate.
    """

    candidate_id: int

    outcome_count: int

    authoritative_outcome_id: int | None = None

    outcomes: list[AssessmentResultOutcomeOut] = Field(
        default_factory=list,
    )


# ---------------------------------------------------------------------------
# Compact current-authoritative representation
# ---------------------------------------------------------------------------


class AuthoritativeAssessmentResultOut(BaseModel):
    """
    Compact authoritative-result view.

    Useful later for dashboards, published-result integration and analytics.
    """

    outcome_id: int

    candidate_id: int

    assessment_id: int

    script_id: int

    script_version: int

    outcome_version: int

    change_type: AssessmentResultChangeTypeValue

    mark_awarded: Decimal

    maximum_mark: Decimal

    percentage: Decimal | None = None

    grade_label: str | None = None

    grade_points: Decimal | None = None

    is_pass: bool | None = None

    effective_at: datetime
