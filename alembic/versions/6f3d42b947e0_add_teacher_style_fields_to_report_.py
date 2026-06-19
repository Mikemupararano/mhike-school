"""add teacher style fields to report memory

Revision ID: 6f3d42b947e0
Revises: dc0142301987
Create Date: 2026-06-19 18:15:08.311914+00:00

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "6f3d42b947e0"
down_revision = "dc0142301987"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "report_memory",
        sa.Column("teacher_id", sa.Integer(), nullable=True),
    )
    op.add_column(
        "report_memory",
        sa.Column("teacher_name", sa.String(length=255), nullable=True),
    )

    op.create_foreign_key(
        "fk_report_memory_teacher_id",
        "report_memory",
        "users",
        ["teacher_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.create_index(
        "ix_report_memory_teacher_id",
        "report_memory",
        ["teacher_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_report_memory_teacher_id",
        table_name="report_memory",
    )
    op.drop_constraint(
        "fk_report_memory_teacher_id",
        "report_memory",
        type_="foreignkey",
    )
    op.drop_column("report_memory", "teacher_name")
    op.drop_column("report_memory", "teacher_id")
