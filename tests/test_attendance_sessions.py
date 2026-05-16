from datetime import date

import pytest
from httpx import AsyncClient

from app.models.attendance_session import AttendanceSession
from app.schemas.attendance import AttendanceSessionType


@pytest.mark.asyncio
async def test_create_attendance_session_returns_existing_session(
    client: AsyncClient,
    db_session,
    teacher_user,
    auth_headers,
):
    existing_session = AttendanceSession(
        school_id=teacher_user.school_id,
        class_group_id=1,
        session_date=date(2026, 5, 16),
        session_type=AttendanceSessionType.AM,
        created_by_id=teacher_user.id,
    )

    db_session.add(existing_session)
    await db_session.commit()
    await db_session.refresh(existing_session)

    response = await client.post(
        "/api/v1/attendance/sessions",
        headers=auth_headers(teacher_user),
        json={
            "school_id": teacher_user.school_id,
            "class_group_id": 1,
            "session_date": "2026-05-16",
            "session_type": "am",
        },
    )

    assert response.status_code in (200, 201)

    data = response.json()

    assert data["id"] == existing_session.id
    assert data["school_id"] == teacher_user.school_id
    assert data["class_group_id"] == 1


@pytest.mark.asyncio
async def test_create_attendance_session_creates_new_when_no_existing_session(
    client: AsyncClient,
    teacher_user,
    auth_headers,
):
    response = await client.post(
        "/api/v1/attendance/sessions",
        headers=auth_headers(teacher_user),
        json={
            "school_id": teacher_user.school_id,
            "class_group_id": 2,
            "session_date": "2026-05-16",
            "session_type": "pm",
        },
    )

    assert response.status_code in (200, 201)

    data = response.json()

    assert data["id"] is not None
    assert data["school_id"] == teacher_user.school_id
    assert data["class_group_id"] == 2
    assert data["session_type"] == "pm"
