from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    String,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)
from sqlalchemy.sql import func

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.assignment import Assignment
    from app.models.module import Module
    from app.models.school import School
    from app.models.user import User


class Course(Base):
    """
    Represent one course owned by a teacher within a school.

    Courses are created unpublished by default. Publishing remains an
    explicit application workflow and must not occur implicitly through
    imports or repository operations.
    """

    __tablename__ = "courses"

    # ------------------------------------------------------------------
    # Identity
    # ------------------------------------------------------------------

    id: Mapped[int] = mapped_column(
        primary_key=True,
    )

    # ------------------------------------------------------------------
    # Course details
    # ------------------------------------------------------------------

    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )

    description: Mapped[str | None] = mapped_column(
        String(2000),
        nullable=True,
    )

    # ------------------------------------------------------------------
    # Ownership and school scope
    # ------------------------------------------------------------------

    teacher_id: Mapped[int] = mapped_column(
        ForeignKey(
            "users.id",
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

    # ------------------------------------------------------------------
    # Publication state
    # ------------------------------------------------------------------

    published: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    # ------------------------------------------------------------------
    # Audit timestamps
    # ------------------------------------------------------------------

    created_at: Mapped[datetime] = mapped_column(
        DateTime(
            timezone=True,
        ),
        server_default=func.now(),
        nullable=False,
    )

    # ------------------------------------------------------------------
    # Relationships
    # ------------------------------------------------------------------

    teacher: Mapped["User"] = relationship(
        "User",
        foreign_keys=[teacher_id],
        lazy="selectin",
    )

    school: Mapped["School"] = relationship(
        "School",
        foreign_keys=[school_id],
        lazy="selectin",
    )

    modules: Mapped[list["Module"]] = relationship(
        "Module",
        back_populates="course",
        cascade="all, delete-orphan",
        order_by="Module.order",
        lazy="selectin",
    )

    assignments: Mapped[list["Assignment"]] = relationship(
        "Assignment",
        back_populates="course",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return (
            "<Course "
            f"id={self.id!r} "
            f"title={self.title!r} "
            f"teacher_id={self.teacher_id!r} "
            f"school_id={self.school_id!r} "
            f"published={self.published!r}>"
        )
