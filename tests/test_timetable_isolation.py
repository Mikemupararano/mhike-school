from datetime import date, time

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.timetable import Timetable
from app.models.timetable_entry import (
    TimetableDay,
    TimetableEntry,
)
from app.models.timetable_period import TimetablePeriod


@pytest.mark.asyncio
async def test_school_admin_cannot_view_other_school_timetables(
    client: AsyncClient,
    db_session: AsyncSession,
    school_admin_teacher_user,
    auth_headers,
):
    timetable_one = Timetable(
        school_id=1,
        name="School One Timetable",
        academic_year="2025/2026",
        effective_from=date(2025, 9, 1),
    )

    timetable_two = Timetable(
        school_id=2,
        name="School Two Timetable",
        academic_year="2025/2026",
        effective_from=date(2025, 9, 1),
    )

    db_session.add_all([timetable_one, timetable_two])
    await db_session.commit()

    response = await client.get(
        "/api/v1/timetables/",
        headers=auth_headers(school_admin_teacher_user),
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data) == 1
    assert data[0]["school_id"] == 1


@pytest.mark.asyncio
async def test_teacher_cannot_create_timetable_for_other_school(
    client: AsyncClient,
    teacher_user,
    auth_headers,
):
    response = await client.post(
        "/api/v1/timetables/",
        headers=auth_headers(teacher_user),
        json={
            "school_id": 2,
            "name": "Illegal Timetable",
            "academic_year": "2025/2026",
            "effective_from": "2025-09-01",
        },
    )

    assert response.status_code in (200, 201)

    data = response.json()

    assert data["school_id"] == teacher_user.school_id
    assert data["school_id"] != 2


@pytest.mark.asyncio
async def test_timetable_entries_are_filtered_by_school(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
):
    period = TimetablePeriod(
        school_id=1,
        name="Period 1",
        short_name="P1",
        period_number=1,
        start_time=time(8, 30),
        end_time=time(9, 30),
    )

    visible_timetable = Timetable(
        school_id=1,
        name="Visible Timetable",
        academic_year="2025/2026",
        effective_from=date(2025, 9, 1),
    )

    hidden_timetable = Timetable(
        school_id=2,
        name="Hidden Timetable",
        academic_year="2025/2026",
        effective_from=date(2025, 9, 1),
    )

    db_session.add_all(
        [
            period,
            visible_timetable,
            hidden_timetable,
        ]
    )

    await db_session.commit()

    visible_entry = TimetableEntry(
        timetable_id=visible_timetable.id,
        school_id=1,
        timetable_period_id=period.id,
        day_of_week=TimetableDay.MONDAY,
        title="Visible Lesson",
    )

    hidden_entry = TimetableEntry(
        timetable_id=hidden_timetable.id,
        school_id=2,
        timetable_period_id=period.id,
        day_of_week=TimetableDay.TUESDAY,
        title="Hidden Lesson",
    )

    db_session.add_all([visible_entry, hidden_entry])
    await db_session.commit()

    response = await client.get(
        "/api/v1/timetables/entries",
        headers=auth_headers(teacher_user),
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data) == 1
    assert data[0]["school_id"] == 1
    assert data[0]["title"] == "Visible Lesson"


@pytest.mark.asyncio
async def test_platform_admin_can_view_cross_school_timetables(
    client: AsyncClient,
    db_session: AsyncSession,
    platform_admin_user,
    auth_headers,
):
    timetable_one = Timetable(
        school_id=1,
        name="School One Timetable",
        academic_year="2025/2026",
        effective_from=date(2025, 9, 1),
    )

    timetable_two = Timetable(
        school_id=2,
        name="School Two Timetable",
        academic_year="2025/2026",
        effective_from=date(2025, 9, 1),
    )

    db_session.add_all([timetable_one, timetable_two])
    await db_session.commit()

    response = await client.get(
        "/api/v1/timetables/",
        headers=auth_headers(platform_admin_user),
    )

    assert response.status_code == 200

    data = response.json()

    school_ids = {item["school_id"] for item in data}

    assert 1 in school_ids
    assert 2 in school_ids
