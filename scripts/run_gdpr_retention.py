from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT_DIR))

from app.db.session import async_session_maker
from app.services.gdpr_service import GDPRService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main() -> None:
    async with async_session_maker() as db:
        anonymised_count = await GDPRService.anonymise_expired_users(db)
        await db.commit()

    logger.info("GDPR retention job completed. anonymised_count=%s", anonymised_count)


if __name__ == "__main__":
    asyncio.run(main())
