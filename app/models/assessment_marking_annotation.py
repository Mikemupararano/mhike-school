from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum as SqlEnum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)
from sqlalchemy.sql import func

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.assessment_response import AssessmentResponse
    from app.models.marking_palette import MarkingPaletteTool
    from app.models.user import User


class MarkingAnnotationType(str, Enum):
    """
    Visual annotation types supported by the examiner marking workspace.

    SYMBOL
        A compact marking symbol such as ✓ or ✗.

    CODE
        A marking code such as ECF, BOD, GR, P, IP, L1, L2 or L3.

    TEXT
        A free-text marker comment positioned on the candidate response.

    LINE
        A straight line between two normalized coordinates.

    ARROW
        A directional arrow between two normalized coordinates.

    HIGHLIGHT
        A rectangular highlighted region.
    """

    SYMBOL = "symbol"
    CODE = "code"
    TEXT = "text"
    LINE = "line"
    ARROW = "arrow"
    HIGHLIGHT = "highlight"


class MarkingAnnotationSurfaceType(str, Enum):
    """
    Surface on which an annotation is positioned.

    RESPONSE
        The candidate response itself.

    QUESTION_ASSET
        A candidate-visible question asset such as a graph or diagram.

    SCRIPT_PAGE
        A page of a scanned or uploaded assessment script.
    """

    RESPONSE = "response"
    QUESTION_ASSET = "question_asset"
    SCRIPT_PAGE = "script_page"


