from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.import_batch import (
    ImportBatch,
    ImportRow,
    ImportRowStatus,
    ImportStatus,
)
from app.schemas.import_batch import (
    ImportBatchCreate,
    ImportBatchUpdate,
    ImportRowCreate,
    ImportRowUpdate,
)


def utc_now() -> datetime:
    """Return the current timezone-aware UTC datetime."""

    return datetime.now(timezone.utc)


def _apply_batch_filters(
    statement: Select[tuple[ImportBatch]],
    *,
    school_id: int,
    import_type: str | None = None,
    status: ImportStatus | None = None,
    uploaded_by_id: int | None = None,
    is_archived: bool | None = False,
) -> Select[tuple[ImportBatch]]:
    """
    Apply reusable school-scoped filters to an import batch query.

    All batch queries must be constrained by ``school_id`` to prevent
    cross-school data exposure.
    """

    statement = statement.where(
        ImportBatch.school_id == school_id,
    )

    if import_type is not None:
        statement = statement.where(
            ImportBatch.import_type == import_type,
        )

    if status is not None:
        statement = statement.where(
            ImportBatch.status == status,
        )

    if uploaded_by_id is not None:
        statement = statement.where(
            ImportBatch.uploaded_by_id == uploaded_by_id,
        )

    if is_archived is not None:
        statement = statement.where(
            ImportBatch.is_archived.is_(is_archived),
        )

    return statement


async def create_import_batch(
    db: AsyncSession,
    *,
    school_id: int,
    uploaded_by_id: int,
    payload: ImportBatchCreate,
    commit: bool = True,
) -> ImportBatch:
    """Create and persist a new import batch."""

    batch = ImportBatch(
        school_id=school_id,
        uploaded_by_id=uploaded_by_id,
        status=ImportStatus.UPLOADED,
        **payload.model_dump(),
    )

    db.add(batch)

    if commit:
        await db.commit()
        await db.refresh(batch)
    else:
        await db.flush()

    return batch


async def get_import_batch(
    db: AsyncSession,
    *,
    batch_id: int,
    school_id: int,
    include_archived: bool = False,
    for_update: bool = False,
) -> ImportBatch | None:
    """
    Return one school-scoped import batch.

    ``for_update=True`` locks the row for workflows that change batch state,
    counters or processing metadata.
    """

    statement = select(ImportBatch).where(
        ImportBatch.id == batch_id,
        ImportBatch.school_id == school_id,
    )

    if not include_archived:
        statement = statement.where(
            ImportBatch.is_archived.is_(False),
        )

    if for_update:
        statement = statement.with_for_update()

    result = await db.execute(statement)

    return result.scalar_one_or_none()


async def list_import_batches(
    db: AsyncSession,
    *,
    school_id: int,
    import_type: str | None = None,
    status: ImportStatus | None = None,
    uploaded_by_id: int | None = None,
    is_archived: bool | None = False,
    offset: int = 0,
    limit: int = 50,
) -> Sequence[ImportBatch]:
    """List import batches for one school with filtering and pagination."""

    safe_offset = max(offset, 0)
    safe_limit = min(
        max(limit, 1),
        200,
    )

    statement = select(ImportBatch)

    statement = _apply_batch_filters(
        statement,
        school_id=school_id,
        import_type=import_type,
        status=status,
        uploaded_by_id=uploaded_by_id,
        is_archived=is_archived,
    )

    statement = (
        statement.order_by(
            ImportBatch.created_at.desc(),
            ImportBatch.id.desc(),
        )
        .offset(safe_offset)
        .limit(safe_limit)
    )

    result = await db.execute(statement)

    return result.scalars().all()


async def count_import_batches(
    db: AsyncSession,
    *,
    school_id: int,
    import_type: str | None = None,
    status: ImportStatus | None = None,
    uploaded_by_id: int | None = None,
    is_archived: bool | None = False,
) -> int:
    """Count school-scoped import batches matching the supplied filters."""

    filtered_statement = select(ImportBatch)

    filtered_statement = _apply_batch_filters(
        filtered_statement,
        school_id=school_id,
        import_type=import_type,
        status=status,
        uploaded_by_id=uploaded_by_id,
        is_archived=is_archived,
    )

    count_statement = select(func.count()).select_from(
        filtered_statement.subquery(),
    )

    result = await db.execute(count_statement)

    return int(result.scalar_one())


