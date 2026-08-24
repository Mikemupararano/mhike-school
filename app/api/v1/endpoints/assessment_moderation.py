from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.assessment_moderation import (
    AssessmentModerationOutcome,
    AssessmentModerationReviewStatus,
)
from app.models.user import User
from app.schemas.assessment_moderation import (
    AssessmentModerationItemCreate,
    AssessmentModerationItemRead,
    AssessmentModerationReviewCancel,
    AssessmentModerationReviewComplete,
    AssessmentModerationReviewCreate,
    AssessmentModerationReviewList,
    AssessmentModerationReviewRead,
    AssessmentModerationReviewSummary,
)
from app.services.assessment_moderation_service import (
    add_moderation_item,
    cancel_moderation_review,
    complete_moderation_review,
    create_moderation_review,
    get_moderation_review,
    list_assessment_moderation_reviews,
    list_script_moderation_reviews,
    start_moderation_review,
)

router = APIRouter(
    prefix="/assessment-moderation",
    tags=["assessment-moderation"],
)


# ----------------------------------------------------------------------
# Review creation
# ----------------------------------------------------------------------


@router.post(
    "/scripts/{script_id}/reviews",
    response_model=AssessmentModerationReviewRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_review(
    script_id: int,
    payload: AssessmentModerationReviewCreate,
    db: AsyncSession = Depends(
        get_db,
    ),
    current_user: User = Depends(
        get_current_user,
    ),
) -> AssessmentModerationReviewRead:
    """
    Create a moderation review for an assessment script.

    The service validates:

    - moderation authority;
    - school scope;
    - script/candidate/assessment consistency;
    - script lifecycle;
    - moderator eligibility.

    A MARKED script enters MODERATION when appropriate. A FINALISED script
    may receive a later moderation review without silently reopening its
    existing official result.
    """

    review = await create_moderation_review(
        db,
        current_user,
        script_id,
        moderator_id=payload.moderator_id,
        sampling_method=payload.sampling_method,
        reason=payload.reason,
        notes=payload.notes,
        sample_description=payload.sample_description,
    )

    return AssessmentModerationReviewRead.model_validate(
        review,
    )


# ----------------------------------------------------------------------
# Review retrieval
# ----------------------------------------------------------------------


@router.get(
    "/reviews/{review_id}",
    response_model=AssessmentModerationReviewRead,
)
async def get_review(
    review_id: int,
    db: AsyncSession = Depends(
        get_db,
    ),
    current_user: User = Depends(
        get_current_user,
    ),
) -> AssessmentModerationReviewRead:
    """
    Return one moderation review with its immutable item evidence.
    """

    review = await get_moderation_review(
        db,
        current_user,
        review_id,
    )

    return AssessmentModerationReviewRead.model_validate(
        review,
    )


@router.get(
    "/scripts/{script_id}/reviews",
    response_model=AssessmentModerationReviewList,
)
async def list_reviews_for_script(
    script_id: int,
    db: AsyncSession = Depends(
        get_db,
    ),
    current_user: User = Depends(
        get_current_user,
    ),
) -> AssessmentModerationReviewList:
    """
    Return moderation history for one script.
    """

    reviews = await list_script_moderation_reviews(
        db,
        current_user,
        script_id,
    )

    items = [
        AssessmentModerationReviewSummary.model_validate(
            review,
        )
        for review in reviews
    ]

    return AssessmentModerationReviewList(
        items=items,
        total=len(items),
    )


@router.get(
    "/assessments/{assessment_id}/reviews",
    response_model=AssessmentModerationReviewList,
)
async def list_reviews_for_assessment(
    assessment_id: int,
    review_status: AssessmentModerationReviewStatus | None = Query(
        default=None,
        alias="status",
    ),
    outcome: AssessmentModerationOutcome | None = Query(
        default=None,
    ),
    db: AsyncSession = Depends(
        get_db,
    ),
    current_user: User = Depends(
        get_current_user,
    ),
) -> AssessmentModerationReviewList:
    """
    Return moderation reviews belonging to one assessment.

    Optional ``status`` and ``outcome`` query parameters allow moderation
    queues and completed-review history to be filtered without exposing
    repository implementation details.
    """

    reviews = await list_assessment_moderation_reviews(
        db,
        current_user,
        assessment_id,
        review_status=review_status,
        outcome=outcome,
    )

    items = [
        AssessmentModerationReviewSummary.model_validate(
            review,
        )
        for review in reviews
    ]

    return AssessmentModerationReviewList(
        items=items,
        total=len(items),
    )


# ----------------------------------------------------------------------
# Review lifecycle
# ----------------------------------------------------------------------


@router.post(
    "/reviews/{review_id}/start",
    response_model=AssessmentModerationReviewRead,
)
async def start_review(
    review_id: int,
    db: AsyncSession = Depends(
        get_db,
    ),
    current_user: User = Depends(
        get_current_user,
    ),
) -> AssessmentModerationReviewRead:
    """
    Start a pending moderation review.
    """

    review = await start_moderation_review(
        db,
        current_user,
        review_id,
    )

    return AssessmentModerationReviewRead.model_validate(
        review,
    )


@router.post(
    "/reviews/{review_id}/complete",
    response_model=AssessmentModerationReviewRead,
)
async def complete_review(
    review_id: int,
    payload: AssessmentModerationReviewComplete,
    db: AsyncSession = Depends(
        get_db,
    ),
    current_user: User = Depends(
        get_current_user,
    ),
) -> AssessmentModerationReviewRead:
    """
    Complete an active moderation review.

    CONFIRMED, ADJUSTED and NO_ACTION may complete the operational moderation
    path. RETURNED and ESCALATED leave the script available for further
    moderation action.

    This endpoint does not create or replace an authoritative result outcome.
    """

    review = await complete_moderation_review(
        db,
        current_user,
        review_id,
        outcome=payload.outcome,
        notes=payload.notes,
    )

    return AssessmentModerationReviewRead.model_validate(
        review,
    )


@router.post(
    "/reviews/{review_id}/cancel",
    response_model=AssessmentModerationReviewRead,
)
async def cancel_review(
    review_id: int,
    payload: AssessmentModerationReviewCancel,
    db: AsyncSession = Depends(
        get_db,
    ),
    current_user: User = Depends(
        get_current_user,
    ),
) -> AssessmentModerationReviewRead:
    """
    Cancel a pending or active moderation review.

    Cancellation preserves the review and any evidence already recorded.
    """

    review = await cancel_moderation_review(
        db,
        current_user,
        review_id,
        cancellation_reason=payload.cancellation_reason,
    )

    return AssessmentModerationReviewRead.model_validate(
        review,
    )


# ----------------------------------------------------------------------
# Moderation items
# ----------------------------------------------------------------------


@router.post(
    "/reviews/{review_id}/items",
    response_model=AssessmentModerationItemRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_review_item(
    review_id: int,
    payload: AssessmentModerationItemCreate,
    db: AsyncSession = Depends(
        get_db,
    ),
    current_user: User = Depends(
        get_current_user,
    ),
) -> AssessmentModerationItemRead:
    """
    Record moderation evidence for one response.

    Snapshot and audit fields are derived server-side and cannot be supplied
    by the client.

    An ADJUSTED item may alter the current operational MarkingDecision, but it
    does not silently change an authoritative AssessmentResultOutcome.
    """

    item = await add_moderation_item(
        db,
        current_user,
        review_id,
        response_id=payload.response_id,
        marking_decision_id=payload.marking_decision_id,
        expected_revision=payload.expected_revision,
        outcome=payload.outcome,
        mark_after=payload.mark_after,
        moderator_comment=payload.moderator_comment,
        evidence_notes=payload.evidence_notes,
    )

    return AssessmentModerationItemRead.model_validate(
        item,
    )
