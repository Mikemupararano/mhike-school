"""add user lifecycle fields

Revision ID: d3ed01427113
Revises: fdaaec6b809c
Create Date: 2026-04-14 21:25:12.221633+00:00
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "d3ed01427113"
down_revision = "fdaaec6b809c"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # =========================
    # Add lifecycle fields
    # =========================
    op.add_column(
        "users",
        sa.Column(
            "status",
            sa.String(length=50),
            nullable=False,
            server_default="active",
        ),
    )

    op.add_column(
        "users",
        sa.Column(
            "deletion_requested_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )

    op.add_column(
        "users",
        sa.Column(
            "deleted_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )

    op.add_column(
        "users",
        sa.Column(
            "anonymised_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )

    op.add_column(
        "users",
        sa.Column(
            "retention_expires_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )

    # =========================
    # Backfill existing data
    # =========================
    op.execute("UPDATE users SET status = 'active' WHERE status IS NULL")

    # =========================
    # Optional: remove default after backfill
    # (keeps DB clean; app handles default)
    # =========================
    op.alter_column(
        "users",
        "status",
        server_default=None,
    )


def downgrade() -> None:
    # =========================
    # Remove lifecycle fields
    # =========================
    op.drop_column("users", "retention_expires_at")
    op.drop_column("users", "anonymised_at")
    op.drop_column("users", "deleted_at")
    op.drop_column("users", "deletion_requested_at")
    op.drop_column("users", "status")
