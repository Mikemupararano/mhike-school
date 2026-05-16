from datetime import date

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.attendance_record import AttendanceRecord
from app.models.attendance_session import AttendanceSession
from app.schemas.attendance import AttendanceSessionType, AttendanceStatus


@pytest.mark.asyncio
async def test_submitted_register_blocks_new_attendance_records(
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
        is_submitted=True,
        submitted_by_id=teacher_user.id,
    )

    db_session.add(session)
    await db_session.commit()
    await db_session.refresh(session)

    response = await client.post(
        "/api/v1/attendance/records",
        headers=auth_headers(teacher_user),
        json={
            "attendance_session_id": session.id,
            "student_id": 1,
            "status": "present",
            "notes": "Blocked",
        },
    )

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_submitted_register_blocks_bulk_resubmission(
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
        is_submitted=True,
        submitted_by_id=teacher_user.id,
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
                    "status": "late",
                    "notes": "Blocked",
                }
            ]
        },
    )

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_submitted_register_blocks_record_updates(
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
        is_submitted=True,
        submitted_by_id=teacher_user.id,
    )

    db_session.add(session)
    await db_session.commit()
    await db_session.refresh(session)

    record = AttendanceRecord(
        attendance_session_id=session.id,
        student_id=1,
        status=AttendanceStatus.PRESENT,
        marked_by_id=teacher_user.id,
        notes="Initial",
    )

    db_session.add(record)
    await db_session.commit()
    await db_session.refresh(record)

    response = await client.patch(
        f"/api/v1/attendance/records/{record.id}",
        headers=auth_headers(teacher_user),
        json={
            "status": "late",
            "notes": "Should fail",
        },
    )

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_bulk_submission_marks_session_as_submitted(
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
                    "notes": "Submitted",
                    "marked_by_id": teacher_user.id,
                }
            ]
        },
    )

    assert response.status_code in (200, 201)

    await db_session.refresh(session)

    assert session.is_submitted is True
    assert session.submitted_by_id == teacher_user.id
    assert session.submitted_at is not None
