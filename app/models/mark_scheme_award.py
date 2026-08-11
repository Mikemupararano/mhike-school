from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Numeric,
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
    from app.models.assessment_response import MarkingDecision
    from app.models.mark_scheme import MarkSchemeItem
    from app.models.user import User


class MarkSchemeItemAward(Base):
    """
    Represent one awarded mark-scheme criterion within a marking decision.

    A MarkSchemeItemAward links:
        - one MarkingDecision
        - one MarkSchemeItem

    It records whether the criterion was awarded and, where necessary,
    how many marks were awarded against that criterion.

    This separation allows detailed criterion-level marking evidence while
    keeping ``MarkingDecision.mark_awarded`` as the authoritative total mark
    for the question.

    Examples:

        M1 — awarded
        A1 — awarded
        B1 — not awarded

    Fractional marks are supported for qualifications or school assessment
    systems that require them.

    One mark-scheme item may be recorded at most once for a given marking
    decision.
    """

    __tablename__ = "mark_scheme_item_awards"

    __table_args__ = (
        UniqueConstraint(
            "marking_decision_id",
            "mark_scheme_item_id",
            name="uq_mark_scheme_item_award_decision_item",
        ),
    )

    # ------------------------------------------------------------------
    # Identity
    # ------------------------------------------------------------------

    id: Mapped[int] = mapped_column(
        primary_key=True,
    )

    # ------------------------------------------------------------------
    # Marking scope
    # ------------------------------------------------------------------

    marking_decision_id: Mapped[int] = mapped_column(
        ForeignKey(
            "marking_decisions.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    mark_scheme_item_id: Mapped[int] = mapped_column(
        ForeignKey(
            "mark_scheme_items.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    # ------------------------------------------------------------------
    # Award
    # ------------------------------------------------------------------

    marks_awarded: Mapped[Decimal] = mapped_column(
        Numeric(
            precision=8,
            scale=2,
        ),
        nullable=False,
        default=0,
    )

    marker_note: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # ------------------------------------------------------------------
    # Audit
    # ------------------------------------------------------------------

    awarded_by_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "users.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    awarded_at: Mapped[datetime] = mapped_column(
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

    marking_decision: Mapped["MarkingDecision"] = relationship(
        "MarkingDecision",
        back_populates="item_awards",
        foreign_keys=[marking_decision_id],
        lazy="selectin",
    )

    mark_scheme_item: Mapped["MarkSchemeItem"] = relationship(
        "MarkSchemeItem",
        back_populates="awards",
        foreign_keys=[mark_scheme_item_id],
        lazy="selectin",
    )

    awarded_by: Mapped["User | None"] = relationship(
        "User",
        foreign_keys=[awarded_by_id],
        lazy="selectin",
    )

    # ------------------------------------------------------------------
    # Representation
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        return (
            "<MarkSchemeItemAward "
            f"id={self.id!r} "
            f"marking_decision_id={self.marking_decision_id!r} "
            f"mark_scheme_item_id={self.mark_scheme_item_id!r} "
            f"marks_awarded={self.marks_awarded!r}>"
        )
