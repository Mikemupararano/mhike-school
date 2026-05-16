from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.permissions import PermissionService
from app.db.session import get_db
from app.models.user import User
from app.schemas.timetable import (
    TimetableAssignmentCreate,
    TimetableAssignmentFilter,
    TimetableAssignmentOut,
    TimetableCreate,
    TimetableEntryCreate,
    TimetableEntryFilter,
    TimetableEntryOut,
    TimetableFilter,
    TimetableOut,
    TimetablePeriodCreate,
    TimetablePeriodOut,
)
from app.services.timetable_service import TimetableService

router = APIRouter()


# =========================================================
# TIMETABLE PERIODS
# =========================================================


@router.post(
    "/periods",
    response_model=TimetablePeriodOut,
)
async def create_timetable_period(
    payload: TimetablePeriodCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    PermissionService.ensure_active_user(current_user)
    PermissionService.ensure_school_admin_or_teacher(current_user)

    payload.school_id = current_user.school_id

    service = TimetableService(db)

    return await service.create_period(payload)


@router.get(
    "/periods",
    response_model=list[TimetablePeriodOut],
)
async def list_timetable_periods(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    PermissionService.ensure_active_user(current_user)
    PermissionService.ensure_school_admin_or_teacher(current_user)

    service = TimetableService(db)

    return await service.list_periods(current_user.school_id)


# =========================================================
# TIMETABLES
# =========================================================


@router.post(
    "/",
    response_model=TimetableOut,
)
async def create_timetable(
    payload: TimetableCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    PermissionService.ensure_active_user(current_user)
    PermissionService.ensure_school_admin_or_teacher(current_user)

    payload.school_id = current_user.school_id

    service = TimetableService(db)

    return await service.create_timetable(payload)


@router.get(
    "/",
    response_model=list[TimetableOut],
)
async def list_timetables(
    academic_year: str | None = Query(default=None),
    is_active: bool | None = Query(default=None),
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    PermissionService.ensure_active_user(current_user)
    PermissionService.ensure_school_admin_or_teacher(current_user)

    filters = TimetableFilter(
        school_id=current_user.school_id,
        academic_year=academic_year,
        is_active=is_active,
        limit=limit,
        offset=offset,
    )

    service = TimetableService(db)

    return await service.list_timetables(filters)


# =========================================================
# TIMETABLE ENTRIES
# =========================================================


@router.post(
    "/entries",
    response_model=TimetableEntryOut,
)
async def create_timetable_entry(
    payload: TimetableEntryCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    PermissionService.ensure_active_user(current_user)
    PermissionService.ensure_school_admin_or_teacher(current_user)

    payload.school_id = current_user.school_id

    service = TimetableService(db)

    return await service.create_entry(payload)


@router.get(
    "/entries",
    response_model=list[TimetableEntryOut],
)
async def list_timetable_entries(
    timetable_id: int | None = Query(default=None),
    class_group_id: int | None = Query(default=None),
    course_id: int | None = Query(default=None),
    teacher_id: int | None = Query(default=None),
    day_of_week: str | None = Query(default=None),
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    PermissionService.ensure_active_user(current_user)
    PermissionService.ensure_school_admin_or_teacher(current_user)

    filters = TimetableEntryFilter(
        school_id=current_user.school_id,
        timetable_id=timetable_id,
        class_group_id=class_group_id,
        course_id=course_id,
        teacher_id=teacher_id,
        day_of_week=day_of_week,
        limit=limit,
        offset=offset,
    )

    service = TimetableService(db)

    return await service.list_entries(filters)


# =========================================================
# TEACHER TIMETABLE
# =========================================================


@router.get(
    "/teacher/me",
    response_model=list[TimetableEntryOut],
)
async def get_my_teacher_timetable(
    day_of_week: str | None = Query(default=None),
    limit: int = Query(default=100, le=200),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    PermissionService.ensure_active_user(current_user)
    PermissionService.ensure_can_teach(current_user)

    filters = TimetableEntryFilter(
        school_id=current_user.school_id,
        teacher_id=current_user.id,
        day_of_week=day_of_week,
        limit=limit,
        offset=offset,
    )

    service = TimetableService(db)

    return await service.list_entries(filters)


# =========================================================
# TIMETABLE ASSIGNMENTS
# =========================================================


@router.post(
    "/assignments",
    response_model=TimetableAssignmentOut,
)
async def create_timetable_assignment(
    payload: TimetableAssignmentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    PermissionService.ensure_active_user(current_user)
    PermissionService.ensure_school_admin_or_teacher(current_user)

    payload.school_id = current_user.school_id

    service = TimetableService(db)

    return await service.create_assignment(payload)


@router.get(
    "/assignments",
    response_model=list[TimetableAssignmentOut],
)
async def list_timetable_assignments(
    timetable_id: int | None = Query(default=None),
    assignment_type: str | None = Query(default=None),
    user_id: int | None = Query(default=None),
    class_group_id: int | None = Query(default=None),
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    PermissionService.ensure_active_user(current_user)
    PermissionService.ensure_school_admin_or_teacher(current_user)

    filters = TimetableAssignmentFilter(
        school_id=current_user.school_id,
        timetable_id=timetable_id,
        assignment_type=assignment_type,
        user_id=user_id,
        class_group_id=class_group_id,
        limit=limit,
        offset=offset,
    )

    service = TimetableService(db)

    return await service.list_assignments(filters)