async def update_import_batch(
    db: AsyncSession,
    *,
    batch: ImportBatch,
    payload: ImportBatchUpdate,
    commit: bool = True,
) -> ImportBatch:
    """
    Apply user-editable batch fields.

    System-controlled fields such as school ownership, uploader, counters and
    status are deliberately not accepted by ``ImportBatchUpdate``.
    """

    update_data = payload.model_dump(
        exclude_unset=True,
    )

    for field_name, value in update_data.items():
        setattr(
            batch,
            field_name,
            value,
        )

    if commit:
        await db.commit()
        await db.refresh(batch)
    else:
        await db.flush()

    return batch


async def set_import_batch_status(
    db: AsyncSession,
    *,
    batch: ImportBatch,
    status: ImportStatus,
    current_stage: str | None = None,
    error_message: str | None = None,
    commit: bool = True,
) -> ImportBatch:
    """Update a batch workflow status and its associated timestamps."""

    now = utc_now()

    batch.status = status

    if current_stage is not None:
        batch.current_stage = current_stage

    if status == ImportStatus.READY:
        batch.confirmed_at = batch.confirmed_at or now

    elif status == ImportStatus.QUEUED:
        batch.queued_at = batch.queued_at or now

    elif status == ImportStatus.PROCESSING:
        batch.started_at = batch.started_at or now

    elif status in {
        ImportStatus.COMPLETED,
        ImportStatus.COMPLETED_WITH_ERRORS,
        ImportStatus.FAILED,
    }:
        batch.completed_at = now

    elif status == ImportStatus.CANCELLED:
        batch.cancelled_at = now

    if status == ImportStatus.FAILED:
        batch.error_message = error_message

    elif error_message is not None:
        batch.error_message = error_message

    if commit:
        await db.commit()
        await db.refresh(batch)
    else:
        await db.flush()

    return batch


async def update_import_batch_counters(
    db: AsyncSession,
    *,
    batch: ImportBatch,
    total_rows: int | None = None,
    validated_rows: int | None = None,
    processed_rows: int | None = None,
    successful_rows: int | None = None,
    warning_rows: int | None = None,
    failed_rows: int | None = None,
    skipped_rows: int | None = None,
    commit: bool = True,
) -> ImportBatch:
    """Update validated non-negative batch counters."""

    counter_values = {
        "total_rows": total_rows,
        "validated_rows": validated_rows,
        "processed_rows": processed_rows,
        "successful_rows": successful_rows,
        "warning_rows": warning_rows,
        "failed_rows": failed_rows,
        "skipped_rows": skipped_rows,
    }

    for field_name, value in counter_values.items():
        if value is None:
            continue

        if value < 0:
            raise ValueError(
                f"{field_name} cannot be negative",
            )

        setattr(
            batch,
            field_name,
            value,
        )

    if commit:
        await db.commit()
        await db.refresh(batch)
    else:
        await db.flush()

    return batch


async def archive_import_batch(
    db: AsyncSession,
    *,
    batch: ImportBatch,
    archived_by_id: int,
    archive_reason: str | None = None,
    commit: bool = True,
) -> ImportBatch:
    """Archive an import batch while retaining its permanent history."""

    if not batch.is_archived:
        batch.is_archived = True
        batch.archived_at = utc_now()
        batch.archived_by_id = archived_by_id
        batch.archive_reason = archive_reason

    if commit:
        await db.commit()
        await db.refresh(batch)
    else:
        await db.flush()

    return batch


async def restore_import_batch(
    db: AsyncSession,
    *,
    batch: ImportBatch,
    commit: bool = True,
) -> ImportBatch:
    """Restore an archived import batch."""

    batch.is_archived = False
    batch.archived_at = None
    batch.archived_by_id = None
    batch.archive_reason = None

    if commit:
        await db.commit()
        await db.refresh(batch)
    else:
        await db.flush()

    return batch


async def create_import_row(
    db: AsyncSession,
    *,
    payload: ImportRowCreate,
    commit: bool = True,
) -> ImportRow:
    """Create one import row."""

    row = ImportRow(
        **payload.model_dump(),
    )

    db.add(row)

    if commit:
        await db.commit()
        await db.refresh(row)
    else:
        await db.flush()

    return row


