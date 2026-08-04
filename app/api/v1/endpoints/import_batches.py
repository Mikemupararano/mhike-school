from __future__ import annotations

from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Response,
    UploadFile,
    status,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.imports.registry import registered_import_handlers
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
    update_import_batch,
)
from app.schemas.import_batch import (
    ImportBatchCreate,
    ImportBatchProgress,
    ImportBatchRead,
    ImportBatchSummary,
    ImportBatchUpdate,
    ImportRowRead,
    ImportTypeRead,
)
from app.schemas.import_template import (
    ImportTemplateCsvPreviewRead,
    ImportTemplateListRead,
    ImportTemplateMetadataRead,
)
from app.services.import_service import (
    ImportBatchStateError,
    ImportFileError,
    ImportHeaderError,
    cancel_import_batch,
    retry_import_batch,
    stage_csv_rows,
)
from app.services.import_template_service import (
    build_import_template_csv_preview,
    generate_import_template_csv,
    get_import_template_metadata,
    list_import_template_summaries,
)
from app.tasks.imports import (
    process_import_batch_task,
    validate_import_batch_task,
)

router = APIRouter(
    prefix="/import-batches",
    tags=["Import batches"],
)

DatabaseSession = Annotated[
    AsyncSession,
    Depends(get_db),
]

CurrentUser = Annotated[
    User,
    Depends(get_current_user),
]

MAXIMUM_CSV_FILE_SIZE_BYTES = 10 * 1024 * 1024

IMPORT_ADMIN_ROLE_VALUES = {
    UserRole.PLATFORM_ADMIN.value,
    UserRole.SCHOOL_ADMIN.value,
}


def _normalise_role_value(
    value: object,
) -> str:
    """Return a canonical string representation of a role value."""

    raw_value = getattr(
        value,
        "value",
        value,
    )

    return (
        str(raw_value)
        .strip()
        .lower()
        .replace(
            "-",
            "_",
        )
        .replace(
            " ",
            "_",
        )
    )


def _user_roles(
    current_user: User,
) -> set[str]:
    """
    Resolve all roles belonging to the current user.

    Both the newer multi-role ``roles`` property and the legacy ``role``
    attribute are supported.
    """

    resolved_roles: set[str] = set()

    roles = getattr(
        current_user,
        "roles",
        None,
    )

    if isinstance(
        roles,
        (
            list,
            tuple,
            set,
        ),
    ):
        resolved_roles.update(
            _normalise_role_value(
                role,
            )
            for role in roles
            if role is not None
        )

    primary_role = getattr(
        current_user,
        "role",
        None,
    )

    if primary_role is not None:
        resolved_roles.add(
            _normalise_role_value(
                primary_role,
            ),
        )

    return resolved_roles


def _require_school_id(
    current_user: User,
) -> int:
    """Return the current user's school ID or reject the request."""

    roles = _user_roles(
        current_user,
    )

    is_platform_admin = UserRole.PLATFORM_ADMIN.value in roles

    if is_platform_admin and current_user.school_id is None:
        raise HTTPException(
            status_code=(status.HTTP_400_BAD_REQUEST),
            detail=(
                "A platform administrator must select or belong to a "
                "school before using school import endpoints."
            ),
        )

    if current_user.school_id is None:
        raise HTTPException(
            status_code=(status.HTTP_403_FORBIDDEN),
            detail=("The current user is not assigned to a school."),
        )

    return current_user.school_id


def _require_import_admin(
    current_user: User,
) -> int:
    """Allow only school or platform administrators to manage imports."""

    if not (
        _user_roles(
            current_user,
        )
        & IMPORT_ADMIN_ROLE_VALUES
    ):
        raise HTTPException(
            status_code=(status.HTTP_403_FORBIDDEN),
            detail=(
                "Only school administrators or platform administrators "
                "can manage imports."
            ),
        )

    return _require_school_id(
        current_user,
    )


