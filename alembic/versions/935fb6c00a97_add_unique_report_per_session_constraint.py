"""add unique report per session constraint

Revision ID: 935fb6c00a97
Revises: 6f3d42b947e0
Create Date: 2026-06-19 19:14:03.887409+00:00

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "935fb6c00a97"
down_revision = "6f3d42b947e0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_student_report_session_teacher",
        "student_reports",
        [
            "school_id",
            "student_id",
            "teacher_id",
            "report_session_id",
        ],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_student_report_session_teacher",
        "student_reports",
        type_="unique",
    )