async def create_import_rows(
    db: AsyncSession,
    *,
    rows: Sequence[ImportRowCreate],
    commit: bool = True,
) -> list[ImportRow]:
    """Create multiple import rows in one transaction."""

    database_rows = [
        ImportRow(
            **row.model_dump(),
        )
        for row in rows
    ]

    db.add_all(database_rows)

    if commit:
        await db.commit()

        for database_row in database_rows:
            await db.refresh(database_row)
    else:
        await db.flush()

    return database_rows


async def get_import_row(
    db: AsyncSession,
    *,
    row_id: int,
    batch_id: int,
    school_id: int,
    for_update: bool = False,
) -> ImportRow | None:
    """Return one row using school and batch ownership checks."""

    statement = select(ImportRow).where(
        ImportRow.id == row_id,
        ImportRow.batch_id == batch_id,
        ImportRow.school_id == school_id,
    )

    if for_update:
        statement = statement.with_for_update()

    result = await db.execute(statement)

    return result.scalar_one_or_none()


async def get_import_row_by_number(
    db: AsyncSession,
    *,
    batch_id: int,
    school_id: int,
    row_number: int,
    for_update: bool = False,
) -> ImportRow | None:
    """Return one import row by its source-file row number."""

    statement = select(ImportRow).where(
        ImportRow.batch_id == batch_id,
        ImportRow.school_id == school_id,
        ImportRow.row_number == row_number,
    )

    if for_update:
        statement = statement.with_for_update()

    result = await db.execute(statement)

    return result.scalar_one_or_none()


async def list_import_rows(
    db: AsyncSession,
    *,
    batch_id: int,
    school_id: int,
    status: ImportRowStatus | None = None,
    offset: int = 0,
    limit: int = 100,
) -> Sequence[ImportRow]:
    """List rows belonging to one school-scoped batch."""

    safe_offset = max(offset, 0)
    safe_limit = min(
        max(limit, 1),
        500,
    )

    statement = select(ImportRow).where(
        ImportRow.batch_id == batch_id,
        ImportRow.school_id == school_id,
    )

    if status is not None:
        statement = statement.where(
            ImportRow.status == status,
        )

    statement = (
        statement.order_by(
            ImportRow.row_number.asc(),
            ImportRow.id.asc(),
        )
        .offset(safe_offset)
        .limit(safe_limit)
    )

    result = await db.execute(statement)

    return result.scalars().all()


async def count_import_rows(
    db: AsyncSession,
    *,
    batch_id: int,
    school_id: int,
    status: ImportRowStatus | None = None,
) -> int:
    """Count rows belonging to one school-scoped import batch."""

    statement = select(
        func.count(ImportRow.id),
    ).where(
        ImportRow.batch_id == batch_id,
        ImportRow.school_id == school_id,
    )

    if status is not None:
        statement = statement.where(
            ImportRow.status == status,
        )

    result = await db.execute(statement)

    return int(result.scalar_one())


async def count_import_rows_by_status(
    db: AsyncSession,
    *,
    batch_id: int,
    school_id: int,
) -> dict[ImportRowStatus, int]:
    """Return row totals grouped by status for one import batch."""

    statement = (
        select(
            ImportRow.status,
            func.count(ImportRow.id),
        )
        .where(
            ImportRow.batch_id == batch_id,
            ImportRow.school_id == school_id,
        )
        .group_by(ImportRow.status)
    )

    result = await db.execute(statement)

    return {row_status: int(count) for row_status, count in result.all()}


async def update_import_row(
    db: AsyncSession,
    *,
    row: ImportRow,
    payload: ImportRowUpdate,
    commit: bool = True,
) -> ImportRow:
    """Update one import row."""

    update_data = payload.model_dump(
        exclude_unset=True,
    )

    for field_name, value in update_data.items():
        setattr(
            row,
            field_name,
            value,
        )

    if commit:
        await db.commit()
        await db.refresh(row)
    else:
        await db.flush()

    return row


