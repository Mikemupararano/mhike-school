from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.course import Course
from app.models.enrollment import Enrollment
from app.models.school import School
from app.models.user import User

router = APIRouter()


def _ensure_platform_admin(current_user: User) -> None:
    if current_user.role != "platform_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Platform admin access required",
        )


@router.get("/dashboard")
async def platform_admin_dashboard(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _ensure_platform_admin(current_user)

    total_users = await db.scalar(select(func.count()).select_from(User)) or 0
    total_students = (
        await db.scalar(
            select(func.count()).select_from(User).where(User.role == "student")
        )
        or 0
    )
    total_teachers = (
        await db.scalar(
            select(func.count()).select_from(User).where(User.role == "teacher")
        )
        or 0
    )
    total_admins = (
        await db.scalar(
            select(func.count())
            .select_from(User)
            .where(User.role.in_(["admin", "platform_admin"]))
        )
        or 0
    )
    total_courses = await db.scalar(select(func.count()).select_from(Course)) or 0
    published_courses = (
        await db.scalar(
            select(func.count()).select_from(Course).where(Course.published.is_(True))
        )
        or 0
    )
    total_enrollments = (
        await db.scalar(select(func.count()).select_from(Enrollment)) or 0
    )

    draft_courses = max(0, total_courses - published_courses)
    published_rate = (
        round((published_courses / total_courses) * 100, 1) if total_courses else 0
    )

    return {
        "scope": "platform",
        "school_id": None,
        "total_users": total_users,
        "total_students": total_students,
        "total_teachers": total_teachers,
        "total_admins": total_admins,
        "total_courses": total_courses,
        "published_courses": published_courses,
        "draft_courses": draft_courses,
        "total_enrollments": total_enrollments,
        "published_rate": published_rate,
    }


@router.get("/schools")
async def platform_admin_schools(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    search: str | None = Query(default=None),
):
    _ensure_platform_admin(current_user)

    query = select(School).order_by(School.id.asc())

    if search:
        term = f"%{search.strip()}%"
        query = query.where(School.name.ilike(term))

    result = await db.execute(query)
    schools = result.scalars().all()

    items = []
    for school in schools:
        school_id = school.id

        total_users = (
            await db.scalar(
                select(func.count())
                .select_from(User)
                .where(User.school_id == school_id)
            )
            or 0
        )

        total_students = (
            await db.scalar(
                select(func.count())
                .select_from(User)
                .where(
                    User.school_id == school_id,
                    User.role == "student",
                )
            )
            or 0
        )

        total_teachers = (
            await db.scalar(
                select(func.count())
                .select_from(User)
                .where(
                    User.school_id == school_id,
                    User.role == "teacher",
                )
            )
            or 0
        )

        total_courses = (
            await db.scalar(
                select(func.count())
                .select_from(Course)
                .where(Course.school_id == school_id)
            )
            or 0
        )

        items.append(
            {
                "id": school.id,
                "name": school.name,
                "total_users": total_users,
                "total_students": total_students,
                "total_teachers": total_teachers,
                "total_courses": total_courses,
            }
        )

    return items


@router.get("/users")
async def platform_admin_users(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    school_id: int | None = Query(default=None),
    role: str | None = Query(default=None),
    search: str | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=8, ge=1, le=100),
):
    _ensure_platform_admin(current_user)

    query = select(User).options(selectinload(User.school))
    count_query = select(func.count()).select_from(User)

    filters = []

    if school_id is not None:
        filters.append(User.school_id == school_id)

    if role:
        filters.append(User.role == role)

    if search:
        term = f"%{search.strip()}%"
        filters.append(
            or_(
                User.email.ilike(term),
                User.full_name.ilike(term),
            )
        )

    if filters:
        query = query.where(*filters)
        count_query = count_query.where(*filters)

    total = await db.scalar(count_query) or 0

    result = await db.execute(
        query.order_by(User.created_at.desc()).offset(skip).limit(limit)
    )
    users = result.scalars().all()

    return {
        "items": [
            {
                "id": user.id,
                "full_name": user.full_name,
                "email": user.email,
                "role": user.role,
                "school_id": user.school_id,
                "school_name": user.school.name if user.school else None,
                "is_active": user.is_active,
            }
            for user in users
        ],
        "total": total,
        "skip": skip,
        "limit": limit,
    }


@router.get("/courses")
async def platform_admin_courses(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    school_id: int | None = Query(default=None),
    search: str | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=8, ge=1, le=100),
):
    _ensure_platform_admin(current_user)

    query = select(Course).options(selectinload(Course.teacher))
    count_query = select(func.count()).select_from(Course)

    filters = []

    if school_id is not None:
        filters.append(Course.school_id == school_id)

    if search:
        term = f"%{search.strip()}%"
        filters.append(Course.title.ilike(term))

    if filters:
        query = query.where(*filters)
        count_query = count_query.where(*filters)

    total = await db.scalar(count_query) or 0

    result = await db.execute(
        query.order_by(Course.id.desc()).offset(skip).limit(limit)
    )
    courses = result.scalars().all()

    return {
        "items": [
            {
                "id": course.id,
                "title": course.title,
                "description": course.description,
                "teacher_id": course.teacher_id,
                "teacher_name": (
                    course.teacher.full_name
                    if getattr(course, "teacher", None)
                    else None
                ),
                "school_id": course.school_id,
                "published": course.published,
            }
            for course in courses
        ],
        "total": total,
        "skip": skip,
        "limit": limit,
    }


@router.post("/users/{user_id}/role")
async def platform_admin_update_user_role(
    user_id: int,
    payload: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _ensure_platform_admin(current_user)

    role = payload.get("role")
    if role not in {"student", "teacher", "admin"}:
        raise HTTPException(status_code=400, detail="Invalid role")

    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.role == "platform_admin":
        raise HTTPException(
            status_code=400,
            detail="Cannot modify platform admin role",
        )

    user.role = role
    await db.commit()
    await db.refresh(user)

    return {
        "id": user.id,
        "full_name": user.full_name,
        "email": user.email,
        "role": user.role,
        "school_id": user.school_id,
        "is_active": user.is_active,
    }


@router.post("/users/{user_id}/active")
async def platform_admin_toggle_user_active(
    user_id: int,
    payload: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _ensure_platform_admin(current_user)

    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.role == "platform_admin":
        raise HTTPException(
            status_code=400,
            detail="Cannot deactivate platform admin",
        )

    user.is_active = bool(payload.get("is_active"))
    await db.commit()
    await db.refresh(user)

    return {
        "id": user.id,
        "full_name": user.full_name,
        "email": user.email,
        "role": user.role,
        "school_id": user.school_id,
        "is_active": user.is_active,
    }


@router.post("/courses/{course_id}/publish")
async def platform_admin_set_course_published(
    course_id: int,
    payload: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _ensure_platform_admin(current_user)

    course = await db.get(Course, course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    course.published = bool(payload.get("published"))
    await db.commit()
    await db.refresh(course)

    return {
        "id": course.id,
        "title": course.title,
        "description": course.description,
        "teacher_id": course.teacher_id,
        "school_id": course.school_id,
        "published": course.published,
    }


@router.post("/courses/{course_id}/delete")
async def platform_admin_delete_course(
    course_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _ensure_platform_admin(current_user)

    course = await db.get(Course, course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    await db.delete(course)
    await db.commit()

    return {"success": True}
