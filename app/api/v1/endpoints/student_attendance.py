from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.permissions import PermissionService
from app.db.session import get_db
from app.models.user import User
from app.schemas.student_attendance import StudentAttendanceProfile
from app.services.student_attendance_service import StudentAttendanceService

router = APIRouter(tags=["Student Attendance"])


@router.get(
    "/students/{student_id}/profile",
    response_model=StudentAttendanceProfile,
)
async def get_student_attendance_profile(
    student_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> StudentAttendanceProfile:
    PermissionService.ensure_active_user(current_user)
    PermissionService.ensure_school_admin_or_platform_admin(current_user)

    if current_user.school_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current user is not linked to a school.",
        )

    service = StudentAttendanceService(db)

    return await service.get_student_profile(
        school_id=current_user.school_id,
        student_id=student_id,
    )
