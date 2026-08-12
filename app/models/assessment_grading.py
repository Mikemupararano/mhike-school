from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum as SqlEnum,
    ForeignKey,
    Integer,
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
    from app.models.assessment import Assessment
    from app.models.user import User


class AssessmentGradingBasis(str, Enum):
    """
    Define the value against which assessment grade boundaries are applied.

    PERCENTAGE
        Boundaries are expressed as percentages.

        Example:
            9 >= 80
            8 >= 70
            7 >= 60

    RAW_MARK
        Boundaries are expressed directly as assessment marks.

        Example:
            A* >= 72
            A  >= 64
            B  >= 56

    The grading service is responsible for obtaining the appropriate
    candidate result before applying these boundaries.
    """

    PERCENTAGE = "percentage"
    RAW_MARK = "raw_mark"


class AssessmentGradingScheme(Base):
    """
    Represent the grading configuration for one assessment.

    An assessment may have at most one active grading scheme in the current
    design.

    The scheme describes *how* the assessment result is interpreted, while
    individual ``AssessmentGradeBoundary`` rows define the actual grade
    thresholds.

    Examples:

        GCSE 9-1
            basis = PERCENTAGE

        A Level A*-E
            basis = RAW_MARK

        Internal school assessment
            basis = PERCENTAGE

    Grade labels are intentionally free text so MHike School does not
    hard-code any particular examination system.

    The grading scheme does not persist candidate grades. Candidate grades
    are derived from authoritative assessment results and these boundaries.

    This keeps:

        AssessmentQuestion.maximum_mark
            authoritative for available marks;

        MarkingDecision.mark_awarded
            authoritative for awarded question marks;

        AssessmentGradingScheme
            authoritative for interpreting the resulting total or percentage.
    """

    __tablename__ = "assessment_grading_schemes"

    __table_args__ = (
        UniqueConstraint(
            "assessment_id",
            name="uq_assessment_grading_scheme_assessment",
        ),
    )

    # ------------------------------------------------------------------
    # Identity
    # ------------------------------------------------------------------

    id: Mapped[int] = mapped_column(
        primary_key=True,
    )

    # ------------------------------------------------------------------
    # Assessment ownership
    # ------------------------------------------------------------------

    assessment_id: Mapped[int] = mapped_column(
        ForeignKey(
            "assessments.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    # ------------------------------------------------------------------
    # Grading configuration
    # ------------------------------------------------------------------

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    basis: Mapped[AssessmentGradingBasis] = mapped_column(
        SqlEnum(
            AssessmentGradingBasis,
            name="assessment_grading_basis",
            values_callable=lambda enum_cls: [value.value for value in enum_cls],
            native_enum=False,
            validate_strings=True,
        ),
        default=AssessmentGradingBasis.PERCENTAGE,
        nullable=False,
        index=True,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        index=True,
    )

    # ------------------------------------------------------------------
    # Audit
    # ------------------------------------------------------------------

    created_by_id: Mapped[int] = mapped_column(
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

    assessment: Mapped["Assessment"] = relationship(
        "Assessment",
        back_populates="grading_scheme",
        foreign_keys=[assessment_id],
        lazy="selectin",
    )

    created_by: Mapped["User"] = relationship(
        "User",
        foreign_keys=[created_by_id],
        lazy="selectin",
    )

    boundaries: Mapped[list["AssessmentGradeBoundary"]] = relationship(
        "AssessmentGradeBoundary",
        back_populates="grading_scheme",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by=(
            "AssessmentGradeBoundary.minimum_value.desc(), "
            "AssessmentGradeBoundary.order.asc(), "
            "AssessmentGradeBoundary.id.asc()"
        ),
    )

    # ------------------------------------------------------------------
    # Representation
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        return (
            "<AssessmentGradingScheme "
            f"id={self.id!r} "
            f"assessment_id={self.assessment_id!r} "
            f"name={self.name!r} "
            f"basis={self.basis!r} "
            f"is_active={self.is_active!r}>"
        )


class AssessmentGradeBoundary(Base):
    """
    Represent one grade threshold within an assessment grading scheme.

    ``minimum_value`` is inclusive.

    Example percentage boundaries:

        Grade 9   minimum_value = 80
        Grade 8   minimum_value = 70
        Grade 7   minimum_value = 60
        Grade 6   minimum_value = 50

    A percentage of 70 therefore resolves to Grade 8.

    Example raw-mark boundaries:

        A*   minimum_value = 72
        A    minimum_value = 64
        B    minimum_value = 56

    Boundaries should be evaluated from highest minimum value to lowest.

    ``grade_label`` is intentionally free text and can therefore represent:

        9
        8
        7
        A*
        A
        B
        Distinction
        Merit
        Pass
        U
        Ungraded

    ``grade_points`` is optional metadata for future analytics and progress
    calculations. It does not participate in boundary resolution.

    ``is_pass`` is optional so schools may identify pass/fail classifications
    where that concept is meaningful.
    """

    __tablename__ = "assessment_grade_boundaries"

    __table_args__ = (
        UniqueConstraint(
            "grading_scheme_id",
            "grade_label",
            name="uq_assessment_grade_boundary_scheme_label",
        ),
        UniqueConstraint(
            "grading_scheme_id",
            "minimum_value",
            name="uq_assessment_grade_boundary_scheme_minimum",
        ),
        UniqueConstraint(
            "grading_scheme_id",
            "order",
            name="uq_assessment_grade_boundary_scheme_order",
        ),
        CheckConstraint(
            "minimum_value >= 0",
            name="ck_assessment_grade_boundary_minimum_nonnegative",
        ),
    )

    # ------------------------------------------------------------------
    # Identity
    # ------------------------------------------------------------------

    id: Mapped[int] = mapped_column(
        primary_key=True,
    )

    # ------------------------------------------------------------------
    # Grading scheme ownership
    # ------------------------------------------------------------------

    grading_scheme_id: Mapped[int] = mapped_column(
        ForeignKey(
            "assessment_grading_schemes.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    # ------------------------------------------------------------------
    # Boundary definition
    # ------------------------------------------------------------------

    grade_label: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    minimum_value: Mapped[Decimal] = mapped_column(
        Numeric(
            precision=10,
            scale=4,
        ),
        nullable=False,
    )

    order: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # ------------------------------------------------------------------
    # Optional classification metadata
    # ------------------------------------------------------------------

    grade_points: Mapped[Decimal | None] = mapped_column(
        Numeric(
            precision=8,
            scale=2,
        ),
        nullable=True,
    )

    is_pass: Mapped[bool | None] = mapped_column(
        Boolean,
        nullable=True,
    )

    # ------------------------------------------------------------------
    # Audit
    # ------------------------------------------------------------------

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

    grading_scheme: Mapped["AssessmentGradingScheme"] = relationship(
        "AssessmentGradingScheme",
        back_populates="boundaries",
        foreign_keys=[grading_scheme_id],
        lazy="selectin",
    )

    # ------------------------------------------------------------------
    # Representation
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        return (
            "<AssessmentGradeBoundary "
            f"id={self.id!r} "
            f"grading_scheme_id={self.grading_scheme_id!r} "
            f"grade_label={self.grade_label!r} "
            f"minimum_value={self.minimum_value!r} "
            f"order={self.order!r}>"
        )
