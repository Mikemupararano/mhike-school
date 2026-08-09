"""Make attendance timestamps timezone aware.

Revision ID: 3c4f6c39f198
Revises: 745d7131aa09
Create Date: 2026-08-09 20:44:23.994786+00:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "3c4f6c39f198"
down_revision = "745d7131aa09"
branch_labels = None
depends_on = None


def _upgrade_timestamp_column(
    table_name: str,
    column_name: str,
    *,
    nullable: bool,
) -> None:
    """
    Convert a PostgreSQL timestamp-without-time-zone column to
    timestamp-with-time-zone.

    Existing naive values are explicitly interpreted as UTC before being
    converted to timestamptz. This preserves the application's established
    convention that persisted timestamps represent UTC.
    """

    op.alter_column(
        table_name,
        column_name,
        existing_type=postgresql.TIMESTAMP(timezone=False),
        type_=sa.DateTime(timezone=True),
        existing_nullable=nullable,
        postgresql_using=(f"{column_name} AT TIME ZONE 'UTC'"),
    )


def _downgrade_timestamp_column(
    table_name: str,
    column_name: str,
    *,
    nullable: bool,
) -> None:
    """
    Convert a PostgreSQL timestamp-with-time-zone column back to
    timestamp-without-time-zone.

    Values are first represented in UTC so the downgrade preserves the same
    wall-clock UTC value rather than depending on the database session's
    timezone.
    """

    op.alter_column(
        table_name,
        column_name,
        existing_type=postgresql.TIMESTAMP(timezone=True),
        type_=sa.DateTime(timezone=False),
        existing_nullable=nullable,
        postgresql_using=(f"{column_name} AT TIME ZONE 'UTC'"),
    )


def upgrade() -> None:
    """
    Make attendance-domain timestamps timezone-aware.

    Only the attendance and absence timestamp columns are modified here.
    Unrelated schema differences discovered by Alembic autogenerate are
    intentionally excluded from this migration.
    """

    # Absence requests.
    _upgrade_timestamp_column(
        "absence_requests",
        "created_at",
        nullable=False,
    )
    _upgrade_timestamp_column(
        "absence_requests",
        "updated_at",
        nullable=False,
    )
    _upgrade_timestamp_column(
        "absence_requests",
        "reviewed_at",
        nullable=True,
    )

    # Attendance records.
    _upgrade_timestamp_column(
        "attendance_records",
        "created_at",
        nullable=False,
    )
    _upgrade_timestamp_column(
        "attendance_records",
        "updated_at",
        nullable=False,
    )

    # Attendance sessions.
    _upgrade_timestamp_column(
        "attendance_sessions",
        "submitted_at",
        nullable=True,
    )
    _upgrade_timestamp_column(
        "attendance_sessions",
        "created_at",
        nullable=False,
    )
    _upgrade_timestamp_column(
        "attendance_sessions",
        "updated_at",
        nullable=False,
    )


def downgrade() -> None:
    """
    Restore attendance-domain timestamps to timezone-naive UTC columns.
    """

    # Reverse in dependency-neutral order.

    # Attendance sessions.
    _downgrade_timestamp_column(
        "attendance_sessions",
        "updated_at",
        nullable=False,
    )
    _downgrade_timestamp_column(
        "attendance_sessions",
        "created_at",
        nullable=False,
    )
    _downgrade_timestamp_column(
        "attendance_sessions",
        "submitted_at",
        nullable=True,
    )

    # Attendance records.
    _downgrade_timestamp_column(
        "attendance_records",
        "updated_at",
        nullable=False,
    )
    _downgrade_timestamp_column(
        "attendance_records",
        "created_at",
        nullable=False,
    )

    # Absence requests.
    _downgrade_timestamp_column(
        "absence_requests",
        "reviewed_at",
        nullable=True,
    )
    _downgrade_timestamp_column(
        "absence_requests",
        "updated_at",
        nullable=False,
    )
    _downgrade_timestamp_column(
        "absence_requests",
        "created_at",
        nullable=False,
    )
