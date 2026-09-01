from __future__ import annotations

from decimal import Decimal
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    ForeignKey,
    Integer,
    JSON,
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
    from app.models.assessment_document import AssessmentDocument
    from app.models.assessment_question_snapshot import AssessmentQuestionSnapshot
    from app.models.assessment_response import AssessmentResponse
    from app.models.mark_scheme import MarkScheme


class AssessmentQuestionType(StrEnum):
    """
    Canonical interaction type for an assessment question.

    ``written`` remains the default so existing questions retain their current
    behaviour after the database migration.

    Multiple-choice questions store their answer choices in
    ``AssessmentQuestionOption`` rows rather than embedding choices inside the
    prompt. This allows learner-facing radio buttons/checkboxes and reliable
    automatic marking later.

    ``diagram_annotation`` is used when the learner must place labels, symbols,
    markers, points or other annotations directly onto a candidate-visible
    diagram or image.

    ``structural`` is reserved for non-markable hierarchy nodes such as a
    synthesised parent "1" above markable children "1(a)", "1(b)", etc.
    """

    WRITTEN = "written"
    MULTIPLE_CHOICE_SINGLE = "multiple_choice_single"
    MULTIPLE_CHOICE_MULTIPLE = "multiple_choice_multiple"
    TRUE_FALSE = "true_false"
    NUMERIC = "numeric"
    DIAGRAM_ANNOTATION = "diagram_annotation"
    STRUCTURAL = "structural"


class AssessmentQuestionAssetType(StrEnum):
    """
    Candidate-visible visual/resource type attached to a question.

    Assets are stored independently from prompt text so diagrams, graphs,
    figures and photographs extracted from a source paper can be reviewed,
    retained and rendered to the learner exactly where they are needed.
    """

    IMAGE = "image"
    DIAGRAM = "diagram"
    GRAPH = "graph"
    FIGURE = "figure"


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
    Represent one question, sub-question or structural parent in an assessment.

    Questions may be nested using ``parent_question_id`` so structures such as
    1(a), 1(a)(i) and 1(a)(ii) can be represented without a separate table for
    question parts.

    ``question_type`` determines how the learner answers the question:

        - written
        - multiple_choice_single
        - multiple_choice_multiple
        - true_false
        - numeric
        - diagram_annotation
        - structural

    Multiple-choice answer choices live in ``AssessmentQuestionOption``.
    Candidate-visible diagrams, graphs, photographs and other figures live in
    ``AssessmentQuestionAsset``.

    ``interaction_config`` stores the question-specific learner interaction
    configuration. It is intentionally generic so the same visual-response
    engine can support subject-aware symbol palettes, point plotting, graph
    labelling, axis labelling, line/curve drawing and other annotation tools
    without introducing a new database column for each subject or interaction.

    ``maximum_mark`` remains authoritative for the total marks available for
    the question. Structural questions should use zero marks and
    ``is_markable=False``.

    A question may have one structured MarkScheme. Candidate responses are
    stored separately through ``AssessmentResponse`` records so the same
    question can be answered independently by many scripts.

    Section membership is optional. Deleting a section sets ``section_id`` to
    NULL rather than deleting the question.

    Child questions, answer options and question assets are structurally owned
    by their question and are removed when that question is deleted.
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

    question_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=AssessmentQuestionType.WRITTEN.value,
        index=True,
    )

    interaction_config: Mapped[dict[str, object] | None] = mapped_column(
        JSON,
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

    source_page_number: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
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

    options: Mapped[list["AssessmentQuestionOption"]] = relationship(
        "AssessmentQuestionOption",
        back_populates="question",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="AssessmentQuestionOption.order",
    )

    assets: Mapped[list["AssessmentQuestionAsset"]] = relationship(
        "AssessmentQuestionAsset",
        back_populates="question",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="AssessmentQuestionAsset.order",
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

    snapshots: Mapped[list["AssessmentQuestionSnapshot"]] = relationship(
        "AssessmentQuestionSnapshot",
        back_populates="question",
        lazy="selectin",
        passive_deletes=True,
    )

    def __repr__(self) -> str:
        return (
            "<AssessmentQuestion "
            f"id={self.id!r} "
            f"assessment_id={self.assessment_id!r} "
            f"question_number={self.question_number!r} "
            f"question_type={self.question_type!r} "
            f"maximum_mark={self.maximum_mark!r} "
            f"order={self.order!r}>"
        )


class AssessmentQuestionOption(Base):
    """
    Represent one structured answer choice for a canonical question.

    For ``multiple_choice_single`` exactly one option will eventually be
    validated as correct.

    For ``multiple_choice_multiple`` one or more options may be correct.

    The option text is deliberately stored separately from the question prompt
    so the learner UI can render genuine radio buttons/checkboxes and the
    marking layer can evaluate selections reliably.
    """

    __tablename__ = "assessment_question_options"

    __table_args__ = (
        UniqueConstraint(
            "question_id",
            "order",
            name="uq_assessment_question_option_order",
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

    text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    order: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
    )

    is_correct: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    feedback: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    question: Mapped["AssessmentQuestion"] = relationship(
        "AssessmentQuestion",
        back_populates="options",
        foreign_keys=[question_id],
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return (
            "<AssessmentQuestionOption "
            f"id={self.id!r} "
            f"question_id={self.question_id!r} "
            f"order={self.order!r} "
            f"is_correct={self.is_correct!r}>"
        )


class AssessmentQuestionAsset(Base):
    """
    Represent a visual/resource that belongs to one canonical question.

    Typical assets are diagrams, graphs, figures and photographs required by
    the learner to answer the question.

    ``candidate_visible`` defaults to True so an imported question cannot
    accidentally hide a required diagram from the candidate.

    Source-document metadata allows an extracted/cropped visual to retain its
    audit trail back to the uploaded question paper. ``source_bbox`` is a JSON
    object reserved for extraction coordinates such as::

        {
            "x0": 72.0,
            "y0": 180.0,
            "x1": 520.0,
            "y1": 410.0
        }

    The actual binary file is referenced by ``storage_path``. File storage and
    download authorization remain service/API concerns rather than ORM logic.
    """

    __tablename__ = "assessment_question_assets"

    __table_args__ = (
        UniqueConstraint(
            "question_id",
            "order",
            name="uq_assessment_question_asset_order",
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

    asset_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=AssessmentQuestionAssetType.FIGURE.value,
        index=True,
    )

    storage_path: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    original_filename: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    mime_type: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    file_size_bytes: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    alt_text: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    caption: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    order: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
    )

    candidate_visible: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )

    source_document_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "assessment_documents.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    source_page_number: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    source_bbox: Mapped[dict[str, object] | None] = mapped_column(
        JSON,
        nullable=True,
    )

    question: Mapped["AssessmentQuestion"] = relationship(
        "AssessmentQuestion",
        back_populates="assets",
        foreign_keys=[question_id],
        lazy="selectin",
    )

    source_document: Mapped["AssessmentDocument | None"] = relationship(
        "AssessmentDocument",
        foreign_keys=[source_document_id],
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return (
            "<AssessmentQuestionAsset "
            f"id={self.id!r} "
            f"question_id={self.question_id!r} "
            f"asset_type={self.asset_type!r} "
            f"order={self.order!r} "
            f"candidate_visible={self.candidate_visible!r}>"
        )
