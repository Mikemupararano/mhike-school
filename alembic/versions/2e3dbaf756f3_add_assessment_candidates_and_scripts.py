"""add assessment candidates and scripts

Revision ID: 2e3dbaf756f3
Revises: 720fd01911c8
Create Date: 2026-08-11 09:51:30.233889+00:00
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.

revision = "2e3dbaf756f3"
down_revision = "720fd01911c8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create assessment candidates and assessment scripts."""

    op.create_table(
        "assessment_candidates",
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
            "student_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum(
                "allocated",
                "started",
                "submitted",
                "withdrawn",
                "absent",
                name="assessment_candidate_status",
                native_enum=False,
            ),
            nullable=False,
        ),
        sa.Column(
            "candidate_number",
            sa.String(length=100),
            nullable=True,
        ),
        sa.Column(
            "access_arrangements",
            sa.Text(),
            nullable=True,
        ),
        sa.Column(
            "allocated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "submitted_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(
            ["assessment_id"],
            ["assessments.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["student_id"],
            ["users.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint(
            "id",
        ),
        sa.UniqueConstraint(
            "assessment_id",
            "student_id",
            name="uq_assessment_candidate_student",
        ),
    )

    op.create_index(
        op.f("ix_assessment_candidates_assessment_id"),
        "assessment_candidates",
        ["assessment_id"],
        unique=False,
    )

    op.create_index(
        op.f("ix_assessment_candidates_status"),
        "assessment_candidates",
        ["status"],
        unique=False,
    )

    op.create_index(
        op.f("ix_assessment_candidates_student_id"),
        "assessment_candidates",
        ["student_id"],
        unique=False,
    )

    op.create_table(
        "assessment_scripts",
        sa.Column(
            "id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "candidate_id",
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
                "not_submitted",
                "submitted",
                "marking",
                "marked",
                "moderation",
                "finalised",
                name="assessment_script_status",
                native_enum=False,
            ),
            nullable=False,
        ),
        sa.Column(
            "source_type",
            sa.String(length=100),
            nullable=True,
        ),
        sa.Column(
            "source_filename",
            sa.String(length=500),
            nullable=True,
        ),
        sa.Column(
            "storage_key",
            sa.String(length=1000),
            nullable=True,
        ),
        sa.Column(
            "mime_type",
            sa.String(length=255),
            nullable=True,
        ),
        sa.Column(
            "checksum",
            sa.String(length=255),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "submitted_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "marking_started_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "marked_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "finalised_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(
            ["candidate_id"],
            ["assessment_candidates.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "id",
        ),
        sa.UniqueConstraint(
            "candidate_id",
            "version",
            name="uq_assessment_script_candidate_version",
        ),
    )

    op.create_index(
        op.f("ix_assessment_scripts_candidate_id"),
        "assessment_scripts",
        ["candidate_id"],
        unique=False,
    )

    op.create_index(
        op.f("ix_assessment_scripts_status"),
        "assessment_scripts",
        ["status"],
        unique=False,
    )


def downgrade() -> None:
    """Remove assessment scripts and assessment candidates."""

    op.drop_index(
        op.f("ix_assessment_scripts_status"),
        table_name="assessment_scripts",
    )

    op.drop_index(
        op.f("ix_assessment_scripts_candidate_id"),
        table_name="assessment_scripts",
    )

    op.drop_table(
        "assessment_scripts",
    )

    op.drop_index(
        op.f("ix_assessment_candidates_student_id"),
        table_name="assessment_candidates",
    )

    op.drop_index(
        op.f("ix_assessment_candidates_status"),
        table_name="assessment_candidates",
    )

    op.drop_index(
        op.f("ix_assessment_candidates_assessment_id"),
        table_name="assessment_candidates",
    )

    op.drop_table(
        "assessment_candidates",
    )
