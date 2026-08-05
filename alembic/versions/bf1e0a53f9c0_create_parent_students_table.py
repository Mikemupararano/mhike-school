"""create parent students table

Revision ID: bf1e0a53f9c0
Revises: 4d96e12264da
Create Date: 2026-08-05 21:43:38.997218+00:00

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "bf1e0a53f9c0"
down_revision = "4d96e12264da"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "parent_students",
        sa.Column(
            "id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "parent_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "student_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["parent_id"],
            ["users.id"],
            name="fk_parent_students_parent_id_users",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["student_id"],
            ["users.id"],
            name="fk_parent_students_student_id_users",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "id",
            name="pk_parent_students",
        ),
        sa.UniqueConstraint(
            "parent_id",
            "student_id",
            name="uq_parent_student",
        ),
    )

    op.create_index(
        "ix_parent_students_id",
        "parent_students",
        ["id"],
        unique=False,
    )

    op.create_index(
        "ix_parent_students_parent_id",
        "parent_students",
        ["parent_id"],
        unique=False,
    )

    op.create_index(
        "ix_parent_students_student_id",
        "parent_students",
        ["student_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_parent_students_student_id",
        table_name="parent_students",
    )

    op.drop_index(
        "ix_parent_students_parent_id",
        table_name="parent_students",
    )

    op.drop_index(
        "ix_parent_students_id",
        table_name="parent_students",
    )

    op.drop_table(
        "parent_students",
    )
