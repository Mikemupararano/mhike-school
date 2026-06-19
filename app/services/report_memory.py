from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.report_memory import ReportMemory
from app.schemas.report_memory import ReportMemoryCreate


async def create_report_memory(
    db: AsyncSession,
    payload: ReportMemoryCreate,
) -> ReportMemory:
    memory = ReportMemory(**payload.model_dump())

    db.add(memory)
    await db.commit()
    await db.refresh(memory)

    return memory


async def list_school_report_memory(
    db: AsyncSession,
    *,
    school_id: int,
    subject: str | None = None,
    year_group: str | None = None,
    limit: int = 20,
) -> list[ReportMemory]:
    query = select(ReportMemory).where(
        ReportMemory.school_id == school_id,
        ReportMemory.approved.is_(True),
    )

    if subject:
        query = query.where(ReportMemory.subject.ilike(f"%{subject}%"))

    if year_group:
        query = query.where(ReportMemory.year_group == year_group)

    query = query.order_by(ReportMemory.created_at.desc()).limit(limit)

    result = await db.execute(query)

    return list(result.scalars().all())


async def find_similar_report_memory(
    db: AsyncSession,
    *,
    school_id: int,
    subject: str,
    year_group: str | None = None,
    teacher_notes: str | None = None,
    limit: int = 10,
) -> list[ReportMemory]:
    memories = await list_school_report_memory(
        db,
        school_id=school_id,
        subject=subject,
        year_group=year_group,
        limit=50,
    )

    if not teacher_notes:
        return memories[:limit]

    keywords = {
        word.strip(".,!?").lower()
        for word in teacher_notes.split()
        if len(word.strip(".,!?")) >= 5
    }

    scored: list[tuple[int, ReportMemory]] = []

    for memory in memories:
        searchable_text = " ".join(
            [
                memory.teacher_notes or "",
                memory.final_report or "",
                memory.topics_studied or "",
            ],
        ).lower()

        score = sum(1 for keyword in keywords if keyword in searchable_text)

        scored.append((score, memory))

    scored.sort(key=lambda item: item[0], reverse=True)

    return [memory for score, memory in scored[:limit] if score > 0] or memories[:limit]
