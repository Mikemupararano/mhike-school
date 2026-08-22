from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    DateTime,
    ForeignKey,
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
from sqlalchemy.sql import func

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.assessment_candidate import AssessmentScript
    from app.models.assessment_question import AssessmentQuestion


class AssessmentQuestionSnapshot(Base):
    """
    Immutable learner-facing snapshot of one canonical assessment question
    for one assessment script/version.

    A snapshot is created when a browser assessment attempt starts. From that
    point onward, candidate delivery for that script should use this record
    rather than mutable canonical question content.

    ``question_id`` is retained as provenance to the canonical source question.
    It must not be treated as the authoritative source of learner-facing
    content after the snapshot has been created.

    ``section_snapshot`` freezes candidate-visible section metadata.

    ``options_snapshot`` contains learner-visible option identity, text and
    ordering only. Correct-answer flags and feedback must never be included.

    ``assets_snapshot`` freezes the exact candidate-visible asset metadata and
    storage identity used by the attempt. Each asset snapshot should include a
    SHA-256 checksum so later file replacement at the same storage path can be
    detected.

    Snapshot rows are append-once historical records. Application services must
    never update them after creation.
    """

    __tablename__ = "assessment_question_snapshots"

    __table_args__ = (
        UniqueConstraint(
            "script_id",
            "question_id",
            name="uq_assessment_question_snapshot_script_question",
        ),
    )

    # ------------------------------------------------------------------
    # Identity
    # ------------------------------------------------------------------

    id: Mapped[int] = mapped_column(
        primary_key=True,
    )

    # ------------------------------------------------------------------
    # Script ownership and canonical provenance
    # ------------------------------------------------------------------

    script_id: Mapped[int] = mapped_column(
        ForeignKey(
            "assessment_scripts.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    question_id: Mapped[int] = mapped_column(
        ForeignKey(
            "assessment_questions.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
        index=True,
    )

    parent_question_id_snapshot: Mapped[int | None] = mapped_column(
        nullable=True,
    )

    # ------------------------------------------------------------------
    # Learner-facing question snapshot
    # ------------------------------------------------------------------

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
        index=True,
    )

    interaction_config_snapshot: Mapped[dict[str, object] | None] = mapped_column(
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
        nullable=False,
    )

    is_markable: Mapped[bool] = mapped_column(
        nullable=False,
    )

    # ------------------------------------------------------------------
    # Related learner-facing state
    # ------------------------------------------------------------------

    section_snapshot: Mapped[dict[str, object] | None] = mapped_column(
        JSON,
        nullable=True,
    )

    options_snapshot: Mapped[list[dict[str, object]]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )

    assets_snapshot: Mapped[list[dict[str, object]]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )

    # ------------------------------------------------------------------
    # Audit timestamp
    # ------------------------------------------------------------------

    created_at: Mapped[datetime] = mapped_column(
        DateTime(
            timezone=True,
        ),
        server_default=func.now(),
        nullable=False,
    )

    # ------------------------------------------------------------------
    # Provenance relationships
    # ------------------------------------------------------------------

    script: Mapped["AssessmentScript"] = relationship(
        "AssessmentScript",
        foreign_keys=[script_id],
        lazy="selectin",
    )

    question: Mapped["AssessmentQuestion"] = relationship(
        "AssessmentQuestion",
        foreign_keys=[question_id],
        lazy="selectin",
    )

    # ------------------------------------------------------------------
    # Representation
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        return (
            "<AssessmentQuestionSnapshot "
            f"id={self.id!r} "
            f"script_id={self.script_id!r} "
            f"question_id={self.question_id!r} "
            f"question_number={self.question_number!r}>"
        )
