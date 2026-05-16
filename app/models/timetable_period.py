from __future__ import annotations

from datetime import time

from sqlalchemy import Boolean, Integer, String, Time
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class TimetablePeriod(Base):
    __tablename__ = "timetable_periods"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
    )

    school_id: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    short_name: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    period_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    start_time: Mapped[time] = mapped_column(
        Time,
        nullable=False,
    )

    end_time: Mapped[time] = mapped_column(
        Time,
        nullable=False,
    )

    is_registration: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    is_break: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    is_lunch: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
