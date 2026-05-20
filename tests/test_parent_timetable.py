from datetime import date, time

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.timetable import Timetable
from app.models.timetable_entry import TimetableDay, TimetableEntry
from app.models.timetable_period import TimetablePeriod


@pytest.mark.asyncio
async def test_parent_child_timetable_endpoint_requires_authentication(
    client: AsyncClient,
):
    response = await client.get("/api/v1/timetables/parent/child/1")

    assert response.status_code in (401, 403)


@pytest.mark.asyncio
async def test_school_admin_cannot_view_parent_child_timetable_entries(
    client: AsyncClient,
    db_session: AsyncSession,
    school_admin_user,
    auth_headers,
):
    period = TimetablePeriod(
        school_id=school_admin_user.school_id,
        name="Period 1",
        short_name="P1",
        period_number=1,
        start_time=time(8, 30),
        end_time=time(9, 30),
    )

    timetable = Timetable(
        school_id=school_admin_user.school_id,
        name="Child Timetable",
        academic_year="2025/2026",
        effective_from=date(2025, 9, 1),
    )

    db_session.add_all([period, timetable])
    await db_session.commit()

    entry = TimetableEntry(
        timetable_id=timetable.id,
        school_id=school_admin_user.school_id,
        class_group_id=1,
        timetable_period_id=period.id,
        day_of_week=TimetableDay.MONDAY,
        title="Physics",
        room="Lab 1",
    )

    db_session.add(entry)
    await db_session.commit()

    response = await client.get(
        "/api/v1/timetables/parent/child/1?class_group_id=1",
        headers=auth_headers(school_admin_user),
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_school_admin_cannot_filter_parent_child_timetable_by_day(
    client: AsyncClient,
    db_session: AsyncSession,
    school_admin_user,
    auth_headers,
):
    period = TimetablePeriod(
        school_id=school_admin_user.school_id,
        name="Period 1",
        short_name="P1",
        period_number=1,
        start_time=time(8, 30),
        end_time=time(9, 30),
    )

    timetable = Timetable(
        school_id=school_admin_user.school_id,
        name="Child Timetable",
        academic_year="2025/2026",
        effective_from=date(2025, 9, 1),
    )

    db_session.add_all([period, timetable])
    await db_session.commit()

    monday_entry = TimetableEntry(
        timetable_id=timetable.id,
        school_id=school_admin_user.school_id,
        class_group_id=1,
        timetable_period_id=period.id,
        day_of_week=TimetableDay.MONDAY,
        title="Monday Physics",
    )

    tuesday_entry = TimetableEntry(
        timetable_id=timetable.id,
        school_id=school_admin_user.school_id,
        class_group_id=1,
        timetable_period_id=period.id,
        day_of_week=TimetableDay.TUESDAY,
        title="Tuesday Chemistry",
    )

    db_session.add_all([monday_entry, tuesday_entry])
    await db_session.commit()

    response = await client.get(
        "/api/v1/timetables/parent/child/1?class_group_id=1&day_of_week=monday",
        headers=auth_headers(school_admin_user),
    )

    assert response.status_code == 403
