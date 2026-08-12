from __future__ import annotations

from fastapi import (
    APIRouter,
    Depends,
    Response,
    status,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.assessment_result_publication import (
    AssessmentPublishedResultVisibilityOut,
    AssessmentResultPublicationApprovalRequest,
    AssessmentResultPublicationCreate,
    AssessmentResultPublicationOut,
    AssessmentResultPublicationScheduleRequest,
    AssessmentResultPublicationUpdate,
    AssessmentResultPublicationWithdrawRequest,
)
from app.services.assessment_result_publication_service import (
    approve_result_publication,
    create_result_publication,
    delete_result_publication,
    get_published_result_visibility,
    get_result_publication,
    publish_results,
    revoke_result_publication_approval,
    schedule_results_publication,
    update_result_publication,
    withdraw_results,
)

router = APIRouter()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _publication_update_kwargs(
    payload: AssessmentResultPublicationUpdate,
) -> dict[str, object]:
    """
    Build service keyword arguments while preserving explicitly supplied
    null values.

    This is particularly important for ``release_message`` because:

        {}

    means leave the existing message unchanged, while:

        {"release_message": null}

    means clear it.
    """

    output: dict[str, object] = {}

    if "requires_approval" in payload.model_fields_set:
        output["requires_approval"] = payload.requires_approval

    if "visible_to_students" in payload.model_fields_set:
        output["visible_to_students"] = payload.visible_to_students

    if "visible_to_parents" in payload.model_fields_set:
        output["visible_to_parents"] = payload.visible_to_parents

    if "include_mark" in payload.model_fields_set:
        output["include_mark"] = payload.include_mark

    if "include_percentage" in payload.model_fields_set:
        output["include_percentage"] = payload.include_percentage

    if "include_grade" in payload.model_fields_set:
        output["include_grade"] = payload.include_grade

    if "include_question_breakdown" in payload.model_fields_set:
        output["include_question_breakdown"] = payload.include_question_breakdown

    if "release_message" in payload.model_fields_set:
        output["release_message"] = payload.release_message

    return output


# ---------------------------------------------------------------------------
# Publication configuration
# ---------------------------------------------------------------------------


@router.post(
    "/assessments/{assessment_id}",
    response_model=AssessmentResultPublicationOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_assessment_result_publication(
    assessment_id: int,
    payload: AssessmentResultPublicationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AssessmentResultPublicationOut:
    """
    Create result-publication configuration for an assessment.

    Ordinary classroom assessments default to ``requires_approval=False``.

    The assessment's course teacher may therefore configure and later
    publish their own end-of-topic test results without waiting for SMT.

    Detailed assessment ownership and school isolation are enforced by the
    publication service through the existing assessment-results access
    policy.
    """

    publication = await create_result_publication(
        db=db,
        current_user=current_user,
        assessment_id=assessment_id,
        requires_approval=payload.requires_approval,
        visible_to_students=payload.visible_to_students,
        visible_to_parents=payload.visible_to_parents,
        include_mark=payload.include_mark,
        include_percentage=payload.include_percentage,
        include_grade=payload.include_grade,
        include_question_breakdown=payload.include_question_breakdown,
        release_message=payload.release_message,
    )

    return AssessmentResultPublicationOut.model_validate(
        publication,
    )


@router.get(
    "/assessments/{assessment_id}",
    response_model=AssessmentResultPublicationOut,
)
async def get_assessment_result_publication(
    assessment_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AssessmentResultPublicationOut:
    """
    Return result-publication configuration for an assessment.
    """

    publication = await get_result_publication(
        db=db,
        current_user=current_user,
        assessment_id=assessment_id,
    )

    return AssessmentResultPublicationOut.model_validate(
        publication,
    )


@router.patch(
    "/publications/{publication_id}",
    response_model=AssessmentResultPublicationOut,
)
async def update_assessment_result_publication(
    publication_id: int,
    payload: AssessmentResultPublicationUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AssessmentResultPublicationOut:
    """
    Update result-publication settings.

    Explicit null values are preserved so nullable configuration such as
    ``release_message`` can be cleared.
    """

    publication = await update_result_publication(
        db=db,
        current_user=current_user,
        publication_id=publication_id,
        **_publication_update_kwargs(payload),
    )

    return AssessmentResultPublicationOut.model_validate(
        publication,
    )


@router.delete(
    "/publications/{publication_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_assessment_result_publication(
    publication_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    """
    Delete result-publication configuration.

    Published releases must first be withdrawn so their release history is
    not silently removed.
    """

    await delete_result_publication(
        db=db,
        current_user=current_user,
        publication_id=publication_id,
    )

    return Response(
        status_code=status.HTTP_204_NO_CONTENT,
    )


# ---------------------------------------------------------------------------
# Controlled-assessment approval
# ---------------------------------------------------------------------------


@router.post(
    "/publications/{publication_id}/approve",
    response_model=AssessmentResultPublicationOut,
)
async def approve_assessment_result_publication(
    publication_id: int,
    payload: AssessmentResultPublicationApprovalRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AssessmentResultPublicationOut:
    """
    Approve a controlled assessment result release.

    This endpoint is not part of the normal end-of-topic test workflow.
    Approval is required only when ``requires_approval=True``.

    The service restricts approval to School Admin, SMT or Platform Admin.
    """

    publication = await approve_result_publication(
        db=db,
        current_user=current_user,
        publication_id=publication_id,
        approval_note=payload.approval_note,
    )

    return AssessmentResultPublicationOut.model_validate(
        publication,
    )


@router.post(
    "/publications/{publication_id}/revoke-approval",
    response_model=AssessmentResultPublicationOut,
)
async def revoke_assessment_result_publication_approval(
    publication_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AssessmentResultPublicationOut:
    """
    Revoke controlled-result approval before publication.
    """

    publication = await revoke_result_publication_approval(
        db=db,
        current_user=current_user,
        publication_id=publication_id,
    )

    return AssessmentResultPublicationOut.model_validate(
        publication,
    )


# ---------------------------------------------------------------------------
# Immediate publication
# ---------------------------------------------------------------------------


@router.post(
    "/publications/{publication_id}/publish",
    response_model=AssessmentResultPublicationOut,
)
async def publish_assessment_results(
    publication_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AssessmentResultPublicationOut:
    """
    Publish assessment results immediately.

    For an ordinary assessment with ``requires_approval=False``, the owning
    course teacher may publish directly once all expected marks are
    finalised.

    No SMT approval step is imposed on normal classroom assessment results.
    """

    publication = await publish_results(
        db=db,
        current_user=current_user,
        publication_id=publication_id,
    )

    return AssessmentResultPublicationOut.model_validate(
        publication,
    )


# ---------------------------------------------------------------------------
# Scheduled publication
# ---------------------------------------------------------------------------


@router.post(
    "/publications/{publication_id}/schedule",
    response_model=AssessmentResultPublicationOut,
)
async def schedule_assessment_results(
    publication_id: int,
    payload: AssessmentResultPublicationScheduleRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AssessmentResultPublicationOut:
    """
    Schedule fully marked assessment results for future release.
    """

    publication = await schedule_results_publication(
        db=db,
        current_user=current_user,
        publication_id=publication_id,
        scheduled_for=payload.scheduled_for,
    )

    return AssessmentResultPublicationOut.model_validate(
        publication,
    )


# ---------------------------------------------------------------------------
# Withdrawal
# ---------------------------------------------------------------------------


@router.post(
    "/publications/{publication_id}/withdraw",
    response_model=AssessmentResultPublicationOut,
)
async def withdraw_assessment_results(
    publication_id: int,
    payload: AssessmentResultPublicationWithdrawRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AssessmentResultPublicationOut:
    """
    Withdraw a published or scheduled result release.

    The owning teacher may withdraw their own ordinary assessment release.
    """

    publication = await withdraw_results(
        db=db,
        current_user=current_user,
        publication_id=publication_id,
        withdrawal_reason=payload.withdrawal_reason,
    )

    return AssessmentResultPublicationOut.model_validate(
        publication,
    )


# ---------------------------------------------------------------------------
# Published visibility metadata
# ---------------------------------------------------------------------------


@router.get(
    "/assessments/{assessment_id}/published-visibility",
    response_model=AssessmentPublishedResultVisibilityOut | None,
)
async def get_assessment_published_visibility(
    assessment_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AssessmentPublishedResultVisibilityOut | None:
    """
    Return active publication visibility configuration.

    This staff-facing endpoint is useful for administration and diagnostics.

    Student and parent result endpoints will perform their own candidate or
    parent-child checks before exposing any actual marks, percentages,
    grades or question-level details.
    """

    # First enforce normal staff access to the assessment.
    await get_result_publication(
        db=db,
        current_user=current_user,
        assessment_id=assessment_id,
    )

    publication = await get_published_result_visibility(
        db,
        assessment_id=assessment_id,
    )

    if publication is None:
        return None

    return AssessmentPublishedResultVisibilityOut(
        assessment_id=publication.assessment_id,
        status=publication.status,
        visible_to_students=publication.visible_to_students,
        visible_to_parents=publication.visible_to_parents,
        include_mark=publication.include_mark,
        include_percentage=publication.include_percentage,
        include_grade=publication.include_grade,
        include_question_breakdown=(publication.include_question_breakdown),
        release_message=publication.release_message,
        published_at=publication.published_at,
    )
