from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.base import Base


class ReportGroupContent(Base):
    """
    Stores report content shared by every pupil in one class group,
    subject and reporting session.

    Work covered is entered once and reused for all matching pupil reports.

    The shared scope is:

    - school_id
    - report_session_id
    - class_group_id
    - subject_name

    Individual StudentReport rows should not maintain independent copies of
    work covered once the shared-content migration is complete.
    """

    __tablename__ = "report_group_contents"

    __table_args__ = (
        UniqueConstraint(
            "school_id",
            "report_session_id",
            "class_group_id",
            "subject_name",
            name="uq_report_group_content_scope",
        ),
    )

    # ------------------------------------------------------------------
    # Identity
    # ------------------------------------------------------------------

    id: Mapped[int] = mapped_column(
        primary_key=True,
    )

    school_id: Mapped[int] = mapped_column(
        ForeignKey(
            "schools.id",
            ondelete="CASCADE",
        ),
        index=True,
        nullable=False,
    )

    report_session_id: Mapped[int] = mapped_column(
        ForeignKey(
            "report_sessions.id",
            ondelete="CASCADE",
        ),
        index=True,
        nullable=False,
    )

    class_group_id: Mapped[int] = mapped_column(
        ForeignKey(
            "class_groups.id",
            ondelete="CASCADE",
        ),
        index=True,
        nullable=False,
    )

    # ClassGroup does not currently contain a dedicated subject field.
    # The subject is therefore part of the shared-content scope.
    subject_name: Mapped[str] = mapped_column(
        String(100),
        index=True,
        nullable=False,
    )

    # ------------------------------------------------------------------
    # Shared report content
    # ------------------------------------------------------------------

    work_covered: Mapped[str] = mapped_column(
        Text,
        default="",
        server_default="",
        nullable=False,
    )

    # ------------------------------------------------------------------
    # Audit information
    # ------------------------------------------------------------------

    updated_by_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "users.id",
            ondelete="SET NULL",
        ),
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

    # ------------------------------------------------------------------
    # Relationships
    # ------------------------------------------------------------------

    school = relationship(
        "School",
        foreign_keys=[school_id],
        lazy="selectin",
    )

    report_session = relationship(
        "ReportSession",
        foreign_keys=[report_session_id],
        lazy="selectin",
    )

    class_group = relationship(
        "ClassGroup",
        back_populates="report_group_contents",
        foreign_keys=[class_group_id],
        lazy="selectin",
    )

    updated_by = relationship(
        "User",
        foreign_keys=[updated_by_id],
        lazy="selectin",
    )