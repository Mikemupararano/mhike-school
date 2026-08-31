from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.assessment_marking_annotation import (
    AssessmentMarkingAnnotation,
    MarkingAnnotationSurfaceType,
    MarkingAnnotationType,
)
from app.models.assessment_response import (
    AssessmentResponse,
    AssessmentResponseStatus,
    MarkingDecisionStatus,
)
from app.models.marking_palette import (
    MarkingPaletteTool,
    MarkingPaletteToolType,
)
from app.models.marking_decision_revision import (
    MarkingDecisionRevisionChangeType,
    MarkingDecisionRevisionSource,
)
from app.models.user import User
from app.repositories.assessment_marking import (
    AssessmentMarkingRepository,
)
from app.repositories.assessment_marking_annotation import (
    AssessmentMarkingAnnotationRepository,
)
from app.repositories.marking_palette import (
    MarkingPaletteRepository,
)
from app.services.assessment_marking_service import (
    _ensure_decision_editable,
    _ensure_marker_or_admin,
    _ensure_response_marking_access,
    _get_authoritative_response_maximum_mark,
    _get_response_or_404,
    list_script_responses,
)


_UNSET = object()

_TICK_SYMBOL = "✓"
_CROSS_SYMBOL = "✗"


def _is_score_annotation(
    annotation_type: MarkingAnnotationType,
    value: str | None,
) -> bool:
    return (
        annotation_type == MarkingAnnotationType.SYMBOL
        and value in {
            _TICK_SYMBOL,
            _CROSS_SYMBOL,
        }
    )


def _is_tick_annotation(
    annotation: AssessmentMarkingAnnotation,
) -> bool:
    return (
        annotation.annotation_type
        == MarkingAnnotationType.SYMBOL
        and annotation.value == _TICK_SYMBOL
        and annotation.deleted_at is None
    )


def _ensure_tick_scoring_consistent(
    *,
    decision_mark: Decimal | None,
    active_tick_count: int,
) -> None:
    """
    Prevent tick/cross scoring from silently replacing an
    incompatible existing authoritative mark.

    Tick-scored decisions must satisfy:
        mark_awarded == number of active ticks

    A pristine None mark is allowed only when there are no
    existing active ticks.
    """

    tick_mark = Decimal(
        active_tick_count,
    )

    if decision_mark is None:
        if active_tick_count == 0:
            return

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Existing marking evidence is inconsistent with "
                "the authoritative question mark. Resolve the "
                "mark before using tick or cross scoring."
            ),
        )

    if Decimal(decision_mark) != tick_mark:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "The existing question mark is not consistent "
                "with the active tick annotations. Resolve the "
                "mark before using tick or cross scoring."
            ),
        )


def _normalise_decision_revision(
    value: Any,
) -> int | None:
    if value is None:
        return None

    if isinstance(
        value,
        bool,
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=(
                "expected_decision_revision must be "
                "a non-negative integer"
            ),
        )

    try:
        revision = int(
            value,
        )
    except (
        TypeError,
        ValueError,
    ) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=(
                "expected_decision_revision must be "
                "a non-negative integer"
            ),
        ) from exc

    if revision < 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=(
                "expected_decision_revision must be "
                "a non-negative integer"
            ),
        )

    return revision


def _utc_now() -> datetime:
    return datetime.now(
        timezone.utc,
    )


def _normalise_annotation_type(
    value: MarkingAnnotationType | str,
) -> MarkingAnnotationType:
    if isinstance(
        value,
        MarkingAnnotationType,
    ):
        return value

    try:
        return MarkingAnnotationType(
            str(value).strip().lower(),
        )
    except (TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Invalid marking annotation type: {value!r}",
        ) from exc


def _normalise_surface_type(
    value: MarkingAnnotationSurfaceType | str,
) -> MarkingAnnotationSurfaceType:
    if isinstance(
        value,
        MarkingAnnotationSurfaceType,
    ):
        return value

    try:
        return MarkingAnnotationSurfaceType(
            str(value).strip().lower(),
        )
    except (TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Invalid annotation surface type: {value!r}",
        ) from exc


