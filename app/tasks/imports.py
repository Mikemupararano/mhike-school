from __future__ import annotations

import asyncio
import logging
from typing import Any

from sqlalchemy.exc import OperationalError

from app.db.session import AsyncSessionLocal
from app.imports.registry import (
    RowProcessingAction,
    RowProcessingResult,
    get_import_handler,
)
from app.models.import_batch import (
    ImportRowStatus,
    ImportStatus,
)
from app.repositories.import_batches import (
    count_import_rows_by_status,
    get_import_batch,
    get_import_row,
    list_import_rows,
    set_import_batch_status,
    set_import_row_result,
    update_import_batch_counters,
)
from app.services.import_service import validate_import_batch
from app.tasks.celery_app import celery

logger = logging.getLogger(__name__)

PROCESSABLE_ROW_STATUSES = (
    ImportRowStatus.VALID,
    ImportRowStatus.WARNING,
    ImportRowStatus.QUEUED,
    ImportRowStatus.PROCESSING,
)

FINISHED_BATCH_STATUSES = {
    ImportStatus.COMPLETED,
    ImportStatus.COMPLETED_WITH_ERRORS,
    ImportStatus.FAILED,
}


class ImportBatchNotFoundError(LookupError):
    """Raised when a school-scoped import batch cannot be found."""


def _normalise_import_type(value: Any) -> str:
    """
    Convert an import-type enum or string into the registry key.

    ImportBatch.import_type may be stored as either a string or a
    string-backed Enum, so this helper safely supports both.
    """

    enum_value = getattr(value, "value", value)

    if not isinstance(enum_value, str):
        raise TypeError(
            "Import batch import_type must be a string or string-backed enum."
        )

    normalised = enum_value.strip().lower()

    if not normalised:
        raise ValueError("Import batch import_type cannot be blank.")

    return normalised


def _result_to_row_status(
    result: RowProcessingResult,
) -> ImportRowStatus:
    """Map a processor result onto the permanent import-row status."""

    if result.action == RowProcessingAction.CREATED:
        return ImportRowStatus.IMPORTED

    if result.action == RowProcessingAction.UPDATED:
        return ImportRowStatus.UPDATED

    if result.action == RowProcessingAction.SKIPPED:
        return ImportRowStatus.SKIPPED

    raise ValueError(f"Unsupported row processing action: {result.action!r}")


