"""merge attendance and notification heads

Revision ID: e3972690bbdc
Revises: 5c8413388149, 19d3fedcc212
Create Date: 2026-05-20 20:43:55.073851+00:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e3972690bbdc'
down_revision = ('5c8413388149', '19d3fedcc212')
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass