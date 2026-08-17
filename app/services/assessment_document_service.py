from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.assessment import AssessmentStatus
from app.models.assessment_document import AssessmentDocument
from app.models.user import User
from app.repositories.assessment_document import AssessmentDocumentRepository
from app.services.assessment_service import get_assessment

QUESTION_PAPER_DOCUMENT_TYPE = "question_paper"

PDF_MIME_TYPE = "application/pdf"

MAX_QUESTION_PAPER_SIZE_BYTES = 25 * 1024 * 1024

ASSESSMENT_UPLOAD_ROOT = (
    Path(
        "uploads",
    )
    / "assessments"
)


def _normalise_original_filename(
    filename: str | None,
) -> str:
    """
    Return a safe display filename for an uploaded assessment document.

    The original user-supplied path must never be trusted. Browsers normally
    send only a filename, but Path.name also protects against a client
    deliberately submitting directory components.
    """

    raw_filename = (filename or "").strip()

    if not raw_filename:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="The uploaded question paper must have a filename.",
        )

    normalised_filename = Path(
        raw_filename,
    ).name.strip()

    if not normalised_filename:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="The uploaded question paper must have a valid filename.",
        )

    if len(normalised_filename) > 500:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="The uploaded filename cannot exceed 500 characters.",
        )

    return normalised_filename


def _normalise_mime_type(
    mime_type: str | None,
) -> str:
    """
    Return a normalised upload MIME type.
    """

    return (mime_type or "").strip().lower()


def _validate_pdf_upload(
    *,
    filename: str,
    mime_type: str,
    contents: bytes,
) -> None:
    """
    Validate an uploaded question paper.

    Validation deliberately checks:

    - filename extension;
    - declared MIME type;
    - non-empty content;
    - maximum upload size;
    - the PDF magic header.

    MIME type and filename checks alone are insufficient because both are
    supplied by the client.
    """

    if (
        Path(
            filename,
        ).suffix.lower()
        != ".pdf"
    ):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Question papers must be uploaded as PDF files.",
        )

    if mime_type != PDF_MIME_TYPE:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Question papers must use the application/pdf MIME type.",
        )

    file_size = len(
        contents,
    )

    if file_size == 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="The uploaded question paper is empty.",
        )

    if file_size > MAX_QUESTION_PAPER_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Question papers cannot exceed 25 MB.",
        )

    if not contents.startswith(
        b"%PDF-",
    ):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="The uploaded file does not appear to be a valid PDF.",
        )


def _build_assessment_upload_directory(
    *,
    school_id: int,
    assessment_id: int,
) -> Path:
    """
    Return the storage directory for one assessment.

    Generated storage paths use database identifiers only. No user-controlled
    filename component is included in the directory hierarchy.
    """

    if school_id < 1:
        raise ValueError(
            "school_id must be a positive integer.",
        )

    if assessment_id < 1:
        raise ValueError(
            "assessment_id must be a positive integer.",
        )

    upload_directory = (
        ASSESSMENT_UPLOAD_ROOT
        / str(
            school_id,
        )
        / str(
            assessment_id,
        )
    )

    upload_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    return upload_directory


def _build_stored_filename() -> str:
    """
    Return a generated storage filename.

    Original filenames are retained only as metadata. Using a generated name
    prevents collisions and avoids trusting user-controlled path components.
    """

    return f"{uuid4().hex}.pdf"


async def _load_accessible_assessment(
    *,
    db: AsyncSession,
    current_user: User,
    assessment_id: int,
):
    """
    Load an assessment through the established assessment access policy.

    This reuses the same teacher ownership, administrator scope, and school
    isolation rules as the ordinary assessment-management API.
    """

    return await get_assessment(
        db=db,
        current_user=current_user,
        assessment_id=assessment_id,
        include_relationships=False,
    )


async def _load_editable_assessment(
    *,
    db: AsyncSession,
    current_user: User,
    assessment_id: int,
):
    """
    Load an assessment and ensure its source paper may still be changed.
    """

    assessment = await _load_accessible_assessment(
        db=db,
        current_user=current_user,
        assessment_id=assessment_id,
    )

    if assessment.status != AssessmentStatus.DRAFT:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Question papers can only be uploaded or replaced "
                "while the assessment is in draft."
            ),
        )

    return assessment


async def get_current_question_paper(
    *,
    db: AsyncSession,
    current_user: User,
    assessment_id: int,
) -> AssessmentDocument | None:
    """
    Return the current question paper visible to the current user.
    """

    await _load_accessible_assessment(
        db=db,
        current_user=current_user,
        assessment_id=assessment_id,
    )

    repository = AssessmentDocumentRepository(
        db,
    )

    return await repository.get_current(
        assessment_id=assessment_id,
        document_type=QUESTION_PAPER_DOCUMENT_TYPE,
        include_relationships=False,
    )