def _normalise_optional_text(
    value: str | None,
    *,
    field_name: str,
    maximum_length: int | None = None,
) -> str | None:
    if value is None:
        return None

    cleaned = str(
        value,
    ).strip()

    if not cleaned:
        return None

    if (
        maximum_length is not None
        and len(cleaned) > maximum_length
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=(
                f"{field_name} cannot exceed "
                f"{maximum_length} characters"
            ),
        )

    return cleaned


def _normalise_coordinate(
    value: Any,
    *,
    field_name: str,
    required: bool,
) -> Decimal | None:
    if value is None:
        if required:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=f"{field_name} is required",
            )

        return None

    if isinstance(
        value,
        bool,
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"{field_name} must be numeric",
        )

    try:
        result = Decimal(
            str(value),
        )
    except (
        InvalidOperation,
        TypeError,
        ValueError,
    ) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"{field_name} must be numeric",
        ) from exc

    if not result.is_finite():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"{field_name} must be finite",
        )

    if (
        result < Decimal("0")
        or result > Decimal("1")
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"{field_name} must be between 0 and 1",
        )

    return result


def _normalise_page_number(
    value: int | None,
) -> int | None:
    if value is None:
        return None

    if (
        not isinstance(value, int)
        or isinstance(value, bool)
        or value < 1
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="page_number must be a positive integer",
        )

    return value


def _validate_surface(
    *,
    surface_type: MarkingAnnotationSurfaceType,
    surface_reference: str | None,
    page_number: int | None,
) -> None:
    if surface_type == MarkingAnnotationSurfaceType.RESPONSE:
        if surface_reference is not None or page_number is not None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=(
                    "Response-surface annotations cannot use "
                    "surface_reference or page_number"
                ),
            )
        return

    if surface_type == MarkingAnnotationSurfaceType.QUESTION_ASSET:
        if surface_reference is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=(
                    "Question-asset annotations require "
                    "surface_reference"
                ),
            )

        if page_number is not None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=(
                    "Question-asset annotations cannot use "
                    "page_number"
                ),
            )
        return

    if surface_type == MarkingAnnotationSurfaceType.SCRIPT_PAGE:
        if page_number is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Script-page annotations require page_number",
            )

        if surface_reference is not None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=(
                    "Script-page annotations cannot use "
                    "surface_reference"
                ),
            )
        return

    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        detail=f"Unsupported annotation surface type: {surface_type!r}",
    )


def _normalise_revision(
    value: int,
) -> int:
    if (
        not isinstance(value, int)
        or isinstance(value, bool)
        or value < 1
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="revision must be a positive integer",
        )

    return value


def _map_palette_tool_type(
    tool_type: MarkingPaletteToolType,
) -> MarkingAnnotationType:
    try:
        return MarkingAnnotationType(
            tool_type.value,
        )
    except (TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Palette tool type cannot be used as an annotation",
        ) from exc


def _validate_geometry(
    *,
    annotation_type: MarkingAnnotationType,
    x: Decimal,
    y: Decimal,
    end_x: Decimal | None,
    end_y: Decimal | None,
    width: Decimal | None,
    height: Decimal | None,
) -> None:
    del x
    del y

    if annotation_type in {
        MarkingAnnotationType.LINE,
        MarkingAnnotationType.ARROW,
    }:
        if end_x is None or end_y is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=(
                    "Line and arrow annotations require "
                    "end_x and end_y"
                ),
            )

        if width is not None or height is not None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=(
                    "Line and arrow annotations cannot use "
                    "width or height"
                ),
            )

        return

    if annotation_type == MarkingAnnotationType.HIGHLIGHT:
        if width is None or height is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=(
                    "Highlight annotations require width and height"
                ),
            )

        if end_x is not None or end_y is not None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=(
                    "Highlight annotations cannot use "
                    "end_x or end_y"
                ),
            )

        return

    if (
        end_x is not None
        or end_y is not None
        or width is not None
        or height is not None
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=(
                "Point annotations cannot use end coordinates "
                "or dimensions"
            ),
        )


