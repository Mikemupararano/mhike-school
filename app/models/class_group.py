from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    DateTime,
    ForeignKey,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)
from sqlalchemy.sql import func

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.enrollment import Enrollment
    from app.models.report_group_content import ReportGroupContent
    from app.models.school import School
    from app.models.user import User


class ClassGroup(Base):
    """
    Represent a teaching class within one school.

    A class group belongs to one school and may have an assigned teacher.
    Student membership is managed through enrolment records.

    Subject information is intentionally not stored directly on the class
    group because the same group may be used in different reporting contexts.
    ``ReportGroupContent`` scopes shared reporting content by class group,
    reporting session and subject.
    """

    __tablename__ = "class_groups"

    __table_args__ = (
        UniqueConstraint(
            "name",
            "school_id",
            name="uq_class_name_school",
        ),
    )

    # ------------------------------------------------------------------
    # Identity and ownership
    # ------------------------------------------------------------------

    id: Mapped[int] = mapped_column(
        primary_key=True,
    )

    # The current production schema does not define a standalone index on
    # class_groups.name. School-scoped uniqueness is enforced by
    # uq_class_name_school.
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    # These foreign keys intentionally mirror the existing database schema.
    # No ON DELETE behaviour is declared because the production constraints
    # were created without it.
    school_id: Mapped[int] = mapped_column(
        ForeignKey(
            "schools.id",
        ),
        nullable=False,
        index=True,
    )

    teacher_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "users.id",
        ),
        nullable=True,
        index=True,
    )

    # ------------------------------------------------------------------
    # Audit timestamps
    # ------------------------------------------------------------------

    created_at: Mapped[datetime] = mapped_column(
        DateTime(
            timezone=True,
        ),
        server_default=func.now(),
        nullable=False,
    )

    # ------------------------------------------------------------------
    # Relationships
    # ------------------------------------------------------------------

    school: Mapped["School"] = relationship(
        "School",
        back_populates="classes",
        foreign_keys=[school_id],
        lazy="selectin",
    )

    teacher: Mapped["User | None"] = relationship(
        "User",
        back_populates="classes_taught",
        foreign_keys=[teacher_id],
        lazy="selectin",
    )

    enrollments: Mapped[list["Enrollment"]] = relationship(
        "Enrollment",
        back_populates="class_group",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="selectin",
    )

    report_group_contents: Mapped[list["ReportGroupContent"]] = relationship(
        "ReportGroupContent",
        back_populates="class_group",
        foreign_keys="ReportGroupContent.class_group_id",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return (
            "<ClassGroup "
            f"id={self.id!r} "
            f"name={self.name!r} "
            f"school_id={self.school_id!r} "
            f"teacher_id={self.teacher_id!r}>"
        )
