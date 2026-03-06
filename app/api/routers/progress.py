from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from app.db.session import get_db
from app.api.deps import require_role
from app.models import Lesson, Progress, User
from app.schemas.progress import ProgressOut, MarkLessonIn

router = APIRouter()


@router.post("/lessons/{lesson_id}/progress", response_model=ProgressOut)
async def mark_lesson(
    lesson_id: int,
    payload: MarkLessonIn,
    db: AsyncSession = Depends(get_db),
    student: User = Depends(require_role("student", "admin")),
):
    res = await db.execute(select(Lesson).where(Lesson.id == lesson_id))
    lesson = res.scalar_one_or_none()
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")

    # Upsert progress (Postgres)
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
    res = await db.execute(select(Progress).where(Progress.student_id == student.id))
    return list(res.scalars().all())