@celery.task(
    name="imports.validate_batch",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def validate_import_batch_task(
    self,
    batch_id: int,
    school_id: int,
) -> dict[str, Any]:
    """
    Validate all staged rows belonging to an import batch.

    The Celery task remains synchronous and enters the application's
    asynchronous SQLAlchemy layer through asyncio.run(), matching the
    existing notification-task pattern.
    """

    try:
        return asyncio.run(
            _validate_import_batch_task(
                batch_id=batch_id,
                school_id=school_id,
            )
        )
    except OperationalError as exc:
        logger.exception(
            "Transient database error while validating import batch. "
            "batch_id=%s school_id=%s",
            batch_id,
            school_id,
        )
        raise self.retry(exc=exc) from exc


async def _validate_import_batch_task(
    *,
    batch_id: int,
    school_id: int,
) -> dict[str, Any]:
    """
    Async implementation of the import-batch validation task.

    Workflow:

        load and lock batch
        resolve registered handler
        validate staged rows
        return validation summary
    """

    async with AsyncSessionLocal() as db:
        batch = await get_import_batch(
            db,
            batch_id=batch_id,
            school_id=school_id,
            include_archived=False,
            for_update=True,
        )

        if batch is None:
            raise ImportBatchNotFoundError(
                f"Import batch {batch_id} was not found for school {school_id}."
            )

        if batch.status == ImportStatus.CANCELLED:
            logger.info(
                "Skipping cancelled import batch. batch_id=%s school_id=%s",
                batch_id,
                school_id,
            )
            return {
                "batch_id": batch_id,
                "school_id": school_id,
                "status": ImportStatus.CANCELLED.value,
                "skipped": True,
                "reason": "Batch has been cancelled.",
            }

        import_type = _normalise_import_type(batch.import_type)

        try:
            handler = get_import_handler(import_type)
        except KeyError as exc:
            error_message = str(exc)

            await set_import_batch_status(
                db,
                batch=batch,
                status=ImportStatus.FAILED,
                current_stage="handler_resolution_failed",
                error_message=error_message,
                commit=True,
            )

            logger.error(
                "No handler registered for import batch. "
                "batch_id=%s school_id=%s import_type=%s",
                batch_id,
                school_id,
                import_type,
            )

            raise

        logger.info(
            "Validating import batch. " "batch_id=%s school_id=%s import_type=%s",
            batch_id,
            school_id,
            import_type,
        )

        summary = await validate_import_batch(
            db,
            batch=batch,
            validator=handler.validator,
            commit=True,
        )

        logger.info(
            "Import batch validation completed. "
            "batch_id=%s school_id=%s total_rows=%s "
            "valid_rows=%s invalid_rows=%s warning_rows=%s",
            batch_id,
            school_id,
            summary.total_rows,
            summary.valid_rows,
            summary.invalid_rows,
            summary.warning_rows,
        )

        return {
            "batch_id": batch.id,
            "school_id": batch.school_id,
            "import_type": import_type,
            "status": batch.status.value,
            "total_rows": summary.total_rows,
            "valid_rows": summary.valid_rows,
            "invalid_rows": summary.invalid_rows,
            "warning_rows": summary.warning_rows,
        }


@celery.task(
    name="imports.process_batch",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def process_import_batch_task(
    self,
    batch_id: int,
    school_id: int,
) -> dict[str, Any]:
    """
    Process all validated rows belonging to an import batch.

    Database connectivity failures are retried by Celery. Ordinary row-level
    processing failures are retained against the affected row and do not stop
    the remaining rows from being processed.
    """

    try:
        return asyncio.run(
            _process_import_batch_task(
                batch_id=batch_id,
                school_id=school_id,
            )
        )
    except OperationalError as exc:
        logger.exception(
            "Transient database error while processing import batch. "
            "batch_id=%s school_id=%s",
            batch_id,
            school_id,
        )
        raise self.retry(exc=exc) from exc


async def _list_processable_row_ids(
    *,
    batch_id: int,
    school_id: int,
) -> list[int]:
    """
    Return IDs for rows eligible for processing.

    Rows are collected before processing begins so pagination is not affected
    as row statuses change.
    """

    row_ids: list[int] = []

    async with AsyncSessionLocal() as db:
        for status in PROCESSABLE_ROW_STATUSES:
            offset = 0

            while True:
                rows = await list_import_rows(
                    db,
                    batch_id=batch_id,
                    school_id=school_id,
                    status=status,
                    offset=offset,
                    limit=500,
                )

                if not rows:
                    break

                row_ids.extend(row.id for row in rows)
                offset += len(rows)

                if len(rows) < 500:
                    break

    return row_ids


async def _mark_row_failed(
    *,
    row_id: int,
    batch_id: int,
    school_id: int,
    error_message: str,
) -> None:
    """Persist a row-level processing failure in a fresh transaction."""

    async with AsyncSessionLocal() as db:
        row = await get_import_row(
            db,
            row_id=row_id,
            batch_id=batch_id,
            school_id=school_id,
            for_update=True,
        )

        if row is None:
            logger.error(
                "Could not record failed import row because it disappeared. "
                "row_id=%s batch_id=%s school_id=%s",
                row_id,
                batch_id,
                school_id,
            )
            return

        await set_import_row_result(
            db,
            row=row,
            status=ImportRowStatus.FAILED,
            error_message=error_message,
            increment_attempt=True,
            commit=True,
        )


async def _process_one_import_row(
    *,
    row_id: int,
    batch_id: int,
    school_id: int,
    import_type: str,
    processor: Any,
) -> ImportRowStatus | None:
    """
    Process one row in its own database transaction.

    A separate transaction per row prevents one invalid record from rolling
    back successful records already processed from the same batch.
    """

    try:
        async with AsyncSessionLocal() as db:
            row = await get_import_row(
                db,
                row_id=row_id,
                batch_id=batch_id,
                school_id=school_id,
                for_update=True,
            )

            if row is None:
                logger.warning(
                    "Skipping missing import row. "
                    "row_id=%s batch_id=%s school_id=%s",
                    row_id,
                    batch_id,
                    school_id,
                )
                return None

            if row.status not in PROCESSABLE_ROW_STATUSES:
                logger.info(
                    "Skipping import row with non-processable status. "
                    "row_id=%s batch_id=%s status=%s",
                    row.id,
                    batch_id,
                    row.status.value,
                )
                return row.status

            row.status = ImportRowStatus.PROCESSING
            row.attempt_count += 1
            row.error_message = None

            await db.flush()

            import_data = dict(row.normalised_data or row.original_data or {})

            result = await processor(
                db,
                import_data,
                school_id,
            )

            if not isinstance(result, RowProcessingResult):
                raise TypeError("Import processors must return RowProcessingResult.")

            final_status = _result_to_row_status(result)

            await set_import_row_result(
                db,
                row=row,
                status=final_status,
                entity_type=import_type,
                created_entity_id=result.entity_id,
                error_message=result.message,
                increment_attempt=False,
                commit=True,
            )

            logger.info(
                "Import row processed. "
                "row_id=%s batch_id=%s school_id=%s status=%s entity_id=%s",
                row_id,
                batch_id,
                school_id,
                final_status.value,
                result.entity_id,
            )

            return final_status

    except OperationalError:
        raise

    except Exception as exc:
        error_message = str(exc) or exc.__class__.__name__

        logger.exception(
            "Import row processing failed. " "row_id=%s batch_id=%s school_id=%s",
            row_id,
            batch_id,
            school_id,
        )

        await _mark_row_failed(
            row_id=row_id,
            batch_id=batch_id,
            school_id=school_id,
            error_message=error_message,
        )

        return ImportRowStatus.FAILED


async def _finalise_import_batch(
    *,
    batch_id: int,
    school_id: int,
    import_type: str,
) -> dict[str, Any]:
    """Recalculate counters and set the batch's terminal workflow status."""

    async with AsyncSessionLocal() as db:
        batch = await get_import_batch(
            db,
            batch_id=batch_id,
            school_id=school_id,
            include_archived=False,
            for_update=True,
        )

        if batch is None:
            raise ImportBatchNotFoundError(
                f"Import batch {batch_id} was not found for school {school_id}."
            )

        counts = await count_import_rows_by_status(
            db,
            batch_id=batch_id,
            school_id=school_id,
        )

        imported_rows = counts.get(ImportRowStatus.IMPORTED, 0)
        updated_rows = counts.get(ImportRowStatus.UPDATED, 0)
        skipped_rows = counts.get(ImportRowStatus.SKIPPED, 0)
        processing_failed_rows = counts.get(ImportRowStatus.FAILED, 0)
        invalid_rows = counts.get(ImportRowStatus.INVALID, 0)

        successful_rows = imported_rows + updated_rows
        failed_rows = invalid_rows + processing_failed_rows

        processed_rows = successful_rows + skipped_rows + failed_rows

        final_status = (
            ImportStatus.COMPLETED_WITH_ERRORS
            if failed_rows > 0
            else ImportStatus.COMPLETED
        )

        batch.result_summary = {
            "import_type": import_type,
            "imported_rows": imported_rows,
            "updated_rows": updated_rows,
            "skipped_rows": skipped_rows,
            "invalid_rows": invalid_rows,
            "processing_failed_rows": processing_failed_rows,
            "successful_rows": successful_rows,
            "failed_rows": failed_rows,
            "processed_rows": processed_rows,
        }

        await update_import_batch_counters(
            db,
            batch=batch,
            processed_rows=processed_rows,
            successful_rows=successful_rows,
            failed_rows=failed_rows,
            skipped_rows=skipped_rows,
            commit=False,
        )

        await set_import_batch_status(
            db,
            batch=batch,
            status=final_status,
            current_stage=final_status.value,
            error_message=None,
            commit=True,
        )

        return {
            "batch_id": batch.id,
            "school_id": batch.school_id,
            "import_type": import_type,
            "status": final_status.value,
            "total_rows": batch.total_rows,
            "processed_rows": processed_rows,
            "successful_rows": successful_rows,
            "imported_rows": imported_rows,
            "updated_rows": updated_rows,
            "skipped_rows": skipped_rows,
            "invalid_rows": invalid_rows,
            "failed_rows": failed_rows,
        }


async def _process_import_batch_task(
    *,
    batch_id: int,
    school_id: int,
) -> dict[str, Any]:
    """
    Async implementation of the generic import processing task.

    Workflow:

        load and lock batch
        resolve registered handler
        mark batch as processing
        process each eligible row independently
        recalculate counters
        mark batch completed or completed-with-errors
    """

    async with AsyncSessionLocal() as db:
        batch = await get_import_batch(
            db,
            batch_id=batch_id,
            school_id=school_id,
            include_archived=False,
            for_update=True,
        )

        if batch is None:
            raise ImportBatchNotFoundError(
                f"Import batch {batch_id} was not found for school {school_id}."
            )

        if batch.status == ImportStatus.CANCELLED:
            logger.info(
                "Skipping cancelled import batch. batch_id=%s school_id=%s",
                batch_id,
                school_id,
            )
            return {
                "batch_id": batch_id,
                "school_id": school_id,
                "status": ImportStatus.CANCELLED.value,
                "skipped": True,
                "reason": "Batch has been cancelled.",
            }

        if batch.status in FINISHED_BATCH_STATUSES:
            logger.info(
                "Skipping finished import batch. " "batch_id=%s school_id=%s status=%s",
                batch_id,
                school_id,
                batch.status.value,
            )
            return {
                "batch_id": batch_id,
                "school_id": school_id,
                "status": batch.status.value,
                "skipped": True,
                "reason": "Batch has already finished.",
            }

        import_type = _normalise_import_type(batch.import_type)

        try:
            handler = get_import_handler(import_type)
        except KeyError as exc:
            error_message = str(exc)

            await set_import_batch_status(
                db,
                batch=batch,
                status=ImportStatus.FAILED,
                current_stage="handler_resolution_failed",
                error_message=error_message,
                commit=True,
            )

            logger.error(
                "No handler registered for import batch. "
                "batch_id=%s school_id=%s import_type=%s",
                batch_id,
                school_id,
                import_type,
            )

            raise

        await set_import_batch_status(
            db,
            batch=batch,
            status=ImportStatus.PROCESSING,
            current_stage="processing_rows",
            error_message=None,
            commit=True,
        )

        processor = handler.processor

    row_ids = await _list_processable_row_ids(
        batch_id=batch_id,
        school_id=school_id,
    )

    logger.info(
        "Processing import batch. "
        "batch_id=%s school_id=%s import_type=%s row_count=%s",
        batch_id,
        school_id,
        import_type,
        len(row_ids),
    )

    for row_id in row_ids:
        await _process_one_import_row(
            row_id=row_id,
            batch_id=batch_id,
            school_id=school_id,
            import_type=import_type,
            processor=processor,
        )

    summary = await _finalise_import_batch(
        batch_id=batch_id,
        school_id=school_id,
        import_type=import_type,
    )

    logger.info(
        "Import batch processing completed. "
        "batch_id=%s school_id=%s status=%s "
        "processed_rows=%s successful_rows=%s failed_rows=%s",
        batch_id,
        school_id,
        summary["status"],
        summary["processed_rows"],
        summary["successful_rows"],
        summary["failed_rows"],
    )

    return summary
