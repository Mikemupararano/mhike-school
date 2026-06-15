from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.report_session import ReportSession
from app.schemas.report_session import ReportSessionCreate, ReportSessionUpdate


async def create_report_session(
    db: AsyncSession,
    *,
    school_id: int,
    payload: ReportSessionCreate,
) -> ReportSession:
    session = ReportSession(
        school_id=school_id,
        **payload.model_dump(),
    )

    db.add(session)
    await db.commit()
    await db.refresh(session)

    return session


async def list_report_sessions(
    db: AsyncSession,
    *,
    school_id: int,
) -> list[ReportSession]:
    result = await db.execute(
        select(ReportSession)
        .where(ReportSession.school_id == school_id)
        .order_by(ReportSession.created_at.desc()),
    )

    return list(result.scalars().all())


async def get_report_session(
    db: AsyncSession,
    *,
    school_id: int,
    report_session_id: int,
) -> ReportSession | None:
    result = await db.execute(
        select(ReportSession).where(
            ReportSession.id == report_session_id,
            ReportSession.school_id == school_id,
        ),
    )

    return result.scalar_one_or_none()


async def update_report_session(
    db: AsyncSession,
    *,
    session: ReportSession,
    payload: ReportSessionUpdate,
) -> ReportSession:
    update_data = payload.model_dump(exclude_unset=True)

    for key, value in update_data.items():
        setattr(session, key, value)

    await db.commit()
    await db.refresh(session)

    return session


async def delete_report_session(
    db: AsyncSession,
    *,
    session: ReportSession,
) -> None:
    await db.delete(session)
    await db.commit()
