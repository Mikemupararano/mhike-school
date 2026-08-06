from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    DateTime,
    ForeignKey,
    UniqueConstraint,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)
from sqlalchemy.sql import func

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.class_group import ClassGroup
    from app.models.user import User


class Enrollment(Base):
    """
    Represent one student's membership of one class group.

    Each student may be enrolled in a given class only once. The unique
    constraint on ``user_id`` and ``class_id`` enforces idempotency at the
    database level as a final safeguard alongside repository checks.
    """

    __tablename__ = "enrollments"

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "class_id",
            name="uq_enrollments_user_class",
        ),
    )

    # ------------------------------------------------------------------
    # Identity
    # ------------------------------------------------------------------

    id: Mapped[int] = mapped_column(
        primary_key=True,
    )

    # ------------------------------------------------------------------
    # Membership
    # ------------------------------------------------------------------

    user_id: Mapped[int] = mapped_column(
        ForeignKey(
            "users.id",
        ),
        nullable=False,
        index=True,
    )

    class_id: Mapped[int] = mapped_column(
        ForeignKey(
            "class_groups.id",
        ),
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
        server_default=func.now(),
        nullable=False,
    )

    # ------------------------------------------------------------------
    # Relationships
    # ------------------------------------------------------------------

    user: Mapped["User"] = relationship(
        "User",
        foreign_keys=[user_id],
        lazy="selectin",
    )

    class_group: Mapped["ClassGroup"] = relationship(
        "ClassGroup",
        back_populates="enrollments",
        foreign_keys=[class_id],
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return (
            "<Enrollment "
            f"id={self.id!r} "
            f"user_id={self.user_id!r} "
            f"class_id={self.class_id!r}>"
        )
