from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    DateTime,
    String,
    func,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.class_group import ClassGroup
    from app.models.notification import Notification
    from app.models.subject import Subject
    from app.models.user import User


class School(Base):
    __tablename__ = "schools"

    # ------------------------------------------------------------------
    # Identity
    # ------------------------------------------------------------------

    id: Mapped[int] = mapped_column(
        primary_key=True,
    )

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
        index=True,
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

    users: Mapped[list["User"]] = relationship(
        "User",
        back_populates="school",
    )

    classes: Mapped[list["ClassGroup"]] = relationship(
        "ClassGroup",
        back_populates="school",
        cascade="all, delete-orphan",
    )

    subjects: Mapped[list["Subject"]] = relationship(
        "Subject",
        back_populates="school",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="selectin",
    )

    notifications: Mapped[list["Notification"]] = relationship(
        "Notification",
        back_populates="school",
        cascade="all, delete-orphan",
    )

    # ------------------------------------------------------------------
    # Representation
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        return "<School " f"id={self.id!r} " f"name={self.name!r}>"
