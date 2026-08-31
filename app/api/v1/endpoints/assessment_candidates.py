from __future__ import annotations

from fastapi import (
    APIRouter,
    Depends,
    File,
    Query,
    Response,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.permissions import PermissionService
from app.db.session import get_db
from app.models.assessment_candidate import (
    AssessmentCandidateStatus,
    AssessmentScriptStatus,
)
from app.models.user import User
from app.schemas.assessment_candidate import (
    AssessmentCandidateAllocate,
    AssessmentCandidateBulkAllocate,
    AssessmentCandidateBulkOut,
    AssessmentCandidateClassPreviewOut,
    AssessmentCandidateOut,
    AssessmentCandidateStatusUpdate,
    AssessmentCandidateUpdate,
    AssessmentScriptCreate,
    AssessmentScriptOut,
    AssessmentScriptStatusUpdate,
)
from app.services.assessment_candidate_bulk_service import (
    allocate_class_candidates,
    bulk_allocate_candidates,
    preview_class_candidate_allocation,
)
from app.services.assessment_candidate_service import (
    allocate_candidate,
    create_script_version,
    delete_candidate,
    delete_script,
    finalise_script,
    get_candidate,
    get_script,
    list_assessment_candidates,
    list_candidate_scripts,
    mark_candidate_absent,
    mark_script_complete,
    send_script_to_moderation,
    start_candidate,
    start_script_marking,
    submit_candidate,
    submit_script,
    transition_candidate_status,
    transition_script_status,
    update_candidate_details,
    withdraw_candidate,
)
from app.services.assessment_script_upload_service import (
    MAX_SCANNED_SCRIPT_SIZE_BYTES,
    upload_scanned_script,
    resolve_scanned_script_path,
    PDF_MIME_TYPE,
)

router = APIRouter()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ensure_assessment_staff_access(
    current_user: User,
) -> None:
    """
    Ensure the current user may access assessment-management workflows.

    Detailed school isolation, course ownership, candidate ownership, and
    script ownership are enforced by the service layer.
    """

    PermissionService.ensure_active_user(
        current_user,
    )

    PermissionService.ensure_school_staff_or_platform_admin(
        current_user,
    )


# ---------------------------------------------------------------------------
# Candidate allocation and listing
# ---------------------------------------------------------------------------


@router.post(
    "/assessment/{assessment_id}",
    response_model=AssessmentCandidateOut,
    status_code=status.HTTP_201_CREATED,
)
async def allocate_assessment_candidate(
    assessment_id: int,
    payload: AssessmentCandidateAllocate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AssessmentCandidateOut:
    """
    Allocate a student to an assessment.

    The service verifies:

    - assessment management access;
    - course ownership;
    - school isolation;
    - student role;
    - student school membership;
    - duplicate allocation prevention;
    - assessment lifecycle eligibility.
    """

    _ensure_assessment_staff_access(
        current_user,
    )

    candidate = await allocate_candidate(
        db=db,
        current_user=current_user,
        assessment_id=assessment_id,
        student_id=payload.student_id,
        candidate_number=payload.candidate_number,
        access_arrangements=payload.access_arrangements,
    )

    candidate = await get_candidate(
        db=db,
        current_user=current_user,
        candidate_id=candidate.id,
    )

    return AssessmentCandidateOut.model_validate(
        candidate,
    )


@router.get(
    "/assessment/{assessment_id}",
    response_model=list[AssessmentCandidateOut],
)
async def get_assessment_candidates(
    assessment_id: int,
    candidate_status: AssessmentCandidateStatus | None = Query(
        default=None,
    ),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[AssessmentCandidateOut]:
    """
    Return candidates allocated to an assessment.
    """

    _ensure_assessment_staff_access(
        current_user,
    )

    candidates = await list_assessment_candidates(
        db=db,
        current_user=current_user,
        assessment_id=assessment_id,
        candidate_status=candidate_status,
    )

    return [
        AssessmentCandidateOut.model_validate(
            candidate,
        )
        for candidate in candidates
    ]


# ---------------------------------------------------------------------------
# Bulk and class candidate allocation
#
# These static assessment-scoped routes intentionally appear before the
# generic /{candidate_id} routes.
# ---------------------------------------------------------------------------


@router.post(
    "/assessment/{assessment_id}/bulk",
    response_model=AssessmentCandidateBulkOut,
)
async def bulk_allocate_assessment_candidates(
    assessment_id: int,
    payload: AssessmentCandidateBulkAllocate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AssessmentCandidateBulkOut:
    """
    Allocate multiple explicitly selected students to an assessment.

    Duplicate student IDs in the request are collapsed by the service.
    Existing candidate allocations are preserved and reported as already
    allocated rather than causing the whole operation to fail.

    All requested students are validated before any new candidate records are
    committed.
    """

    _ensure_assessment_staff_access(
        current_user,
    )

    result = await bulk_allocate_candidates(
        db=db,
        current_user=current_user,
        assessment_id=assessment_id,
        student_ids=payload.student_ids,
    )

    return AssessmentCandidateBulkOut.model_validate(
        result,
    )


@router.post(
    "/assessment/{assessment_id}/class/{class_id}",
    response_model=AssessmentCandidateBulkOut,
)
async def allocate_assessment_candidates_from_class(
    assessment_id: int,
    class_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AssessmentCandidateBulkOut:
    """
    Allocate the current eligible membership of a class to an assessment.

    Class membership is resolved from current enrolment records at the time of
    allocation.

    Candidate records remain individual assessment allocations. The source
    class is not copied onto AssessmentCandidate, so later class membership
    changes do not rewrite assessment history.

    Existing candidate allocations are preserved and reported rather than
    duplicated.
    """

    _ensure_assessment_staff_access(
        current_user,
    )

    result = await allocate_class_candidates(
        db=db,
        current_user=current_user,
        assessment_id=assessment_id,
        class_id=class_id,
    )

    return AssessmentCandidateBulkOut.model_validate(
        result,
    )


@router.get(
    "/assessment/{assessment_id}/class/{class_id}/preview",
    response_model=AssessmentCandidateClassPreviewOut,
)
async def preview_assessment_candidate_class_allocation(
    assessment_id: int,
    class_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AssessmentCandidateClassPreviewOut:
    """
    Preview class-to-assessment candidate allocation.

    This endpoint is read-only and reports:

    - current enrolment population;
    - students eligible for a new candidate allocation;
    - students already allocated;
    - ineligible enrolment records;
    - whether the assessment currently allows new allocations.

    Closed or archived assessments may still be previewed, but
    ``allocation_allowed`` will be false.
    """

    _ensure_assessment_staff_access(
        current_user,
    )

    preview = await preview_class_candidate_allocation(
        db=db,
        current_user=current_user,
        assessment_id=assessment_id,
        class_id=class_id,
    )

    return AssessmentCandidateClassPreviewOut.model_validate(
        preview,
    )


# ---------------------------------------------------------------------------
# Script routes
#
# These routes intentionally appear before the generic /{candidate_id}
# routes so the static "scripts" path cannot be interpreted as a candidate
# identifier.
# ---------------------------------------------------------------------------


@router.get(
    "/scripts/{script_id}",
    response_model=AssessmentScriptOut,
)
async def get_assessment_script(
    script_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AssessmentScriptOut:
    """
    Return one assessment script.
    """

    _ensure_assessment_staff_access(
        current_user,
    )

    script = await get_script(
        db=db,
        current_user=current_user,
        script_id=script_id,
    )

    return AssessmentScriptOut.model_validate(
        script,
    )


@router.get(
    "/scripts/{script_id}/file",
    response_class=FileResponse,
)
async def get_scanned_assessment_script_file(
    script_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FileResponse:
    """
    Return an authorised scanned assessment-script PDF for inline viewing.
    """

    _ensure_assessment_staff_access(
        current_user,
    )

    (
        script,
        script_path,
    ) = await resolve_scanned_script_path(
        db=db,
        current_user=current_user,
        script_id=script_id,
    )

    filename = (
        script.source_filename
        or f"assessment-script-{script.id}.pdf"
    )

    return FileResponse(
        path=script_path,
        media_type=PDF_MIME_TYPE,
        filename=filename,
        content_disposition_type="inline",
    )


@router.patch(
    "/scripts/{script_id}/status",
    response_model=AssessmentScriptOut,
)
async def update_assessment_script_status(
    script_id: int,
    payload: AssessmentScriptStatusUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AssessmentScriptOut:
    """
    Move a script through an allowed lifecycle transition.
    """

    _ensure_assessment_staff_access(
        current_user,
    )

    script = await transition_script_status(
        db=db,
        current_user=current_user,
        script_id=script_id,
        new_status=payload.status,
    )

    return AssessmentScriptOut.model_validate(
        script,
    )


@router.post(
    "/scripts/{script_id}/submit",
    response_model=AssessmentScriptOut,
)
async def submit_assessment_script(
    script_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AssessmentScriptOut:
    """
    Submit a script for marking.
    """

    _ensure_assessment_staff_access(
        current_user,
    )

    script = await submit_script(
        db=db,
        current_user=current_user,
        script_id=script_id,
    )

    return AssessmentScriptOut.model_validate(
        script,
    )


@router.post(
    "/scripts/{script_id}/start-marking",
    response_model=AssessmentScriptOut,
)
async def start_assessment_script_marking(
    script_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AssessmentScriptOut:
    """
    Move a submitted script into marking.
    """

    _ensure_assessment_staff_access(
        current_user,
    )

    script = await start_script_marking(
        db=db,
        current_user=current_user,
        script_id=script_id,
    )

    return AssessmentScriptOut.model_validate(
        script,
    )


@router.post(
    "/scripts/{script_id}/mark-complete",
    response_model=AssessmentScriptOut,
)
async def complete_assessment_script_marking(
    script_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AssessmentScriptOut:
    """
    Mark primary marking as complete.
    """

    _ensure_assessment_staff_access(
        current_user,
    )

    script = await mark_script_complete(
        db=db,
        current_user=current_user,
        script_id=script_id,
    )

    return AssessmentScriptOut.model_validate(
        script,
    )


@router.post(
    "/scripts/{script_id}/moderation",
    response_model=AssessmentScriptOut,
)
async def send_assessment_script_to_moderation(
    script_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AssessmentScriptOut:
    """
    Send a marked script to moderation.
    """

    _ensure_assessment_staff_access(
        current_user,
    )

    script = await send_script_to_moderation(
        db=db,
        current_user=current_user,
        script_id=script_id,
    )

    return AssessmentScriptOut.model_validate(
        script,
    )


@router.post(
    "/scripts/{script_id}/finalise",
    response_model=AssessmentScriptOut,
)
async def finalise_assessment_script(
    script_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AssessmentScriptOut:
    """
    Finalise a marked or moderated script.
    """

    _ensure_assessment_staff_access(
        current_user,
    )

    script = await finalise_script(
        db=db,
        current_user=current_user,
        script_id=script_id,
    )

    return AssessmentScriptOut.model_validate(
        script,
    )


@router.delete(
    "/scripts/{script_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_assessment_script(
    script_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    """
    Delete an unsubmitted script.

    Submitted scripts are retained for marking, moderation, analysis, and
    audit history.
    """

    _ensure_assessment_staff_access(
        current_user,
    )

    await delete_script(
        db=db,
        current_user=current_user,
        script_id=script_id,
    )

    return Response(
        status_code=status.HTTP_204_NO_CONTENT,
    )


# ---------------------------------------------------------------------------
# Candidate retrieval and editing
# ---------------------------------------------------------------------------


@router.get(
    "/{candidate_id}",
    response_model=AssessmentCandidateOut,
)
async def get_assessment_candidate(
    candidate_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AssessmentCandidateOut:
    """
    Return one assessment candidate.
    """

    _ensure_assessment_staff_access(
        current_user,
    )

    candidate = await get_candidate(
        db=db,
        current_user=current_user,
        candidate_id=candidate_id,
    )

    return AssessmentCandidateOut.model_validate(
        candidate,
    )


@router.patch(
    "/{candidate_id}",
    response_model=AssessmentCandidateOut,
)
async def update_assessment_candidate(
    candidate_id: int,
    payload: AssessmentCandidateUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AssessmentCandidateOut:
    """
    Update candidate metadata.

    Candidate metadata becomes immutable once the candidate has submitted,
    withdrawn, or been marked absent.
    """

    _ensure_assessment_staff_access(
        current_user,
    )

    candidate = await update_candidate_details(
        db=db,
        current_user=current_user,
        candidate_id=candidate_id,
        candidate_number=payload.candidate_number,
        access_arrangements=payload.access_arrangements,
    )

    candidate = await get_candidate(
        db=db,
        current_user=current_user,
        candidate_id=candidate.id,
    )

    return AssessmentCandidateOut.model_validate(
        candidate,
    )


# ---------------------------------------------------------------------------
# Candidate lifecycle
# ---------------------------------------------------------------------------


@router.patch(
    "/{candidate_id}/status",
    response_model=AssessmentCandidateOut,
)
async def update_assessment_candidate_status(
    candidate_id: int,
    payload: AssessmentCandidateStatusUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AssessmentCandidateOut:
    """
    Move a candidate through an allowed lifecycle transition.
    """

    _ensure_assessment_staff_access(
        current_user,
    )

    candidate = await transition_candidate_status(
        db=db,
        current_user=current_user,
        candidate_id=candidate_id,
        new_status=payload.status,
    )

    candidate = await get_candidate(
        db=db,
        current_user=current_user,
        candidate_id=candidate.id,
    )

    return AssessmentCandidateOut.model_validate(
        candidate,
    )


@router.post(
    "/{candidate_id}/start",
    response_model=AssessmentCandidateOut,
)
async def start_assessment_candidate(
    candidate_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AssessmentCandidateOut:
    """
    Mark an allocated candidate as having started the assessment.
    """

    _ensure_assessment_staff_access(
        current_user,
    )

    candidate = await start_candidate(
        db=db,
        current_user=current_user,
        candidate_id=candidate_id,
    )

    candidate = await get_candidate(
        db=db,
        current_user=current_user,
        candidate_id=candidate.id,
    )

    return AssessmentCandidateOut.model_validate(
        candidate,
    )


@router.post(
    "/{candidate_id}/submit",
    response_model=AssessmentCandidateOut,
)
async def submit_assessment_candidate(
    candidate_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AssessmentCandidateOut:
    """
    Mark a started candidate as submitted.
    """

    _ensure_assessment_staff_access(
        current_user,
    )

    candidate = await submit_candidate(
        db=db,
        current_user=current_user,
        candidate_id=candidate_id,
    )

    candidate = await get_candidate(
        db=db,
        current_user=current_user,
        candidate_id=candidate.id,
    )

    return AssessmentCandidateOut.model_validate(
        candidate,
    )


@router.post(
    "/{candidate_id}/withdraw",
    response_model=AssessmentCandidateOut,
)
async def withdraw_assessment_candidate(
    candidate_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AssessmentCandidateOut:
    """
    Withdraw an allocated or started candidate.
    """

    _ensure_assessment_staff_access(
        current_user,
    )

    candidate = await withdraw_candidate(
        db=db,
        current_user=current_user,
        candidate_id=candidate_id,
    )

    candidate = await get_candidate(
        db=db,
        current_user=current_user,
        candidate_id=candidate.id,
    )

    return AssessmentCandidateOut.model_validate(
        candidate,
    )


@router.post(
    "/{candidate_id}/absent",
    response_model=AssessmentCandidateOut,
)
async def mark_assessment_candidate_absent(
    candidate_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AssessmentCandidateOut:
    """
    Mark an allocated candidate absent.
    """

    _ensure_assessment_staff_access(
        current_user,
    )

    candidate = await mark_candidate_absent(
        db=db,
        current_user=current_user,
        candidate_id=candidate_id,
    )

    candidate = await get_candidate(
        db=db,
        current_user=current_user,
        candidate_id=candidate.id,
    )

    return AssessmentCandidateOut.model_validate(
        candidate,
    )


# ---------------------------------------------------------------------------
# Candidate scripts
# ---------------------------------------------------------------------------


@router.post(
    "/{candidate_id}/scripts/upload",
    response_model=AssessmentScriptOut,
    status_code=status.HTTP_201_CREATED,
)
async def upload_assessment_scanned_script(
    candidate_id: int,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AssessmentScriptOut:
    """
    Upload a scanned handwritten PDF script for an assessment candidate.

    The upload is read with a strict upper bound of the configured maximum
    size plus one byte so oversized requests can be rejected without loading
    an arbitrarily large file into memory.
    """

    _ensure_assessment_staff_access(
        current_user,
    )

    filename = file.filename
    mime_type = file.content_type

    try:
        contents = await file.read(
            MAX_SCANNED_SCRIPT_SIZE_BYTES + 1,
        )
    finally:
        await file.close()

    script = await upload_scanned_script(
        db=db,
        current_user=current_user,
        candidate_id=candidate_id,
        filename=filename,
        mime_type=mime_type,
        contents=contents,
    )

    return AssessmentScriptOut.model_validate(
        script,
    )


@router.post(
    "/{candidate_id}/scripts",
    response_model=AssessmentScriptOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_assessment_script(
    candidate_id: int,
    payload: AssessmentScriptCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AssessmentScriptOut:
    """
    Create the next script version for a candidate.
    """

    _ensure_assessment_staff_access(
        current_user,
    )

    script = await create_script_version(
        db=db,
        current_user=current_user,
        candidate_id=candidate_id,
        source_type=payload.source_type,
        source_filename=payload.source_filename,
        storage_key=payload.storage_key,
        mime_type=payload.mime_type,
        checksum=payload.checksum,
    )

    return AssessmentScriptOut.model_validate(
        script,
    )


@router.get(
    "/{candidate_id}/scripts",
    response_model=list[AssessmentScriptOut],
)
async def get_candidate_scripts(
    candidate_id: int,
    script_status: AssessmentScriptStatus | None = Query(
        default=None,
    ),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[AssessmentScriptOut]:
    """
    Return all script versions for a candidate.
    """

    _ensure_assessment_staff_access(
        current_user,
    )

    scripts = await list_candidate_scripts(
        db=db,
        current_user=current_user,
        candidate_id=candidate_id,
        script_status=script_status,
    )

    return [
        AssessmentScriptOut.model_validate(
            script,
        )
        for script in scripts
    ]


# ---------------------------------------------------------------------------
# Candidate deletion
# ---------------------------------------------------------------------------


@router.delete(
    "/{candidate_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_assessment_candidate(
    candidate_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    """
    Delete an untouched candidate allocation.

    Once participation or script history exists, the allocation is retained
    for assessment and audit history.
    """

    _ensure_assessment_staff_access(
        current_user,
    )

    await delete_candidate(
        db=db,
        current_user=current_user,
        candidate_id=candidate_id,
    )

    return Response(
        status_code=status.HTTP_204_NO_CONTENT,
    )

