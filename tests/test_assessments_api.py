from __future__ import annotations

from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.assessment import Assessment, AssessmentStatus
from app.models.assessment_question import AssessmentQuestion
from app.models.course import Course
from app.models.user import UserRole
from tests.conftest import create_test_user


async def _create_course(
    db_session: AsyncSession,
    *,
    teacher_id: int,
    school_id: int,
    title: str = "Assessment API Test Course",
) -> Course:
    """
    Create and persist a course suitable for assessment API tests.
    """

    course = Course(
        title=title,
        description="Course used by assessment API tests.",
        teacher_id=teacher_id,
        school_id=school_id,
        published=True,
    )

    db_session.add(course)

    await db_session.commit()
    await db_session.refresh(course)

    return course


async def _create_assessment_via_api(
    client: AsyncClient,
    *,
    course_id: int,
    user,
    auth_headers,
    title: str = "Physics Assessment",
) -> dict:
    """
    Create a draft assessment through the public API.
    """

    response = await client.post(
        "/api/v1/assessments",
        json={
            "course_id": course_id,
            "title": title,
            "description": "Assessment API test.",
            "assessment_type": "class_test",
            "academic_year": "2026/27",
            "term": "Autumn",
            "anonymous_marking": False,
        },
        headers=auth_headers(user),
    )

    assert response.status_code == 201, response.text

    return response.json()


async def _add_markable_question(
    db_session: AsyncSession,
    *,
    assessment_id: int,
    question_number: str = "1",
    maximum_mark: Decimal = Decimal("10.00"),
) -> AssessmentQuestion:
    """
    Persist one markable assessment question.
    """

    question = AssessmentQuestion(
        assessment_id=assessment_id,
        question_number=question_number,
        prompt="Assessment API test question.",
        maximum_mark=maximum_mark,
        order=1,
        is_markable=True,
    )

    db_session.add(question)

    await db_session.commit()
    await db_session.refresh(question)

    return question


@pytest.mark.asyncio
async def test_teacher_can_create_assessment_for_own_course(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
):
    course = await _create_course(
        db_session,
        teacher_id=teacher_user.id,
        school_id=teacher_user.school_id,
    )

    response = await client.post(
        "/api/v1/assessments",
        json={
            "course_id": course.id,
            "title": "Mechanics Test",
            "description": "Forces and motion.",
            "assessment_type": "class_test",
            "academic_year": "2026/27",
            "term": "Autumn",
            "anonymous_marking": True,
        },
        headers=auth_headers(teacher_user),
    )

    assert response.status_code == 201, response.text

    data = response.json()

    assert data["id"] is not None
    assert data["course_id"] == course.id
    assert data["school_id"] == teacher_user.school_id
    assert data["created_by_id"] == teacher_user.id
    assert data["title"] == "Mechanics Test"
    assert data["description"] == "Forces and motion."
    assert data["assessment_type"] == "class_test"
    assert data["academic_year"] == "2026/27"
    assert data["term"] == "Autumn"
    assert data["status"] == AssessmentStatus.DRAFT.value
    assert data["anonymous_marking"] is True
    assert data["sections"] == []
    assert data["questions"] == []


