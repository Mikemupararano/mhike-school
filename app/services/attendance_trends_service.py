from __future__ import annotations

from collections import defaultdict
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.attendance_trends import (
    AttendanceTrendsRepository,
)
from app.schemas.attendance_trends import (
    AttendanceTrendPoint,
    AttendanceTrendSummary,
)


class AttendanceTrendsService:
    def __init__(self, db: AsyncSession):
        self.repo = AttendanceTrendsRepository(db)

    async def get_trends(
        self,
        school_id: int,
        start_date: date,
        end_date: date,
    ) -> AttendanceTrendSummary:
        rows = await self.repo.list_daily_status_counts(
            school_id=school_id,
            start_date=start_date,
            end_date=end_date,
        )

        grouped: dict[date, dict[str, int]] = defaultdict(
            lambda: {
                "present": 0,
                "late": 0,
                "authorised_absence": 0,
                "unauthorised_absence": 0,
            }
        )

        for trend_date, status, count in rows:
            grouped[trend_date][str(status)] = int(count)

        points: list[AttendanceTrendPoint] = []

        for trend_date in sorted(grouped.keys()):
            values = grouped[trend_date]

            present = values["present"]
            late = values["late"]
            authorised_absence = values["authorised_absence"]
            unauthorised_absence = values["unauthorised_absence"]

            total_records = present + late + authorised_absence + unauthorised_absence

            attendance_percentage = (
                round(
                    ((present + late) / total_records) * 100,
                    2,
                )
                if total_records > 0
                else 0.0
            )

            points.append(
                AttendanceTrendPoint(
                    trend_date=trend_date,
                    total_records=total_records,
                    present=present,
                    late=late,
                    authorised_absence=authorised_absence,
                    unauthorised_absence=unauthorised_absence,
                    attendance_percentage=attendance_percentage,
                )
            )

        return AttendanceTrendSummary(
            school_id=school_id,
            start_date=start_date,
            end_date=end_date,
            points=points,
        )