def _raise_import_service_error(
    exc: Exception,
) -> None:
    """Convert known import-service exceptions into HTTP responses."""

    if isinstance(
        exc,
        ImportHeaderError,
    ):
        raise HTTPException(
            status_code=(status.HTTP_422_UNPROCESSABLE_ENTITY),
            detail=str(exc),
        ) from exc

    if isinstance(
        exc,
        ImportFileError,
    ):
        raise HTTPException(
            status_code=(status.HTTP_400_BAD_REQUEST),
            detail=str(exc),
        ) from exc

    if isinstance(
        exc,
        ImportBatchStateError,
    ):
        raise HTTPException(
            status_code=(status.HTTP_409_CONFLICT),
            detail=str(exc),
        ) from exc

    raise exc


def _raise_unknown_import_type(
    import_type: str,
    exc: KeyError,
) -> None:
    """Convert an unknown registered import type into HTTP 404."""

    raise HTTPException(
        status_code=(status.HTTP_404_NOT_FOUND),
        detail=(f"Import type '{import_type}' is not registered."),
    ) from exc


async def _get_school_batch_or_404(
    db: AsyncSession,
    *,
    batch_id: int,
    school_id: int,
    include_archived: bool = False,
    for_update: bool = False,
) -> ImportBatch:
    """Return one school-scoped import batch or raise HTTP 404."""

    batch = await get_import_batch(
        db,
        batch_id=batch_id,
        school_id=school_id,
        include_archived=include_archived,
        for_update=for_update,
    )

    if batch is None:
        raise HTTPException(
            status_code=(status.HTTP_404_NOT_FOUND),
            detail=("Import batch not found."),
        )

    return batch


async def _queue_processing_task(
    db: AsyncSession,
    *,
    batch: ImportBatch,
    school_id: int,
    queued_stage: str,
    queue_failure_stage: str,
    queue_failure_message: str,
) -> ImportBatch:
    """
    Persist a queued state and dispatch the generic processing task.

    If Celery cannot accept the task, the batch is restored to ``READY``.
    Its row state remains valid and can therefore be queued again safely.
    """

    batch.error_message = None

    await set_import_batch_status(
        db,
        batch=batch,
        status=ImportStatus.QUEUED,
        current_stage=queued_stage,
        error_message=None,
        commit=True,
    )

    try:
        process_import_batch_task.delay(
            batch_id=batch.id,
            school_id=school_id,
        )
    except Exception as exc:
        batch.queued_at = None

        await set_import_batch_status(
            db,
            batch=batch,
            status=ImportStatus.READY,
            current_stage=queue_failure_stage,
            error_message=(queue_failure_message),
            commit=True,
        )

        raise HTTPException(
            status_code=(status.HTTP_503_SERVICE_UNAVAILABLE),
            detail=(queue_failure_message),
        ) from exc

    return batch


@router.post(
    "",
    response_model=ImportBatchRead,
    status_code=(status.HTTP_201_CREATED),
)
async def create_batch(
    payload: ImportBatchCreate,
    db: DatabaseSession,
    current_user: CurrentUser,
) -> ImportBatchRead:
    """Create an empty school-scoped import batch."""

    school_id = _require_import_admin(
        current_user,
    )

    batch = await create_import_batch(
        db,
        school_id=school_id,
        uploaded_by_id=(current_user.id),
        payload=payload,
    )

    return ImportBatchRead.model_validate(
        batch,
    )


@router.get(
    "",
    response_model=(list[ImportBatchSummary]),
)
async def get_batches(
    db: DatabaseSession,
    current_user: CurrentUser,
    import_type: str | None = Query(
        default=None,
    ),
    batch_status: ImportStatus | None = Query(
        default=None,
        alias="status",
    ),
    uploaded_by_id: int | None = Query(
        default=None,
        ge=1,
    ),
    include_archived: bool = Query(
        default=False,
    ),
    offset: int = Query(
        default=0,
        ge=0,
    ),
    limit: int = Query(
        default=50,
        ge=1,
        le=200,
    ),
) -> list[ImportBatchSummary]:
    """List import batches belonging to the current school."""

    school_id = _require_import_admin(
        current_user,
    )

    batches = await list_import_batches(
        db,
        school_id=school_id,
        import_type=import_type,
        status=batch_status,
        uploaded_by_id=(uploaded_by_id),
        is_archived=(None if include_archived else False),
        offset=offset,
        limit=limit,
    )

    return [
        ImportBatchSummary.model_validate(
            batch,
        )
        for batch in batches
    ]


