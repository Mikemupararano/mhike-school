from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.db.session import get_db
from app.api.deps import require_role
from app.models import Course, Module, Lesson, Progress, Enrollment, User

router = APIRouter()


@router.get("/courses/{course_id}/progress")
async def course_progress(
    course_id: int,
    db: AsyncSession = Depends(get_db),
    student: User = Depends(require_role("student", "admin")),
):
    # Ensure student is enrolled (admin can view regardless)
    if student.role != "admin":
        enr = await db.execute(
            select(Enrollment).where(
                Enrollment.course_id == course_id,
                Enrollment.student_id == student.id,
            )
        )
        if not enr.scalar_one_or_none():
            raise HTTPException(status_code=403, detail="Not enrolled in this course")

    # total lessons in course
    total_q = (
        select(func.count(Lesson.id))
        .join(Module, Lesson.module_id == Module.id)
        .where(Module.course_id == course_id)
    )
    total = (await db.execute(total_q)).scalar_one()

    # completed lessons by this student in this course
    completed_q = (
        select(func.count(Progress.id))
        .join(Lesson, Progress.lesson_id == Lesson.id)
        .join(Module, Lesson.module_id == Module.id)
        .where(
            Module.course_id == course_id,
            Progress.student_id == student.id,
            Progress.completed == True,
        )
    )
    completed = (await db.execute(completed_q)).scalar_one()

    pct = 0 if total == 0 else round((completed / total) * 100, 2)

    # Optional: course existence check (nicer errors)
    cres = await db.execute(select(Course).where(Course.id == course_id))
    if not cres.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Course not found")

    return {
        "course_id": course_id,
        "student_id": student.id,
        "total_lessons": total,
        "completed_lessons": completed,
        "progress_percent": pct,
    }
