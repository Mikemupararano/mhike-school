from datetime import date

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.attendance_record import AttendanceRecord
from app.models.attendance_session import AttendanceSession
from app.schemas.attendance import (
    AttendanceSessionType,
    AttendanceStatus,
)


@pytest.mark.asyncio
async def test_school_admin_can_view_attendance_trends(
    client: AsyncClient,
    db_session: AsyncSession,
    school_admin_user,
    student_user,
    auth_headers,
):
    session_1 = AttendanceSession(
        school_id=school_admin_user.school_id,
        class_group_id=1,
        session_date=date(2026, 5, 20),
        session_type=AttendanceSessionType.AM,
        created_by_id=school_admin_user.id,
        is_submitted=True,
    )

    session_2 = AttendanceSession(
        school_id=school_admin_user.school_id,
        class_group_id=1,
        session_date=date(2026, 5, 21),
        session_type=AttendanceSessionType.AM,
        created_by_id=school_admin_user.id,
        is_submitted=True,
    )

    db_session.add_all([session_1, session_2])
    await db_session.commit()

    await db_session.refresh(session_1)
    await db_session.refresh(session_2)

    records = [
        AttendanceRecord(
            attendance_session_id=session_1.id,
            student_id=student_user.id,
            status=AttendanceStatus.PRESENT,
            marked_by_id=school_admin_user.id,
        ),
        AttendanceRecord(
            attendance_session_id=session_1.id,
            student_id=student_user.id + 1000,
            status=AttendanceStatus.UNAUTHORISED_ABSENCE,
            marked_by_id=school_admin_user.id,
        ),
        AttendanceRecord(
            attendance_session_id=session_2.id,
            student_id=student_user.id,
            status=AttendanceStatus.LATE,
            marked_by_id=school_admin_user.id,
        ),
    ]

    db_session.add_all(records)
    await db_session.commit()

    response = await client.get(
        (
            "/api/v1/attendance-trends/summary"
            "?start_date=2026-05-20&end_date=2026-05-21"
        ),
        headers=auth_headers(school_admin_user),
    )

    assert response.status_code == 200

    data = response.json()

    assert data["school_id"] == school_admin_user.school_id
    assert data["start_date"] == "2026-05-20"
    assert data["end_date"] == "2026-05-21"
    assert len(data["points"]) == 2

    first_point = data["points"][0]
    second_point = data["points"][1]

    assert first_point["trend_date"] == "2026-05-20"
    assert first_point["total_records"] == 2
    assert first_point["present"] == 1
    assert first_point["late"] == 0
    assert first_point["unauthorised_absence"] == 1
    assert first_point["attendance_percentage"] == 50.0

    assert second_point["trend_date"] == "2026-05-21"
    assert second_point["total_records"] == 1
    assert second_point["present"] == 0
    assert second_point["late"] == 1
    assert second_point["attendance_percentage"] == 100.0


@pytest.mark.asyncio
async def test_attendance_trends_rejects_invalid_date_range(
    client: AsyncClient,
    school_admin_user,
    auth_headers,
):
    response = await client.get(
        (
            "/api/v1/attendance-trends/summary"
            "?start_date=2026-05-22&end_date=2026-05-20"
        ),
        headers=auth_headers(school_admin_user),
    )

    assert response.status_code == 400
