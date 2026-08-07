from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum

from sqlalchemy import (
    DateTime,
    Enum as SqlEnum,
    ForeignKey,
    Integer,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def utc_now() -> datetime:
    """
    Return the current timezone-aware UTC datetime.
    """

    return datetime.now(UTC)


class TimetableAssignmentType(str, Enum):
    STUDENT = "student"
    TEACHER = "teacher"
    CLASS_GROUP = "class_group"


class TimetableAssignment(Base):
    __tablename__ = "timetable_assignments"

    __table_args__ = (
        UniqueConstraint(
            "timetable_id",
            "assignment_type",
            "user_id",
            "class_group_id",
            name="uq_timetable_assignment_scope",
        ),
    )

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

    assignment_type: Mapped[TimetableAssignmentType] = mapped_column(
        SqlEnum(
            TimetableAssignmentType,
            name="timetableassignmenttype",
        ),
        nullable=False,
        index=True,
    )

    user_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "users.id",
            ondelete="CASCADE",
        ),
        nullable=True,
        index=True,
    )

    class_group_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "class_groups.id",
            ondelete="CASCADE",
        ),
        nullable=True,
        index=True,
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
    )

    user = relationship(
        "User",
    )

    class_group = relationship(
        "ClassGroup",
    )
