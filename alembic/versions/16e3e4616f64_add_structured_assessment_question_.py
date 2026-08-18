"""add structured assessment question options and assets

Revision ID: 16e3e4616f64
Revises: 8aa9c6b5a49c
Create Date: 2026-08-18 20:35:45.938857+00:00

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "16e3e4616f64"
down_revision = "8aa9c6b5a49c"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # Canonical question interaction type
    # ------------------------------------------------------------------
    #
    # Use a temporary server default so every existing assessment question
    # receives the legacy-equivalent "written" type safely. The server
    # default is removed afterwards because the ORM owns the application
    # default.
    op.add_column(
        "assessment_questions",
        sa.Column(
            "question_type",
            sa.String(length=50),
            nullable=False,
            server_default="written",
        ),
    )

    op.create_index(
        "ix_assessment_questions_question_type",
        "assessment_questions",
        ["question_type"],
        unique=False,
    )

    op.alter_column(
        "assessment_questions",
        "question_type",
        server_default=None,
    )

    # ------------------------------------------------------------------
    # Structured answer choices
    # ------------------------------------------------------------------
    op.create_table(
        "assessment_question_options",
        sa.Column(
            "id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "question_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "text",
            sa.Text(),
            nullable=False,
        ),
        sa.Column(
            "order",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "is_correct",
            sa.Boolean(),
            nullable=False,
        ),
        sa.Column(
            "feedback",
            sa.Text(),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(
            ["question_id"],
            ["assessment_questions.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "id",
        ),
        sa.UniqueConstraint(
            "question_id",
            "order",
            name="uq_assessment_question_option_order",
        ),
    )

    op.create_index(
        "ix_assessment_question_options_question_id",
        "assessment_question_options",
        ["question_id"],
        unique=False,
    )

    # ------------------------------------------------------------------
    # Candidate-visible question assets
    # ------------------------------------------------------------------
    #
    # These rows reference the stored visual rather than embedding binary
    # content in the database. source_document_id/source_page_number and
    # source_bbox retain the extraction audit trail back to the uploaded
    # question paper.
    op.create_table(
        "assessment_question_assets",
        sa.Column(
            "id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "question_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "asset_type",
            sa.String(length=50),
            nullable=False,
        ),
        sa.Column(
            "storage_path",
            sa.Text(),
            nullable=False,
        ),
        sa.Column(
            "original_filename",
            sa.String(length=255),
            nullable=True,
        ),
        sa.Column(
            "mime_type",
            sa.String(length=255),
            nullable=False,
        ),
        sa.Column(
            "file_size_bytes",
            sa.Integer(),
            nullable=True,
        ),
        sa.Column(
            "alt_text",
            sa.Text(),
            nullable=True,
        ),
        sa.Column(
            "caption",
            sa.Text(),
            nullable=True,
        ),
        sa.Column(
            "order",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "candidate_visible",
            sa.Boolean(),
            nullable=False,
        ),
        sa.Column(
            "source_document_id",
            sa.Integer(),
            nullable=True,
        ),
        sa.Column(
            "source_page_number",
            sa.Integer(),
            nullable=True,
        ),
        sa.Column(
            "source_bbox",
            sa.JSON(),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(
            ["question_id"],
            ["assessment_questions.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["source_document_id"],
            ["assessment_documents.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint(
            "id",
        ),
        sa.UniqueConstraint(
            "question_id",
            "order",
            name="uq_assessment_question_asset_order",
        ),
    )

    op.create_index(
        "ix_assessment_question_assets_question_id",
        "assessment_question_assets",
        ["question_id"],
        unique=False,
    )

    op.create_index(
        "ix_assessment_question_assets_asset_type",
        "assessment_question_assets",
        ["asset_type"],
        unique=False,
    )

    op.create_index(
        "ix_assessment_question_assets_source_document_id",
        "assessment_question_assets",
        ["source_document_id"],
        unique=False,
    )


def downgrade() -> None:
    # Drop dependent tables before removing the parent question column.
    op.drop_index(
        "ix_assessment_question_assets_source_document_id",
        table_name="assessment_question_assets",
    )

    op.drop_index(
        "ix_assessment_question_assets_asset_type",
        table_name="assessment_question_assets",
    )

    op.drop_index(
        "ix_assessment_question_assets_question_id",
        table_name="assessment_question_assets",
    )

    op.drop_table(
        "assessment_question_assets",
    )

    op.drop_index(
        "ix_assessment_question_options_question_id",
        table_name="assessment_question_options",
    )

    op.drop_table(
        "assessment_question_options",
    )

    op.drop_index(
        "ix_assessment_questions_question_type",
        table_name="assessment_questions",
    )

    op.drop_column(
        "assessment_questions",
        "question_type",
    )
