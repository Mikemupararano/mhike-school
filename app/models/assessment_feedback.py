from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum as SqlEnum,
    ForeignKey,
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
    from app.models.assessment_response import AssessmentResponse
    from app.models.school import School
    from app.models.user import User


class AssessmentFeedbackStatus(str, Enum):
    """
    Workflow state for structured assessment feedback.

    DRAFT
        Feedback is still being prepared and may be edited freely.

    FINALISED
        Feedback has been completed by staff and is ready to accompany an
        authorised published assessment result.

    ARCHIVED
        Feedback is retained for historical reference but is no longer part
        of the active feedback workflow.
    """

    DRAFT = "draft"
    FINALISED = "finalised"
    ARCHIVED = "archived"


class AssessmentFeedback(Base):
    """
    Represent structured overall teacher feedback for one assessment script.

    Feedback is deliberately stored separately from marking decisions.

    Marking decisions remain the authoritative record of marks awarded to
    individual responses. This model stores pedagogical feedback such as:

        - overall teacher comment;
        - strengths;
        - areas for improvement;
        - next steps.

    Feedback belongs to an AssessmentScript rather than directly to an
    AssessmentCandidate. This preserves the feedback that belonged to a
    particular script version if a candidate later submits a correction,
    replacement script or retake.

    Only one overall feedback record may exist for a script.

    Visibility to students and parents is not determined solely by the
    existence of this record. The result-publication layer remains
    authoritative for whether assessment information may be released.
    """

    __tablename__ = "assessment_feedback"

    __table_args__ = (
        UniqueConstraint(
            "script_id",
            name="uq_assessment_feedback_script",
        ),
    )

    # ------------------------------------------------------------------
    # Identity
    # ------------------------------------------------------------------

    id: Mapped[int] = mapped_column(
        primary_key=True,
    )

    # ------------------------------------------------------------------
    # School and assessment scope
    # ------------------------------------------------------------------

    school_id: Mapped[int] = mapped_column(
        ForeignKey(
            "schools.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    script_id: Mapped[int] = mapped_column(
        ForeignKey(
            "assessment_scripts.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    # ------------------------------------------------------------------
    # Structured feedback
    # ------------------------------------------------------------------

    overall_comment: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    strengths: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    areas_for_improvement: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    next_steps: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # ------------------------------------------------------------------
    # Workflow
    # ------------------------------------------------------------------

    status: Mapped[AssessmentFeedbackStatus] = mapped_column(
        SqlEnum(
            AssessmentFeedbackStatus,
            name="assessment_feedback_status",
            values_callable=lambda enum_cls: [value.value for value in enum_cls],
            native_enum=False,
            validate_strings=True,
        ),
        default=AssessmentFeedbackStatus.DRAFT,
        nullable=False,
        index=True,
    )

    # Allows a teacher to prepare internal feedback that should not yet
    # accompany a published result even after finalisation.
    include_with_result: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    # ------------------------------------------------------------------
    # Audit ownership
    # ------------------------------------------------------------------

    created_by_id: Mapped[int] = mapped_column(
        ForeignKey(
            "users.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
        index=True,
    )

    updated_by_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "users.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
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

    finalised_at: Mapped[datetime | None] = mapped_column(
        DateTime(
            timezone=True,
        ),
        nullable=True,
    )

    finalised_by_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "users.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    # ------------------------------------------------------------------
    # Relationships
    # ------------------------------------------------------------------

    school: Mapped["School"] = relationship(
        "School",
        foreign_keys=[school_id],
        lazy="selectin",
    )

    script: Mapped["AssessmentScript"] = relationship(
        "AssessmentScript",
        foreign_keys=[script_id],
        lazy="selectin",
    )

    created_by: Mapped["User"] = relationship(
        "User",
        foreign_keys=[created_by_id],
        lazy="selectin",
    )

    updated_by: Mapped["User | None"] = relationship(
        "User",
        foreign_keys=[updated_by_id],
        lazy="selectin",
    )

    finalised_by: Mapped["User | None"] = relationship(
        "User",
        foreign_keys=[finalised_by_id],
        lazy="selectin",
    )

    # ------------------------------------------------------------------
    # Representation
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        return (
            "<AssessmentFeedback "
            f"id={self.id!r} "
            f"school_id={self.school_id!r} "
            f"script_id={self.script_id!r} "
            f"status={self.status!r} "
            f"include_with_result={self.include_with_result!r} "
            f"created_by_id={self.created_by_id!r}>"
        )


class AssessmentQuestionFeedback(Base):
    """
    Represent teacher feedback for one individual assessment response.

    The response already identifies the script and assessment question, so
    those identifiers are deliberately not duplicated here.

    Marks remain in MarkingDecision. This model stores feedback only.

    One current question-feedback record may exist for each response.
    """

    __tablename__ = "assessment_question_feedback"

    __table_args__ = (
        UniqueConstraint(
            "response_id",
            name="uq_assessment_question_feedback_response",
        ),
    )

    # ------------------------------------------------------------------
    # Identity
    # ------------------------------------------------------------------

    id: Mapped[int] = mapped_column(
        primary_key=True,
    )

    # ------------------------------------------------------------------
    # School and response scope
    # ------------------------------------------------------------------

    school_id: Mapped[int] = mapped_column(
        ForeignKey(
            "schools.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    response_id: Mapped[int] = mapped_column(
        ForeignKey(
            "assessment_responses.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    # ------------------------------------------------------------------
    # Structured response feedback
    # ------------------------------------------------------------------

    feedback_text: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    strength: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    improvement: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # ------------------------------------------------------------------
    # Visibility
    # ------------------------------------------------------------------

    include_with_result: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    # ------------------------------------------------------------------
    # Audit ownership
    # ------------------------------------------------------------------

    created_by_id: Mapped[int] = mapped_column(
        ForeignKey(
            "users.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
        index=True,
    )

    updated_by_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "users.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
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

    # ------------------------------------------------------------------
    # Relationships
    # ------------------------------------------------------------------

    school: Mapped["School"] = relationship(
        "School",
        foreign_keys=[school_id],
        lazy="selectin",
    )

    response: Mapped["AssessmentResponse"] = relationship(
        "AssessmentResponse",
        foreign_keys=[response_id],
        lazy="selectin",
    )

    created_by: Mapped["User"] = relationship(
        "User",
        foreign_keys=[created_by_id],
        lazy="selectin",
    )

    updated_by: Mapped["User | None"] = relationship(
        "User",
        foreign_keys=[updated_by_id],
        lazy="selectin",
    )

    # ------------------------------------------------------------------
    # Representation
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        return (
            "<AssessmentQuestionFeedback "
            f"id={self.id!r} "
            f"school_id={self.school_id!r} "
            f"response_id={self.response_id!r} "
            f"include_with_result={self.include_with_result!r} "
            f"created_by_id={self.created_by_id!r}>"
        )
