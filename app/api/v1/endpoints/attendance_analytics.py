from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.permissions import PermissionService
from app.db.session import get_db
from app.models.user import User
from app.schemas.attendance_analytics import AttendanceAnalyticsSummary
from app.services.attendance_analytics_service import AttendanceAnalyticsService

router = APIRouter(tags=["Attendance Analytics"])


@router.get("/summary", response_model=AttendanceAnalyticsSummary)
async def get_attendance_analytics_summary(
    persistent_absence_threshold: float = Query(default=90.0, ge=0, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AttendanceAnalyticsSummary:
    PermissionService.ensure_active_user(current_user)
    PermissionService.ensure_school_admin_or_platform_admin(current_user)

    service = AttendanceAnalyticsService(db)

    return await service.get_school_analytics(
        school_id=current_user.school_id,
        persistent_absence_threshold=persistent_absence_threshold,
    )
