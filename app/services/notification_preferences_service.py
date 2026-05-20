from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification_preferences import NotificationPreference
from app.schemas.notification_preferences import (
    NotificationPreferenceUpdate,
)


class NotificationPreferencesService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_or_create_for_user(
        self,
        school_id: int | None,
        user_id: int,
    ) -> NotificationPreference:
        if school_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User is not linked to a school.",
            )

        result = await self.db.execute(
            select(NotificationPreference).where(
                NotificationPreference.school_id == school_id,
                NotificationPreference.user_id == user_id,
            )
        )

        preferences = result.scalar_one_or_none()

        if preferences is not None:
            return preferences

        preferences = NotificationPreference(
            school_id=school_id,
            user_id=user_id,
        )

        self.db.add(preferences)
        await self.db.commit()
        await self.db.refresh(preferences)

        return preferences

    async def update_for_user(
        self,
        school_id: int | None,
        user_id: int,
        payload: NotificationPreferenceUpdate,
    ) -> NotificationPreference:
        preferences = await self.get_or_create_for_user(
            school_id=school_id,
            user_id=user_id,
        )

        update_data = payload.model_dump()

        for field, value in update_data.items():
            setattr(preferences, field, value)

        self.db.add(preferences)

        await self.db.commit()
        await self.db.refresh(preferences)

        return preferences
