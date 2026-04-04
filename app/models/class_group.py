from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class ClassGroup(Base):
    __tablename__ = "class_groups"

    id: Mapped[int] = mapped_column(primary_key=True)

    name: Mapped[str] = mapped_column(String(255))

    school_id: Mapped[int] = mapped_column(
        ForeignKey("schools.id"),
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    school = relationship("School", back_populates="classes")

    enrollments: Mapped[list["Enrollment"]] = relationship(
        "Enrollment",
        back_populates="class_group",
        cascade="all, delete-orphan",
    )
