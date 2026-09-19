"""add question source regions

Revision ID: b7d42f81a6c3
Revises: f3a9b7c21d44
Create Date: 2026-09-19

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "b7d42f81a6c3"
down_revision: str | None = "f3a9b7c21d44"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "assessment_questions",
        sa.Column(
            "source_regions",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'[]'::json"),
        ),
    )

    op.add_column(
        "assessment_question_snapshots",
        sa.Column(
            "source_regions",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'[]'::json"),
        ),
    )

    op.alter_column(
        "assessment_questions",
        "source_regions",
        server_default=None,
    )

    op.alter_column(
        "assessment_question_snapshots",
        "source_regions",
        server_default=None,
    )


def downgrade() -> None:
    op.drop_column(
        "assessment_question_snapshots",
        "source_regions",
    )

    op.drop_column(
        "assessment_questions",
        "source_regions",
    )
