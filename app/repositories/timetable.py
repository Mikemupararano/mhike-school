from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.timetable import Timetable
from app.models.timetable_assignment import TimetableAssignment
from app.models.timetable_entry import TimetableEntry
from app.models.timetable_period import TimetablePeriod
from app.schemas.timetable import (
    TimetableAssignmentCreate,
    TimetableAssignmentFilter,
    TimetableCreate,
    TimetableEntryCreate,
    TimetableEntryFilter,
    TimetableFilter,
    TimetablePeriodCreate,
)


class TimetableRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_period(self, data: TimetablePeriodCreate) -> TimetablePeriod:
        period = TimetablePeriod(**data.model_dump())

        self.db.add(period)
        await self.db.flush()
        await self.db.refresh(period)

        return period

    async def list_periods(self, school_id: int) -> list[TimetablePeriod]:
        result = await self.db.execute(
            select(TimetablePeriod)
            .where(TimetablePeriod.school_id == school_id)
            .order_by(TimetablePeriod.period_number.asc())
        )

        return list(result.scalars().all())

    async def create_timetable(self, data: TimetableCreate) -> Timetable:
        timetable = Timetable(**data.model_dump())

        self.db.add(timetable)
        await self.db.flush()
        await self.db.refresh(timetable)

        return timetable

    async def list_timetables(self, filters: TimetableFilter) -> list[Timetable]:
        query = select(Timetable).order_by(
            Timetable.effective_from.desc(),
            Timetable.id.desc(),
        )

        if filters.school_id is not None:
            query = query.where(Timetable.school_id == filters.school_id)

        if filters.academic_year is not None:
            query = query.where(Timetable.academic_year == filters.academic_year)

        if filters.is_active is not None:
            query = query.where(Timetable.is_active == filters.is_active)

        query = query.offset(filters.offset).limit(filters.limit)

        result = await self.db.execute(query)

        return list(result.scalars().all())

    async def get_timetable_by_id(self, timetable_id: int) -> Timetable | None:
        result = await self.db.execute(
            select(Timetable).where(Timetable.id == timetable_id)
        )

        return result.scalar_one_or_none()

    async def create_entry(self, data: TimetableEntryCreate) -> TimetableEntry:
        entry = TimetableEntry(**data.model_dump())

        self.db.add(entry)
        await self.db.flush()
        await self.db.refresh(entry)

        return entry

    async def list_entries(
        self,
        filters: TimetableEntryFilter,
    ) -> list[TimetableEntry]:
        query = select(TimetableEntry).order_by(
            TimetableEntry.day_of_week.asc(),
            TimetableEntry.timetable_period_id.asc(),
            TimetableEntry.id.asc(),
        )

        if filters.school_id is not None:
            query = query.where(TimetableEntry.school_id == filters.school_id)

        if filters.timetable_id is not None:
            query = query.where(TimetableEntry.timetable_id == filters.timetable_id)

        if filters.class_group_id is not None:
            query = query.where(TimetableEntry.class_group_id == filters.class_group_id)

        if filters.course_id is not None:
            query = query.where(TimetableEntry.course_id == filters.course_id)

        if filters.teacher_id is not None:
            query = query.where(TimetableEntry.teacher_id == filters.teacher_id)

        if filters.day_of_week is not None:
            query = query.where(TimetableEntry.day_of_week == filters.day_of_week)

        query = query.offset(filters.offset).limit(filters.limit)

        result = await self.db.execute(query)

        return list(result.scalars().all())

    async def create_assignment(
        self,
        data: TimetableAssignmentCreate,
    ) -> TimetableAssignment:
        assignment = TimetableAssignment(**data.model_dump())

        self.db.add(assignment)
        await self.db.flush()
        await self.db.refresh(assignment)

        return assignment

    async def list_assignments(
        self,
        filters: TimetableAssignmentFilter,
    ) -> list[TimetableAssignment]:
        query = select(TimetableAssignment).order_by(TimetableAssignment.id.desc())

        if filters.school_id is not None:
            query = query.where(TimetableAssignment.school_id == filters.school_id)

        if filters.timetable_id is not None:
            query = query.where(
                TimetableAssignment.timetable_id == filters.timetable_id
            )

        if filters.assignment_type is not None:
            query = query.where(
                TimetableAssignment.assignment_type == filters.assignment_type
            )

        if filters.user_id is not None:
            query = query.where(TimetableAssignment.user_id == filters.user_id)

        if filters.class_group_id is not None:
            query = query.where(
                TimetableAssignment.class_group_id == filters.class_group_id
            )

        query = query.offset(filters.offset).limit(filters.limit)

        result = await self.db.execute(query)

        return list(result.scalars().all())
