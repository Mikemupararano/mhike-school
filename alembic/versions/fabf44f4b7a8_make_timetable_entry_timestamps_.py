"""Make timetable timestamps timezone aware.

Revision ID: fabf44f4b7a8
Revises: bf1e0a53f9c0
Create Date: 2026-08-07 20:01:28.582930+00:00

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# Revision identifiers, used by Alembic.
revision = "fabf44f4b7a8"
down_revision = "bf1e0a53f9c0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Convert timetable timestamp columns to timezone-aware PostgreSQL
    timestamps.

    Existing naive timestamp values are interpreted as UTC explicitly.
    This keeps historical values stable while bringing the database schema
    into line with the application's timezone-aware UTC datetime handling.

    No unrelated schema changes belong in this migration.
    """

    op.alter_column(
        "timetable_entries",
        "created_at",
        existing_type=postgresql.TIMESTAMP(
            timezone=False,
        ),
        type_=sa.DateTime(
            timezone=True,
        ),
        existing_nullable=False,
        postgresql_using=("created_at AT TIME ZONE 'UTC'"),
    )

    op.alter_column(
        "timetable_entries",
        "updated_at",
        existing_type=postgresql.TIMESTAMP(
            timezone=False,
        ),
        type_=sa.DateTime(
            timezone=True,
        ),
        existing_nullable=False,
        postgresql_using=("updated_at AT TIME ZONE 'UTC'"),
    )

    op.alter_column(
        "timetables",
        "created_at",
        existing_type=postgresql.TIMESTAMP(
            timezone=False,
        ),
        type_=sa.DateTime(
            timezone=True,
        ),
        existing_nullable=False,
        postgresql_using=("created_at AT TIME ZONE 'UTC'"),
    )

    op.alter_column(
        "timetables",
        "updated_at",
        existing_type=postgresql.TIMESTAMP(
            timezone=False,
        ),
        type_=sa.DateTime(
            timezone=True,
        ),
        existing_nullable=False,
        postgresql_using=("updated_at AT TIME ZONE 'UTC'"),
    )


def downgrade() -> None:
    """
    Restore the timetable timestamp columns to timezone-naive UTC values.

    UTC is explicitly selected before removing timezone information so that
    downgrading does not depend on the PostgreSQL session timezone.
    """

    op.alter_column(
        "timetables",
        "updated_at",
        existing_type=postgresql.TIMESTAMP(
            timezone=True,
        ),
        type_=sa.DateTime(
            timezone=False,
        ),
        existing_nullable=False,
        postgresql_using=("updated_at AT TIME ZONE 'UTC'"),
    )

    op.alter_column(
        "timetables",
        "created_at",
        existing_type=postgresql.TIMESTAMP(
            timezone=True,
        ),
        type_=sa.DateTime(
            timezone=False,
        ),
        existing_nullable=False,
        postgresql_using=("created_at AT TIME ZONE 'UTC'"),
    )

    op.alter_column(
        "timetable_entries",
        "updated_at",
        existing_type=postgresql.TIMESTAMP(
            timezone=True,
        ),
        type_=sa.DateTime(
            timezone=False,
        ),
        existing_nullable=False,
        postgresql_using=("updated_at AT TIME ZONE 'UTC'"),
    )

    op.alter_column(
        "timetable_entries",
        "created_at",
        existing_type=postgresql.TIMESTAMP(
            timezone=True,
        ),
        type_=sa.DateTime(
            timezone=False,
        ),
        existing_nullable=False,
        postgresql_using=("created_at AT TIME ZONE 'UTC'"),
    )
