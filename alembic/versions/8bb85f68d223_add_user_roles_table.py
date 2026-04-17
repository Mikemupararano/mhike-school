"""add user_roles table

Revision ID: 8bb85f68d223
Revises: d3ed01427113
Create Date: 2026-04-17 18:18:52.793205+00:00

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "8bb85f68d223"
down_revision = "d3ed01427113"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user_roles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column(
            "role",
            sa.Enum(
                "platform_admin",
                "school_admin",
                "teacher",
                "student",
                name="user_role",
                native_enum=False,
            ),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "role", name="uq_user_roles_user_role"),
    )
    op.create_index(op.f("ix_user_roles_role"), "user_roles", ["role"], unique=False)
    op.create_index(
        op.f("ix_user_roles_user_id"), "user_roles", ["user_id"], unique=False
    )

    op.execute(
        """
        INSERT INTO user_roles (user_id, role)
        SELECT id, role
        FROM users
        WHERE role IS NOT NULL
        """
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_user_roles_user_id"), table_name="user_roles")
    op.drop_index(op.f("ix_user_roles_role"), table_name="user_roles")
    op.drop_table("user_roles")
