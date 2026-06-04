from datetime import date

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.assignment import Assignment
from app.models.assignment_submission import AssignmentSubmission
from app.models.attendance_record import AttendanceRecord
from app.models.attendance_session import AttendanceSession
from app.models.parent_student import ParentStudent
from app.models.student_report import StudentReport
from app.schemas.attendance import AttendanceSessionType, AttendanceStatus


@pytest.mark.asyncio
async def test_teacher_can_view_student_progress(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    student_user,
    auth_headers,
):
    report = StudentReport(
        school_id=student_user.school_id,
        student_id=student_user.id,
        teacher_id=teacher_user.id,
        title="Progress Report",
        report_text="Strong progress.",
        grade="A",
        academic_year="2026/27",
        term="Autumn",
    )

    db_session.add(report)
    await db_session.commit()

    response = await client.get(
        f"/api/v1/student-progress/{student_user.id}",
        headers=auth_headers(teacher_user),
    )

    assert response.status_code == 200

    data = response.json()

    assert data["student_id"] == student_user.id
    assert data["report_count"] == 1
    assert data["latest_report_title"] == "Progress Report"


@pytest.mark.asyncio
async def test_linked_parent_can_view_child_progress(
    client: AsyncClient,
    db_session: AsyncSession,
    parent_user,
    student_user,
    teacher_user,
    auth_headers,
):
    link = ParentStudent(
        parent_id=parent_user.id,
        student_id=student_user.id,
    )

    report = StudentReport(
        school_id=student_user.school_id,
        student_id=student_user.id,
        teacher_id=teacher_user.id,
        title="Parent Progress Report",
        report_text="Visible to parent.",
        grade="B",
        academic_year="2026/27",
        term="Spring",
    )

    db_session.add_all([link, report])
    await db_session.commit()

    response = await client.get(
        f"/api/v1/student-progress/parent/{student_user.id}",
        headers=auth_headers(parent_user),
    )

    assert response.status_code == 200

    data = response.json()

    assert data["student_id"] == student_user.id
    assert data["report_count"] == 1
    assert data["latest_report_title"] == "Parent Progress Report"


@pytest.mark.asyncio
async def test_unlinked_parent_cannot_view_child_progress(
    client: AsyncClient,
    parent_user,
    student_user,
    auth_headers,
):
    response = await client.get(
        f"/api/v1/student-progress/parent/{student_user.id}",
        headers=auth_headers(parent_user),
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_student_progress_calculates_attendance_percentage(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    student_user,
    auth_headers,
):
    session_one = AttendanceSession(
        school_id=student_user.school_id,
        class_group_id=1,
        session_date=date(2026, 6, 1),
        session_type=AttendanceSessionType.AM,
        created_by_id=teacher_user.id,
        is_submitted=True,
    )

    session_two = AttendanceSession(
        school_id=student_user.school_id,
        class_group_id=1,
        session_date=date(2026, 6, 2),
        session_type=AttendanceSessionType.AM,
        created_by_id=teacher_user.id,
        is_submitted=True,
    )

    session_three = AttendanceSession(
        school_id=student_user.school_id,
        class_group_id=1,
        session_date=date(2026, 6, 3),
        session_type=AttendanceSessionType.AM,
        created_by_id=teacher_user.id,
        is_submitted=True,
    )

    db_session.add_all(
        [
            session_one,
            session_two,
            session_three,
        ],
    )

    await db_session.commit()

    await db_session.refresh(session_one)
    await db_session.refresh(session_two)
    await db_session.refresh(session_three)

    db_session.add_all(
        [
            AttendanceRecord(
                attendance_session_id=session_one.id,
                student_id=student_user.id,
                status=AttendanceStatus.PRESENT,
                marked_by_id=teacher_user.id,
            ),
            AttendanceRecord(
                attendance_session_id=session_two.id,
                student_id=student_user.id,
                status=AttendanceStatus.LATE,
                marked_by_id=teacher_user.id,
            ),
            AttendanceRecord(
                attendance_session_id=session_three.id,
                student_id=student_user.id,
                status=AttendanceStatus.UNAUTHORISED_ABSENCE,
                marked_by_id=teacher_user.id,
            ),
        ],
    )

    await db_session.commit()

    response = await client.get(
        f"/api/v1/student-progress/{student_user.id}",
        headers=auth_headers(teacher_user),
    )

    assert response.status_code == 200

    data = response.json()

    assert data["attendance_percentage"] == 66.67


@pytest.mark.asyncio
async def test_student_progress_calculates_assignment_average(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    student_user,
    auth_headers,
):
    assignment_one = Assignment(
        title="Assignment One",
        description="First assignment.",
        course_id=1,
        school_id=student_user.school_id,
        created_by=teacher_user.id,
        max_score=20,
        is_published=True,
    )

    assignment_two = Assignment(
        title="Assignment Two",
        description="Second assignment.",
        course_id=1,
        school_id=student_user.school_id,
        created_by=teacher_user.id,
        max_score=40,
        is_published=True,
    )

    db_session.add_all([assignment_one, assignment_two])
    await db_session.flush()

    db_session.add_all(
        [
            AssignmentSubmission(
                assignment_id=assignment_one.id,
                student_id=student_user.id,
                school_id=student_user.school_id,
                submission_text="Answer one",
                status="graded",
                score=10,
                feedback="Good.",
                graded_by=teacher_user.id,
            ),
            AssignmentSubmission(
                assignment_id=assignment_two.id,
                student_id=student_user.id,
                school_id=student_user.school_id,
                submission_text="Answer two",
                status="graded",
                score=30,
                feedback="Very good.",
                graded_by=teacher_user.id,
            ),
        ],
    )

    await db_session.commit()

    response = await client.get(
        f"/api/v1/student-progress/{student_user.id}",
        headers=auth_headers(teacher_user),
    )

    assert response.status_code == 200

    data = response.json()

    assert data["assignments_completed"] == 2
    assert data["average_assignment_score"] == 62.5
    assert data["recent_feedback_count"] == 2


@pytest.mark.asyncio
async def test_student_progress_reports_empty_defaults(
    client: AsyncClient,
    teacher_user,
    student_user,
    auth_headers,
):
    response = await client.get(
        f"/api/v1/student-progress/{student_user.id}",
        headers=auth_headers(teacher_user),
    )

    assert response.status_code == 200

    data = response.json()

    assert data["student_id"] == student_user.id
    assert data["attendance_percentage"] == 0.0
    assert data["assignments_completed"] == 0
    assert data["average_assignment_score"] is None
    assert data["report_count"] == 0
    assert data["latest_report_title"] is None
    assert data["recent_feedback_count"] == 0
