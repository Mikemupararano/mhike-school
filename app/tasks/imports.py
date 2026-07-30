from __future__ import annotations

import asyncio
import logging
from typing import Any

from sqlalchemy.exc import OperationalError

from app.db.session import AsyncSessionLocal
from app.imports.registry import get_import_handler
from app.models.import_batch import ImportStatus
from app.repositories.import_batches import (
    get_import_batch,
    set_import_batch_status,
)
from app.services.import_service import validate_import_batch
from app.tasks.celery_app import celery

logger = logging.getLogger(__name__)


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
