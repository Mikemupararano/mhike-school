from datetime import datetime

from sqlalchemy import String, ForeignKey, Integer, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Lesson(Base):
    __tablename__ = "lessons"

    id: Mapped[int] = mapped_column(primary_key=True)

    module_id: Mapped[int] = mapped_column(ForeignKey("modules.id", ondelete="CASCADE"))

    title: Mapped[str] = mapped_column(String(255), index=True)
    content_type: Mapped[str] = mapped_column(String(50), default="text")
    content: Mapped[str | None] = mapped_column(String, default=None)
    order: Mapped[int] = mapped_column(Integer, default=1)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    module = relationship("Module", back_populates="lessons")
