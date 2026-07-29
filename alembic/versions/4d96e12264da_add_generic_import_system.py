"""Add generic import system.

Revision ID: 4d96e12264da
Revises: 8204770d7934
Create Date: 2026-07-29 16:40:13.878768+00:00
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

# Revision identifiers, used by Alembic.
revision: str = "4d96e12264da"
down_revision: str | None = "8204770d7934"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create the generic import batch and row tables."""

    op.create_table(
        "import_batches",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("school_id", sa.Integer(), nullable=False),
        sa.Column("uploaded_by_id", sa.Integer(), nullable=False),
        sa.Column("import_type", sa.String(length=100), nullable=False),
        sa.Column(
            "operation",
            sa.Enum(
                "create",
                "update",
                "upsert",
                name="import_operation",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum(
                "uploaded",
                "parsing",
                "validating",
                "ready",
                "queued",
                "processing",
                "completed",
                "completed_with_errors",
                "failed",
                "cancelled",
                name="import_status",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("stored_filename", sa.String(length=500), nullable=True),
        sa.Column("file_format", sa.String(length=20), nullable=True),
        sa.Column("mime_type", sa.String(length=150), nullable=True),
        sa.Column("file_size_bytes", sa.BigInteger(), nullable=True),
        sa.Column("file_hash", sa.String(length=128), nullable=True),
        sa.Column("column_mapping", sa.JSON(), nullable=False),
        sa.Column("import_options", sa.JSON(), nullable=False),
        sa.Column("total_rows", sa.Integer(), nullable=False),
        sa.Column("validated_rows", sa.Integer(), nullable=False),
        sa.Column("processed_rows", sa.Integer(), nullable=False),
        sa.Column("successful_rows", sa.Integer(), nullable=False),
        sa.Column("warning_rows", sa.Integer(), nullable=False),
        sa.Column("failed_rows", sa.Integer(), nullable=False),
        sa.Column("skipped_rows", sa.Integer(), nullable=False),
        sa.Column("current_stage", sa.String(length=100), nullable=True),
        sa.Column("validation_summary", sa.JSON(), nullable=False),
        sa.Column("result_summary", sa.JSON(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("error_report_path", sa.String(length=500), nullable=True),
        sa.Column(
            "confirmed_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "queued_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "completed_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "cancelled_at",
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
        sa.Column("is_archived", sa.Boolean(), nullable=False),
        sa.Column(
            "archived_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column("archived_by_id", sa.Integer(), nullable=True),
        sa.Column("archive_reason", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "failed_rows >= 0",
            name="ck_import_batches_failed_rows_non_negative",
        ),
        sa.CheckConstraint(
            "file_size_bytes IS NULL OR file_size_bytes >= 0",
            name="ck_import_batches_file_size_non_negative",
        ),
        sa.CheckConstraint(
            "processed_rows >= 0",
            name="ck_import_batches_processed_rows_non_negative",
        ),
        sa.CheckConstraint(
            "skipped_rows >= 0",
            name="ck_import_batches_skipped_rows_non_negative",
        ),
        sa.CheckConstraint(
            "successful_rows >= 0",
            name="ck_import_batches_successful_rows_non_negative",
        ),
        sa.CheckConstraint(
            "total_rows >= 0",
            name="ck_import_batches_total_rows_non_negative",
        ),
        sa.CheckConstraint(
            "validated_rows >= 0",
            name="ck_import_batches_validated_rows_non_negative",
        ),
        sa.CheckConstraint(
            "warning_rows >= 0",
            name="ck_import_batches_warning_rows_non_negative",
        ),
        sa.ForeignKeyConstraint(
            ["archived_by_id"],
            ["users.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["school_id"],
            ["schools.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["uploaded_by_id"],
            ["users.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        op.f("ix_import_batches_archived_by_id"),
        "import_batches",
        ["archived_by_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_import_batches_created_at"),
        "import_batches",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_import_batches_file_hash"),
        "import_batches",
        ["file_hash"],
        unique=False,
    )
    op.create_index(
        op.f("ix_import_batches_import_type"),
        "import_batches",
        ["import_type"],
        unique=False,
    )
    op.create_index(
        op.f("ix_import_batches_is_archived"),
        "import_batches",
        ["is_archived"],
        unique=False,
    )
    op.create_index(
        op.f("ix_import_batches_operation"),
        "import_batches",
        ["operation"],
        unique=False,
    )
    op.create_index(
        "ix_import_batches_school_archived_created",
        "import_batches",
        ["school_id", "is_archived", "created_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_import_batches_school_id"),
        "import_batches",
        ["school_id"],
        unique=False,
    )
    op.create_index(
        "ix_import_batches_school_status_created",
        "import_batches",
        ["school_id", "status", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_import_batches_school_type_created",
        "import_batches",
        ["school_id", "import_type", "created_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_import_batches_status"),
        "import_batches",
        ["status"],
        unique=False,
    )
    op.create_index(
        op.f("ix_import_batches_uploaded_by_id"),
        "import_batches",
        ["uploaded_by_id"],
        unique=False,
    )

    op.create_table(
        "import_rows",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("batch_id", sa.Integer(), nullable=False),
        sa.Column("school_id", sa.Integer(), nullable=False),
        sa.Column("row_number", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "pending",
                "valid",
                "warning",
                "invalid",
                "queued",
                "processing",
                "imported",
                "updated",
                "skipped",
                "failed",
                name="import_row_status",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column("original_data", sa.JSON(), nullable=False),
        sa.Column("normalised_data", sa.JSON(), nullable=False),
        sa.Column("validation_errors", sa.JSON(), nullable=False),
        sa.Column("validation_warnings", sa.JSON(), nullable=False),
        sa.Column("entity_type", sa.String(length=100), nullable=True),
        sa.Column("created_entity_id", sa.Integer(), nullable=True),
        sa.Column("attempt_count", sa.Integer(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "processed_at",
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
        sa.CheckConstraint(
            "attempt_count >= 0",
            name="ck_import_rows_attempt_count_non_negative",
        ),
        sa.CheckConstraint(
            "row_number > 0",
            name="ck_import_rows_row_number_positive",
        ),
        sa.ForeignKeyConstraint(
            ["batch_id"],
            ["import_batches.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["school_id"],
            ["schools.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "batch_id",
            "row_number",
            name="uq_import_rows_batch_row_number",
        ),
    )

    op.create_index(
        op.f("ix_import_rows_batch_id"),
        "import_rows",
        ["batch_id"],
        unique=False,
    )
    op.create_index(
        "ix_import_rows_batch_status",
        "import_rows",
        ["batch_id", "status"],
        unique=False,
    )
    op.create_index(
        op.f("ix_import_rows_created_entity_id"),
        "import_rows",
        ["created_entity_id"],
        unique=False,
    )
    op.create_index(
        "ix_import_rows_entity_reference",
        "import_rows",
        ["entity_type", "created_entity_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_import_rows_entity_type"),
        "import_rows",
        ["entity_type"],
        unique=False,
    )
    op.create_index(
        op.f("ix_import_rows_school_id"),
        "import_rows",
        ["school_id"],
        unique=False,
    )
    op.create_index(
        "ix_import_rows_school_status",
        "import_rows",
        ["school_id", "status"],
        unique=False,
    )
    op.create_index(
        op.f("ix_import_rows_status"),
        "import_rows",
        ["status"],
        unique=False,
    )


def downgrade() -> None:
    """Remove the generic import batch and row tables."""

    op.drop_index(
        op.f("ix_import_rows_status"),
        table_name="import_rows",
    )
    op.drop_index(
        "ix_import_rows_school_status",
        table_name="import_rows",
    )
    op.drop_index(
        op.f("ix_import_rows_school_id"),
        table_name="import_rows",
    )
    op.drop_index(
        op.f("ix_import_rows_entity_type"),
        table_name="import_rows",
    )
    op.drop_index(
        "ix_import_rows_entity_reference",
        table_name="import_rows",
    )
    op.drop_index(
        op.f("ix_import_rows_created_entity_id"),
        table_name="import_rows",
    )
    op.drop_index(
        "ix_import_rows_batch_status",
        table_name="import_rows",
    )
    op.drop_index(
        op.f("ix_import_rows_batch_id"),
        table_name="import_rows",
    )
    op.drop_table("import_rows")

    op.drop_index(
        op.f("ix_import_batches_uploaded_by_id"),
        table_name="import_batches",
    )
    op.drop_index(
        op.f("ix_import_batches_status"),
        table_name="import_batches",
    )
    op.drop_index(
        "ix_import_batches_school_type_created",
        table_name="import_batches",
    )
    op.drop_index(
        "ix_import_batches_school_status_created",
        table_name="import_batches",
    )
    op.drop_index(
        op.f("ix_import_batches_school_id"),
        table_name="import_batches",
    )
    op.drop_index(
        "ix_import_batches_school_archived_created",
        table_name="import_batches",
    )
    op.drop_index(
        op.f("ix_import_batches_operation"),
        table_name="import_batches",
    )
    op.drop_index(
        op.f("ix_import_batches_is_archived"),
        table_name="import_batches",
    )
    op.drop_index(
        op.f("ix_import_batches_import_type"),
        table_name="import_batches",
    )
    op.drop_index(
        op.f("ix_import_batches_file_hash"),
        table_name="import_batches",
    )
    op.drop_index(
        op.f("ix_import_batches_created_at"),
        table_name="import_batches",
    )
    op.drop_index(
        op.f("ix_import_batches_archived_by_id"),
        table_name="import_batches",
    )
    op.drop_table("import_batches")
