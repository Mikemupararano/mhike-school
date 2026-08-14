from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.assessment import Assessment, AssessmentStatus
from app.models.class_group import ClassGroup
from app.models.course import Course
from app.models.enrollment import Enrollment
from app.models.user import UserRole
from tests.conftest import create_test_user


async def _create_course(
    db_session: AsyncSession,
    *,
    teacher_id: int,
    school_id: int,
    title: str = "Bulk Candidate API Course",
) -> Course:
    course = Course(
        title=title,
        description="Course used by bulk candidate API tests.",
        teacher_id=teacher_id,
        school_id=school_id,
        published=True,
    )

    db_session.add(
        course,
    )
    await db_session.commit()
    await db_session.refresh(
        course,
    )

    return course


async def _create_assessment(
    db_session: AsyncSession,
    *,
    teacher_user,
    title: str = "Bulk Candidate API Assessment",
    assessment_status: AssessmentStatus = AssessmentStatus.DRAFT,
) -> Assessment:
    course = await _create_course(
        db_session,
        teacher_id=teacher_user.id,
        school_id=teacher_user.school_id,
        title=f"{title} Course",
    )

    assessment = Assessment(
        school_id=teacher_user.school_id,
        course_id=course.id,
        created_by_id=teacher_user.id,
        title=title,
        description="Bulk candidate API test.",
        assessment_type="test",
        academic_year="2026/27",
        term="Autumn",
        status=assessment_status,
        anonymous_marking=False,
    )

    db_session.add(
        assessment,
    )
    await db_session.commit()
    await db_session.refresh(
        assessment,
    )

    return assessment


async def _create_student(
    db_session: AsyncSession,
    *,
    school_id: int,
    email: str,
):
    return await create_test_user(
        db_session,
        email=email,
        roles=[
            UserRole.STUDENT,
        ],
        school_id=school_id,
    )


async def _create_class(
    db_session: AsyncSession,
    *,
    school_id: int,
    name: str,
) -> ClassGroup:
    class_group = ClassGroup(
        name=name,
        school_id=school_id,
    )

    db_session.add(
        class_group,
    )
    await db_session.commit()
    await db_session.refresh(
        class_group,
    )

    return class_group


async def _enrol_student(
    db_session: AsyncSession,
    *,
    class_id: int,
    student_id: int,
) -> Enrollment:
    enrollment = Enrollment(
        class_id=class_id,
        user_id=student_id,
    )

    db_session.add(
        enrollment,
    )
    await db_session.commit()
    await db_session.refresh(
        enrollment,
    )

    return enrollment


@pytest.mark.asyncio
async def test_teacher_can_bulk_allocate_students_to_own_assessment(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
) -> None:
    assessment = await _create_assessment(
        db_session,
        teacher_user=teacher_user,
    )

    first_student = await _create_student(
        db_session,
        school_id=teacher_user.school_id,
        email="bulk.api.first@example.com",
    )
    second_student = await _create_student(
        db_session,
        school_id=teacher_user.school_id,
        email="bulk.api.second@example.com",
    )

    response = await client.post(
        f"/api/v1/assessment-candidates/assessment/{assessment.id}/bulk",
        json={
            "student_ids": [
                first_student.id,
                second_student.id,
            ],
        },
        headers=auth_headers(
            teacher_user,
        ),
    )

    assert response.status_code == 200, response.text

    data = response.json()

    assert data["assessment_id"] == assessment.id
    assert data["source"] == "explicit"
    assert data["requested_count"] == 2
    assert data["unique_requested_count"] == 2
    assert data["created_count"] == 2
    assert data["already_allocated_count"] == 0
    assert data["ineligible_count"] == 0

    assert {
        item["student_id"] for item in data["items"] if item["outcome"] == "created"
    } == {
        first_student.id,
        second_student.id,
    }


@pytest.mark.asyncio
async def test_bulk_api_deduplicates_student_ids(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
) -> None:
    assessment = await _create_assessment(
        db_session,
        teacher_user=teacher_user,
    )

    student = await _create_student(
        db_session,
        school_id=teacher_user.school_id,
        email="bulk.api.deduplicate@example.com",
    )

    response = await client.post(
        f"/api/v1/assessment-candidates/assessment/{assessment.id}/bulk",
        json={
            "student_ids": [
                student.id,
                student.id,
                student.id,
            ],
        },
        headers=auth_headers(
            teacher_user,
        ),
    )

    assert response.status_code == 200, response.text

    data = response.json()

    assert data["requested_count"] == 3
    assert data["unique_requested_count"] == 1
    assert data["created_count"] == 1
    assert len(data["items"]) == 1


