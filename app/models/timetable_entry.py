from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum

from sqlalchemy import (
    DateTime,
    Enum as SqlEnum,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def utc_now() -> datetime:
    """
    Return the current timezone-aware UTC datetime.

    TimetableEntry timestamp columns are stored using timezone-aware
    database types so application and database datetime semantics remain
    consistent.
    """

    return datetime.now(UTC)


class TimetableDay(str, Enum):
    MONDAY = "monday"
    TUESDAY = "tuesday"
    WEDNESDAY = "wednesday"
    THURSDAY = "thursday"
    FRIDAY = "friday"
    SATURDAY = "saturday"
    SUNDAY = "sunday"


class TimetableEntry(Base):
    __tablename__ = "timetable_entries"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
    )

    timetable_id: Mapped[int] = mapped_column(
        ForeignKey(
            "timetables.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    school_id: Mapped[int] = mapped_column(
        ForeignKey(
            "schools.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    class_group_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "class_groups.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    course_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "courses.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    teacher_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "users.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    timetable_period_id: Mapped[int] = mapped_column(
        ForeignKey(
            "timetable_periods.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    day_of_week: Mapped[TimetableDay] = mapped_column(
        SqlEnum(
            TimetableDay,
            name="timetableday",
        ),
        nullable=False,
        index=True,
    )

    room: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    title: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
    )

    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )

    timetable = relationship(
        "Timetable",
        back_populates="entries",
    )

    period = relationship(
        "TimetablePeriod",
    )
