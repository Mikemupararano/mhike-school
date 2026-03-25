"""add full_name and is_active to users

Revision ID: 7695c925335e
Revises: 515bfe2197e9
Create Date: 2026-03-22 19:11:25.370832+00:00

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "7695c925335e"
down_revision = "515bfe2197e9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("full_name", sa.String(length=255), nullable=True))
    op.add_column(
        "users",
        sa.Column(
            "is_active", sa.Boolean(), nullable=True, server_default=sa.text("true")
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "is_active")
    op.drop_column("users", "full_name")
