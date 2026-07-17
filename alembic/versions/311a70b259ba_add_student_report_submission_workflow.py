"""add student report submission workflow

Revision ID: 311a70b259ba
Revises: 2505932baf5e
Create Date: 2026-07-17 06:25:37.086976+00:00

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "311a70b259ba"
down_revision = "2505932baf5e"
branch_labels = None
depends_on = None


SUBMITTED_BY_FK_NAME = "fk_student_reports_submitted_by_id_users"
SUBMITTED_BY_INDEX_NAME = "ix_student_reports_submitted_by_id"


def upgrade() -> None:
    op.add_column(
        "student_reports",
        sa.Column(
            "submitted_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )

    op.add_column(
        "student_reports",
        sa.Column(
            "submitted_by_id",
            sa.Integer(),
            nullable=True,
        ),
    )

    op.add_column(
        "student_reports",
        sa.Column(
            "review_comments",
            sa.Text(),
            nullable=True,
        ),
    )

    op.create_index(
        SUBMITTED_BY_INDEX_NAME,
        "student_reports",
        ["submitted_by_id"],
        unique=False,
    )

    op.create_foreign_key(
        SUBMITTED_BY_FK_NAME,
        source_table="student_reports",
        referent_table="users",
        local_cols=["submitted_by_id"],
        remote_cols=["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        SUBMITTED_BY_FK_NAME,
        "student_reports",
        type_="foreignkey",
    )

    op.drop_index(
        SUBMITTED_BY_INDEX_NAME,
        table_name="student_reports",
    )

    op.drop_column(
        "student_reports",
        "review_comments",
    )

    op.drop_column(
        "student_reports",
        "submitted_by_id",
    )

    op.drop_column(
        "student_reports",
        "submitted_at",
    )
