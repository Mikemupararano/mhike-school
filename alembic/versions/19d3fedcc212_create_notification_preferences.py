"""create notification preferences

Revision ID: 19d3fedcc212
Revises: d74321c2ffcd
Create Date: 2026-05-20 20:08:35.578409+00:00

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "19d3fedcc212"
down_revision = "d74321c2ffcd"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "notification_preferences",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("school_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column(
            "attendance_alerts_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
        sa.Column(
            "absence_notifications_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
        sa.Column(
            "persistent_absence_alerts_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
        sa.Column(
            "safeguarding_alerts_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
        sa.Column(
            "email_enabled", sa.Boolean(), nullable=False, server_default=sa.true()
        ),
        sa.Column(
            "push_enabled", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.Column(
            "sms_enabled", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.ForeignKeyConstraint(["school_id"], ["schools.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
    )

    op.create_index(
        "ix_notification_preferences_school_id",
        "notification_preferences",
        ["school_id"],
    )

    op.create_index(
        "ix_notification_preferences_user_id",
        "notification_preferences",
        ["user_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_notification_preferences_user_id",
        table_name="notification_preferences",
    )

    op.drop_index(
        "ix_notification_preferences_school_id",
        table_name="notification_preferences",
    )

    op.drop_table("notification_preferences")
