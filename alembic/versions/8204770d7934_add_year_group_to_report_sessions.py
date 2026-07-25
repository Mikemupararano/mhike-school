"""add year group to report sessions

Revision ID: 8204770d7934
Revises: d8484b2da293
Create Date: 2026-07-24 18:24:57.715275+00:00

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "8204770d7934"
down_revision = "d8484b2da293"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --------------------------------------------------------------
    # Add the new column as nullable first.
    # --------------------------------------------------------------

    op.add_column(
        "report_sessions",
        sa.Column(
            "year_group",
            sa.String(length=50),
            nullable=True,
        ),
    )

    # --------------------------------------------------------------
    # Populate existing rows.
    #
    # Where possible derive the year group from the title.
    # --------------------------------------------------------------

    op.execute("""
        UPDATE report_sessions
        SET year_group =
            CASE
                WHEN title ILIKE '%Year 7%' THEN 'Year 7'
                WHEN title ILIKE '%Year 8%' THEN 'Year 8'
                WHEN title ILIKE '%Year 9%' THEN 'Year 9'
                WHEN title ILIKE '%Year 10%' THEN 'Year 10'
                WHEN title ILIKE '%Year 11%' THEN 'Year 11'
                WHEN title ILIKE '%Year 12%' THEN 'Year 12'
                WHEN title ILIKE '%Year 13%' THEN 'Year 13'
                WHEN title ILIKE '%Reception%' THEN 'Reception'
                WHEN title ILIKE '%Sixth Form%' THEN 'Sixth Form'
                ELSE 'All Years'
            END
        WHERE year_group IS NULL
        """)

    # --------------------------------------------------------------
    # Make the column mandatory.
    # --------------------------------------------------------------

    op.alter_column(
        "report_sessions",
        "year_group",
        existing_type=sa.String(length=50),
        nullable=False,
    )

    # --------------------------------------------------------------
    # Index used by the SQLAlchemy model.
    # --------------------------------------------------------------

    op.create_index(
        "ix_report_sessions_year_group",
        "report_sessions",
        ["year_group"],
        unique=False,
    )

    # --------------------------------------------------------------
    # Composite indexes.
    # --------------------------------------------------------------

    op.create_index(
        "ix_report_sessions_school_academic_year",
        "report_sessions",
        [
            "school_id",
            "academic_year",
        ],
        unique=False,
    )

    op.create_index(
        "ix_report_sessions_school_year_group",
        "report_sessions",
        [
            "school_id",
            "year_group",
        ],
        unique=False,
    )

    op.create_index(
        "ix_report_sessions_school_year_group_active",
        "report_sessions",
        [
            "school_id",
            "year_group",
            "active",
        ],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_report_sessions_school_year_group_active",
        table_name="report_sessions",
    )

    op.drop_index(
        "ix_report_sessions_school_year_group",
        table_name="report_sessions",
    )

    op.drop_index(
        "ix_report_sessions_school_academic_year",
        table_name="report_sessions",
    )

    op.drop_index(
        "ix_report_sessions_year_group",
        table_name="report_sessions",
    )

    op.drop_column(
        "report_sessions",
        "year_group",
    )
