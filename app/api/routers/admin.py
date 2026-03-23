from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_role
from app.db.session import get_db
from app.models.course import Course
from app.models.enrollment import Enrollment
from app.models.lesson import Lesson
from app.models.module import Module
from app.models.user import User

router = APIRouter(prefix="/admin", tags=["admin"])


class RoleUpdateIn(BaseModel):
    role: str


class ActiveUpdateIn(BaseModel):
    is_active: bool


class PublishUpdateIn(BaseModel):
    published: bool


@router.get("/stats")
async def admin_stats(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_role("admin")),
):
    total_users = await db.scalar(select(func.count()).select_from(User))
    total_students = await db.scalar(
        select(func.count()).select_from(User).where(User.role == "student")
    )
    total_teachers = await db.scalar(
        select(func.count()).select_from(User).where(User.role == "teacher")
    )
    total_admins = await db.scalar(
        select(func.count()).select_from(User).where(User.role == "admin")
    )
    total_courses = await db.scalar(select(func.count()).select_from(Course))
    published_courses = await db.scalar(
        select(func.count()).select_from(Course).where(Course.published.is_(True))
    )
    total_enrollments = await db.scalar(select(func.count()).select_from(Enrollment))

    return {
        "total_users": total_users or 0,
        "total_students": total_students or 0,
        "total_teachers": total_teachers or 0,
        "total_admins": total_admins or 0,
        "total_courses": total_courses or 0,
        "published_courses": published_courses or 0,
        "total_enrollments": total_enrollments or 0,
    }


@router.get("/users")
async def admin_users(
    role: Optional[str] = Query(default=None),
    search: Optional[str] = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=8, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_role("admin")),
):
    stmt = select(User)

    if role and role != "all":
        stmt = stmt.where(User.role == role)

    if search:
        pattern = f"%{search.strip()}%"
        stmt = stmt.where(
            or_(
                User.full_name.ilike(pattern),
                User.email.ilike(pattern),
            )
        )

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = await db.scalar(count_stmt)

    stmt = stmt.order_by(User.id.desc()).offset(skip).limit(limit)
    res = await db.execute(stmt)
    users = res.scalars().all()

    return {
        "items": [
            {
                "id": u.id,
                "full_name": u.full_name,
                "email": u.email,
                "role": u.role,
                "is_active": getattr(u, "is_active", True),
            }
            for u in users
        ],
        "total": total or 0,
        "skip": skip,
        "limit": limit,
    }


@router.get("/courses")
async def admin_courses(
    search: Optional[str] = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=8, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_role("admin")),
):
    stmt = select(Course)

    if search:
        pattern = f"%{search.strip()}%"
        stmt = stmt.where(
            or_(
                Course.title.ilike(pattern),
                Course.description.ilike(pattern),
            )
        )

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = await db.scalar(count_stmt)

    stmt = stmt.order_by(Course.id.desc()).offset(skip).limit(limit)
    res = await db.execute(stmt)
    courses = res.scalars().all()

    return {
        "items": [
            {
                "id": c.id,
                "title": c.title,
                "description": c.description,
                "teacher_id": c.teacher_id,
                "published": c.published,
            }
            for c in courses
        ],
        "total": total or 0,
        "skip": skip,
        "limit": limit,
    }


@router.post("/users/{user_id}/role")
async def admin_update_user_role(
    user_id: int,
    body: RoleUpdateIn,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_role("admin")),
):
    if body.role not in {"student", "teacher", "admin"}:
        raise HTTPException(status_code=400, detail="Invalid role")

    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.role = body.role
    await db.commit()
    await db.refresh(user)

    return {
        "id": user.id,
        "full_name": user.full_name,
        "email": user.email,
        "role": user.role,
        "is_active": getattr(user, "is_active", True),
    }


@router.post("/users/{user_id}/active")
async def admin_update_user_active(
    user_id: int,
    body: ActiveUpdateIn,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_role("admin")),
):
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if not hasattr(user, "is_active"):
        raise HTTPException(
            status_code=400,
            detail="User model does not support is_active yet",
        )

    user.is_active = body.is_active
    await db.commit()
    await db.refresh(user)

    return {
        "id": user.id,
        "full_name": user.full_name,
        "email": user.email,
        "role": user.role,
        "is_active": user.is_active,
    }


@router.post("/courses/{course_id}/publish")
async def admin_set_course_publish(
    course_id: int,
    body: PublishUpdateIn,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_role("admin")),
):
    course = await db.get(Course, course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    course.published = body.published
    await db.commit()
    await db.refresh(course)

    return {
        "id": course.id,
        "title": course.title,
        "description": course.description,
        "teacher_id": course.teacher_id,
        "published": course.published,
    }


@router.post("/courses/{course_id}/delete")
async def admin_delete_course(
    course_id: int,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_role("admin")),
):
    course = await db.get(Course, course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    module_ids_result = await db.execute(
        select(Module.id).where(Module.course_id == course_id)
    )
    module_ids = list(module_ids_result.scalars().all())

    if module_ids:
        await db.execute(delete(Lesson).where(Lesson.module_id.in_(module_ids)))
        await db.execute(delete(Module).where(Module.id.in_(module_ids)))

    await db.execute(delete(Enrollment).where(Enrollment.course_id == course_id))
    await db.delete(course)
    await db.commit()

    return {"success": True}
