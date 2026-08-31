from __future__ import annotations

from hashlib import sha256
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.assessment_candidate import (
    AssessmentScript,
    AssessmentScriptStatus,
)
from app.models.user import User
from app.services.assessment_candidate_service import (
    create_script_version,
    get_candidate,
    get_script,
)


PDF_MIME_TYPE = "application/pdf"

SCANNED_SCRIPT_SOURCE_TYPE = "scanned_pdf"

MAX_SCANNED_SCRIPT_SIZE_BYTES = 25 * 1024 * 1024

ASSESSMENT_SCRIPT_UPLOAD_ROOT = (
    Path("uploads")
    / "assessment-scripts"
)


def _normalise_original_filename(
    filename: str | None,
) -> str:
    """
    Return a safe display filename for an uploaded candidate script.

    Original client path components are never trusted or used for storage.
    """

    raw_filename = (filename or "").strip()

    if not raw_filename:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="The uploaded assessment script must have a filename.",
        )

    normalised_filename = Path(
        raw_filename,
    ).name.strip()

    if not normalised_filename:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="The uploaded assessment script must have a valid filename.",
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


def _validate_scanned_script_pdf(
    *,
    filename: str,
    mime_type: str,
    contents: bytes,
) -> None:
    """
    Validate an uploaded scanned assessment script.
    """

    if (
        Path(
            filename,
        ).suffix.lower()
        != ".pdf"
    ):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Assessment scripts must be uploaded as PDF files.",
        )

    if mime_type != PDF_MIME_TYPE:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Assessment scripts must use the application/pdf MIME type.",
        )

    file_size = len(
        contents,
    )

    if file_size == 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="The uploaded assessment script is empty.",
        )

    if file_size > MAX_SCANNED_SCRIPT_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail="Assessment scripts cannot exceed 25 MB.",
        )

    if not contents.startswith(
        b"%PDF-",
    ):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="The uploaded file does not appear to be a valid PDF.",
        )


def _build_script_upload_directory(
    *,
    school_id: int,
    assessment_id: int,
    candidate_id: int,
) -> Path:
    """
    Return the generated storage directory for one candidate's scripts.
    """

    for value, field_name in (
        (school_id, "school_id"),
        (assessment_id, "assessment_id"),
        (candidate_id, "candidate_id"),
    ):
        if (
            not isinstance(value, int)
            or isinstance(value, bool)
            or value < 1
        ):
            raise ValueError(
                f"{field_name} must be a positive integer.",
            )

    upload_directory = (
        ASSESSMENT_SCRIPT_UPLOAD_ROOT
        / str(
            school_id,
        )
        / str(
            assessment_id,
        )
        / str(
            candidate_id,
        )
    )

    upload_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    return upload_directory


def _build_stored_filename() -> str:
    """
    Return a collision-resistant server-generated PDF filename.
    """

    return f"{uuid4().hex}.pdf"


async def upload_scanned_script(
    *,
    db: AsyncSession,
    current_user: User,
    candidate_id: int,
    filename: str | None,
    mime_type: str | None,
    contents: bytes,
) -> AssessmentScript:
    """
    Store a scanned handwritten script and create its script version.

    The physical PDF and database metadata are treated as one workflow.
    If script creation fails after the file has been written, the newly
    written file is removed before the exception is re-raised.
    """

    candidate = await get_candidate(
        db=db,
        current_user=current_user,
        candidate_id=candidate_id,
    )

    assessment = candidate.assessment

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

    _validate_scanned_script_pdf(
        filename=original_filename,
        mime_type=normalised_mime_type,
        contents=contents,
    )

    upload_directory = _build_script_upload_directory(
        school_id=assessment.school_id,
        assessment_id=assessment.id,
        candidate_id=candidate.id,
    )

    stored_filename = _build_stored_filename()

    destination = (
        upload_directory
        / stored_filename
    )

    checksum = sha256(
        contents,
    ).hexdigest()

    destination.write_bytes(
        contents,
    )

    try:
        script = await create_script_version(
            db=db,
            current_user=current_user,
            candidate_id=candidate.id,
            source_type=SCANNED_SCRIPT_SOURCE_TYPE,
            source_filename=original_filename,
            storage_key=str(
                destination,
            ),
            mime_type=PDF_MIME_TYPE,
            checksum=checksum,
            initial_status=AssessmentScriptStatus.SUBMITTED,
        )

        return script

    except Exception:
        try:
            destination.unlink(
                missing_ok=True,
            )
        except OSError:
            pass

        raise


async def resolve_scanned_script_path(
    *,
    db: AsyncSession,
    current_user: User,
    script_id: int,
) -> tuple[AssessmentScript, Path]:
    """
    Resolve an authorised scanned assessment script to a safe PDF path.

    The stored path must belong to the exact school, assessment, and
    candidate directory represented by the script. This prevents legacy
    or manually created script metadata from referencing another
    candidate's scanned PDF.
    """

    script = await get_script(
        db=db,
        current_user=current_user,
        script_id=script_id,
    )

    if (
        script.source_type != SCANNED_SCRIPT_SOURCE_TYPE
        or not script.storage_key
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scanned assessment script file is not available.",
        )

    candidate = script.candidate
    assessment = candidate.assessment

    expected_directory = (
        ASSESSMENT_SCRIPT_UPLOAD_ROOT
        / str(assessment.school_id)
        / str(assessment.id)
        / str(candidate.id)
    ).resolve()

    script_path = Path(
        script.storage_key,
    ).resolve()

    try:
        script_path.relative_to(
            expected_directory,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Stored scanned assessment script path is invalid.",
        ) from exc

    if not script_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scanned assessment script file is no longer available.",
        )

    return (
        script,
        script_path,
    )

