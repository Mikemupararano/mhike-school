from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.assessment import Assessment
    from app.models.assessment_document import AssessmentDocument
    from app.models.user import User


class AssessmentQuestionExtractionStatus(str, Enum):
    """
    Lifecycle state for one question-paper extraction attempt.

    Extraction produces a reviewable proposal. It never creates canonical
    AssessmentSection or AssessmentQuestion records merely because extraction
    completed successfully.
    """

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    IMPORTED = "imported"
    SUPERSEDED = "superseded"


class AssessmentQuestionExtraction(Base):
    """
    Persist one extraction attempt for an assessment question paper.

    The original AssessmentDocument remains the immutable source of truth.
    This model stores the machine-generated interpretation of that source so
    teachers can review and correct detected question structure before anything
    is imported into the canonical assessment model.

    Extraction attempts are versioned rather than overwritten. This allows
    MHike School to:

    - preserve every extraction attempt for audit/history;
    - re-run extraction when parsing improves;
    - retain page references and source evidence;
    - distinguish machine extraction from teacher-approved questions;
    - keep failed attempts without losing diagnostic information;
    - import only an explicitly reviewed proposal.
    """

    __tablename__ = "assessment_question_extractions"

    __table_args__ = (
        UniqueConstraint(
            "assessment_document_id",
            "version",
            name="uq_assessment_question_extraction_document_version",
        ),
        Index(
            "ix_assessment_question_extractions_assessment_document_status",
            "assessment_document_id",
            "status",
        ),
        Index(
            "ix_assessment_question_extractions_assessment_status",
            "assessment_id",
            "status",
        ),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True,
    )

    assessment_id: Mapped[int] = mapped_column(
        ForeignKey(
            "assessments.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    assessment_document_id: Mapped[int] = mapped_column(
        ForeignKey(
            "assessment_documents.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    requested_by_id: Mapped[int] = mapped_column(
        ForeignKey(
            "users.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
        index=True,
    )

    imported_by_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "users.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(
            30,
        ),
        nullable=False,
        default=AssessmentQuestionExtractionStatus.PENDING.value,
        server_default=AssessmentQuestionExtractionStatus.PENDING.value,
        index=True,
    )

    extractor_name: Mapped[str] = mapped_column(
        String(
            100,
        ),
        nullable=False,
        default="pypdf",
        server_default="pypdf",
    )

    extractor_version: Mapped[str | None] = mapped_column(
        String(
            50,
        ),
        nullable=True,
    )

    parser_version: Mapped[str] = mapped_column(
        String(
            50,
        ),
        nullable=False,
        default="1",
        server_default="1",
    )

    page_count: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    text_page_count: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    detected_question_count: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    detected_markable_question_count: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    detected_total_marks: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    source_metadata: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        nullable=True,
    )

    page_data: Mapped[list[dict[str, Any]] | None] = mapped_column(
        JSON,
        nullable=True,
    )

    proposal_data: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        nullable=True,
    )

    error_message: Mapped[str | None] = mapped_column(
        String(
            4000,
        ),
        nullable=True,
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

    imported_at: Mapped[datetime | None] = mapped_column(
        DateTime(
            timezone=True,
        ),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(
            timezone=True,
        ),
        nullable=False,
        server_default=func.now(),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(
            timezone=True,
        ),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    assessment: Mapped["Assessment"] = relationship(
        "Assessment",
        lazy="selectin",
    )

    assessment_document: Mapped["AssessmentDocument"] = relationship(
        "AssessmentDocument",
        lazy="selectin",
    )

    requested_by: Mapped["User"] = relationship(
        "User",
        foreign_keys=[requested_by_id],
        lazy="selectin",
    )

    imported_by: Mapped["User | None"] = relationship(
        "User",
        foreign_keys=[imported_by_id],
        lazy="selectin",
    )