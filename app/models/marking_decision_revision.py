from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum as SqlEnum,
    ForeignKey,
    Integer,
    Numeric,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)
from sqlalchemy.sql import func

from app.db.base import Base
from app.models.assessment_response import MarkingDecisionStatus

if TYPE_CHECKING:
    from app.models.assessment_response import (
        AssessmentResponse,
        MarkingDecision,
    )
    from app.models.user import User


class MarkingDecisionRevisionChangeType(str, Enum):
    """
    Authoritative marking action that produced one immutable revision.

    UPDATED
        Mark or marker comment changed through normal editing.

    INSTANT_MARKED
        Examiner quick-mark action awarded the question mark and completed
        primary marking atomically.

    STARTED
        Primary marking entered active marking.

    MARKED
        Primary marking was completed through the normal lifecycle.

    REVIEWED
        A completed marking decision was reviewed through the normal
        review workflow.

    MODERATED
        A completed marking decision was confirmed or adjusted through
        the formal moderation workflow.

    FINALISED
        The reviewed/marked decision became final.
    """

    UPDATED = "updated"
    INSTANT_MARKED = "instant_marked"
    STARTED = "started"
    MARKED = "marked"
    REVIEWED = "reviewed"
    MODERATED = "moderated"
    FINALISED = "finalised"


class MarkingDecisionRevisionSource(str, Enum):
    """
    Origin of the authoritative marking mutation.

    MANUAL
        Standard marker or administrative review workflow.

    MODERATION
        Formal moderation workflow that confirms or adjusts completed
        primary marking.

    QUICK_MARK
        Examiner-style one-click or keyboard marking.

    AUTOMATED
        Reserved for deterministic automated marking.

    AI
        Reserved for future AI-assisted marking decisions.
    """

    MANUAL = "manual"
    MODERATION = "moderation"
    QUICK_MARK = "quick_mark"
    AUTOMATED = "automated"
    AI = "ai"


class MarkingDecisionRevision(Base):
    """
    Immutable snapshot of one historical MarkingDecision state.

    The live ``MarkingDecision`` row remains the authoritative current state.
    Each meaningful mutation appends one revision containing the complete
    resulting state, allowing any historical marking decision to be inspected
    without replaying a chain of deltas.

    Revision rows are append-only. They must never be updated in place.

    ``marking_decision_id`` and ``response_id`` use RESTRICT deletion so an
    established marking audit trail cannot be removed accidentally through
    database cascades.
    """

    __tablename__ = "marking_decision_revisions"

    __table_args__ = (
        UniqueConstraint(
            "marking_decision_id",
            "revision",
            name="uq_marking_decision_revision_number",
        ),
        CheckConstraint(
            "revision >= 1",
            name="ck_marking_decision_revision_positive",
        ),
    )

    # ------------------------------------------------------------------
    # Identity and provenance
    # ------------------------------------------------------------------

    id: Mapped[int] = mapped_column(
        primary_key=True,
    )

    marking_decision_id: Mapped[int] = mapped_column(
        ForeignKey(
            "marking_decisions.id",
            ondelete="RESTRICT",
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

    revision: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    changed_by_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "users.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    change_type: Mapped[MarkingDecisionRevisionChangeType] = mapped_column(
        SqlEnum(
            MarkingDecisionRevisionChangeType,
            name="marking_decision_revision_change_type",
            values_callable=lambda enum_cls: [
                value.value
                for value in enum_cls
            ],
            native_enum=False,
            validate_strings=True,
        ),
        nullable=False,
        index=True,
    )

    source: Mapped[MarkingDecisionRevisionSource] = mapped_column(
        SqlEnum(
            MarkingDecisionRevisionSource,
            name="marking_decision_revision_source",
            values_callable=lambda enum_cls: [
                value.value
                for value in enum_cls
            ],
            native_enum=False,
            validate_strings=True,
        ),
        nullable=False,
        index=True,
    )

    # ------------------------------------------------------------------
    # Complete authoritative state snapshot
    # ------------------------------------------------------------------

    marker_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "users.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    status: Mapped[MarkingDecisionStatus] = mapped_column(
        SqlEnum(
            MarkingDecisionStatus,
            name="marking_decision_revision_status",
            values_callable=lambda enum_cls: [
                value.value
                for value in enum_cls
            ],
            native_enum=False,
            validate_strings=True,
        ),
        nullable=False,
        index=True,
    )

    mark_awarded: Mapped[Decimal | None] = mapped_column(
        Numeric(
            precision=8,
            scale=2,
        ),
        nullable=True,
    )

    marker_comment: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    moderation_comment: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    marked_at: Mapped[datetime | None] = mapped_column(
        DateTime(
            timezone=True,
        ),
        nullable=True,
    )

    reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(
            timezone=True,
        ),
        nullable=True,
    )

    finalised_at: Mapped[datetime | None] = mapped_column(
        DateTime(
            timezone=True,
        ),
        nullable=True,
    )

    # ------------------------------------------------------------------
    # Audit timestamp
    # ------------------------------------------------------------------

    created_at: Mapped[datetime] = mapped_column(
        DateTime(
            timezone=True,
        ),
        server_default=func.now(),
        nullable=False,
        index=True,
    )

    # ------------------------------------------------------------------
    # Relationships
    # ------------------------------------------------------------------

    marking_decision: Mapped["MarkingDecision"] = relationship(
        "MarkingDecision",
        back_populates="revisions",
        foreign_keys=[marking_decision_id],
        lazy="selectin",
    )

    response: Mapped["AssessmentResponse"] = relationship(
        "AssessmentResponse",
        foreign_keys=[response_id],
        lazy="selectin",
    )

    changed_by: Mapped["User | None"] = relationship(
        "User",
        foreign_keys=[changed_by_id],
        lazy="selectin",
    )

    marker: Mapped["User | None"] = relationship(
        "User",
        foreign_keys=[marker_id],
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return (
            "<MarkingDecisionRevision "
            f"id={self.id!r} "
            f"marking_decision_id={self.marking_decision_id!r} "
            f"revision={self.revision!r} "
            f"change_type={self.change_type!r} "
            f"status={self.status!r} "
            f"mark_awarded={self.mark_awarded!r}>"
        )
