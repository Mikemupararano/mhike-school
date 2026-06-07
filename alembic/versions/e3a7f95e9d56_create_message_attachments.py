"""create message attachments

Revision ID: e3a7f95e9d56
Revises: 228d09de8ed7
Create Date: 2026-06-07 20:18:18.568587+00:00

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "e3a7f95e9d56"
down_revision = "228d09de8ed7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "message_attachments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("message_id", sa.Integer(), nullable=False),
        sa.Column("uploaded_by_id", sa.Integer(), nullable=True),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("mime_type", sa.String(length=255), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=False),
        sa.Column("storage_path", sa.String(length=500), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["message_id"],
            ["messages.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["uploaded_by_id"],
            ["users.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        op.f("ix_message_attachments_id"),
        "message_attachments",
        ["id"],
        unique=False,
    )

    op.create_index(
        op.f("ix_message_attachments_message_id"),
        "message_attachments",
        ["message_id"],
        unique=False,
    )

    op.create_index(
        op.f("ix_message_attachments_uploaded_by_id"),
        "message_attachments",
        ["uploaded_by_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_message_attachments_uploaded_by_id"),
        table_name="message_attachments",
    )

    op.drop_index(
        op.f("ix_message_attachments_message_id"),
        table_name="message_attachments",
    )

    op.drop_index(
        op.f("ix_message_attachments_id"),
        table_name="message_attachments",
    )

    op.drop_table("message_attachments")
