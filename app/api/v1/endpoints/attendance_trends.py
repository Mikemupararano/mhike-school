from __future__ import annotations

from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.permissions import PermissionService
from app.db.session import get_db
from app.models.user import User
from app.schemas.attendance_trends import (
    AttendanceTrendSummary,
)
from app.services.attendance_trends_service import (
    AttendanceTrendsService,
)

router = APIRouter(tags=["Attendance Trends"])


@router.get(
    "/summary",
    response_model=AttendanceTrendSummary,
)
async def get_attendance_trends(
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AttendanceTrendSummary:
    PermissionService.ensure_active_user(current_user)
    PermissionService.ensure_school_admin_or_platform_admin(current_user)

    if current_user.school_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current user is not linked to a school.",
        )

    resolved_end_date = end_date or date.today()

    resolved_start_date = start_date or resolved_end_date - timedelta(days=30)

    if resolved_start_date > resolved_end_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="start_date cannot be after end_date.",
        )

    service = AttendanceTrendsService(db)

    return await service.get_trends(
        school_id=current_user.school_id,
        start_date=resolved_start_date,
        end_date=resolved_end_date,
    )
