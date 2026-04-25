from __future__ import annotations

import asyncio
import logging

from app.db.session import async_session_maker
from app.services.gdpr_service import GDPRService

logger = logging.getLogger(__name__)


async def run_gdpr_retention_job() -> None:
    async with async_session_maker() as db:
        anonymised_count = await GDPRService.anonymise_expired_users(db)
        await db.commit()

    logger.info("GDPR retention job completed. anonymised_count=%s", anonymised_count)


async def run_worker_loop(interval_seconds: int = 3600) -> None:
    """
    Simple async worker loop.

    Runs GDPR retention once per interval.
    For production, this can later be replaced with Celery, APScheduler,
    Dramatiq, or a managed cron job.
    """
    logger.info("Worker started. interval_seconds=%s", interval_seconds)

    while True:
        try:
            await run_gdpr_retention_job()
        except Exception:
            logger.exception("GDPR retention job failed.")

        await asyncio.sleep(interval_seconds)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_worker_loop())
