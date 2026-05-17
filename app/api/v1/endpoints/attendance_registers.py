from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.permissions import PermissionService
from app.db.session import get_db
from app.models.user import User
from app.schemas.attendance import (
    AttendanceFilter,
    AttendanceRecordOut,
    AttendanceSessionOut,
)
from app.services.attendance_service import AttendanceService

router = APIRouter(tags=["Attendance Registers"])


@router.get("/{session_id}", response_model=AttendanceSessionOut)
async def get_attendance_register(
    session_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AttendanceSessionOut:
    PermissionService.ensure_active_user(current_user)
    PermissionService.ensure_school_admin_or_platform_admin(current_user)

    service = AttendanceService(db)
    session = await service.get_session_or_404(session_id)

    if session.school_id != current_user.school_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot access attendance register from another school.",
        )

    return session


@router.get("/{session_id}/records", response_model=list[AttendanceRecordOut])
async def get_attendance_register_records(
    session_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[AttendanceRecordOut]:
    PermissionService.ensure_active_user(current_user)
    PermissionService.ensure_school_admin_or_platform_admin(current_user)

    service = AttendanceService(db)
    session = await service.get_session_or_404(session_id)

    if session.school_id != current_user.school_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot access attendance register from another school.",
        )

    return await service.list_records(
        AttendanceFilter(
            school_id=current_user.school_id,
            class_group_id=session.class_group_id,
            session_date=session.session_date,
            session_type=session.session_type,
            timetable_entry_id=session.timetable_entry_id,
            timetable_period_id=session.timetable_period_id,
            limit=300,
            offset=0,
        )
    )


@router.patch("/{session_id}/reopen", response_model=AttendanceSessionOut)
async def reopen_attendance_register(
    session_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AttendanceSessionOut:
    PermissionService.ensure_active_user(current_user)
    PermissionService.ensure_school_admin_or_platform_admin(current_user)

    service = AttendanceService(db)
    session = await service.get_session_or_404(session_id)

    if session.school_id != current_user.school_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot reopen attendance register from another school.",
        )

    return await service.reopen_register(session_id)
