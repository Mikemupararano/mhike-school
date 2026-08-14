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
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
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
    from app.models.assessment_response import (
        AssessmentResponse,
        MarkingDecision,
    )
    from app.models.user import User


class AssessmentModerationReviewStatus(str, Enum):
    """
    Lifecycle state for one script-level moderation review.

    PENDING
        The moderation exercise has been created but has not started.

    IN_PROGRESS
        Moderation work has begun.

    COMPLETED
        The moderation exercise has reached a recorded conclusion.

    CANCELLED
        The moderation exercise was cancelled without completion.
    """

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class AssessmentModerationOutcome(str, Enum):
    """
    Overall conclusion of one moderation review.

    CONFIRMED
        The sampled or reviewed marking was accepted without adjustment.

    ADJUSTED
        One or more marks were changed through moderation.

    RETURNED
        Work was returned for correction or reconsideration.

    ESCALATED
        The review requires further or more senior moderation.

    NO_ACTION
        Quality-assurance review completed without requiring formal action.
    """

    CONFIRMED = "confirmed"
    ADJUSTED = "adjusted"
    RETURNED = "returned"
    ESCALATED = "escalated"
    NO_ACTION = "no_action"


class AssessmentModerationSamplingMethod(str, Enum):
    """
    Describe how work was selected for moderation.

    FULL
        Every available response in the script was reviewed.

    RANDOM_SAMPLE
        Responses were selected using a random sampling process.

    TARGETED
        Responses were deliberately selected because of identified concerns.

    THRESHOLD
        Selection was driven by a mark, grade or other threshold.

    MANUAL
        The moderator or authorised user selected the sample manually.
    """

    FULL = "full"
    RANDOM_SAMPLE = "random_sample"
    TARGETED = "targeted"
    THRESHOLD = "threshold"
    MANUAL = "manual"


class AssessmentModerationItemOutcome(str, Enum):
    """
    Conclusion for one response inspected during moderation.

    CONFIRMED
        The original question-level mark was accepted.

    ADJUSTED
        The question-level mark was changed.

    RETURNED
        The response requires further marking work.

    ESCALATED
        The response requires further or more senior moderation.
    """

    CONFIRMED = "confirmed"
    ADJUSTED = "adjusted"
    RETURNED = "returned"
    ESCALATED = "escalated"


class AssessmentModerationReview(Base):
    """
    Preserve one immutable moderation or quality-assurance exercise.

    The review belongs to one submitted script version.

    ``AssessmentScript.status`` remains the operational workflow state.
    ``MarkingDecision`` remains the current question-level marking result.

    This model records the historical moderation event itself so that later
    changes to marking decisions, comments or result outcomes cannot erase
    evidence of what was reviewed, by whom, and with what conclusion.

    A script may have multiple moderation reviews over its lifetime. This
    supports initial moderation, re-moderation, escalation, later QA sampling
    and audits without overwriting earlier review history.

    Completion does not itself make a candidate result authoritative.
    Candidate-level official result history remains the responsibility of
    ``AssessmentResultOutcome``.
    """

    __tablename__ = "assessment_moderation_reviews"

    __table_args__ = (
        UniqueConstraint(
            "script_id",
            "review_number",
            name="uq_assessment_moderation_review_script_number",
        ),
        CheckConstraint(
            "review_number >= 1",
            name="ck_assessment_moderation_review_number_positive",
        ),
        CheckConstraint(
            (
                "(status = 'completed' AND outcome IS NOT NULL) "
                "OR "
                "(status <> 'completed')"
            ),
            name="ck_assessment_moderation_review_completed_outcome",
        ),
        CheckConstraint(
            (
                "(status = 'cancelled' AND cancelled_at IS NOT NULL) "
                "OR "
                "(status <> 'cancelled')"
            ),
            name="ck_assessment_moderation_review_cancelled_timestamp",
        ),
    )

    # ------------------------------------------------------------------
    # Identity
    # ------------------------------------------------------------------

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    # ------------------------------------------------------------------
    # Tenant and assessment scope
    # ------------------------------------------------------------------

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

    # ------------------------------------------------------------------
    # Review identity and workflow
    # ------------------------------------------------------------------

    review_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    status: Mapped[AssessmentModerationReviewStatus] = mapped_column(
        SqlEnum(
            AssessmentModerationReviewStatus,
            name="assessment_moderation_review_status",
            native_enum=False,
            values_callable=lambda enum_cls: [
                member.value
                for member in enum_cls
            ],
        ),
        nullable=False,
        default=AssessmentModerationReviewStatus.PENDING,
        index=True,
    )

    outcome: Mapped[AssessmentModerationOutcome | None] = mapped_column(
        SqlEnum(
            AssessmentModerationOutcome,
            name="assessment_moderation_outcome",
            native_enum=False,
            values_callable=lambda enum_cls: [
                member.value
                for member in enum_cls
            ],
        ),
        nullable=True,
        index=True,
    )

    sampling_method: Mapped[
        AssessmentModerationSamplingMethod
    ] = mapped_column(
        SqlEnum(
            AssessmentModerationSamplingMethod,
            name="assessment_moderation_sampling_method",
            native_enum=False,
            values_callable=lambda enum_cls: [
                member.value
                for member in enum_cls
            ],
        ),
        nullable=False,
        default=AssessmentModerationSamplingMethod.MANUAL,
        index=True,
    )

    # ------------------------------------------------------------------
    # Moderator and initiation audit
    # ------------------------------------------------------------------

    moderator_id: Mapped[int] = mapped_column(
        ForeignKey(
            "users.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
        index=True,
    )

    initiated_by_id: Mapped[int] = mapped_column(
        ForeignKey(
            "users.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
        index=True,
    )

    # ------------------------------------------------------------------
    # Review metadata
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

    sample_description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # ------------------------------------------------------------------
    # Audit timestamps
    # ------------------------------------------------------------------

    created_at: Mapped[datetime] = mapped_column(
        DateTime(
            timezone=True,
        ),
        nullable=False,
        server_default=func.now(),
    )

    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(
            timezone=True,
        ),
        nullable=True,
    )

    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(
            timezone=True,
        ),
        nullable=True,
    )

    # ------------------------------------------------------------------
    # Cancellation audit
    # ------------------------------------------------------------------

    cancelled_at: Mapped[datetime | None] = mapped_column(
        DateTime(
            timezone=True,
        ),
        nullable=True,
    )

    cancelled_by_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "users.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    cancellation_reason: Mapped[str | None] = mapped_column(
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

    moderator: Mapped[User] = relationship(
        "User",
        foreign_keys=[
            moderator_id,
        ],
        lazy="selectin",
    )

    initiated_by: Mapped[User] = relationship(
        "User",
        foreign_keys=[
            initiated_by_id,
        ],
        lazy="selectin",
    )

    cancelled_by: Mapped[User | None] = relationship(
        "User",
        foreign_keys=[
            cancelled_by_id,
        ],
        lazy="selectin",
    )

    items: Mapped[list[AssessmentModerationItem]] = relationship(
        "AssessmentModerationItem",
        back_populates="review",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="AssessmentModerationItem.id",
    )

    # ------------------------------------------------------------------
    # Convenience properties
    # ------------------------------------------------------------------

    @property
    def is_complete(self) -> bool:
        """
        Return whether the moderation review has reached completion.
        """

        return (
            self.status
            == AssessmentModerationReviewStatus.COMPLETED
        )

    @property
    def is_cancelled(self) -> bool:
        """
        Return whether the moderation review has been cancelled.
        """

        return (
            self.status
            == AssessmentModerationReviewStatus.CANCELLED
        )


