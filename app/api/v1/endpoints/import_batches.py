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
from app.models.import_batch import ImportRowStatus, ImportStatus
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
from app.tasks.imports import validate_import_batch_task

router = APIRouter(
    prefix="/import-batches",
    tags=["Import batches"],
)

DatabaseSession = Annotated[AsyncSession, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]

IMPORT_ADMIN_ROLES = {
    UserRole.PLATFORM_ADMIN,
    UserRole.SCHOOL_ADMIN,
}


def _require_school_id(current_user: User) -> int:
    """Return the current user's school ID or reject the request."""

    if current_user.role == UserRole.PLATFORM_ADMIN:
        if current_user.school_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "A platform administrator must select or belong to a "
                    "school before using school import endpoints."
                ),
            )

        return current_user.school_id

    if current_user.school_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The current user is not assigned to a school.",
        )

    return current_user.school_id


def _user_roles(current_user: User) -> set[UserRole]:
    """Resolve both the multi-role and legacy single-role user fields."""

    resolved_roles: set[UserRole] = set()

    roles = getattr(current_user, "roles", None)

    if isinstance(roles, list):
        resolved_roles.update(roles)

    role = getattr(current_user, "role", None)

    if role is not None:
        resolved_roles.add(role)

    return resolved_roles


def _require_import_admin(current_user: User) -> int:
    """Allow only school or platform administrators to manage imports."""

    if not (_user_roles(current_user) & IMPORT_ADMIN_ROLES):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "Only school administrators or platform administrators "
                "can manage imports."
            ),
        )

    return _require_school_id(current_user)


def _raise_import_service_error(exc: Exception) -> None:
    """Convert known service errors into appropriate HTTP responses."""

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
):
    """Return one school-scoped batch or raise an HTTP 404 response."""

    batch = await get_import_batch(
        db,
        batch_id=batch_id,
        school_id=school_id,
        include_archived=include_archived,
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
    uploaded_by_id: int | None = Query(default=None, ge=1),
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
    uploaded_by_id: int | None = Query(default=None, ge=1),
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

    After staging succeeds, validation is dispatched to Celery so that
    row validation runs outside the HTTP request.
    """

    school_id = _require_import_admin(current_user)

    batch = await _get_school_batch_or_404(
        db,
        batch_id=batch_id,
        school_id=school_id,
    )

    filename = file.filename or ""

    if not filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Only CSV files are currently supported.",
        )

    content = await file.read()

    maximum_file_size = 10 * 1024 * 1024

    if len(content) > maximum_file_size:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="The CSV file must not exceed 10 MB.",
        )

    batch.original_filename = filename
    batch.content_type = file.content_type

    try:
        await stage_csv_rows(
            db,
            batch=batch,
            content=content,
            replace_existing=replace_existing,
        )
    except Exception as exc:
        _raise_import_service_error(exc)

    validate_import_batch_task.delay(
        batch_id=batch.id,
        school_id=school_id,
    )

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
    )

    await restore_import_batch(
        db,
        batch=batch,
    )

    return ImportBatchRead.model_validate(batch)
