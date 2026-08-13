"""add assessment targets

Revision ID: b119fe202777
Revises: b777d14a213f
Create Date: 2026-08-13 15:26:53.690355+00:00
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "b119fe202777"
down_revision = "b777d14a213f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "assessment_targets",
        sa.Column(
            "id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "school_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "student_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "course_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "grade_label",
            sa.String(length=100),
            nullable=False,
        ),
        sa.Column(
            "grade_points",
            sa.Numeric(
                precision=10,
                scale=2,
            ),
            nullable=True,
        ),
        sa.Column(
            "academic_year",
            sa.String(length=50),
            nullable=True,
        ),
        sa.Column(
            "notes",
            sa.Text(),
            nullable=True,
        ),
        sa.Column(
            "set_by_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "grade_points IS NULL OR grade_points >= 0",
            name="ck_assessment_target_grade_points_nonnegative",
        ),
        sa.ForeignKeyConstraint(
            ["course_id"],
            ["courses.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["school_id"],
            ["schools.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["set_by_id"],
            ["users.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["student_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "id",
        ),
        sa.UniqueConstraint(
            "student_id",
            "course_id",
            name="uq_assessment_target_student_course",
        ),
    )

    op.create_index(
        op.f("ix_assessment_targets_academic_year"),
        "assessment_targets",
        ["academic_year"],
        unique=False,
    )

    op.create_index(
        op.f("ix_assessment_targets_course_id"),
        "assessment_targets",
        ["course_id"],
        unique=False,
    )

    op.create_index(
        op.f("ix_assessment_targets_school_id"),
        "assessment_targets",
        ["school_id"],
        unique=False,
    )

    op.create_index(
        op.f("ix_assessment_targets_set_by_id"),
        "assessment_targets",
        ["set_by_id"],
        unique=False,
    )

    op.create_index(
        op.f("ix_assessment_targets_student_id"),
        "assessment_targets",
        ["student_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_assessment_targets_student_id"),
        table_name="assessment_targets",
    )

    op.drop_index(
        op.f("ix_assessment_targets_set_by_id"),
        table_name="assessment_targets",
    )

    op.drop_index(
        op.f("ix_assessment_targets_school_id"),
        table_name="assessment_targets",
    )

    op.drop_index(
        op.f("ix_assessment_targets_course_id"),
        table_name="assessment_targets",
    )

    op.drop_index(
        op.f("ix_assessment_targets_academic_year"),
        table_name="assessment_targets",
    )

    op.drop_table(
        "assessment_targets",
    )
