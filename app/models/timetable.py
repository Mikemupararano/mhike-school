from __future__ import annotations

from datetime import UTC, date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.school import School
    from app.models.timetable_entry import TimetableEntry


def utc_now() -> datetime:
    """
    Return the current timezone-aware UTC datetime.

    This helper is used for Python-side timestamp defaults and updates.
    """

    return datetime.now(
        UTC,
    )


class Timetable(Base):
    """
    Represent one master timetable belonging to a school.

    A timetable defines:

    - its school;
    - display name;
    - academic year;
    - effective date range;
    - active state;
    - timetable entries.

    Import matching uses the school-scoped natural key consisting of
    ``school_id``, ``name`` and ``academic_year``.
    """

    __tablename__ = "timetables"

    # ------------------------------------------------------------------
    # Identity
    # ------------------------------------------------------------------

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
    )

    # ------------------------------------------------------------------
    # School scope and timetable details
    # ------------------------------------------------------------------

    school_id: Mapped[int] = mapped_column(
        ForeignKey(
            "schools.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )

    academic_year: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        index=True,
    )

    effective_from: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        index=True,
    )

    effective_to: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
        index=True,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        index=True,
    )

    # ------------------------------------------------------------------
    # Audit timestamps
    # ------------------------------------------------------------------

    created_at: Mapped[datetime] = mapped_column(
        DateTime(
            timezone=True,
        ),
        default=utc_now,
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(
            timezone=True,
        ),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )

    # ------------------------------------------------------------------
    # Relationships
    # ------------------------------------------------------------------

    school: Mapped["School"] = relationship(
        "School",
        foreign_keys=[school_id],
        lazy="selectin",
    )

    entries: Mapped[list["TimetableEntry"]] = relationship(
        "TimetableEntry",
        back_populates="timetable",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return (
            "<Timetable "
            f"id={self.id!r} "
            f"school_id={self.school_id!r} "
            f"name={self.name!r} "
            f"academic_year={self.academic_year!r} "
            f"is_active={self.is_active!r}>"
        )