@router.get(
    "/count",
    response_model=dict[str, int],
)
async def get_batch_count(
    db: DatabaseSession,
    current_user: CurrentUser,
    import_type: str | None = Query(
        default=None,
    ),
    batch_status: ImportStatus | None = Query(
        default=None,
        alias="status",
    ),
    uploaded_by_id: int | None = Query(
        default=None,
        ge=1,
    ),
    include_archived: bool = Query(
        default=False,
    ),
) -> dict[str, int]:
    """Count school-scoped import batches."""

    school_id = _require_import_admin(
        current_user,
    )

    total = await count_import_batches(
        db,
        school_id=school_id,
        import_type=import_type,
        status=batch_status,
        uploaded_by_id=(uploaded_by_id),
        is_archived=(None if include_archived else False),
    )

    return {
        "total": total,
    }


@router.get(
    "/types",
    response_model=(list[ImportTypeRead]),
)
async def list_supported_import_types(
    current_user: CurrentUser,
) -> list[ImportTypeRead]:
    """
    Return all import types currently registered by the backend.

    The Import Wizard can use this endpoint instead of maintaining a
    separate hard-coded list of supported import handlers.
    """

    _require_import_admin(
        current_user,
    )

    return [
        ImportTypeRead(
            value=(handler.import_type),
            label=(handler.display_name),
            description=(handler.description),
        )
        for handler in registered_import_handlers()
    ]


@router.get(
    "/templates",
    response_model=(ImportTemplateListRead),
)
async def list_import_templates(
    current_user: CurrentUser,
) -> ImportTemplateListRead:
    """
    Return compact metadata for every registered import template.

    Clients can use this endpoint to discover available templates and display
    field counts, descriptions and template links without loading full
    field-level metadata for every import type.
    """

    _require_import_admin(
        current_user,
    )

    return list_import_template_summaries()


@router.get(
    "/templates/{import_type}",
    response_model=(ImportTemplateMetadataRead),
)
async def get_import_template(
    import_type: str,
    current_user: CurrentUser,
) -> ImportTemplateMetadataRead:
    """
    Return complete metadata for one registered import type.

    Field names, ordering, required status, types, descriptions, examples and
    validation constraints are derived from the handler's registered Pydantic
    schema.
    """

    _require_import_admin(
        current_user,
    )

    try:
        return get_import_template_metadata(
            import_type,
        )
    except KeyError as exc:
        _raise_unknown_import_type(
            import_type,
            exc,
        )


@router.get(
    "/templates/{import_type}/preview",
    response_model=(ImportTemplateCsvPreviewRead),
)
async def preview_import_template(
    import_type: str,
    current_user: CurrentUser,
    include_sample_row: bool = Query(
        default=True,
    ),
) -> ImportTemplateCsvPreviewRead:
    """
    Return a text preview of a generated CSV import template.

    The preview preserves the exact CSV line endings and can optionally omit
    the sample row.
    """

    _require_import_admin(
        current_user,
    )

    try:
        return build_import_template_csv_preview(
            import_type,
            include_sample_row=(include_sample_row),
        )
    except KeyError as exc:
        _raise_unknown_import_type(
            import_type,
            exc,
        )


