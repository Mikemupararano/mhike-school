from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.absence_request import AbsenceRequest
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
        existing_session = await self.repo.get_existing_session(
            school_id=data.school_id,
            class_group_id=data.class_group_id,
            session_date=data.session_date,
            session_type=data.session_type,
        )

        if existing_session is not None:
            return existing_session

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

    async def create_records_bulk(
        self,
        records: list[AttendanceRecordCreate],
    ) -> list[AttendanceRecord]:
        upserted_records: list[AttendanceRecord] = []

        for record_data in records:
            await self.get_session_or_404(record_data.attendance_session_id)

            existing_record = await self.repo.get_record_by_session_and_student(
                attendance_session_id=record_data.attendance_session_id,
                student_id=record_data.student_id,
            )

            if existing_record is not None:
                updated_record = await self.repo.update_record(
                    existing_record,
                    AttendanceRecordUpdate(
                        status=record_data.status,
                        notes=record_data.notes,
                    ),
                )

                if record_data.marked_by_id is not None:
                    updated_record.marked_by_id = record_data.marked_by_id

                upserted_records.append(updated_record)
                continue

            created_record = await self.repo.create_record(record_data)
            upserted_records.append(created_record)

        return upserted_records

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
    ) -> list[AbsenceRequest]:
        return await self.repo.list_absence_requests(filters)
