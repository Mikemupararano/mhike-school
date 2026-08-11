"""add assessment sections and questions

Revision ID: 34e9a2dd71ad
Revises: e90c440972d8
Create Date: 2026-08-11 09:09:12.966114+00:00
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "34e9a2dd71ad"
down_revision = "e90c440972d8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create assessment sections and assessment questions."""

    op.create_table(
        "assessment_sections",
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
            "title",
            sa.String(length=255),
            nullable=False,
        ),
        sa.Column(
            "description",
            sa.Text(),
            nullable=True,
        ),
        sa.Column(
            "order",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "is_optional",
            sa.Boolean(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["assessment_id"],
            ["assessments.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "id",
        ),
        sa.UniqueConstraint(
            "assessment_id",
            "order",
            name="uq_assessment_section_order",
        ),
    )

    op.create_index(
        op.f("ix_assessment_sections_assessment_id"),
        "assessment_sections",
        ["assessment_id"],
        unique=False,
    )

    op.create_table(
        "assessment_questions",
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
            "section_id",
            sa.Integer(),
            nullable=True,
        ),
        sa.Column(
            "parent_question_id",
            sa.Integer(),
            nullable=True,
        ),
        sa.Column(
            "question_number",
            sa.String(length=50),
            nullable=False,
        ),
        sa.Column(
            "title",
            sa.String(length=255),
            nullable=True,
        ),
        sa.Column(
            "prompt",
            sa.Text(),
            nullable=True,
        ),
        sa.Column(
            "maximum_mark",
            sa.Numeric(
                precision=8,
                scale=2,
            ),
            nullable=False,
        ),
        sa.Column(
            "order",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "is_markable",
            sa.Boolean(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["assessment_id"],
            ["assessments.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["parent_question_id"],
            ["assessment_questions.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["section_id"],
            ["assessment_sections.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint(
            "id",
        ),
        sa.UniqueConstraint(
            "assessment_id",
            "question_number",
            name="uq_assessment_question_number",
        ),
    )

    op.create_index(
        op.f("ix_assessment_questions_assessment_id"),
        "assessment_questions",
        ["assessment_id"],
        unique=False,
    )

    op.create_index(
        op.f("ix_assessment_questions_parent_question_id"),
        "assessment_questions",
        ["parent_question_id"],
        unique=False,
    )

    op.create_index(
        op.f("ix_assessment_questions_section_id"),
        "assessment_questions",
        ["section_id"],
        unique=False,
    )


def downgrade() -> None:
    """Remove assessment questions and sections."""

    op.drop_index(
        op.f("ix_assessment_questions_section_id"),
        table_name="assessment_questions",
    )

    op.drop_index(
        op.f("ix_assessment_questions_parent_question_id"),
        table_name="assessment_questions",
    )

    op.drop_index(
        op.f("ix_assessment_questions_assessment_id"),
        table_name="assessment_questions",
    )

    op.drop_table(
        "assessment_questions",
    )

    op.drop_index(
        op.f("ix_assessment_sections_assessment_id"),
        table_name="assessment_sections",
    )

    op.drop_table(
        "assessment_sections",
    )
