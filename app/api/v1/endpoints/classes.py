from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_school_id, get_current_user, require_role
from app.db.session import get_db
from app.models import User
from app.schemas.class_group import ClassGroupCreate, ClassGroupOut
from app.services.class_service import ClassService
from app.schemas.user import UserOut

router = APIRouter()


@router.get("/", response_model=List[ClassGroupOut])
async def list_classes(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    current_school_id: int = Depends(get_current_school_id),
):
    return await ClassService.list_classes_by_school(db, current_school_id)


@router.get("/{class_id}", response_model=ClassGroupOut)
async def get_class(
    class_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    current_school_id: int = Depends(get_current_school_id),
):
    class_group = await ClassService.get_class_by_id(db, class_id, current_school_id)
    if class_group is None:
        raise HTTPException(status_code=404, detail="Class not found")
    return class_group


@router.post("/", response_model=ClassGroupOut, status_code=201)
async def create_class(
    payload: ClassGroupCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin", "teacher")),
    current_school_id: int = Depends(get_current_school_id),
):
    return await ClassService.create_class(db, payload, current_school_id)


@router.get("/{class_id}/students", response_model=List[UserOut])
async def get_class_students(
    class_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    current_school_id: int = Depends(get_current_school_id),
):
    students = await ClassService.get_students_in_class(
        db,
        class_id,
        current_school_id,
    )

    if students is None:
        raise HTTPException(status_code=404, detail="Class not found")

    return students