async def _get_annotation_or_404(
    db: AsyncSession,
    annotation_id: int,
    *,
    include_deleted: bool = False,
) -> AssessmentMarkingAnnotation:
    annotation = await AssessmentMarkingAnnotationRepository(
        db,
    ).get_by_id(
        annotation_id,
        include_relationships=True,
        include_deleted=include_deleted,
    )

    if annotation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assessment marking annotation not found",
        )

    return annotation


async def _ensure_annotation_access(
    db: AsyncSession,
    current_user: User,
    annotation: AssessmentMarkingAnnotation,
) -> AssessmentResponse:
    response = await _get_response_or_404(
        db,
        annotation.response_id,
        include_relationships=True,
    )

    await _ensure_response_marking_access(
        db,
        current_user,
        response,
    )

    return response


async def _resolve_palette_tool(
    db: AsyncSession,
    *,
    palette_tool_id: int,
    response: AssessmentResponse,
) -> MarkingPaletteTool:
    if (
        not isinstance(palette_tool_id, int)
        or isinstance(palette_tool_id, bool)
        or palette_tool_id < 1
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="palette_tool_id must be a positive integer",
        )

    tool = await MarkingPaletteRepository(
        db,
    ).get_tool_by_id(
        palette_tool_id,
    )

    if tool is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Marking palette tool not found",
        )

    palette = tool.palette

    if palette is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Marking palette tool is not linked to a palette",
        )

    if not palette.is_active:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Marking palette is inactive",
        )

    if not tool.is_active:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Marking palette tool is inactive",
        )

    script = response.script

    if script is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Assessment response is not linked to a script",
        )

    candidate = script.candidate

    if candidate is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Assessment script is not linked to a candidate",
        )

    assessment = candidate.assessment

    if assessment is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Assessment candidate is not linked to an assessment",
        )

    if palette.school_id != assessment.school_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "Marking palette tool does not belong to "
                "the assessment school"
            ),
        )

    return tool


def _ensure_annotation_marker_access(
    current_user: User,
    response: AssessmentResponse,
) -> None:
    """
    Restrict annotation changes to the allocated marker or administrators.

    Annotations are part of primary marking, so a marking decision must
    already exist before examiner annotations can be created or changed.
    """

    decision = response.marking_decision

    if decision is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "A marking decision must exist before "
                "annotations can be changed"
            ),
        )

    _ensure_decision_editable(
        decision,
    )

    _ensure_marker_or_admin(
        current_user,
        decision,
    )


def _ensure_response_can_be_annotated(
    response: AssessmentResponse,
) -> None:
    if response.status != AssessmentResponseStatus.SUBMITTED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only submitted responses can be annotated",
        )


async def list_script_marking_annotations(
    db: AsyncSession,
    current_user: User,
    script_id: int,
    *,
    include_deleted: bool = False,
) -> list[AssessmentMarkingAnnotation]:
    """
    Return all examiner annotations for one script in one
    database query after validating script-level access.
    """

    responses = await list_script_responses(
        db=db,
        current_user=current_user,
        script_id=script_id,
        response_status=None,
    )

    response_ids = [
        response.id
        for response in responses
    ]

    if not response_ids:
        return []

    return await AssessmentMarkingAnnotationRepository(
        db,
    ).list_for_responses(
        response_ids,
        include_deleted=include_deleted,
        include_relationships=False,
    )

async def list_marking_annotations(
    db: AsyncSession,
    current_user: User,
    response_id: int,
    *,
    include_deleted: bool = False,
) -> list[AssessmentMarkingAnnotation]:
    response = await _get_response_or_404(
        db,
        response_id,
        include_relationships=True,
    )

    await _ensure_response_marking_access(
        db,
        current_user,
        response,
    )

    return await AssessmentMarkingAnnotationRepository(
        db,
    ).list_for_response(
        response.id,
        include_deleted=include_deleted,
        include_relationships=True,
    )


