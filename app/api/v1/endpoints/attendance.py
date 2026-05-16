from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.permissions import PermissionService
from app.db.session import get_db
from app.models.user import User
from app.schemas.attendance import (
    AbsenceRequestFilter,
    AbsenceRequestOut,
    AbsenceRequestStatus,
    AbsenceRequestType,
    AttendanceFilter,
    AttendanceRecordCreate,
    AttendanceRecordOut,
    AttendanceRecordUpdate,
    AttendanceSessionCreate,
    AttendanceSessionOut,
    AttendanceSessionType,
    AttendanceStatus,
)
from app.services.attendance_service import AttendanceService

router = APIRouter(tags=["Attendance"])


@router.post("/sessions", response_model=AttendanceSessionOut)
async def create_attendance_session(
    data: AttendanceSessionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AttendanceSessionOut:
    PermissionService.ensure_active_user(current_user)
    PermissionService.ensure_school_admin_or_teacher(current_user)

    if not current_user.is_platform_admin:
        data.school_id = current_user.school_id

    data.created_by_id = current_user.id

    service = AttendanceService(db)

    return await service.create_session(data)


@router.get("/sessions", response_model=list[AttendanceSessionOut])
async def list_attendance_sessions(
    school_id: int | None = Query(default=None),
    class_group_id: int | None = Query(default=None),
    session_date: date | None = Query(default=None),
    session_type: AttendanceSessionType | None = Query(default=None),
    timetable_entry_id: int | None = Query(default=None),
    timetable_period_id: int | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[AttendanceSessionOut]:
    PermissionService.ensure_active_user(current_user)
    PermissionService.ensure_school_admin_or_teacher(current_user)

    if not current_user.is_platform_admin:
        school_id = current_user.school_id

    filters = AttendanceFilter(
        school_id=school_id,
        class_group_id=class_group_id,
        session_date=session_date,
        session_type=session_type,
        timetable_entry_id=timetable_entry_id,
        timetable_period_id=timetable_period_id,
        limit=limit,
        offset=offset,
    )

    service = AttendanceService(db)

    return await service.list_sessions(filters)


@router.post("/records", response_model=AttendanceRecordOut)
async def create_attendance_record(
    data: AttendanceRecordCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AttendanceRecordOut:
    PermissionService.ensure_active_user(current_user)
    PermissionService.ensure_school_admin_or_teacher(current_user)

    data.marked_by_id = current_user.id

    service = AttendanceService(db)

    return await service.create_record(data)


@router.get("/records", response_model=list[AttendanceRecordOut])
async def list_attendance_records(
    school_id: int | None = Query(default=None),
    class_group_id: int | None = Query(default=None),
    student_id: int | None = Query(default=None),
    session_date: date | None = Query(default=None),
    session_type: AttendanceSessionType | None = Query(default=None),
    status: AttendanceStatus | None = Query(default=None),
    timetable_entry_id: int | None = Query(default=None),
    timetable_period_id: int | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[AttendanceRecordOut]:
    PermissionService.ensure_active_user(current_user)

    if not current_user.is_platform_admin:
        school_id = current_user.school_id

    filters = AttendanceFilter(
        school_id=school_id,
        class_group_id=class_group_id,
        student_id=student_id,
        session_date=session_date,
        session_type=session_type,
        status=status,
        timetable_entry_id=timetable_entry_id,
        timetable_period_id=timetable_period_id,
        limit=limit,
        offset=offset,
    )

    service = AttendanceService(db)

    return await service.list_records(filters)


@router.patch("/records/{record_id}", response_model=AttendanceRecordOut)
async def update_attendance_record(
    record_id: int,
    data: AttendanceRecordUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AttendanceRecordOut:
    PermissionService.ensure_active_user(current_user)
    PermissionService.ensure_school_admin_or_teacher(current_user)

    service = AttendanceService(db)

    return await service.update_record(record_id, data)


@router.get("/absence-requests", response_model=list[AbsenceRequestOut])
async def list_absence_requests(
    school_id: int | None = Query(default=None),
    student_id: int | None = Query(default=None),
    absence_type: AbsenceRequestType | None = Query(default=None),
    status: AbsenceRequestStatus | None = Query(default=None),
    start_date_from: date | None = Query(default=None),
    start_date_to: date | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[AbsenceRequestOut]:
    PermissionService.ensure_active_user(current_user)

    if not current_user.is_platform_admin:
        school_id = current_user.school_id

    filters = AbsenceRequestFilter(
        school_id=school_id,
        student_id=student_id,
        absence_type=absence_type,
        status=status,
        start_date_from=start_date_from,
        start_date_to=start_date_to,
        limit=limit,
        offset=offset,
    )

    service = AttendanceService(db)

    return await service.list_absence_requests(filters)
