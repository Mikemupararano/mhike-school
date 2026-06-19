"""add report generation feedback fields

Revision ID: 2505932baf5e
Revises: 935fb6c00a97
Create Date: 2026-06-19 20:01:58.517376+00:00

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "2505932baf5e"
down_revision = "935fb6c00a97"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "student_reports",
        sa.Column("work_covered", sa.Text(), nullable=True),
    )
    op.add_column(
        "student_reports",
        sa.Column("teacher_notes", sa.Text(), nullable=True),
    )
    op.add_column(
        "student_reports",
        sa.Column("generated_report_text", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("student_reports", "generated_report_text")
    op.drop_column("student_reports", "teacher_notes")
    op.drop_column("student_reports", "work_covered")
