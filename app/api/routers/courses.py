from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_role
from app.db.session import get_db
from app.models import Course, Enrollment, User
from app.schemas.course import CourseCreate, CourseOut

router = APIRouter()


@router.post("", response_model=CourseOut, status_code=status.HTTP_201_CREATED)
async def create_course(
    payload: CourseCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("teacher", "admin")),
):
    # ✅ enforce school ownership
    course = Course(
        title=payload.title,
        description=payload.description,
        teacher_id=current_user.id,
        school_id=current_user.school_id,
    )

    db.add(course)

    try:
        await db.commit()
        await db.refresh(course)
    except Exception:
        await db.rollback()
        raise

    return course


@router.get("", response_model=list[CourseOut])
async def list_courses(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("student", "teacher", "admin")),
):
    # ✅ ALWAYS scope by school
    stmt = select(Course).where(Course.school_id == current_user.school_id)

    # ✅ students only see published
    if current_user.role == "student":
        stmt = stmt.where(Course.published.is_(True))

    res = await db.execute(stmt)
    return list(res.scalars().all())


@router.post("/{course_id}/publish", response_model=CourseOut)
async def publish_course(
    course_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("teacher", "admin")),
):
    # ✅ scope by school
    res = await db.execute(
        select(Course).where(
            Course.id == course_id,
            Course.school_id == current_user.school_id,
        )
    )
    course = res.scalar_one_or_none()

    if course is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found",
        )

    # ✅ ownership check
    if current_user.role != "admin" and course.teacher_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not your course",
        )

    course.published = True

    try:
        await db.commit()
        await db.refresh(course)
    except Exception:
        await db.rollback()
        raise

    return course


@router.post("/{course_id}/enroll", status_code=status.HTTP_200_OK)
async def enroll(
    course_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("student", "admin")),
):
    # ✅ scope by school + published
    res = await db.execute(
        select(Course).where(
            Course.id == course_id,
            Course.school_id == current_user.school_id,
            Course.published.is_(True),
        )
    )
    course = res.scalar_one_or_none()

    if course is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found or not published",
        )

    enrollment = Enrollment(
        course_id=course_id,
        student_id=current_user.id,
    )
    db.add(enrollment)

    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Already enrolled",
        )
    except Exception:
        await db.rollback()
        raise

    return {"enrolled": True, "course_id": course_id}


@router.get("/me", response_model=list[CourseOut])
async def my_courses(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("teacher", "admin")),
):
    # ✅ ALWAYS scope by school
    stmt = select(Course).where(Course.school_id == current_user.school_id)

    # ✅ teachers see only their own courses
    if current_user.role == "teacher":
        stmt = stmt.where(Course.teacher_id == current_user.id)

    res = await db.execute(stmt)
    return list(res.scalars().all())
