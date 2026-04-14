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

    name: Mapped[str] = mapped_column(String(255), nullable=False)

    school_id: Mapped[int] = mapped_column(
        ForeignKey("schools.id"),
        index=True,
        nullable=False,
    )

    # 👨‍🏫 Assign a teacher to the class
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

    # =========================
    # Relationships
    # =========================

    school = relationship("School", back_populates="classes")

    teacher = relationship("User", foreign_keys=[teacher_id])

    enrollments: Mapped[list["Enrollment"]] = relationship(
        "Enrollment",
        back_populates="class_group",
        cascade="all, delete-orphan",
    )
