from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.permissions import PermissionService
from app.db.session import get_db
from app.models.user import User
from app.schemas.parent_student import (
    ParentStudentCreate,
    ParentStudentOut,
)
from app.services.parent_student_service import (
    ParentStudentService,
)

router = APIRouter(tags=["Parent Students"])


@router.post(
    "/links",
    response_model=ParentStudentOut,
)
async def create_parent_student_link(
    data: ParentStudentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ParentStudentOut:
    PermissionService.ensure_active_user(current_user)
    PermissionService.ensure_school_admin_or_platform_admin(current_user)

    service = ParentStudentService(db)

    try:
        link = await service.create_link(
            data,
        )

        await db.commit()
        await db.refresh(
            link,
        )

        return link
    except Exception:
        await db.rollback()
        raise


@router.get(
    "/parents/{parent_id}/children",
    response_model=list[ParentStudentOut],
)
async def list_children_for_parent(
    parent_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ParentStudentOut]:
    PermissionService.ensure_active_user(current_user)
    PermissionService.ensure_school_admin_or_platform_admin(current_user)

    service = ParentStudentService(db)

    return await service.list_children_for_parent(
        parent_id=parent_id,
    )


@router.get(
    "/students/{student_id}/parents",
    response_model=list[ParentStudentOut],
)
async def list_parents_for_student(
    student_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ParentStudentOut]:
    PermissionService.ensure_active_user(current_user)
    PermissionService.ensure_school_admin_or_platform_admin(current_user)

    service = ParentStudentService(db)

    return await service.list_parents_for_student(
        student_id=student_id,
    )


@router.delete(
    "/links",
    status_code=204,
)
async def remove_parent_student_link(
    parent_id: int,
    student_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    PermissionService.ensure_active_user(current_user)
    PermissionService.ensure_school_admin_or_platform_admin(current_user)

    service = ParentStudentService(db)

    try:
        await service.remove_link(
            parent_id=parent_id,
            student_id=student_id,
        )

        await db.commit()
    except Exception:
        await db.rollback()
        raise
