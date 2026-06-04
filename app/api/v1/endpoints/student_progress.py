from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.core.permissions import PermissionService
from app.models.user import User, UserRole
from app.repositories.parent_student import ParentStudentRepository
from app.repositories.student_progress import get_student_progress_summary
from app.schemas.student_progress import StudentProgressSummary

router = APIRouter()


def _require_school_id(user: User) -> int:
    if user.school_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not linked to a school.",
        )

    return user.school_id


@router.get(
    "/{student_id}",
    response_model=StudentProgressSummary,
)
async def get_student_progress_endpoint(
    student_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> StudentProgressSummary:
    PermissionService.ensure_active_user(current_user)
    PermissionService.ensure_can_teach(current_user)

    school_id = _require_school_id(current_user)

    return await get_student_progress_summary(
        db,
        student_id=student_id,
        school_id=school_id,
    )


@router.get(
    "/parent/{student_id}",
    response_model=StudentProgressSummary,
)
async def get_parent_student_progress_endpoint(
    student_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> StudentProgressSummary:
    PermissionService.ensure_active_user(current_user)
    PermissionService.ensure_has_role(current_user, UserRole.PARENT)

    school_id = _require_school_id(current_user)

    parent_repository = ParentStudentRepository(db)

    link = await parent_repository.get_link(
        parent_id=current_user.id,
        student_id=student_id,
    )

    if link is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not linked to this student.",
        )

    return await get_student_progress_summary(
        db,
        student_id=student_id,
        school_id=school_id,
    )
