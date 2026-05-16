from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class AttendanceSessionType(StrEnum):
    AM = "am"
    PM = "pm"


class AttendanceSession(Base):
    __tablename__ = "attendance_sessions"

    __table_args__ = (
        UniqueConstraint(
            "school_id",
            "class_group_id",
            "session_date",
            "session_type",
            name="uq_attendance_session_school_class_date_type",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    school_id: Mapped[int] = mapped_column(
        ForeignKey("schools.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    class_group_id: Mapped[int] = mapped_column(
        ForeignKey("class_groups.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    timetable_entry_id: Mapped[int | None] = mapped_column(
        ForeignKey("timetable_entries.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    timetable_period_id: Mapped[int | None] = mapped_column(
        ForeignKey("timetable_periods.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    session_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        index=True,
    )

    session_type: Mapped[AttendanceSessionType] = mapped_column(
        Enum(
            AttendanceSessionType,
            name="attendance_session_type",
            native_enum=False,
        ),
        nullable=False,
        index=True,
    )

    created_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    records = relationship(
        "AttendanceRecord",
        back_populates="session",
        cascade="all, delete-orphan",
    )

    timetable_entry = relationship("TimetableEntry")
    timetable_period = relationship("TimetablePeriod")
