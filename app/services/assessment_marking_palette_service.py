from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.marking_palette import (
    MarkingPalette,
    MarkingPaletteTool,
    MarkingPaletteToolType,
)
from app.repositories.marking_palette import MarkingPaletteRepository


DEFAULT_MARKING_PALETTE_NAME = "General Marking"


@dataclass(frozen=True)
class DefaultMarkingToolDefinition:
    tool_type: MarkingPaletteToolType
    value: str
    label: str
    description: str | None
    keyboard_shortcut: str | None
    sort_order: int


DEFAULT_MARKING_TOOLS: tuple[DefaultMarkingToolDefinition, ...] = (
    DefaultMarkingToolDefinition(
        tool_type=MarkingPaletteToolType.SYMBOL,
        value="✓",
        label="Correct / credit",
        description="Indicates correct work or creditworthy evidence.",
        keyboard_shortcut=None,
        sort_order=10,
    ),
    DefaultMarkingToolDefinition(
        tool_type=MarkingPaletteToolType.SYMBOL,
        value="✗",
        label="Incorrect",
        description="Indicates incorrect work.",
        keyboard_shortcut=None,
        sort_order=20,
    ),
    DefaultMarkingToolDefinition(
        tool_type=MarkingPaletteToolType.CODE,
        value="ECF",
        label="Error carried forward",
        description="Credit awarded after an earlier error has been carried forward.",
        keyboard_shortcut=None,
        sort_order=30,
    ),
    DefaultMarkingToolDefinition(
        tool_type=MarkingPaletteToolType.CODE,
        value="BOD",
        label="Benefit of doubt",
        description="Credit awarded where the response is sufficiently acceptable.",
        keyboard_shortcut=None,
        sort_order=40,
    ),
    DefaultMarkingToolDefinition(
        tool_type=MarkingPaletteToolType.CODE,
        value="GR",
        label="Grammar",
        description="Highlights a grammatical issue.",
        keyboard_shortcut=None,
        sort_order=50,
    ),
    DefaultMarkingToolDefinition(
        tool_type=MarkingPaletteToolType.CODE,
        value="P",
        label="Punctuation",
        description="Highlights a punctuation issue.",
        keyboard_shortcut=None,
        sort_order=60,
    ),
    DefaultMarkingToolDefinition(
        tool_type=MarkingPaletteToolType.CODE,
        value="Sp",
        label="Spelling",
        description="Highlights a spelling issue.",
        keyboard_shortcut=None,
        sort_order=70,
    ),
    DefaultMarkingToolDefinition(
        tool_type=MarkingPaletteToolType.CODE,
        value="REP",
        label="Repetition",
        description="Marks unnecessary repetition.",
        keyboard_shortcut=None,
        sort_order=80,
    ),
    DefaultMarkingToolDefinition(
        tool_type=MarkingPaletteToolType.CODE,
        value="^",
        label="Omission",
        description="Indicates omitted material.",
        keyboard_shortcut=None,
        sort_order=90,
    ),
    DefaultMarkingToolDefinition(
        tool_type=MarkingPaletteToolType.TEXT,
        value="TEXT",
        label="Text comment",
        description="Place a free-text examiner comment.",
        keyboard_shortcut=None,
        sort_order=100,
    ),
    DefaultMarkingToolDefinition(
        tool_type=MarkingPaletteToolType.LINE,
        value="LINE",
        label="Line",
        description="Draw a straight marking line.",
        keyboard_shortcut=None,
        sort_order=110,
    ),
    DefaultMarkingToolDefinition(
        tool_type=MarkingPaletteToolType.ARROW,
        value="ARROW",
        label="Arrow",
        description="Draw a directional marking arrow.",
        keyboard_shortcut=None,
        sort_order=120,
    ),
    DefaultMarkingToolDefinition(
        tool_type=MarkingPaletteToolType.HIGHLIGHT,
        value="HIGHLIGHT",
        label="Highlight",
        description="Highlight a region of the candidate response.",
        keyboard_shortcut=None,
        sort_order=130,
    ),
)


async def ensure_default_marking_palette(
    db: AsyncSession,
    school_id: int,
) -> MarkingPalette:
    """
    Ensure one universal school-wide marking palette exists.

    The operation is idempotent. Existing school customisations are not
    overwritten. Missing default tools are added, but existing tools are left
    unchanged.

    The palette is deliberately exam-board neutral.
    """

    if not isinstance(school_id, int) or isinstance(school_id, bool) or school_id < 1:
        raise ValueError("school_id must be a positive integer.")

    repository = MarkingPaletteRepository(
        db,
    )

    palette = await repository.get_palette_by_school_and_name(
        school_id,
        DEFAULT_MARKING_PALETTE_NAME,
        include_relationships=True,
    )

    try:
        if palette is None:
            palette = MarkingPalette(
                school_id=school_id,
                subject_id=None,
                name=DEFAULT_MARKING_PALETTE_NAME,
                description=(
                    "Universal examiner marking tools for use across subjects "
                    "and exam boards."
                ),
                is_default=True,
                is_active=True,
            )

            palette = await repository.create_palette(
                palette,
            )

        existing_tools = await repository.list_tools_for_palette(
            palette.id,
            active_only=False,
        )

        existing_keys = {
            (
                tool.tool_type,
                tool.value,
            )
            for tool in existing_tools
        }

        for definition in DEFAULT_MARKING_TOOLS:
            key = (
                definition.tool_type,
                definition.value,
            )

            if key in existing_keys:
                continue

            tool = MarkingPaletteTool(
                palette_id=palette.id,
                tool_type=definition.tool_type,
                value=definition.value,
                label=definition.label,
                description=definition.description,
                keyboard_shortcut=definition.keyboard_shortcut,
                sort_order=definition.sort_order,
                is_active=True,
            )

            await repository.create_tool(
                tool,
            )

            existing_keys.add(
                key,
            )

        await db.commit()

    except IntegrityError:
        await db.rollback()

        palette = await repository.get_palette_by_school_and_name(
            school_id,
            DEFAULT_MARKING_PALETTE_NAME,
            include_relationships=True,
        )

        if palette is None:
            raise

    except Exception:
        await db.rollback()
        raise

    refreshed = await repository.get_palette_by_school_and_name(
        school_id,
        DEFAULT_MARKING_PALETTE_NAME,
        include_relationships=True,
    )

    if refreshed is None:
        raise RuntimeError(
            "Default marking palette could not be loaded after creation."
        )

    return refreshed
