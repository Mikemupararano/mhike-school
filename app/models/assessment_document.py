from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    String,
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
    from app.models.user import User


class AssessmentDocument(Base):
    """
    Persist an original document attached to an assessment.

    The initial use case is an uploaded question paper, normally PDF.

    Keeping the original source document separate from the structured
    AssessmentSection / AssessmentQuestion records allows MHike School to:

    - preserve the teacher's original paper for audit/reference;
    - extract questions into structured assessment records later;
    - re-run extraction without losing the source file;
    - support replacement/versioning without changing question records;
    - add mark schemes and other assessment documents in future.
    """

    __tablename__ = "assessment_documents"

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

    uploaded_by_id: Mapped[int] = mapped_column(
        ForeignKey(
            "users.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
        index=True,
    )

    document_type: Mapped[str] = mapped_column(
        String(
            50,
        ),
        nullable=False,
        default="question_paper",
        server_default="question_paper",
        index=True,
    )

    original_filename: Mapped[str] = mapped_column(
        String(
            500,
        ),
        nullable=False,
    )

    stored_filename: Mapped[str] = mapped_column(
        String(
            500,
        ),
        nullable=False,
    )

    storage_path: Mapped[str] = mapped_column(
        String(
            2000,
        ),
        nullable=False,
    )

    mime_type: Mapped[str] = mapped_column(
        String(
            255,
        ),
        nullable=False,
    )

    file_size_bytes: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
    )

    is_current: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
        index=True,
    )

    extraction_requested: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )

    extraction_completed: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )

    extraction_error: Mapped[str | None] = mapped_column(
        String(
            2000,
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

    uploaded_by: Mapped["User"] = relationship(
        "User",
        lazy="selectin",
    )

    __table_args__ = (
        Index(
            "ix_assessment_documents_assessment_type_current",
            "assessment_id",
            "document_type",
            "is_current",
        ),
    )