class AssessmentMarkingAnnotation(Base):
    """
    Represent one examiner annotation placed on a candidate response.

    Marking annotations are always separate from the immutable candidate
    response. Moving, editing or deleting an annotation must therefore never
    modify the student's original work.

    Coordinates are normalized to the interval 0..1 so annotations remain
    aligned when the marking surface is resized.

    ``value`` stores the compact visible symbol or code, for example ``✓``,
    ``✗``, ``ECF`` or ``BOD``.

    ``text`` stores free-text comments where applicable.

    ``label_snapshot`` preserves the human-readable meaning of a palette tool
    at the time the annotation was created. This allows palette definitions to
    change later without altering historical marking.

    ``surface_reference`` identifies a particular target where required. For
    example, a question-asset annotation may store the immutable asset id and
    a scanned script annotation may store its page reference.

    Deletion is soft. ``deleted_at`` and ``deleted_by_id`` preserve the audit
    trail while allowing the annotation to disappear from the active marking
    interface.
    """

    __tablename__ = "assessment_marking_annotations"

    __table_args__ = (
        CheckConstraint(
            "x >= 0 AND x <= 1",
            name="ck_assessment_marking_annotation_x_normalized",
        ),
        CheckConstraint(
            "y >= 0 AND y <= 1",
            name="ck_assessment_marking_annotation_y_normalized",
        ),
        CheckConstraint(
            "end_x IS NULL OR (end_x >= 0 AND end_x <= 1)",
            name="ck_assessment_marking_annotation_end_x_normalized",
        ),
        CheckConstraint(
            "end_y IS NULL OR (end_y >= 0 AND end_y <= 1)",
            name="ck_assessment_marking_annotation_end_y_normalized",
        ),
        CheckConstraint(
            "width IS NULL OR (width >= 0 AND width <= 1)",
            name="ck_assessment_marking_annotation_width_normalized",
        ),
        CheckConstraint(
            "height IS NULL OR (height >= 0 AND height <= 1)",
            name="ck_assessment_marking_annotation_height_normalized",
        ),
        CheckConstraint(
            "page_number IS NULL OR page_number >= 1",
            name="ck_assessment_marking_annotation_page_number_positive",
        ),
        CheckConstraint(
            "revision >= 1",
            name="ck_assessment_marking_annotation_revision_positive",
        ),
    )

    # ------------------------------------------------------------------
    # Identity
    # ------------------------------------------------------------------

    id: Mapped[int] = mapped_column(
        primary_key=True,
    )

    # ------------------------------------------------------------------
    # Response and marker ownership
    # ------------------------------------------------------------------

    response_id: Mapped[int] = mapped_column(
        ForeignKey(
            "assessment_responses.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    marker_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "users.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    palette_tool_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "marking_palette_tools.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    # ------------------------------------------------------------------
    # Annotation identity and meaning
    # ------------------------------------------------------------------

    annotation_type: Mapped[MarkingAnnotationType] = mapped_column(
        SqlEnum(
            MarkingAnnotationType,
            name="marking_annotation_type",
            values_callable=lambda enum_cls: [
                value.value
                for value in enum_cls
            ],
            native_enum=False,
            validate_strings=True,
        ),
        nullable=False,
        index=True,
    )

    value: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    label_snapshot: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    text: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # ------------------------------------------------------------------
    # Marking surface
    # ------------------------------------------------------------------

    surface_type: Mapped[MarkingAnnotationSurfaceType] = mapped_column(
        SqlEnum(
            MarkingAnnotationSurfaceType,
            name="marking_annotation_surface_type",
            values_callable=lambda enum_cls: [
                value.value
                for value in enum_cls
            ],
            native_enum=False,
            validate_strings=True,
        ),
        default=MarkingAnnotationSurfaceType.RESPONSE,
        nullable=False,
        index=True,
    )

    surface_reference: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    page_number: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    # ------------------------------------------------------------------
    # Normalized geometry
    # ------------------------------------------------------------------

    x: Mapped[Decimal] = mapped_column(
        Numeric(
            precision=9,
            scale=6,
        ),
        nullable=False,
    )

    y: Mapped[Decimal] = mapped_column(
        Numeric(
            precision=9,
            scale=6,
        ),
        nullable=False,
    )

    end_x: Mapped[Decimal | None] = mapped_column(
        Numeric(
            precision=9,
            scale=6,
        ),
        nullable=True,
    )

    end_y: Mapped[Decimal | None] = mapped_column(
        Numeric(
            precision=9,
            scale=6,
        ),
        nullable=True,
    )

    width: Mapped[Decimal | None] = mapped_column(
        Numeric(
            precision=9,
            scale=6,
        ),
        nullable=True,
    )

    height: Mapped[Decimal | None] = mapped_column(
        Numeric(
            precision=9,
            scale=6,
        ),
        nullable=True,
    )

    # ------------------------------------------------------------------
    # Editing / concurrency
    # ------------------------------------------------------------------

    revision: Mapped[int] = mapped_column(
        Integer,
        default=1,
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

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(
            timezone=True,
        ),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(
            timezone=True,
        ),
        nullable=True,
        index=True,
    )

    deleted_by_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "users.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    # ------------------------------------------------------------------
    # Relationships
    # ------------------------------------------------------------------

    response: Mapped["AssessmentResponse"] = relationship(
        "AssessmentResponse",
        back_populates="marking_annotations",
        foreign_keys=[response_id],
        lazy="selectin",
    )

    marker: Mapped["User | None"] = relationship(
        "User",
        foreign_keys=[marker_id],
        lazy="selectin",
    )

    palette_tool: Mapped["MarkingPaletteTool | None"] = relationship(
        "MarkingPaletteTool",
        foreign_keys=[palette_tool_id],
        lazy="selectin",
    )

    deleted_by: Mapped["User | None"] = relationship(
        "User",
        foreign_keys=[deleted_by_id],
        lazy="selectin",
    )

    # ------------------------------------------------------------------
    # Representation
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        return (
            "<AssessmentMarkingAnnotation "
            f"id={self.id!r} "
            f"response_id={self.response_id!r} "
            f"marker_id={self.marker_id!r} "
            f"annotation_type={self.annotation_type!r} "
            f"value={self.value!r} "
            f"revision={self.revision!r}>"
        )
