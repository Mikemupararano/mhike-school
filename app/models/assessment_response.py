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
    String,
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

if TYPE_CHECKING:
    from app.models.assessment_candidate import AssessmentScript
    from app.models.assessment_marking_annotation import AssessmentMarkingAnnotation
    from app.models.assessment_question import AssessmentQuestion
    from app.models.assessment_question_snapshot import AssessmentQuestionSnapshot
    from app.models.mark_scheme_award import MarkSchemeItemAward
    from app.models.marking_decision_revision import MarkingDecisionRevision
    from app.models.user import User


class AssessmentResponseStatus(str, Enum):
    """
    Lifecycle state for one candidate response.

    NOT_STARTED
        No response has yet been captured.

    IN_PROGRESS
        Candidate response exists but is not complete.

    SUBMITTED
        Candidate response has been submitted for marking.

    VOID
        Response has been invalidated and must not contribute to marks.
    """

    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    SUBMITTED = "submitted"
    VOID = "void"


class MarkingDecisionStatus(str, Enum):
    """
    Lifecycle state for one marking decision.

    UNMARKED
        No mark has yet been awarded.

    IN_PROGRESS
        Marking has started but is not complete.

    MARKED
        Primary marking is complete.

    REVIEWED
        Mark has been reviewed or moderated.

    FINALISED
        Mark is final and should not normally be changed.
    """

    UNMARKED = "unmarked"
    IN_PROGRESS = "in_progress"
    MARKED = "marked"
    REVIEWED = "reviewed"
    FINALISED = "finalised"


