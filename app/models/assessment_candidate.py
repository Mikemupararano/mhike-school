from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import (
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
    from app.models.assessment import Assessment
    from app.models.assessment_response import AssessmentResponse
    from app.models.user import User


class AssessmentCandidateStatus(str, Enum):
    """
    Lifecycle state for one candidate's participation in an assessment.

    ALLOCATED
        Candidate has been assigned to the assessment.

    STARTED
        Candidate has begun the assessment.

    SUBMITTED
        Candidate has submitted work for marking.

    WITHDRAWN
        Candidate is no longer participating in the assessment.

    ABSENT
        Candidate was expected to sit the assessment but was absent.
    """

    ALLOCATED = "allocated"
    STARTED = "started"
    SUBMITTED = "submitted"
    WITHDRAWN = "withdrawn"
    ABSENT = "absent"


class AssessmentScriptStatus(str, Enum):
    """
    Lifecycle state for one submitted assessment script.

    NOT_SUBMITTED
        No script has yet been submitted.

    SUBMITTED
        Script has been submitted and is awaiting marking.

    MARKING
        Script is currently being marked.

    MARKED
        Primary marking is complete.

    MODERATION
        Script is undergoing moderation or review.

    FINALISED
        Marking and moderation are complete.
    """

    NOT_SUBMITTED = "not_submitted"
    SUBMITTED = "submitted"
    MARKING = "marking"
    MARKED = "marked"
    MODERATION = "moderation"
    FINALISED = "finalised"


class AssessmentCandidate(Base):
    """
    Represent one student's allocation to an assessment.

    The candidate record separates assessment participation from the student's
    User record and from the eventual submitted script.

    This is important because a candidate may be allocated but absent,
    withdrawn, not yet started, or may submit more than one script version
    during future workflows.

    One student may be allocated to the same assessment only once.
    """

    __tablename__ = "assessment_candidates"

    __table_args__ = (
        UniqueConstraint(
            "assessment_id",
            "student_id",
            name="uq_assessment_candidate_student",
        ),
    )

    # ------------------------------------------------------------------
    # Identity
    # ------------------------------------------------------------------

    id: Mapped[int] = mapped_column(
        primary_key=True,
    )

    # ------------------------------------------------------------------
    # Assessment and student scope
    # ------------------------------------------------------------------

    assessment_id: Mapped[int] = mapped_column(
        ForeignKey(
            "assessments.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    student_id: Mapped[int] = mapped_column(
        ForeignKey(
            "users.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
        index=True,
    )

    # ------------------------------------------------------------------
    # Candidate workflow
    # ------------------------------------------------------------------

    status: Mapped[AssessmentCandidateStatus] = mapped_column(
        SqlEnum(
            AssessmentCandidateStatus,
            name="assessment_candidate_status",
            values_callable=lambda enum_cls: [value.value for value in enum_cls],
            native_enum=False,
            validate_strings=True,
        ),
        default=AssessmentCandidateStatus.ALLOCATED,
        nullable=False,
        index=True,
    )

    candidate_number: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    access_arrangements: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # ------------------------------------------------------------------
    # Audit timestamps
    # ------------------------------------------------------------------

    allocated_at: Mapped[datetime] = mapped_column(
        DateTime(
            timezone=True,
        ),
        server_default=func.now(),
        nullable=False,
    )

    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(
            timezone=True,
        ),
        nullable=True,
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

    assessment: Mapped["Assessment"] = relationship(
        "Assessment",
        back_populates="candidates",
        foreign_keys=[assessment_id],
        lazy="selectin",
    )

    student: Mapped["User"] = relationship(
        "User",
        foreign_keys=[student_id],
        lazy="selectin",
    )

    scripts: Mapped[list["AssessmentScript"]] = relationship(
        "AssessmentScript",
        back_populates="candidate",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="AssessmentScript.version",
    )

    # ------------------------------------------------------------------
    # Representation
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        return (
            "<AssessmentCandidate "
            f"id={self.id!r} "
            f"assessment_id={self.assessment_id!r} "
            f"student_id={self.student_id!r} "
            f"status={self.status!r}>"
        )


class AssessmentScript(Base):
    """
    Represent one submitted script/version for an assessment candidate.

    The script record is intentionally separate from the candidate allocation.

    This supports future workflows such as:
        - uploaded PDF scripts
        - scanned handwritten papers
        - browser-completed assessments
        - revised or replacement uploads
        - moderation copies
        - version history

    Question-level responses are stored separately and linked to this script.
    """

    __tablename__ = "assessment_scripts"

    __table_args__ = (
        UniqueConstraint(
            "candidate_id",
            "version",
            name="uq_assessment_script_candidate_version",
        ),
    )

    # ------------------------------------------------------------------
    # Identity
    # ------------------------------------------------------------------

    id: Mapped[int] = mapped_column(
        primary_key=True,
    )

    # ------------------------------------------------------------------
    # Candidate ownership
    # ------------------------------------------------------------------

    candidate_id: Mapped[int] = mapped_column(
        ForeignKey(
            "assessment_candidates.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    # ------------------------------------------------------------------
    # Script metadata
    # ------------------------------------------------------------------

    version: Mapped[int] = mapped_column(
        nullable=False,
        default=1,
    )

    status: Mapped[AssessmentScriptStatus] = mapped_column(
        SqlEnum(
            AssessmentScriptStatus,
            name="assessment_script_status",
            values_callable=lambda enum_cls: [value.value for value in enum_cls],
            native_enum=False,
            validate_strings=True,
        ),
        default=AssessmentScriptStatus.NOT_SUBMITTED,
        nullable=False,
        index=True,
    )

    source_type: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    source_filename: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    storage_key: Mapped[str | None] = mapped_column(
        String(1000),
        nullable=True,
    )

    mime_type: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    checksum: Mapped[str | None] = mapped_column(
        String(255),
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

    submitted_at: Mapped[datetime | None] = mapped_column(
        DateTime(
            timezone=True,
        ),
        nullable=True,
    )

    marking_started_at: Mapped[datetime | None] = mapped_column(
        DateTime(
            timezone=True,
        ),
        nullable=True,
    )

    marked_at: Mapped[datetime | None] = mapped_column(
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

    candidate: Mapped["AssessmentCandidate"] = relationship(
        "AssessmentCandidate",
        back_populates="scripts",
        foreign_keys=[candidate_id],
        lazy="selectin",
    )

    responses: Mapped[list["AssessmentResponse"]] = relationship(
        "AssessmentResponse",
        back_populates="script",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="AssessmentResponse.question_id",
    )

    # ------------------------------------------------------------------
    # Representation
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        return (
            "<AssessmentScript "
            f"id={self.id!r} "
            f"candidate_id={self.candidate_id!r} "
            f"version={self.version!r} "
            f"status={self.status!r}>"
        )
