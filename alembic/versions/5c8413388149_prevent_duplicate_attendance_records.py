"""prevent duplicate attendance records

Revision ID: 5c8413388149
Revises: 155cea059f2a
Create Date: 2026-05-16 18:48:44.538657+00:00

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "5c8413388149"
down_revision = "155cea059f2a"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM information_schema.table_constraints
                WHERE table_name = 'attendance_records'
                AND constraint_name = 'uq_attendance_session_student'
            ) THEN
                ALTER TABLE attendance_records
                DROP CONSTRAINT uq_attendance_session_student;
            END IF;
        END
        $$;
        """)

    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1
                FROM information_schema.table_constraints
                WHERE table_name = 'attendance_records'
                AND constraint_name = 'uq_attendance_record_session_student'
            ) THEN
                ALTER TABLE attendance_records
                ADD CONSTRAINT uq_attendance_record_session_student
                UNIQUE (attendance_session_id, student_id);
            END IF;
        END
        $$;
        """)

    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1
                FROM information_schema.columns
                WHERE table_name = 'attendance_sessions'
                AND column_name = 'timetable_entry_id'
            ) THEN
                ALTER TABLE attendance_sessions
                ADD COLUMN timetable_entry_id INTEGER;
            END IF;
        END
        $$;
        """)

    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1
                FROM information_schema.columns
                WHERE table_name = 'attendance_sessions'
                AND column_name = 'timetable_period_id'
            ) THEN
                ALTER TABLE attendance_sessions
                ADD COLUMN timetable_period_id INTEGER;
            END IF;
        END
        $$;
        """)

    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_attendance_sessions_timetable_entry_id
        ON attendance_sessions (timetable_entry_id);
        """)

    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_attendance_sessions_timetable_period_id
        ON attendance_sessions (timetable_period_id);
        """)

    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1
                FROM information_schema.table_constraints
                WHERE table_name = 'attendance_sessions'
                AND constraint_name = 'fk_attendance_sessions_timetable_period_id'
            ) THEN
                ALTER TABLE attendance_sessions
                ADD CONSTRAINT fk_attendance_sessions_timetable_period_id
                FOREIGN KEY (timetable_period_id)
                REFERENCES timetable_periods(id)
                ON DELETE SET NULL;
            END IF;
        END
        $$;
        """)

    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1
                FROM information_schema.table_constraints
                WHERE table_name = 'attendance_sessions'
                AND constraint_name = 'fk_attendance_sessions_timetable_entry_id'
            ) THEN
                ALTER TABLE attendance_sessions
                ADD CONSTRAINT fk_attendance_sessions_timetable_entry_id
                FOREIGN KEY (timetable_entry_id)
                REFERENCES timetable_entries(id)
                ON DELETE SET NULL;
            END IF;
        END
        $$;
        """)


def downgrade() -> None:
    op.execute("""
        ALTER TABLE attendance_sessions
        DROP CONSTRAINT IF EXISTS fk_attendance_sessions_timetable_entry_id;
        """)

    op.execute("""
        ALTER TABLE attendance_sessions
        DROP CONSTRAINT IF EXISTS fk_attendance_sessions_timetable_period_id;
        """)

    op.execute("""
        DROP INDEX IF EXISTS ix_attendance_sessions_timetable_period_id;
        """)

    op.execute("""
        DROP INDEX IF EXISTS ix_attendance_sessions_timetable_entry_id;
        """)

    op.execute("""
        ALTER TABLE attendance_sessions
        DROP COLUMN IF EXISTS timetable_period_id;
        """)

    op.execute("""
        ALTER TABLE attendance_sessions
        DROP COLUMN IF EXISTS timetable_entry_id;
        """)

    op.execute("""
        ALTER TABLE attendance_records
        DROP CONSTRAINT IF EXISTS uq_attendance_record_session_student;
        """)

    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1
                FROM information_schema.table_constraints
                WHERE table_name = 'attendance_records'
                AND constraint_name = 'uq_attendance_session_student'
            ) THEN
                ALTER TABLE attendance_records
                ADD CONSTRAINT uq_attendance_session_student
                UNIQUE (attendance_session_id, student_id);
            END IF;
        END
        $$;
        """)
