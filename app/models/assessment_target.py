from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    Text,
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
    from app.models.course import Course
    from app.models.school import School
    from app.models.user import User


class AssessmentTarget(Base):
    """
    Represent a student's academic assessment target for one course.

    Targets are deliberately course-scoped rather than assessment-scoped.

    Example:

        Student:
            Jane Smith

        Course:
            OCR A Level Physics A

        Target:
            grade_label = "A"
            grade_points = 5

    A target therefore survives across multiple assessments belonging to the
    same course and can be compared with the student's formal assessment
    results over time.

    ``grade_label`` is free text so that MHike School does not hard-code a
    particular grading system. Examples include:

        9
        7
        A*
        B
        Distinction
        Merit
        Pass

    ``grade_points`` is optional numeric metadata used when the school's
    grading system provides an ordinal numeric representation. Where both a
    target and an assessment result have grade points, progress can be
    calculated numerically.

    The target does not reference an AssessmentGradeBoundary directly because
    grading schemes and boundaries belong to individual assessments. A
    course-level target must remain valid across multiple assessments whose
    grading configurations may differ.

    Derived values such as current grade, current grade points, variance from
    target and progress status are intentionally not persisted here. They are
    calculated from authoritative finalised assessment results.

    One current target exists per student/course pair.
    """

    __tablename__ = "assessment_targets"

    __table_args__ = (
        UniqueConstraint(
            "student_id",
            "course_id",
            name="uq_assessment_target_student_course",
        ),
        CheckConstraint(
            "grade_points IS NULL OR grade_points >= 0",
            name="ck_assessment_target_grade_points_nonnegative",
        ),
    )

    # ------------------------------------------------------------------
    # Identity
    # ------------------------------------------------------------------

    id: Mapped[int] = mapped_column(
        primary_key=True,
    )

    # ------------------------------------------------------------------
    # School and academic scope
    # ------------------------------------------------------------------

    school_id: Mapped[int] = mapped_column(
        ForeignKey(
            "schools.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    student_id: Mapped[int] = mapped_column(
        ForeignKey(
            "users.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    course_id: Mapped[int] = mapped_column(
        ForeignKey(
            "courses.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    # ------------------------------------------------------------------
    # Target
    # ------------------------------------------------------------------

    grade_label: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    grade_points: Mapped[Decimal | None] = mapped_column(
        Numeric(
            10,
            2,
        ),
        nullable=True,
    )

    academic_year: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        index=True,
    )

    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # ------------------------------------------------------------------
    # Audit
    # ------------------------------------------------------------------

    set_by_id: Mapped[int] = mapped_column(
        ForeignKey(
            "users.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(
            timezone=True,
        ),
        server_default=func.now(),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(
            timezone=True,
        ),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # ------------------------------------------------------------------
    # Relationships
    # ------------------------------------------------------------------

    school: Mapped["School"] = relationship(
        "School",
        foreign_keys=[school_id],
        lazy="selectin",
    )

    student: Mapped["User"] = relationship(
        "User",
        foreign_keys=[student_id],
        lazy="selectin",
    )

    course: Mapped["Course"] = relationship(
        "Course",
        foreign_keys=[course_id],
        lazy="selectin",
    )

    set_by: Mapped["User"] = relationship(
        "User",
        foreign_keys=[set_by_id],
        lazy="selectin",
    )

    # ------------------------------------------------------------------
    # Representation
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        return (
            "<AssessmentTarget "
            f"id={self.id!r} "
            f"school_id={self.school_id!r} "
            f"student_id={self.student_id!r} "
            f"course_id={self.course_id!r} "
            f"grade_label={self.grade_label!r} "
            f"grade_points={self.grade_points!r} "
            f"academic_year={self.academic_year!r} "
            f"set_by_id={self.set_by_id!r}>"
        )
