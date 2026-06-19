from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ReportMemory(Base):
    __tablename__ = "report_memory"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    school_id: Mapped[int] = mapped_column(
        ForeignKey("schools.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )

    teacher_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )

    teacher_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    subject: Mapped[str] = mapped_column(
        String(100),
        index=True,
        nullable=False,
    )

    year_group: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    topics_studied: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    teacher_notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    generated_report: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    final_report: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    source_report_id: Mapped[int | None] = mapped_column(
        ForeignKey("student_reports.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )

    approved: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
