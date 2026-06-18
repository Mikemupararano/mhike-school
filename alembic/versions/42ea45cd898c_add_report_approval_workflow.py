"""add report approval workflow

Revision ID: 42ea45cd898c
Revises: c4a8f4af691f
Create Date: 2026-06-17 10:46:44.978055+00:00

"""

from alembic import op
import sqlalchemy as sa


revision = "42ea45cd898c"
down_revision = "c4a8f4af691f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "student_reports",
        sa.Column(
            "status",
            sa.String(length=50),
            nullable=False,
            server_default="draft",
        ),
    )

    op.add_column(
        "student_reports",
        sa.Column(
            "reviewed_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )

    op.add_column(
        "student_reports",
        sa.Column(
            "reviewed_by_id",
            sa.Integer(),
            nullable=True,
        ),
    )

    op.create_index(
        "ix_student_reports_status",
        "student_reports",
        ["status"],
        unique=False,
    )

    op.create_index(
        "ix_student_reports_reviewed_by_id",
        "student_reports",
        ["reviewed_by_id"],
        unique=False,
    )

    op.create_foreign_key(
        "fk_student_reports_reviewed_by_id_users",
        "student_reports",
        "users",
        ["reviewed_by_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_student_reports_reviewed_by_id_users",
        "student_reports",
        type_="foreignkey",
    )

    op.drop_index(
        "ix_student_reports_reviewed_by_id",
        table_name="student_reports",
    )

    op.drop_index(
        "ix_student_reports_status",
        table_name="student_reports",
    )

    op.drop_column("student_reports", "reviewed_by_id")
    op.drop_column("student_reports", "reviewed_at")
    op.drop_column("student_reports", "status")