@router.get(
    "/templates/{import_type}/download",
    response_class=Response,
    responses={
        status.HTTP_200_OK: {
            "content": {
                "text/csv": {},
            },
            "description": ("Generated CSV import template."),
        },
        status.HTTP_404_NOT_FOUND: {
            "description": ("The requested import type is not registered."),
        },
    },
)
async def download_import_template(
    import_type: str,
    current_user: CurrentUser,
    include_sample_row: bool = Query(
        default=True,
    ),
) -> Response:
    """
    Download a generated CSV template for one registered import type.

    CSV headers follow the authoritative Pydantic schema field order. A sample
    row is included by default and may be omitted through the query parameter.
    """

    _require_import_admin(
        current_user,
    )

    try:
        csv_content = generate_import_template_csv(
            import_type,
            include_sample_row=(include_sample_row),
        )
    except KeyError as exc:
        _raise_unknown_import_type(
            import_type,
            exc,
        )

    filename = f"{import_type.strip().lower()}" "_import_template.csv"

    return Response(
        content=csv_content.encode(
            "utf-8-sig",
        ),
        media_type="text/csv",
        headers={
            "Content-Disposition": (f'attachment; filename="{filename}"'),
            "X-Content-Type-Options": ("nosniff"),
        },
    )


@router.get(
    "/{batch_id}",
    response_model=ImportBatchRead,
)
async def get_batch(
    batch_id: int,
    db: DatabaseSession,
    current_user: CurrentUser,
    include_archived: bool = Query(
        default=False,
    ),
) -> ImportBatchRead:
    """Return one import batch belonging to the current school."""

    school_id = _require_import_admin(
        current_user,
    )

    batch = await _get_school_batch_or_404(
        db,
        batch_id=batch_id,
        school_id=school_id,
        include_archived=(include_archived),
    )

    return ImportBatchRead.model_validate(
        batch,
    )


@router.patch(
    "/{batch_id}",
    response_model=ImportBatchRead,
)
async def update_batch(
    batch_id: int,
    payload: ImportBatchUpdate,
    db: DatabaseSession,
    current_user: CurrentUser,
) -> ImportBatchRead:
    """
    Update user-configurable settings for an unprocessed import batch.

    This endpoint is intended for the Import Wizard. It allows administrators
    to persist column mappings, import options and other fields explicitly
    exposed by ``ImportBatchUpdate``.

    Configuration can only be changed while the batch has status
    ``UPLOADED``. Once parsing or validation begins, the persisted row data
    and validation results must remain aligned with the configuration used to
    produce them.
    """

    school_id = _require_import_admin(
        current_user,
    )

    batch = await _get_school_batch_or_404(
        db,
        batch_id=batch_id,
        school_id=school_id,
        include_archived=True,
        for_update=True,
    )

    if batch.is_archived:
        raise HTTPException(
            status_code=(status.HTTP_409_CONFLICT),
            detail=("Archived import batches cannot be updated."),
        )

    if batch.status != ImportStatus.UPLOADED:
        raise HTTPException(
            status_code=(status.HTTP_409_CONFLICT),
            detail=(
                "Import batch configuration can only be updated while "
                "the batch has status 'uploaded'. Current status: "
                f"'{batch.status.value}'."
            ),
        )

    batch = await update_import_batch(
        db,
        batch=batch,
        payload=payload,
        commit=True,
    )

    return ImportBatchRead.model_validate(
        batch,
    )


