from datetime import date

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.absence_request import AbsenceRequest
from app.models.attendance_record import AttendanceRecord
from app.models.attendance_session import AttendanceSession
from app.schemas.attendance import (
    AbsenceRequestStatus,
    AbsenceRequestType,
    AttendanceSessionType,
    AttendanceStatus,
)


@pytest.mark.asyncio
async def test_attendance_session_model_can_be_created(
    db_session: AsyncSession,
):
    session = AttendanceSession(
        school_id=1,
        class_group_id=1,
        session_date=date(2026, 5, 16),
        session_type=AttendanceSessionType.AM,
        created_by_id=None,
    )

    db_session.add(session)

    await db_session.commit()
    await db_session.refresh(session)

    assert session.id is not None
    assert session.school_id == 1
    assert session.class_group_id == 1
    assert session.session_type == AttendanceSessionType.AM


@pytest.mark.asyncio
async def test_attendance_record_model_can_be_created(
    db_session: AsyncSession,
):
    session = AttendanceSession(
        school_id=1,
        class_group_id=1,
        session_date=date(2026, 5, 16),
        session_type=AttendanceSessionType.AM,
        created_by_id=None,
    )

    db_session.add(session)

    await db_session.commit()
    await db_session.refresh(session)

    record = AttendanceRecord(
        attendance_session_id=session.id,
        student_id=1,
        status=AttendanceStatus.PRESENT,
        marked_by_id=None,
        notes="Present for AM registration.",
    )

    db_session.add(record)

    await db_session.commit()
    await db_session.refresh(record)

    assert record.id is not None
    assert record.attendance_session_id == session.id
    assert record.student_id == 1
    assert record.status == AttendanceStatus.PRESENT


@pytest.mark.asyncio
async def test_absence_request_model_can_be_created(
    db_session: AsyncSession,
):
    absence_request = AbsenceRequest(
        school_id=1,
        student_id=1,
        submitted_by_id=None,
        reviewed_by_id=None,
        absence_type=AbsenceRequestType.PLANNED,
        status=AbsenceRequestStatus.PENDING,
        start_date=date(2026, 5, 16),
        end_date=date(2026, 5, 17),
        reason="Medical appointment.",
        review_note=None,
    )

    db_session.add(absence_request)

    await db_session.commit()
    await db_session.refresh(absence_request)

    assert absence_request.id is not None
    assert absence_request.school_id == 1
    assert absence_request.student_id == 1
    assert absence_request.absence_type == AbsenceRequestType.PLANNED
    assert absence_request.status == AbsenceRequestStatus.PENDING


@pytest.mark.asyncio
async def test_attendance_endpoint_requires_authentication(
    client: AsyncClient,
):
    response = await client.get("/api/v1/attendance/sessions")

    assert response.status_code in (401, 403, 404)
