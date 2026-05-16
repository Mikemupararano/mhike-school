from datetime import date

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.attendance_session import AttendanceSession
from app.schemas.attendance import AttendanceSessionType


@pytest.mark.asyncio
async def test_teacher_can_create_bulk_attendance_records(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
):
    session = AttendanceSession(
        school_id=teacher_user.school_id,
        class_group_id=1,
        session_date=date(2026, 5, 16),
        session_type=AttendanceSessionType.AM,
        created_by_id=teacher_user.id,
    )

    db_session.add(session)
    await db_session.commit()
    await db_session.refresh(session)

    response = await client.post(
        "/api/v1/attendance/records/bulk",
        headers=auth_headers(teacher_user),
        json={
            "records": [
                {
                    "attendance_session_id": session.id,
                    "student_id": 1,
                    "status": "present",
                    "notes": None,
                },
                {
                    "attendance_session_id": session.id,
                    "student_id": 2,
                    "status": "late",
                    "notes": "Arrived after registration.",
                },
            ],
        },
    )

    assert response.status_code in (200, 201)

    data = response.json()

    assert len(data) == 2
    assert data[0]["marked_by_id"] == teacher_user.id
    assert data[1]["marked_by_id"] == teacher_user.id


@pytest.mark.asyncio
async def test_student_cannot_create_bulk_attendance_records(
    client: AsyncClient,
    db_session: AsyncSession,
    student_user,
    auth_headers,
):
    session = AttendanceSession(
        school_id=student_user.school_id,
        class_group_id=1,
        session_date=date(2026, 5, 16),
        session_type=AttendanceSessionType.AM,
        created_by_id=None,
    )

    db_session.add(session)
    await db_session.commit()
    await db_session.refresh(session)

    response = await client.post(
        "/api/v1/attendance/records/bulk",
        headers=auth_headers(student_user),
        json={
            "records": [
                {
                    "attendance_session_id": session.id,
                    "student_id": student_user.id,
                    "status": "present",
                    "notes": None,
                },
            ],
        },
    )

    assert response.status_code in (401, 403)


@pytest.mark.asyncio
async def test_bulk_attendance_requires_at_least_one_record(
    client: AsyncClient,
    teacher_user,
    auth_headers,
):
    response = await client.post(
        "/api/v1/attendance/records/bulk",
        headers=auth_headers(teacher_user),
        json={"records": []},
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_unauthenticated_user_cannot_create_bulk_attendance_records(
    client: AsyncClient,
):
    response = await client.post(
        "/api/v1/attendance/records/bulk",
        json={
            "records": [
                {
                    "attendance_session_id": 1,
                    "student_id": 1,
                    "status": "present",
                    "notes": None,
                },
            ],
        },
    )

    assert response.status_code in (401, 403)
