from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_current_school_id
from app.db.session import get_db
from app.models.course import Course
from app.models.user import User

router = APIRouter()


@router.get("/me")
async def get_my_courses(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    school_id: int = Depends(get_current_school_id),
):
    result = await db.execute(
        select(Course).where(
            Course.teacher_id == current_user.id,
            Course.school_id == school_id,
        )
    )

    courses = result.scalars().all()

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
