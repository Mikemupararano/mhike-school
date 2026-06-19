"""add report memory table

Revision ID: dc0142301987
Revises: 42ea45cd898c
Create Date: 2026-06-19 16:02:22.823307+00:00

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "dc0142301987"
down_revision = "42ea45cd898c"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "report_memory",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("school_id", sa.Integer(), nullable=False),
        sa.Column("subject", sa.String(length=100), nullable=False),
        sa.Column("year_group", sa.String(length=50), nullable=True),
        sa.Column("topics_studied", sa.Text(), nullable=True),
        sa.Column("teacher_notes", sa.Text(), nullable=True),
        sa.Column("generated_report", sa.Text(), nullable=True),
        sa.Column("final_report", sa.Text(), nullable=False),
        sa.Column("source_report_id", sa.Integer(), nullable=True),
        sa.Column(
            "approved",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["school_id"],
            ["schools.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["source_report_id"],
            ["student_reports.id"],
            ondelete="SET NULL",
        ),
    )

    op.create_index(
        "ix_report_memory_school_id",
        "report_memory",
        ["school_id"],
    )
    op.create_index(
        "ix_report_memory_subject",
        "report_memory",
        ["subject"],
    )
    op.create_index(
        "ix_report_memory_source_report_id",
        "report_memory",
        ["source_report_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_report_memory_source_report_id",
        table_name="report_memory",
    )
    op.drop_index(
        "ix_report_memory_subject",
        table_name="report_memory",
    )
    op.drop_index(
        "ix_report_memory_school_id",
        table_name="report_memory",
    )
    op.drop_table("report_memory")
