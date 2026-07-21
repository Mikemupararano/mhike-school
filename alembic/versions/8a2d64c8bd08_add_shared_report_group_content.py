"""add shared report group content

Revision ID: 8a2d64c8bd08
Revises: 287ab7d2024b
Create Date: 2026-07-21 18:35:02.453172+00:00

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "8a2d64c8bd08"
down_revision = "287ab7d2024b"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Create shared report content scoped to:

    - school
    - reporting session
    - class group
    - subject

    This migration intentionally does not alter the existing class_groups
    table. The foreign-key and index changes generated for class_groups
    were caused by model metadata differences rather than a required
    reporting-system change.
    """

    op.create_table(
        "report_group_contents",
        sa.Column(
            "id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "school_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "report_session_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "class_group_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "subject_name",
            sa.String(length=100),
            nullable=False,
        ),
        sa.Column(
            "work_covered",
            sa.Text(),
            server_default=sa.text("''"),
            nullable=False,
        ),
        sa.Column(
            "updated_by_id",
            sa.Integer(),
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
        sa.ForeignKeyConstraint(
            ["school_id"],
            ["schools.id"],
            name="fk_report_group_contents_school_id_schools",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["report_session_id"],
            ["report_sessions.id"],
            name=("fk_report_group_contents_report_session_id_" "report_sessions"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["class_group_id"],
            ["class_groups.id"],
            name=("fk_report_group_contents_class_group_id_" "class_groups"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["updated_by_id"],
            ["users.id"],
            name="fk_report_group_contents_updated_by_id_users",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint(
            "id",
            name="pk_report_group_contents",
        ),
        sa.UniqueConstraint(
            "school_id",
            "report_session_id",
            "class_group_id",
            "subject_name",
            name="uq_report_group_content_scope",
        ),
    )

    op.create_index(
        "ix_report_group_contents_school_id",
        "report_group_contents",
        ["school_id"],
        unique=False,
    )

    op.create_index(
        "ix_report_group_contents_report_session_id",
        "report_group_contents",
        ["report_session_id"],
        unique=False,
    )

    op.create_index(
        "ix_report_group_contents_class_group_id",
        "report_group_contents",
        ["class_group_id"],
        unique=False,
    )

    op.create_index(
        "ix_report_group_contents_subject_name",
        "report_group_contents",
        ["subject_name"],
        unique=False,
    )

    op.create_index(
        "ix_report_group_contents_updated_by_id",
        "report_group_contents",
        ["updated_by_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_report_group_contents_updated_by_id",
        table_name="report_group_contents",
    )

    op.drop_index(
        "ix_report_group_contents_subject_name",
        table_name="report_group_contents",
    )

    op.drop_index(
        "ix_report_group_contents_class_group_id",
        table_name="report_group_contents",
    )

    op.drop_index(
        "ix_report_group_contents_report_session_id",
        table_name="report_group_contents",
    )

    op.drop_index(
        "ix_report_group_contents_school_id",
        table_name="report_group_contents",
    )

    op.drop_table("report_group_contents")
