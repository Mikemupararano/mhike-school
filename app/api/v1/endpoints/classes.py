from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_school_id, get_current_user
from app.core.permissions import PermissionService
from app.db.session import get_db
from app.models import User
from app.schemas.class_group import ClassGroupCreate, ClassGroupOut
from app.schemas.user import UserOut
from app.services.class_service import ClassService

router = APIRouter()


@router.get("/", response_model=List[ClassGroupOut])
async def list_classes(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    current_school_id: int = Depends(get_current_school_id),
):
    PermissionService.ensure_active_user(current_user)
    return await ClassService.list_classes_by_school(db, current_school_id)


@router.get("/{class_id}", response_model=ClassGroupOut)
async def get_class(
    class_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    current_school_id: int = Depends(get_current_school_id),
):
    PermissionService.ensure_active_user(current_user)
    return await ClassService.get_class(db, class_id, current_school_id)


@router.post("/", response_model=ClassGroupOut, status_code=status.HTTP_201_CREATED)
async def create_class(
    payload: ClassGroupCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    current_school_id: int = Depends(get_current_school_id),
):
    PermissionService.ensure_active_user(current_user)
    PermissionService.ensure_can_teach(current_user)

    try:
        class_group = await ClassService.create_class(
            db=db,
            name=payload.name,
            school_id=current_school_id,
            teacher_id=payload.teacher_id,
        )
        await db.commit()
        await db.refresh(class_group)
        return class_group
    except ValueError as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.patch("/{class_id}/assign-teacher", response_model=ClassGroupOut)
async def assign_teacher(
    class_id: int,
    teacher_id: int = Query(..., ge=1),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    current_school_id: int = Depends(get_current_school_id),
):
    PermissionService.ensure_active_user(current_user)
    PermissionService.ensure_school_admin_or_platform_admin(current_user)

    try:
        class_group = await ClassService.assign_teacher(
            db=db,
            class_id=class_id,
            teacher_id=teacher_id,
            school_id=current_school_id,
        )
        await db.commit()
        await db.refresh(class_group)
        return class_group
    except ValueError as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.get("/{class_id}/students", response_model=List[UserOut])
async def get_class_students(
    class_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    current_school_id: int = Depends(get_current_school_id),
):
    PermissionService.ensure_active_user(current_user)
    return await ClassService.get_students_in_class(
        db,
        class_id,
        current_school_id,
    )
