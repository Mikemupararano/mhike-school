from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.permissions import PermissionService
from app.db.session import get_db
from app.models.user import User
from app.schemas.attendance import (
    AttendanceRecordBulkUpdate,
    AttendanceRecordOut,
)
from app.services.attendance_bulk_service import AttendanceBulkService

router = APIRouter(tags=["Attendance Bulk Actions"])


@router.patch(
    "/records",
    response_model=list[AttendanceRecordOut],
)
async def bulk_update_attendance_records(
    data: AttendanceRecordBulkUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[AttendanceRecordOut]:
    PermissionService.ensure_active_user(current_user)
    PermissionService.ensure_school_admin_or_platform_admin(current_user)

    service = AttendanceBulkService(db)

    return await service.update_records_bulk(data)
