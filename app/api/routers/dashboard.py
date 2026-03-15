from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_role
from app.db.session import get_db
from app.models import Course, Enrollment, Lesson, Module, Progress, User
from app.schemas.dashboard import CourseProgressOut, DashboardMeOut, NextLessonOut

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/courses/{course_id}/progress")
async def course_progress(
    course_id: int,
    db: AsyncSession = Depends(get_db),
    student: User = Depends(require_role("student", "admin")),
):
    if student.role != "admin":
        enr = await db.execute(
            select(Enrollment).where(
                Enrollment.course_id == course_id,
                Enrollment.student_id == student.id,
            )
        )
        if not enr.scalar_one_or_none():
            raise HTTPException(status_code=403, detail="Not enrolled in this course")

    course_res = await db.execute(select(Course).where(Course.id == course_id))
    course = course_res.scalar_one_or_none()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    total_q = (
        select(func.count(Lesson.id))
        .join(Module, Lesson.module_id == Module.id)
        .where(Module.course_id == course_id)
    )
    total = (await db.execute(total_q)).scalar_one()

    completed_q = (
        select(func.count(Progress.id))
        .join(Lesson, Progress.lesson_id == Lesson.id)
        .join(Module, Lesson.module_id == Module.id)
        .where(
            Module.course_id == course_id,
            Progress.student_id == student.id,
            Progress.completed.is_(True),
        )
    )
    completed = (await db.execute(completed_q)).scalar_one()

    pct = 0.0 if total == 0 else round((completed / total) * 100, 2)

    return {
        "course_id": course_id,
        "student_id": student.id,
        "total_lessons": total,
        "completed_lessons": completed,
        "progress_percent": pct,
    }


@router.get("/me", response_model=DashboardMeOut)
async def dashboard_me(
    db: AsyncSession = Depends(get_db),
    student: User = Depends(require_role("student", "admin")),
):
    enroll_q = (
        select(Course)
        .join(Enrollment, Enrollment.course_id == Course.id)
        .where(Enrollment.student_id == student.id)
        .order_by(Course.id)
    )
    enrolled_courses = list((await db.execute(enroll_q)).scalars().all())

    courses_out: list[CourseProgressOut] = []
    total_completed_all_courses = 0

    for course in enrolled_courses:
        total_q = (
            select(func.count(Lesson.id))
            .join(Module, Lesson.module_id == Module.id)
            .where(Module.course_id == course.id)
        )
        total_lessons = (await db.execute(total_q)).scalar_one()

        completed_q = (
            select(func.count(Progress.id))
            .join(Lesson, Progress.lesson_id == Lesson.id)
            .join(Module, Lesson.module_id == Module.id)
            .where(
                Module.course_id == course.id,
                Progress.student_id == student.id,
                Progress.completed.is_(True),
            )
        )
        completed_lessons = (await db.execute(completed_q)).scalar_one()
        total_completed_all_courses += completed_lessons

        pct = (
            0.0
            if total_lessons == 0
            else round((completed_lessons / total_lessons) * 100, 2)
        )

        next_lesson_q = (
            select(Lesson.id, Lesson.title)
            .join(Module, Lesson.module_id == Module.id)
            .where(Module.course_id == course.id)
            .order_by(Module.order, Lesson.order)
        )
        lessons = (await db.execute(next_lesson_q)).all()

        next_lesson: NextLessonOut | None = None
        if lessons:
            completed_ids_q = (
                select(Lesson.id)
                .join(Module, Lesson.module_id == Module.id)
                .join(Progress, Progress.lesson_id == Lesson.id)
                .where(
                    Module.course_id == course.id,
                    Progress.student_id == student.id,
                    Progress.completed.is_(True),
                )
            )
            completed_ids = set((await db.execute(completed_ids_q)).scalars().all())

            for lesson_id, title in lessons:
                if lesson_id not in completed_ids:
                    next_lesson = NextLessonOut(lesson_id=lesson_id, title=title)
                    break

        courses_out.append(
            CourseProgressOut(
                course_id=course.id,
                title=course.title,
                published=course.published,
                total_lessons=total_lessons,
                completed_lessons=completed_lessons,
                progress_percent=pct,
                next_lesson=next_lesson,
            )
        )

    return DashboardMeOut(
        student_id=student.id,
        enrolled_courses=len(enrolled_courses),
        total_lessons_completed=total_completed_all_courses,
        courses=courses_out,
    )
