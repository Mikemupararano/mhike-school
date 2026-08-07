"""Make timetable assignment timestamps timezone aware.

Revision ID: 745d7131aa09
Revises: fabf44f4b7a8
Create Date: 2026-08-07 21:21:25.820611+00:00

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# Revision identifiers, used by Alembic.
revision = "745d7131aa09"
down_revision = "fabf44f4b7a8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Convert timetable-assignment timestamps to timezone-aware PostgreSQL
    timestamps.

    Existing timezone-naive values are explicitly interpreted as UTC.
    No unrelated schema changes belong in this migration.
    """

    op.alter_column(
        "timetable_assignments",
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
        "timetable_assignments",
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
    Restore timetable-assignment timestamps to timezone-naive UTC values.
    """

    op.alter_column(
        "timetable_assignments",
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
        "timetable_assignments",
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
