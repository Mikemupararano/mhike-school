from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class ClassGroup(Base):
    __tablename__ = "class_groups"
    __table_args__ = (
        UniqueConstraint("name", "school_id", name="uq_class_name_school"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    school_id: Mapped[int] = mapped_column(
        ForeignKey("schools.id"),
        index=True,
        nullable=False,
    )

    teacher_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"),
        nullable=True,
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    school: Mapped["School"] = relationship(
        "School",
        back_populates="classes",
    )

    teacher: Mapped["User | None"] = relationship(
        "User",
        back_populates="classes_taught",
        foreign_keys=[teacher_id],
    )

    enrollments: Mapped[list["Enrollment"]] = relationship(
        "Enrollment",
        back_populates="class_group",
        cascade="all, delete-orphan",
    )
