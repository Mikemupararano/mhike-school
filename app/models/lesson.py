from sqlalchemy import String, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class Lesson(Base):
    __tablename__ = "lessons"
    __table_args__ = (
        UniqueConstraint("module_id", "order", name="uq_lesson_module_order"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    module_id: Mapped[int] = mapped_column(
        ForeignKey("modules.id", ondelete="CASCADE"), index=True
    )

    title: Mapped[str] = mapped_column(String(255))
    content_type: Mapped[str] = mapped_column(
        String(50), default="text"
    )  # text/video/pdf/link
    content: Mapped[str | None] = mapped_column(String(5000), default=None)

    order: Mapped[int] = mapped_column(Integer, default=1)
