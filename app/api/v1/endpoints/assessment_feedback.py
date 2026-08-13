from __future__ import annotations

from typing import Any

from fastapi import (
    APIRouter,
    Depends,
    Query,
    Response,
    status,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    get_current_user,
    get_db,
)
from app.models.user import User
from app.schemas.assessment_feedback import (
    AssessmentFeedbackCreate,
    AssessmentFeedbackOut,
    AssessmentFeedbackUpdate,
    AssessmentFeedbackWorkflowOut,
    AssessmentQuestionFeedbackCreate,
    AssessmentQuestionFeedbackOut,
    AssessmentQuestionFeedbackUpdate,
)
from app.services.assessment_feedback_service import (
    create_assessment_feedback,
    create_assessment_question_feedback,
    delete_assessment_feedback,
    delete_assessment_question_feedback,
    finalise_assessment_feedback,
    get_assessment_feedback,
    get_assessment_feedback_for_script,
    get_assessment_question_feedback,
    get_assessment_question_feedback_for_response,
    reopen_assessment_feedback,
    update_assessment_feedback,
    update_assessment_question_feedback,
)

router = APIRouter()


# ---------------------------------------------------------------------------
# Overall feedback
# ---------------------------------------------------------------------------


@router.post(
    "",
    response_model=AssessmentFeedbackOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_feedback(
    payload: AssessmentFeedbackCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AssessmentFeedbackOut:
    """
    Create overall structured feedback for one assessment script.
    """

    result = await create_assessment_feedback(
        db,
        current_user,
        school_id=payload.school_id,
        script_id=payload.script_id,
        overall_comment=payload.overall_comment,
        strengths=payload.strengths,
        areas_for_improvement=payload.areas_for_improvement,
        next_steps=payload.next_steps,
        include_with_result=payload.include_with_result,
    )

    return AssessmentFeedbackOut.model_validate(
        result,
    )


@router.get(
    "/{feedback_id}",
    response_model=AssessmentFeedbackOut,
)
async def get_feedback(
    feedback_id: int,
    school_id: int | None = Query(
        default=None,
        ge=1,
    ),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AssessmentFeedbackOut:
    """
    Return one authorised overall feedback record.
    """

    result = await get_assessment_feedback(
        db,
        current_user,
        feedback_id=feedback_id,
        school_id=school_id,
    )

    return AssessmentFeedbackOut.model_validate(
        result,
    )


@router.get(
    "/scripts/{script_id}",
    response_model=AssessmentFeedbackOut,
)
async def get_feedback_for_script(
    script_id: int,
    school_id: int | None = Query(
        default=None,
        ge=1,
    ),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AssessmentFeedbackOut:
    """
    Return overall feedback for one authorised script.
    """

    result = await get_assessment_feedback_for_script(
        db,
        current_user,
        script_id=script_id,
        school_id=school_id,
    )

    return AssessmentFeedbackOut.model_validate(
        result,
    )


@router.patch(
    "/{feedback_id}",
    response_model=AssessmentFeedbackOut,
)
async def update_feedback(
    feedback_id: int,
    payload: AssessmentFeedbackUpdate,
    school_id: int | None = Query(
        default=None,
        ge=1,
    ),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AssessmentFeedbackOut:
    """
    Partially update overall feedback.

    Only explicitly supplied fields are forwarded so JSON null may be used
    to clear nullable feedback fields.
    """

    update_values: dict[str, Any] = payload.model_dump(
        exclude_unset=True,
    )

    result = await update_assessment_feedback(
        db,
        current_user,
        feedback_id=feedback_id,
        school_id=school_id,
        **update_values,
    )

    return AssessmentFeedbackOut.model_validate(
        result,
    )


@router.post(
    "/{feedback_id}/finalise",
    response_model=AssessmentFeedbackWorkflowOut,
)
async def finalise_feedback(
    feedback_id: int,
    school_id: int | None = Query(
        default=None,
        ge=1,
    ),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AssessmentFeedbackWorkflowOut:
    """
    Finalise overall assessment feedback.
    """

    result = await finalise_assessment_feedback(
        db,
        current_user,
        feedback_id=feedback_id,
        school_id=school_id,
    )

    return AssessmentFeedbackWorkflowOut.model_validate(
        result,
    )


@router.post(
    "/{feedback_id}/reopen",
    response_model=AssessmentFeedbackWorkflowOut,
)
async def reopen_feedback(
    feedback_id: int,
    school_id: int | None = Query(
        default=None,
        ge=1,
    ),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AssessmentFeedbackWorkflowOut:
    """
    Return finalised feedback to draft status.
    """

    result = await reopen_assessment_feedback(
        db,
        current_user,
        feedback_id=feedback_id,
        school_id=school_id,
    )

    return AssessmentFeedbackWorkflowOut.model_validate(
        result,
    )


@router.delete(
    "/{feedback_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_feedback(
    feedback_id: int,
    school_id: int | None = Query(
        default=None,
        ge=1,
    ),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    """
    Delete one authorised non-finalised overall feedback record.
    """

    await delete_assessment_feedback(
        db,
        current_user,
        feedback_id=feedback_id,
        school_id=school_id,
    )

    return Response(
        status_code=status.HTTP_204_NO_CONTENT,
    )


# ---------------------------------------------------------------------------
# Question feedback
# ---------------------------------------------------------------------------


@router.post(
    "/questions",
    response_model=AssessmentQuestionFeedbackOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_question_feedback(
    payload: AssessmentQuestionFeedbackCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AssessmentQuestionFeedbackOut:
    """
    Create feedback for one assessment response.
    """

    result = await create_assessment_question_feedback(
        db,
        current_user,
        school_id=payload.school_id,
        response_id=payload.response_id,
        feedback_text=payload.feedback_text,
        strength=payload.strength,
        improvement=payload.improvement,
        include_with_result=payload.include_with_result,
    )

    return AssessmentQuestionFeedbackOut.model_validate(
        result,
    )


@router.get(
    "/questions/{question_feedback_id}",
    response_model=AssessmentQuestionFeedbackOut,
)
async def get_question_feedback(
    question_feedback_id: int,
    school_id: int | None = Query(
        default=None,
        ge=1,
    ),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AssessmentQuestionFeedbackOut:
    """
    Return one authorised question-feedback record.
    """

    result = await get_assessment_question_feedback(
        db,
        current_user,
        question_feedback_id=question_feedback_id,
        school_id=school_id,
    )

    return AssessmentQuestionFeedbackOut.model_validate(
        result,
    )


@router.get(
    "/responses/{response_id}/question-feedback",
    response_model=AssessmentQuestionFeedbackOut,
)
async def get_question_feedback_for_response(
    response_id: int,
    school_id: int | None = Query(
        default=None,
        ge=1,
    ),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AssessmentQuestionFeedbackOut:
    """
    Return question feedback for one authorised assessment response.
    """

    result = await get_assessment_question_feedback_for_response(
        db,
        current_user,
        response_id=response_id,
        school_id=school_id,
    )

    return AssessmentQuestionFeedbackOut.model_validate(
        result,
    )


@router.patch(
    "/questions/{question_feedback_id}",
    response_model=AssessmentQuestionFeedbackOut,
)
async def update_question_feedback(
    question_feedback_id: int,
    payload: AssessmentQuestionFeedbackUpdate,
    school_id: int | None = Query(
        default=None,
        ge=1,
    ),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AssessmentQuestionFeedbackOut:
    """
    Partially update question-specific feedback.
    """

    update_values: dict[str, Any] = payload.model_dump(
        exclude_unset=True,
    )

    result = await update_assessment_question_feedback(
        db,
        current_user,
        question_feedback_id=question_feedback_id,
        school_id=school_id,
        **update_values,
    )

    return AssessmentQuestionFeedbackOut.model_validate(
        result,
    )


@router.delete(
    "/questions/{question_feedback_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_question_feedback(
    question_feedback_id: int,
    school_id: int | None = Query(
        default=None,
        ge=1,
    ),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    """
    Delete one authorised question-feedback record.
    """

    await delete_assessment_question_feedback(
        db,
        current_user,
        question_feedback_id=question_feedback_id,
        school_id=school_id,
    )

    return Response(
        status_code=status.HTTP_204_NO_CONTENT,
    )
