from __future__ import annotations

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.permissions import PermissionService
from app.db.session import get_db
from app.models.user import User
from app.schemas.assessment_document import (
    AssessmentDocumentListResponse,
    AssessmentDocumentRead,
    AssessmentDocumentUploadResponse,
)
from app.services.assessment_document_service import (
    MAX_QUESTION_PAPER_SIZE_BYTES,
    PDF_MIME_TYPE,
    get_current_question_paper,
    list_assessment_documents,
    resolve_assessment_document_path,
    upload_question_paper,
)

router = APIRouter()


def _ensure_assessment_document_staff_access(
    current_user: User,
) -> None:
    """
    Ensure the current user may access staff assessment-document endpoints.

    Detailed assessment ownership, school isolation and administrator scope are
    enforced by the assessment-document service through the established
    assessment access policy.
    """

    PermissionService.ensure_active_user(
        current_user,
    )

    PermissionService.ensure_school_staff_or_platform_admin(
        current_user,
    )


def _translate_value_error(
    exc: ValueError,
) -> HTTPException:
    """
    Translate repository/domain validation errors into HTTP 422.
    """

    return HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        detail=str(
            exc,
        ),
    )


@router.post(
    "/{assessment_id}/documents/question-paper",
    response_model=AssessmentDocumentUploadResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_assessment_question_paper(
    assessment_id: int,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AssessmentDocumentUploadResponse:
    """
    Upload or replace the current PDF question paper for a draft assessment.

    Previous question-paper versions remain retained for audit/history.

    The upload is read with a strict upper bound of the configured maximum
    file size plus one byte. Reading one additional byte allows the endpoint
    to detect an oversized upload without first loading an arbitrarily large
    file into memory.
    """

    _ensure_assessment_document_staff_access(
        current_user,
    )

    try:
        contents = await file.read(
            MAX_QUESTION_PAPER_SIZE_BYTES + 1,
        )

        if len(contents) > MAX_QUESTION_PAPER_SIZE_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                detail="Question papers cannot exceed 25 MB.",
            )

        try:
            document = await upload_question_paper(
                db=db,
                current_user=current_user,
                assessment_id=assessment_id,
                filename=file.filename,
                mime_type=file.content_type,
                contents=contents,
            )
        except ValueError as exc:
            raise _translate_value_error(
                exc,
            ) from exc
    finally:
        await file.close()

    return AssessmentDocumentUploadResponse(
        id=document.id,
        assessment_id=document.assessment_id,
        uploaded_by_id=document.uploaded_by_id,
        document_type=document.document_type,
        original_filename=document.original_filename,
        mime_type=document.mime_type,
        file_size_bytes=document.file_size_bytes,
        is_current=document.is_current,
        extraction_requested=document.extraction_requested,
        extraction_completed=document.extraction_completed,
        extraction_error=document.extraction_error,
        created_at=document.created_at,
        updated_at=document.updated_at,
        message="Question paper uploaded successfully.",
    )


@router.get(
    "/{assessment_id}/documents/question-paper",
    response_model=AssessmentDocumentRead | None,
)
async def get_current_assessment_question_paper(
    assessment_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AssessmentDocumentRead | None:
    """
    Return metadata for the current question paper.

    Returns null when the assessment has no current question paper.
    """

    _ensure_assessment_document_staff_access(
        current_user,
    )

    try:
        document = await get_current_question_paper(
            db=db,
            current_user=current_user,
            assessment_id=assessment_id,
        )
    except ValueError as exc:
        raise _translate_value_error(
            exc,
        ) from exc

    if document is None:
        return None

    return AssessmentDocumentRead.model_validate(
        document,
    )


@router.get(
    "/{assessment_id}/documents",
    response_model=AssessmentDocumentListResponse,
)
async def get_assessment_documents(
    assessment_id: int,
    document_type: str | None = Query(
        default=None,
        min_length=1,
        max_length=50,
    ),
    current_only: bool = Query(
        default=False,
    ),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AssessmentDocumentListResponse:
    """
    Return documents attached to an assessment.

    Historical versions are included by default.
    """

    _ensure_assessment_document_staff_access(
        current_user,
    )

    try:
        documents = await list_assessment_documents(
            db=db,
            current_user=current_user,
            assessment_id=assessment_id,
            document_type=document_type,
            current_only=current_only,
        )
    except ValueError as exc:
        raise _translate_value_error(
            exc,
        ) from exc

    return AssessmentDocumentListResponse(
        assessment_id=assessment_id,
        documents=[
            AssessmentDocumentRead.model_validate(
                document,
            )
            for document in documents
        ],
    )


@router.get(
    "/{assessment_id}/documents/{document_id}/download",
)
async def download_assessment_document(
    assessment_id: int,
    document_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FileResponse:
    """
    Download one assessment document after assessment-scoped permission checks.

    The stored filesystem path is never returned directly to the client.
    """

    _ensure_assessment_document_staff_access(
        current_user,
    )

    try:
        (
            document,
            document_path,
        ) = await resolve_assessment_document_path(
            db=db,
            current_user=current_user,
            assessment_id=assessment_id,
            document_id=document_id,
        )
    except ValueError as exc:
        raise _translate_value_error(
            exc,
        ) from exc

    media_type = document.mime_type or PDF_MIME_TYPE

    return FileResponse(
        path=document_path,
        media_type=media_type,
        filename=document.original_filename,
    )
