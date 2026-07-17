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

    assert data["status"] == "draft"

    assert data["submitted_at"] is None
    assert data["submitted_by_id"] is None

    assert data["reviewed_at"] is None
    assert data["reviewed_by_id"] is None
    assert data["review_comments"] is None

    assert data["published"] is False
    assert data["published_at"] is None
    assert data["published_by_id"] is None


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
        status="draft",
        published=False,
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
    assert data[0]["status"] == "draft"


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
        status="published",
        published=True,
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
    assert data[0]["report_text"] == (
        "This report should be visible to linked parents."
    )
    assert data[0]["status"] == "published"
    assert data[0]["published"] is True


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
        status="draft",
        published=False,
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
        status="draft",
        published=False,
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
    assert data["status"] == "draft"


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
        status="draft",
        published=False,
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


@pytest.mark.asyncio
async def test_published_field_cannot_be_changed_through_patch(
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
        title="Draft Report",
        report_text="This report must use the workflow endpoints.",
        grade="B",
        academic_year="2026/27",
        term="Autumn",
        status="draft",
        published=False,
    )

    db_session.add(report)
    await db_session.commit()
    await db_session.refresh(report)

    response = await client.patch(
        f"/api/v1/student-reports/{report.id}",
        json={"published": True},
        headers=auth_headers(teacher_user),
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_status_field_cannot_be_changed_through_patch(
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
        title="Draft Status Report",
        report_text="Status must use the workflow endpoints.",
        grade="B",
        academic_year="2026/27",
        term="Autumn",
        status="draft",
        published=False,
    )

    db_session.add(report)
    await db_session.commit()
    await db_session.refresh(report)

    response = await client.patch(
        f"/api/v1/student-reports/{report.id}",
        json={"status": "published"},
        headers=auth_headers(teacher_user),
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_teacher_can_submit_own_draft_report(
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
        title="Submission Report",
        report_text="This report is complete and ready for review.",
        grade="A",
        academic_year="2026/27",
        term="Spring",
        status="draft",
        published=False,
    )

    db_session.add(report)
    await db_session.commit()
    await db_session.refresh(report)

    response = await client.post(
        f"/api/v1/student-reports/{report.id}/submit",
        headers=auth_headers(teacher_user),
    )

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "submitted"
    assert data["submitted_by_id"] == teacher_user.id
    assert data["submitted_at"] is not None

    assert data["reviewed_at"] is None
    assert data["reviewed_by_id"] is None
    assert data["review_comments"] is None

    assert data["published"] is False
    assert data["published_at"] is None
    assert data["published_by_id"] is None


@pytest.mark.asyncio
async def test_platform_admin_without_school_cannot_submit_report(
    client: AsyncClient,
    db_session: AsyncSession,
    student_user,
    teacher_user,
    platform_admin_user,
    auth_headers,
):
    report = StudentReport(
        school_id=student_user.school_id,
        student_id=student_user.id,
        teacher_id=teacher_user.id,
        title="Platform Admin Report",
        report_text="A school context is required.",
        grade="A",
        academic_year="2026/27",
        term="Summer",
        status="draft",
        published=False,
    )

    db_session.add(report)
    await db_session.commit()
    await db_session.refresh(report)

    response = await client.post(
        f"/api/v1/student-reports/{report.id}/submit",
        headers=auth_headers(platform_admin_user),
    )

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_submitted_report_cannot_be_submitted_again(
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
        title="Already Submitted Report",
        report_text="This report has already been submitted.",
        grade="A",
        academic_year="2026/27",
        term="Summer",
        status="submitted",
        published=False,
        submitted_by_id=teacher_user.id,
    )

    db_session.add(report)
    await db_session.commit()
    await db_session.refresh(report)

    response = await client.post(
        f"/api/v1/student-reports/{report.id}/submit",
        headers=auth_headers(teacher_user),
    )

    assert response.status_code == 409


@pytest.mark.asyncio
async def test_report_without_text_cannot_be_submitted(
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
        title="Incomplete Report",
        report_text="",
        grade="A",
        academic_year="2026/27",
        term="Summer",
        status="draft",
        published=False,
    )

    db_session.add(report)
    await db_session.commit()
    await db_session.refresh(report)

    response = await client.post(
        f"/api/v1/student-reports/{report.id}/submit",
        headers=auth_headers(teacher_user),
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_submitted_report_cannot_be_edited(
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
        title="Submitted Report",
        report_text="This report has already been submitted.",
        grade="A",
        academic_year="2026/27",
        term="Summer",
        status="submitted",
        published=False,
        submitted_by_id=teacher_user.id,
    )

    db_session.add(report)
    await db_session.commit()
    await db_session.refresh(report)

    response = await client.patch(
        f"/api/v1/student-reports/{report.id}",
        json={"grade": "B"},
        headers=auth_headers(teacher_user),
    )

    assert response.status_code == 409


@pytest.mark.asyncio
async def test_submitted_report_cannot_be_deleted(
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
        title="Submitted Report",
        report_text="This submitted report must not be deleted.",
        grade="A",
        academic_year="2026/27",
        term="Summer",
        status="submitted",
        published=False,
        submitted_by_id=teacher_user.id,
    )

    db_session.add(report)
    await db_session.commit()
    await db_session.refresh(report)

    response = await client.delete(
        f"/api/v1/student-reports/{report.id}",
        headers=auth_headers(teacher_user),
    )

    assert response.status_code == 409


@pytest.mark.asyncio
async def test_parent_cannot_see_draft_report(
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
        title="Draft Parent Hidden Report",
        report_text="This draft should not be visible to parents.",
        grade="B",
        academic_year="2026/27",
        term="Autumn",
        status="draft",
        published=False,
    )

    db_session.add_all([link, report])
    await db_session.commit()

    response = await client.get(
        "/api/v1/student-reports/parent",
        headers=auth_headers(parent_user),
    )

    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_parent_cannot_see_submitted_report(
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
        title="Submitted Parent Hidden Report",
        report_text="This submitted report should not be visible to parents.",
        grade="B",
        academic_year="2026/27",
        term="Autumn",
        status="submitted",
        published=False,
        submitted_by_id=teacher_user.id,
    )

    db_session.add_all([link, report])
    await db_session.commit()

    response = await client.get(
        "/api/v1/student-reports/parent",
        headers=auth_headers(parent_user),
    )

    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_parent_can_see_published_report(
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
        title="Published Parent Visible Report",
        report_text="This published report should be visible to parents.",
        grade="A",
        academic_year="2026/27",
        term="Summer",
        status="published",
        published=True,
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
    assert data[0]["title"] == "Published Parent Visible Report"
    assert data[0]["status"] == "published"
    assert data[0]["published"] is True


@pytest.mark.asyncio
async def test_school_admin_can_approve_submitted_report(
    client: AsyncClient,
    db_session: AsyncSession,
    student_user,
    teacher_user,
    school_admin_user,
    auth_headers,
):
    report = StudentReport(
        school_id=student_user.school_id,
        student_id=student_user.id,
        teacher_id=teacher_user.id,
        title="Report Awaiting Approval",
        report_text="This report is ready for approval.",
        grade="A",
        academic_year="2026/27",
        term="Summer",
        status="submitted",
        submitted_by_id=teacher_user.id,
        published=False,
    )

    db_session.add(report)
    await db_session.commit()
    await db_session.refresh(report)

    response = await client.post(
        f"/api/v1/student-reports/{report.id}/approve",
        json={
            "review_comments": "Approved for publication.",
        },
        headers=auth_headers(school_admin_user),
    )

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == report.id
    assert data["status"] == "approved"
    assert data["reviewed_at"] is not None
    assert data["reviewed_by_id"] == school_admin_user.id
    assert data["review_comments"] == "Approved for publication."

    assert data["published"] is False
    assert data["published_at"] is None
    assert data["published_by_id"] is None


@pytest.mark.asyncio
async def test_school_admin_can_approve_without_review_comments(
    client: AsyncClient,
    db_session: AsyncSession,
    student_user,
    teacher_user,
    school_admin_user,
    auth_headers,
):
    report = StudentReport(
        school_id=student_user.school_id,
        student_id=student_user.id,
        teacher_id=teacher_user.id,
        title="Approval Without Comments",
        report_text="This report can be approved without comments.",
        grade="A",
        academic_year="2026/27",
        term="Summer",
        status="submitted",
        submitted_by_id=teacher_user.id,
        published=False,
    )

    db_session.add(report)
    await db_session.commit()
    await db_session.refresh(report)

    response = await client.post(
        f"/api/v1/student-reports/{report.id}/approve",
        json={},
        headers=auth_headers(school_admin_user),
    )

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "approved"
    assert data["reviewed_at"] is not None
    assert data["reviewed_by_id"] == school_admin_user.id
    assert data["review_comments"] is None
    assert data["published"] is False


@pytest.mark.asyncio
async def test_school_admin_can_return_submitted_report(
    client: AsyncClient,
    db_session: AsyncSession,
    student_user,
    teacher_user,
    school_admin_user,
    auth_headers,
):
    report = StudentReport(
        school_id=student_user.school_id,
        student_id=student_user.id,
        teacher_id=teacher_user.id,
        title="Report Requiring Correction",
        report_text="This report requires a small correction.",
        grade="B",
        academic_year="2026/27",
        term="Summer",
        status="submitted",
        submitted_by_id=teacher_user.id,
        published=False,
    )

    db_session.add(report)
    await db_session.commit()
    await db_session.refresh(report)

    response = await client.post(
        f"/api/v1/student-reports/{report.id}/return",
        json={
            "review_comments": (
                "Please correct the final sentence before resubmitting."
            ),
        },
        headers=auth_headers(school_admin_user),
    )

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == report.id
    assert data["status"] == "draft"

    assert data["submitted_at"] is None
    assert data["submitted_by_id"] is None

    assert data["reviewed_at"] is not None
    assert data["reviewed_by_id"] == school_admin_user.id
    assert data["review_comments"] == (
        "Please correct the final sentence before resubmitting."
    )

    assert data["published"] is False
    assert data["published_at"] is None
    assert data["published_by_id"] is None


@pytest.mark.asyncio
async def test_returning_report_requires_review_comments(
    client: AsyncClient,
    db_session: AsyncSession,
    student_user,
    teacher_user,
    school_admin_user,
    auth_headers,
):
    report = StudentReport(
        school_id=student_user.school_id,
        student_id=student_user.id,
        teacher_id=teacher_user.id,
        title="Return Without Comments",
        report_text="This report should not be returned without comments.",
        grade="B",
        academic_year="2026/27",
        term="Summer",
        status="submitted",
        submitted_by_id=teacher_user.id,
        published=False,
    )

    db_session.add(report)
    await db_session.commit()
    await db_session.refresh(report)

    response = await client.post(
        f"/api/v1/student-reports/{report.id}/return",
        json={
            "review_comments": "",
        },
        headers=auth_headers(school_admin_user),
    )

    assert response.status_code == 409

    await db_session.refresh(report)

    assert report.status == "submitted"
    assert report.reviewed_at is None
    assert report.reviewed_by_id is None
    assert report.review_comments is None
    assert report.published is False


@pytest.mark.asyncio
async def test_teacher_cannot_approve_submitted_report(
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
        title="Teacher Approval Attempt",
        report_text="Teachers must not approve reports.",
        grade="A",
        academic_year="2026/27",
        term="Summer",
        status="submitted",
        submitted_by_id=teacher_user.id,
        published=False,
    )

    db_session.add(report)
    await db_session.commit()
    await db_session.refresh(report)

    response = await client.post(
        f"/api/v1/student-reports/{report.id}/approve",
        json={
            "review_comments": "Attempted teacher approval.",
        },
        headers=auth_headers(teacher_user),
    )

    assert response.status_code == 403

    await db_session.refresh(report)

    assert report.status == "submitted"
    assert report.reviewed_at is None
    assert report.reviewed_by_id is None
    assert report.review_comments is None
    assert report.published is False


@pytest.mark.asyncio
async def test_teacher_cannot_return_submitted_report(
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
        title="Teacher Return Attempt",
        report_text="Teachers must not return submitted reports.",
        grade="A",
        academic_year="2026/27",
        term="Summer",
        status="submitted",
        submitted_by_id=teacher_user.id,
        published=False,
    )

    db_session.add(report)
    await db_session.commit()
    await db_session.refresh(report)

    response = await client.post(
        f"/api/v1/student-reports/{report.id}/return",
        json={
            "review_comments": "Attempted teacher return.",
        },
        headers=auth_headers(teacher_user),
    )

    assert response.status_code == 403

    await db_session.refresh(report)

    assert report.status == "submitted"
    assert report.reviewed_at is None
    assert report.reviewed_by_id is None
    assert report.review_comments is None
    assert report.published is False


@pytest.mark.asyncio
async def test_draft_report_cannot_be_approved(
    client: AsyncClient,
    db_session: AsyncSession,
    student_user,
    teacher_user,
    school_admin_user,
    auth_headers,
):
    report = StudentReport(
        school_id=student_user.school_id,
        student_id=student_user.id,
        teacher_id=teacher_user.id,
        title="Draft Approval Attempt",
        report_text="A draft report cannot be approved.",
        grade="B",
        academic_year="2026/27",
        term="Summer",
        status="draft",
        published=False,
    )

    db_session.add(report)
    await db_session.commit()
    await db_session.refresh(report)

    response = await client.post(
        f"/api/v1/student-reports/{report.id}/approve",
        json={},
        headers=auth_headers(school_admin_user),
    )

    assert response.status_code == 409

    await db_session.refresh(report)

    assert report.status == "draft"
    assert report.reviewed_at is None
    assert report.reviewed_by_id is None
    assert report.review_comments is None
    assert report.published is False


@pytest.mark.asyncio
async def test_approved_report_cannot_be_returned(
    client: AsyncClient,
    db_session: AsyncSession,
    student_user,
    teacher_user,
    school_admin_user,
    auth_headers,
):
    report = StudentReport(
        school_id=student_user.school_id,
        student_id=student_user.id,
        teacher_id=teacher_user.id,
        title="Approved Return Attempt",
        report_text="An approved report cannot use the submitted return route.",
        grade="A",
        academic_year="2026/27",
        term="Summer",
        status="approved",
        submitted_by_id=teacher_user.id,
        reviewed_by_id=school_admin_user.id,
        published=False,
    )

    db_session.add(report)
    await db_session.commit()
    await db_session.refresh(report)

    response = await client.post(
        f"/api/v1/student-reports/{report.id}/return",
        json={
            "review_comments": "Attempting to return an approved report.",
        },
        headers=auth_headers(school_admin_user),
    )

    assert response.status_code == 409

    await db_session.refresh(report)

    assert report.status == "approved"
    assert report.reviewed_by_id == school_admin_user.id
    assert report.published is False