@router.get(
    "/{batch_id}/progress",
    response_model=(ImportBatchProgress),
)
async def get_batch_progress(
    batch_id: int,
    db: DatabaseSession,
    current_user: CurrentUser,
    include_archived: bool = Query(
        default=False,
    ),
) -> ImportBatchProgress:
    """
    Return current validation and processing progress for an import batch.

    Progress is derived from persisted counters, allowing the administration
    interface to poll this endpoint without loading individual rows.
    """

    school_id = _require_import_admin(
        current_user,
    )

    batch = await _get_school_batch_or_404(
        db,
        batch_id=batch_id,
        school_id=school_id,
        include_archived=(include_archived),
    )

    total_rows = max(
        batch.total_rows,
        0,
    )

    validated_rows = max(
        batch.validated_rows,
        0,
    )

    processed_rows = max(
        batch.processed_rows,
        0,
    )

    validation_percentage = (
        0
        if total_rows == 0
        else min(
            100,
            max(
                0,
                round(
                    (validated_rows / total_rows) * 100,
                ),
            ),
        )
    )

    progress_percentage = (
        0
        if total_rows == 0
        else min(
            100,
            max(
                0,
                round(
                    (processed_rows / total_rows) * 100,
                ),
            ),
        )
    )

    return ImportBatchProgress(
        id=batch.id,
        school_id=batch.school_id,
        import_type=(batch.import_type),
        status=batch.status,
        current_stage=(batch.current_stage),
        total_rows=total_rows,
        validated_rows=(validated_rows),
        processed_rows=(processed_rows),
        successful_rows=max(
            batch.successful_rows,
            0,
        ),
        warning_rows=max(
            batch.warning_rows,
            0,
        ),
        failed_rows=max(
            batch.failed_rows,
            0,
        ),
        skipped_rows=max(
            batch.skipped_rows,
            0,
        ),
        validation_percentage=(validation_percentage),
        progress_percentage=(progress_percentage),
        remaining_validation_rows=max(
            (total_rows - validated_rows),
            0,
        ),
        remaining_processing_rows=max(
            (total_rows - processed_rows),
            0,
        ),
        is_finished=(batch.is_finished),
        is_archived=(batch.is_archived),
        error_message=(batch.error_message),
        queued_at=batch.queued_at,
        started_at=batch.started_at,
        completed_at=(batch.completed_at),
        cancelled_at=(batch.cancelled_at),
        updated_at=batch.updated_at,
    )


@router.post(
    "/{batch_id}/upload",
    response_model=ImportBatchRead,
)
async def upload_batch_file(
    batch_id: int,
    db: DatabaseSession,
    current_user: CurrentUser,
    file: UploadFile = File(...),
    replace_existing: bool = Form(
        default=False,
    ),
) -> ImportBatchRead:
    """
    Upload and stage CSV rows for an existing batch.

    Validation is dispatched after the staged rows have been committed.
    """

    school_id = _require_import_admin(
        current_user,
    )

    batch = await _get_school_batch_or_404(
        db,
        batch_id=batch_id,
        school_id=school_id,
        for_update=True,
    )

    filename = (file.filename or "").strip()

    if not filename.lower().endswith(
        ".csv",
    ):
        raise HTTPException(
            status_code=(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE),
            detail=("Only CSV files are currently supported."),
        )

    content = await file.read()

    if not content:
        raise HTTPException(
            status_code=(status.HTTP_400_BAD_REQUEST),
            detail=("The selected CSV file is empty."),
        )

    if len(content) > MAXIMUM_CSV_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE),
            detail=("The CSV file must not exceed 10 MB."),
        )

    batch.original_filename = filename
    batch.file_format = "csv"
    batch.mime_type = file.content_type or "text/csv"
    batch.file_size_bytes = len(
        content,
    )

    try:
        await stage_csv_rows(
            db,
            batch=batch,
            content=content,
            replace_existing=(replace_existing),
        )
    except Exception as exc:
        _raise_import_service_error(
            exc,
        )

    try:
        validate_import_batch_task.delay(
            batch_id=batch.id,
            school_id=school_id,
        )
    except Exception as exc:
        await set_import_batch_status(
            db,
            batch=batch,
            status=(ImportStatus.UPLOADED),
            current_stage=("validation_queue_failed"),
            error_message=(
                "The validation job could not be queued. "
                "Please try the upload again."
            ),
            commit=True,
        )

        raise HTTPException(
            status_code=(status.HTTP_503_SERVICE_UNAVAILABLE),
            detail=(
                "The CSV was uploaded, but validation could not be "
                "queued. Please try again."
            ),
        ) from exc

    return ImportBatchRead.model_validate(
        batch,
    )


