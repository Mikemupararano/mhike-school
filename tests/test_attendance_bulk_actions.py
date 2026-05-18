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
async def test_school_admin_can_bulk_update_attendance_records(
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
        is_submitted=False,
    )

    db_session.add(session)
    await db_session.commit()
    await db_session.refresh(session)

    record = AttendanceRecord(
        attendance_session_id=session.id,
        student_id=student_user.id,
        status=AttendanceStatus.PRESENT,
        marked_by_id=school_admin_user.id,
        notes="Original note",
    )

    db_session.add(record)
    await db_session.commit()
    await db_session.refresh(record)

    response = await client.patch(
        "/api/v1/attendance-bulk-actions/records",
        json={
            "records": [
                {
                    "record_id": record.id,
                    "status": "late",
                    "notes": "Updated in bulk",
                }
            ]
        },
        headers=auth_headers(school_admin_user),
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data) == 1
    assert data[0]["id"] == record.id
    assert data[0]["status"] == "late"
    assert data[0]["notes"] == "Updated in bulk"


@pytest.mark.asyncio
async def test_bulk_update_rejects_submitted_register(
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
    )

    db_session.add(record)
    await db_session.commit()
    await db_session.refresh(record)

    response = await client.patch(
        "/api/v1/attendance-bulk-actions/records",
        json={
            "records": [
                {
                    "record_id": record.id,
                    "status": "late",
                    "notes": "Should fail",
                }
            ]
        },
        headers=auth_headers(school_admin_user),
    )

    assert response.status_code == 400
