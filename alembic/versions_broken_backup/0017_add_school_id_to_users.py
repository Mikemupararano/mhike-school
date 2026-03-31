from alembic import op
import sqlalchemy as sa


revision = "0017"
down_revision = "0016"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("users", sa.Column("school_id", sa.Integer(), nullable=True))
    op.create_index(op.f("ix_users_school_id"), "users", ["school_id"], unique=False)
    op.create_foreign_key(
        "fk_users_school_id_schools",
        "users",
        "schools",
        ["school_id"],
        ["id"],
    )


def downgrade():
    op.drop_constraint("fk_users_school_id_schools", "users", type_="foreignkey")
    op.drop_index(op.f("ix_users_school_id"), table_name="users")
    op.drop_column("users", "school_id")
