from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.attendance_analytics import AttendanceAnalyticsRepository
from app.schemas.attendance_analytics import (
    AttendanceAnalyticsSummary,
    PersistentAbsenteeSummary,
)


class AttendanceAnalyticsService:
    def __init__(self, db: AsyncSession):
        self.repo = AttendanceAnalyticsRepository(db)

    async def get_school_analytics(
        self,
        school_id: int,
        persistent_absence_threshold: float = 90.0,
    ) -> AttendanceAnalyticsSummary:
        rows = await self.repo.get_persistent_absentees(
            school_id=school_id,
            threshold_percentage=persistent_absence_threshold,
        )

        return AttendanceAnalyticsSummary(
            school_id=school_id,
            persistent_absence_threshold=persistent_absence_threshold,
            persistent_absentees=[PersistentAbsenteeSummary(**row) for row in rows],
        )
