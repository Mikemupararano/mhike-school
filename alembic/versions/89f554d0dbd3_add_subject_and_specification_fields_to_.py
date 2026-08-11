"""add subject and specification fields to courses

Revision ID: 89f554d0dbd3
Revises: d42ff9cfc696
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "89f554d0dbd3"
down_revision = "d42ff9cfc696"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Add canonical academic classification fields to courses.

    subject_id remains nullable during migration so that courses created
    before the Subject model was introduced remain valid until explicitly
    mapped to a school-scoped Subject.
    """

    op.add_column(
        "courses",
        sa.Column(
            "subject_id",
            sa.Integer(),
            nullable=True,
        ),
    )

    op.add_column(
        "courses",
        sa.Column(
            "exam_board",
            sa.String(length=100),
            nullable=True,
        ),
    )

    op.add_column(
        "courses",
        sa.Column(
            "qualification",
            sa.String(length=100),
            nullable=True,
        ),
    )

    op.add_column(
        "courses",
        sa.Column(
            "specification_code",
            sa.String(length=100),
            nullable=True,
        ),
    )

    op.create_index(
        op.f("ix_courses_subject_id"),
        "courses",
        ["subject_id"],
        unique=False,
    )

    op.create_foreign_key(
        "fk_courses_subject_id_subjects",
        "courses",
        "subjects",
        ["subject_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    """
    Remove academic classification fields from courses.
    """

    op.drop_constraint(
        "fk_courses_subject_id_subjects",
        "courses",
        type_="foreignkey",
    )

    op.drop_index(
        op.f("ix_courses_subject_id"),
        table_name="courses",
    )

    op.drop_column(
        "courses",
        "specification_code",
    )

    op.drop_column(
        "courses",
        "qualification",
    )

    op.drop_column(
        "courses",
        "exam_board",
    )

    op.drop_column(
        "courses",
        "subject_id",
    )
