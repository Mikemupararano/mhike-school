from __future__ import annotations

from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.attendance_dashboard import AttendanceDashboardRepository
from app.schemas.attendance_dashboard import (
    AttendanceClassSummary,
    AttendanceDashboardSummary,
    AttendanceRegisterSummary,
)


class AttendanceDashboardService:
    def __init__(self, db: AsyncSession):
        self.repo = AttendanceDashboardRepository(db)

    async def get_school_summary(
        self,
        school_id: int,
        summary_date: date,
    ) -> AttendanceDashboardSummary:
        status_counts = await self.repo.count_records_by_status(
            school_id=school_id,
            summary_date=summary_date,
        )

        submitted_registers = await self.repo.count_registers(
            school_id=school_id,
            summary_date=summary_date,
            is_submitted=True,
        )

        unsubmitted_registers = await self.repo.count_registers(
            school_id=school_id,
            summary_date=summary_date,
            is_submitted=False,
        )

        register_rows = await self.repo.list_register_summaries(
            school_id=school_id,
            summary_date=summary_date,
        )

        class_rows = await self.repo.list_class_status_summaries(
            school_id=school_id,
            summary_date=summary_date,
        )

        registers = [
            AttendanceRegisterSummary(
                session_id=session.id,
                class_group_id=session.class_group_id,
                class_name=class_name,
                session_date=session.session_date,
                session_type=str(session.session_type),
                is_submitted=session.is_submitted,
                total_records=total_records,
            )
            for session, class_name, total_records in register_rows
        ]

        class_summary_map: dict[int, AttendanceClassSummary] = {}

        for class_group_id, class_name, status, count in class_rows:
            if class_group_id not in class_summary_map:
                class_summary_map[class_group_id] = AttendanceClassSummary(
                    class_group_id=class_group_id,
                    class_name=class_name,
                    total_records=0,
                    present=0,
                    late=0,
                    authorised_absence=0,
                    unauthorised_absence=0,
                )

            summary = class_summary_map[class_group_id]
            status_key = str(status)

            summary.total_records += count

            if status_key == "present":
                summary.present += count
            elif status_key == "late":
                summary.late += count
            elif status_key == "authorised_absence":
                summary.authorised_absence += count
            elif status_key == "unauthorised_absence":
                summary.unauthorised_absence += count

        return AttendanceDashboardSummary(
            school_id=school_id,
            summary_date=summary_date,
            total_records=sum(status_counts.values()),
            submitted_registers=submitted_registers,
            unsubmitted_registers=unsubmitted_registers,
            present=status_counts.get("present", 0),
            late=status_counts.get("late", 0),
            authorised_absence=status_counts.get("authorised_absence", 0),
            unauthorised_absence=status_counts.get(
                "unauthorised_absence",
                0,
            ),
            registers=registers,
            classes=list(class_summary_map.values()),
        )
