import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.report_session import ReportSession
from app.models.school import School


@pytest.mark.asyncio
async def test_school_admin_can_create_report_session(
    client: AsyncClient,
    school_admin_user,
    auth_headers,
):
    payload = {
        "title": "Year 10 Autumn Reports",
        "academic_year": "2026/27",
        "term": "Autumn",
        "active": True,
        "include_work_covered": True,
        "include_student_comment": True,
        "include_exam_mark": True,
        "include_attainment_grade": True,
        "include_effort_grade": True,
        "include_target_grade": False,
        "include_next_steps": True,
        "include_tutor_comment": False,
    }

    response = await client.post(
        "/api/v1/report-sessions/",
        json=payload,
        headers=auth_headers(school_admin_user),
    )

    assert response.status_code == 201

    data = response.json()

    assert data["title"] == "Year 10 Autumn Reports"
    assert data["academic_year"] == "2026/27"
    assert data["term"] == "Autumn"
    assert data["school_id"] == school_admin_user.school_id
    assert data["active"] is True
    assert data["include_work_covered"] is True
    assert data["include_student_comment"] is True
    assert data["include_exam_mark"] is True
    assert data["include_attainment_grade"] is True
    assert data["include_effort_grade"] is True
    assert data["include_target_grade"] is False
    assert data["include_next_steps"] is True
    assert data["include_tutor_comment"] is False


@pytest.mark.asyncio
async def test_teacher_cannot_create_report_session(
    client: AsyncClient,
    teacher_user,
    auth_headers,
):
    payload = {
        "title": "Teacher Attempt",
        "academic_year": "2026/27",
        "term": "Spring",
        "active": True,
    }

    response = await client.post(
        "/api/v1/report-sessions/",
        json=payload,
        headers=auth_headers(teacher_user),
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_school_staff_can_list_report_sessions(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
):
    report_session = ReportSession(
        school_id=teacher_user.school_id,
        title="Year 9 Spring Reports",
        academic_year="2026/27",
        term="Spring",
        active=True,
        include_work_covered=True,
        include_student_comment=True,
        include_exam_mark=False,
        include_attainment_grade=True,
        include_effort_grade=True,
        include_target_grade=False,
        include_next_steps=True,
        include_tutor_comment=False,
    )

    db_session.add(report_session)
    await db_session.commit()
    await db_session.refresh(report_session)

    response = await client.get(
        "/api/v1/report-sessions/",
        headers=auth_headers(teacher_user),
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data) == 1
    assert data[0]["id"] == report_session.id
    assert data[0]["title"] == "Year 9 Spring Reports"
    assert data[0]["school_id"] == teacher_user.school_id


@pytest.mark.asyncio
async def test_school_admin_can_update_report_session(
    client: AsyncClient,
    db_session: AsyncSession,
    school_admin_user,
    auth_headers,
):
    report_session = ReportSession(
        school_id=school_admin_user.school_id,
        title="Original Report Session",
        academic_year="2026/27",
        term="Autumn",
        active=True,
        include_work_covered=True,
        include_student_comment=True,
        include_exam_mark=False,
        include_attainment_grade=False,
        include_effort_grade=False,
        include_target_grade=False,
        include_next_steps=False,
        include_tutor_comment=False,
    )

    db_session.add(report_session)
    await db_session.commit()
    await db_session.refresh(report_session)

    response = await client.patch(
        f"/api/v1/report-sessions/{report_session.id}",
        json={
            "title": "Updated Report Session",
            "include_exam_mark": True,
            "include_effort_grade": True,
            "active": False,
        },
        headers=auth_headers(school_admin_user),
    )

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == report_session.id
    assert data["title"] == "Updated Report Session"
    assert data["include_exam_mark"] is True
    assert data["include_effort_grade"] is True
    assert data["active"] is False


@pytest.mark.asyncio
async def test_teacher_cannot_update_report_session(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
):
    report_session = ReportSession(
        school_id=teacher_user.school_id,
        title="Protected Report Session",
        academic_year="2026/27",
        term="Summer",
        active=True,
        include_work_covered=True,
        include_student_comment=True,
        include_exam_mark=False,
        include_attainment_grade=False,
        include_effort_grade=False,
        include_target_grade=False,
        include_next_steps=False,
        include_tutor_comment=False,
    )

    db_session.add(report_session)
    await db_session.commit()
    await db_session.refresh(report_session)

    response = await client.patch(
        f"/api/v1/report-sessions/{report_session.id}",
        json={"title": "Teacher Should Not Update"},
        headers=auth_headers(teacher_user),
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_school_admin_can_delete_report_session(
    client: AsyncClient,
    db_session: AsyncSession,
    school_admin_user,
    auth_headers,
):
    report_session = ReportSession(
        school_id=school_admin_user.school_id,
        title="Delete Report Session",
        academic_year="2026/27",
        term="Summer",
        active=True,
        include_work_covered=True,
        include_student_comment=True,
        include_exam_mark=False,
        include_attainment_grade=False,
        include_effort_grade=False,
        include_target_grade=False,
        include_next_steps=False,
        include_tutor_comment=False,
    )

    db_session.add(report_session)
    await db_session.commit()
    await db_session.refresh(report_session)

    response = await client.delete(
        f"/api/v1/report-sessions/{report_session.id}",
        headers=auth_headers(school_admin_user),
    )

    assert response.status_code == 204

    deleted = await db_session.get(ReportSession, report_session.id)

    assert deleted is None


@pytest.mark.asyncio
async def test_teacher_cannot_delete_report_session(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
):
    report_session = ReportSession(
        school_id=teacher_user.school_id,
        title="Teacher Cannot Delete",
        academic_year="2026/27",
        term="Summer",
        active=True,
        include_work_covered=True,
        include_student_comment=True,
        include_exam_mark=False,
        include_attainment_grade=False,
        include_effort_grade=False,
        include_target_grade=False,
        include_next_steps=False,
        include_tutor_comment=False,
    )

    db_session.add(report_session)
    await db_session.commit()
    await db_session.refresh(report_session)

    response = await client.delete(
        f"/api/v1/report-sessions/{report_session.id}",
        headers=auth_headers(teacher_user),
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_report_session_school_isolation(
    client: AsyncClient,
    db_session: AsyncSession,
    school_admin_user,
    auth_headers,
):
    other_school = School(
        name="Other School",
    )

    db_session.add(other_school)
    await db_session.flush()
    await db_session.refresh(other_school)

    if other_school.id == school_admin_user.school_id:
        other_school = School(
            name="Second Other School",
        )

        db_session.add(other_school)
        await db_session.flush()
        await db_session.refresh(other_school)

    other_school_session = ReportSession(
        school_id=other_school.id,
        title="Other School Report Session",
        academic_year="2026/27",
        term="Autumn",
        active=True,
        include_work_covered=True,
        include_student_comment=True,
        include_exam_mark=True,
        include_attainment_grade=True,
        include_effort_grade=True,
        include_target_grade=True,
        include_next_steps=True,
        include_tutor_comment=True,
    )

    db_session.add(other_school_session)
    await db_session.commit()

    response = await client.get(
        "/api/v1/report-sessions/",
        headers=auth_headers(school_admin_user),
    )

    assert response.status_code == 200

    data = response.json()

    assert all(
        report_session["school_id"] == school_admin_user.school_id
        for report_session in data
    )

    assert all(
        report_session["title"] != "Other School Report Session"
        for report_session in data
    )
