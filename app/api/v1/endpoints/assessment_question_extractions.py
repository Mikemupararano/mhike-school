from __future__ import annotations

from decimal import Decimal

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
    AssessmentQuestionExtractionImportResponse,
    AssessmentQuestionExtractionResponse,
    AssessmentQuestionExtractionReviewResponse,
    AssessmentQuestionExtractionReviewUpdate,
    AssessmentQuestionExtractionSummaryResponse,
)
from app.services.assessment_question_extraction_service import (
    create_question_extraction,
    get_question_extraction,
    import_question_extraction,
    list_question_extractions_for_document,
    update_question_extraction_review,
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
    required by the extraction-review workspace.
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


@router.patch(
    "/{assessment_id}/question-extractions/{extraction_id}/review",
    response_model=AssessmentQuestionExtractionReviewResponse,
)
async def review_assessment_question_extraction(
    assessment_id: int,
    extraction_id: int,
    payload: AssessmentQuestionExtractionReviewUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AssessmentQuestionExtractionReviewResponse:
    """
    Save teacher review changes for an extraction proposal.

    Review changes may edit proposal question numbering, text, marks,
    parent relationships and inclusion state.

    Raw page evidence and extractor-owned source metadata remain immutable.
    This operation does not create canonical AssessmentQuestion records.
    """

    _ensure_assessment_staff_access(
        current_user,
    )

    extraction = await update_question_extraction_review(
        db=db,
        current_user=current_user,
        assessment_id=assessment_id,
        extraction_id=extraction_id,
        review_update=payload,
    )

    response = AssessmentQuestionExtractionReviewResponse.model_validate(
        extraction,
    )

    return response.model_copy(
        update={
            "message": "Question extraction review saved.",
        }
    )


@router.post(
    "/{assessment_id}/question-extractions/{extraction_id}/import",
    response_model=AssessmentQuestionExtractionImportResponse,
)
async def import_assessment_question_extraction(
    assessment_id: int,
    extraction_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AssessmentQuestionExtractionImportResponse:
    """
    Explicitly import a fully reviewed extraction proposal.

    Import:

    - is allowed only for a fully reviewed active extraction;
    - creates canonical AssessmentQuestion records;
    - synthesises missing structural parent questions when required;
    - preserves canonical parent-child relationships;
    - runs atomically with the extraction lifecycle transition;
    - marks the extraction IMPORTED only after successful question creation.

    No request body is accepted because the stored reviewed proposal is the
    authoritative import source. This prevents the client from modifying the
    approved proposal during import.
    """

    _ensure_assessment_staff_access(
        current_user,
    )

    extraction, imported_questions = await import_question_extraction(
        db=db,
        current_user=current_user,
        assessment_id=assessment_id,
        extraction_id=extraction_id,
    )

    imported_markable_questions = [
        question for question in imported_questions if question.is_markable
    ]

    synthesised_parents = [
        question for question in imported_questions if question.synthesised
    ]

    imported_total_marks = sum(
        (question.maximum_mark for question in imported_markable_questions),
        Decimal("0"),
    )

    extraction_response = AssessmentQuestionExtractionResponse.model_validate(
        extraction,
    )

    return AssessmentQuestionExtractionImportResponse(
        **extraction_response.model_dump(),
        message="Reviewed question extraction imported.",
        imported_question_count=len(
            imported_questions,
        ),
        imported_markable_question_count=len(
            imported_markable_questions,
        ),
        synthesised_parent_count=len(
            synthesised_parents,
        ),
        imported_total_marks=imported_total_marks,
        imported_questions=imported_questions,
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
