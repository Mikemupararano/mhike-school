from __future__ import annotations

from fastapi import (
    APIRouter,
    Depends,
    status,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.permissions import PermissionService
from app.db.session import get_db
from app.models.user import User
from app.schemas.assessment_question_extraction import (
    AssessmentQuestionExtractionCreatedResponse,
    AssessmentQuestionExtractionHistoryResponse,
    AssessmentQuestionExtractionResponse,
    AssessmentQuestionExtractionSummaryResponse,
)
from app.services.assessment_question_extraction_service import (
    create_question_extraction,
    get_question_extraction,
    list_question_extractions_for_document,
)

router = APIRouter()


def _ensure_assessment_staff_access(
    current_user: User,
) -> None:
    """
    Ensure the current user may access assessment question extraction.

    Detailed school isolation, assessment ownership and question-paper
    document access are enforced by the service layer.
    """

    PermissionService.ensure_active_user(
        current_user,
    )

    PermissionService.ensure_school_staff_or_platform_admin(
        current_user,
    )


@router.post(
    "/{assessment_id}/documents/{document_id}/question-extractions",
    response_model=AssessmentQuestionExtractionCreatedResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_assessment_question_extraction(
    assessment_id: int,
    document_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AssessmentQuestionExtractionCreatedResponse:
    """
    Extract a question paper into a reviewable question proposal.

    Extraction:

    - reads the source PDF;
    - retains page-level evidence;
    - detects question and mark candidates;
    - stores a versioned proposal;
    - never creates canonical AssessmentQuestion records automatically.

    The returned proposal therefore always remains subject to explicit review
    and later import.
    """

    _ensure_assessment_staff_access(
        current_user,
    )

    extraction = await create_question_extraction(
        db=db,
        current_user=current_user,
        assessment_id=assessment_id,
        document_id=document_id,
    )

    response = AssessmentQuestionExtractionCreatedResponse.model_validate(
        extraction,
    )

    return response.model_copy(
        update={
            "message": "Question-paper extraction completed.",
        }
    )


@router.get(
    "/{assessment_id}/question-extractions/{extraction_id}",
    response_model=AssessmentQuestionExtractionResponse,
)
async def get_assessment_question_extraction(
    assessment_id: int,
    extraction_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AssessmentQuestionExtractionResponse:
    """
    Return one full question extraction proposal.

    The full response contains the retained page evidence and review proposal
    required by the future extraction-review workspace.
    """

    _ensure_assessment_staff_access(
        current_user,
    )

    extraction = await get_question_extraction(
        db=db,
        current_user=current_user,
        assessment_id=assessment_id,
        extraction_id=extraction_id,
    )

    return AssessmentQuestionExtractionResponse.model_validate(
        extraction,
    )


@router.get(
    "/{assessment_id}/documents/{document_id}/question-extractions",
    response_model=AssessmentQuestionExtractionHistoryResponse,
)
async def get_assessment_question_extraction_history(
    assessment_id: int,
    document_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AssessmentQuestionExtractionHistoryResponse:
    """
    Return extraction history for one question-paper document.

    History responses deliberately omit the potentially large page text and
    proposal JSON. Clients can retrieve a specific extraction separately when
    the full review data is required.
    """

    _ensure_assessment_staff_access(
        current_user,
    )

    extractions = await list_question_extractions_for_document(
        db=db,
        current_user=current_user,
        assessment_id=assessment_id,
        document_id=document_id,
    )

    return AssessmentQuestionExtractionHistoryResponse(
        assessment_id=assessment_id,
        assessment_document_id=document_id,
        extractions=[
            AssessmentQuestionExtractionSummaryResponse.model_validate(
                extraction,
            )
            for extraction in extractions
        ],
    )
