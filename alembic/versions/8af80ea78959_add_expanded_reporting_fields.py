"""add expanded reporting fields

Revision ID: 8af80ea78959
Revises: 311a70b259ba
Create Date: 2026-07-18 07:42:55.375687+00:00
"""

from alembic import op
import sqlalchemy as sa

# Revision identifiers, used by Alembic.
revision = "8af80ea78959"
down_revision = "311a70b259ba"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # Report sessions
    # ------------------------------------------------------------------
    op.add_column(
        "report_sessions",
        sa.Column("checkpoint_name", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "report_sessions",
        sa.Column(
            "display_order",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("1"),
        ),
    )
    op.add_column(
        "report_sessions",
        sa.Column(
            "reporting_mode",
            sa.String(length=30),
            nullable=False,
            server_default=sa.text("'full_report'"),
        ),
    )
    op.add_column(
        "report_sessions",
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "report_sessions",
        sa.Column(
            "include_exam_grade",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.add_column(
        "report_sessions",
        sa.Column(
            "include_ucas_predicted_grade",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.add_column(
        "report_sessions",
        sa.Column(
            "include_head_of_year_comment",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.add_column(
        "report_sessions",
        sa.Column(
            "include_headteacher_comment",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.add_column(
        "report_sessions",
        sa.Column(
            "show_previous_grades",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.add_column(
        "report_sessions",
        sa.Column(
            "show_previous_tutor_comments",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.add_column(
        "report_sessions",
        sa.Column(
            "show_progress_journey",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.add_column(
        "report_sessions",
        sa.Column("copied_from_session_id", sa.Integer(), nullable=True),
    )
    op.add_column(
        "report_sessions",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    op.create_index(
        "ix_report_sessions_checkpoint_name",
        "report_sessions",
        ["checkpoint_name"],
        unique=False,
    )
    op.create_index(
        "ix_report_sessions_copied_from_session_id",
        "report_sessions",
        ["copied_from_session_id"],
        unique=False,
    )

    op.create_foreign_key(
        "fk_report_sessions_copied_from_session_id",
        "report_sessions",
        "report_sessions",
        ["copied_from_session_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # ------------------------------------------------------------------
    # Student reports: report content and grade fields
    # ------------------------------------------------------------------
    op.add_column(
        "student_reports",
        sa.Column("checkpoint_name", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "student_reports",
        sa.Column("subject_name", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "student_reports",
        sa.Column("next_steps", sa.Text(), nullable=True),
    )
    op.add_column(
        "student_reports",
        sa.Column("attainment_grade", sa.String(length=50), nullable=True),
    )
    op.add_column(
        "student_reports",
        sa.Column("effort_grade", sa.String(length=50), nullable=True),
    )
    op.add_column(
        "student_reports",
        sa.Column("target_grade", sa.String(length=50), nullable=True),
    )
    op.add_column(
        "student_reports",
        sa.Column("exam_grade", sa.String(length=50), nullable=True),
    )
    op.add_column(
        "student_reports",
        sa.Column("exam_mark", sa.Integer(), nullable=True),
    )
    op.add_column(
        "student_reports",
        sa.Column("exam_max_mark", sa.Integer(), nullable=True),
    )
    op.add_column(
        "student_reports",
        sa.Column(
            "ucas_predicted_grade",
            sa.String(length=50),
            nullable=True,
        ),
    )

    # ------------------------------------------------------------------
    # Student reports: review comments and audit fields
    # ------------------------------------------------------------------
    op.add_column(
        "student_reports",
        sa.Column("tutor_comment", sa.Text(), nullable=True),
    )
    op.add_column(
        "student_reports",
        sa.Column("head_of_year_comment", sa.Text(), nullable=True),
    )
    op.add_column(
        "student_reports",
        sa.Column("headteacher_comment", sa.Text(), nullable=True),
    )
    op.add_column(
        "student_reports",
        sa.Column("tutor_reviewed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "student_reports",
        sa.Column("tutor_reviewed_by_id", sa.Integer(), nullable=True),
    )
    op.add_column(
        "student_reports",
        sa.Column("tutor_review_comments", sa.Text(), nullable=True),
    )
    op.add_column(
        "student_reports",
        sa.Column("ready_for_smt_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "student_reports",
        sa.Column("ready_for_smt_by_id", sa.Integer(), nullable=True),
    )
    op.add_column(
        "student_reports",
        sa.Column(
            "head_of_year_reviewed_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )
    op.add_column(
        "student_reports",
        sa.Column("head_of_year_reviewed_by_id", sa.Integer(), nullable=True),
    )
    op.add_column(
        "student_reports",
        sa.Column(
            "headteacher_reviewed_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )
    op.add_column(
        "student_reports",
        sa.Column("headteacher_reviewed_by_id", sa.Integer(), nullable=True),
    )

    # ------------------------------------------------------------------
    # Student-report indexes
    # ------------------------------------------------------------------
    op.create_index(
        "ix_student_reports_checkpoint_name",
        "student_reports",
        ["checkpoint_name"],
        unique=False,
    )
    op.create_index(
        "ix_student_reports_subject_name",
        "student_reports",
        ["subject_name"],
        unique=False,
    )
    op.create_index(
        "ix_student_reports_tutor_reviewed_by_id",
        "student_reports",
        ["tutor_reviewed_by_id"],
        unique=False,
    )
    op.create_index(
        "ix_student_reports_ready_for_smt_by_id",
        "student_reports",
        ["ready_for_smt_by_id"],
        unique=False,
    )
    op.create_index(
        "ix_student_reports_head_of_year_reviewed_by_id",
        "student_reports",
        ["head_of_year_reviewed_by_id"],
        unique=False,
    )
    op.create_index(
        "ix_student_reports_headteacher_reviewed_by_id",
        "student_reports",
        ["headteacher_reviewed_by_id"],
        unique=False,
    )

    # ------------------------------------------------------------------
    # Student-report foreign keys
    # ------------------------------------------------------------------
    op.create_foreign_key(
        "fk_student_reports_tutor_reviewed_by_id",
        "student_reports",
        "users",
        ["tutor_reviewed_by_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_student_reports_ready_for_smt_by_id",
        "student_reports",
        "users",
        ["ready_for_smt_by_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_student_reports_head_of_year_reviewed_by_id",
        "student_reports",
        "users",
        ["head_of_year_reviewed_by_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_student_reports_headteacher_reviewed_by_id",
        "student_reports",
        "users",
        ["headteacher_reviewed_by_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # Remove temporary defaults after existing rows have been populated.
    op.alter_column(
        "report_sessions",
        "display_order",
        server_default=None,
    )
    op.alter_column(
        "report_sessions",
        "reporting_mode",
        server_default=None,
    )


def downgrade() -> None:
    # ------------------------------------------------------------------
    # Student-report foreign keys
    # ------------------------------------------------------------------
    op.drop_constraint(
        "fk_student_reports_headteacher_reviewed_by_id",
        "student_reports",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_student_reports_head_of_year_reviewed_by_id",
        "student_reports",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_student_reports_ready_for_smt_by_id",
        "student_reports",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_student_reports_tutor_reviewed_by_id",
        "student_reports",
        type_="foreignkey",
    )

    # ------------------------------------------------------------------
    # Student-report indexes
    # ------------------------------------------------------------------
    op.drop_index(
        "ix_student_reports_headteacher_reviewed_by_id",
        table_name="student_reports",
    )
    op.drop_index(
        "ix_student_reports_head_of_year_reviewed_by_id",
        table_name="student_reports",
    )
    op.drop_index(
        "ix_student_reports_ready_for_smt_by_id",
        table_name="student_reports",
    )
    op.drop_index(
        "ix_student_reports_tutor_reviewed_by_id",
        table_name="student_reports",
    )
    op.drop_index(
        "ix_student_reports_subject_name",
        table_name="student_reports",
    )
    op.drop_index(
        "ix_student_reports_checkpoint_name",
        table_name="student_reports",
    )

    # ------------------------------------------------------------------
    # Student-report columns
    # ------------------------------------------------------------------
    op.drop_column("student_reports", "headteacher_reviewed_by_id")
    op.drop_column("student_reports", "headteacher_reviewed_at")
    op.drop_column("student_reports", "head_of_year_reviewed_by_id")
    op.drop_column("student_reports", "head_of_year_reviewed_at")
    op.drop_column("student_reports", "ready_for_smt_by_id")
    op.drop_column("student_reports", "ready_for_smt_at")
    op.drop_column("student_reports", "tutor_review_comments")
    op.drop_column("student_reports", "tutor_reviewed_by_id")
    op.drop_column("student_reports", "tutor_reviewed_at")
    op.drop_column("student_reports", "headteacher_comment")
    op.drop_column("student_reports", "head_of_year_comment")
    op.drop_column("student_reports", "tutor_comment")
    op.drop_column("student_reports", "ucas_predicted_grade")
    op.drop_column("student_reports", "exam_max_mark")
    op.drop_column("student_reports", "exam_mark")
    op.drop_column("student_reports", "exam_grade")
    op.drop_column("student_reports", "target_grade")
    op.drop_column("student_reports", "effort_grade")
    op.drop_column("student_reports", "attainment_grade")
    op.drop_column("student_reports", "next_steps")
    op.drop_column("student_reports", "subject_name")
    op.drop_column("student_reports", "checkpoint_name")

    # ------------------------------------------------------------------
    # Report sessions
    # ------------------------------------------------------------------
    op.drop_constraint(
        "fk_report_sessions_copied_from_session_id",
        "report_sessions",
        type_="foreignkey",
    )

    op.drop_index(
        "ix_report_sessions_copied_from_session_id",
        table_name="report_sessions",
    )
    op.drop_index(
        "ix_report_sessions_checkpoint_name",
        table_name="report_sessions",
    )

    op.drop_column("report_sessions", "updated_at")
    op.drop_column("report_sessions", "copied_from_session_id")
    op.drop_column("report_sessions", "show_progress_journey")
    op.drop_column("report_sessions", "show_previous_tutor_comments")
    op.drop_column("report_sessions", "show_previous_grades")
    op.drop_column("report_sessions", "include_headteacher_comment")
    op.drop_column("report_sessions", "include_head_of_year_comment")
    op.drop_column("report_sessions", "include_ucas_predicted_grade")
    op.drop_column("report_sessions", "include_exam_grade")
    op.drop_column("report_sessions", "published_at")
    op.drop_column("report_sessions", "reporting_mode")
    op.drop_column("report_sessions", "display_order")
    op.drop_column("report_sessions", "checkpoint_name")
