from __future__ import annotations

from decimal import Decimal

import pytest
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.assessment_marking_annotation import (
    MarkingAnnotationType,
)
from app.models.assessment_response import MarkingDecisionStatus
from app.models.marking_palette import (
    MarkingPaletteTool,
    MarkingPaletteToolType,
)
from app.models.school import School
from app.models.user import UserRole
from app.services.assessment_marking_annotation_service import (
    create_marking_annotation,
    delete_marking_annotation,
    get_marking_annotation,
    list_marking_annotations,
    update_marking_annotation,
)
from app.services.assessment_marking_palette_service import (
    ensure_default_marking_palette,
)
from app.services.assessment_marking_service import (
    create_marking_decision,
    create_response,
    submit_response,
)
from tests.conftest import create_test_user
from tests.test_assessment_marking_service import (
    _build_marking_context,
)


async def _build_annotation_context(
    db_session: AsyncSession,
    teacher_user,
):
    """
    Build one submitted response with an allocated marking decision and
    the school's default marking palette.
    """

    context = await _build_marking_context(
        db_session,
        teacher_user,
    )

    response = await create_response(
        db=db_session,
        current_user=teacher_user,
        script_id=context["script"].id,
        question_id=context["question"].id,
        response_text="v = u + at",
    )

    response = await submit_response(
        db=db_session,
        current_user=teacher_user,
        response_id=response.id,
    )

    decision = await create_marking_decision(
        db=db_session,
        current_user=teacher_user,
        response_id=response.id,
    )

    palette = await ensure_default_marking_palette(
        db_session,
        school_id=teacher_user.school_id,
    )

    return {
        **context,
        "response": response,
        "decision": decision,
        "palette": palette,
    }


def _find_tool(
    palette,
    *,
    tool_type: MarkingPaletteToolType,
    value: str,
) -> MarkingPaletteTool:
    for tool in palette.tools:
        if (
            tool.tool_type == tool_type
            and tool.value == value
        ):
            return tool

    raise AssertionError(
        f"Palette tool not found: {tool_type.value} {value!r}"
    )


@pytest.mark.asyncio
async def test_marker_can_create_symbol_annotation(
    db_session: AsyncSession,
    teacher_user,
):
    context = await _build_annotation_context(
        db_session,
        teacher_user,
    )

    tick_tool = _find_tool(
        context["palette"],
        tool_type=MarkingPaletteToolType.SYMBOL,
        value="✓",
    )

    annotation = await create_marking_annotation(
        db=db_session,
        current_user=teacher_user,
        response_id=context["response"].id,
        palette_tool_id=tick_tool.id,
        x=Decimal("0.250000"),
        y=Decimal("0.500000"),
    )

    assert annotation.id is not None
    assert annotation.response_id == context["response"].id
    assert annotation.marker_id == teacher_user.id
    assert annotation.palette_tool_id == tick_tool.id
    assert annotation.annotation_type == MarkingAnnotationType.SYMBOL
    assert annotation.value == "✓"
    assert annotation.label_snapshot == tick_tool.label
    assert annotation.x == Decimal("0.250000")
    assert annotation.y == Decimal("0.500000")
    assert annotation.revision == 1
    assert annotation.deleted_at is None


@pytest.mark.asyncio
async def test_annotation_snapshots_palette_label_and_value(
    db_session: AsyncSession,
    teacher_user,
):
    context = await _build_annotation_context(
        db_session,
        teacher_user,
    )

    ecf_tool = _find_tool(
        context["palette"],
        tool_type=MarkingPaletteToolType.CODE,
        value="ECF",
    )

    annotation = await create_marking_annotation(
        db=db_session,
        current_user=teacher_user,
        response_id=context["response"].id,
        palette_tool_id=ecf_tool.id,
        x="0.10",
        y="0.20",
    )

    original_value = annotation.value
    original_label = annotation.label_snapshot

    ecf_tool.value = "ECF-CHANGED"
    ecf_tool.label = "Changed label"

    await db_session.commit()

    annotation = await get_marking_annotation(
        db=db_session,
        current_user=teacher_user,
        annotation_id=annotation.id,
    )

    assert annotation.value == original_value
    assert annotation.label_snapshot == original_label


