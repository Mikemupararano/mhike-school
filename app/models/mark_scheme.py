from __future__ import annotations

from decimal import Decimal
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
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

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.assessment_question import AssessmentQuestion
    from app.models.mark_scheme_award import MarkSchemeItemAward


class MarkSchemeItemType(str, Enum):
    """
    Classification for one mark-scheme item.

    MARK
        Generic marking point.

    METHOD
        Method mark, for example M1.

    ACCURACY
        Accuracy mark, for example A1.

    INDEPENDENT
        Independent mark, for example B1.

    ASSESSMENT_OBJECTIVE
        Assessment-objective criterion such as AO1, AO2, AO3 or AO4.

    LEVEL
        Level-based descriptor used by extended-response questions.

    OTHER
        Provider- or school-specific criterion.
    """

    MARK = "mark"
    METHOD = "method"
    ACCURACY = "accuracy"
    INDEPENDENT = "independent"
    ASSESSMENT_OBJECTIVE = "assessment_objective"
    LEVEL = "level"
    OTHER = "other"


class MarkScheme(Base):
    """
    Represent the structured mark scheme for one assessment question.

    A question may have no mark scheme yet, but when one exists it provides
    the marking guidance used by digital marking, moderation and analytics.

    The question remains the source of truth for its maximum available mark.
    The mark scheme describes how those marks may be awarded.
    """

    __tablename__ = "mark_schemes"

    __table_args__ = (
        UniqueConstraint(
            "question_id",
            name="uq_mark_scheme_question",
        ),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True,
    )

    question_id: Mapped[int] = mapped_column(
        ForeignKey(
            "assessment_questions.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    title: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    general_guidance: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    allow_alternative_answers: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )

    question: Mapped["AssessmentQuestion"] = relationship(
        "AssessmentQuestion",
        back_populates="mark_scheme",
        foreign_keys=[question_id],
        lazy="selectin",
    )

    items: Mapped[list["MarkSchemeItem"]] = relationship(
        "MarkSchemeItem",
        back_populates="mark_scheme",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="MarkSchemeItem.order",
    )

    def __repr__(self) -> str:
        return "<MarkScheme " f"id={self.id!r} " f"question_id={self.question_id!r}>"


class MarkSchemeItem(Base):
    """
    Represent one independently identifiable marking criterion.

    Examples:
        M1 — selects the correct equation
        A1 — substitutes correctly
        B1 — gives the correct unit
        AO2 — applies knowledge appropriately

    ``marks`` supports fractional marks if a school or qualification requires
    them, although most conventional mark schemes will use whole-number values.

    ``awards`` records how this criterion was applied across candidate marking
    decisions.
    """

    __tablename__ = "mark_scheme_items"

    __table_args__ = (
        UniqueConstraint(
            "mark_scheme_id",
            "order",
            name="uq_mark_scheme_item_order",
        ),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True,
    )

    mark_scheme_id: Mapped[int] = mapped_column(
        ForeignKey(
            "mark_schemes.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    code: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    item_type: Mapped[MarkSchemeItemType] = mapped_column(
        SqlEnum(
            MarkSchemeItemType,
            name="mark_scheme_item_type",
            values_callable=lambda enum_cls: [value.value for value in enum_cls],
            native_enum=False,
            validate_strings=True,
        ),
        default=MarkSchemeItemType.MARK,
        nullable=False,
        index=True,
    )

    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    marks: Mapped[Decimal] = mapped_column(
        Numeric(
            precision=8,
            scale=2,
        ),
        nullable=False,
    )

    order: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
    )

    is_optional: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    alternative_group: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    examiner_notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    mark_scheme: Mapped["MarkScheme"] = relationship(
        "MarkScheme",
        back_populates="items",
        foreign_keys=[mark_scheme_id],
        lazy="selectin",
    )

    awards: Mapped[list["MarkSchemeItemAward"]] = relationship(
        "MarkSchemeItemAward",
        back_populates="mark_scheme_item",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="MarkSchemeItemAward.id",
    )

    def __repr__(self) -> str:
        return (
            "<MarkSchemeItem "
            f"id={self.id!r} "
            f"mark_scheme_id={self.mark_scheme_id!r} "
            f"code={self.code!r} "
            f"item_type={self.item_type!r} "
            f"marks={self.marks!r} "
            f"order={self.order!r}>"
        )
