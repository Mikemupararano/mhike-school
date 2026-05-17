from __future__ import annotations

import csv
from io import StringIO

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.permissions import PermissionService
from app.db.session import get_db
from app.models.user import User
from app.schemas.attendance import AttendanceFilter
from app.services.attendance_service import AttendanceService

router = APIRouter(tags=["Attendance Exports"])


@router.get("/registers/export/{session_id}")
async def export_attendance_register_csv(
    session_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    PermissionService.ensure_active_user(current_user)
    PermissionService.ensure_school_admin_or_platform_admin(current_user)

    service = AttendanceService(db)
    session = await service.get_session_or_404(session_id)

    if session.school_id != current_user.school_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot export attendance register from another school.",
        )

    records = await service.list_records(
        AttendanceFilter(
            school_id=current_user.school_id,
            class_group_id=session.class_group_id,
            session_date=session.session_date,
            session_type=session.session_type,
            timetable_entry_id=session.timetable_entry_id,
            timetable_period_id=session.timetable_period_id,
            limit=200,
            offset=0,
        )
    )

    output = StringIO()
    writer = csv.writer(output)

    writer.writerow(
        [
            "record_id",
            "attendance_session_id",
            "student_id",
            "status",
            "notes",
            "marked_by_id",
            "created_at",
            "updated_at",
        ]
    )

    for record in records:
        writer.writerow(
            [
                record.id,
                record.attendance_session_id,
                record.student_id,
                record.status,
                record.notes or "",
                record.marked_by_id or "",
                record.created_at.isoformat(),
                record.updated_at.isoformat(),
            ]
        )

    filename = f"attendance_register_{session.id}_{session.session_date}.csv"

    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )
