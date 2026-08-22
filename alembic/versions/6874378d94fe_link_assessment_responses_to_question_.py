"""link assessment responses to question snapshots

Revision ID: 6874378d94fe
Revises: fbef62a0cb7e
Create Date: 2026-08-22 20:28:22.903530+00:00

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "6874378d94fe"
down_revision = "fbef62a0cb7e"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Link assessment responses to immutable question snapshots.

    Existing responses are backfilled where a matching snapshot exists for
    the same script and canonical question. Responses belonging to genuinely
    legacy scripts without snapshots remain NULL for backward compatibility.
    """

    op.add_column(
        "assessment_responses",
        sa.Column(
            "question_snapshot_id",
            sa.Integer(),
            nullable=True,
        ),
    )

    op.create_index(
        "ix_assessment_responses_question_snapshot_id",
        "assessment_responses",
        ["question_snapshot_id"],
        unique=False,
    )

    op.create_foreign_key(
        "fk_assessment_responses_question_snapshot_id",
        "assessment_responses",
        "assessment_question_snapshots",
        ["question_snapshot_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # Backfill responses created for scripts that now have immutable question
    # snapshots. The snapshot table has a unique constraint on
    # (script_id, question_id), so this mapping is deterministic.
    op.execute(
        """
        UPDATE assessment_responses AS response
        SET question_snapshot_id = snapshot.id
        FROM assessment_question_snapshots AS snapshot
        WHERE
            response.question_snapshot_id IS NULL
            AND snapshot.script_id = response.script_id
            AND snapshot.question_id = response.question_id
        """
    )

    op.create_unique_constraint(
        "uq_assessment_response_script_question_snapshot",
        "assessment_responses",
        [
            "script_id",
            "question_snapshot_id",
        ],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_assessment_response_script_question_snapshot",
        "assessment_responses",
        type_="unique",
    )

    op.drop_constraint(
        "fk_assessment_responses_question_snapshot_id",
        "assessment_responses",
        type_="foreignkey",
    )

    op.drop_index(
        "ix_assessment_responses_question_snapshot_id",
        table_name="assessment_responses",
    )

    op.drop_column(
        "assessment_responses",
        "question_snapshot_id",
    )
