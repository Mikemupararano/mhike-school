from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    JSON,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
)
from sqlalchemy.sql import func

from app.db.base import Base


class AssessmentScriptQuestionMap(Base):
    """
    Persist physical scanned-script geometry for one assessment response.

    Logical source-paper geometry remains on the immutable question snapshot.
    This record stores only the candidate-script-side regions and the
    provenance of how that mapping was produced.
    """

    __tablename__ = "assessment_script_question_maps"

    __table_args__ = (
        UniqueConstraint(
            "response_id",
            name="uq_assessment_script_question_map_response",
        ),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True,
    )

    response_id: Mapped[int] = mapped_column(
        ForeignKey(
            "assessment_responses.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    script_regions: Mapped[list[dict[str, object]]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )

    mapping_method: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    confidence: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    mapping_metadata: Mapped[dict[str, object]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
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

    def __repr__(self) -> str:
        return (
            "<AssessmentScriptQuestionMap "
            f"id={self.id!r} "
            f"response_id={self.response_id!r} "
            f"mapping_method={self.mapping_method!r} "
            f"confidence={self.confidence!r}>"
        )
