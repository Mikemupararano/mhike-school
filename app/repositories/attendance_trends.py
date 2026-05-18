from __future__ import annotations

from datetime import date

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.attendance_record import AttendanceRecord
from app.models.attendance_session import AttendanceSession


class AttendanceTrendsRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_daily_status_counts(
        self,
        school_id: int,
        start_date: date,
        end_date: date,
    ) -> list[tuple[date, str, int]]:
        result = await self.db.execute(
            select(
                AttendanceSession.session_date,
                AttendanceRecord.status,
                func.count(AttendanceRecord.id),
            )
            .join(
                AttendanceSession,
                AttendanceRecord.attendance_session_id == AttendanceSession.id,
            )
            .where(
                AttendanceSession.school_id == school_id,
                AttendanceSession.session_date >= start_date,
                AttendanceSession.session_date <= end_date,
            )
            .group_by(
                AttendanceSession.session_date,
                AttendanceRecord.status,
            )
            .order_by(AttendanceSession.session_date.asc())
        )

        return list(result.all())
