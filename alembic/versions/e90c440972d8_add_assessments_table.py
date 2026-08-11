"""add assessments table

Revision ID: e90c440972d8
Revises: 89f554d0dbd3
Create Date: 2026-08-10 22:05:54.947311+00:00
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "e90c440972d8"
down_revision = "89f554d0dbd3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create the assessments table."""

    op.create_table(
        "assessments",
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
            "course_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "created_by_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "title",
            sa.String(length=255),
            nullable=False,
        ),
        sa.Column(
            "description",
            sa.Text(),
            nullable=True,
        ),
        sa.Column(
            "assessment_type",
            sa.String(length=100),
            nullable=True,
        ),
        sa.Column(
            "academic_year",
            sa.String(length=50),
            nullable=True,
        ),
        sa.Column(
            "term",
            sa.String(length=100),
            nullable=True,
        ),
        sa.Column(
            "status",
            sa.Enum(
                "draft",
                "published",
                "closed",
                "archived",
                name="assessment_status",
                native_enum=False,
            ),
            nullable=False,
        ),
        sa.Column(
            "anonymous_marking",
            sa.Boolean(),
            nullable=False,
        ),
        sa.Column(
            "scheduled_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "closes_at",
            sa.DateTime(timezone=True),
            nullable=True,
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
            ["course_id"],
            ["courses.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_id"],
            ["users.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["school_id"],
            ["schools.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "id",
        ),
    )

    op.create_index(
        op.f("ix_assessments_course_id"),
        "assessments",
        ["course_id"],
        unique=False,
    )

    op.create_index(
        op.f("ix_assessments_created_by_id"),
        "assessments",
        ["created_by_id"],
        unique=False,
    )

    op.create_index(
        op.f("ix_assessments_school_id"),
        "assessments",
        ["school_id"],
        unique=False,
    )

    op.create_index(
        op.f("ix_assessments_status"),
        "assessments",
        ["status"],
        unique=False,
    )

    op.create_index(
        op.f("ix_assessments_title"),
        "assessments",
        ["title"],
        unique=False,
    )


def downgrade() -> None:
    """Remove the assessments table."""

    op.drop_index(
        op.f("ix_assessments_title"),
        table_name="assessments",
    )

    op.drop_index(
        op.f("ix_assessments_status"),
        table_name="assessments",
    )

    op.drop_index(
        op.f("ix_assessments_school_id"),
        table_name="assessments",
    )

    op.drop_index(
        op.f("ix_assessments_created_by_id"),
        table_name="assessments",
    )

    op.drop_index(
        op.f("ix_assessments_course_id"),
        table_name="assessments",
    )

    op.drop_table(
        "assessments",
    )
