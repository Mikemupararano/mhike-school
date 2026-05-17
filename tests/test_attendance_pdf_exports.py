from datetime import date

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.attendance_record import AttendanceRecord
from app.models.attendance_session import AttendanceSession
from app.schemas.attendance import AttendanceSessionType, AttendanceStatus


@pytest.mark.asyncio
async def test_school_admin_can_export_attendance_register_pdf(
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
        notes="PDF export test",
    )

    db_session.add(record)
    await db_session.commit()

    response = await client.get(
        f"/api/v1/attendance-pdf-exports/registers/export/{session.id}/pdf",
        headers=auth_headers(school_admin_user),
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/pdf")
    assert response.content.startswith(b"%PDF")
    assert "attachment" in response.headers["content-disposition"]
    assert (
        f"attendance_register_{session.id}_2026-05-20.pdf"
        in response.headers["content-disposition"]
    )


@pytest.mark.asyncio
async def test_school_admin_cannot_export_pdf_register_from_another_school(
    client: AsyncClient,
    db_session: AsyncSession,
    school_admin_user,
    auth_headers,
):
    other_school_id = school_admin_user.school_id + 999

    session = AttendanceSession(
        school_id=other_school_id,
        class_group_id=1,
        session_date=date(2026, 5, 20),
        session_type=AttendanceSessionType.AM,
        is_submitted=True,
    )

    db_session.add(session)
    await db_session.commit()
    await db_session.refresh(session)

    response = await client.get(
        f"/api/v1/attendance-pdf-exports/registers/export/{session.id}/pdf",
        headers=auth_headers(school_admin_user),
    )

    assert response.status_code == 403
