from datetime import date, time

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.timetable import Timetable
from app.models.timetable_entry import TimetableDay, TimetableEntry
from app.models.timetable_period import TimetablePeriod


@pytest.mark.asyncio
async def test_student_can_view_own_class_timetable_entries(
    client: AsyncClient,
    db_session: AsyncSession,
    student_user,
    auth_headers,
):
    period = TimetablePeriod(
        school_id=student_user.school_id,
        name="Period 1",
        short_name="P1",
        period_number=1,
        start_time=time(8, 30),
        end_time=time(9, 30),
    )

    timetable = Timetable(
        school_id=student_user.school_id,
        name="Student Timetable",
        academic_year="2025/2026",
        effective_from=date(2025, 9, 1),
    )

    db_session.add_all([period, timetable])
    await db_session.commit()

    entry = TimetableEntry(
        timetable_id=timetable.id,
        school_id=student_user.school_id,
        class_group_id=1,
        timetable_period_id=period.id,
        day_of_week=TimetableDay.MONDAY,
        title="Physics",
        room="Lab 1",
    )

    db_session.add(entry)
    await db_session.commit()

    response = await client.get(
        "/api/v1/timetables/student/me?class_group_id=1",
        headers=auth_headers(student_user),
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data) == 1
    assert data[0]["class_group_id"] == 1
    assert data[0]["title"] == "Physics"


@pytest.mark.asyncio
async def test_student_timetable_can_be_filtered_by_day(
    client: AsyncClient,
    db_session: AsyncSession,
    student_user,
    auth_headers,
):
    period = TimetablePeriod(
        school_id=student_user.school_id,
        name="Period 1",
        short_name="P1",
        period_number=1,
        start_time=time(8, 30),
        end_time=time(9, 30),
    )

    timetable = Timetable(
        school_id=student_user.school_id,
        name="Student Timetable",
        academic_year="2025/2026",
        effective_from=date(2025, 9, 1),
    )

    db_session.add_all([period, timetable])
    await db_session.commit()

    monday_entry = TimetableEntry(
        timetable_id=timetable.id,
        school_id=student_user.school_id,
        class_group_id=1,
        timetable_period_id=period.id,
        day_of_week=TimetableDay.MONDAY,
        title="Monday Physics",
    )

    tuesday_entry = TimetableEntry(
        timetable_id=timetable.id,
        school_id=student_user.school_id,
        class_group_id=1,
        timetable_period_id=period.id,
        day_of_week=TimetableDay.TUESDAY,
        title="Tuesday Chemistry",
    )

    db_session.add_all([monday_entry, tuesday_entry])
    await db_session.commit()

    response = await client.get(
        "/api/v1/timetables/student/me?class_group_id=1&day_of_week=monday",
        headers=auth_headers(student_user),
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data) == 1
    assert data[0]["day_of_week"] == "monday"
    assert data[0]["title"] == "Monday Physics"


@pytest.mark.asyncio
async def test_teacher_cannot_access_student_timetable_endpoint(
    client: AsyncClient,
    teacher_user,
    auth_headers,
):
    response = await client.get(
        "/api/v1/timetables/student/me",
        headers=auth_headers(teacher_user),
    )

    assert response.status_code in (401, 403)


@pytest.mark.asyncio
async def test_unauthenticated_user_cannot_access_student_timetable(
    client: AsyncClient,
):
    response = await client.get("/api/v1/timetables/student/me")

    assert response.status_code in (401, 403)