async def set_import_row_result(
    db: AsyncSession,
    *,
    row: ImportRow,
    status: ImportRowStatus,
    normalised_data: dict[str, Any] | None = None,
    validation_errors: list[Any] | None = None,
    validation_warnings: list[Any] | None = None,
    entity_type: str | None = None,
    created_entity_id: int | None = None,
    error_message: str | None = None,
    increment_attempt: bool = False,
    commit: bool = True,
) -> ImportRow:
    """Store a validation or processing result for one import row."""

    row.status = status

    if normalised_data is not None:
        row.normalised_data = normalised_data

    if validation_errors is not None:
        row.validation_errors = validation_errors

    if validation_warnings is not None:
        row.validation_warnings = validation_warnings

    if entity_type is not None:
        row.entity_type = entity_type

    if created_entity_id is not None:
        row.created_entity_id = created_entity_id

    row.error_message = error_message

    if increment_attempt:
        row.attempt_count += 1

    if status in {
        ImportRowStatus.IMPORTED,
        ImportRowStatus.UPDATED,
        ImportRowStatus.SKIPPED,
        ImportRowStatus.FAILED,
    }:
        row.processed_at = utc_now()

    if commit:
        await db.commit()
        await db.refresh(row)
    else:
        await db.flush()

    return row


async def count_retryable_rows(
    db: AsyncSession,
    *,
    batch_id: int,
    school_id: int,
) -> int:
    """
    Count processing failures that are eligible for retry.

    Validation-invalid rows are excluded because they must be corrected and
    validated before they can enter the processing pipeline.
    """

    statement = select(
        func.count(ImportRow.id),
    ).where(
        ImportRow.batch_id == batch_id,
        ImportRow.school_id == school_id,
        ImportRow.status == ImportRowStatus.FAILED,
    )

    result = await db.execute(statement)

    return int(result.scalar_one())


async def reset_rows_for_retry(
    db: AsyncSession,
    *,
    batch_id: int,
    school_id: int,
    commit: bool = True,
) -> int:
    """
    Reset failed processing rows so they can be processed again.

    The rows return to ``VALID`` because validation has already succeeded.
    Attempt counts and validation information are retained as audit history.
    Successfully imported, updated and skipped rows remain unchanged.
    """

    statement = (
        select(ImportRow)
        .where(
            ImportRow.batch_id == batch_id,
            ImportRow.school_id == school_id,
            ImportRow.status == ImportRowStatus.FAILED,
        )
        .order_by(
            ImportRow.row_number.asc(),
            ImportRow.id.asc(),
        )
        .with_for_update()
    )

    result = await db.execute(statement)
    rows = result.scalars().all()

    for row in rows:
        row.status = ImportRowStatus.VALID
        row.error_message = None
        row.processed_at = None
        row.created_entity_id = None
        row.entity_type = None

    if commit:
        await db.commit()
    else:
        await db.flush()

    return len(rows)


async def retry_failed_rows(
    db: AsyncSession,
    *,
    batch: ImportBatch,
    commit: bool = True,
) -> int:
    """
    Prepare a batch's failed processing rows for another attempt.

    Returns the number of reset rows.

    This operation preserves:

    - successful imported or updated rows;
    - skipped rows;
    - validation results;
    - row attempt counts;
    - source data and normalised data.
    """

    if batch.is_archived:
        raise ValueError(
            "Archived import batches cannot be retried.",
        )

    retry_count = await reset_rows_for_retry(
        db,
        batch_id=batch.id,
        school_id=batch.school_id,
        commit=False,
    )

    if retry_count == 0:
        raise ValueError(
            "This import batch does not contain any failed rows.",
        )

    batch.status = ImportStatus.READY
    batch.current_stage = "ready_for_retry"

    batch.processed_rows = max(
        batch.processed_rows - retry_count,
        0,
    )

    batch.failed_rows = max(
        batch.failed_rows - retry_count,
        0,
    )

    batch.error_message = None
    batch.result_summary = {}

    batch.queued_at = None
    batch.started_at = None
    batch.completed_at = None
    batch.cancelled_at = None

    if commit:
        await db.commit()
        await db.refresh(batch)
    else:
        await db.flush()

    return retry_count


async def delete_import_rows_for_batch(
    db: AsyncSession,
    *,
    batch_id: int,
    school_id: int,
    commit: bool = True,
) -> int:
    """
    Delete all rows belonging to one batch.

    This is intended for rebuilding a batch before processing begins.
    Permanent completed import history should normally be retained.
    """

    statement = select(ImportRow).where(
        ImportRow.batch_id == batch_id,
        ImportRow.school_id == school_id,
    )

    result = await db.execute(statement)
    rows = result.scalars().all()

    for row in rows:
        await db.delete(row)

    if commit:
        await db.commit()
    else:
        await db.flush()

    return len(rows)
