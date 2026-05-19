from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.permissions import PermissionService
from app.db.session import get_db
from app.models.user import User
from app.schemas.student_attendance import StudentAttendanceProfile
from app.services.parent_student_service import ParentStudentService
from app.services.student_attendance_service import StudentAttendanceService

router = APIRouter(tags=["Parent Attendance"])


@router.get(
    "/students/{student_id}/profile",
    response_model=StudentAttendanceProfile,
)
async def get_child_attendance_profile(
    student_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> StudentAttendanceProfile:
    PermissionService.ensure_active_user(current_user)

    if current_user.school_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current user is not linked to a school.",
        )

    if current_user.is_parent:
        parent_student_service = ParentStudentService(db)

        await parent_student_service.validate_parent_access(
            parent_id=current_user.id,
            student_id=student_id,
        )
    else:
        PermissionService.ensure_school_admin_or_platform_admin(current_user)

    attendance_service = StudentAttendanceService(db)

    return await attendance_service.get_student_profile(
        school_id=current_user.school_id,
        student_id=student_id,
    )
