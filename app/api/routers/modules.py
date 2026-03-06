from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.api.deps import require_role
from app.models import Course, Module, User
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
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    if teacher.role != "admin" and course.teacher_id != teacher.id:
        raise HTTPException(status_code=403, detail="Not your course")

    module = Module(course_id=course_id, title=payload.title, order=payload.order)
    db.add(module)
    await db.commit()
    await db.refresh(module)
    return module


@router.get("/courses/{course_id}/modules", response_model=list[ModuleOut])
async def list_modules(course_id: int, db: AsyncSession = Depends(get_db)):
    res = await db.execute(
        select(Module).where(Module.course_id == course_id).order_by(Module.order)
    )
    return list(res.scalars().all())
