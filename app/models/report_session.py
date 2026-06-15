from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.base import Base


class ReportSession(Base):
    __tablename__ = "report_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)

    school_id: Mapped[int] = mapped_column(
        ForeignKey("schools.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )

    title: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )

    academic_year: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    term: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    # Report configuration

    include_work_covered: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    include_student_comment: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    include_exam_mark: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    include_attainment_grade: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    include_effort_grade: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    include_target_grade: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    include_next_steps: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    include_tutor_comment: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    school = relationship(
        "School",
        lazy="selectin",
    )