@pytest.mark.asyncio
async def test_bulk_api_is_idempotent_for_existing_candidates(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
) -> None:
    assessment = await _create_assessment(
        db_session,
        teacher_user=teacher_user,
    )

    student = await _create_student(
        db_session,
        school_id=teacher_user.school_id,
        email="bulk.api.idempotent@example.com",
    )

    first = await client.post(
        f"/api/v1/assessment-candidates/assessment/{assessment.id}/bulk",
        json={
            "student_ids": [
                student.id,
            ],
        },
        headers=auth_headers(
            teacher_user,
        ),
    )

    assert first.status_code == 200, first.text
    assert first.json()["created_count"] == 1

    second = await client.post(
        f"/api/v1/assessment-candidates/assessment/{assessment.id}/bulk",
        json={
            "student_ids": [
                student.id,
            ],
        },
        headers=auth_headers(
            teacher_user,
        ),
    )

    assert second.status_code == 200, second.text

    data = second.json()

    assert data["created_count"] == 0
    assert data["already_allocated_count"] == 1
    assert data["items"][0]["outcome"] == "already_allocated"


@pytest.mark.asyncio
async def test_bulk_api_rejects_non_student(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
) -> None:
    assessment = await _create_assessment(
        db_session,
        teacher_user=teacher_user,
    )

    other_teacher = await create_test_user(
        db_session,
        email="bulk.api.non.student@example.com",
        roles=[
            UserRole.TEACHER,
        ],
        school_id=teacher_user.school_id,
    )

    response = await client.post(
        f"/api/v1/assessment-candidates/assessment/{assessment.id}/bulk",
        json={
            "student_ids": [
                other_teacher.id,
            ],
        },
        headers=auth_headers(
            teacher_user,
        ),
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_bulk_api_rejects_other_school_student(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
) -> None:
    assessment = await _create_assessment(
        db_session,
        teacher_user=teacher_user,
    )

    other_school_student = await create_test_user(
        db_session,
        email="bulk.api.other.school@example.com",
        roles=[
            UserRole.STUDENT,
        ],
        school_id=None,
    )

    response = await client.post(
        f"/api/v1/assessment-candidates/assessment/{assessment.id}/bulk",
        json={
            "student_ids": [
                other_school_student.id,
            ],
        },
        headers=auth_headers(
            teacher_user,
        ),
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_bulk_api_rejects_closed_assessment(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
) -> None:
    assessment = await _create_assessment(
        db_session,
        teacher_user=teacher_user,
        assessment_status=AssessmentStatus.CLOSED,
    )

    student = await _create_student(
        db_session,
        school_id=teacher_user.school_id,
        email="bulk.api.closed@example.com",
    )

    response = await client.post(
        f"/api/v1/assessment-candidates/assessment/{assessment.id}/bulk",
        json={
            "student_ids": [
                student.id,
            ],
        },
        headers=auth_headers(
            teacher_user,
        ),
    )

    assert response.status_code == 409


@pytest.mark.asyncio
async def test_teacher_can_allocate_class_to_assessment(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
) -> None:
    assessment = await _create_assessment(
        db_session,
        teacher_user=teacher_user,
    )

    class_group = await _create_class(
        db_session,
        school_id=teacher_user.school_id,
        name="Bulk API Class",
    )

    first_student = await _create_student(
        db_session,
        school_id=teacher_user.school_id,
        email="bulk.api.class.first@example.com",
    )
    second_student = await _create_student(
        db_session,
        school_id=teacher_user.school_id,
        email="bulk.api.class.second@example.com",
    )

    await _enrol_student(
        db_session,
        class_id=class_group.id,
        student_id=first_student.id,
    )
    await _enrol_student(
        db_session,
        class_id=class_group.id,
        student_id=second_student.id,
    )

    response = await client.post(
        (
            f"/api/v1/assessment-candidates/assessment/"
            f"{assessment.id}/class/{class_group.id}"
        ),
        headers=auth_headers(
            teacher_user,
        ),
    )

    assert response.status_code == 200, response.text

    data = response.json()

    assert data["source"] == "class"
    assert data["class_id"] == class_group.id
    assert data["requested_count"] == 2
    assert data["created_count"] == 2


@pytest.mark.asyncio
async def test_class_allocation_api_is_idempotent(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
) -> None:
    assessment = await _create_assessment(
        db_session,
        teacher_user=teacher_user,
    )

    class_group = await _create_class(
        db_session,
        school_id=teacher_user.school_id,
        name="Bulk API Idempotent Class",
    )

    student = await _create_student(
        db_session,
        school_id=teacher_user.school_id,
        email="bulk.api.class.idempotent@example.com",
    )

    await _enrol_student(
        db_session,
        class_id=class_group.id,
        student_id=student.id,
    )

    url = (
        f"/api/v1/assessment-candidates/assessment/"
        f"{assessment.id}/class/{class_group.id}"
    )

    first = await client.post(
        url,
        headers=auth_headers(
            teacher_user,
        ),
    )

    assert first.status_code == 200, first.text
    assert first.json()["created_count"] == 1

    second = await client.post(
        url,
        headers=auth_headers(
            teacher_user,
        ),
    )

    assert second.status_code == 200, second.text

    data = second.json()

    assert data["created_count"] == 0
    assert data["already_allocated_count"] == 1


@pytest.mark.asyncio
async def test_class_preview_reports_existing_and_eligible_students(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
) -> None:
    assessment = await _create_assessment(
        db_session,
        teacher_user=teacher_user,
    )

    class_group = await _create_class(
        db_session,
        school_id=teacher_user.school_id,
        name="Bulk API Preview Class",
    )

    allocated_student = await _create_student(
        db_session,
        school_id=teacher_user.school_id,
        email="bulk.api.preview.allocated@example.com",
    )
    eligible_student = await _create_student(
        db_session,
        school_id=teacher_user.school_id,
        email="bulk.api.preview.eligible@example.com",
    )

    await _enrol_student(
        db_session,
        class_id=class_group.id,
        student_id=allocated_student.id,
    )
    await _enrol_student(
        db_session,
        class_id=class_group.id,
        student_id=eligible_student.id,
    )

    allocation_response = await client.post(
        f"/api/v1/assessment-candidates/assessment/{assessment.id}/bulk",
        json={
            "student_ids": [
                allocated_student.id,
            ],
        },
        headers=auth_headers(
            teacher_user,
        ),
    )

    assert allocation_response.status_code == 200, allocation_response.text

    response = await client.get(
        (
            f"/api/v1/assessment-candidates/assessment/"
            f"{assessment.id}/class/{class_group.id}/preview"
        ),
        headers=auth_headers(
            teacher_user,
        ),
    )

    assert response.status_code == 200, response.text

    data = response.json()

    assert data["allocation_allowed"] is True
    assert data["enrolled_count"] == 2
    assert data["student_count"] == 2
    assert data["eligible_count"] == 1
    assert data["already_allocated_count"] == 1

    assert data["eligible_student_ids"] == [
        eligible_student.id,
    ]

    assert data["already_allocated_student_ids"] == [
        allocated_student.id,
    ]


@pytest.mark.asyncio
async def test_closed_assessment_class_preview_is_available_but_not_allocatable(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
) -> None:
    assessment = await _create_assessment(
        db_session,
        teacher_user=teacher_user,
        assessment_status=AssessmentStatus.CLOSED,
    )

    class_group = await _create_class(
        db_session,
        school_id=teacher_user.school_id,
        name="Bulk API Closed Preview",
    )

    student = await _create_student(
        db_session,
        school_id=teacher_user.school_id,
        email="bulk.api.preview.closed@example.com",
    )

    await _enrol_student(
        db_session,
        class_id=class_group.id,
        student_id=student.id,
    )

    response = await client.get(
        (
            f"/api/v1/assessment-candidates/assessment/"
            f"{assessment.id}/class/{class_group.id}/preview"
        ),
        headers=auth_headers(
            teacher_user,
        ),
    )

    assert response.status_code == 200, response.text

    data = response.json()

    assert data["allocation_allowed"] is False
    assert data["eligible_count"] == 1


@pytest.mark.asyncio
async def test_class_allocation_rejects_unknown_class(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
) -> None:
    assessment = await _create_assessment(
        db_session,
        teacher_user=teacher_user,
    )

    response = await client.post(
        (f"/api/v1/assessment-candidates/assessment/" f"{assessment.id}/class/999999"),
        headers=auth_headers(
            teacher_user,
        ),
    )

    assert response.status_code == 404
