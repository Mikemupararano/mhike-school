from __future__ import annotations

from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.import_batch import (
    ImportBatch,
    ImportRowStatus,
    ImportStatus,
)
from app.models.user import User, UserRole
from app.repositories.import_batches import (
    archive_import_batch,
    count_import_batches,
    count_import_rows,
    create_import_batch,
    get_import_batch,
    get_import_row,
    list_import_batches,
    list_import_rows,
    restore_import_batch,
    set_import_batch_status,
)
from app.schemas.import_batch import (
    ImportBatchCreate,
    ImportBatchRead,
    ImportBatchSummary,
    ImportRowRead,
)
from app.services.import_service import (
    ImportBatchStateError,
    ImportFileError,
    ImportHeaderError,
    cancel_import_batch,
    stage_csv_rows,
)
from app.tasks.imports import (
    process_import_batch_task,
    validate_import_batch_task,
)

router = APIRouter(
    prefix="/import-batches",
    tags=["Import batches"],
)

DatabaseSession = Annotated[AsyncSession, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]

MAXIMUM_CSV_FILE_SIZE_BYTES = 10 * 1024 * 1024

IMPORT_ADMIN_ROLE_VALUES = {
    UserRole.PLATFORM_ADMIN.value,
    UserRole.SCHOOL_ADMIN.value,
}


def _normalise_role_value(value: object) -> str:
    """Return a canonical string representation of a role value."""

    raw_value = getattr(value, "value", value)

    return str(raw_value).strip().lower().replace("-", "_").replace(" ", "_")


def _user_roles(current_user: User) -> set[str]:
    """
    Resolve the user's primary and secondary roles.

    This supports both the legacy ``role`` field and the multi-role
    ``roles`` property.
    """

    resolved_roles: set[str] = set()

    roles = getattr(current_user, "roles", None)

    if isinstance(roles, (list, tuple, set)):
        resolved_roles.update(
            _normalise_role_value(role) for role in roles if role is not None
        )

    primary_role = getattr(current_user, "role", None)

    if primary_role is not None:
        resolved_roles.add(
            _normalise_role_value(primary_role),
        )

    return resolved_roles


def _require_school_id(current_user: User) -> int:
    """Return the current user's school ID or reject the request."""

    is_platform_admin = UserRole.PLATFORM_ADMIN.value in _user_roles(current_user)

    if is_platform_admin and current_user.school_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "A platform administrator must select or belong to a "
                "school before using school import endpoints."
            ),
        )

    if current_user.school_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The current user is not assigned to a school.",
        )

    return current_user.school_id


def _require_import_admin(current_user: User) -> int:
    """Allow only school or platform administrators to manage imports."""

    if not (_user_roles(current_user) & IMPORT_ADMIN_ROLE_VALUES):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "Only school administrators or platform administrators "
                "can manage imports."
            ),
        )

    return _require_school_id(current_user)


def _raise_import_service_error(exc: Exception) -> None:
    """Convert known import-service errors into HTTP responses."""

    if isinstance(exc, ImportHeaderError):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    if isinstance(exc, ImportFileError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    if isinstance(exc, ImportBatchStateError):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    raise exc


async def _get_school_batch_or_404(
    db: AsyncSession,
    *,
    batch_id: int,
    school_id: int,
    include_archived: bool = False,
    for_update: bool = False,
) -> ImportBatch:
    """Return one school-scoped batch or raise HTTP 404."""

    batch = await get_import_batch(
        db,
        batch_id=batch_id,
        school_id=school_id,
        include_archived=include_archived,
        for_update=for_update,
    )

    if batch is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Import batch not found.",
        )

    return batch


