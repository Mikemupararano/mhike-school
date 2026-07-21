from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.base import Base


class ReportSession(Base):
    """
    Defines one reporting checkpoint for a school.

    A reporting session controls the fields collected once from teachers and
    the documents produced from that shared data.

    Supported output modes:

        grade_card
            Produce a compact grade card only.

        full_report
            Produce a full written report only.

        both
            Produce both the grade card and the full written report from the
            same StudentReport data.

    Teachers may always type the final report manually. Where report
    generation is enabled, teacher notes or prompts may be used to create an
    editable suggestion, but generated text must never be compulsory.

    Workflow stages indicate progress but must not create a dependency on one
    named member of staff. Authorised tutors, Heads of Year, the Headmaster,
    SMT, School Admin and Platform Admin may continue unpublished reports when
    an earlier contributor is unavailable.

    Existing fields such as ``term`` are retained for backward compatibility.
    New code should primarily use ``checkpoint_name``.
    """

    __tablename__ = "report_sessions"

    __table_args__ = (
        CheckConstraint(
            "reporting_mode IN ('grade_card', 'full_report', 'both')",
            name="ck_report_sessions_reporting_mode",
        ),
        CheckConstraint(
            "display_order >= 1",
            name="ck_report_sessions_display_order_positive",
        ),
    )

    # ------------------------------------------------------------------
    # Identity and ownership
    # ------------------------------------------------------------------

    id: Mapped[int] = mapped_column(primary_key=True)

    school_id: Mapped[int] = mapped_column(
        ForeignKey("schools.id", ondelete="CASCADE"),
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

    # Legacy reporting-period field retained for compatibility with
    # existing data, API clients, frontend pages and tests.
    term: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    # Flexible school-defined checkpoint, for example:
    # Autumn 1, Spring 2, Progress Check 3 or Final Report.
    checkpoint_name: Mapped[str | None] = mapped_column(
        String(100),
        index=True,
        nullable=True,
    )

    # Controls checkpoint ordering within the academic year.
    display_order: Mapped[int] = mapped_column(
        Integer,
        default=1,
        server_default="1",
        nullable=False,
    )

    # Supported values:
    #
    # grade_card
    #     Grade Card only.
    #
    # full_report
    #     Full written report only.
    #
    # both
    #     Grade Card and Full Report from the same saved report data.
    reporting_mode: Mapped[str] = mapped_column(
        String(30),
        default="full_report",
        server_default="full_report",
        nullable=False,
        index=True,
    )

    active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default="true",
        nullable=False,
        index=True,
    )

    # Generation is an optional time-saving tool. Manual report writing
    # remains available regardless of this setting.
    enable_report_generation: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default="true",
        nullable=False,
    )

    # The date on which the session was published as a whole.
    # Individual StudentReport records retain their own publication audit.
    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # ------------------------------------------------------------------
    # Branding and document-header configuration
    # ------------------------------------------------------------------

    # School name should normally be displayed on every exported report.
    include_school_name: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default="true",
        nullable=False,
    )

    # School logos are optional because some schools may not have uploaded
    # one or may prefer text-only reports.
    include_school_logo: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default="true",
        nullable=False,
    )

    include_teacher_name: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default="true",
        nullable=False,
    )

    include_subject_name: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default="true",
        nullable=False,
    )

    # ------------------------------------------------------------------
    # Report field display configuration
    # ------------------------------------------------------------------

    include_work_covered: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default="true",
        nullable=False,
    )

    # Controls whether the editable teacher-written/generated report
    # narrative is included.
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

    # Standard grade-panel fields. These default to enabled because they
    # appear at the top of the full report and form the core grade card.
    include_effort_grade: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default="true",
        nullable=False,
    )

    include_attainment_grade: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default="true",
        nullable=False,
    )

    include_target_grade: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default="true",
        nullable=False,
    )

    include_gcse_predicted_grade: Mapped[bool] = mapped_column(
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

    # Optional future-facing whole-school indicators.
    include_attendance: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
        nullable=False,
    )

    include_behaviour: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
        nullable=False,
    )

    # ------------------------------------------------------------------
    # Submission/publication validation configuration
    # ------------------------------------------------------------------

    # Drafts may always be saved incomplete. These flags should be checked
    # only when moving reports through submission, approval or publication.
    require_student_comment: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default="true",
        nullable=False,
    )

    require_effort_grade: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default="true",
        nullable=False,
    )

    require_attainment_grade: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default="true",
        nullable=False,
    )

    require_target_grade: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default="true",
        nullable=False,
    )

    require_exam_mark: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
        nullable=False,
    )

    require_exam_grade: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
        nullable=False,
    )

    require_gcse_predicted_grade: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
        nullable=False,
    )

    require_ucas_predicted_grade: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
        nullable=False,
    )

    require_next_steps: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
        nullable=False,
    )

    require_tutor_comment: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
        nullable=False,
    )

    require_head_of_year_comment: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
        nullable=False,
    )

    require_headteacher_comment: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
        nullable=False,
    )

    # ------------------------------------------------------------------
    # Workflow editing policy
    # ------------------------------------------------------------------

    # When enabled, the assigned teacher may continue correcting an
    # unpublished report after submission. Higher-authority reviewer roles
    # remain able to edit according to their permissions regardless.
    allow_teacher_edit_after_submission: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
        nullable=False,
    )

    # When enabled, SMT/School Admin/Platform Admin may make final corrections
    # after approval but before publication without first returning the report
    # to an earlier workflow state.
    allow_smt_edit_after_approval: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default="true",
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
    # from an earlier reporting checkpoint. Report data itself is not copied.
    copied_from_session_id: Mapped[int | None] = mapped_column(
        ForeignKey("report_sessions.id", ondelete="SET NULL"),
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
            f"reporting_mode={self.reporting_mode!r} "
            f"active={self.active}>"
        )