@router.post(
    "/{batch_id}/process",
    response_model=ImportBatchRead,
    status_code=(status.HTTP_202_ACCEPTED),
)
async def process_batch(
    batch_id: int,
    db: DatabaseSession,
    current_user: CurrentUser,
) -> ImportBatchRead:
    """Queue a validated import batch for background processing."""

    school_id = _require_import_admin(
        current_user,
    )

    batch = await _get_school_batch_or_404(
        db,
        batch_id=batch_id,
        school_id=school_id,
        for_update=True,
    )

    if batch.is_archived:
        raise HTTPException(
            status_code=(status.HTTP_409_CONFLICT),
            detail=("Archived import batches cannot be processed."),
        )

    if batch.status != ImportStatus.READY:
        raise HTTPException(
            status_code=(status.HTTP_409_CONFLICT),
            detail=(
                "Only import batches with status 'ready' can be "
                "queued for processing. Current status: "
                f"'{batch.status.value}'."
            ),
        )

    if batch.total_rows < 1:
        raise HTTPException(
            status_code=(status.HTTP_409_CONFLICT),
            detail=("An empty import batch cannot be processed."),
        )

    await _queue_processing_task(
        db,
        batch=batch,
        school_id=school_id,
        queued_stage="queued",
        queue_failure_stage=("processing_queue_failed"),
        queue_failure_message=(
            "The import could not be queued for processing. "
            "The batch remains ready and may be queued again."
        ),
    )

    return ImportBatchRead.model_validate(
        batch,
    )


@router.post(
    "/{batch_id}/retry",
    response_model=ImportBatchRead,
    status_code=(status.HTTP_202_ACCEPTED),
)
async def retry_batch(
    batch_id: int,
    db: DatabaseSession,
    current_user: CurrentUser,
) -> ImportBatchRead:
    """
    Retry only rows that previously failed during processing.

    Successfully imported, updated and skipped rows remain unchanged.
    Validation-invalid rows are not retried by this endpoint.
    """

    school_id = _require_import_admin(
        current_user,
    )

    batch = await _get_school_batch_or_404(
        db,
        batch_id=batch_id,
        school_id=school_id,
        for_update=True,
    )

    try:
        await retry_import_batch(
            db,
            batch=batch,
            commit=True,
        )
    except Exception as exc:
        _raise_import_service_error(
            exc,
        )

    await _queue_processing_task(
        db,
        batch=batch,
        school_id=school_id,
        queued_stage=("retry_queued"),
        queue_failure_stage=("retry_queue_failed"),
        queue_failure_message=(
            "The retry job could not be queued. "
            "The batch remains ready and may be queued again."
        ),
    )

    return ImportBatchRead.model_validate(
        batch,
    )


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
    offset: int = Query(
        default=0,
        ge=0,
    ),
    limit: int = Query(
        default=100,
        ge=1,
        le=500,
    ),
) -> list[ImportRowRead]:
    """List rows belonging to one import batch."""

    school_id = _require_import_admin(
        current_user,
    )

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

    return [
        ImportRowRead.model_validate(
            row,
        )
        for row in rows
    ]


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

    school_id = _require_import_admin(
        current_user,
    )

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

    return {
        "total": total,
    }


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

    school_id = _require_import_admin(
        current_user,
    )

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
            status_code=(status.HTTP_404_NOT_FOUND),
            detail=("Import row not found."),
        )

    return ImportRowRead.model_validate(
        row,
    )


@router.post(
    "/{batch_id}/cancel",
    response_model=ImportBatchRead,
)
async def cancel_batch(
    batch_id: int,
    db: DatabaseSession,
    current_user: CurrentUser,
    reason: str | None = Form(
        default=None,
    ),
) -> ImportBatchRead:
    """Cancel an import batch that has not completed."""

    school_id = _require_import_admin(
        current_user,
    )

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
        _raise_import_service_error(
            exc,
        )

    return ImportBatchRead.model_validate(
        batch,
    )


@router.post(
    "/{batch_id}/archive",
    response_model=ImportBatchRead,
)
async def archive_batch(
    batch_id: int,
    db: DatabaseSession,
    current_user: CurrentUser,
    reason: str | None = Form(
        default=None,
    ),
) -> ImportBatchRead:
    """Archive an import batch while preserving its history."""

    school_id = _require_import_admin(
        current_user,
    )

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
        archived_by_id=(current_user.id),
        archive_reason=reason,
    )

    return ImportBatchRead.model_validate(
        batch,
    )


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

    school_id = _require_import_admin(
        current_user,
    )

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

    return ImportBatchRead.model_validate(
        batch,
    )
