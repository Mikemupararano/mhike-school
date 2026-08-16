from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
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
    from app.models.assessment import Assessment
    from app.models.assessment_response import AssessmentResponse
    from app.models.mark_scheme import MarkScheme


class AssessmentSection(Base):
    """
    Represent an optional section within an assessment.

    Examples:
        - Section A
        - Multiple Choice
        - Mechanics
        - Paper 1 Section B

    Sections allow an assessment to group related questions while keeping
    question numbering and marking logic independent.

    A section does not own its questions. Deleting a section therefore leaves
    its questions in the assessment and removes only their section assignment.
    """

    __tablename__ = "assessment_sections"

    __table_args__ = (
        UniqueConstraint(
            "assessment_id",
            "order",
            name="uq_assessment_section_order",
        ),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True,
    )

    assessment_id: Mapped[int] = mapped_column(
        ForeignKey(
            "assessments.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
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

    assessment: Mapped["Assessment"] = relationship(
        "Assessment",
        back_populates="sections",
        foreign_keys=[assessment_id],
        lazy="selectin",
    )

    questions: Mapped[list["AssessmentQuestion"]] = relationship(
        "AssessmentQuestion",
        back_populates="section",
        lazy="selectin",
        order_by="AssessmentQuestion.order",
        passive_deletes=True,
    )

    def __repr__(self) -> str:
        return (
            "<AssessmentSection "
            f"id={self.id!r} "
            f"assessment_id={self.assessment_id!r} "
            f"title={self.title!r} "
            f"order={self.order!r}>"
        )


class AssessmentQuestion(Base):
    """
    Represent one markable question or sub-question within an assessment.

    Questions may be nested using ``parent_question_id`` so structures such as
    1(a), 1(a)(i) and 1(a)(ii) can be represented without a separate table for
    question parts.

    ``maximum_mark`` is stored at question level because question-level marks
    are the basis of digital marking, QLA and curriculum analysis.

    A question may have one structured MarkScheme. The mark scheme describes
    how the available marks can be awarded, while ``maximum_mark`` remains the
    authoritative total available mark for the question.

    Candidate responses are stored separately through ``AssessmentResponse``
    records so the same question can be answered independently by many scripts.

    Section membership is optional. Deleting a section sets ``section_id`` to
    NULL rather than deleting the question.

    Child questions are structurally owned by their parent question and are
    removed when that parent is deleted.
    """

    __tablename__ = "assessment_questions"

    __table_args__ = (
        UniqueConstraint(
            "assessment_id",
            "question_number",
            name="uq_assessment_question_number",
        ),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True,
    )

    assessment_id: Mapped[int] = mapped_column(
        ForeignKey(
            "assessments.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    section_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "assessment_sections.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    parent_question_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "assessment_questions.id",
            ondelete="CASCADE",
        ),
        nullable=True,
        index=True,
    )

    question_number: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    title: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    prompt: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    maximum_mark: Mapped[Decimal] = mapped_column(
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

    is_markable: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )

    assessment: Mapped["Assessment"] = relationship(
        "Assessment",
        back_populates="questions",
        foreign_keys=[assessment_id],
        lazy="selectin",
    )

    section: Mapped["AssessmentSection | None"] = relationship(
        "AssessmentSection",
        back_populates="questions",
        foreign_keys=[section_id],
        lazy="selectin",
    )

    parent_question: Mapped["AssessmentQuestion | None"] = relationship(
        "AssessmentQuestion",
        remote_side="AssessmentQuestion.id",
        back_populates="child_questions",
        foreign_keys=[parent_question_id],
        lazy="selectin",
    )

    child_questions: Mapped[list["AssessmentQuestion"]] = relationship(
        "AssessmentQuestion",
        back_populates="parent_question",
        cascade="all, delete-orphan",
        foreign_keys=[parent_question_id],
        lazy="selectin",
        order_by="AssessmentQuestion.order",
    )

    mark_scheme: Mapped["MarkScheme | None"] = relationship(
        "MarkScheme",
        back_populates="question",
        cascade="all, delete-orphan",
        uselist=False,
        lazy="selectin",
    )

    responses: Mapped[list["AssessmentResponse"]] = relationship(
        "AssessmentResponse",
        back_populates="question",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return (
            "<AssessmentQuestion "
            f"id={self.id!r} "
            f"assessment_id={self.assessment_id!r} "
            f"question_number={self.question_number!r} "
            f"maximum_mark={self.maximum_mark!r} "
            f"order={self.order!r}>"
        )
