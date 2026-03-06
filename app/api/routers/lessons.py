from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.api.deps import require_role
from app.models import Module, Lesson, Course, User
from app.schemas.lesson import LessonCreate, LessonOut

router = APIRouter()


@router.post("/modules/{module_id}/lessons", response_model=LessonOut)
async def create_lesson(
    module_id: int,
    payload: LessonCreate,
    db: AsyncSession = Depends(get_db),
    teacher: User = Depends(require_role("teacher", "admin")),
):
    res = await db.execute(select(Module).where(Module.id == module_id))
    module = res.scalar_one_or_none()
    if not module:
        raise HTTPException(status_code=404, detail="Module not found")

    # check ownership
    cres = await db.execute(select(Course).where(Course.id == module.course_id))
    course = cres.scalar_one_or_none()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    if teacher.role != "admin" and course.teacher_id != teacher.id:
        raise HTTPException(status_code=403, detail="Not your course")

    lesson = Lesson(
        module_id=module_id,
        title=payload.title,
        content_type=payload.content_type,
        content=payload.content,
        order=payload.order,
    )
    db.add(lesson)
    await db.commit()
    await db.refresh(lesson)
    return lesson


@router.get("/modules/{module_id}/lessons", response_model=list[LessonOut])
async def list_lessons(module_id: int, db: AsyncSession = Depends(get_db)):
    res = await db.execute(
        select(Lesson).where(Lesson.module_id == module_id).order_by(Lesson.order)
    )
    return list(res.scalars().all())
