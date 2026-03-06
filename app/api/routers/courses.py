from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.models import Course, Enrollment, User
from app.schemas.course import CourseCreate, CourseOut
from app.api.deps import require_role

router = APIRouter()


@router.post("", response_model=CourseOut)
async def create_course(
    payload: CourseCreate,
    db: AsyncSession = Depends(get_db),
    teacher: User = Depends(require_role("teacher", "admin")),
):
    course = Course(
        title=payload.title,
        description=payload.description,
        teacher_id=teacher.id,
    )
    db.add(course)
    await db.commit()
    await db.refresh(course)
    return course


@router.get("", response_model=list[CourseOut])
async def list_courses(db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(Course))
    return list(res.scalars().all())


@router.post("/{course_id}/publish", response_model=CourseOut)
async def publish_course(
    course_id: int,
    db: AsyncSession = Depends(get_db),
    teacher: User = Depends(require_role("teacher", "admin")),
):
    res = await db.execute(select(Course).where(Course.id == course_id))
    course = res.scalar_one_or_none()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    if teacher.role != "admin" and course.teacher_id != teacher.id:
        raise HTTPException(status_code=403, detail="Not your course")

    course.published = True
    await db.commit()
    await db.refresh(course)
    return course


@router.post("/{course_id}/enroll")
async def enroll(
    course_id: int,
    db: AsyncSession = Depends(get_db),
    student: User = Depends(require_role("student", "admin")),
):
    res = await db.execute(
        select(Course).where(Course.id == course_id, Course.published == True)
    )
    course = res.scalar_one_or_none()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found or not published")

    db.add(Enrollment(course_id=course_id, student_id=student.id))
    try:
        await db.commit()
    except Exception:
        await db.rollback()
        raise HTTPException(status_code=400, detail="Already enrolled")

    return {"enrolled": True, "course_id": course_id}
