from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    String,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)
from sqlalchemy.sql import func

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.assessment import Assessment
    from app.models.assignment import Assignment
    from app.models.module import Module
    from app.models.school import School
    from app.models.subject import Subject
    from app.models.user import User


class Course(Base):
    """
    Represent one taught course, programme, qualification or specification
    within a school.

    A Course is intentionally distinct from a Subject.

    Subject examples:
        - Physics
        - Chemistry
        - Biology
        - Mathematics

    Course examples:
        - AQA GCSE Physics
        - AQA GCSE Chemistry
        - OCR A Level Physics A
        - AQA A Level Physics

    Courses remain teacher-owned teaching/content containers.

    Subject provides the stable academic discipline used by assessment,
    reporting, curriculum analysis and future MIS integrations.

    Courses are created unpublished by default. Publishing remains an
    explicit application workflow and must not occur implicitly through
    imports or repository operations.

    ``subject_id`` is nullable during the transition to the canonical
    Subject model so that existing course records remain valid until they
    are mapped to subjects.
    """

    __tablename__ = "courses"

    # ------------------------------------------------------------------
    # Identity
    # ------------------------------------------------------------------

    id: Mapped[int] = mapped_column(
        primary_key=True,
    )

    # ------------------------------------------------------------------
    # Course details
    # ------------------------------------------------------------------

    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )

    description: Mapped[str | None] = mapped_column(
        String(2000),
        nullable=True,
    )

    # ------------------------------------------------------------------
    # Academic classification
    # ------------------------------------------------------------------

    subject_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "subjects.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    exam_board: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    qualification: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    specification_code: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    # ------------------------------------------------------------------
    # Ownership and school scope
    # ------------------------------------------------------------------

    teacher_id: Mapped[int] = mapped_column(
        ForeignKey(
            "users.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    school_id: Mapped[int] = mapped_column(
        ForeignKey(
            "schools.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    # ------------------------------------------------------------------
    # Publication state
    # ------------------------------------------------------------------

    published: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
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

    teacher: Mapped["User"] = relationship(
        "User",
        foreign_keys=[teacher_id],
        lazy="selectin",
    )

    school: Mapped["School"] = relationship(
        "School",
        foreign_keys=[school_id],
        lazy="selectin",
    )

    subject: Mapped["Subject | None"] = relationship(
        "Subject",
        back_populates="courses",
        foreign_keys=[subject_id],
        lazy="selectin",
    )

    assessments: Mapped[list["Assessment"]] = relationship(
        "Assessment",
        back_populates="course",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    modules: Mapped[list["Module"]] = relationship(
        "Module",
        back_populates="course",
        cascade="all, delete-orphan",
        order_by="Module.order",
        lazy="selectin",
    )

    assignments: Mapped[list["Assignment"]] = relationship(
        "Assignment",
        back_populates="course",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    # ------------------------------------------------------------------
    # Representation
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        return (
            "<Course "
            f"id={self.id!r} "
            f"title={self.title!r} "
            f"subject_id={self.subject_id!r} "
            f"exam_board={self.exam_board!r} "
            f"qualification={self.qualification!r} "
            f"specification_code={self.specification_code!r} "
            f"teacher_id={self.teacher_id!r} "
            f"school_id={self.school_id!r} "
            f"published={self.published!r}>"
        )