async def list_assessment_documents(
    *,
    db: AsyncSession,
    current_user: User,
    assessment_id: int,
    document_type: str | None = None,
    current_only: bool = False,
) -> list[AssessmentDocument]:
    """
    Return assessment documents visible to the current user.

    Historical versions are retained and may be returned unless
    ``current_only`` is requested.
    """

    await _load_accessible_assessment(
        db=db,
        current_user=current_user,
        assessment_id=assessment_id,
    )

    repository = AssessmentDocumentRepository(
        db,
    )

    return await repository.list_for_assessment(
        assessment_id=assessment_id,
        document_type=document_type,
        current_only=current_only,
        include_relationships=False,
    )


async def get_assessment_document(
    *,
    db: AsyncSession,
    current_user: User,
    assessment_id: int,
    document_id: int,
) -> AssessmentDocument:
    """
    Return one assessment-scoped document or raise HTTP 404.
    """

    await _load_accessible_assessment(
        db=db,
        current_user=current_user,
        assessment_id=assessment_id,
    )

    repository = AssessmentDocumentRepository(
        db,
    )

    document = await repository.get_by_id_and_assessment(
        document_id=document_id,
        assessment_id=assessment_id,
        include_relationships=False,
    )

    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assessment document not found.",
        )

    return document


async def resolve_assessment_document_path(
    *,
    db: AsyncSession,
    current_user: User,
    assessment_id: int,
    document_id: int,
) -> tuple[AssessmentDocument, Path]:
    """
    Resolve an assessment document to a safe local storage path.

    The path persisted in the database is never returned directly to the
    client. It is resolved and checked server-side before a download response
    is created.
    """

    document = await get_assessment_document(
        db=db,
        current_user=current_user,
        assessment_id=assessment_id,
        document_id=document_id,
    )

    storage_root = ASSESSMENT_UPLOAD_ROOT.resolve()

    document_path = Path(
        document.storage_path,
    ).resolve()

    try:
        document_path.relative_to(
            storage_root,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Stored assessment document path is invalid.",
        ) from exc

    if not document_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assessment document file is no longer available.",
        )

    return (
        document,
        document_path,
    )


async def upload_question_paper(
    *,
    db: AsyncSession,
    current_user: User,
    assessment_id: int,
    filename: str | None,
    mime_type: str | None,
    contents: bytes,
) -> AssessmentDocument:
    """
    Persist a new current PDF question paper for a draft assessment.

    Replacement is versioned:

    1. the existing current question-paper row is marked non-current;
    2. its physical source PDF remains untouched;
    3. a new generated file is stored;
    4. a new AssessmentDocument row becomes current.

    The database transaction and new file are handled together as closely as
    local filesystem storage allows. If database persistence fails after the
    new file has been written, the new file is removed before the exception is
    re-raised.
    """

    assessment = await _load_editable_assessment(
        db=db,
        current_user=current_user,
        assessment_id=assessment_id,
    )

    if assessment.school_id is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Assessment is not assigned to a school.",
        )

    original_filename = _normalise_original_filename(
        filename,
    )

    normalised_mime_type = _normalise_mime_type(
        mime_type,
    )

    _validate_pdf_upload(
        filename=original_filename,
        mime_type=normalised_mime_type,
        contents=contents,
    )

    upload_directory = _build_assessment_upload_directory(
        school_id=assessment.school_id,
        assessment_id=assessment.id,
    )

    stored_filename = _build_stored_filename()

    destination = upload_directory / stored_filename

    destination.write_bytes(
        contents,
    )

    repository = AssessmentDocumentRepository(
        db,
    )

    document = AssessmentDocument(
        assessment_id=assessment.id,
        uploaded_by_id=current_user.id,
        document_type=QUESTION_PAPER_DOCUMENT_TYPE,
        original_filename=original_filename,
        stored_filename=stored_filename,
        storage_path=str(
            destination,
        ),
        mime_type=PDF_MIME_TYPE,
        file_size_bytes=len(
            contents,
        ),
        is_current=True,
        extraction_requested=False,
        extraction_completed=False,
        extraction_error=None,
    )

    try:
        await repository.mark_current_as_replaced(
            assessment_id=assessment.id,
            document_type=QUESTION_PAPER_DOCUMENT_TYPE,
        )

        document = await repository.create(
            document,
        )

        await db.commit()

        await db.refresh(
            document,
        )

        return document

    except Exception:
        await db.rollback()

        try:
            destination.unlink(
                missing_ok=True,
            )
        except OSError:
            pass

        raise
