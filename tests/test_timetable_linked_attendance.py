from datetime import date

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.attendance_session import AttendanceSession
from app.schemas.attendance import AttendanceSessionType


@pytest.mark.asyncio
async def test_create_timetable_linked_attendance_session(
    client: AsyncClient,
    db_session: AsyncSession,
    school_admin_user,
    auth_headers,
):
    response = await client.post(
        "/api/v1/attendance/sessions/from-timetable",
        params={
            "timetable_entry_id": 101,
            "timetable_period_id": 1,
            "class_group_id": 1,
            "session_date": "2026-05-20",
            "session_type": "am",
        },
        headers=auth_headers(school_admin_user),
    )

    assert response.status_code == 200

    data = response.json()

    assert data["school_id"] == school_admin_user.school_id
    assert data["class_group_id"] == 1
    assert data["timetable_entry_id"] == 101
    assert data["timetable_period_id"] == 1
    assert data["session_date"] == "2026-05-20"
    assert data["session_type"] == "am"


@pytest.mark.asyncio
async def test_reuses_existing_timetable_linked_session(
    client: AsyncClient,
    db_session: AsyncSession,
    school_admin_user,
    auth_headers,
):
    existing_session = AttendanceSession(
        school_id=school_admin_user.school_id,
        class_group_id=1,
        session_date=date(2026, 5, 20),
        session_type=AttendanceSessionType.AM,
        timetable_entry_id=101,
        timetable_period_id=1,
        created_by_id=school_admin_user.id,
        is_submitted=False,
    )

    db_session.add(existing_session)
    await db_session.commit()
    await db_session.refresh(existing_session)

    response = await client.post(
        "/api/v1/attendance/sessions/from-timetable",
        params={
            "timetable_entry_id": 101,
            "timetable_period_id": 1,
            "class_group_id": 1,
            "session_date": "2026-05-20",
            "session_type": "am",
        },
        headers=auth_headers(school_admin_user),
    )

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == existing_session.id
