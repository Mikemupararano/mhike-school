from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.notification_preference import NotificationPreference
from app.models.user import User
from app.schemas.notification_preference import (
    NotificationPreferenceResponse,
    NotificationPreferenceUpdate,
)

router = APIRouter()


async def get_existing_preferences(
    db: AsyncSession,
    user_id: int,
) -> NotificationPreference | None:
    result = await db.execute(
        select(NotificationPreference)
        .where(NotificationPreference.user_id == user_id)
        .limit(1)
    )

    return result.scalar_one_or_none()


def ensure_user_has_school(current_user: User) -> None:
    if current_user.school_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is not assigned to a school.",
        )


@router.get(
    "/me",
    response_model=NotificationPreferenceResponse,
)
async def get_my_preferences(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ensure_user_has_school(current_user)

    preferences = await get_existing_preferences(
        db=db,
        user_id=current_user.id,
    )

    if preferences is None:
        preferences = NotificationPreference(
            school_id=current_user.school_id,
            user_id=current_user.id,
        )

        db.add(preferences)
        await db.commit()
        await db.refresh(preferences)

    return preferences


@router.patch(
    "/me",
    response_model=NotificationPreferenceResponse,
)
async def update_my_preferences(
    payload: NotificationPreferenceUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ensure_user_has_school(current_user)

    preferences = await get_existing_preferences(
        db=db,
        user_id=current_user.id,
    )

    if preferences is None:
        preferences = NotificationPreference(
            school_id=current_user.school_id,
            user_id=current_user.id,
        )

        db.add(preferences)
        await db.flush()

    update_data = payload.model_dump(
        exclude_unset=True,
    )

    for field, value in update_data.items():
        setattr(preferences, field, value)

    await db.commit()
    await db.refresh(preferences)

    return preferences
