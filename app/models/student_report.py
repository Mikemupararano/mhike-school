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
    Stores one student's subject report for one reporting session.

    The report record is the single source of truth for:

    - the editable full written report;
    - the compact grade card;
    - the parent portal;
    - PDF and print output;
    - bulk ZIP exports.

    Teachers may either write ``report_text`` manually or generate a
    suggestion from ``teacher_notes``. Generated text is never compulsory
    and must remain fully editable.

    Workflow audit fields record who performed an action. They must not be
    treated as ownership locks: authorised tutors, Heads of Year, the
    Headmaster, SMT, School Admin and Platform Admin may continue an
    unpublished report when the assigned teacher or an earlier reviewer is
    unavailable.

    Shared class-level content, such as work covered, is stored separately
    in ReportGroupContent and is scoped by:

    - school;
    - reporting session;
    - class group;
    - subject.

    Legacy fields such as ``grade``, ``term`` and ``work_covered`` remain
    temporarily for backward compatibility while existing data and API
    consumers transition to the shared reporting structure.
    """

    __tablename__ = "student_reports"

    __table_args__ = (
        UniqueConstraint(
            "school_id",
            "student_id",
            "report_session_id",
            "class_group_id",
            "subject_name",
            name="uq_student_report_session_class_subject",
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

    # The member of staff currently assigned responsibility for this
    # subject report.
    #
    # Teacher assignment is not part of report uniqueness because a report
    # must remain the same report if responsibility is transferred to
    # another authorised member of staff.
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

    # The teaching class to which this pupil report belongs.
    #
    # This allows the report to resolve shared class-level content through
    # ReportGroupContent using the reporting session, class and subject.
    #
    # It remains nullable during the transition so legacy reports can be
    # migrated safely without immediately requiring a class assignment.
    class_group_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "class_groups.id",
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

    # Legacy reporting-period field retained for compatibility.
    term: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    # Preferred reporting checkpoint for new code.
    # Examples: Autumn 1, Spring 2, Progress Check 3.
    checkpoint_name: Mapped[str | None] = mapped_column(
        String(100),
        index=True,
        nullable=True,
    )

    # Subject remains part of the report identity because ClassGroup does
    # not currently contain a dedicated subject field.
    subject_name: Mapped[str | None] = mapped_column(
        String(100),
        index=True,
        nullable=True,
    )

    # ------------------------------------------------------------------
    # Teacher report content
    # ------------------------------------------------------------------

    # The authoritative, teacher-approved and editable pupil comment.
    # It may be written manually or copied from generated_report_text.
    report_text: Mapped[str] = mapped_column(
        Text,
        default="",
        server_default="",
        nullable=False,
    )

    # Teacher-provided notes, bullet points or prompts about this pupil.
    teacher_notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # The most recent raw suggestion produced from teacher_notes.
    # This is never required when saving or submitting a manually written
    # report.
    generated_report_text: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # Legacy pupil-level copy retained temporarily while existing data and
    # API consumers transition to ReportGroupContent.
    #
    # New code should read and write shared work covered through:
    #
    # school_id
    # report_session_id
    # class_group_id
    # subject_name
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

    # Legacy field retained for backward compatibility.
    # New code should use the structured fields below.
    grade: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    effort_grade: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    attainment_grade: Mapped[str | None] = mapped_column(
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

    gcse_predicted_grade: Mapped[str | None] = mapped_column(
        String(50),
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
    #
    # These states indicate progress. They must not create a hard
    # dependency on the person who completed the previous stage.
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
        foreign_keys=[school_id],
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

    report_session = relationship(
        "ReportSession",
        foreign_keys=[report_session_id],
        lazy="selectin",
    )

    class_group = relationship(
        "ClassGroup",
        foreign_keys=[class_group_id],
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