@pytest.mark.asyncio
async def test_teacher_cannot_create_assessment_for_another_teachers_course(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
):
    other_teacher = await create_test_user(
        db_session,
        email="assessment.api.other.teacher@example.com",
        roles=[UserRole.TEACHER],
        school_id=teacher_user.school_id,
    )

    course = await _create_course(
        db_session,
        teacher_id=other_teacher.id,
        school_id=other_teacher.school_id,
        title="Other Teacher Course",
    )

    response = await client.post(
        "/api/v1/assessments",
        json={
            "course_id": course.id,
            "title": "Forbidden Assessment",
        },
        headers=auth_headers(teacher_user),
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_create_assessment_rejects_invalid_date_window(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
):
    course = await _create_course(
        db_session,
        teacher_id=teacher_user.id,
        school_id=teacher_user.school_id,
    )

    response = await client.post(
        "/api/v1/assessments",
        json={
            "course_id": course.id,
            "title": "Invalid Date Assessment",
            "scheduled_at": "2026-09-10T10:00:00+00:00",
            "closes_at": "2026-09-10T09:00:00+00:00",
        },
        headers=auth_headers(teacher_user),
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_teacher_can_get_own_assessment(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
):
    course = await _create_course(
        db_session,
        teacher_id=teacher_user.id,
        school_id=teacher_user.school_id,
    )

    created = await _create_assessment_via_api(
        client,
        course_id=course.id,
        user=teacher_user,
        auth_headers=auth_headers,
    )

    response = await client.get(
        f"/api/v1/assessments/{created['id']}",
        headers=auth_headers(teacher_user),
    )

    assert response.status_code == 200, response.text

    data = response.json()

    assert data["id"] == created["id"]
    assert data["course_id"] == course.id
    assert data["title"] == "Physics Assessment"


@pytest.mark.asyncio
async def test_teacher_cannot_get_other_teachers_assessment(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
):
    other_teacher = await create_test_user(
        db_session,
        email="assessment.api.owner@example.com",
        roles=[UserRole.TEACHER],
        school_id=teacher_user.school_id,
    )

    course = await _create_course(
        db_session,
        teacher_id=other_teacher.id,
        school_id=other_teacher.school_id,
        title="Other Teacher Assessment Course",
    )

    created = await _create_assessment_via_api(
        client,
        course_id=course.id,
        user=other_teacher,
        auth_headers=auth_headers,
        title="Other Teacher Assessment",
    )

    response = await client.get(
        f"/api/v1/assessments/{created['id']}",
        headers=auth_headers(teacher_user),
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_teacher_lists_only_own_assessments(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
):
    own_course = await _create_course(
        db_session,
        teacher_id=teacher_user.id,
        school_id=teacher_user.school_id,
        title="Teacher Assessment Course",
    )

    own_assessment = await _create_assessment_via_api(
        client,
        course_id=own_course.id,
        user=teacher_user,
        auth_headers=auth_headers,
        title="Teacher Assessment",
    )

    other_teacher = await create_test_user(
        db_session,
        email="assessment.api.list.other@example.com",
        roles=[UserRole.TEACHER],
        school_id=teacher_user.school_id,
    )

    other_course = await _create_course(
        db_session,
        teacher_id=other_teacher.id,
        school_id=other_teacher.school_id,
        title="Other Assessment Course",
    )

    other_assessment = await _create_assessment_via_api(
        client,
        course_id=other_course.id,
        user=other_teacher,
        auth_headers=auth_headers,
        title="Other Assessment",
    )

    response = await client.get(
        "/api/v1/assessments",
        headers=auth_headers(teacher_user),
    )

    assert response.status_code == 200, response.text

    data = response.json()

    assessment_ids = {assessment["id"] for assessment in data}

    assert own_assessment["id"] in assessment_ids
    assert other_assessment["id"] not in assessment_ids


@pytest.mark.asyncio
async def test_teacher_can_filter_assessments_by_course(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
):
    first_course = await _create_course(
        db_session,
        teacher_id=teacher_user.id,
        school_id=teacher_user.school_id,
        title="First Assessment Course",
    )

    second_course = await _create_course(
        db_session,
        teacher_id=teacher_user.id,
        school_id=teacher_user.school_id,
        title="Second Assessment Course",
    )

    first_assessment = await _create_assessment_via_api(
        client,
        course_id=first_course.id,
        user=teacher_user,
        auth_headers=auth_headers,
        title="First Assessment",
    )

    await _create_assessment_via_api(
        client,
        course_id=second_course.id,
        user=teacher_user,
        auth_headers=auth_headers,
        title="Second Assessment",
    )

    response = await client.get(
        f"/api/v1/assessments?course_id={first_course.id}",
        headers=auth_headers(teacher_user),
    )

    assert response.status_code == 200, response.text

    data = response.json()

    assert len(data) == 1
    assert data[0]["id"] == first_assessment["id"]
    assert data[0]["course_id"] == first_course.id


@pytest.mark.asyncio
async def test_teacher_can_update_draft_assessment(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
):
    course = await _create_course(
        db_session,
        teacher_id=teacher_user.id,
        school_id=teacher_user.school_id,
    )

    created = await _create_assessment_via_api(
        client,
        course_id=course.id,
        user=teacher_user,
        auth_headers=auth_headers,
    )

    response = await client.patch(
        f"/api/v1/assessments/{created['id']}",
        json={
            "title": "Updated Physics Assessment",
            "description": "Updated description.",
            "assessment_type": "mock",
            "term": "Spring",
            "anonymous_marking": True,
        },
        headers=auth_headers(teacher_user),
    )

    assert response.status_code == 200, response.text

    data = response.json()

    assert data["title"] == "Updated Physics Assessment"
    assert data["description"] == "Updated description."
    assert data["assessment_type"] == "mock"
    assert data["term"] == "Spring"
    assert data["anonymous_marking"] is True


@pytest.mark.asyncio
async def test_cannot_publish_assessment_without_questions(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
):
    course = await _create_course(
        db_session,
        teacher_id=teacher_user.id,
        school_id=teacher_user.school_id,
    )

    created = await _create_assessment_via_api(
        client,
        course_id=course.id,
        user=teacher_user,
        auth_headers=auth_headers,
    )

    response = await client.post(
        f"/api/v1/assessments/{created['id']}/publish",
        headers=auth_headers(teacher_user),
    )

    assert response.status_code == 409


@pytest.mark.asyncio
async def test_teacher_can_publish_valid_assessment(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
):
    course = await _create_course(
        db_session,
        teacher_id=teacher_user.id,
        school_id=teacher_user.school_id,
    )

    created = await _create_assessment_via_api(
        client,
        course_id=course.id,
        user=teacher_user,
        auth_headers=auth_headers,
    )

    await _add_markable_question(
        db_session,
        assessment_id=created["id"],
        maximum_mark=Decimal("10.00"),
    )

    response = await client.post(
        f"/api/v1/assessments/{created['id']}/publish",
        headers=auth_headers(teacher_user),
    )

    assert response.status_code == 200, response.text

    data = response.json()

    assert data["status"] == AssessmentStatus.PUBLISHED.value
    assert len(data["questions"]) == 1
    assert data["questions"][0]["question_number"] == "1"
    assert Decimal(data["questions"][0]["maximum_mark"]) == Decimal("10.00")


@pytest.mark.asyncio
async def test_published_assessment_cannot_be_edited(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
):
    course = await _create_course(
        db_session,
        teacher_id=teacher_user.id,
        school_id=teacher_user.school_id,
    )

    created = await _create_assessment_via_api(
        client,
        course_id=course.id,
        user=teacher_user,
        auth_headers=auth_headers,
    )

    await _add_markable_question(
        db_session,
        assessment_id=created["id"],
    )

    publish_response = await client.post(
        f"/api/v1/assessments/{created['id']}/publish",
        headers=auth_headers(teacher_user),
    )

    assert publish_response.status_code == 200, publish_response.text

    response = await client.patch(
        f"/api/v1/assessments/{created['id']}",
        json={
            "title": "Should Not Change",
        },
        headers=auth_headers(teacher_user),
    )

    assert response.status_code == 409


@pytest.mark.asyncio
async def test_published_assessment_can_be_closed(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
):
    course = await _create_course(
        db_session,
        teacher_id=teacher_user.id,
        school_id=teacher_user.school_id,
    )

    created = await _create_assessment_via_api(
        client,
        course_id=course.id,
        user=teacher_user,
        auth_headers=auth_headers,
    )

    await _add_markable_question(
        db_session,
        assessment_id=created["id"],
    )

    publish_response = await client.post(
        f"/api/v1/assessments/{created['id']}/publish",
        headers=auth_headers(teacher_user),
    )

    assert publish_response.status_code == 200, publish_response.text

    response = await client.post(
        f"/api/v1/assessments/{created['id']}/close",
        headers=auth_headers(teacher_user),
    )

    assert response.status_code == 200, response.text
    assert response.json()["status"] == AssessmentStatus.CLOSED.value


@pytest.mark.asyncio
async def test_closed_assessment_can_be_archived(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
):
    course = await _create_course(
        db_session,
        teacher_id=teacher_user.id,
        school_id=teacher_user.school_id,
    )

    created = await _create_assessment_via_api(
        client,
        course_id=course.id,
        user=teacher_user,
        auth_headers=auth_headers,
    )

    await _add_markable_question(
        db_session,
        assessment_id=created["id"],
    )

    publish_response = await client.post(
        f"/api/v1/assessments/{created['id']}/publish",
        headers=auth_headers(teacher_user),
    )

    assert publish_response.status_code == 200, publish_response.text

    close_response = await client.post(
        f"/api/v1/assessments/{created['id']}/close",
        headers=auth_headers(teacher_user),
    )

    assert close_response.status_code == 200, close_response.text

    response = await client.post(
        f"/api/v1/assessments/{created['id']}/archive",
        headers=auth_headers(teacher_user),
    )

    assert response.status_code == 200, response.text
    assert response.json()["status"] == AssessmentStatus.ARCHIVED.value


@pytest.mark.asyncio
async def test_generic_status_endpoint_rejects_invalid_transition(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
):
    course = await _create_course(
        db_session,
        teacher_id=teacher_user.id,
        school_id=teacher_user.school_id,
    )

    created = await _create_assessment_via_api(
        client,
        course_id=course.id,
        user=teacher_user,
        auth_headers=auth_headers,
    )

    response = await client.patch(
        f"/api/v1/assessments/{created['id']}/status",
        json={
            "status": AssessmentStatus.CLOSED.value,
        },
        headers=auth_headers(teacher_user),
    )

    assert response.status_code == 409


@pytest.mark.asyncio
async def test_teacher_can_delete_draft_assessment(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
):
    course = await _create_course(
        db_session,
        teacher_id=teacher_user.id,
        school_id=teacher_user.school_id,
    )

    created = await _create_assessment_via_api(
        client,
        course_id=course.id,
        user=teacher_user,
        auth_headers=auth_headers,
    )

    response = await client.delete(
        f"/api/v1/assessments/{created['id']}",
        headers=auth_headers(teacher_user),
    )

    assert response.status_code == 204

    deleted = await db_session.get(
        Assessment,
        created["id"],
    )

    assert deleted is None


@pytest.mark.asyncio
async def test_published_assessment_cannot_be_deleted(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
):
    course = await _create_course(
        db_session,
        teacher_id=teacher_user.id,
        school_id=teacher_user.school_id,
    )

    created = await _create_assessment_via_api(
        client,
        course_id=course.id,
        user=teacher_user,
        auth_headers=auth_headers,
    )

    await _add_markable_question(
        db_session,
        assessment_id=created["id"],
    )

    publish_response = await client.post(
        f"/api/v1/assessments/{created['id']}/publish",
        headers=auth_headers(teacher_user),
    )

    assert publish_response.status_code == 200, publish_response.text

    response = await client.delete(
        f"/api/v1/assessments/{created['id']}",
        headers=auth_headers(teacher_user),
    )

    assert response.status_code == 409
