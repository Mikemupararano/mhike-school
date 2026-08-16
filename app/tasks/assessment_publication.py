from __future__ import annotations

import asyncio
import logging

from app.db.session import TaskAsyncSessionLocal as AsyncSessionLocal
from app.services.assessment_result_publication_service import (
    publish_due_scheduled_results,
)
from app.tasks.celery_app import celery

logger = logging.getLogger(__name__)


@celery.task(
    name="assessments.publish_due_scheduled_results",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def publish_due_assessment_results(
    self,
) -> int:
    """
    Publish assessment-result releases whose scheduled time has arrived.

    The Celery task remains synchronous and enters the application's
    asynchronous SQLAlchemy layer through ``asyncio.run()``.

    The publication service owns the domain transaction, including the
    transition to PUBLISHED and post-commit publication notifications.

    Returns the number of scheduled publications successfully published.
    """

    try:
        return asyncio.run(
            _publish_due_assessment_results(),
        )
    except Exception as exc:
        logger.exception(
            "Scheduled assessment-result publication task failed.",
        )

        raise self.retry(
            exc=exc,
        ) from exc


async def _publish_due_assessment_results() -> int:
    """
    Run one scheduled-publication sweep.

    A task-specific non-pooled database session is used because Celery task
    invocations may execute through separate asyncio event loops.
    """

    async with AsyncSessionLocal() as db:
        published = await publish_due_scheduled_results(
            db,
        )

    published_count = len(
        published,
    )

    logger.info(
        "Scheduled assessment-result publication sweep completed. "
        "published_count=%s",
        published_count,
    )

    return published_count
