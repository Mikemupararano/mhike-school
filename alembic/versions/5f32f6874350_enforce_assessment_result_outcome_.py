"""enforce assessment result outcome authority consistency

Revision ID: 5f32f6874350
Revises: 43e7cbe693ab
Create Date: 2026-08-13

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "5f32f6874350"
down_revision: Union[
    str,
    Sequence[str],
    None,
] = "43e7cbe693ab"
branch_labels: Union[
    str,
    Sequence[str],
    None,
] = None
depends_on: Union[
    str,
    Sequence[str],
    None,
] = None


CONSTRAINT_NAME = "ck_assessment_result_outcome_authority_status_consistency"


def upgrade() -> None:
    """
    Enforce agreement between result lifecycle status and authority state.

    An outcome is authoritative if and only if:

        status = 'authoritative'
        is_authoritative = true

    Every other lifecycle status must have:

        is_authoritative = false

    The separate partial unique index ensures that a candidate can have
    at most one authoritative result outcome at a time.
    """

    op.create_check_constraint(
        CONSTRAINT_NAME,
        "assessment_result_outcomes",
        (
            "("
            "status = 'authoritative' "
            "AND is_authoritative = true"
            ") "
            "OR "
            "("
            "status <> 'authoritative' "
            "AND is_authoritative = false"
            ")"
        ),
    )


def downgrade() -> None:
    """
    Remove only the authority/status consistency constraint.
    """

    op.drop_constraint(
        CONSTRAINT_NAME,
        "assessment_result_outcomes",
        type_="check",
    )
