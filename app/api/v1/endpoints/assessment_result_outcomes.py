from __future__ import annotations

from typing import Any

from fastapi import (
    APIRouter,
    Depends,
    Response,
    status,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    get_current_user,
    get_db,
)
from app.models.user import User
from app.schemas.assessment_result_outcome import (
    AssessmentResultOutcomeCreate,
    AssessmentResultOutcomeHistoryOut,
    AssessmentResultOutcomeOut,
    AssessmentResultOutcomeUpdate,
    AssessmentResultOutcomeWithdraw,
)
from app.services.assessment_result_outcome_service import (
    authorise_assessment_result_outcome,
    create_assessment_result_outcome,
    delete_assessment_result_outcome_draft,
    get_assessment_result_outcome,
    get_authoritative_assessment_result_outcome,
    list_assessment_result_outcome_history,
    update_assessment_result_outcome_draft,
    withdraw_assessment_result_outcome,
)

router = APIRouter()


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------


@router.post(
    "",
    response_model=AssessmentResultOutcomeOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_result_outcome(
    payload: AssessmentResultOutcomeCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AssessmentResultOutcomeOut:
    """
    Capture a new result snapshot.

    The snapshot may remain in draft or become authoritative immediately.
    """

    result = await create_assessment_result_outcome(
        db,
        current_user,
        script_id=payload.script_id,
        change_type=payload.change_type,
        reason=payload.reason,
        notes=payload.notes,
        effective_at=payload.effective_at,
        make_authoritative=payload.make_authoritative,
    )

    return AssessmentResultOutcomeOut.model_validate(
        result,
    )


# ---------------------------------------------------------------------------
# Single-outcome read
# ---------------------------------------------------------------------------


@router.get(
    "/{outcome_id}",
    response_model=AssessmentResultOutcomeOut,
)
async def get_result_outcome(
    outcome_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AssessmentResultOutcomeOut:
    """
    Return one authorised historical result outcome.
    """

    result = await get_assessment_result_outcome(
        db,
        current_user,
        outcome_id=outcome_id,
    )

    return AssessmentResultOutcomeOut.model_validate(
        result,
    )


# ---------------------------------------------------------------------------
# Candidate authoritative result
# ---------------------------------------------------------------------------


@router.get(
    "/candidates/{candidate_id}/authoritative",
    response_model=AssessmentResultOutcomeOut,
)
async def get_authoritative_result_outcome(
    candidate_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AssessmentResultOutcomeOut:
    """
    Return the candidate's current authoritative result outcome.
    """

    result = await get_authoritative_assessment_result_outcome(
        db,
        current_user,
        candidate_id=candidate_id,
    )

    return AssessmentResultOutcomeOut.model_validate(
        result,
    )


# ---------------------------------------------------------------------------
# Candidate history
# ---------------------------------------------------------------------------


@router.get(
    "/candidates/{candidate_id}/history",
    response_model=AssessmentResultOutcomeHistoryOut,
)
async def get_result_outcome_history(
    candidate_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AssessmentResultOutcomeHistoryOut:
    """
    Return the candidate's complete result outcome history.
    """

    outcomes = await list_assessment_result_outcome_history(
        db,
        current_user,
        candidate_id=candidate_id,
    )

    authoritative_outcome_id = next(
        (
            int(
                outcome["id"],
            )
            for outcome in outcomes
            if outcome.get(
                "is_authoritative",
                False,
            )
        ),
        None,
    )

    payload = {
        "candidate_id": candidate_id,
        "outcome_count": len(
            outcomes,
        ),
        "authoritative_outcome_id": authoritative_outcome_id,
        "outcomes": outcomes,
    }

    return AssessmentResultOutcomeHistoryOut.model_validate(
        payload,
    )


# ---------------------------------------------------------------------------
# Draft metadata PATCH
# ---------------------------------------------------------------------------


@router.patch(
    "/{outcome_id}",
    response_model=AssessmentResultOutcomeOut,
)
async def update_result_outcome_draft(
    outcome_id: int,
    payload: AssessmentResultOutcomeUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AssessmentResultOutcomeOut:
    """
    Partially update metadata on a draft result outcome.

    Snapshot fields are never client-editable.
    """

    update_values: dict[str, Any] = payload.model_dump(
        exclude_unset=True,
    )

    result = await update_assessment_result_outcome_draft(
        db,
        current_user,
        outcome_id=outcome_id,
        **update_values,
    )

    return AssessmentResultOutcomeOut.model_validate(
        result,
    )


# ---------------------------------------------------------------------------
# Authorise existing draft
# ---------------------------------------------------------------------------


@router.post(
    "/{outcome_id}/authorise",
    response_model=AssessmentResultOutcomeOut,
)
async def authorise_result_outcome(
    outcome_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AssessmentResultOutcomeOut:
    """
    Promote the latest draft result outcome to authoritative.
    """

    result = await authorise_assessment_result_outcome(
        db,
        current_user,
        outcome_id=outcome_id,
    )

    return AssessmentResultOutcomeOut.model_validate(
        result,
    )


# ---------------------------------------------------------------------------
# Withdraw
# ---------------------------------------------------------------------------


@router.post(
    "/{outcome_id}/withdraw",
    response_model=AssessmentResultOutcomeOut,
)
async def withdraw_result_outcome(
    outcome_id: int,
    payload: AssessmentResultOutcomeWithdraw,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AssessmentResultOutcomeOut:
    """
    Withdraw a historical outcome while preserving its snapshot.
    """

    result = await withdraw_assessment_result_outcome(
        db,
        current_user,
        outcome_id=outcome_id,
        withdrawal_reason=payload.withdrawal_reason,
    )

    return AssessmentResultOutcomeOut.model_validate(
        result,
    )


# ---------------------------------------------------------------------------
# Delete draft
# ---------------------------------------------------------------------------


@router.delete(
    "/{outcome_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_result_outcome_draft(
    outcome_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    """
    Delete a draft that has never become authoritative.

    Historical official outcomes cannot be deleted.
    """

    await delete_assessment_result_outcome_draft(
        db,
        current_user,
        outcome_id=outcome_id,
    )

    return Response(
        status_code=status.HTTP_204_NO_CONTENT,
    )
