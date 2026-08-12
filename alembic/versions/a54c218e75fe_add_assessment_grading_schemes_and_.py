"""add assessment grading schemes and boundaries

Revision ID: a54c218e75fe
Revises: 5d1942bcb74f
Create Date: 2026-08-12 13:13:27.442383+00:00

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "a54c218e75fe"
down_revision = "5d1942bcb74f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create assessment grading schemes and grade boundaries."""

    op.create_table(
        "assessment_grading_schemes",
        sa.Column(
            "id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "assessment_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "name",
            sa.String(length=255),
            nullable=False,
        ),
        sa.Column(
            "description",
            sa.Text(),
            nullable=True,
        ),
        sa.Column(
            "basis",
            sa.Enum(
                "percentage",
                "raw_mark",
                name="assessment_grading_basis",
                native_enum=False,
            ),
            nullable=False,
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
        ),
        sa.Column(
            "created_by_id",
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
        sa.ForeignKeyConstraint(
            ["assessment_id"],
            ["assessments.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_id"],
            ["users.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint(
            "id",
        ),
        sa.UniqueConstraint(
            "assessment_id",
            name="uq_assessment_grading_scheme_assessment",
        ),
    )

    op.create_index(
        op.f("ix_assessment_grading_schemes_assessment_id"),
        "assessment_grading_schemes",
        ["assessment_id"],
        unique=False,
    )

    op.create_index(
        op.f("ix_assessment_grading_schemes_basis"),
        "assessment_grading_schemes",
        ["basis"],
        unique=False,
    )

    op.create_index(
        op.f("ix_assessment_grading_schemes_created_by_id"),
        "assessment_grading_schemes",
        ["created_by_id"],
        unique=False,
    )

    op.create_index(
        op.f("ix_assessment_grading_schemes_is_active"),
        "assessment_grading_schemes",
        ["is_active"],
        unique=False,
    )

    op.create_table(
        "assessment_grade_boundaries",
        sa.Column(
            "id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "grading_scheme_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "grade_label",
            sa.String(length=50),
            nullable=False,
        ),
        sa.Column(
            "minimum_value",
            sa.Numeric(
                precision=10,
                scale=4,
            ),
            nullable=False,
        ),
        sa.Column(
            "order",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "description",
            sa.Text(),
            nullable=True,
        ),
        sa.Column(
            "grade_points",
            sa.Numeric(
                precision=8,
                scale=2,
            ),
            nullable=True,
        ),
        sa.Column(
            "is_pass",
            sa.Boolean(),
            nullable=True,
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
            "minimum_value >= 0",
            name="ck_assessment_grade_boundary_minimum_nonnegative",
        ),
        sa.ForeignKeyConstraint(
            ["grading_scheme_id"],
            ["assessment_grading_schemes.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "id",
        ),
        sa.UniqueConstraint(
            "grading_scheme_id",
            "grade_label",
            name="uq_assessment_grade_boundary_scheme_label",
        ),
        sa.UniqueConstraint(
            "grading_scheme_id",
            "minimum_value",
            name="uq_assessment_grade_boundary_scheme_minimum",
        ),
        sa.UniqueConstraint(
            "grading_scheme_id",
            "order",
            name="uq_assessment_grade_boundary_scheme_order",
        ),
    )

    op.create_index(
        op.f("ix_assessment_grade_boundaries_grading_scheme_id"),
        "assessment_grade_boundaries",
        ["grading_scheme_id"],
        unique=False,
    )


def downgrade() -> None:
    """Remove assessment grading schemes and grade boundaries."""

    op.drop_index(
        op.f("ix_assessment_grade_boundaries_grading_scheme_id"),
        table_name="assessment_grade_boundaries",
    )

    op.drop_table(
        "assessment_grade_boundaries",
    )

    op.drop_index(
        op.f("ix_assessment_grading_schemes_is_active"),
        table_name="assessment_grading_schemes",
    )

    op.drop_index(
        op.f("ix_assessment_grading_schemes_created_by_id"),
        table_name="assessment_grading_schemes",
    )

    op.drop_index(
        op.f("ix_assessment_grading_schemes_basis"),
        table_name="assessment_grading_schemes",
    )

    op.drop_index(
        op.f("ix_assessment_grading_schemes_assessment_id"),
        table_name="assessment_grading_schemes",
    )

    op.drop_table(
        "assessment_grading_schemes",
    )
