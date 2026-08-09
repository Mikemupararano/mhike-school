from __future__ import annotations

from datetime import UTC, date, datetime
from enum import StrEnum

from sqlalchemy import (
    Date,
    DateTime,
    Enum,
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
    """

    return datetime.now(UTC)


class AbsenceRequestType(StrEnum):
    PLANNED = "planned"
    UNPLANNED = "unplanned"


class AbsenceRequestStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class AbsenceRequest(Base):
    __tablename__ = "absence_requests"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
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

    student_id: Mapped[int] = mapped_column(
        ForeignKey(
            "users.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    submitted_by_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "users.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    reviewed_by_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "users.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    absence_type: Mapped[AbsenceRequestType] = mapped_column(
        Enum(
            AbsenceRequestType,
            name="absence_request_type",
            native_enum=False,
        ),
        nullable=False,
        index=True,
    )

    status: Mapped[AbsenceRequestStatus] = mapped_column(
        Enum(
            AbsenceRequestStatus,
            name="absence_request_status",
            native_enum=False,
        ),
        default=AbsenceRequestStatus.PENDING,
        nullable=False,
        index=True,
    )

    start_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        index=True,
    )

    end_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        index=True,
    )

    reason: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    review_note: Mapped[str | None] = mapped_column(
        String(500),
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

    reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    student = relationship(
        "User",
        foreign_keys=[student_id],
    )

    submitted_by = relationship(
        "User",
        foreign_keys=[submitted_by_id],
    )

    reviewed_by = relationship(
        "User",
        foreign_keys=[reviewed_by_id],
    )
