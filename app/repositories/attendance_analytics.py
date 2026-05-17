from __future__ import annotations

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.attendance_record import AttendanceRecord
from app.models.attendance_session import AttendanceSession
from app.models.class_group import ClassGroup
from app.models.enrollment import Enrollment
from app.models.user import User


class AttendanceAnalyticsRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_persistent_absentees(
        self,
        school_id: int,
        threshold_percentage: float = 90.0,
    ) -> list[dict]:
        absence_case = case(
            (
                AttendanceRecord.status.in_(
                    [
                        "authorised_absence",
                        "unauthorised_absence",
                    ]
                ),
                1,
            ),
            else_=0,
        )

        unauthorised_case = case(
            (
                AttendanceRecord.status == "unauthorised_absence",
                1,
            ),
            else_=0,
        )

        result = await self.db.execute(
            select(
                User.id.label("student_id"),
                User.email.label("student_name"),
                ClassGroup.id.label("class_group_id"),
                ClassGroup.name.label("class_name"),
                func.count(AttendanceRecord.id).label("total_records"),
                func.sum(absence_case).label("absence_count"),
                func.sum(unauthorised_case).label(
                    "unauthorised_absence_count",
                ),
            )
            .join(
                AttendanceRecord,
                AttendanceRecord.student_id == User.id,
            )
            .join(
                AttendanceSession,
                AttendanceRecord.attendance_session_id == AttendanceSession.id,
            )
            .outerjoin(
                Enrollment,
                Enrollment.user_id == User.id,
            )
            .outerjoin(
                ClassGroup,
                Enrollment.class_id == ClassGroup.id,
            )
            .where(
                AttendanceSession.school_id == school_id,
            )
            .group_by(
                User.id,
                User.email,
                ClassGroup.id,
                ClassGroup.name,
            )
        )

        rows = result.all()

        persistent_absentees: list[dict] = []

        for row in rows:
            total_records = int(row.total_records or 0)
            absence_count = int(row.absence_count or 0)

            if total_records == 0:
                continue

            attendance_percentage = (
                (total_records - absence_count) / total_records
            ) * 100

            if attendance_percentage > threshold_percentage:
                continue

            persistent_absentees.append(
                {
                    "student_id": row.student_id,
                    "student_name": row.student_name,
                    "class_group_id": row.class_group_id,
                    "class_name": row.class_name,
                    "total_records": total_records,
                    "absence_count": absence_count,
                    "unauthorised_absence_count": int(
                        row.unauthorised_absence_count or 0,
                    ),
                    "absence_percentage": round(
                        (absence_count / total_records) * 100,
                        2,
                    ),
                },
            )

        persistent_absentees.sort(
            key=lambda item: (
                item["absence_percentage"],
                item["unauthorised_absence_count"],
            ),
            reverse=True,
        )

        return persistent_absentees
