from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.user import User, UserRole
from app.schemas.notification import (
    NotificationCreate,
    NotificationMetricsOut,
    NotificationOut,
)
from app.services.notification_service import NotificationService

router = APIRouter()


def _has_role(user: User, role: UserRole) -> bool:
    return role.value in set(user.roles)


def _require_platform_admin(user: User) -> None:
    if not _has_role(user, UserRole.PLATFORM_ADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only platform administrators can access this resource.",
        )


@router.post(
    "",
    response_model=NotificationOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_notification(
    payload: NotificationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> NotificationOut:
    is_platform_admin = _has_role(current_user, UserRole.PLATFORM_ADMIN)
    is_school_admin = _has_role(current_user, UserRole.SCHOOL_ADMIN)

    if not is_platform_admin and not is_school_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to create notifications.",
        )

    school_id = payload.school_id

    if is_school_admin:
        if current_user.school_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User is not linked to a school.",
            )

        school_id = current_user.school_id

    service = NotificationService(db)

    return await service.create_notification(
        school_id=school_id,
        user_id=payload.user_id,
        title=payload.title,
        message=payload.message,
        category=payload.category,
        priority=payload.priority,
        email_enabled=payload.email_enabled,
        push_enabled=payload.push_enabled,
        sms_enabled=payload.sms_enabled,
    )


@router.get(
    "/me",
    response_model=list[NotificationOut],
)
async def get_my_notifications(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[NotificationOut]:
    service = NotificationService(db)

    return await service.get_user_notifications(
        user_id=current_user.id,
    )


@router.patch(
    "/{notification_id}/read",
    response_model=NotificationOut,
)
async def mark_notification_read(
    notification_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> NotificationOut:
    service = NotificationService(db)

    notification = await service.mark_as_read(
        notification_id=notification_id,
        user_id=current_user.id,
    )

    if notification is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found.",
        )

    return notification


@router.get(
    "/admin/metrics",
    response_model=NotificationMetricsOut,
)
async def get_notification_metrics(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> NotificationMetricsOut:
    _require_platform_admin(current_user)

    service = NotificationService(db)

    return await service.get_delivery_metrics()


@router.get("/admin/activity")
async def get_notification_activity(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[dict]:
    _require_platform_admin(current_user)

    service = NotificationService(db)

    return await service.get_recent_delivery_activity()
