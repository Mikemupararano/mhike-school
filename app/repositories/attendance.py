from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.absence_request import AbsenceRequest
from app.models.attendance_record import AttendanceRecord
from app.models.attendance_session import (
    AttendanceSession,
    AttendanceSessionType,
)
from app.schemas.attendance import (
    AbsenceRequestFilter,
    AttendanceFilter,
    AttendanceRecordCreate,
    AttendanceRecordUpdate,
    AttendanceSessionCreate,
)


class AttendanceRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_existing_session(
        self,
        school_id: int,
        class_group_id: int,
        session_date: date,
        session_type: AttendanceSessionType,
    ) -> AttendanceSession | None:
        result = await self.db.execute(
            select(AttendanceSession).where(
                AttendanceSession.school_id == school_id,
                AttendanceSession.class_group_id == class_group_id,
                AttendanceSession.session_date == session_date,
                AttendanceSession.session_type == session_type,
            )
        )

        return result.scalar_one_or_none()

    async def create_session(
        self,
        data: AttendanceSessionCreate,
    ) -> AttendanceSession:
        session = AttendanceSession(**data.model_dump())

        self.db.add(session)
        await self.db.flush()
        await self.db.refresh(session)

        return session

    async def get_session_by_id(
        self,
        session_id: int,
    ) -> AttendanceSession | None:
        result = await self.db.execute(
            select(AttendanceSession).where(AttendanceSession.id == session_id)
        )

        return result.scalar_one_or_none()

    async def list_sessions(
        self,
        filters: AttendanceFilter,
    ) -> list[AttendanceSession]:
        query = select(AttendanceSession).order_by(
            AttendanceSession.session_date.desc(),
            AttendanceSession.id.desc(),
        )

        if filters.school_id is not None:
            query = query.where(AttendanceSession.school_id == filters.school_id)

        if filters.class_group_id is not None:
            query = query.where(
                AttendanceSession.class_group_id == filters.class_group_id
            )

        if filters.session_date is not None:
            query = query.where(AttendanceSession.session_date == filters.session_date)

        if filters.session_type is not None:
            query = query.where(AttendanceSession.session_type == filters.session_type)

        if filters.timetable_entry_id is not None:
            query = query.where(
                AttendanceSession.timetable_entry_id == filters.timetable_entry_id
            )

        if filters.timetable_period_id is not None:
            query = query.where(
                AttendanceSession.timetable_period_id == filters.timetable_period_id
            )

        query = query.offset(filters.offset).limit(filters.limit)

        result = await self.db.execute(query)

        return list(result.scalars().all())

    async def create_record(
        self,
        data: AttendanceRecordCreate,
    ) -> AttendanceRecord:
        record = AttendanceRecord(**data.model_dump())

        self.db.add(record)
        await self.db.flush()
        await self.db.refresh(record)

        return record

    async def get_record_by_id(
        self,
        record_id: int,
    ) -> AttendanceRecord | None:
        result = await self.db.execute(
            select(AttendanceRecord).where(AttendanceRecord.id == record_id)
        )

        return result.scalar_one_or_none()

    async def list_records(
        self,
        filters: AttendanceFilter,
    ) -> list[AttendanceRecord]:
        query = (
            select(AttendanceRecord)
            .join(
                AttendanceSession,
                AttendanceRecord.attendance_session_id == AttendanceSession.id,
            )
            .order_by(AttendanceRecord.id.desc())
        )

        if filters.school_id is not None:
            query = query.where(AttendanceSession.school_id == filters.school_id)

        if filters.class_group_id is not None:
            query = query.where(
                AttendanceSession.class_group_id == filters.class_group_id
            )

        if filters.student_id is not None:
            query = query.where(AttendanceRecord.student_id == filters.student_id)

        if filters.session_date is not None:
            query = query.where(AttendanceSession.session_date == filters.session_date)

        if filters.session_type is not None:
            query = query.where(AttendanceSession.session_type == filters.session_type)

        if filters.status is not None:
            query = query.where(AttendanceRecord.status == filters.status)

        if filters.timetable_entry_id is not None:
            query = query.where(
                AttendanceSession.timetable_entry_id == filters.timetable_entry_id
            )

        if filters.timetable_period_id is not None:
            query = query.where(
                AttendanceSession.timetable_period_id == filters.timetable_period_id
            )

        query = query.offset(filters.offset).limit(filters.limit)

        result = await self.db.execute(query)

        return list(result.scalars().all())

    async def update_record(
        self,
        record: AttendanceRecord,
        data: AttendanceRecordUpdate,
    ) -> AttendanceRecord:
        update_data = data.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            setattr(record, field, value)

        self.db.add(record)
        await self.db.flush()
        await self.db.refresh(record)

        return record

    async def list_absence_requests(
        self,
        filters: AbsenceRequestFilter,
    ) -> list[AbsenceRequest]:
        query = select(AbsenceRequest).order_by(
            AbsenceRequest.created_at.desc(),
            AbsenceRequest.id.desc(),
        )

        if filters.school_id is not None:
            query = query.where(AbsenceRequest.school_id == filters.school_id)

        if filters.student_id is not None:
            query = query.where(AbsenceRequest.student_id == filters.student_id)

        if filters.absence_type is not None:
            query = query.where(AbsenceRequest.absence_type == filters.absence_type)

        if filters.status is not None:
            query = query.where(AbsenceRequest.status == filters.status)

        if filters.start_date_from is not None:
            query = query.where(AbsenceRequest.start_date >= filters.start_date_from)

        if filters.start_date_to is not None:
            query = query.where(AbsenceRequest.start_date <= filters.start_date_to)

        query = query.offset(filters.offset).limit(filters.limit)

        result = await self.db.execute(query)

        return list(result.scalars().all())
