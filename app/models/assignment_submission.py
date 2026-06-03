from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.base import Base


class AssignmentSubmission(Base):
    __tablename__ = "assignment_submissions"

    __table_args__ = (
        UniqueConstraint(
            "assignment_id",
            "student_id",
            name="uq_assignment_student",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    assignment_id: Mapped[int] = mapped_column(
        ForeignKey("assignments.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )

    student_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )

    school_id: Mapped[int] = mapped_column(
        ForeignKey("schools.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )

    submission_text: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    attachment_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    status: Mapped[str] = mapped_column(
        String(50),
        default="submitted",
        nullable=False,
    )

    score: Mapped[int | None] = mapped_column(
        nullable=True,
    )

    feedback: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    graded_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    graded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    assignment = relationship(
        "Assignment",
        back_populates="submissions",
    )

    student = relationship(
        "User",
        foreign_keys=[student_id],
    )

    school = relationship(
        "School",
        lazy="selectin",
    )

    grader = relationship(
        "User",
        foreign_keys=[graded_by],
    )
