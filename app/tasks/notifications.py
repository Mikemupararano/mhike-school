from __future__ import annotations

import asyncio
from datetime import UTC, datetime

from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.models.notification_delivery import NotificationDelivery
from app.tasks.celery_app import celery


@celery.task(
    name="notifications.process_delivery",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def process_notification_delivery(self, delivery_id: int) -> None:
    try:
        asyncio.run(_process_notification_delivery(delivery_id))
    except Exception as exc:
        raise self.retry(exc=exc) from exc


async def _process_notification_delivery(delivery_id: int) -> None:
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(NotificationDelivery).where(
                NotificationDelivery.id == delivery_id,
            )
        )

        delivery = result.scalar_one_or_none()

        if delivery is None:
            return

        delivery.attempts += 1
        delivery.last_attempted_at = datetime.now(UTC)

        try:
            await _dispatch_delivery(delivery)

            delivery.status = "sent"
            delivery.delivered_at = datetime.now(UTC)
            delivery.error_message = None
        except Exception as exc:
            delivery.status = "failed"
            delivery.error_message = str(exc)

        await db.commit()


async def _dispatch_delivery(delivery: NotificationDelivery) -> None:
    if delivery.channel == "email":
        await _send_email(delivery)
        return

    if delivery.channel == "push":
        await _send_push(delivery)
        return

    if delivery.channel == "sms":
        await _send_sms(delivery)
        return

    raise ValueError(f"Unsupported notification channel: {delivery.channel}")


async def _send_email(delivery: NotificationDelivery) -> None:
    await asyncio.sleep(1)
    print(f"[EMAIL SENT] Delivery {delivery.id}")


async def _send_push(delivery: NotificationDelivery) -> None:
    await asyncio.sleep(1)
    print(f"[PUSH SENT] Delivery {delivery.id}")


async def _send_sms(delivery: NotificationDelivery) -> None:
    await asyncio.sleep(1)
    print(f"[SMS SENT] Delivery {delivery.id}")
