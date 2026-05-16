from datetime import date

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.attendance_record import AttendanceRecord
from app.models.attendance_session import AttendanceSession
from app.schemas.attendance import AttendanceSessionType, AttendanceStatus


@pytest.mark.asyncio
async def test_bulk_attendance_resubmission_updates_existing_record(
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

    existing_record = AttendanceRecord(
        attendance_session_id=session.id,
        student_id=1,
        status=AttendanceStatus.PRESENT,
        marked_by_id=teacher_user.id,
        notes="Original mark",
    )

    db_session.add(existing_record)
    await db_session.commit()
    await db_session.refresh(existing_record)

    response = await client.post(
        "/api/v1/attendance/records/bulk",
        headers=auth_headers(teacher_user),
        json={
            "records": [
                {
                    "attendance_session_id": session.id,
                    "student_id": 1,
                    "status": "late",
                    "notes": "Updated mark",
                }
            ]
        },
    )

    assert response.status_code in (200, 201)

    data = response.json()

    assert len(data) == 1
    assert data[0]["id"] == existing_record.id
    assert data[0]["status"] == "late"
    assert data[0]["notes"] == "Updated mark"
    assert data[0]["marked_by_id"] == teacher_user.id
