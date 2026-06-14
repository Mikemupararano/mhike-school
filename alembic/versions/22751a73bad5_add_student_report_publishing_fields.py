"""add student report publishing fields

Revision ID: 22751a73bad5
Revises: e3a7f95e9d56
Create Date: 2026-06-14 20:16:09.096583+00:00

"""

from alembic import op
import sqlalchemy as sa


revision = "22751a73bad5"
down_revision = "e3a7f95e9d56"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "student_reports",
        sa.Column(
            "published",
            sa.Boolean(),
            server_default="false",
            nullable=False,
        ),
    )

    op.add_column(
        "student_reports",
        sa.Column(
            "published_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )

    op.add_column(
        "student_reports",
        sa.Column(
            "published_by_id",
            sa.Integer(),
            nullable=True,
        ),
    )

    op.create_index(
        op.f("ix_student_reports_published"),
        "student_reports",
        ["published"],
        unique=False,
    )

    op.create_index(
        op.f("ix_student_reports_published_by_id"),
        "student_reports",
        ["published_by_id"],
        unique=False,
    )

    op.create_foreign_key(
        "fk_student_reports_published_by_id_users",
        "student_reports",
        "users",
        ["published_by_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_student_reports_published_by_id_users",
        "student_reports",
        type_="foreignkey",
    )

    op.drop_index(
        op.f("ix_student_reports_published_by_id"),
        table_name="student_reports",
    )

    op.drop_index(
        op.f("ix_student_reports_published"),
        table_name="student_reports",
    )

    op.drop_column("student_reports", "published_by_id")
    op.drop_column("student_reports", "published_at")
    op.drop_column("student_reports", "published")