class AssessmentModerationItem(Base):
    """
    Preserve moderation evidence for one reviewed assessment response.

    Each row records the mark and marking-decision state seen when moderation
    occurred, together with the resulting moderated state.

    Snapshot values are deliberate. ``MarkingDecision`` is the mutable current
    result, whereas moderation evidence must continue to show what the
    moderator actually inspected even if the live marking decision changes
    later.

    A response may appear only once within a particular moderation review.
    It may appear again in a later review.
    """

    __tablename__ = "assessment_moderation_items"

    __table_args__ = (
        UniqueConstraint(
            "review_id",
            "response_id",
            name="uq_assessment_moderation_item_review_response",
        ),
        CheckConstraint(
            (
                "mark_before_snapshot IS NULL "
                "OR mark_before_snapshot >= 0"
            ),
            name="ck_assessment_moderation_item_mark_before_nonnegative",
        ),
        CheckConstraint(
            (
                "mark_after_snapshot IS NULL "
                "OR mark_after_snapshot >= 0"
            ),
            name="ck_assessment_moderation_item_mark_after_nonnegative",
        ),
        CheckConstraint(
            (
                "maximum_mark_snapshot IS NULL "
                "OR maximum_mark_snapshot >= 0"
            ),
            name="ck_assessment_moderation_item_maximum_nonnegative",
        ),
        CheckConstraint(
            (
                "mark_before_snapshot IS NULL "
                "OR maximum_mark_snapshot IS NULL "
                "OR mark_before_snapshot <= maximum_mark_snapshot"
            ),
            name="ck_assessment_moderation_item_mark_before_within_maximum",
        ),
        CheckConstraint(
            (
                "mark_after_snapshot IS NULL "
                "OR maximum_mark_snapshot IS NULL "
                "OR mark_after_snapshot <= maximum_mark_snapshot"
            ),
            name="ck_assessment_moderation_item_mark_after_within_maximum",
        ),
        CheckConstraint(
            (
                "(mark_changed = true "
                "AND mark_after_snapshot IS NOT NULL) "
                "OR "
                "(mark_changed = false)"
            ),
            name="ck_assessment_moderation_item_changed_mark_present",
        ),
    )

    # ------------------------------------------------------------------
    # Identity
    # ------------------------------------------------------------------

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    # ------------------------------------------------------------------
    # Review scope
    # ------------------------------------------------------------------

    review_id: Mapped[int] = mapped_column(
        ForeignKey(
            "assessment_moderation_reviews.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    response_id: Mapped[int] = mapped_column(
        ForeignKey(
            "assessment_responses.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
        index=True,
    )

    marking_decision_id: Mapped[int] = mapped_column(
        ForeignKey(
            "marking_decisions.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
        index=True,
    )

    # ------------------------------------------------------------------
    # Moderation conclusion
    # ------------------------------------------------------------------

    outcome: Mapped[AssessmentModerationItemOutcome] = mapped_column(
        SqlEnum(
            AssessmentModerationItemOutcome,
            name="assessment_moderation_item_outcome",
            native_enum=False,
            values_callable=lambda enum_cls: [
                member.value
                for member in enum_cls
            ],
        ),
        nullable=False,
        index=True,
    )

    # ------------------------------------------------------------------
    # Mark snapshots
    # ------------------------------------------------------------------

    mark_before_snapshot: Mapped[Decimal | None] = mapped_column(
        Numeric(
            8,
            2,
        ),
        nullable=True,
    )

    mark_after_snapshot: Mapped[Decimal | None] = mapped_column(
        Numeric(
            8,
            2,
        ),
        nullable=True,
    )

    maximum_mark_snapshot: Mapped[Decimal | None] = mapped_column(
        Numeric(
            8,
            2,
        ),
        nullable=True,
    )

    mark_changed: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        index=True,
    )

    # ------------------------------------------------------------------
    # Marking-decision status snapshots
    # ------------------------------------------------------------------

    decision_status_before_snapshot: Mapped[str | None] = mapped_column(
        String(
            50,
        ),
        nullable=True,
    )

    decision_status_after_snapshot: Mapped[str | None] = mapped_column(
        String(
            50,
        ),
        nullable=True,
    )

    # ------------------------------------------------------------------
    # Moderation evidence
    # ------------------------------------------------------------------

    moderator_comment: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    evidence_notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # ------------------------------------------------------------------
    # Per-item reviewer audit
    #
    # This is intentionally stored even though the parent review has a
    # moderator. It permits future team moderation and escalation without
    # losing the identity of the person who reviewed this specific item.
    # ------------------------------------------------------------------

    reviewed_by_id: Mapped[int] = mapped_column(
        ForeignKey(
            "users.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
        index=True,
    )

    reviewed_at: Mapped[datetime] = mapped_column(
        DateTime(
            timezone=True,
        ),
        nullable=False,
        server_default=func.now(),
    )

    # ------------------------------------------------------------------
    # Relationships
    # ------------------------------------------------------------------

    review: Mapped[AssessmentModerationReview] = relationship(
        "AssessmentModerationReview",
        back_populates="items",
        foreign_keys=[
            review_id,
        ],
        lazy="selectin",
    )

    response: Mapped[AssessmentResponse] = relationship(
        "AssessmentResponse",
        foreign_keys=[
            response_id,
        ],
        lazy="selectin",
    )

    marking_decision: Mapped[MarkingDecision] = relationship(
        "MarkingDecision",
        foreign_keys=[
            marking_decision_id,
        ],
        lazy="selectin",
    )

    reviewed_by: Mapped[User] = relationship(
        "User",
        foreign_keys=[
            reviewed_by_id,
        ],
        lazy="selectin",
    )