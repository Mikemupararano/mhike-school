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
from app.models.school import School
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
    school_id = admin.school_id

    school = await db.get(School, school_id)
    school_name = school.name if school else "Unknown School"

    total_users = await db.scalar(
        select(func.count()).select_from(User).where(User.school_id == school_id)
    )
    total_students = await db.scalar(
        select(func.count())
        .select_from(User)
        .where(
            User.school_id == school_id,
            User.role == "student",
        )
    )
    total_teachers = await db.scalar(
        select(func.count())
        .select_from(User)
        .where(
            User.school_id == school_id,
            User.role == "teacher",
        )
    )
    total_admins = await db.scalar(
        select(func.count())
        .select_from(User)
        .where(
            User.school_id == school_id,
            User.role == "admin",
        )
    )
    total_courses = await db.scalar(
        select(func.count()).select_from(Course).where(Course.school_id == school_id)
    )
    published_courses = await db.scalar(
        select(func.count())
        .select_from(Course)
        .where(
            Course.school_id == school_id,
            Course.published.is_(True),
        )
    )
    total_enrollments = await db.scalar(
        select(func.count())
        .select_from(Enrollment)
        .join(Course, Enrollment.course_id == Course.id)
        .where(Course.school_id == school_id)
    )

    return {
        "school_id": school_id,
        "school_name": school_name,
        "total_users": total_users or 0,
        "total_students": total_students or 0,
        "total_teachers": total_teachers or 0,
        "total_admins": total_admins or 0,
        "total_courses": total_courses or 0,
        "published_courses": published_courses or 0,
        "total_enrollments": total_enrollments or 0,
    }
