from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.attendance_record import AttendanceRecord
from app.repositories.attendance import AttendanceRepository
from app.schemas.attendance import (
    AttendanceRecordBulkUpdate,
    AttendanceRecordUpdate,
)


class AttendanceBulkService:
    def __init__(self, db: AsyncSession):
        self.repo = AttendanceRepository(db)

    async def update_records_bulk(
        self,
        data: AttendanceRecordBulkUpdate,
    ) -> list[AttendanceRecord]:
        updated_records: list[AttendanceRecord] = []

        for item in data.records:
            record = await self.repo.get_record_by_id(item.record_id)

            if record is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Attendance record {item.record_id} not found.",
                )

            session = await self.repo.get_session_by_id(
                record.attendance_session_id,
            )

            if session is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Attendance session not found.",
                )

            if session.is_submitted:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        "Cannot bulk update records from a submitted "
                        "attendance register."
                    ),
                )

            updated_record = await self.repo.update_record(
                record,
                AttendanceRecordUpdate(
                    status=item.status,
                    notes=item.notes,
                ),
            )

            updated_records.append(updated_record)

        return updated_records
