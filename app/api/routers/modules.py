from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import asc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_role
from app.db.session import get_db
from app.models.course import Course
from app.models.module import Module
from app.models.user import User
from app.schemas.module import ModuleCreate, ModuleOut

router = APIRouter()


@router.post("/courses/{course_id}/modules", response_model=ModuleOut)
async def create_module(
    course_id: int,
    payload: ModuleCreate,
    db: AsyncSession = Depends(get_db),
    teacher: User = Depends(require_role("teacher", "admin")),
):
    res = await db.execute(select(Course).where(Course.id == course_id))
    course = res.scalar_one_or_none()

    if course is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found",
        )

    if teacher.role != "admin" and course.teacher_id != teacher.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not your course",
        )

    module = Module(
        course_id=course_id,
        title=payload.title,
        order=payload.order,
    )
    db.add(module)

    try:
        await db.commit()
        await db.refresh(module)
    except Exception:
        await db.rollback()
        raise

    return module


@router.get("/courses/{course_id}/modules", response_model=list[ModuleOut])
async def list_modules(
    course_id: int,
    db: AsyncSession = Depends(get_db),
):
    res = await db.execute(
        select(Module).where(Module.course_id == course_id).order_by(asc(Module.order))
    )
    return list(res.scalars().all())