class AssessmentResponse(Base):
    """
    Represent one candidate response to one assessment question.

    A response belongs to one AssessmentScript.

    ``question_snapshot_id`` links a response to the immutable question
    snapshot that governed the candidate's attempt. New browser-assessment
    responses should use this immutable linkage whenever snapshots exist.

    ``question_id`` is retained for canonical-question provenance and backward
    compatibility with historical responses created before question snapshots
    were introduced.

    The legacy unique constraint on ``script_id`` and ``question_id`` remains
    in place during the compatibility phase.

    The additional unique constraint on ``script_id`` and
    ``question_snapshot_id`` ensures that one script has at most one response
    for a particular immutable question snapshot.

    The response may contain typed text, structured answer data, a reference
    to uploaded/scanned work, or a combination of these.
    """

    __tablename__ = "assessment_responses"

    __table_args__ = (
        UniqueConstraint(
            "script_id",
            "question_id",
            name="uq_assessment_response_script_question",
        ),
        UniqueConstraint(
            "script_id",
            "question_snapshot_id",
            name="uq_assessment_response_script_question_snapshot",
        ),
    )

    # ------------------------------------------------------------------
    # Identity
    # ------------------------------------------------------------------

    id: Mapped[int] = mapped_column(
        primary_key=True,
    )

    # ------------------------------------------------------------------
    # Script and question scope
    # ------------------------------------------------------------------

    script_id: Mapped[int] = mapped_column(
        ForeignKey(
            "assessment_scripts.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    question_id: Mapped[int] = mapped_column(
        ForeignKey(
            "assessment_questions.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    question_snapshot_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "assessment_question_snapshots.id",
            ondelete="CASCADE",
        ),
        nullable=True,
        index=True,
    )

    # ------------------------------------------------------------------
    # Response content
    # ------------------------------------------------------------------

    status: Mapped[AssessmentResponseStatus] = mapped_column(
        SqlEnum(
            AssessmentResponseStatus,
            name="assessment_response_status",
            values_callable=lambda enum_cls: [value.value for value in enum_cls],
            native_enum=False,
            validate_strings=True,
        ),
        default=AssessmentResponseStatus.NOT_STARTED,
        nullable=False,
        index=True,
    )

    response_text: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    response_data: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    source_reference: Mapped[str | None] = mapped_column(
        String(1000),
        nullable=True,
    )

    # ------------------------------------------------------------------
    # Audit timestamps
    # ------------------------------------------------------------------

    created_at: Mapped[datetime] = mapped_column(
        DateTime(
            timezone=True,
        ),
        server_default=func.now(),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(
            timezone=True,
        ),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    submitted_at: Mapped[datetime | None] = mapped_column(
        DateTime(
            timezone=True,
        ),
        nullable=True,
    )

    # ------------------------------------------------------------------
    # Relationships
    # ------------------------------------------------------------------

    script: Mapped["AssessmentScript"] = relationship(
        "AssessmentScript",
        back_populates="responses",
        foreign_keys=[script_id],
        lazy="selectin",
    )

    question: Mapped["AssessmentQuestion"] = relationship(
        "AssessmentQuestion",
        back_populates="responses",
        foreign_keys=[question_id],
        lazy="selectin",
    )

    question_snapshot: Mapped["AssessmentQuestionSnapshot | None"] = relationship(
        "AssessmentQuestionSnapshot",
        foreign_keys=[question_snapshot_id],
        lazy="selectin",
    )

    marking_annotations: Mapped[list["AssessmentMarkingAnnotation"]] = relationship(
        "AssessmentMarkingAnnotation",
        back_populates="response",
        foreign_keys="AssessmentMarkingAnnotation.response_id",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="AssessmentMarkingAnnotation.id",
    )

    marking_decision: Mapped["MarkingDecision | None"] = relationship(
        "MarkingDecision",
        back_populates="response",
        cascade="all, delete-orphan",
        uselist=False,
        lazy="selectin",
    )

    # ------------------------------------------------------------------
    # Representation
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        return (
            "<AssessmentResponse "
            f"id={self.id!r} "
            f"script_id={self.script_id!r} "
            f"question_id={self.question_id!r} "
            f"question_snapshot_id={self.question_snapshot_id!r} "
            f"status={self.status!r}>"
        )


class MarkingDecision(Base):
    """
    Represent the primary marking decision for one assessment response.

    ``mark_awarded`` stores the question-level mark used for totals and QLA.

    Detailed mark-scheme item awards are stored separately so this record
    remains the authoritative question-level result while still allowing
    criterion-level evidence and moderation.

    ``item_awards`` records the individual mark-scheme criteria awarded
    during marking.
    """

    __tablename__ = "marking_decisions"

    __table_args__ = (
        UniqueConstraint(
            "response_id",
            name="uq_marking_decision_response",
        ),
        CheckConstraint(
            "revision >= 0",
            name="ck_marking_decision_revision_non_negative",
        ),
    )

    # ------------------------------------------------------------------
    # Identity
    # ------------------------------------------------------------------

    id: Mapped[int] = mapped_column(
        primary_key=True,
    )

    # ------------------------------------------------------------------
    # Response and marker
    # ------------------------------------------------------------------

    response_id: Mapped[int] = mapped_column(
        ForeignKey(
            "assessment_responses.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    marker_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "users.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    # ------------------------------------------------------------------
    # Marking result
    # ------------------------------------------------------------------

    status: Mapped[MarkingDecisionStatus] = mapped_column(
        SqlEnum(
            MarkingDecisionStatus,
            name="marking_decision_status",
            values_callable=lambda enum_cls: [value.value for value in enum_cls],
            native_enum=False,
            validate_strings=True,
        ),
        default=MarkingDecisionStatus.UNMARKED,
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

    revision: Mapped[int] = mapped_column(
        Integer,
        default=0,
        server_default="0",
        nullable=False,
    )

    # ------------------------------------------------------------------
    # Audit timestamps
    # ------------------------------------------------------------------

    created_at: Mapped[datetime] = mapped_column(
        DateTime(
            timezone=True,
        ),
        server_default=func.now(),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(
            timezone=True,
        ),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
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
    # Relationships
    # ------------------------------------------------------------------

    response: Mapped["AssessmentResponse"] = relationship(
        "AssessmentResponse",
        back_populates="marking_decision",
        foreign_keys=[response_id],
        lazy="selectin",
    )

    marker: Mapped["User | None"] = relationship(
        "User",
        foreign_keys=[marker_id],
        lazy="selectin",
    )

    item_awards: Mapped[list["MarkSchemeItemAward"]] = relationship(
        "MarkSchemeItemAward",
        back_populates="marking_decision",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="MarkSchemeItemAward.id",
    )

    revisions: Mapped[list["MarkingDecisionRevision"]] = relationship(
        "MarkingDecisionRevision",
        back_populates="marking_decision",
        lazy="selectin",
        order_by="MarkingDecisionRevision.revision",
        passive_deletes=True,
    )

    # ------------------------------------------------------------------
    # Representation
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        return (
            "<MarkingDecision "
            f"id={self.id!r} "
            f"response_id={self.response_id!r} "
            f"marker_id={self.marker_id!r} "
            f"mark_awarded={self.mark_awarded!r} "
            f"status={self.status!r}>"
        )
