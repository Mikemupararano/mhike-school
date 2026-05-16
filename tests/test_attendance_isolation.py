from datetime import date

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.attendance_session import AttendanceSession
from app.schemas.attendance import AttendanceSessionType


@pytest.mark.asyncio
async def test_school_admin_cannot_view_other_school_attendance(
    client: AsyncClient,
    db_session: AsyncSession,
    school_admin_user,
    auth_headers,
):
    school_one_session = AttendanceSession(
        school_id=1,
        class_group_id=1,
        session_date=date(2026, 5, 16),
        session_type=AttendanceSessionType.AM,
        created_by_id=None,
    )

    school_two_session = AttendanceSession(
        school_id=2,
        class_group_id=2,
        session_date=date(2026, 5, 16),
        session_type=AttendanceSessionType.PM,
        created_by_id=None,
    )

    db_session.add_all([school_one_session, school_two_session])
    await db_session.commit()

    response = await client.get(
        "/api/v1/attendance/sessions",
        headers=auth_headers(school_admin_user),
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data) == 1
    assert data[0]["school_id"] == 1


@pytest.mark.asyncio
async def test_teacher_cannot_create_attendance_for_other_school(
    client: AsyncClient,
    teacher_user,
    auth_headers,
):
    response = await client.post(
        "/api/v1/attendance/sessions",
        headers=auth_headers(teacher_user),
        json={
            "school_id": 2,
            "class_group_id": 1,
            "session_date": "2026-05-16",
            "session_type": "am",
        },
    )

    assert response.status_code in (200, 201)

    data = response.json()

    assert data["school_id"] == teacher_user.school_id
    assert data["school_id"] != 2


@pytest.mark.asyncio
async def test_attendance_sessions_are_filtered_by_current_school(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
):
    visible_session = AttendanceSession(
        school_id=1,
        class_group_id=1,
        session_date=date(2026, 5, 16),
        session_type=AttendanceSessionType.AM,
        created_by_id=None,
    )

    hidden_session = AttendanceSession(
        school_id=2,
        class_group_id=2,
        session_date=date(2026, 5, 16),
        session_type=AttendanceSessionType.PM,
        created_by_id=None,
    )

    db_session.add_all([visible_session, hidden_session])
    await db_session.commit()

    response = await client.get(
        "/api/v1/attendance/sessions?school_id=2",
        headers=auth_headers(teacher_user),
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data) == 1
    assert data[0]["school_id"] == teacher_user.school_id


@pytest.mark.asyncio
async def test_platform_admin_can_view_cross_school_attendance(
    client: AsyncClient,
    db_session: AsyncSession,
    platform_admin_user,
    auth_headers,
):
    school_one_session = AttendanceSession(
        school_id=1,
        class_group_id=1,
        session_date=date(2026, 5, 16),
        session_type=AttendanceSessionType.AM,
        created_by_id=None,
    )

    school_two_session = AttendanceSession(
        school_id=2,
        class_group_id=2,
        session_date=date(2026, 5, 16),
        session_type=AttendanceSessionType.PM,
        created_by_id=None,
    )

    db_session.add_all([school_one_session, school_two_session])
    await db_session.commit()

    response = await client.get(
        "/api/v1/attendance/sessions",
        headers=auth_headers(platform_admin_user),
    )

    assert response.status_code == 200

    data = response.json()

    school_ids = {item["school_id"] for item in data}

    assert 1 in school_ids
    assert 2 in school_ids
