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
async def test_school_admin_can_view_student_attendance_profile(
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
            attendance_session_id=session_2.id,
            student_id=student_user.id,
            status=AttendanceStatus.LATE,
            marked_by_id=school_admin_user.id,
        ),
    ]

    db_session.add_all(records)
    await db_session.commit()

    response = await client.get(
        ("/api/v1/student-attendance/" f"students/{student_user.id}/profile"),
        headers=auth_headers(school_admin_user),
    )

    assert response.status_code == 200

    data = response.json()

    assert data["student_id"] == student_user.id
    assert data["school_id"] == school_admin_user.school_id
    assert data["total_records"] == 2
    assert data["present"] == 1
    assert data["late"] == 1
    assert data["authorised_absence"] == 0
    assert data["unauthorised_absence"] == 0
    assert data["attendance_percentage"] == 100.0

    assert len(data["history"]) == 2


@pytest.mark.asyncio
async def test_student_attendance_profile_returns_404_for_missing_student(
    client: AsyncClient,
    school_admin_user,
    auth_headers,
):
    response = await client.get(
        "/api/v1/student-attendance/students/999999/profile",
        headers=auth_headers(school_admin_user),
    )

    assert response.status_code == 404