async def get_marking_annotation(
    db: AsyncSession,
    current_user: User,
    annotation_id: int,
    *,
    include_deleted: bool = False,
) -> AssessmentMarkingAnnotation:
    annotation = await _get_annotation_or_404(
        db,
        annotation_id,
        include_deleted=include_deleted,
    )

    await _ensure_annotation_access(
        db,
        current_user,
        annotation,
    )

    return annotation


async def create_marking_annotation(
    db: AsyncSession,
    current_user: User,
    response_id: int,
    *,
    palette_tool_id: int,
    expected_decision_revision: int | None = None,
    x: Any,
    y: Any,
    surface_type: MarkingAnnotationSurfaceType | str = (
        MarkingAnnotationSurfaceType.RESPONSE
    ),
    surface_reference: str | None = None,
    page_number: int | None = None,
    end_x: Any = None,
    end_y: Any = None,
    width: Any = None,
    height: Any = None,
    text: str | None = None,
) -> AssessmentMarkingAnnotation:
    expected_decision_revision = (
        _normalise_decision_revision(
            expected_decision_revision,
        )
    )

    response = await _get_response_or_404(
        db,
        response_id,
        include_relationships=True,
    )

    await _ensure_response_marking_access(
        db,
        current_user,
        response,
    )

    _ensure_response_can_be_annotated(
        response,
    )

    _ensure_annotation_marker_access(
        current_user,
        response,
    )

    tool = await _resolve_palette_tool(
        db,
        palette_tool_id=palette_tool_id,
        response=response,
    )

    annotation_type = _map_palette_tool_type(
        tool.tool_type,
    )

    normalized_x = _normalise_coordinate(
        x,
        field_name="x",
        required=True,
    )
    normalized_y = _normalise_coordinate(
        y,
        field_name="y",
        required=True,
    )
    normalized_end_x = _normalise_coordinate(
        end_x,
        field_name="end_x",
        required=False,
    )
    normalized_end_y = _normalise_coordinate(
        end_y,
        field_name="end_y",
        required=False,
    )
    normalized_width = _normalise_coordinate(
        width,
        field_name="width",
        required=False,
    )
    normalized_height = _normalise_coordinate(
        height,
        field_name="height",
        required=False,
    )

    _validate_geometry(
        annotation_type=annotation_type,
        x=normalized_x,
        y=normalized_y,
        end_x=normalized_end_x,
        end_y=normalized_end_y,
        width=normalized_width,
        height=normalized_height,
    )

    normalized_text = _normalise_optional_text(
        text,
        field_name="text",
    )

    if (
        annotation_type == MarkingAnnotationType.TEXT
        and normalized_text is None
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Text annotations require text",
        )

    if (
        annotation_type != MarkingAnnotationType.TEXT
        and normalized_text is not None
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Only text annotations can contain text",
        )

    normalized_surface_type = _normalise_surface_type(
        surface_type,
    )
    normalized_surface_reference = _normalise_optional_text(
        surface_reference,
        field_name="surface_reference",
        maximum_length=255,
    )
    normalized_page_number = _normalise_page_number(
        page_number,
    )

    _validate_surface(
        surface_type=normalized_surface_type,
        surface_reference=normalized_surface_reference,
        page_number=normalized_page_number,
    )

    annotation = AssessmentMarkingAnnotation(
        response_id=response.id,
        marker_id=current_user.id,
        palette_tool_id=tool.id,
        annotation_type=annotation_type,
        value=tool.value,
        label_snapshot=tool.label,
        text=normalized_text,
        surface_type=normalized_surface_type,
        surface_reference=normalized_surface_reference,
        page_number=normalized_page_number,
        x=normalized_x,
        y=normalized_y,
        end_x=normalized_end_x,
        end_y=normalized_end_y,
        width=normalized_width,
        height=normalized_height,
        revision=1,
        deleted_at=None,
        deleted_by_id=None,
    )

    repository = AssessmentMarkingAnnotationRepository(
        db,
    )

    marking_repository = AssessmentMarkingRepository(
        db,
    )

    is_score_annotation = _is_score_annotation(
        annotation_type,
        tool.value,
    )

    if (
        is_score_annotation
        and expected_decision_revision is None
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=(
                "expected_decision_revision is required "
                "for tick and cross annotations"
            ),
        )

    try:
        locked_decision = None

        if is_score_annotation:
            decision = response.marking_decision

            if decision is None:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=(
                        "A marking decision must exist before "
                        "tick or cross annotations can be used"
                    ),
                )

            locked_decision = (
                await marking_repository
                .get_decision_by_id_for_update(
                    decision.id,
                )
            )

            if locked_decision is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Marking decision not found",
                )

            if (
                locked_decision.revision
                != expected_decision_revision
            ):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=(
                        "Marking decision has changed since it "
                        "was loaded. Refresh the decision and "
                        "try again."
                    ),
                )

            _ensure_decision_editable(
                locked_decision,
            )
            _ensure_marker_or_admin(
                current_user,
                locked_decision,
            )

            existing_annotations = (
                await repository.list_for_response(
                    response.id,
                    include_deleted=False,
                    include_relationships=False,
                )
            )

            existing_tick_count = sum(
                1
                for item in existing_annotations
                if _is_tick_annotation(
                    item,
                )
            )

            _ensure_tick_scoring_consistent(
                decision_mark=locked_decision.mark_awarded,
                active_tick_count=existing_tick_count,
            )

        annotation = await repository.create(
            annotation,
        )

        if is_score_annotation:
            active_annotations = (
                await repository.list_for_response(
                    response.id,
                    include_deleted=False,
                    include_relationships=False,
                )
            )

            tick_count = sum(
                1
                for item in active_annotations
                if _is_tick_annotation(
                    item,
                )
            )

            authoritative_mark = Decimal(
                tick_count,
            )

            maximum_mark = (
                await _get_authoritative_response_maximum_mark(
                    db,
                    response,
                )
            )

            if authoritative_mark > maximum_mark:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                    detail=(
                        "The number of tick annotations exceeds "
                        "the question maximum mark"
                    ),
                )

            assert locked_decision is not None

            values = {
                "mark_awarded": authoritative_mark,
                "status": MarkingDecisionStatus.MARKED,
                "marked_at": (
                    locked_decision.marked_at
                    or _utc_now()
                ),
            }

            decision_changed = any(
                getattr(
                    locked_decision,
                    field_name,
                )
                != field_value
                for (
                    field_name,
                    field_value,
                ) in values.items()
            )

            if decision_changed:
                revision = (
                    await marking_repository
                    .update_decision_with_revision(
                        locked_decision.id,
                        expected_decision_revision,
                        values=values,
                        changed_by_id=current_user.id,
                        change_type=(
                            MarkingDecisionRevisionChangeType
                            .INSTANT_MARKED
                        ),
                        source=(
                            MarkingDecisionRevisionSource
                            .QUICK_MARK
                        ),
                    )
                )

                if revision is None:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=(
                            "Marking decision has changed since "
                            "it was loaded. Refresh the decision "
                            "and try again."
                        ),
                    )

        await db.commit()

        return await _get_annotation_or_404(
            db,
            annotation.id,
            include_deleted=False,
        )

    except HTTPException:
        await db.rollback()
        raise
    except Exception:
        await db.rollback()
        raise


