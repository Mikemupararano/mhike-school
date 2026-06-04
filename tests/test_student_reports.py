import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.parent_student import ParentStudent
from app.models.student_report import StudentReport


@pytest.mark.asyncio
async def test_can_create_student_report(
    client: AsyncClient,
    student_user,
    teacher_user,
    auth_headers,
):
    payload = {
        "student_id": student_user.id,
        "teacher_id": teacher_user.id,
        "title": "Autumn Progress Report",
        "report_text": "Excellent progress in Chemistry.",
        "grade": "A",
        "academic_year": "2026/27",
        "term": "Autumn",
    }

    response = await client.post(
        "/api/v1/student-reports/",
        json=payload,
        headers=auth_headers(teacher_user),
    )

    assert response.status_code == 201

    data = response.json()

    assert data["student_id"] == student_user.id
    assert data["teacher_id"] == teacher_user.id
    assert data["title"] == "Autumn Progress Report"
    assert data["report_text"] == "Excellent progress in Chemistry."
    assert data["grade"] == "A"
    assert data["academic_year"] == "2026/27"
    assert data["term"] == "Autumn"


@pytest.mark.asyncio
async def test_can_list_student_reports_for_student(
    client: AsyncClient,
    db_session: AsyncSession,
    student_user,
    teacher_user,
    auth_headers,
):
    report = StudentReport(
        school_id=student_user.school_id,
        student_id=student_user.id,
        teacher_id=teacher_user.id,
        title="Spring Progress Report",
        report_text="Good effort and improving confidence.",
        grade="B",
        academic_year="2026/27",
        term="Spring",
    )

    db_session.add(report)
    await db_session.commit()

    response = await client.get(
        f"/api/v1/student-reports/student/{student_user.id}",
        headers=auth_headers(teacher_user),
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data) == 1
    assert data[0]["student_id"] == student_user.id
    assert data[0]["title"] == "Spring Progress Report"
    assert data[0]["grade"] == "B"


@pytest.mark.asyncio
async def test_linked_parent_can_view_child_reports(
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
        title="Parent Visible Report",
        report_text="This report should be visible to linked parents.",
        grade="A",
        academic_year="2026/27",
        term="Summer",
    )

    db_session.add_all([link, report])
    await db_session.commit()

    response = await client.get(
        "/api/v1/student-reports/parent",
        headers=auth_headers(parent_user),
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data) == 1
    assert data[0]["student_id"] == student_user.id
    assert data[0]["title"] == "Parent Visible Report"
    assert data[0]["report_text"] == "This report should be visible to linked parents."


@pytest.mark.asyncio
async def test_unlinked_parent_cannot_view_child_reports(
    client: AsyncClient,
    db_session: AsyncSession,
    parent_user,
    student_user,
    teacher_user,
    auth_headers,
):
    report = StudentReport(
        school_id=student_user.school_id,
        student_id=student_user.id,
        teacher_id=teacher_user.id,
        title="Private Report",
        report_text="This report should not be visible to unlinked parents.",
        grade="C",
        academic_year="2026/27",
        term="Autumn",
    )

    db_session.add(report)
    await db_session.commit()

    response = await client.get(
        "/api/v1/student-reports/parent",
        headers=auth_headers(parent_user),
    )

    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_can_update_student_report(
    client: AsyncClient,
    db_session: AsyncSession,
    student_user,
    teacher_user,
    auth_headers,
):
    report = StudentReport(
        school_id=student_user.school_id,
        student_id=student_user.id,
        teacher_id=teacher_user.id,
        title="Original Report",
        report_text="Original text.",
        grade="B",
        academic_year="2026/27",
        term="Autumn",
    )

    db_session.add(report)
    await db_session.commit()
    await db_session.refresh(report)

    response = await client.patch(
        f"/api/v1/student-reports/{report.id}",
        json={
            "title": "Updated Report",
            "report_text": "Updated report text.",
            "grade": "A",
        },
        headers=auth_headers(teacher_user),
    )

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == report.id
    assert data["title"] == "Updated Report"
    assert data["report_text"] == "Updated report text."
    assert data["grade"] == "A"


@pytest.mark.asyncio
async def test_can_delete_student_report(
    client: AsyncClient,
    db_session: AsyncSession,
    student_user,
    teacher_user,
    auth_headers,
):
    report = StudentReport(
        school_id=student_user.school_id,
        student_id=student_user.id,
        teacher_id=teacher_user.id,
        title="Delete Me",
        report_text="This report will be deleted.",
        grade="B",
        academic_year="2026/27",
        term="Autumn",
    )

    db_session.add(report)
    await db_session.commit()
    await db_session.refresh(report)

    response = await client.delete(
        f"/api/v1/student-reports/{report.id}",
        headers=auth_headers(teacher_user),
    )

    assert response.status_code == 204

    deleted = await db_session.get(StudentReport, report.id)

    assert deleted is None
