from __future__ import annotations

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.marking_palette import (
    MarkingPalette,
    MarkingPaletteTool,
)
from app.models.school import School
from app.services.assessment_marking_palette_service import (
    DEFAULT_MARKING_PALETTE_NAME,
    DEFAULT_MARKING_TOOLS,
    ensure_default_marking_palette,
)


@pytest.mark.asyncio
async def test_default_marking_palette_contains_expected_universal_tools(
    db_session: AsyncSession,
):
    palette = await ensure_default_marking_palette(
        db_session,
        school_id=1,
    )

    assert palette.school_id == 1
    assert palette.subject_id is None
    assert palette.name == DEFAULT_MARKING_PALETTE_NAME
    assert palette.is_default is True
    assert palette.is_active is True

    tools = sorted(
        palette.tools,
        key=lambda tool: (
            tool.sort_order,
            tool.id,
        ),
    )

    assert len(tools) == len(DEFAULT_MARKING_TOOLS) == 13

    actual = [
        (
            tool.tool_type,
            tool.value,
            tool.label,
            tool.sort_order,
            tool.is_active,
        )
        for tool in tools
    ]

    expected = [
        (
            definition.tool_type,
            definition.value,
            definition.label,
            definition.sort_order,
            True,
        )
        for definition in DEFAULT_MARKING_TOOLS
    ]

    assert actual == expected


@pytest.mark.asyncio
async def test_default_marking_palette_is_idempotent(
    db_session: AsyncSession,
):
    first = await ensure_default_marking_palette(
        db_session,
        school_id=1,
    )

    first_palette_id = first.id
    first_tool_ids = {
        tool.id
        for tool in first.tools
    }

    second = await ensure_default_marking_palette(
        db_session,
        school_id=1,
    )

    assert second.id == first_palette_id

    second_tool_ids = {
        tool.id
        for tool in second.tools
    }

    assert second_tool_ids == first_tool_ids
    assert len(second_tool_ids) == 13

    palette_count_result = await db_session.execute(
        select(
            MarkingPalette.id,
        ).where(
            MarkingPalette.school_id == 1,
            MarkingPalette.name == DEFAULT_MARKING_PALETTE_NAME,
        )
    )

    assert len(
        palette_count_result.scalars().all(),
    ) == 1


@pytest.mark.asyncio
async def test_default_marking_palette_preserves_school_customisation(
    db_session: AsyncSession,
):
    palette = await ensure_default_marking_palette(
        db_session,
        school_id=1,
    )

    tick = next(
        tool
        for tool in palette.tools
        if tool.value == "✓"
    )

    tick.label = "Credit given"
    tick.sort_order = 999
    tick.is_active = False

    await db_session.commit()

    refreshed = await ensure_default_marking_palette(
        db_session,
        school_id=1,
    )

    customised_tick = next(
        tool
        for tool in refreshed.tools
        if tool.value == "✓"
    )

    assert customised_tick.id == tick.id
    assert customised_tick.label == "Credit given"
    assert customised_tick.sort_order == 999
    assert customised_tick.is_active is False

    assert len(refreshed.tools) == 13


@pytest.mark.asyncio
async def test_default_marking_palette_isolated_by_school(
    db_session: AsyncSession,
):
    school_one = School(
        name="Marking Palette Test School One",
    )
    school_two = School(
        name="Marking Palette Test School Two",
    )

    db_session.add_all(
        [
            school_one,
            school_two,
        ]
    )

    await db_session.commit()
    await db_session.refresh(
        school_one,
    )
    await db_session.refresh(
        school_two,
    )

    school_one_palette = await ensure_default_marking_palette(
        db_session,
        school_id=school_one.id,
    )

    school_two_palette = await ensure_default_marking_palette(
        db_session,
        school_id=school_two.id,
    )

    assert school_one.id != school_two.id
    assert school_one_palette.id != school_two_palette.id
    assert school_one_palette.school_id == school_one.id
    assert school_two_palette.school_id == school_two.id

    school_one_tool_ids = {
        tool.id
        for tool in school_one_palette.tools
    }

    school_two_tool_ids = {
        tool.id
        for tool in school_two_palette.tools
    }

    assert school_one_tool_ids.isdisjoint(
        school_two_tool_ids,
    )

    assert {
        (
            tool.tool_type,
            tool.value,
        )
        for tool in school_one_palette.tools
    } == {
        (
            tool.tool_type,
            tool.value,
        )
        for tool in school_two_palette.tools
    }


@pytest.mark.asyncio
async def test_missing_default_tool_is_restored_without_overwriting_others(
    db_session: AsyncSession,
):
    palette = await ensure_default_marking_palette(
        db_session,
        school_id=1,
    )

    tool_to_remove = next(
        tool
        for tool in palette.tools
        if tool.value == "ECF"
    )

    removed_tool_id = tool_to_remove.id

    await db_session.delete(
        tool_to_remove,
    )
    await db_session.commit()

    refreshed = await ensure_default_marking_palette(
        db_session,
        school_id=1,
    )

    ecf_tools = [
        tool
        for tool in refreshed.tools
        if tool.value == "ECF"
    ]

    assert len(ecf_tools) == 1
    assert ecf_tools[0].id != removed_tool_id
    assert ecf_tools[0].label == "Error carried forward"

    assert len(refreshed.tools) == 13


@pytest.mark.asyncio
async def test_palette_tools_are_persisted_as_database_rows(
    db_session: AsyncSession,
):
    palette = await ensure_default_marking_palette(
        db_session,
        school_id=1,
    )

    result = await db_session.execute(
        select(
            MarkingPaletteTool,
        ).where(
            MarkingPaletteTool.palette_id == palette.id,
        )
    )

    tools = list(
        result.scalars().all(),
    )

    assert len(tools) == 13
