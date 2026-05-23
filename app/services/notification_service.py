from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.notification import Notification
from app.models.notification_delivery import NotificationDelivery
from app.models.notification_preference import NotificationPreference
from app.tasks.notifications import process_notification_delivery


class NotificationService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_notification(
        self,
        *,
        school_id: int | None,
        user_id: int | None,
        title: str,
        message: str,
        category: str = "general",
        priority: str = "normal",
        email_enabled: bool = False,
        push_enabled: bool = True,
        sms_enabled: bool = False,
    ) -> Notification:
        notification = Notification(
            school_id=school_id,
            user_id=user_id,
            title=title,
            message=message,
            category=category,
            priority=priority,
            email_enabled=email_enabled,
            push_enabled=push_enabled,
            sms_enabled=sms_enabled,
            is_read=False,
        )

        self.db.add(notification)
        await self.db.flush()

        preferences: NotificationPreference | None = None

        if user_id is not None:
            preference_result = await self.db.execute(
                select(NotificationPreference).where(
                    NotificationPreference.user_id == user_id,
                )
            )

            preferences = preference_result.scalar_one_or_none()

        delivery_channels: list[str] = []

        if email_enabled and (preferences is None or preferences.email_enabled):
            delivery_channels.append("email")

        if push_enabled and (preferences is None or preferences.push_enabled):
            delivery_channels.append("push")

        if sms_enabled and (preferences is None or preferences.sms_enabled):
            delivery_channels.append("sms")

        delivery_ids: list[int] = []

        for channel in delivery_channels:
            delivery = NotificationDelivery(
                notification_id=notification.id,
                channel=channel,
                status="pending",
                attempts=0,
            )

            self.db.add(delivery)
            await self.db.flush()

            delivery_ids.append(delivery.id)

        await self.db.commit()
        await self.db.refresh(notification)

        for delivery_id in delivery_ids:
            process_notification_delivery.delay(delivery_id)

        return notification

    async def get_user_notifications(
        self,
        *,
        user_id: int,
        limit: int = 50,
    ) -> list[Notification]:
        result = await self.db.execute(
            select(Notification)
            .where(Notification.user_id == user_id)
            .order_by(Notification.created_at.desc())
            .limit(limit)
        )

        return list(result.scalars().all())

    async def mark_as_read(
        self,
        *,
        notification_id: int,
        user_id: int,
    ) -> Notification | None:
        result = await self.db.execute(
            select(Notification).where(
                Notification.id == notification_id,
                Notification.user_id == user_id,
            )
        )

        notification = result.scalar_one_or_none()

        if notification is None:
            return None

        notification.is_read = True
        notification.read_at = datetime.now(UTC)

        await self.db.commit()
        await self.db.refresh(notification)

        return notification

    async def mark_delivery_sent(
        self,
        *,
        delivery_id: int,
        provider_message_id: str | None = None,
    ) -> NotificationDelivery | None:
        result = await self.db.execute(
            select(NotificationDelivery).where(
                NotificationDelivery.id == delivery_id,
            )
        )

        delivery = result.scalar_one_or_none()

        if delivery is None:
            return None

        delivery.status = "sent"
        delivery.provider_message_id = provider_message_id
        delivery.delivered_at = datetime.now(UTC)
        delivery.last_attempted_at = datetime.now(UTC)

        await self.db.commit()
        await self.db.refresh(delivery)

        return delivery

    async def mark_delivery_failed(
        self,
        *,
        delivery_id: int,
        error_message: str,
    ) -> NotificationDelivery | None:
        result = await self.db.execute(
            select(NotificationDelivery).where(
                NotificationDelivery.id == delivery_id,
            )
        )

        delivery = result.scalar_one_or_none()

        if delivery is None:
            return None

        delivery.status = "failed"
        delivery.error_message = error_message
        delivery.attempts += 1
        delivery.last_attempted_at = datetime.now(UTC)

        await self.db.commit()
        await self.db.refresh(delivery)

        return delivery

    async def get_delivery_metrics(self) -> dict:
        total_result = await self.db.execute(
            select(func.count(NotificationDelivery.id))
        )

        sent_result = await self.db.execute(
            select(func.count(NotificationDelivery.id)).where(
                NotificationDelivery.status == "sent",
            )
        )

        failed_result = await self.db.execute(
            select(func.count(NotificationDelivery.id)).where(
                NotificationDelivery.status == "failed",
            )
        )

        pending_result = await self.db.execute(
            select(func.count(NotificationDelivery.id)).where(
                NotificationDelivery.status == "pending",
            )
        )

        return {
            "total_deliveries": total_result.scalar_one(),
            "sent_deliveries": sent_result.scalar_one(),
            "failed_deliveries": failed_result.scalar_one(),
            "pending_deliveries": pending_result.scalar_one(),
        }

    async def get_recent_delivery_activity(
        self,
        limit: int = 25,
    ) -> list[dict]:
        result = await self.db.execute(
            select(NotificationDelivery)
            .options(selectinload(NotificationDelivery.notification))
            .order_by(NotificationDelivery.created_at.desc())
            .limit(limit)
        )

        deliveries = list(result.scalars().all())

        return [
            {
                "id": delivery.id,
                "channel": delivery.channel,
                "status": delivery.status,
                "attempts": delivery.attempts,
                "error_message": delivery.error_message,
                "created_at": delivery.created_at,
                "delivered_at": delivery.delivered_at,
                "notification_title": (
                    delivery.notification.title if delivery.notification else None
                ),
                "school_id": (
                    delivery.notification.school_id if delivery.notification else None
                ),
            }
            for delivery in deliveries
        ]
