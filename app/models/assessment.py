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
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)
from sqlalchemy.sql import func

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.assessment_candidate import AssessmentCandidate
    from app.models.assessment_grading import AssessmentGradingScheme
    from app.models.assessment_question import (
        AssessmentQuestion,
        AssessmentSection,
    )
    from app.models.course import Course
    from app.models.school import School
    from app.models.user import User


class AssessmentStatus(str, Enum):
    """
    Lifecycle state for an assessment.

    DRAFT
        Assessment is being constructed and is not available to candidates.

    PUBLISHED
        Assessment is available for the intended assessment workflow.

    CLOSED
        Assessment is no longer accepting normal candidate work but remains
        available for marking, moderation and analysis.

    ARCHIVED
        Assessment is retained for historical reference and analysis.
    """

    DRAFT = "draft"
    PUBLISHED = "published"
    CLOSED = "closed"
    ARCHIVED = "archived"


class Assessment(Base):
    """
    Represent one formal or teacher-created assessment within a school.

    An Assessment belongs to a Course rather than directly to a Subject.

    Example hierarchy:

        Subject:
            Physics

        Course:
            OCR A Level Physics A

        Assessment:
            Mechanics Test 1

    The Course provides the qualification/specification context and, through
    its Subject relationship, the broad academic discipline.

    Candidate allocation is represented separately through
    ``AssessmentCandidate`` records. This keeps assessment definition
    independent from student participation and supports absent, withdrawn,
    started and submitted candidate states.

    Total available marks are not stored directly on this table. They are
    derived from the assessment's markable questions.

    An assessment may optionally define one ``AssessmentGradingScheme``.
    The grading scheme controls how derived marks or percentages are mapped
    to grade labels without persisting duplicate candidate-grade values on
    the assessment itself.
    """

    __tablename__ = "assessments"

    # ------------------------------------------------------------------
    # Identity
    # ------------------------------------------------------------------

    id: Mapped[int] = mapped_column(
        primary_key=True,
    )

    # ------------------------------------------------------------------
    # School and academic scope
    # ------------------------------------------------------------------

    school_id: Mapped[int] = mapped_column(
        ForeignKey(
            "schools.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    course_id: Mapped[int] = mapped_column(
        ForeignKey(
            "courses.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    created_by_id: Mapped[int] = mapped_column(
        ForeignKey(
            "users.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
        index=True,
    )

    # ------------------------------------------------------------------
    # Assessment metadata
    # ------------------------------------------------------------------

    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    assessment_type: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    academic_year: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    term: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    # ------------------------------------------------------------------
    # Workflow
    # ------------------------------------------------------------------

    status: Mapped[AssessmentStatus] = mapped_column(
        SqlEnum(
            AssessmentStatus,
            name="assessment_status",
            values_callable=lambda enum_cls: [value.value for value in enum_cls],
            native_enum=False,
            validate_strings=True,
        ),
        default=AssessmentStatus.DRAFT,
        nullable=False,
        index=True,
    )

    anonymous_marking: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    # ------------------------------------------------------------------
    # Assessment dates
    # ------------------------------------------------------------------

    scheduled_at: Mapped[datetime | None] = mapped_column(
        DateTime(
            timezone=True,
        ),
        nullable=True,
    )

    closes_at: Mapped[datetime | None] = mapped_column(
        DateTime(
            timezone=True,
        ),
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

    # ------------------------------------------------------------------
    # Relationships
    # ------------------------------------------------------------------

    school: Mapped["School"] = relationship(
        "School",
        foreign_keys=[school_id],
        lazy="selectin",
    )

    course: Mapped["Course"] = relationship(
        "Course",
        back_populates="assessments",
        foreign_keys=[course_id],
        lazy="selectin",
    )

    creator: Mapped["User"] = relationship(
        "User",
        foreign_keys=[created_by_id],
        lazy="selectin",
    )

    sections: Mapped[list["AssessmentSection"]] = relationship(
        "AssessmentSection",
        back_populates="assessment",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="AssessmentSection.order",
    )

    questions: Mapped[list["AssessmentQuestion"]] = relationship(
        "AssessmentQuestion",
        back_populates="assessment",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="AssessmentQuestion.order",
    )

    candidates: Mapped[list["AssessmentCandidate"]] = relationship(
        "AssessmentCandidate",
        back_populates="assessment",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    grading_scheme: Mapped["AssessmentGradingScheme | None"] = relationship(
        "AssessmentGradingScheme",
        back_populates="assessment",
        cascade="all, delete-orphan",
        uselist=False,
        lazy="selectin",
        single_parent=True,
    )

    # ------------------------------------------------------------------
    # Representation
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        return (
            "<Assessment "
            f"id={self.id!r} "
            f"title={self.title!r} "
            f"course_id={self.course_id!r} "
            f"school_id={self.school_id!r} "
            f"status={self.status!r}>"
        )
