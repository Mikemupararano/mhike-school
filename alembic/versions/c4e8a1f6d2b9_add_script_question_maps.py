"""add script question maps

Revision ID: c4e8a1f6d2b9
Revises: b7d42f81a6c3
Create Date: 2026-09-19

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "c4e8a1f6d2b9"
down_revision: str | None = "b7d42f81a6c3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "assessment_script_question_maps",
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
            "script_regions",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'[]'::json"),
        ),
        sa.Column(
            "mapping_method",
            sa.String(
                length=100,
            ),
            nullable=True,
        ),
        sa.Column(
            "confidence",
            sa.String(
                length=50,
            ),
            nullable=True,
        ),
        sa.Column(
            "mapping_metadata",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'{}'::json"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(
                timezone=True,
            ),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(
                timezone=True,
            ),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["response_id"],
            ["assessment_responses.id"],
            name="fk_assessment_script_question_map_response",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "id",
            name="pk_assessment_script_question_maps",
        ),
        sa.UniqueConstraint(
            "response_id",
            name="uq_assessment_script_question_map_response",
        ),
    )

    op.create_index(
        "ix_assessment_script_question_maps_response_id",
        "assessment_script_question_maps",
        ["response_id"],
        unique=False,
    )

    op.alter_column(
        "assessment_script_question_maps",
        "script_regions",
        server_default=None,
    )

    op.alter_column(
        "assessment_script_question_maps",
        "mapping_metadata",
        server_default=None,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_assessment_script_question_maps_response_id",
        table_name="assessment_script_question_maps",
    )

    op.drop_table(
        "assessment_script_question_maps",
    )
