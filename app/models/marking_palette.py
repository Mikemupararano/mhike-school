from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum as SqlEnum,
    ForeignKey,
    Integer,
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
    from app.models.school import School
    from app.models.subject import Subject


class MarkingPaletteToolType(str, Enum):
    """
    Tool types available in a marking palette.

    These are deliberately exam-board neutral.
    """

    SYMBOL = "symbol"
    CODE = "code"
    TEXT = "text"
    LINE = "line"
    ARROW = "arrow"
    HIGHLIGHT = "highlight"


class MarkingPalette(Base):
    """
    Configurable examiner marking palette.

    Palettes are always school-scoped.

    ``subject_id`` is optional:
    - NULL means a general school-wide marking palette.
    - A subject id means the palette is intended for that academic subject.

    The palette is deliberately independent of exam boards so the same
    marking tools can be used consistently across different specifications.
    """

    __tablename__ = "marking_palettes"

    __table_args__ = (
        UniqueConstraint(
            "school_id",
            "name",
            name="uq_marking_palette_school_name",
        ),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True,
    )

    school_id: Mapped[int] = mapped_column(
        ForeignKey(
            "schools.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    subject_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "subjects.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    name: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    is_default: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        index=True,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
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

    school: Mapped["School"] = relationship(
        "School",
        foreign_keys=[school_id],
        lazy="selectin",
    )

    subject: Mapped["Subject | None"] = relationship(
        "Subject",
        foreign_keys=[subject_id],
        lazy="selectin",
    )

    tools: Mapped[list["MarkingPaletteTool"]] = relationship(
        "MarkingPaletteTool",
        back_populates="palette",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="MarkingPaletteTool.sort_order, MarkingPaletteTool.id",
    )

    def __repr__(self) -> str:
        return (
            "<MarkingPalette "
            f"id={self.id!r} "
            f"school_id={self.school_id!r} "
            f"subject_id={self.subject_id!r} "
            f"name={self.name!r} "
            f"is_default={self.is_default!r} "
            f"is_active={self.is_active!r}>"
        )


class MarkingPaletteTool(Base):
    """
    One tool available within a marking palette.

    Examples:
    - ✓ Correct / credit
    - ✗ Incorrect
    - ECF Error carried forward
    - BOD Benefit of doubt
    - GR Grammar
    - P Punctuation
    - Sp Spelling
    - REP Repetition
    - IP Incorrect physics
    - text comment
    - line
    - arrow
    - highlight

    ``value`` is the compact symbol or code displayed on the response.

    ``label`` is the human-readable meaning.

    ``keyboard_shortcut`` is optional and may later be used by the marking
    workspace for fast examiner interaction.
    """

    __tablename__ = "marking_palette_tools"

    __table_args__ = (
        UniqueConstraint(
            "palette_id",
            "tool_type",
            "value",
            name="uq_marking_palette_tool_palette_type_value",
        ),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True,
    )

    palette_id: Mapped[int] = mapped_column(
        ForeignKey(
            "marking_palettes.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    tool_type: Mapped[MarkingPaletteToolType] = mapped_column(
        SqlEnum(
            MarkingPaletteToolType,
            name="marking_palette_tool_type",
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

    value: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    label: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    keyboard_shortcut: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    sort_order: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        index=True,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
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

    palette: Mapped["MarkingPalette"] = relationship(
        "MarkingPalette",
        back_populates="tools",
        foreign_keys=[palette_id],
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return (
            "<MarkingPaletteTool "
            f"id={self.id!r} "
            f"palette_id={self.palette_id!r} "
            f"tool_type={self.tool_type!r} "
            f"value={self.value!r} "
            f"label={self.label!r} "
            f"is_active={self.is_active!r}>"
        )
