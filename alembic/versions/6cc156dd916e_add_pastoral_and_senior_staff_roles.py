"""add pastoral and senior staff roles

Revision ID: 6cc156dd916e
Revises: 8af80ea78959
Create Date: 2026-07-20 18:34:26.215764+00:00

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "6cc156dd916e"
down_revision = "8af80ea78959"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    No database schema changes are required.

    UserRole values are stored as SQLAlchemy non-native enums
    (native_enum=False), and role checks are performed in application code.
    This migration exists only to document the introduction of the additional
    application roles:

        - smt
        - headmaster
        - head_of_year
        - housemaster
        - tutor

    Existing databases remain fully compatible.
    """

    pass


def downgrade() -> None:
    """
    No database changes to reverse.
    """

    pass
