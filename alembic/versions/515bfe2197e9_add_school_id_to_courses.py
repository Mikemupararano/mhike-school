from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "515bfe2197e9"
down_revision = "bc0afdf36a2a"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("courses", sa.Column("school_id", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("courses", "school_id")
