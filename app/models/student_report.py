from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.base import Base


class StudentReport(Base):
    __tablename__ = "student_reports"

    __table_args__ = (
        UniqueConstraint(
            "school_id",
            "student_id",
            "teacher_id",
            "report_session_id",
            name="uq_student_report_session_teacher",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    school_id: Mapped[int] = mapped_column(
        ForeignKey("schools.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )

    student_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )

    teacher_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )

    report_session_id: Mapped[int | None] = mapped_column(
        ForeignKey("report_sessions.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )

    title: Mapped[str] = mapped_column(String(200), nullable=False)
    report_text: Mapped[str] = mapped_column(Text, nullable=False)
    grade: Mapped[str | None] = mapped_column(String(50), nullable=True)

    academic_year: Mapped[str] = mapped_column(
        String(20),
        index=True,
        nullable=False,
    )

    term: Mapped[str | None] = mapped_column(String(50), nullable=True)

    status: Mapped[str] = mapped_column(
        String(50),
        default="draft",
        server_default="draft",
        nullable=False,
        index=True,
    )

    published: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
        nullable=False,
        index=True,
    )

    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    published_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )

    reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    reviewed_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    school = relationship("School", lazy="selectin")
    student = relationship("User", foreign_keys=[student_id])
    teacher = relationship("User", foreign_keys=[teacher_id])
    published_by = relationship("User", foreign_keys=[published_by_id])
    reviewed_by = relationship("User", foreign_keys=[reviewed_by_id])
    report_session = relationship(
        "ReportSession",
        foreign_keys=[report_session_id],
    )
