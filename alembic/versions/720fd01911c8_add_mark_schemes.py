"""add mark schemes

Revision ID: 720fd01911c8
Revises: 34e9a2dd71ad
Create Date: 2026-08-11 09:28:15.385448+00:00
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "720fd01911c8"
down_revision = "34e9a2dd71ad"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create mark schemes and mark-scheme items."""

    op.create_table(
        "mark_schemes",
        sa.Column(
            "id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "question_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "title",
            sa.String(length=255),
            nullable=True,
        ),
        sa.Column(
            "general_guidance",
            sa.Text(),
            nullable=True,
        ),
        sa.Column(
            "allow_alternative_answers",
            sa.Boolean(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["question_id"],
            ["assessment_questions.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "id",
        ),
        sa.UniqueConstraint(
            "question_id",
            name="uq_mark_scheme_question",
        ),
    )

    op.create_index(
        op.f("ix_mark_schemes_question_id"),
        "mark_schemes",
        ["question_id"],
        unique=False,
    )

    op.create_table(
        "mark_scheme_items",
        sa.Column(
            "id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "mark_scheme_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "code",
            sa.String(length=50),
            nullable=True,
        ),
        sa.Column(
            "item_type",
            sa.Enum(
                "mark",
                "method",
                "accuracy",
                "independent",
                "assessment_objective",
                "level",
                "other",
                name="mark_scheme_item_type",
                native_enum=False,
            ),
            nullable=False,
        ),
        sa.Column(
            "description",
            sa.Text(),
            nullable=False,
        ),
        sa.Column(
            "marks",
            sa.Numeric(
                precision=8,
                scale=2,
            ),
            nullable=False,
        ),
        sa.Column(
            "order",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "is_optional",
            sa.Boolean(),
            nullable=False,
        ),
        sa.Column(
            "alternative_group",
            sa.String(length=100),
            nullable=True,
        ),
        sa.Column(
            "examiner_notes",
            sa.Text(),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(
            ["mark_scheme_id"],
            ["mark_schemes.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "id",
        ),
        sa.UniqueConstraint(
            "mark_scheme_id",
            "order",
            name="uq_mark_scheme_item_order",
        ),
    )

    op.create_index(
        op.f("ix_mark_scheme_items_item_type"),
        "mark_scheme_items",
        ["item_type"],
        unique=False,
    )

    op.create_index(
        op.f("ix_mark_scheme_items_mark_scheme_id"),
        "mark_scheme_items",
        ["mark_scheme_id"],
        unique=False,
    )


def downgrade() -> None:
    """Remove mark-scheme items and mark schemes."""

    op.drop_index(
        op.f("ix_mark_scheme_items_mark_scheme_id"),
        table_name="mark_scheme_items",
    )

    op.drop_index(
        op.f("ix_mark_scheme_items_item_type"),
        table_name="mark_scheme_items",
    )

    op.drop_table(
        "mark_scheme_items",
    )

    op.drop_index(
        op.f("ix_mark_schemes_question_id"),
        table_name="mark_schemes",
    )

    op.drop_table(
        "mark_schemes",
    )
