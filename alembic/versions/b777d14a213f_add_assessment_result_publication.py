"""add assessment result publication

Revision ID: b777d14a213f
Revises: a54c218e75fe
Create Date: 2026-08-12 15:50:47.368111+00:00

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "b777d14a213f"
down_revision = "a54c218e75fe"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create assessment result publication configuration."""

    op.create_table(
        "assessment_result_publications",
        sa.Column(
            "id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "assessment_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum(
                "unreleased",
                "scheduled",
                "published",
                "withdrawn",
                name="assessment_result_publication_status",
                native_enum=False,
            ),
            nullable=False,
        ),
        sa.Column(
            "scheduled_for",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "published_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "published_by_id",
            sa.Integer(),
            nullable=True,
        ),
        sa.Column(
            "withdrawn_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "withdrawn_by_id",
            sa.Integer(),
            nullable=True,
        ),
        sa.Column(
            "withdrawal_reason",
            sa.Text(),
            nullable=True,
        ),
        sa.Column(
            "requires_approval",
            sa.Boolean(),
            server_default="false",
            nullable=False,
        ),
        sa.Column(
            "approved_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "approved_by_id",
            sa.Integer(),
            nullable=True,
        ),
        sa.Column(
            "approval_note",
            sa.Text(),
            nullable=True,
        ),
        sa.Column(
            "visible_to_students",
            sa.Boolean(),
            server_default="true",
            nullable=False,
        ),
        sa.Column(
            "visible_to_parents",
            sa.Boolean(),
            server_default="true",
            nullable=False,
        ),
        sa.Column(
            "include_mark",
            sa.Boolean(),
            server_default="true",
            nullable=False,
        ),
        sa.Column(
            "include_percentage",
            sa.Boolean(),
            server_default="true",
            nullable=False,
        ),
        sa.Column(
            "include_grade",
            sa.Boolean(),
            server_default="true",
            nullable=False,
        ),
        sa.Column(
            "include_question_breakdown",
            sa.Boolean(),
            server_default="false",
            nullable=False,
        ),
        sa.Column(
            "release_message",
            sa.String(length=1000),
            nullable=True,
        ),
        sa.Column(
            "created_by_id",
            sa.Integer(),
            nullable=False,
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
            ["approved_by_id"],
            ["users.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["assessment_id"],
            ["assessments.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_id"],
            ["users.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["published_by_id"],
            ["users.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["withdrawn_by_id"],
            ["users.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint(
            "id",
        ),
        sa.UniqueConstraint(
            "assessment_id",
            name="uq_assessment_result_publication_assessment",
        ),
    )

    op.create_index(
        op.f("ix_assessment_result_publications_approved_by_id"),
        "assessment_result_publications",
        ["approved_by_id"],
        unique=False,
    )

    op.create_index(
        op.f("ix_assessment_result_publications_assessment_id"),
        "assessment_result_publications",
        ["assessment_id"],
        unique=False,
    )

    op.create_index(
        op.f("ix_assessment_result_publications_created_by_id"),
        "assessment_result_publications",
        ["created_by_id"],
        unique=False,
    )

    op.create_index(
        op.f("ix_assessment_result_publications_published_at"),
        "assessment_result_publications",
        ["published_at"],
        unique=False,
    )

    op.create_index(
        op.f("ix_assessment_result_publications_published_by_id"),
        "assessment_result_publications",
        ["published_by_id"],
        unique=False,
    )

    op.create_index(
        op.f("ix_assessment_result_publications_requires_approval"),
        "assessment_result_publications",
        ["requires_approval"],
        unique=False,
    )

    op.create_index(
        op.f("ix_assessment_result_publications_scheduled_for"),
        "assessment_result_publications",
        ["scheduled_for"],
        unique=False,
    )

    op.create_index(
        op.f("ix_assessment_result_publications_status"),
        "assessment_result_publications",
        ["status"],
        unique=False,
    )

    op.create_index(
        op.f("ix_assessment_result_publications_visible_to_parents"),
        "assessment_result_publications",
        ["visible_to_parents"],
        unique=False,
    )

    op.create_index(
        op.f("ix_assessment_result_publications_visible_to_students"),
        "assessment_result_publications",
        ["visible_to_students"],
        unique=False,
    )

    op.create_index(
        op.f("ix_assessment_result_publications_withdrawn_by_id"),
        "assessment_result_publications",
        ["withdrawn_by_id"],
        unique=False,
    )


def downgrade() -> None:
    """Remove assessment result publication configuration."""

    op.drop_index(
        op.f("ix_assessment_result_publications_withdrawn_by_id"),
        table_name="assessment_result_publications",
    )

    op.drop_index(
        op.f("ix_assessment_result_publications_visible_to_students"),
        table_name="assessment_result_publications",
    )

    op.drop_index(
        op.f("ix_assessment_result_publications_visible_to_parents"),
        table_name="assessment_result_publications",
    )

    op.drop_index(
        op.f("ix_assessment_result_publications_status"),
        table_name="assessment_result_publications",
    )

    op.drop_index(
        op.f("ix_assessment_result_publications_scheduled_for"),
        table_name="assessment_result_publications",
    )

    op.drop_index(
        op.f("ix_assessment_result_publications_requires_approval"),
        table_name="assessment_result_publications",
    )

    op.drop_index(
        op.f("ix_assessment_result_publications_published_by_id"),
        table_name="assessment_result_publications",
    )

    op.drop_index(
        op.f("ix_assessment_result_publications_published_at"),
        table_name="assessment_result_publications",
    )

    op.drop_index(
        op.f("ix_assessment_result_publications_created_by_id"),
        table_name="assessment_result_publications",
    )

    op.drop_index(
        op.f("ix_assessment_result_publications_assessment_id"),
        table_name="assessment_result_publications",
    )

    op.drop_index(
        op.f("ix_assessment_result_publications_approved_by_id"),
        table_name="assessment_result_publications",
    )

    op.drop_table(
        "assessment_result_publications",
    )