@pytest.mark.asyncio
async def test_marker_can_list_response_annotations(
    db_session: AsyncSession,
    teacher_user,
):
    context = await _build_annotation_context(
        db_session,
        teacher_user,
    )

    tick_tool = _find_tool(
        context["palette"],
        tool_type=MarkingPaletteToolType.SYMBOL,
        value="✓",
    )

    cross_tool = _find_tool(
        context["palette"],
        tool_type=MarkingPaletteToolType.SYMBOL,
        value="✗",
    )

    first = await create_marking_annotation(
        db=db_session,
        current_user=teacher_user,
        response_id=context["response"].id,
        palette_tool_id=tick_tool.id,
        x="0.10",
        y="0.20",
    )

    second = await create_marking_annotation(
        db=db_session,
        current_user=teacher_user,
        response_id=context["response"].id,
        palette_tool_id=cross_tool.id,
        x="0.30",
        y="0.40",
    )

    annotations = await list_marking_annotations(
        db=db_session,
        current_user=teacher_user,
        response_id=context["response"].id,
    )

    assert [
        annotation.id
        for annotation in annotations
    ] == [
        first.id,
        second.id,
    ]


@pytest.mark.asyncio
async def test_drag_update_increments_annotation_revision(
    db_session: AsyncSession,
    teacher_user,
):
    context = await _build_annotation_context(
        db_session,
        teacher_user,
    )

    tick_tool = _find_tool(
        context["palette"],
        tool_type=MarkingPaletteToolType.SYMBOL,
        value="✓",
    )

    annotation = await create_marking_annotation(
        db=db_session,
        current_user=teacher_user,
        response_id=context["response"].id,
        palette_tool_id=tick_tool.id,
        x="0.10",
        y="0.20",
    )

    updated = await update_marking_annotation(
        db=db_session,
        current_user=teacher_user,
        annotation_id=annotation.id,
        revision=annotation.revision,
        x="0.75",
        y="0.80",
    )

    assert updated.x == Decimal("0.750000")
    assert updated.y == Decimal("0.800000")
    assert updated.revision == 2


@pytest.mark.asyncio
async def test_stale_annotation_revision_is_rejected(
    db_session: AsyncSession,
    teacher_user,
):
    context = await _build_annotation_context(
        db_session,
        teacher_user,
    )

    tick_tool = _find_tool(
        context["palette"],
        tool_type=MarkingPaletteToolType.SYMBOL,
        value="✓",
    )

    annotation = await create_marking_annotation(
        db=db_session,
        current_user=teacher_user,
        response_id=context["response"].id,
        palette_tool_id=tick_tool.id,
        x="0.10",
        y="0.20",
    )

    await update_marking_annotation(
        db=db_session,
        current_user=teacher_user,
        annotation_id=annotation.id,
        revision=1,
        x="0.30",
    )

    with pytest.raises(HTTPException) as exc:
        await update_marking_annotation(
            db=db_session,
            current_user=teacher_user,
            annotation_id=annotation.id,
            revision=1,
            x="0.90",
        )

    assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_annotation_is_soft_deleted(
    db_session: AsyncSession,
    teacher_user,
):
    context = await _build_annotation_context(
        db_session,
        teacher_user,
    )

    tick_tool = _find_tool(
        context["palette"],
        tool_type=MarkingPaletteToolType.SYMBOL,
        value="✓",
    )

    annotation = await create_marking_annotation(
        db=db_session,
        current_user=teacher_user,
        response_id=context["response"].id,
        palette_tool_id=tick_tool.id,
        x="0.10",
        y="0.20",
    )

    deleted = await delete_marking_annotation(
        db=db_session,
        current_user=teacher_user,
        annotation_id=annotation.id,
        revision=annotation.revision,
    )

    assert deleted.deleted_at is not None
    assert deleted.deleted_by_id == teacher_user.id
    assert deleted.revision == 2

    active = await list_marking_annotations(
        db=db_session,
        current_user=teacher_user,
        response_id=context["response"].id,
    )

    assert active == []

    including_deleted = await list_marking_annotations(
        db=db_session,
        current_user=teacher_user,
        response_id=context["response"].id,
        include_deleted=True,
    )

    assert len(including_deleted) == 1
    assert including_deleted[0].id == annotation.id
    assert including_deleted[0].deleted_at is not None


