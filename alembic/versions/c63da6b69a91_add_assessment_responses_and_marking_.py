"""add assessment responses and marking decisions

Revision ID: c63da6b69a91
Revises: 2e3dbaf756f3
Create Date: 2026-08-11 13:58:21.725195+00:00
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.

revision = "c63da6b69a91"
down_revision = "2e3dbaf756f3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create assessment responses and marking decisions."""

    op.create_table(
        "assessment_responses",
        sa.Column(
            "id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "script_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "question_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum(
                "not_started",
                "in_progress",
                "submitted",
                "void",
                name="assessment_response_status",
                native_enum=False,
            ),
            nullable=False,
        ),
        sa.Column(
            "response_text",
            sa.Text(),
            nullable=True,
        ),
        sa.Column(
            "response_data",
            sa.Text(),
            nullable=True,
        ),
        sa.Column(
            "source_reference",
            sa.String(length=1000),
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
            "submitted_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(
            ["question_id"],
            ["assessment_questions.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["script_id"],
            ["assessment_scripts.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "id",
        ),
        sa.UniqueConstraint(
            "script_id",
            "question_id",
            name="uq_assessment_response_script_question",
        ),
    )

    op.create_index(
        op.f("ix_assessment_responses_question_id"),
        "assessment_responses",
        ["question_id"],
        unique=False,
    )

    op.create_index(
        op.f("ix_assessment_responses_script_id"),
        "assessment_responses",
        ["script_id"],
        unique=False,
    )

    op.create_index(
        op.f("ix_assessment_responses_status"),
        "assessment_responses",
        ["status"],
        unique=False,
    )

    op.create_table(
        "marking_decisions",
        sa.Column(
            "id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "response_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "marker_id",
            sa.Integer(),
            nullable=True,
        ),
        sa.Column(
            "status",
            sa.Enum(
                "unmarked",
                "in_progress",
                "marked",
                "reviewed",
                "finalised",
                name="marking_decision_status",
                native_enum=False,
            ),
            nullable=False,
        ),
        sa.Column(
            "mark_awarded",
            sa.Numeric(
                precision=8,
                scale=2,
            ),
            nullable=True,
        ),
        sa.Column(
            "marker_comment",
            sa.Text(),
            nullable=True,
        ),
        sa.Column(
            "moderation_comment",
            sa.Text(),
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
            "marked_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "reviewed_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "finalised_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(
            ["marker_id"],
            ["users.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["response_id"],
            ["assessment_responses.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "id",
        ),
        sa.UniqueConstraint(
            "response_id",
            name="uq_marking_decision_response",
        ),
    )

    op.create_index(
        op.f("ix_marking_decisions_marker_id"),
        "marking_decisions",
        ["marker_id"],
        unique=False,
    )

    op.create_index(
        op.f("ix_marking_decisions_response_id"),
        "marking_decisions",
        ["response_id"],
        unique=False,
    )

    op.create_index(
        op.f("ix_marking_decisions_status"),
        "marking_decisions",
        ["status"],
        unique=False,
    )


def downgrade() -> None:
    """Remove marking decisions and assessment responses."""

    op.drop_index(
        op.f("ix_marking_decisions_status"),
        table_name="marking_decisions",
    )

    op.drop_index(
        op.f("ix_marking_decisions_response_id"),
        table_name="marking_decisions",
    )

    op.drop_index(
        op.f("ix_marking_decisions_marker_id"),
        table_name="marking_decisions",
    )

    op.drop_table(
        "marking_decisions",
    )

    op.drop_index(
        op.f("ix_assessment_responses_status"),
        table_name="assessment_responses",
    )

    op.drop_index(
        op.f("ix_assessment_responses_script_id"),
        table_name="assessment_responses",
    )

    op.drop_index(
        op.f("ix_assessment_responses_question_id"),
        table_name="assessment_responses",
    )

    op.drop_table(
        "assessment_responses",
    )
