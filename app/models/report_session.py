from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.base import Base


class ReportSession(Base):
    """
    Defines one reporting checkpoint for a school.

    Examples:
        Autumn 1 grade card
        Autumn 2 grade card
        Spring full report
        Summer end-of-year report

    Existing fields such as ``term`` are retained for backward compatibility.
    New code should primarily use ``checkpoint_name``.
    """

    __tablename__ = "report_sessions"

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

    # ------------------------------------------------------------------
    # Session identification
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

    # ------------------------------------------------------------------
    # Reporting checkpoint
    # ------------------------------------------------------------------

    # Retained temporarily for compatibility with existing data,
    # API clients, frontend pages and tests.
    term: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    # Flexible school-defined checkpoint name, for example:
    # Autumn 1, Autumn 2, Spring, Progress Check 3 or Final Report.
    checkpoint_name: Mapped[str | None] = mapped_column(
        String(100),
        index=True,
        nullable=True,
    )

    # Controls the order in which checkpoints appear within the
    # academic year.
    display_order: Mapped[int] = mapped_column(
        Integer,
        default=1,
        server_default="1",
        nullable=False,
    )

    # Supported values:
    # full_report
    # grade_card
    reporting_mode: Mapped[str] = mapped_column(
        String(30),
        default="full_report",
        server_default="full_report",
        nullable=False,
    )

    active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default="true",
        nullable=False,
    )

    # The date on which this reporting checkpoint was published.
    # Individual StudentReport records retain their own publication
    # audit fields.
    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # ------------------------------------------------------------------
    # Report field configuration
    # ------------------------------------------------------------------

    include_work_covered: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default="true",
        nullable=False,
    )

    include_student_comment: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default="true",
        nullable=False,
    )

    include_exam_mark: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
        nullable=False,
    )

    include_exam_grade: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
        nullable=False,
    )

    include_attainment_grade: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
        nullable=False,
    )

    include_effort_grade: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
        nullable=False,
    )

    include_target_grade: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
        nullable=False,
    )

    include_ucas_predicted_grade: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
        nullable=False,
    )

    include_next_steps: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
        nullable=False,
    )

    include_tutor_comment: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
        nullable=False,
    )

    include_head_of_year_comment: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
        nullable=False,
    )

    include_headteacher_comment: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
        nullable=False,
    )

    # ------------------------------------------------------------------
    # Cumulative report display configuration
    # ------------------------------------------------------------------

    # Include grades from earlier published checkpoints in the same
    # academic year.
    show_previous_grades: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
        nullable=False,
    )

    # Include tutor comments from earlier checkpoints.
    show_previous_tutor_comments: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
        nullable=False,
    )

    # Display calculated progress indicators where the school chooses
    # to use them.
    show_progress_journey: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
        nullable=False,
    )

    # ------------------------------------------------------------------
    # Configuration-copy support
    # ------------------------------------------------------------------

    # Records the source session when an administrator copies settings
    # from an earlier reporting checkpoint. Report data itself is not
    # copied.
    copied_from_session_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "report_sessions.id",
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

    school: Mapped["School"] = relationship(
        "School",
        lazy="selectin",
    )

    copied_from_session: Mapped["ReportSession | None"] = relationship(
        "ReportSession",
        remote_side=[id],
        foreign_keys=[copied_from_session_id],
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return (
            f"<ReportSession "
            f"id={self.id} "
            f"school_id={self.school_id} "
            f"title={self.title!r} "
            f"academic_year={self.academic_year!r} "
            f"checkpoint_name={self.checkpoint_name!r} "
            f"active={self.active}>"
        )
