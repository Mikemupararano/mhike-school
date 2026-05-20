from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.permissions import PermissionService
from app.db.session import get_db
from app.models.user import User
from app.schemas.notification_preferences import (
    NotificationPreferenceOut,
    NotificationPreferenceUpdate,
)
from app.services.notification_preferences_service import (
    NotificationPreferencesService,
)

router = APIRouter(tags=["Notification Preferences"])


@router.get(
    "/me",
    response_model=NotificationPreferenceOut,
)
async def get_my_notification_preferences(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    PermissionService.ensure_active_user(current_user)

    service = NotificationPreferencesService(db)

    return await service.get_or_create_for_user(
        school_id=current_user.school_id,
        user_id=current_user.id,
    )


@router.patch(
    "/me",
    response_model=NotificationPreferenceOut,
)
async def update_my_notification_preferences(
    payload: NotificationPreferenceUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    PermissionService.ensure_active_user(current_user)

    service = NotificationPreferencesService(db)

    return await service.update_for_user(
        school_id=current_user.school_id,
        user_id=current_user.id,
        payload=payload,
    )
