from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.assessment_taking import (
    AssessmentTakingResponseOut,
    AssessmentTakingResponseSave,
    StudentAssessmentAttemptOut,
    StudentAssessmentStartOut,
    StudentAssessmentSubmitOut,
    StudentAssessmentSummaryOut,
)
from app.services.assessment_taking_service import (
    get_student_assessment_attempt,
    list_student_assessments,
    resolve_student_assessment_asset_path,
    save_student_assessment_response,
    start_student_assessment,
    submit_student_assessment,
)


router = APIRouter()


@router.get(
    "",
    response_model=list[StudentAssessmentSummaryOut],
)
async def get_student_assessments(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[StudentAssessmentSummaryOut]:
    return await list_student_assessments(
        db=db,
        current_user=current_user,
    )


@router.get(
    "/{assessment_id}",
    response_model=StudentAssessmentSummaryOut,
)
async def get_student_assessment(
    assessment_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> StudentAssessmentSummaryOut:
    assessments = await list_student_assessments(
        db=db,
        current_user=current_user,
    )

    for assessment in assessments:
        if assessment.assessment_id == assessment_id:
            return assessment

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Student assessment allocation not found.",
    )


@router.post(
    "/{assessment_id}/start",
    response_model=StudentAssessmentStartOut,
)
async def start_student_assessment_attempt(
    assessment_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> StudentAssessmentStartOut:
    return await start_student_assessment(
        db=db,
        current_user=current_user,
        assessment_id=assessment_id,
    )


@router.get(
    "/{assessment_id}/attempt",
    response_model=StudentAssessmentAttemptOut,
)
async def get_student_assessment_attempt_endpoint(
    assessment_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> StudentAssessmentAttemptOut:
    return await get_student_assessment_attempt(
        db=db,
        current_user=current_user,
        assessment_id=assessment_id,
    )


@router.get(
    "/{assessment_id}/questions/{question_id}/assets/{asset_id}/content",
    response_class=FileResponse,
)
async def get_student_assessment_question_asset_content(
    assessment_id: int,
    question_id: int,
    asset_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FileResponse:
    asset_path, mime_type, download_name = (
        await resolve_student_assessment_asset_path(
            db=db,
            current_user=current_user,
            assessment_id=assessment_id,
            question_id=question_id,
            asset_id=asset_id,
        )
    )

    return FileResponse(
        path=asset_path,
        media_type=mime_type,
        filename=download_name,
    )


@router.put(
    "/{assessment_id}/responses/{question_id}",
    response_model=AssessmentTakingResponseOut,
)
async def save_student_assessment_response_endpoint(
    assessment_id: int,
    question_id: int,
    payload: AssessmentTakingResponseSave,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AssessmentTakingResponseOut:
    return await save_student_assessment_response(
        db=db,
        current_user=current_user,
        assessment_id=assessment_id,
        question_id=question_id,
        payload=payload,
    )


@router.post(
    "/{assessment_id}/submit",
    response_model=StudentAssessmentSubmitOut,
)
async def submit_student_assessment_attempt(
    assessment_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> StudentAssessmentSubmitOut:
    return await submit_student_assessment(
        db=db,
        current_user=current_user,
        assessment_id=assessment_id,
    )