@router.post(
    "",
    response_model=ImportBatchRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_batch(
    payload: ImportBatchCreate,
    db: DatabaseSession,
    current_user: CurrentUser,
) -> ImportBatchRead:
    """Create an empty school-scoped import batch."""

    school_id = _require_import_admin(current_user)

    batch = await create_import_batch(
        db,
        school_id=school_id,
        uploaded_by_id=current_user.id,
        payload=payload,
    )

    return ImportBatchRead.model_validate(batch)


@router.get(
    "",
    response_model=list[ImportBatchSummary],
)
async def get_batches(
    db: DatabaseSession,
    current_user: CurrentUser,
    import_type: str | None = Query(default=None),
    batch_status: ImportStatus | None = Query(
        default=None,
        alias="status",
    ),
    uploaded_by_id: int | None = Query(
        default=None,
        ge=1,
    ),
    include_archived: bool = Query(default=False),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
) -> list[ImportBatchSummary]:
    """List import batches belonging to the current school."""

    school_id = _require_import_admin(current_user)

    batches = await list_import_batches(
        db,
        school_id=school_id,
        import_type=import_type,
        status=batch_status,
        uploaded_by_id=uploaded_by_id,
        is_archived=None if include_archived else False,
        offset=offset,
        limit=limit,
    )

    return [ImportBatchSummary.model_validate(batch) for batch in batches]


@router.get(
    "/count",
    response_model=dict[str, int],
)
async def get_batch_count(
    db: DatabaseSession,
    current_user: CurrentUser,
    import_type: str | None = Query(default=None),
    batch_status: ImportStatus | None = Query(
        default=None,
        alias="status",
    ),
    uploaded_by_id: int | None = Query(
        default=None,
        ge=1,
    ),
    include_archived: bool = Query(default=False),
) -> dict[str, int]:
    """Count school-scoped import batches."""

    school_id = _require_import_admin(current_user)

    total = await count_import_batches(
        db,
        school_id=school_id,
        import_type=import_type,
        status=batch_status,
        uploaded_by_id=uploaded_by_id,
        is_archived=None if include_archived else False,
    )

    return {"total": total}


@router.get(
    "/{batch_id}",
    response_model=ImportBatchRead,
)
async def get_batch(
    batch_id: int,
    db: DatabaseSession,
    current_user: CurrentUser,
    include_archived: bool = Query(default=False),
) -> ImportBatchRead:
    """Return one import batch belonging to the current school."""

    school_id = _require_import_admin(current_user)

    batch = await _get_school_batch_or_404(
        db,
        batch_id=batch_id,
        school_id=school_id,
        include_archived=include_archived,
    )

    return ImportBatchRead.model_validate(batch)


@router.post(
    "/{batch_id}/upload",
    response_model=ImportBatchRead,
)
async def upload_batch_file(
    batch_id: int,
    db: DatabaseSession,
    current_user: CurrentUser,
    file: UploadFile = File(...),
    replace_existing: bool = Form(default=False),
) -> ImportBatchRead:
    """
    Upload and stage CSV rows for an existing import batch.

    Validation is dispatched to Celery after the staged rows have been
    committed successfully.
    """

    school_id = _require_import_admin(current_user)

    batch = await _get_school_batch_or_404(
        db,
        batch_id=batch_id,
        school_id=school_id,
        for_update=True,
    )

    filename = (file.filename or "").strip()

    if not filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Only CSV files are currently supported.",
        )

    content = await file.read()

    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The selected CSV file is empty.",
        )

    if len(content) > MAXIMUM_CSV_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="The CSV file must not exceed 10 MB.",
        )

    batch.original_filename = filename
    batch.file_format = "csv"
    batch.mime_type = file.content_type or "text/csv"
    batch.file_size_bytes = len(content)

    try:
        await stage_csv_rows(
            db,
            batch=batch,
            content=content,
            replace_existing=replace_existing,
        )
    except Exception as exc:
        _raise_import_service_error(exc)

    try:
        validate_import_batch_task.delay(
            batch_id=batch.id,
            school_id=school_id,
        )
    except Exception as exc:
        await set_import_batch_status(
            db,
            batch=batch,
            status=ImportStatus.UPLOADED,
            current_stage="validation_queue_failed",
            error_message=(
                "The validation job could not be queued. "
                "Please try the upload again."
            ),
            commit=True,
        )

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "The CSV was uploaded, but validation could not be "
                "queued. Please try again."
            ),
        ) from exc

    return ImportBatchRead.model_validate(batch)


@router.post(
    "/{batch_id}/process",
    response_model=ImportBatchRead,
    status_code=status.HTTP_202_ACCEPTED,
)
async def process_batch(
    batch_id: int,
    db: DatabaseSession,
    current_user: CurrentUser,
) -> ImportBatchRead:
    """
    Queue a validated import batch for background processing.

    A row-level database lock prevents concurrent requests from queuing the
    same batch more than once.
    """

    school_id = _require_import_admin(current_user)

    batch = await _get_school_batch_or_404(
        db,
        batch_id=batch_id,
        school_id=school_id,
        for_update=True,
    )

    if batch.is_archived:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Archived import batches cannot be processed.",
        )

    if batch.status != ImportStatus.READY:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Only import batches with status 'ready' can be "
                f"queued for processing. Current status: "
                f"'{batch.status.value}'."
            ),
        )

    if batch.total_rows < 1:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An empty import batch cannot be processed.",
        )

    await set_import_batch_status(
        db,
        batch=batch,
        status=ImportStatus.QUEUED,
        current_stage="queued",
        error_message=None,
        commit=True,
    )

    try:
        process_import_batch_task.delay(
            batch_id=batch.id,
            school_id=school_id,
        )
    except Exception as exc:
        # Restore READY so the administrator can retry safely.
        await set_import_batch_status(
            db,
            batch=batch,
            status=ImportStatus.READY,
            current_stage="processing_queue_failed",
            error_message=(
                "The processing job could not be queued. " "The batch may be retried."
            ),
            commit=True,
        )

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "The import could not be queued for processing. " "Please try again."
            ),
        ) from exc

    return ImportBatchRead.model_validate(batch)


