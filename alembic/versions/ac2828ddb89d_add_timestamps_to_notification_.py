"""add timestamps to notification preferences

Revision ID: ac2828ddb89d
Revises: 5002042dd468
Create Date: 2026-05-24 11:02:55.299292+00:00

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "ac2828ddb89d"
down_revision = "5002042dd468"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "notification_preferences",
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )

    op.add_column(
        "notification_preferences",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column(
        "notification_preferences",
        "updated_at",
    )

    op.drop_column(
        "notification_preferences",
        "created_at",
    )
