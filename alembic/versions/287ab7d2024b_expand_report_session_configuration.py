"""expand report session configuration

Revision ID: 287ab7d2024b
Revises: 6cc156dd916e
Create Date: 2026-07-21 11:50:40.056835+00:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "287ab7d2024b"
down_revision = "6cc156dd916e"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # Remove the retired report-memory table.
    #
    # This is intentionally destructive. The application now uses
    # StudentReport as the single source of truth.
    # ------------------------------------------------------------------

    op.drop_index(
        op.f("ix_report_memory_id"),
        table_name="report_memory",
    )
    op.drop_index(
        op.f("ix_report_memory_school_id"),
        table_name="report_memory",
    )
    op.drop_index(
        op.f("ix_report_memory_source_report_id"),
        table_name="report_memory",
    )
    op.drop_index(
        op.f("ix_report_memory_subject"),
        table_name="report_memory",
    )
    op.drop_index(
        op.f("ix_report_memory_teacher_id"),
        table_name="report_memory",
    )
    op.drop_table("report_memory")

    # ------------------------------------------------------------------
    # Expand report-session configuration.
    # ------------------------------------------------------------------

    op.add_column(
        "report_sessions",
        sa.Column(
            "enable_report_generation",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
    )

    op.add_column(
        "report_sessions",
        sa.Column(
            "include_school_name",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
    )
    op.add_column(
        "report_sessions",
        sa.Column(
            "include_school_logo",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
    )
    op.add_column(
        "report_sessions",
        sa.Column(
            "include_teacher_name",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
    )
    op.add_column(
        "report_sessions",
        sa.Column(
            "include_subject_name",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
    )

    op.add_column(
        "report_sessions",
        sa.Column(
            "include_gcse_predicted_grade",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
    )
    op.add_column(
        "report_sessions",
        sa.Column(
            "include_attendance",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
    )
    op.add_column(
        "report_sessions",
        sa.Column(
            "include_behaviour",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
    )

    op.add_column(
        "report_sessions",
        sa.Column(
            "require_student_comment",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
    )
    op.add_column(
        "report_sessions",
        sa.Column(
            "require_effort_grade",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
    )
    op.add_column(
        "report_sessions",
        sa.Column(
            "require_attainment_grade",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
    )
    op.add_column(
        "report_sessions",
        sa.Column(
            "require_target_grade",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
    )

    op.add_column(
        "report_sessions",
        sa.Column(
            "require_exam_mark",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
    )
    op.add_column(
        "report_sessions",
        sa.Column(
            "require_exam_grade",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
    )
    op.add_column(
        "report_sessions",
        sa.Column(
            "require_gcse_predicted_grade",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
    )
    op.add_column(
        "report_sessions",
        sa.Column(
            "require_ucas_predicted_grade",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
    )
    op.add_column(
        "report_sessions",
        sa.Column(
            "require_next_steps",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
    )
    op.add_column(
        "report_sessions",
        sa.Column(
            "require_tutor_comment",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
    )
    op.add_column(
        "report_sessions",
        sa.Column(
            "require_head_of_year_comment",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
    )
    op.add_column(
        "report_sessions",
        sa.Column(
            "require_headteacher_comment",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
    )

    op.add_column(
        "report_sessions",
        sa.Column(
            "allow_teacher_edit_after_submission",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
    )
    op.add_column(
        "report_sessions",
        sa.Column(
            "allow_smt_edit_after_approval",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
    )

    # Existing sessions may exclude one of the fields whose new
    # require_* setting defaults to true. Align those requirement flags
    # with the existing include_* settings before application validation
    # reads the records.
    op.execute(sa.text("""
            UPDATE report_sessions
            SET
                require_student_comment = include_student_comment,
                require_effort_grade = include_effort_grade,
                require_attainment_grade = include_attainment_grade,
                require_target_grade = include_target_grade
            """))

    op.create_index(
        op.f("ix_report_sessions_academic_year"),
        "report_sessions",
        ["academic_year"],
        unique=False,
    )
    op.create_index(
        op.f("ix_report_sessions_active"),
        "report_sessions",
        ["active"],
        unique=False,
    )
    op.create_index(
        op.f("ix_report_sessions_reporting_mode"),
        "report_sessions",
        ["reporting_mode"],
        unique=False,
    )

    # ------------------------------------------------------------------
    # Expand StudentReport.
    # ------------------------------------------------------------------

    op.add_column(
        "student_reports",
        sa.Column(
            "gcse_predicted_grade",
            sa.String(length=50),
            nullable=True,
        ),
    )

    op.drop_constraint(
        op.f("uq_student_report_session_teacher"),
        "student_reports",
        type_="unique",
    )
    op.create_unique_constraint(
        "uq_student_report_session_teacher_subject",
        "student_reports",
        [
            "school_id",
            "student_id",
            "teacher_id",
            "report_session_id",
            "subject_name",
        ],
    )

    # ------------------------------------------------------------------
    # Align the users.school_id foreign key with the current model.
    # ------------------------------------------------------------------

    op.drop_constraint(
        op.f("users_school_id_fkey"),
        "users",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "users_school_id_fkey",
        "users",
        "schools",
        ["school_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    # ------------------------------------------------------------------
    # Restore the previous users.school_id foreign key.
    # ------------------------------------------------------------------

    op.drop_constraint(
        "users_school_id_fkey",
        "users",
        type_="foreignkey",
    )
    op.create_foreign_key(
        op.f("users_school_id_fkey"),
        "users",
        "schools",
        ["school_id"],
        ["id"],
    )

    # ------------------------------------------------------------------
    # Restore the previous StudentReport structure.
    # ------------------------------------------------------------------

    op.drop_constraint(
        "uq_student_report_session_teacher_subject",
        "student_reports",
        type_="unique",
    )
    op.create_unique_constraint(
        op.f("uq_student_report_session_teacher"),
        "student_reports",
        [
            "school_id",
            "student_id",
            "teacher_id",
            "report_session_id",
        ],
        postgresql_nulls_not_distinct=False,
    )
    op.drop_column(
        "student_reports",
        "gcse_predicted_grade",
    )

    # ------------------------------------------------------------------
    # Remove expanded report-session configuration.
    # ------------------------------------------------------------------

    op.drop_index(
        op.f("ix_report_sessions_reporting_mode"),
        table_name="report_sessions",
    )
    op.drop_index(
        op.f("ix_report_sessions_active"),
        table_name="report_sessions",
    )
    op.drop_index(
        op.f("ix_report_sessions_academic_year"),
        table_name="report_sessions",
    )

    op.drop_column(
        "report_sessions",
        "allow_smt_edit_after_approval",
    )
    op.drop_column(
        "report_sessions",
        "allow_teacher_edit_after_submission",
    )

    op.drop_column(
        "report_sessions",
        "require_headteacher_comment",
    )
    op.drop_column(
        "report_sessions",
        "require_head_of_year_comment",
    )
    op.drop_column(
        "report_sessions",
        "require_tutor_comment",
    )
    op.drop_column(
        "report_sessions",
        "require_next_steps",
    )
    op.drop_column(
        "report_sessions",
        "require_ucas_predicted_grade",
    )
    op.drop_column(
        "report_sessions",
        "require_gcse_predicted_grade",
    )
    op.drop_column(
        "report_sessions",
        "require_exam_grade",
    )
    op.drop_column(
        "report_sessions",
        "require_exam_mark",
    )
    op.drop_column(
        "report_sessions",
        "require_target_grade",
    )
    op.drop_column(
        "report_sessions",
        "require_attainment_grade",
    )
    op.drop_column(
        "report_sessions",
        "require_effort_grade",
    )
    op.drop_column(
        "report_sessions",
        "require_student_comment",
    )

    op.drop_column(
        "report_sessions",
        "include_behaviour",
    )
    op.drop_column(
        "report_sessions",
        "include_attendance",
    )
    op.drop_column(
        "report_sessions",
        "include_gcse_predicted_grade",
    )
    op.drop_column(
        "report_sessions",
        "include_subject_name",
    )
    op.drop_column(
        "report_sessions",
        "include_teacher_name",
    )
    op.drop_column(
        "report_sessions",
        "include_school_logo",
    )
    op.drop_column(
        "report_sessions",
        "include_school_name",
    )
    op.drop_column(
        "report_sessions",
        "enable_report_generation",
    )

    # ------------------------------------------------------------------
    # Recreate the retired report-memory table.
    #
    # Downgrading restores the table structure only. Data deleted by the
    # upgrade cannot be recovered automatically.
    # ------------------------------------------------------------------

    op.create_table(
        "report_memory",
        sa.Column(
            "id",
            sa.INTEGER(),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column(
            "school_id",
            sa.INTEGER(),
            autoincrement=False,
            nullable=False,
        ),
        sa.Column(
            "subject",
            sa.VARCHAR(length=100),
            autoincrement=False,
            nullable=False,
        ),
        sa.Column(
            "year_group",
            sa.VARCHAR(length=50),
            autoincrement=False,
            nullable=True,
        ),
        sa.Column(
            "topics_studied",
            sa.TEXT(),
            autoincrement=False,
            nullable=True,
        ),
        sa.Column(
            "teacher_notes",
            sa.TEXT(),
            autoincrement=False,
            nullable=True,
        ),
        sa.Column(
            "generated_report",
            sa.TEXT(),
            autoincrement=False,
            nullable=True,
        ),
        sa.Column(
            "final_report",
            sa.TEXT(),
            autoincrement=False,
            nullable=False,
        ),
        sa.Column(
            "source_report_id",
            sa.INTEGER(),
            autoincrement=False,
            nullable=True,
        ),
        sa.Column(
            "approved",
            sa.BOOLEAN(),
            server_default=sa.text("true"),
            autoincrement=False,
            nullable=False,
        ),
        sa.Column(
            "created_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            autoincrement=False,
            nullable=False,
        ),
        sa.Column(
            "teacher_id",
            sa.INTEGER(),
            autoincrement=False,
            nullable=True,
        ),
        sa.Column(
            "teacher_name",
            sa.VARCHAR(length=255),
            autoincrement=False,
            nullable=True,
        ),
        sa.ForeignKeyConstraint(
            ["school_id"],
            ["schools.id"],
            name=op.f("report_memory_school_id_fkey"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["source_report_id"],
            ["student_reports.id"],
            name=op.f("report_memory_source_report_id_fkey"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["teacher_id"],
            ["users.id"],
            name=op.f("fk_report_memory_teacher_id"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint(
            "id",
            name=op.f("report_memory_pkey"),
        ),
    )

    op.create_index(
        op.f("ix_report_memory_teacher_id"),
        "report_memory",
        ["teacher_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_report_memory_subject"),
        "report_memory",
        ["subject"],
        unique=False,
    )
    op.create_index(
        op.f("ix_report_memory_source_report_id"),
        "report_memory",
        ["source_report_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_report_memory_school_id"),
        "report_memory",
        ["school_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_report_memory_id"),
        "report_memory",
        ["id"],
        unique=False,
    )