@router.get(
    "/{batch_id}/rows",
    response_model=list[ImportRowRead],
)
async def get_batch_rows(
    batch_id: int,
    db: DatabaseSession,
    current_user: CurrentUser,
    row_status: ImportRowStatus | None = Query(
        default=None,
        alias="status",
    ),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
) -> list[ImportRowRead]:
    """List rows belonging to one import batch."""

    school_id = _require_import_admin(current_user)

    await _get_school_batch_or_404(
        db,
        batch_id=batch_id,
        school_id=school_id,
    )

    rows = await list_import_rows(
        db,
        batch_id=batch_id,
        school_id=school_id,
        status=row_status,
        offset=offset,
        limit=limit,
    )

    return [ImportRowRead.model_validate(row) for row in rows]


@router.get(
    "/{batch_id}/rows/count",
    response_model=dict[str, int],
)
async def get_batch_row_count(
    batch_id: int,
    db: DatabaseSession,
    current_user: CurrentUser,
    row_status: ImportRowStatus | None = Query(
        default=None,
        alias="status",
    ),
) -> dict[str, int]:
    """Count rows in one school-scoped import batch."""

    school_id = _require_import_admin(current_user)

    await _get_school_batch_or_404(
        db,
        batch_id=batch_id,
        school_id=school_id,
    )

    total = await count_import_rows(
        db,
        batch_id=batch_id,
        school_id=school_id,
        status=row_status,
    )

    return {"total": total}


@router.get(
    "/{batch_id}/rows/{row_id}",
    response_model=ImportRowRead,
)
async def get_batch_row(
    batch_id: int,
    row_id: int,
    db: DatabaseSession,
    current_user: CurrentUser,
) -> ImportRowRead:
    """Return one import row."""

    school_id = _require_import_admin(current_user)

    await _get_school_batch_or_404(
        db,
        batch_id=batch_id,
        school_id=school_id,
    )

    row = await get_import_row(
        db,
        row_id=row_id,
        batch_id=batch_id,
        school_id=school_id,
    )

    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Import row not found.",
        )

    return ImportRowRead.model_validate(row)


@router.post(
    "/{batch_id}/cancel",
    response_model=ImportBatchRead,
)
async def cancel_batch(
    batch_id: int,
    db: DatabaseSession,
    current_user: CurrentUser,
    reason: str | None = Form(default=None),
) -> ImportBatchRead:
    """Cancel an import batch that has not completed."""

    school_id = _require_import_admin(current_user)

    batch = await _get_school_batch_or_404(
        db,
        batch_id=batch_id,
        school_id=school_id,
        for_update=True,
    )

    try:
        await cancel_import_batch(
            db,
            batch=batch,
            reason=reason,
        )
    except Exception as exc:
        _raise_import_service_error(exc)

    return ImportBatchRead.model_validate(batch)


@router.post(
    "/{batch_id}/archive",
    response_model=ImportBatchRead,
)
async def archive_batch(
    batch_id: int,
    db: DatabaseSession,
    current_user: CurrentUser,
    reason: str | None = Form(default=None),
) -> ImportBatchRead:
    """Archive an import batch while preserving its history."""

    school_id = _require_import_admin(current_user)

    batch = await _get_school_batch_or_404(
        db,
        batch_id=batch_id,
        school_id=school_id,
        include_archived=True,
        for_update=True,
    )

    await archive_import_batch(
        db,
        batch=batch,
        archived_by_id=current_user.id,
        archive_reason=reason,
    )

    return ImportBatchRead.model_validate(batch)


@router.post(
    "/{batch_id}/restore",
    response_model=ImportBatchRead,
)
async def restore_batch(
    batch_id: int,
    db: DatabaseSession,
    current_user: CurrentUser,
) -> ImportBatchRead:
    """Restore an archived import batch."""

    school_id = _require_import_admin(current_user)

    batch = await _get_school_batch_or_404(
        db,
        batch_id=batch_id,
        school_id=school_id,
        include_archived=True,
        for_update=True,
    )

    await restore_import_batch(
        db,
        batch=batch,
    )

    return ImportBatchRead.model_validate(batch)
