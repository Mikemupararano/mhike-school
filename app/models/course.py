from sqlalchemy import String, ForeignKey, Boolean, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Course(Base):
    __tablename__ = "courses"

    id: Mapped[int] = mapped_column(primary_key=True)

    title: Mapped[str] = mapped_column(String(255), index=True)
    description: Mapped[str | None] = mapped_column(String(2000), default=None)

    teacher_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))

    # 🔥 Add this (multi-school support)
    school_id: Mapped[int | None] = mapped_column(
        ForeignKey("schools.id"), default=None
    )

    published: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[str] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    # Relationships
    teacher = relationship("User", lazy="selectin")

    # 🔥 Modules inside this course
    modules = relationship(
        "Module",
        back_populates="course",
        cascade="all, delete-orphan",
        order_by="Module.order",
    )

    # 🔥 Enrollments (students taking this course)
    enrollments = relationship(
        "Enrollment",
        back_populates="course",
        cascade="all, delete-orphan",
    )
