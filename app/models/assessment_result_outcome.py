from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum as SqlEnum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.assessment import Assessment
    from app.models.assessment_candidate import (
        AssessmentCandidate,
        AssessmentScript,
    )
    from app.models.user import User


class AssessmentResultChangeType(str, Enum):
    INITIAL = "initial"
    RETAKE = "retake"
    REMARK = "remark"
    CORRECTION = "correction"
    MODERATION = "moderation"
    ADMINISTRATIVE = "administrative"


class AssessmentResultOutcomeStatus(str, Enum):
    DRAFT = "draft"
    AUTHORITATIVE = "authoritative"
    SUPERSEDED = "superseded"
    WITHDRAWN = "withdrawn"


class AssessmentResultOutcome(Base):
    """
    Immutable historical snapshot of an assessment candidate's result.

    Assessment scripts represent versions of submitted work.

    Assessment result outcomes represent versions of the official result
    decision made from that work.

    A candidate may therefore have multiple scripts and multiple result
    outcomes, but at most one outcome may be authoritative at any moment.

    Historical result values are snapshotted deliberately so later changes to
    marks, grading schemes, grade boundaries or grading configuration cannot
    rewrite previously recorded official results.
    """

    __tablename__ = "assessment_result_outcomes"

    __table_args__ = (
        UniqueConstraint(
            "candidate_id",
            "version",
            name="uq_assessment_result_outcome_candidate_version",
        ),
        CheckConstraint(
            "version >= 1",
            name="ck_assessment_result_outcome_version_positive",
        ),
        CheckConstraint(
            "mark_awarded_snapshot >= 0",
            name="ck_assessment_result_outcome_mark_nonnegative",
        ),
        CheckConstraint(
            "maximum_mark_snapshot >= 0",
            name="ck_assessment_result_outcome_maximum_nonnegative",
        ),
        CheckConstraint(
            (
                "percentage_snapshot IS NULL "
                "OR "
                "("
                "percentage_snapshot >= 0 "
                "AND percentage_snapshot <= 100"
                ")"
            ),
            name="ck_assessment_result_outcome_percentage_range",
        ),
        CheckConstraint(
            ("grade_points_snapshot IS NULL " "OR grade_points_snapshot >= 0"),
            name="ck_assessment_result_outcome_grade_points_nonnegative",
        ),
        CheckConstraint(
            (
                "(status = 'authoritative' "
                "AND is_authoritative = true) "
                "OR "
                "(status <> 'authoritative' "
                "AND is_authoritative = false)"
            ),
            name=("ck_assessment_result_outcome_" "authority_status_consistency"),
        ),
        Index(
            "ix_assessment_result_outcome_one_authoritative_candidate",
            "candidate_id",
            unique=True,
            postgresql_where=text(
                "is_authoritative = true",
            ),
            sqlite_where=text(
                "is_authoritative = 1",
            ),
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    school_id: Mapped[int] = mapped_column(
        ForeignKey(
            "schools.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    assessment_id: Mapped[int] = mapped_column(
        ForeignKey(
            "assessments.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    candidate_id: Mapped[int] = mapped_column(
        ForeignKey(
            "assessment_candidates.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    script_id: Mapped[int] = mapped_column(
        ForeignKey(
            "assessment_scripts.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
        index=True,
    )

    version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    status: Mapped[AssessmentResultOutcomeStatus] = mapped_column(
        SqlEnum(
            AssessmentResultOutcomeStatus,
            name="assessment_result_outcome_status",
            native_enum=False,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
        default=AssessmentResultOutcomeStatus.DRAFT,
        index=True,
    )

    change_type: Mapped[AssessmentResultChangeType] = mapped_column(
        SqlEnum(
            AssessmentResultChangeType,
            name="assessment_result_change_type",
            native_enum=False,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
        index=True,
    )

    supersedes_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "assessment_result_outcomes.id",
            ondelete="RESTRICT",
        ),
        nullable=True,
        index=True,
    )

    is_authoritative: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        index=True,
    )

    # ------------------------------------------------------------------
    # Result snapshot
    # ------------------------------------------------------------------

    mark_awarded_snapshot: Mapped[Decimal] = mapped_column(
        Numeric(
            10,
            2,
        ),
        nullable=False,
    )

    maximum_mark_snapshot: Mapped[Decimal] = mapped_column(
        Numeric(
            10,
            2,
        ),
        nullable=False,
    )

    percentage_snapshot: Mapped[Decimal | None] = mapped_column(
        Numeric(
            7,
            2,
        ),
        nullable=True,
    )

    # ------------------------------------------------------------------
    # Grading snapshot
    #
    # These identifiers are intentionally not foreign keys.
    #
    # Historical outcomes must remain meaningful even if grading
    # configuration or boundaries are later changed or removed.
    # ------------------------------------------------------------------

    grading_scheme_id_snapshot: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    grading_scheme_name_snapshot: Mapped[str | None] = mapped_column(
        String(
            255,
        ),
        nullable=True,
    )

    grading_basis_snapshot: Mapped[str | None] = mapped_column(
        String(
            50,
        ),
        nullable=True,
    )

    grade_boundary_id_snapshot: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    grade_label_snapshot: Mapped[str | None] = mapped_column(
        String(
            50,
        ),
        nullable=True,
    )

    grade_points_snapshot: Mapped[Decimal | None] = mapped_column(
        Numeric(
            8,
            2,
        ),
        nullable=True,
    )

    is_pass_snapshot: Mapped[bool | None] = mapped_column(
        Boolean,
        nullable=True,
    )

    # ------------------------------------------------------------------
    # Script snapshot
    # ------------------------------------------------------------------

    script_version_snapshot: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    # ------------------------------------------------------------------
    # Change metadata
    # ------------------------------------------------------------------

    reason: Mapped[str | None] = mapped_column(
        String(
            1000,
        ),
        nullable=True,
    )

    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    effective_at: Mapped[datetime] = mapped_column(
        DateTime(
            timezone=True,
        ),
        nullable=False,
    )

    # ------------------------------------------------------------------
    # Recording audit
    # ------------------------------------------------------------------

    recorded_by_id: Mapped[int] = mapped_column(
        ForeignKey(
            "users.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
        index=True,
    )

    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(
            timezone=True,
        ),
        nullable=False,
        server_default=func.now(),
    )

    # ------------------------------------------------------------------
    # Withdrawal audit
    # ------------------------------------------------------------------

    withdrawn_at: Mapped[datetime | None] = mapped_column(
        DateTime(
            timezone=True,
        ),
        nullable=True,
    )

    withdrawn_by_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "users.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    withdrawal_reason: Mapped[str | None] = mapped_column(
        String(
            1000,
        ),
        nullable=True,
    )

    # ------------------------------------------------------------------
    # Relationships
    # ------------------------------------------------------------------

    assessment: Mapped[Assessment] = relationship(
        "Assessment",
        lazy="selectin",
    )

    candidate: Mapped[AssessmentCandidate] = relationship(
        "AssessmentCandidate",
        lazy="selectin",
    )

    script: Mapped[AssessmentScript] = relationship(
        "AssessmentScript",
        lazy="selectin",
    )

    recorded_by: Mapped[User] = relationship(
        "User",
        foreign_keys=[
            recorded_by_id,
        ],
        lazy="selectin",
    )

    withdrawn_by: Mapped[User | None] = relationship(
        "User",
        foreign_keys=[
            withdrawn_by_id,
        ],
        lazy="selectin",
    )

    supersedes: Mapped[AssessmentResultOutcome | None] = relationship(
        "AssessmentResultOutcome",
        remote_side=[
            id,
        ],
        foreign_keys=[
            supersedes_id,
        ],
        lazy="selectin",
    )

    @property
    def is_current(self) -> bool:
        """
        Return whether this row is the candidate's current official outcome.
        """

        return (
            self.status == AssessmentResultOutcomeStatus.AUTHORITATIVE
            and self.is_authoritative
        )
