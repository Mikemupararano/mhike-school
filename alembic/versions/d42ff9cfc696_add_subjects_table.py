"""add subjects table

Revision ID: d42ff9cfc696
Revises: 3c4f6c39f198
Create Date: 2026-08-10 20:05:25.793691+00:00
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "d42ff9cfc696"
down_revision = "3c4f6c39f198"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create the canonical school-scoped subjects table."""

    op.create_table(
        "subjects",
        sa.Column(
            "id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "school_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "name",
            sa.String(length=150),
            nullable=False,
        ),
        sa.Column(
            "code",
            sa.String(length=50),
            nullable=True,
        ),
        sa.Column(
            "description",
            sa.Text(),
            nullable=True,
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
        ),
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
        sa.PrimaryKeyConstraint(
            "id",
        ),
        sa.UniqueConstraint(
            "school_id",
            "code",
            name="uq_subject_school_code",
        ),
        sa.UniqueConstraint(
            "school_id",
            "name",
            name="uq_subject_school_name",
        ),
    )

    op.create_index(
        op.f("ix_subjects_is_active"),
        "subjects",
        ["is_active"],
        unique=False,
    )

    op.create_index(
        op.f("ix_subjects_school_id"),
        "subjects",
        ["school_id"],
        unique=False,
    )


def downgrade() -> None:
    """Remove the canonical subjects table."""

    op.drop_index(
        op.f("ix_subjects_school_id"),
        table_name="subjects",
    )

    op.drop_index(
        op.f("ix_subjects_is_active"),
        table_name="subjects",
    )

    op.drop_table(
        "subjects",
    )
