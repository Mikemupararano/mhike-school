from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.permissions import PermissionService
from app.db.session import get_db
from app.models.user import User
from app.schemas.attendance_dashboard import AttendanceDashboardSummary
from app.services.attendance_dashboard_service import AttendanceDashboardService

router = APIRouter(tags=["Attendance Dashboard"])


@router.get("/summary", response_model=AttendanceDashboardSummary)
async def get_attendance_dashboard_summary(
    summary_date: date = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AttendanceDashboardSummary:
    PermissionService.ensure_active_user(current_user)
    PermissionService.ensure_school_admin_or_platform_admin(current_user)

    school_id = current_user.school_id

    service = AttendanceDashboardService(db)

    return await service.get_school_summary(
        school_id=school_id,
        summary_date=summary_date,
    )
