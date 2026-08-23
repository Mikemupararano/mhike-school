from __future__ import annotations

from fastapi import (
    APIRouter,
    Depends,
    Query,
    Response,
    status,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.permissions import PermissionService
from app.db.session import get_db
from app.models.assessment_response import (
    AssessmentResponseStatus,
    MarkingDecisionStatus,
)
from app.models.user import User
from app.schemas.assessment_marking import (
    AssessmentResponseCreate,
    AssessmentResponseOut,
    AssessmentResponseStatusUpdate,
    AssessmentResponseUpdate,
    InstantMarkRequest,
    MarkingAnnotationCreate,
    MarkingAnnotationOut,
    MarkingAnnotationUpdate,
    MarkingDecisionCreate,
    MarkingDecisionOut,
    MarkingDecisionStatusUpdate,
    MarkingDecisionUpdate,
    MarkingReviewRequest,
    MarkSchemeItemAwardCreate,
    MarkSchemeItemAwardOut,
)
from app.services.assessment_marking_annotation_service import (
    create_marking_annotation,
    delete_marking_annotation,
    get_marking_annotation,
    list_marking_annotations,
    update_marking_annotation,
)
from app.services.assessment_marking_service import (
    award_mark_scheme_item,
    complete_marking,
    create_marking_decision,
    create_response,
    delete_mark_scheme_item_award,
    delete_marking_decision,
    delete_response,
    finalise_marking,
    get_marking_decision,
    get_response,
    instant_mark_decision,
    list_script_marking_decisions,
    list_script_responses,
    review_marking,
    start_marking,
    submit_response,
    transition_marking_decision_status,
    transition_response_status,
    update_marking_decision,
    update_response,
    void_response,
)

router = APIRouter()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ensure_marking_staff_access(
    current_user: User,
) -> None:
    """
    Ensure the current user may access assessment-marking workflows.

    Detailed course ownership, school isolation, marker ownership,
    moderation permissions, and lifecycle rules are enforced in the
    service layer.
    """

    PermissionService.ensure_active_user(
        current_user,
    )

    PermissionService.ensure_school_staff_or_platform_admin(
        current_user,
    )


# ---------------------------------------------------------------------------
# Script response routes
# ---------------------------------------------------------------------------


@router.post(
    "/scripts/{script_id}/responses",
    response_model=AssessmentResponseOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_assessment_response(
    script_id: int,
    payload: AssessmentResponseCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AssessmentResponseOut:
    """
    Create one response for a script/question pair.
    """

    _ensure_marking_staff_access(
        current_user,
    )

    response = await create_response(
        db=db,
        current_user=current_user,
        script_id=script_id,
        question_id=payload.question_id,
        response_text=payload.response_text,
        response_data=payload.response_data,
        source_reference=payload.source_reference,
    )

    return AssessmentResponseOut.model_validate(
        response,
    )


@router.get(
    "/scripts/{script_id}/responses",
    response_model=list[AssessmentResponseOut],
)
async def get_script_responses(
    script_id: int,
    response_status: AssessmentResponseStatus | None = Query(
        default=None,
    ),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[AssessmentResponseOut]:
    """
    Return responses belonging to one assessment script.
    """

    _ensure_marking_staff_access(
        current_user,
    )

    responses = await list_script_responses(
        db=db,
        current_user=current_user,
        script_id=script_id,
        response_status=response_status,
    )

    return [
        AssessmentResponseOut.model_validate(
            response,
        )
        for response in responses
    ]


@router.get(
    "/scripts/{script_id}/decisions",
    response_model=list[MarkingDecisionOut],
)
async def get_script_marking_decisions(
    script_id: int,
    decision_status: MarkingDecisionStatus | None = Query(
        default=None,
    ),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[MarkingDecisionOut]:
    """
    Return marking decisions belonging to one assessment script.
    """

    _ensure_marking_staff_access(
        current_user,
    )

    decisions = await list_script_marking_decisions(
        db=db,
        current_user=current_user,
        script_id=script_id,
        decision_status=decision_status,
    )

    return [
        MarkingDecisionOut.model_validate(
            decision,
        )
        for decision in decisions
    ]


# ---------------------------------------------------------------------------
# Response routes
# ---------------------------------------------------------------------------


@router.get(
    "/responses/{response_id}",
    response_model=AssessmentResponseOut,
)
async def get_assessment_response(
    response_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AssessmentResponseOut:
    """
    Return one assessment response.
    """

    _ensure_marking_staff_access(
        current_user,
    )

    response = await get_response(
        db=db,
        current_user=current_user,
        response_id=response_id,
    )

    return AssessmentResponseOut.model_validate(
        response,
    )


@router.patch(
    "/responses/{response_id}",
    response_model=AssessmentResponseOut,
)
async def update_assessment_response(
    response_id: int,
    payload: AssessmentResponseUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AssessmentResponseOut:
    """
    Update editable response content.
    """

    _ensure_marking_staff_access(
        current_user,
    )

    response = await update_response(
        db=db,
        current_user=current_user,
        response_id=response_id,
        response_text=payload.response_text,
        response_data=payload.response_data,
        source_reference=payload.source_reference,
    )

    return AssessmentResponseOut.model_validate(
        response,
    )


@router.patch(
    "/responses/{response_id}/status",
    response_model=AssessmentResponseOut,
)
async def update_assessment_response_status(
    response_id: int,
    payload: AssessmentResponseStatusUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AssessmentResponseOut:
    """
    Move a response through an allowed lifecycle transition.
    """

    _ensure_marking_staff_access(
        current_user,
    )

    response = await transition_response_status(
        db=db,
        current_user=current_user,
        response_id=response_id,
        new_status=payload.status,
    )

    return AssessmentResponseOut.model_validate(
        response,
    )


@router.post(
    "/responses/{response_id}/submit",
    response_model=AssessmentResponseOut,
)
async def submit_assessment_response(
    response_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AssessmentResponseOut:
    """
    Submit a response for marking.
    """

    _ensure_marking_staff_access(
        current_user,
    )

    response = await submit_response(
        db=db,
        current_user=current_user,
        response_id=response_id,
    )

    return AssessmentResponseOut.model_validate(
        response,
    )


@router.post(
    "/responses/{response_id}/void",
    response_model=AssessmentResponseOut,
)
async def void_assessment_response(
    response_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AssessmentResponseOut:
    """
    Void a response so it does not contribute to marking.
    """

    _ensure_marking_staff_access(
        current_user,
    )

    response = await void_response(
        db=db,
        current_user=current_user,
        response_id=response_id,
    )

    return AssessmentResponseOut.model_validate(
        response,
    )


@router.delete(
    "/responses/{response_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_assessment_response(
    response_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    """
    Delete an untouched assessment response.
    """

    _ensure_marking_staff_access(
        current_user,
    )

    await delete_response(
        db=db,
        current_user=current_user,
        response_id=response_id,
    )

    return Response(
        status_code=status.HTTP_204_NO_CONTENT,
    )


# ---------------------------------------------------------------------------
# Marking decision creation
# ---------------------------------------------------------------------------


@router.post(
    "/responses/{response_id}/decision",
    response_model=MarkingDecisionOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_response_marking_decision(
    response_id: int,
    payload: MarkingDecisionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MarkingDecisionOut:
    """
    Start marking one submitted response.
    """

    _ensure_marking_staff_access(
        current_user,
    )

    decision = await create_marking_decision(
        db=db,
        current_user=current_user,
        response_id=response_id,
        marker_comment=payload.marker_comment,
    )

    return MarkingDecisionOut.model_validate(
        decision,
    )


# ---------------------------------------------------------------------------
# Examiner annotation routes
# ---------------------------------------------------------------------------


@router.get(
    "/responses/{response_id}/annotations",
    response_model=list[MarkingAnnotationOut],
)
async def get_response_marking_annotations(
    response_id: int,
    include_deleted: bool = Query(
        default=False,
    ),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[MarkingAnnotationOut]:
    """
    Return examiner annotations for one assessment response.

    Deleted annotations are hidden by default but may be included for
    authorised audit/review workflows.
    """

    _ensure_marking_staff_access(
        current_user,
    )

    annotations = await list_marking_annotations(
        db=db,
        current_user=current_user,
        response_id=response_id,
        include_deleted=include_deleted,
    )

    return [
        MarkingAnnotationOut.model_validate(
            annotation,
        )
        for annotation in annotations
    ]


@router.get(
    "/annotations/{annotation_id}",
    response_model=MarkingAnnotationOut,
)
async def get_response_marking_annotation(
    annotation_id: int,
    include_deleted: bool = Query(
        default=False,
    ),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MarkingAnnotationOut:
    """
    Return one examiner annotation.
    """

    _ensure_marking_staff_access(
        current_user,
    )

    annotation = await get_marking_annotation(
        db=db,
        current_user=current_user,
        annotation_id=annotation_id,
        include_deleted=include_deleted,
    )

    return MarkingAnnotationOut.model_validate(
        annotation,
    )


@router.post(
    "/responses/{response_id}/annotations",
    response_model=MarkingAnnotationOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_response_marking_annotation(
    response_id: int,
    payload: MarkingAnnotationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MarkingAnnotationOut:
    """
    Place one examiner annotation on a submitted response.
    """

    _ensure_marking_staff_access(
        current_user,
    )

    annotation = await create_marking_annotation(
        db=db,
        current_user=current_user,
        response_id=response_id,
        palette_tool_id=payload.palette_tool_id,
        x=payload.x,
        y=payload.y,
        surface_type=payload.surface_type,
        surface_reference=payload.surface_reference,
        page_number=payload.page_number,
        end_x=payload.end_x,
        end_y=payload.end_y,
        width=payload.width,
        height=payload.height,
        text=payload.text,
    )

    return MarkingAnnotationOut.model_validate(
        annotation,
    )


@router.patch(
    "/annotations/{annotation_id}",
    response_model=MarkingAnnotationOut,
)
async def update_response_marking_annotation(
    annotation_id: int,
    payload: MarkingAnnotationUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MarkingAnnotationOut:
    """
    Update mutable examiner annotation state using optimistic concurrency.
    """

    _ensure_marking_staff_access(
        current_user,
    )

    values = payload.model_dump(
        exclude_unset=True,
    )

    revision = values.pop(
        "revision",
    )

    annotation = await update_marking_annotation(
        db=db,
        current_user=current_user,
        annotation_id=annotation_id,
        revision=revision,
        **values,
    )

    return MarkingAnnotationOut.model_validate(
        annotation,
    )


@router.delete(
    "/annotations/{annotation_id}",
    response_model=MarkingAnnotationOut,
)
async def delete_response_marking_annotation(
    annotation_id: int,
    revision: int = Query(
        ...,
        gt=0,
    ),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MarkingAnnotationOut:
    """
    Soft-delete one examiner annotation using optimistic concurrency.

    The returned representation includes the new revision and deletion
    metadata so clients can reconcile local autosave state.
    """

    _ensure_marking_staff_access(
        current_user,
    )

    annotation = await delete_marking_annotation(
        db=db,
        current_user=current_user,
        annotation_id=annotation_id,
        revision=revision,
    )

    return MarkingAnnotationOut.model_validate(
        annotation,
    )


# ---------------------------------------------------------------------------
# Marking decision routes
# ---------------------------------------------------------------------------


@router.get(
    "/decisions/{decision_id}",
    response_model=MarkingDecisionOut,
)
async def get_response_marking_decision(
    decision_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MarkingDecisionOut:
    """
    Return one marking decision.
    """

    _ensure_marking_staff_access(
        current_user,
    )

    decision = await get_marking_decision(
        db=db,
        current_user=current_user,
        decision_id=decision_id,
    )

    return MarkingDecisionOut.model_validate(
        decision,
    )


@router.patch(
    "/decisions/{decision_id}",
    response_model=MarkingDecisionOut,
)
async def update_response_marking_decision(
    decision_id: int,
    payload: MarkingDecisionUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MarkingDecisionOut:
    """
    Update the authoritative question-level mark and marker comment.
    """

    _ensure_marking_staff_access(
        current_user,
    )

    decision = await update_marking_decision(
        db=db,
        current_user=current_user,
        decision_id=decision_id,
        mark_awarded=payload.mark_awarded,
        marker_comment=payload.marker_comment,
    )

    return MarkingDecisionOut.model_validate(
        decision,
    )


@router.post(
    "/decisions/{decision_id}/instant-mark",
    response_model=MarkingDecisionOut,
)
async def instant_mark_response_decision(
    decision_id: int,
    payload: InstantMarkRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MarkingDecisionOut:
    """
    Award a question-level mark and complete primary marking atomically.
    """

    _ensure_marking_staff_access(
        current_user,
    )

    decision = await instant_mark_decision(
        db=db,
        current_user=current_user,
        decision_id=decision_id,
        mark_awarded=payload.mark_awarded,
    )

    return MarkingDecisionOut.model_validate(
        decision,
    )


@router.patch(
    "/decisions/{decision_id}/status",
    response_model=MarkingDecisionOut,
)
async def update_marking_decision_status(
    decision_id: int,
    payload: MarkingDecisionStatusUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MarkingDecisionOut:
    """
    Move a marking decision through an allowed lifecycle transition.
    """

    _ensure_marking_staff_access(
        current_user,
    )

    decision = await transition_marking_decision_status(
        db=db,
        current_user=current_user,
        decision_id=decision_id,
        new_status=payload.status,
        moderation_comment=payload.moderation_comment,
    )

    return MarkingDecisionOut.model_validate(
        decision,
    )


@router.post(
    "/decisions/{decision_id}/start",
    response_model=MarkingDecisionOut,
)
async def start_response_marking(
    decision_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MarkingDecisionOut:
    """
    Move an unmarked decision into active marking.
    """

    _ensure_marking_staff_access(
        current_user,
    )

    decision = await start_marking(
        db=db,
        current_user=current_user,
        decision_id=decision_id,
    )

    return MarkingDecisionOut.model_validate(
        decision,
    )


@router.post(
    "/decisions/{decision_id}/complete",
    response_model=MarkingDecisionOut,
)
async def complete_response_marking(
    decision_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MarkingDecisionOut:
    """
    Complete primary marking.
    """

    _ensure_marking_staff_access(
        current_user,
    )

    decision = await complete_marking(
        db=db,
        current_user=current_user,
        decision_id=decision_id,
    )

    return MarkingDecisionOut.model_validate(
        decision,
    )


@router.post(
    "/decisions/{decision_id}/review",
    response_model=MarkingDecisionOut,
)
async def review_response_marking(
    decision_id: int,
    payload: MarkingReviewRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MarkingDecisionOut:
    """
    Review or moderate a completed marking decision.
    """

    _ensure_marking_staff_access(
        current_user,
    )

    decision = await review_marking(
        db=db,
        current_user=current_user,
        decision_id=decision_id,
        moderation_comment=payload.moderation_comment,
    )

    return MarkingDecisionOut.model_validate(
        decision,
    )


@router.post(
    "/decisions/{decision_id}/finalise",
    response_model=MarkingDecisionOut,
)
async def finalise_response_marking(
    decision_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MarkingDecisionOut:
    """
    Finalise a marked or reviewed decision.
    """

    _ensure_marking_staff_access(
        current_user,
    )

    decision = await finalise_marking(
        db=db,
        current_user=current_user,
        decision_id=decision_id,
    )

    return MarkingDecisionOut.model_validate(
        decision,
    )


@router.delete(
    "/decisions/{decision_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_response_marking_decision(
    decision_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    """
    Delete an untouched marking decision.
    """

    _ensure_marking_staff_access(
        current_user,
    )

    await delete_marking_decision(
        db=db,
        current_user=current_user,
        decision_id=decision_id,
    )

    return Response(
        status_code=status.HTTP_204_NO_CONTENT,
    )


# ---------------------------------------------------------------------------
# Criterion-level mark-scheme awards
# ---------------------------------------------------------------------------


@router.put(
    "/decisions/{decision_id}/awards",
    response_model=MarkSchemeItemAwardOut,
)
async def set_mark_scheme_item_award(
    decision_id: int,
    payload: MarkSchemeItemAwardCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MarkSchemeItemAwardOut:
    """
    Create or update one criterion-level mark-scheme item award.
    """

    _ensure_marking_staff_access(
        current_user,
    )

    award = await award_mark_scheme_item(
        db=db,
        current_user=current_user,
        decision_id=decision_id,
        mark_scheme_item_id=payload.mark_scheme_item_id,
        marks_awarded=payload.marks_awarded,
        marker_note=payload.marker_note,
    )

    return MarkSchemeItemAwardOut.model_validate(
        award,
    )


@router.delete(
    "/awards/{award_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_marking_award(
    award_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    """
    Delete a criterion-level award while the decision remains editable.
    """

    _ensure_marking_staff_access(
        current_user,
    )

    await delete_mark_scheme_item_award(
        db=db,
        current_user=current_user,
        award_id=award_id,
    )

    return Response(
        status_code=status.HTTP_204_NO_CONTENT,
    )