async def update_marking_annotation(
    db: AsyncSession,
    current_user: User,
    annotation_id: int,
    *,
    revision: int,
    x: Any = _UNSET,
    y: Any = _UNSET,
    end_x: Any = _UNSET,
    end_y: Any = _UNSET,
    width: Any = _UNSET,
    height: Any = _UNSET,
    text: str | None | object = _UNSET,
    surface_type: MarkingAnnotationSurfaceType | str | object = _UNSET,
    surface_reference: str | None | object = _UNSET,
    page_number: int | None | object = _UNSET,
) -> AssessmentMarkingAnnotation:
    expected_revision = _normalise_revision(
        revision,
    )

    annotation = await _get_annotation_or_404(
        db,
        annotation_id,
        include_deleted=False,
    )

    response = await _ensure_annotation_access(
        db,
        current_user,
        annotation,
    )

    _ensure_response_can_be_annotated(
        response,
    )

    _ensure_annotation_marker_access(
        current_user,
        response,
    )

    current_x = annotation.x
    current_y = annotation.y
    current_end_x = annotation.end_x
    current_end_y = annotation.end_y
    current_width = annotation.width
    current_height = annotation.height
    current_text = annotation.text
    current_surface_type = annotation.surface_type
    current_surface_reference = annotation.surface_reference
    current_page_number = annotation.page_number

    if x is not _UNSET:
        current_x = _normalise_coordinate(
            x,
            field_name="x",
            required=True,
        )

    if y is not _UNSET:
        current_y = _normalise_coordinate(
            y,
            field_name="y",
            required=True,
        )

    if end_x is not _UNSET:
        current_end_x = _normalise_coordinate(
            end_x,
            field_name="end_x",
            required=False,
        )

    if end_y is not _UNSET:
        current_end_y = _normalise_coordinate(
            end_y,
            field_name="end_y",
            required=False,
        )

    if width is not _UNSET:
        current_width = _normalise_coordinate(
            width,
            field_name="width",
            required=False,
        )

    if height is not _UNSET:
        current_height = _normalise_coordinate(
            height,
            field_name="height",
            required=False,
        )

    if text is not _UNSET:
        current_text = _normalise_optional_text(
            text,
            field_name="text",
        )

    if surface_type is not _UNSET:
        current_surface_type = _normalise_surface_type(
            surface_type,
        )

    if surface_reference is not _UNSET:
        current_surface_reference = _normalise_optional_text(
            surface_reference,
            field_name="surface_reference",
            maximum_length=255,
        )

    if page_number is not _UNSET:
        current_page_number = _normalise_page_number(
            page_number,
        )

    _validate_geometry(
        annotation_type=annotation.annotation_type,
        x=current_x,
        y=current_y,
        end_x=current_end_x,
        end_y=current_end_y,
        width=current_width,
        height=current_height,
    )

    if (
        annotation.annotation_type == MarkingAnnotationType.TEXT
        and current_text is None
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Text annotations require text",
        )

    if (
        annotation.annotation_type != MarkingAnnotationType.TEXT
        and current_text is not None
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Only text annotations can contain text",
        )

    values = {
        "x": current_x,
        "y": current_y,
        "end_x": current_end_x,
        "end_y": current_end_y,
        "width": current_width,
        "height": current_height,
        "text": current_text,
        "surface_type": current_surface_type,
        "surface_reference": current_surface_reference,
        "page_number": current_page_number,
    }

    repository = AssessmentMarkingAnnotationRepository(
        db,
    )

    try:
        updated = await repository.update_if_revision(
            annotation.id,
            expected_revision,
            values=values,
        )

        if not updated:
            await db.rollback()

            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "Marking annotation changed or was deleted "
                    "by another request"
                ),
            )

        await db.commit()

        return await _get_annotation_or_404(
            db,
            annotation.id,
            include_deleted=False,
        )
    except HTTPException:
        raise
    except Exception:
        await db.rollback()
        raise