@pytest.mark.asyncio
async def test_inactive_palette_tool_is_rejected(
    db_session: AsyncSession,
    teacher_user,
):
    context = await _build_annotation_context(
        db_session,
        teacher_user,
    )

    tick_tool = _find_tool(
        context["palette"],
        tool_type=MarkingPaletteToolType.SYMBOL,
        value="✓",
    )

    tick_tool.is_active = False
    await db_session.commit()

    with pytest.raises(HTTPException) as exc:
        await create_marking_annotation(
            db=db_session,
            current_user=teacher_user,
            response_id=context["response"].id,
            palette_tool_id=tick_tool.id,
            x="0.10",
            y="0.20",
        )

    assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_cross_school_palette_tool_is_rejected(
    db_session: AsyncSession,
    teacher_user,
):
    school_one = School(
        name="Annotation Test School One",
    )
    school_two = School(
        name="Annotation Test School Two",
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

    assert school_one.id != school_two.id

    teacher_user.school_id = school_one.id
    await db_session.commit()
    await db_session.refresh(
        teacher_user,
    )

    context = await _build_annotation_context(
        db_session,
        teacher_user,
    )

    other_palette = await ensure_default_marking_palette(
        db_session,
        school_id=school_two.id,
    )

    other_tick = _find_tool(
        other_palette,
        tool_type=MarkingPaletteToolType.SYMBOL,
        value="✓",
    )

    assert context["assessment"].school_id == school_one.id
    assert other_palette.school_id == school_two.id

    with pytest.raises(HTTPException) as exc:
        await create_marking_annotation(
            db=db_session,
            current_user=teacher_user,
            response_id=context["response"].id,
            palette_tool_id=other_tick.id,
            x="0.10",
            y="0.20",
        )

    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_line_requires_end_coordinates(
    db_session: AsyncSession,
    teacher_user,
):
    context = await _build_annotation_context(
        db_session,
        teacher_user,
    )

    line_tool = _find_tool(
        context["palette"],
        tool_type=MarkingPaletteToolType.LINE,
        value="LINE",
    )

    with pytest.raises(HTTPException) as exc:
        await create_marking_annotation(
            db=db_session,
            current_user=teacher_user,
            response_id=context["response"].id,
            palette_tool_id=line_tool.id,
            x="0.10",
            y="0.20",
        )

    assert exc.value.status_code == 422


@pytest.mark.asyncio
async def test_highlight_requires_dimensions(
    db_session: AsyncSession,
    teacher_user,
):
    context = await _build_annotation_context(
        db_session,
        teacher_user,
    )

    highlight_tool = _find_tool(
        context["palette"],
        tool_type=MarkingPaletteToolType.HIGHLIGHT,
        value="HIGHLIGHT",
    )

    with pytest.raises(HTTPException) as exc:
        await create_marking_annotation(
            db=db_session,
            current_user=teacher_user,
            response_id=context["response"].id,
            palette_tool_id=highlight_tool.id,
            x="0.10",
            y="0.20",
        )

    assert exc.value.status_code == 422


@pytest.mark.asyncio
async def test_text_annotation_requires_text(
    db_session: AsyncSession,
    teacher_user,
):
    context = await _build_annotation_context(
        db_session,
        teacher_user,
    )

    text_tool = _find_tool(
        context["palette"],
        tool_type=MarkingPaletteToolType.TEXT,
        value="TEXT",
    )

    with pytest.raises(HTTPException) as exc:
        await create_marking_annotation(
            db=db_session,
            current_user=teacher_user,
            response_id=context["response"].id,
            palette_tool_id=text_tool.id,
            x="0.10",
            y="0.20",
        )

    assert exc.value.status_code == 422


@pytest.mark.asyncio
async def test_allocated_marker_guard_blocks_course_teacher_when_reassigned(
    db_session: AsyncSession,
    teacher_user,
):
    context = await _build_annotation_context(
        db_session,
        teacher_user,
    )

    other_teacher = await create_test_user(
        db_session,
        email="annotation.allocated.marker@example.com",
        roles=[UserRole.TEACHER],
        school_id=teacher_user.school_id,
    )

    context["decision"].marker_id = other_teacher.id
    await db_session.commit()

    tick_tool = _find_tool(
        context["palette"],
        tool_type=MarkingPaletteToolType.SYMBOL,
        value="✓",
    )

    with pytest.raises(HTTPException) as exc:
        await create_marking_annotation(
            db=db_session,
            current_user=teacher_user,
            response_id=context["response"].id,
            palette_tool_id=tick_tool.id,
            x="0.10",
            y="0.20",
        )

    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_annotation_rows_persist_in_database(
    db_session: AsyncSession,
    teacher_user,
):
    context = await _build_annotation_context(
        db_session,
        teacher_user,
    )

    bod_tool = _find_tool(
        context["palette"],
        tool_type=MarkingPaletteToolType.CODE,
        value="BOD",
    )

    annotation = await create_marking_annotation(
        db=db_session,
        current_user=teacher_user,
        response_id=context["response"].id,
        palette_tool_id=bod_tool.id,
        x="0.40",
        y="0.60",
    )

    result = await db_session.execute(
        select(
            MarkingPaletteTool,
        ).where(
            MarkingPaletteTool.id == annotation.palette_tool_id,
        )
    )

    persisted_tool = result.scalar_one()

    assert persisted_tool.id == bod_tool.id
    assert annotation.value == "BOD"

@pytest.mark.asyncio
async def test_response_surface_rejects_page_number(
    db_session: AsyncSession,
    teacher_user,
):
    context = await _build_annotation_context(
        db_session,
        teacher_user,
    )

    tick_tool = _find_tool(
        context["palette"],
        tool_type=MarkingPaletteToolType.SYMBOL,
        value="✓",
    )

    with pytest.raises(HTTPException) as exc:
        await create_marking_annotation(
            db=db_session,
            current_user=teacher_user,
            response_id=context["response"].id,
            palette_tool_id=tick_tool.id,
            x="0.10",
            y="0.20",
            surface_type="response",
            page_number=1,
        )

    assert exc.value.status_code == 422


@pytest.mark.asyncio
async def test_question_asset_surface_requires_reference(
    db_session: AsyncSession,
    teacher_user,
):
    context = await _build_annotation_context(
        db_session,
        teacher_user,
    )

    tick_tool = _find_tool(
        context["palette"],
        tool_type=MarkingPaletteToolType.SYMBOL,
        value="✓",
    )

    with pytest.raises(HTTPException) as exc:
        await create_marking_annotation(
            db=db_session,
            current_user=teacher_user,
            response_id=context["response"].id,
            palette_tool_id=tick_tool.id,
            x="0.10",
            y="0.20",
            surface_type="question_asset",
        )

    assert exc.value.status_code == 422


@pytest.mark.asyncio
async def test_script_page_surface_requires_page_number(
    db_session: AsyncSession,
    teacher_user,
):
    context = await _build_annotation_context(
        db_session,
        teacher_user,
    )

    tick_tool = _find_tool(
        context["palette"],
        tool_type=MarkingPaletteToolType.SYMBOL,
        value="✓",
    )

    with pytest.raises(HTTPException) as exc:
        await create_marking_annotation(
            db=db_session,
            current_user=teacher_user,
            response_id=context["response"].id,
            palette_tool_id=tick_tool.id,
            x="0.10",
            y="0.20",
            surface_type="script_page",
        )

    assert exc.value.status_code == 422


@pytest.mark.asyncio
async def test_valid_script_page_annotation_is_created(
    db_session: AsyncSession,
    teacher_user,
):
    context = await _build_annotation_context(
        db_session,
        teacher_user,
    )

    tick_tool = _find_tool(
        context["palette"],
        tool_type=MarkingPaletteToolType.SYMBOL,
        value="✓",
    )

    annotation = await create_marking_annotation(
        db=db_session,
        current_user=teacher_user,
        response_id=context["response"].id,
        palette_tool_id=tick_tool.id,
        x="0.10",
        y="0.20",
        surface_type="script_page",
        page_number=2,
    )

    assert annotation.surface_type.value == "script_page"
    assert annotation.page_number == 2
    assert annotation.surface_reference is None

@pytest.mark.asyncio
async def test_finalised_decision_blocks_annotation_creation(
    db_session: AsyncSession,
    teacher_user,
):
    context = await _build_annotation_context(
        db_session,
        teacher_user,
    )

    context["decision"].status = MarkingDecisionStatus.FINALISED
    await db_session.commit()

    tick_tool = _find_tool(
        context["palette"],
        tool_type=MarkingPaletteToolType.SYMBOL,
        value="✓",
    )

    with pytest.raises(HTTPException) as exc:
        await create_marking_annotation(
            db=db_session,
            current_user=teacher_user,
            response_id=context["response"].id,
            palette_tool_id=tick_tool.id,
            x="0.10",
            y="0.20",
        )

    assert exc.value.status_code == 409
    assert exc.value.detail == "Finalised marking decisions cannot be changed"


@pytest.mark.asyncio
async def test_finalised_decision_blocks_annotation_update(
    db_session: AsyncSession,
    teacher_user,
):
    context = await _build_annotation_context(
        db_session,
        teacher_user,
    )

    tick_tool = _find_tool(
        context["palette"],
        tool_type=MarkingPaletteToolType.SYMBOL,
        value="✓",
    )

    annotation = await create_marking_annotation(
        db=db_session,
        current_user=teacher_user,
        response_id=context["response"].id,
        palette_tool_id=tick_tool.id,
        x="0.10",
        y="0.20",
    )

    context["decision"].status = MarkingDecisionStatus.FINALISED
    await db_session.commit()

    with pytest.raises(HTTPException) as exc:
        await update_marking_annotation(
            db=db_session,
            current_user=teacher_user,
            annotation_id=annotation.id,
            revision=annotation.revision,
            x="0.50",
        )

    assert exc.value.status_code == 409
    assert exc.value.detail == "Finalised marking decisions cannot be changed"


@pytest.mark.asyncio
async def test_finalised_decision_blocks_annotation_delete(
    db_session: AsyncSession,
    teacher_user,
):
    context = await _build_annotation_context(
        db_session,
        teacher_user,
    )

    tick_tool = _find_tool(
        context["palette"],
        tool_type=MarkingPaletteToolType.SYMBOL,
        value="✓",
    )

    annotation = await create_marking_annotation(
        db=db_session,
        current_user=teacher_user,
        response_id=context["response"].id,
        palette_tool_id=tick_tool.id,
        x="0.10",
        y="0.20",
    )

    context["decision"].status = MarkingDecisionStatus.FINALISED
    await db_session.commit()

    with pytest.raises(HTTPException) as exc:
        await delete_marking_annotation(
            db=db_session,
            current_user=teacher_user,
            annotation_id=annotation.id,
            revision=annotation.revision,
        )

    assert exc.value.status_code == 409
    assert exc.value.detail == "Finalised marking decisions cannot be changed"

