"""add student reports

Revision ID: 228d09de8ed7
Revises: 7115d2a95b40
Create Date: 2026-06-03 20:58:00.955076+00:00

"""

from alembic import op
import sqlalchemy as sa

revision = "228d09de8ed7"
down_revision = "7115d2a95b40"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "student_reports",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("school_id", sa.Integer(), nullable=False),
        sa.Column("student_id", sa.Integer(), nullable=False),
        sa.Column("teacher_id", sa.Integer(), nullable=True),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("report_text", sa.Text(), nullable=False),
        sa.Column("grade", sa.String(length=50), nullable=True),
        sa.Column("academic_year", sa.String(length=20), nullable=False),
        sa.Column("term", sa.String(length=50), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["school_id"],
            ["schools.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["student_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["teacher_id"],
            ["users.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        op.f("ix_student_reports_academic_year"),
        "student_reports",
        ["academic_year"],
        unique=False,
    )

    op.create_index(
        op.f("ix_student_reports_school_id"),
        "student_reports",
        ["school_id"],
        unique=False,
    )

    op.create_index(
        op.f("ix_student_reports_student_id"),
        "student_reports",
        ["student_id"],
        unique=False,
    )

    op.create_index(
        op.f("ix_student_reports_teacher_id"),
        "student_reports",
        ["teacher_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_student_reports_teacher_id"),
        table_name="student_reports",
    )

    op.drop_index(
        op.f("ix_student_reports_student_id"),
        table_name="student_reports",
    )

    op.drop_index(
        op.f("ix_student_reports_school_id"),
        table_name="student_reports",
    )

    op.drop_index(
        op.f("ix_student_reports_academic_year"),
        table_name="student_reports",
    )

    op.drop_table("student_reports")
