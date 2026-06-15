"""add report sessions

Revision ID: e8676cb4fa4e
Revises: 22751a73bad5
Create Date: 2026-06-15 19:32:41.643637+00:00

"""

from alembic import op
import sqlalchemy as sa

revision = "e8676cb4fa4e"
down_revision = "22751a73bad5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "report_sessions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("school_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("academic_year", sa.String(length=20), nullable=False),
        sa.Column("term", sa.String(length=50), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("include_work_covered", sa.Boolean(), nullable=False),
        sa.Column("include_student_comment", sa.Boolean(), nullable=False),
        sa.Column("include_exam_mark", sa.Boolean(), nullable=False),
        sa.Column("include_attainment_grade", sa.Boolean(), nullable=False),
        sa.Column("include_effort_grade", sa.Boolean(), nullable=False),
        sa.Column("include_target_grade", sa.Boolean(), nullable=False),
        sa.Column("include_next_steps", sa.Boolean(), nullable=False),
        sa.Column("include_tutor_comment", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["school_id"],
            ["schools.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        op.f("ix_report_sessions_school_id"),
        "report_sessions",
        ["school_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_report_sessions_school_id"),
        table_name="report_sessions",
    )

    op.drop_table("report_sessions")
