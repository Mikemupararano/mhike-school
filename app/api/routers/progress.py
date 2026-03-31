from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_role
from app.db.session import get_db
from app.models.course import Course
from app.models.lesson import Lesson
from app.models.module import Module
from app.models.progress import Progress
from app.models.user import User
from app.schemas.progress import MarkLessonIn, ProgressOut

router = APIRouter()


@router.post("/lessons/{lesson_id}/progress", response_model=ProgressOut)
async def mark_lesson(
    lesson_id: int,
    payload: MarkLessonIn,
    db: AsyncSession = Depends(get_db),
    student: User = Depends(require_role("student", "admin")),
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
            Course.school_id == student.school_id,
        )
    )
    course = course_res.scalar_one_or_none()

    if course is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lesson not found",
        )

    if student.role == "student" and not course.published:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lesson not found",
        )

    stmt = (
        insert(Progress)
        .values(
            student_id=student.id,
            lesson_id=lesson_id,
            completed=payload.completed,
        )
        .on_conflict_do_update(
            index_elements=["student_id", "lesson_id"],
            set_={"completed": payload.completed},
        )
        .returning(Progress)
    )

    result = await db.execute(stmt)
    await db.commit()
    progress = result.scalar_one()
    return progress


@router.get("/me/progress", response_model=list[ProgressOut])
async def my_progress(
    db: AsyncSession = Depends(get_db),
    student: User = Depends(require_role("student", "admin")),
):
    stmt = (
        select(Progress)
        .join(Lesson, Progress.lesson_id == Lesson.id)
        .join(Module, Lesson.module_id == Module.id)
        .join(Course, Module.course_id == Course.id)
        .where(
            Progress.student_id == student.id,
            Course.school_id == student.school_id,
        )
    )

    res = await db.execute(stmt)
    return list(res.scalars().all())
