"""add assessment feedback

Revision ID: 1de5623f088c
Revises: b119fe202777
Create Date: 2026-08-13 17:16:28.850713+00:00

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "1de5623f088c"
down_revision = "b119fe202777"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Add structured assessment feedback storage.

    This migration intentionally contains only the schema changes required
    for the assessment feedback subsystem. Unrelated schema drift detected
    by Alembic autogenerate is deliberately excluded.
    """

    op.create_table(
        "assessment_feedback",
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
            "script_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "overall_comment",
            sa.Text(),
            nullable=True,
        ),
        sa.Column(
            "strengths",
            sa.Text(),
            nullable=True,
        ),
        sa.Column(
            "areas_for_improvement",
            sa.Text(),
            nullable=True,
        ),
        sa.Column(
            "next_steps",
            sa.Text(),
            nullable=True,
        ),
        sa.Column(
            "status",
            sa.Enum(
                "draft",
                "finalised",
                "archived",
                name="assessment_feedback_status",
                native_enum=False,
            ),
            nullable=False,
        ),
        sa.Column(
            "include_with_result",
            sa.Boolean(),
            nullable=False,
        ),
        sa.Column(
            "created_by_id",
            sa.Integer(),
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
        sa.Column(
            "finalised_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "finalised_by_id",
            sa.Integer(),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(
            ["created_by_id"],
            ["users.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["finalised_by_id"],
            ["users.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["school_id"],
            ["schools.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["script_id"],
            ["assessment_scripts.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["updated_by_id"],
            ["users.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint(
            "id",
        ),
        sa.UniqueConstraint(
            "script_id",
            name="uq_assessment_feedback_script",
        ),
    )

    op.create_index(
        op.f("ix_assessment_feedback_created_by_id"),
        "assessment_feedback",
        ["created_by_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_assessment_feedback_finalised_by_id"),
        "assessment_feedback",
        ["finalised_by_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_assessment_feedback_school_id"),
        "assessment_feedback",
        ["school_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_assessment_feedback_script_id"),
        "assessment_feedback",
        ["script_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_assessment_feedback_status"),
        "assessment_feedback",
        ["status"],
        unique=False,
    )
    op.create_index(
        op.f("ix_assessment_feedback_updated_by_id"),
        "assessment_feedback",
        ["updated_by_id"],
        unique=False,
    )

    op.create_table(
        "assessment_question_feedback",
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
            "response_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "feedback_text",
            sa.Text(),
            nullable=True,
        ),
        sa.Column(
            "strength",
            sa.Text(),
            nullable=True,
        ),
        sa.Column(
            "improvement",
            sa.Text(),
            nullable=True,
        ),
        sa.Column(
            "include_with_result",
            sa.Boolean(),
            nullable=False,
        ),
        sa.Column(
            "created_by_id",
            sa.Integer(),
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
            ["created_by_id"],
            ["users.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["response_id"],
            ["assessment_responses.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["school_id"],
            ["schools.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["updated_by_id"],
            ["users.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint(
            "id",
        ),
        sa.UniqueConstraint(
            "response_id",
            name="uq_assessment_question_feedback_response",
        ),
    )

    op.create_index(
        op.f("ix_assessment_question_feedback_created_by_id"),
        "assessment_question_feedback",
        ["created_by_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_assessment_question_feedback_response_id"),
        "assessment_question_feedback",
        ["response_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_assessment_question_feedback_school_id"),
        "assessment_question_feedback",
        ["school_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_assessment_question_feedback_updated_by_id"),
        "assessment_question_feedback",
        ["updated_by_id"],
        unique=False,
    )


def downgrade() -> None:
    """
    Remove structured assessment feedback storage.
    """

    op.drop_index(
        op.f("ix_assessment_question_feedback_updated_by_id"),
        table_name="assessment_question_feedback",
    )
    op.drop_index(
        op.f("ix_assessment_question_feedback_school_id"),
        table_name="assessment_question_feedback",
    )
    op.drop_index(
        op.f("ix_assessment_question_feedback_response_id"),
        table_name="assessment_question_feedback",
    )
    op.drop_index(
        op.f("ix_assessment_question_feedback_created_by_id"),
        table_name="assessment_question_feedback",
    )
    op.drop_table(
        "assessment_question_feedback",
    )

    op.drop_index(
        op.f("ix_assessment_feedback_updated_by_id"),
        table_name="assessment_feedback",
    )
    op.drop_index(
        op.f("ix_assessment_feedback_status"),
        table_name="assessment_feedback",
    )
    op.drop_index(
        op.f("ix_assessment_feedback_script_id"),
        table_name="assessment_feedback",
    )
    op.drop_index(
        op.f("ix_assessment_feedback_school_id"),
        table_name="assessment_feedback",
    )
    op.drop_index(
        op.f("ix_assessment_feedback_finalised_by_id"),
        table_name="assessment_feedback",
    )
    op.drop_index(
        op.f("ix_assessment_feedback_created_by_id"),
        table_name="assessment_feedback",
    )
    op.drop_table(
        "assessment_feedback",
    )
