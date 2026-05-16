from __future__ import annotations

from datetime import date

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.attendance_record import AttendanceRecord
from app.models.attendance_session import AttendanceSession


class AttendanceDashboardRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def count_records_by_status(
        self,
        school_id: int,
        summary_date: date,
    ) -> dict[str, int]:
        result = await self.db.execute(
            select(
                AttendanceRecord.status,
                func.count(AttendanceRecord.id),
            )
            .join(
                AttendanceSession,
                AttendanceRecord.attendance_session_id == AttendanceSession.id,
            )
            .where(
                AttendanceSession.school_id == school_id,
                AttendanceSession.session_date == summary_date,
            )
            .group_by(AttendanceRecord.status)
        )

        return {str(status): count for status, count in result.all()}

    async def count_registers(
        self,
        school_id: int,
        summary_date: date,
        is_submitted: bool,
    ) -> int:
        result = await self.db.execute(
            select(func.count(AttendanceSession.id)).where(
                AttendanceSession.school_id == school_id,
                AttendanceSession.session_date == summary_date,
                AttendanceSession.is_submitted == is_submitted,
            )
        )

        return int(result.scalar_one() or 0)

    async def list_register_summaries(
        self,
        school_id: int,
        summary_date: date,
    ) -> list[tuple[AttendanceSession, int]]:
        result = await self.db.execute(
            select(
                AttendanceSession,
                func.count(AttendanceRecord.id),
            )
            .outerjoin(
                AttendanceRecord,
                AttendanceRecord.attendance_session_id == AttendanceSession.id,
            )
            .where(
                AttendanceSession.school_id == school_id,
                AttendanceSession.session_date == summary_date,
            )
            .group_by(AttendanceSession.id)
            .order_by(
                AttendanceSession.session_type.asc(),
                AttendanceSession.id.asc(),
            )
        )

        return list(result.all())

    async def list_class_status_summaries(
        self,
        school_id: int,
        summary_date: date,
    ) -> list[tuple[int, str, int]]:
        result = await self.db.execute(
            select(
                AttendanceSession.class_group_id,
                AttendanceRecord.status,
                func.count(AttendanceRecord.id),
            )
            .join(
                AttendanceSession,
                AttendanceRecord.attendance_session_id == AttendanceSession.id,
            )
            .where(
                AttendanceSession.school_id == school_id,
                AttendanceSession.session_date == summary_date,
            )
            .group_by(
                AttendanceSession.class_group_id,
                AttendanceRecord.status,
            )
        )

        return list(result.all())
