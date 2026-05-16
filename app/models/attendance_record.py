from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class AttendanceStatus(StrEnum):
    PRESENT = "present"
    LATE = "late"
    AUTHORISED_ABSENCE = "authorised_absence"
    UNAUTHORISED_ABSENCE = "unauthorised_absence"


class AttendanceRecord(Base):
    __tablename__ = "attendance_records"

    __table_args__ = (
        UniqueConstraint(
            "attendance_session_id",
            "student_id",
            name="uq_attendance_session_student",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    attendance_session_id: Mapped[int] = mapped_column(
        ForeignKey("attendance_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    student_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    status: Mapped[AttendanceStatus] = mapped_column(
        Enum(
            AttendanceStatus,
            name="attendance_status",
            native_enum=False,
        ),
        nullable=False,
        index=True,
    )

    marked_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    notes: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
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

    session = relationship(
        "AttendanceSession",
        back_populates="records",
    )

    student = relationship(
        "User",
        foreign_keys=[student_id],
    )

    marked_by = relationship(
        "User",
        foreign_keys=[marked_by_id],
    )
