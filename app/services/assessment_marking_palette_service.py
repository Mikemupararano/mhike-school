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
        tool_type=MarkingPaletteToolType.CODE,
        value="L1^1",
        label="Level 1 – 1 mark",
        description="Level 1 response awarded 1 mark.",
        keyboard_shortcut=None,
        sort_order=91,
    ),
    DefaultMarkingToolDefinition(
        tool_type=MarkingPaletteToolType.CODE,
        value="L1",
        label="Level 1 – 2 marks",
        description="Level 1 response awarded 2 marks.",
        keyboard_shortcut=None,
        sort_order=92,
    ),
    DefaultMarkingToolDefinition(
        tool_type=MarkingPaletteToolType.CODE,
        value="L2^2",
        label="Level 2 – 3 marks",
        description="Level 2 response awarded 3 marks.",
        keyboard_shortcut=None,
        sort_order=93,
    ),
    DefaultMarkingToolDefinition(
        tool_type=MarkingPaletteToolType.CODE,
        value="L2",
        label="Level 2 – 4 marks",
        description="Level 2 response awarded 4 marks.",
        keyboard_shortcut=None,
        sort_order=94,
    ),
    DefaultMarkingToolDefinition(
        tool_type=MarkingPaletteToolType.CODE,
        value="L3^",
        label="Level 3 – 5 marks",
        description="Level 3 response awarded 5 marks.",
        keyboard_shortcut=None,
        sort_order=95,
    ),
    DefaultMarkingToolDefinition(
        tool_type=MarkingPaletteToolType.CODE,
        value="L3",
        label="Level 3 – 6 marks",
        description="Level 3 response awarded 6 marks.",
        keyboard_shortcut=None,
        sort_order=96,
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


LEGACY_LEVEL_RESPONSE_TOOL_KEYS = frozenset(
    {
        (
            MarkingPaletteToolType.CODE,
            "L1^",
        ),
    }
)

EXACT_LEVEL_RESPONSE_TOOL_KEYS = frozenset(
    {
        (
            MarkingPaletteToolType.CODE,
            "L1^1",
        ),
        (
            MarkingPaletteToolType.CODE,
            "L1",
        ),
        (
            MarkingPaletteToolType.CODE,
            "L2^2",
        ),
        (
            MarkingPaletteToolType.CODE,
            "L2",
        ),
        (
            MarkingPaletteToolType.CODE,
            "L3^",
        ),
        (
            MarkingPaletteToolType.CODE,
            "L3",
        ),
    }
)


async def get_default_marking_palette(
    db: AsyncSession,
    school_id: int,
) -> MarkingPalette:
    """
    Return the active school-wide default marking palette
    without performing maintenance writes.

    The normal marking workspace should use this read path.
    The ensure operation is retained as a fallback for schools
    whose default palette has not yet been initialised.
    """

    if (
        not isinstance(school_id, int)
        or isinstance(school_id, bool)
        or school_id < 1
    ):
        raise ValueError(
            "school_id must be a positive integer.",
        )

    repository = MarkingPaletteRepository(
        db,
    )

    palette = await repository.get_default_palette(
        school_id,
        subject_id=None,
        include_relationships=True,
    )

    if palette is not None:
        existing_keys = {
            (
                tool.tool_type,
                tool.value,
            )
            for tool in palette.tools
        }

        defaults_complete = all(
            (
                definition.tool_type,
                definition.value,
            )
            in existing_keys
            for definition in DEFAULT_MARKING_TOOLS
        )

        legacy_tools_active = any(
            (
                tool.tool_type,
                tool.value,
            )
            in LEGACY_LEVEL_RESPONSE_TOOL_KEYS
            and tool.is_active
            for tool in palette.tools
        )

        exact_level_tools_inactive = any(
            (
                tool.tool_type,
                tool.value,
            )
            in EXACT_LEVEL_RESPONSE_TOOL_KEYS
            and not tool.is_active
            for tool in palette.tools
        )

        if (
            defaults_complete
            and not legacy_tools_active
            and not exact_level_tools_inactive
        ):
            return palette

    return await ensure_default_marking_palette(
        db,
        school_id,
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

        for tool in existing_tools:
            tool_key = (
                tool.tool_type,
                tool.value,
            )

            if (
                tool_key
                in LEGACY_LEVEL_RESPONSE_TOOL_KEYS
                and tool.is_active
            ):
                tool.is_active = False

            if (
                tool_key
                in EXACT_LEVEL_RESPONSE_TOOL_KEYS
                and not tool.is_active
            ):
                tool.is_active = True

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






