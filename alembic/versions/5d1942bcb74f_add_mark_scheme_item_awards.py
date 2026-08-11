"""add mark scheme item awards

Revision ID: 5d1942bcb74f
Revises: c63da6b69a91
Create Date: 2026-08-11 14:14:04.257466+00:00
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.

revision = "5d1942bcb74f"
down_revision = "c63da6b69a91"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create mark-scheme item awards."""

    op.create_table(
        "mark_scheme_item_awards",
        sa.Column(
            "id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "marking_decision_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "mark_scheme_item_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "marks_awarded",
            sa.Numeric(
                precision=8,
                scale=2,
            ),
            nullable=False,
        ),
        sa.Column(
            "marker_note",
            sa.Text(),
            nullable=True,
        ),
        sa.Column(
            "awarded_by_id",
            sa.Integer(),
            nullable=True,
        ),
        sa.Column(
            "awarded_at",
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
            ["awarded_by_id"],
            ["users.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["mark_scheme_item_id"],
            ["mark_scheme_items.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["marking_decision_id"],
            ["marking_decisions.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "id",
        ),
        sa.UniqueConstraint(
            "marking_decision_id",
            "mark_scheme_item_id",
            name="uq_mark_scheme_item_award_decision_item",
        ),
    )

    op.create_index(
        op.f("ix_mark_scheme_item_awards_awarded_by_id"),
        "mark_scheme_item_awards",
        ["awarded_by_id"],
        unique=False,
    )

    op.create_index(
        op.f("ix_mark_scheme_item_awards_mark_scheme_item_id"),
        "mark_scheme_item_awards",
        ["mark_scheme_item_id"],
        unique=False,
    )

    op.create_index(
        op.f("ix_mark_scheme_item_awards_marking_decision_id"),
        "mark_scheme_item_awards",
        ["marking_decision_id"],
        unique=False,
    )


def downgrade() -> None:
    """Remove mark-scheme item awards."""

    op.drop_index(
        op.f("ix_mark_scheme_item_awards_marking_decision_id"),
        table_name="mark_scheme_item_awards",
    )

    op.drop_index(
        op.f("ix_mark_scheme_item_awards_mark_scheme_item_id"),
        table_name="mark_scheme_item_awards",
    )

    op.drop_index(
        op.f("ix_mark_scheme_item_awards_awarded_by_id"),
        table_name="mark_scheme_item_awards",
    )

    op.drop_table(
        "mark_scheme_item_awards",
    )
