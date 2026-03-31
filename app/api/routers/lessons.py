from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_role
from app.db.session import get_db
from app.models.course import Course
from app.models.lesson import Lesson
from app.models.module import Module
from app.models.user import User
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

    if module is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Module not found",
        )

    cres = await db.execute(
        select(Course).where(
            Course.id == module.course_id,
            Course.school_id == teacher.school_id,
        )
    )
    course = cres.scalar_one_or_none()

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

    lesson = Lesson(
        module_id=module_id,
        title=payload.title,
        content_type=payload.content_type,
        content=payload.content,
        order=payload.order,
    )
    db.add(lesson)

    try:
        await db.commit()
        await db.refresh(lesson)
    except Exception:
        await db.rollback()
        raise

    return lesson


@router.get("/modules/{module_id}/lessons", response_model=list[LessonOut])
async def list_lessons(
    module_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("student", "teacher", "admin")),
):
    module_res = await db.execute(select(Module).where(Module.id == module_id))
    module = module_res.scalar_one_or_none()

    if module is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Module not found",
        )

    course_res = await db.execute(
        select(Course).where(
            Course.id == module.course_id,
            Course.school_id == current_user.school_id,
        )
    )
    course = course_res.scalar_one_or_none()

    if course is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found",
        )

    if current_user.role == "student" and not course.published:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found",
        )

    lessons_res = await db.execute(
        select(Lesson).where(Lesson.module_id == module_id).order_by(Lesson.order)
    )
    return list(lessons_res.scalars().all())


@router.get("/lessons/{lesson_id}", response_model=LessonOut)
async def get_lesson(
    lesson_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("student", "teacher", "admin")),
):
    lesson_res = await db.execute(select(Lesson).where(Lesson.id == lesson_id))
    lesson = lesson_res.scalar_one_or_none()

    if lesson is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lesson not found",
        )

    module_res = await db.execute(select(Module).where(Module.id == lesson.module_id))
    module = module_res.scalar_one_or_none()

    if module is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Module not found",
        )

    course_res = await db.execute(
        select(Course).where(
            Course.id == module.course_id,
            Course.school_id == current_user.school_id,
        )
    )
    course = course_res.scalar_one_or_none()

    if course is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lesson not found",
        )

    if current_user.role == "student" and not course.published:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lesson not found",
        )

    return lesson
