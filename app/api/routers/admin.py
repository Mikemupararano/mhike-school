from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_role
from app.db.session import get_db
from app.models.course import Course
from app.models.enrollment import Enrollment
from app.models.user import User

router = APIRouter(prefix="/admin", tags=["admin"])


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
        select(func.count()).select_from(Course).where(Course.published == True)
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
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_role("admin")),
):
    res = await db.execute(select(User).order_by(User.id.desc()))
    users = res.scalars().all()

    return [
        {
            "id": u.id,
            "full_name": u.full_name,
            "email": u.email,
            "role": u.role,
            "is_active": getattr(u, "is_active", True),
        }
        for u in users
    ]


@router.get("/courses")
async def admin_courses(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_role("admin")),
):
    res = await db.execute(select(Course).order_by(Course.id.desc()))
    courses = res.scalars().all()

    return [
        {
            "id": c.id,
            "title": c.title,
            "description": c.description,
            "teacher_id": c.teacher_id,
            "published": c.published,
        }
        for c in courses
    ]
