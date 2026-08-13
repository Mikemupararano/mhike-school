"""add assessment result outcomes

Revision ID: 43e7cbe693ab
Revises: 1de5623f088c
Create Date: 2026-08-13 20:31:36.895666+00:00

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "43e7cbe693ab"
down_revision = "1de5623f088c"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "assessment_result_outcomes",
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
            "assessment_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "candidate_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "script_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "version",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum(
                "draft",
                "authoritative",
                "superseded",
                "withdrawn",
                name="assessment_result_outcome_status",
                native_enum=False,
            ),
            nullable=False,
        ),
        sa.Column(
            "change_type",
            sa.Enum(
                "initial",
                "retake",
                "remark",
                "correction",
                "moderation",
                "administrative",
                name="assessment_result_change_type",
                native_enum=False,
            ),
            nullable=False,
        ),
        sa.Column(
            "supersedes_id",
            sa.Integer(),
            nullable=True,
        ),
        sa.Column(
            "is_authoritative",
            sa.Boolean(),
            nullable=False,
        ),
        sa.Column(
            "mark_awarded_snapshot",
            sa.Numeric(
                precision=10,
                scale=2,
            ),
            nullable=False,
        ),
        sa.Column(
            "maximum_mark_snapshot",
            sa.Numeric(
                precision=10,
                scale=2,
            ),
            nullable=False,
        ),
        sa.Column(
            "percentage_snapshot",
            sa.Numeric(
                precision=7,
                scale=2,
            ),
            nullable=True,
        ),
        sa.Column(
            "grading_scheme_id_snapshot",
            sa.Integer(),
            nullable=True,
        ),
        sa.Column(
            "grading_scheme_name_snapshot",
            sa.String(
                length=255,
            ),
            nullable=True,
        ),
        sa.Column(
            "grading_basis_snapshot",
            sa.String(
                length=50,
            ),
            nullable=True,
        ),
        sa.Column(
            "grade_boundary_id_snapshot",
            sa.Integer(),
            nullable=True,
        ),
        sa.Column(
            "grade_label_snapshot",
            sa.String(
                length=50,
            ),
            nullable=True,
        ),
        sa.Column(
            "grade_points_snapshot",
            sa.Numeric(
                precision=8,
                scale=2,
            ),
            nullable=True,
        ),
        sa.Column(
            "is_pass_snapshot",
            sa.Boolean(),
            nullable=True,
        ),
        sa.Column(
            "script_version_snapshot",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "reason",
            sa.String(
                length=1000,
            ),
            nullable=True,
        ),
        sa.Column(
            "notes",
            sa.Text(),
            nullable=True,
        ),
        sa.Column(
            "effective_at",
            sa.DateTime(
                timezone=True,
            ),
            nullable=False,
        ),
        sa.Column(
            "recorded_by_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "recorded_at",
            sa.DateTime(
                timezone=True,
            ),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "withdrawn_at",
            sa.DateTime(
                timezone=True,
            ),
            nullable=True,
        ),
        sa.Column(
            "withdrawn_by_id",
            sa.Integer(),
            nullable=True,
        ),
        sa.Column(
            "withdrawal_reason",
            sa.String(
                length=1000,
            ),
            nullable=True,
        ),
        sa.CheckConstraint(
            ("grade_points_snapshot IS NULL " "OR grade_points_snapshot >= 0"),
            name=("ck_assessment_result_outcome_" "grade_points_nonnegative"),
        ),
        sa.CheckConstraint(
            "mark_awarded_snapshot >= 0",
            name="ck_assessment_result_outcome_mark_nonnegative",
        ),
        sa.CheckConstraint(
            "maximum_mark_snapshot >= 0",
            name=("ck_assessment_result_outcome_" "maximum_nonnegative"),
        ),
        sa.CheckConstraint(
            (
                "percentage_snapshot IS NULL "
                "OR "
                "(percentage_snapshot >= 0 "
                "AND percentage_snapshot <= 100)"
            ),
            name="ck_assessment_result_outcome_percentage_range",
        ),
        sa.CheckConstraint(
            "version >= 1",
            name="ck_assessment_result_outcome_version_positive",
        ),
        sa.ForeignKeyConstraint(
            ["assessment_id"],
            ["assessments.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["candidate_id"],
            ["assessment_candidates.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["recorded_by_id"],
            ["users.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["school_id"],
            ["schools.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["script_id"],
            ["assessment_scripts.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["supersedes_id"],
            ["assessment_result_outcomes.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["withdrawn_by_id"],
            ["users.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint(
            "id",
        ),
        sa.UniqueConstraint(
            "candidate_id",
            "version",
            name="uq_assessment_result_outcome_candidate_version",
        ),
    )

    op.create_index(
        "ix_assessment_result_outcome_one_authoritative_candidate",
        "assessment_result_outcomes",
        ["candidate_id"],
        unique=True,
        postgresql_where=sa.text(
            "is_authoritative = true",
        ),
        sqlite_where=sa.text(
            "is_authoritative = 1",
        ),
    )

    op.create_index(
        op.f(
            "ix_assessment_result_outcomes_assessment_id",
        ),
        "assessment_result_outcomes",
        ["assessment_id"],
        unique=False,
    )

    op.create_index(
        op.f(
            "ix_assessment_result_outcomes_candidate_id",
        ),
        "assessment_result_outcomes",
        ["candidate_id"],
        unique=False,
    )

    op.create_index(
        op.f(
            "ix_assessment_result_outcomes_change_type",
        ),
        "assessment_result_outcomes",
        ["change_type"],
        unique=False,
    )

    op.create_index(
        op.f(
            "ix_assessment_result_outcomes_is_authoritative",
        ),
        "assessment_result_outcomes",
        ["is_authoritative"],
        unique=False,
    )

    op.create_index(
        op.f(
            "ix_assessment_result_outcomes_recorded_by_id",
        ),
        "assessment_result_outcomes",
        ["recorded_by_id"],
        unique=False,
    )

    op.create_index(
        op.f(
            "ix_assessment_result_outcomes_school_id",
        ),
        "assessment_result_outcomes",
        ["school_id"],
        unique=False,
    )

    op.create_index(
        op.f(
            "ix_assessment_result_outcomes_script_id",
        ),
        "assessment_result_outcomes",
        ["script_id"],
        unique=False,
    )

    op.create_index(
        op.f(
            "ix_assessment_result_outcomes_status",
        ),
        "assessment_result_outcomes",
        ["status"],
        unique=False,
    )

    op.create_index(
        op.f(
            "ix_assessment_result_outcomes_supersedes_id",
        ),
        "assessment_result_outcomes",
        ["supersedes_id"],
        unique=False,
    )

    op.create_index(
        op.f(
            "ix_assessment_result_outcomes_withdrawn_by_id",
        ),
        "assessment_result_outcomes",
        ["withdrawn_by_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f(
            "ix_assessment_result_outcomes_withdrawn_by_id",
        ),
        table_name="assessment_result_outcomes",
    )

    op.drop_index(
        op.f(
            "ix_assessment_result_outcomes_supersedes_id",
        ),
        table_name="assessment_result_outcomes",
    )

    op.drop_index(
        op.f(
            "ix_assessment_result_outcomes_status",
        ),
        table_name="assessment_result_outcomes",
    )

    op.drop_index(
        op.f(
            "ix_assessment_result_outcomes_script_id",
        ),
        table_name="assessment_result_outcomes",
    )

    op.drop_index(
        op.f(
            "ix_assessment_result_outcomes_school_id",
        ),
        table_name="assessment_result_outcomes",
    )

    op.drop_index(
        op.f(
            "ix_assessment_result_outcomes_recorded_by_id",
        ),
        table_name="assessment_result_outcomes",
    )

    op.drop_index(
        op.f(
            "ix_assessment_result_outcomes_is_authoritative",
        ),
        table_name="assessment_result_outcomes",
    )

    op.drop_index(
        op.f(
            "ix_assessment_result_outcomes_change_type",
        ),
        table_name="assessment_result_outcomes",
    )

    op.drop_index(
        op.f(
            "ix_assessment_result_outcomes_candidate_id",
        ),
        table_name="assessment_result_outcomes",
    )

    op.drop_index(
        op.f(
            "ix_assessment_result_outcomes_assessment_id",
        ),
        table_name="assessment_result_outcomes",
    )

    op.drop_index(
        "ix_assessment_result_outcome_one_authoritative_candidate",
        table_name="assessment_result_outcomes",
    )

    op.drop_table(
        "assessment_result_outcomes",
    )
