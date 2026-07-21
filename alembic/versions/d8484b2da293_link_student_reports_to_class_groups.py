"""link student reports to class groups

Revision ID: d8484b2da293
Revises: 8a2d64c8bd08
Create Date: 2026-07-21 18:52:56.239129+00:00

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "d8484b2da293"
down_revision = "8a2d64c8bd08"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Link each student report to its teaching class.

    This migration intentionally leaves the existing class_groups table
    unchanged. The class_groups index and foreign-key alterations produced
    by autogenerate were metadata differences rather than required schema
    changes.
    """

    op.add_column(
        "student_reports",
        sa.Column(
            "class_group_id",
            sa.Integer(),
            nullable=True,
        ),
    )

    op.create_index(
        "ix_student_reports_class_group_id",
        "student_reports",
        ["class_group_id"],
        unique=False,
    )

    op.create_foreign_key(
        "fk_student_reports_class_group_id_class_groups",
        "student_reports",
        "class_groups",
        ["class_group_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.drop_constraint(
        "uq_student_report_session_teacher_subject",
        "student_reports",
        type_="unique",
    )

    op.create_unique_constraint(
        "uq_student_report_session_class_subject",
        "student_reports",
        [
            "school_id",
            "student_id",
            "report_session_id",
            "class_group_id",
            "subject_name",
        ],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_student_report_session_class_subject",
        "student_reports",
        type_="unique",
    )

    op.create_unique_constraint(
        "uq_student_report_session_teacher_subject",
        "student_reports",
        [
            "school_id",
            "student_id",
            "teacher_id",
            "report_session_id",
            "subject_name",
        ],
    )

    op.drop_constraint(
        "fk_student_reports_class_group_id_class_groups",
        "student_reports",
        type_="foreignkey",
    )

    op.drop_index(
        "ix_student_reports_class_group_id",
        table_name="student_reports",
    )

    op.drop_column(
        "student_reports",
        "class_group_id",
    )
