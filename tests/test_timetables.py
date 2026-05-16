from datetime import date, time

import pytest

from app.models.timetable import Timetable
from app.models.timetable_assignment import (
    TimetableAssignment,
    TimetableAssignmentType,
)
from app.models.timetable_entry import (
    TimetableDay,
    TimetableEntry,
)
from app.models.timetable_period import TimetablePeriod


@pytest.mark.asyncio
async def test_timetable_period_model_can_be_created(db_session):
    period = TimetablePeriod(
        school_id=1,
        name="Period 1",
        short_name="P1",
        period_number=1,
        start_time=time(8, 30),
        end_time=time(9, 30),
    )

    db_session.add(period)
    await db_session.commit()
    await db_session.refresh(period)

    assert period.id is not None
    assert period.name == "Period 1"
    assert period.short_name == "P1"


@pytest.mark.asyncio
async def test_timetable_model_can_be_created(db_session):
    timetable = Timetable(
        school_id=1,
        name="Year 10 Timetable",
        academic_year="2025/2026",
        effective_from=date(2025, 9, 1),
    )

    db_session.add(timetable)
    await db_session.commit()
    await db_session.refresh(timetable)

    assert timetable.id is not None
    assert timetable.school_id == 1
    assert timetable.is_active is True


@pytest.mark.asyncio
async def test_timetable_entry_model_can_be_created(db_session):
    period = TimetablePeriod(
        school_id=1,
        name="Period 1",
        short_name="P1",
        period_number=1,
        start_time=time(8, 30),
        end_time=time(9, 30),
    )

    timetable = Timetable(
        school_id=1,
        name="Main Timetable",
        academic_year="2025/2026",
        effective_from=date(2025, 9, 1),
    )

    db_session.add_all([period, timetable])
    await db_session.commit()

    entry = TimetableEntry(
        timetable_id=timetable.id,
        school_id=1,
        timetable_period_id=period.id,
        day_of_week=TimetableDay.MONDAY,
        room="Lab 2",
        title="Physics",
    )

    db_session.add(entry)
    await db_session.commit()
    await db_session.refresh(entry)

    assert entry.id is not None
    assert entry.room == "Lab 2"
    assert entry.day_of_week == TimetableDay.MONDAY


@pytest.mark.asyncio
async def test_timetable_assignment_model_can_be_created(db_session):
    timetable = Timetable(
        school_id=1,
        name="Teacher Timetable",
        academic_year="2025/2026",
        effective_from=date(2025, 9, 1),
    )

    db_session.add(timetable)
    await db_session.commit()

    assignment = TimetableAssignment(
        timetable_id=timetable.id,
        school_id=1,
        assignment_type=TimetableAssignmentType.TEACHER,
        user_id=1,
    )

    db_session.add(assignment)
    await db_session.commit()
    await db_session.refresh(assignment)

    assert assignment.id is not None
    assert assignment.assignment_type == TimetableAssignmentType.TEACHER
