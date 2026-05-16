from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.attendance_record import AttendanceRecord
from app.models.attendance_session import AttendanceSession
from app.repositories.attendance import AttendanceRepository
from app.schemas.attendance import (
    AbsenceRequestFilter,
    AttendanceFilter,
    AttendanceRecordCreate,
    AttendanceRecordUpdate,
    AttendanceSessionCreate,
)


class AttendanceService:
    def __init__(self, db: AsyncSession):
        self.repo = AttendanceRepository(db)

    async def create_session(
        self,
        data: AttendanceSessionCreate,
    ) -> AttendanceSession:
        return await self.repo.create_session(data)

    async def get_session_or_404(
        self,
        session_id: int,
    ) -> AttendanceSession:
        session = await self.repo.get_session_by_id(session_id)

        if session is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Attendance session not found.",
            )

        return session

    async def list_sessions(
        self,
        filters: AttendanceFilter,
    ) -> list[AttendanceSession]:
        return await self.repo.list_sessions(filters)

    async def create_record(
        self,
        data: AttendanceRecordCreate,
    ) -> AttendanceRecord:
        session = await self.get_session_or_404(data.attendance_session_id)

        if session.school_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Attendance session is missing a school.",
            )

        return await self.repo.create_record(data)

    async def get_record_or_404(
        self,
        record_id: int,
    ) -> AttendanceRecord:
        record = await self.repo.get_record_by_id(record_id)

        if record is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Attendance record not found.",
            )

        return record

    async def list_records(
        self,
        filters: AttendanceFilter,
    ) -> list[AttendanceRecord]:
        return await self.repo.list_records(filters)

    async def update_record(
        self,
        record_id: int,
        data: AttendanceRecordUpdate,
    ) -> AttendanceRecord:
        record = await self.get_record_or_404(record_id)

        return await self.repo.update_record(record, data)

    async def list_absence_requests(
        self,
        filters: AbsenceRequestFilter,
    ):
        return await self.repo.list_absence_requests(filters)
