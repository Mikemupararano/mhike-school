"""map legacy admin role to school_admin

Revision ID: d6a4f690a68e
Revises: b9731b07194b
Create Date: 2026-05-09 06:38:12.118854+00:00

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "d6a4f690a68e"
down_revision = "b9731b07194b"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        UPDATE users
        SET role = 'school_admin'
        WHERE role = 'admin'
        """)


def downgrade() -> None:
    op.execute("""
        UPDATE users
        SET role = 'admin'
        WHERE role = 'school_admin'
        """)
