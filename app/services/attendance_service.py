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
        session = await self.get_session_or_404(
            data.attendance_session_id,
        )

        if session.school_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Attendance session is missing a school.",
            )

        if session.is_submitted:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Attendance register has already been submitted.",
            )

        return await self.repo.create_record(data)

    async def create_records_bulk(
        self,
        records: list[AttendanceRecordCreate],
    ) -> list[AttendanceRecord]:
        upserted_records: list[AttendanceRecord] = []

        if not records:
            return upserted_records

        session = await self.get_session_or_404(
            records[0].attendance_session_id,
        )

        if session.is_submitted:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Attendance register has already been submitted.",
            )

        submitted_by_id = records[0].marked_by_id

        for record_data in records:
            if record_data.attendance_session_id != session.id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        "Bulk attendance records must belong " "to the same session."
                    ),
                )

            existing_record = await self.repo.get_record_by_session_and_student(
                attendance_session_id=(record_data.attendance_session_id),
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

            created_record = await self.repo.create_record(
                record_data,
            )

            upserted_records.append(created_record)

        if submitted_by_id is not None:
            await self.repo.mark_session_submitted(
                session=session,
                submitted_by_id=submitted_by_id,
            )

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

        session = await self.get_session_or_404(
            record.attendance_session_id,
        )

        if session.is_submitted:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Attendance register has already been submitted.",
            )

        return await self.repo.update_record(record, data)

    async def reopen_register(
        self,
        session_id: int,
    ) -> AttendanceSession:
        session = await self.get_session_or_404(session_id)

        if not session.is_submitted:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Attendance register is already open.",
            )

        session.is_submitted = False
        session.submitted_at = None
        session.submitted_by_id = None

        await self.repo.db.commit()
        await self.repo.db.refresh(session)

        return session

    async def list_absence_requests(
        self,
        filters: AbsenceRequestFilter,
    ) -> list[AbsenceRequest]:
        return await self.repo.list_absence_requests(filters)
