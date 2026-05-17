from datetime import date

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.attendance_record import AttendanceRecord
from app.models.attendance_session import AttendanceSession
from app.models.class_group import ClassGroup
from app.models.enrollment import Enrollment
from app.schemas.attendance import (
    AttendanceSessionType,
    AttendanceStatus,
)


@pytest.mark.asyncio
async def test_attendance_analytics_returns_persistent_absentees(
    client: AsyncClient,
    db_session: AsyncSession,
    school_admin_user,
    student_user,
    auth_headers,
):
    class_group = ClassGroup(
        school_id=school_admin_user.school_id,
        name="Year 11 Physics",
    )

    db_session.add(class_group)
    await db_session.commit()
    await db_session.refresh(class_group)

    enrollment = Enrollment(
        user_id=student_user.id,
        class_id=class_group.id,
    )

    db_session.add(enrollment)
    await db_session.commit()

    session_1 = AttendanceSession(
        school_id=school_admin_user.school_id,
        class_group_id=class_group.id,
        session_date=date(2026, 5, 20),
        session_type=AttendanceSessionType.AM,
        created_by_id=school_admin_user.id,
        is_submitted=True,
    )

    session_2 = AttendanceSession(
        school_id=school_admin_user.school_id,
        class_group_id=class_group.id,
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
            status=AttendanceStatus.UNAUTHORISED_ABSENCE,
            marked_by_id=school_admin_user.id,
        ),
        AttendanceRecord(
            attendance_session_id=session_2.id,
            student_id=student_user.id,
            status=AttendanceStatus.AUTHORISED_ABSENCE,
            marked_by_id=school_admin_user.id,
        ),
    ]

    db_session.add_all(records)
    await db_session.commit()

    response = await client.get(
        "/api/v1/attendance-analytics/summary",
        headers=auth_headers(school_admin_user),
    )

    assert response.status_code == 200

    data = response.json()

    assert data["school_id"] == school_admin_user.school_id
    assert len(data["persistent_absentees"]) >= 1

    absentee = data["persistent_absentees"][0]

    assert absentee["student_id"] == student_user.id
    assert absentee["class_group_id"] == class_group.id
    assert absentee["class_name"] == "Year 11 Physics"
    assert absentee["absence_count"] == 2
    assert absentee["unauthorised_absence_count"] == 1
    assert absentee["absence_percentage"] == 100.0


@pytest.mark.asyncio
async def test_attendance_analytics_excludes_good_attendance(
    client: AsyncClient,
    db_session: AsyncSession,
    school_admin_user,
    student_user,
    auth_headers,
):
    class_group = ClassGroup(
        school_id=school_admin_user.school_id,
        name="Year 10 Chemistry",
    )

    db_session.add(class_group)
    await db_session.commit()
    await db_session.refresh(class_group)

    enrollment = Enrollment(
        user_id=student_user.id,
        class_id=class_group.id,
    )

    db_session.add(enrollment)
    await db_session.commit()

    session = AttendanceSession(
        school_id=school_admin_user.school_id,
        class_group_id=class_group.id,
        session_date=date(2026, 5, 22),
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

    response = await client.get(
        "/api/v1/attendance-analytics/summary",
        headers=auth_headers(school_admin_user),
    )

    assert response.status_code == 200

    data = response.json()

    matching_students = [
        item
        for item in data["persistent_absentees"]
        if item["student_id"] == student_user.id
        and item["class_group_id"] == class_group.id
    ]

    assert matching_students == []
