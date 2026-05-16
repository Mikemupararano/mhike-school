from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.timetable import Timetable
from app.repositories.timetable import TimetableRepository
from app.schemas.timetable import (
    TimetableAssignmentCreate,
    TimetableAssignmentFilter,
    TimetableCreate,
    TimetableEntryCreate,
    TimetableEntryFilter,
    TimetableFilter,
    TimetablePeriodCreate,
)


class TimetableService:
    def __init__(self, db: AsyncSession):
        self.repo = TimetableRepository(db)

    async def create_period(self, data: TimetablePeriodCreate):
        return await self.repo.create_period(data)

    async def list_periods(self, school_id: int):
        return await self.repo.list_periods(school_id)

    async def create_timetable(self, data: TimetableCreate) -> Timetable:
        return await self.repo.create_timetable(data)

    async def get_timetable_or_404(self, timetable_id: int) -> Timetable:
        timetable = await self.repo.get_timetable_by_id(timetable_id)

        if timetable is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Timetable not found.",
            )

        return timetable

    async def list_timetables(self, filters: TimetableFilter):
        return await self.repo.list_timetables(filters)

    async def create_entry(self, data: TimetableEntryCreate):
        timetable = await self.get_timetable_or_404(data.timetable_id)

        if timetable.school_id != data.school_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Timetable entry school does not match timetable school.",
            )

        return await self.repo.create_entry(data)

    async def list_entries(self, filters: TimetableEntryFilter):
        return await self.repo.list_entries(filters)

    async def create_assignment(self, data: TimetableAssignmentCreate):
        timetable = await self.get_timetable_or_404(data.timetable_id)

        if timetable.school_id != data.school_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Timetable assignment school does not match timetable school.",
            )

        return await self.repo.create_assignment(data)

    async def list_assignments(self, filters: TimetableAssignmentFilter):
        return await self.repo.list_assignments(filters)
