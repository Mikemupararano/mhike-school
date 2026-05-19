from datetime import date

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.attendance_record import AttendanceRecord
from app.models.attendance_session import AttendanceSession
from app.models.parent_student import ParentStudent
from app.schemas.attendance import (
    AttendanceSessionType,
    AttendanceStatus,
)


@pytest.mark.asyncio
async def test_school_admin_can_view_parent_attendance_profile(
    client: AsyncClient,
    db_session: AsyncSession,
    school_admin_user,
    student_user,
    auth_headers,
):
    session = AttendanceSession(
        school_id=school_admin_user.school_id,
        class_group_id=1,
        session_date=date(2026, 5, 20),
        session_type=AttendanceSessionType.AM,
        created_by_id=school_admin_user.id,
        is_submitted=True,
    )

    db_session.add(session)
    await db_session.commit()
    await db_session.refresh(session)

    record = AttendanceRecord(
        attendance_session_id=session.id,
        student_id=student_user.id,
        status=AttendanceStatus.PRESENT,
        marked_by_id=school_admin_user.id,
        notes="Parent visibility test",
    )

    db_session.add(record)
    await db_session.commit()

    response = await client.get(
        f"/api/v1/parent-attendance/students/{student_user.id}/profile",
        headers=auth_headers(school_admin_user),
    )

    assert response.status_code == 200

    data = response.json()

    assert data["student_id"] == student_user.id
    assert data["total_records"] == 1
    assert data["present"] == 1
    assert data["attendance_percentage"] == 100.0
    assert len(data["history"]) == 1
    assert data["history"][0]["notes"] == "Parent visibility test"


@pytest.mark.asyncio
async def test_linked_parent_can_view_child_attendance_profile(
    client: AsyncClient,
    db_session: AsyncSession,
    parent_user,
    student_user,
    school_admin_user,
    auth_headers,
):
    link = ParentStudent(
        parent_id=parent_user.id,
        student_id=student_user.id,
    )

    db_session.add(link)

    session = AttendanceSession(
        school_id=school_admin_user.school_id,
        class_group_id=1,
        session_date=date(2026, 5, 20),
        session_type=AttendanceSessionType.AM,
        created_by_id=school_admin_user.id,
        is_submitted=True,
    )

    db_session.add(session)
    await db_session.commit()
    await db_session.refresh(session)

    record = AttendanceRecord(
        attendance_session_id=session.id,
        student_id=student_user.id,
        status=AttendanceStatus.LATE,
        marked_by_id=school_admin_user.id,
        notes="Linked parent visibility test",
    )

    db_session.add(record)
    await db_session.commit()

    response = await client.get(
        f"/api/v1/parent-attendance/students/{student_user.id}/profile",
        headers=auth_headers(parent_user),
    )

    assert response.status_code == 200

    data = response.json()

    assert data["student_id"] == student_user.id
    assert data["total_records"] == 1
    assert data["late"] == 1
    assert data["attendance_percentage"] == 100.0
    assert data["history"][0]["notes"] == "Linked parent visibility test"


@pytest.mark.asyncio
async def test_unlinked_parent_cannot_view_child_attendance_profile(
    client: AsyncClient,
    parent_user,
    student_user,
    auth_headers,
):
    response = await client.get(
        f"/api/v1/parent-attendance/students/{student_user.id}/profile",
        headers=auth_headers(parent_user),
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_parent_attendance_returns_404_for_missing_student(
    client: AsyncClient,
    school_admin_user,
    auth_headers,
):
    response = await client.get(
        "/api/v1/parent-attendance/students/999999/profile",
        headers=auth_headers(school_admin_user),
    )

    assert response.status_code == 404
