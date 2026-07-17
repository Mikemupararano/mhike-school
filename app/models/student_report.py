from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.base import Base


class StudentReport(Base):
    """
    Stores an individual student's report for one reporting session.

    The model supports the complete reporting workflow:

        draft
        → submitted
        → tutor review
        → ready for SMT
        → approved
        → published

    Legacy fields such as ``grade``, ``term`` and ``work_covered`` are
    retained while the application transitions to the expanded reporting
    structure.
    """

    __tablename__ = "student_reports"

    __table_args__ = (
        UniqueConstraint(
            "school_id",
            "student_id",
            "teacher_id",
            "report_session_id",
            name="uq_student_report_session_teacher",
        ),
    )

    # ------------------------------------------------------------------
    # Identity and ownership
    # ------------------------------------------------------------------

    id: Mapped[int] = mapped_column(
        primary_key=True,
    )

    school_id: Mapped[int] = mapped_column(
        ForeignKey(
            "schools.id",
            ondelete="CASCADE",
        ),
        index=True,
        nullable=False,
    )

    student_id: Mapped[int] = mapped_column(
        ForeignKey(
            "users.id",
            ondelete="CASCADE",
        ),
        index=True,
        nullable=False,
    )

    teacher_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "users.id",
            ondelete="SET NULL",
        ),
        index=True,
        nullable=True,
    )

    report_session_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "report_sessions.id",
            ondelete="SET NULL",
        ),
        index=True,
        nullable=True,
    )

    # ------------------------------------------------------------------
    # Report identification
    # ------------------------------------------------------------------

    title: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )

    academic_year: Mapped[str] = mapped_column(
        String(20),
        index=True,
        nullable=False,
    )

    # Retained for compatibility with existing reports, schemas,
    # endpoints and frontend pages.
    term: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    # Preferred reporting checkpoint field for new code.
    # Examples: Autumn 1, Spring 2, Progress Check 3.
    checkpoint_name: Mapped[str | None] = mapped_column(
        String(100),
        index=True,
        nullable=True,
    )

    # Optional subject identification. This allows reports to be grouped
    # reliably without depending only on their title.
    subject_name: Mapped[str | None] = mapped_column(
        String(100),
        index=True,
        nullable=True,
    )

    # ------------------------------------------------------------------
    # Teacher report content
    # ------------------------------------------------------------------

    # The final teacher-written or approved subject report comment.
    report_text: Mapped[str] = mapped_column(
        Text,
        default="",
        server_default="",
        nullable=False,
    )

    # Notes entered by the teacher before report generation.
    teacher_notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # Text produced by the report-writing system from teacher notes.
    generated_report_text: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # Retained temporarily until work covered is moved to a shared
    # class-and-subject configuration model.
    work_covered: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    next_steps: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # ------------------------------------------------------------------
    # Assessment and grade information
    # ------------------------------------------------------------------

    # Legacy grade field retained for backward compatibility.
    # New code should use the structured fields below.
    grade: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    attainment_grade: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    effort_grade: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    target_grade: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    exam_grade: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    exam_mark: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    exam_max_mark: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    ucas_predicted_grade: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    # ------------------------------------------------------------------
    # Tutor and senior pastoral comments
    # ------------------------------------------------------------------

    tutor_comment: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    head_of_year_comment: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    headteacher_comment: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # ------------------------------------------------------------------
    # Workflow state
    # ------------------------------------------------------------------

    # Expected states:
    #
    # draft
    # submitted
    # returned_to_teacher
    # tutor_reviewed
    # returned_by_tutor
    # ready_for_smt
    # approved
    # returned_by_smt
    # published
    status: Mapped[str] = mapped_column(
        String(50),
        default="draft",
        server_default="draft",
        nullable=False,
        index=True,
    )

    # ------------------------------------------------------------------
    # Teacher submission stage
    # ------------------------------------------------------------------

    submitted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    submitted_by_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "users.id",
            ondelete="SET NULL",
        ),
        index=True,
        nullable=True,
    )

    # ------------------------------------------------------------------
    # Tutor-review stage
    # ------------------------------------------------------------------

    tutor_reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    tutor_reviewed_by_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "users.id",
            ondelete="SET NULL",
        ),
        index=True,
        nullable=True,
    )

    tutor_review_comments: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    ready_for_smt_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    ready_for_smt_by_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "users.id",
            ondelete="SET NULL",
        ),
        index=True,
        nullable=True,
    )

    # ------------------------------------------------------------------
    # SMT / School Admin review stage
    # ------------------------------------------------------------------

    reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    reviewed_by_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "users.id",
            ondelete="SET NULL",
        ),
        index=True,
        nullable=True,
    )

    review_comments: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # ------------------------------------------------------------------
    # Optional Head of Year review
    # ------------------------------------------------------------------

    head_of_year_reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    head_of_year_reviewed_by_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "users.id",
            ondelete="SET NULL",
        ),
        index=True,
        nullable=True,
    )

    # ------------------------------------------------------------------
    # Optional Headteacher review
    # ------------------------------------------------------------------

    headteacher_reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    headteacher_reviewed_by_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "users.id",
            ondelete="SET NULL",
        ),
        index=True,
        nullable=True,
    )

    # ------------------------------------------------------------------
    # Publication
    # ------------------------------------------------------------------

    published: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
        nullable=False,
        index=True,
    )

    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    published_by_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "users.id",
            ondelete="SET NULL",
        ),
        index=True,
        nullable=True,
    )

    # ------------------------------------------------------------------
    # Audit timestamps
    # ------------------------------------------------------------------

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # ------------------------------------------------------------------
    # Relationships
    # ------------------------------------------------------------------

    school = relationship(
        "School",
        lazy="selectin",
    )

    student = relationship(
        "User",
        foreign_keys=[student_id],
        lazy="selectin",
    )

    teacher = relationship(
        "User",
        foreign_keys=[teacher_id],
        lazy="selectin",
    )

    submitted_by = relationship(
        "User",
        foreign_keys=[submitted_by_id],
        lazy="selectin",
    )

    tutor_reviewed_by = relationship(
        "User",
        foreign_keys=[tutor_reviewed_by_id],
        lazy="selectin",
    )

    ready_for_smt_by = relationship(
        "User",
        foreign_keys=[ready_for_smt_by_id],
        lazy="selectin",
    )

    reviewed_by = relationship(
        "User",
        foreign_keys=[reviewed_by_id],
        lazy="selectin",
    )

    head_of_year_reviewed_by = relationship(
        "User",
        foreign_keys=[head_of_year_reviewed_by_id],
        lazy="selectin",
    )

    headteacher_reviewed_by = relationship(
        "User",
        foreign_keys=[headteacher_reviewed_by_id],
        lazy="selectin",
    )

    published_by = relationship(
        "User",
        foreign_keys=[published_by_id],
        lazy="selectin",
    )

    report_session = relationship(
        "ReportSession",
        foreign_keys=[report_session_id],
        lazy="selectin",
    )