async def delete_marking_annotation(
    db: AsyncSession,
    current_user: User,
    annotation_id: int,
    *,
    revision: int,
    expected_decision_revision: int | None = None,
) -> AssessmentMarkingAnnotation:
    expected_revision = _normalise_revision(
        revision,
    )
    expected_decision_revision = (
        _normalise_decision_revision(
            expected_decision_revision,
        )
    )

    annotation = await _get_annotation_or_404(
        db,
        annotation_id,
        include_deleted=False,
    )

    response = await _ensure_annotation_access(
        db,
        current_user,
        annotation,
    )

    _ensure_response_can_be_annotated(
        response,
    )

    _ensure_annotation_marker_access(
        current_user,
        response,
    )

    repository = AssessmentMarkingAnnotationRepository(
        db,
    )

    marking_repository = AssessmentMarkingRepository(
        db,
    )

    is_score_annotation = _is_score_annotation(
        annotation.annotation_type,
        annotation.value,
    )

    if (
        is_score_annotation
        and expected_decision_revision is None
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=(
                "expected_decision_revision is required "
                "for tick and cross annotations"
            ),
        )

    try:
        locked_decision = None

        if is_score_annotation:
            decision = response.marking_decision

            if decision is None:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=(
                        "A marking decision must exist before "
                        "tick or cross annotations can be removed"
                    ),
                )

            locked_decision = (
                await marking_repository
                .get_decision_by_id_for_update(
                    decision.id,
                )
            )

            if locked_decision is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Marking decision not found",
                )

            if (
                locked_decision.revision
                != expected_decision_revision
            ):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=(
                        "Marking decision has changed since it "
                        "was loaded. Refresh the decision and "
                        "try again."
                    ),
                )

            _ensure_decision_editable(
                locked_decision,
            )
            _ensure_marker_or_admin(
                current_user,
                locked_decision,
            )

            existing_annotations = (
                await repository.list_for_response(
                    response.id,
                    include_deleted=False,
                    include_relationships=False,
                )
            )

            existing_tick_count = sum(
                1
                for item in existing_annotations
                if _is_tick_annotation(
                    item,
                )
            )

            _ensure_tick_scoring_consistent(
                decision_mark=locked_decision.mark_awarded,
                active_tick_count=existing_tick_count,
            )

        deleted = await repository.soft_delete_if_revision(
            annotation.id,
            expected_revision,
            deleted_at=_utc_now(),
            deleted_by_id=current_user.id,
        )

        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "Marking annotation changed or was deleted "
                    "by another request"
                ),
            )

        if is_score_annotation:
            active_annotations = (
                await repository.list_for_response(
                    response.id,
                    include_deleted=False,
                    include_relationships=False,
                )
            )

            tick_count = sum(
                1
                for item in active_annotations
                if _is_tick_annotation(
                    item,
                )
            )

            authoritative_mark = Decimal(
                tick_count,
            )

            maximum_mark = (
                await _get_authoritative_response_maximum_mark(
                    db,
                    response,
                )
            )

            if authoritative_mark > maximum_mark:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=(
                        "Active tick annotations exceed the "
                        "question maximum mark"
                    ),
                )

            assert locked_decision is not None

            values = {
                "mark_awarded": authoritative_mark,
                "status": MarkingDecisionStatus.MARKED,
                "marked_at": (
                    locked_decision.marked_at
                    or _utc_now()
                ),
            }

            decision_changed = any(
                getattr(
                    locked_decision,
                    field_name,
                )
                != field_value
                for (
                    field_name,
                    field_value,
                ) in values.items()
            )

            if decision_changed:
                revision = (
                    await marking_repository
                    .update_decision_with_revision(
                        locked_decision.id,
                        expected_decision_revision,
                        values=values,
                        changed_by_id=current_user.id,
                        change_type=(
                            MarkingDecisionRevisionChangeType
                            .INSTANT_MARKED
                        ),
                        source=(
                            MarkingDecisionRevisionSource
                            .QUICK_MARK
                        ),
                    )
                )

                if revision is None:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=(
                            "Marking decision has changed since "
                            "it was loaded. Refresh the decision "
                            "and try again."
                        ),
                    )

        await db.commit()

        return await _get_annotation_or_404(
            db,
            annotation.id,
            include_deleted=True,
        )

    except HTTPException:
        await db.rollback()
        raise
    except Exception:
        await db.rollback()
        raise



