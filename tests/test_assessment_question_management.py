from __future__ import annotations

from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.assessment import AssessmentStatus
from app.models.course import Course
from app.models.user import UserRole
from tests.conftest import create_test_user


async def _create_course(
    db_session: AsyncSession,
    *,
    teacher_id: int,
    school_id: int,
    title: str = "Assessment Structure Test Course",
) -> Course:
    """
    Create and persist a course suitable for assessment-structure tests.
    """

    course = Course(
        title=title,
        description="Course used by assessment structure API tests.",
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
    client: AsyncClient,
    *,
    course_id: int,
    user,
    auth_headers,
    title: str = "Assessment Structure Test",
) -> dict:
    """
    Create a draft assessment through the public API.
    """

    response = await client.post(
        "/api/v1/assessments",
        json={
            "course_id": course_id,
            "title": title,
            "description": "Assessment structure API test.",
            "assessment_type": "class_test",
            "academic_year": "2026/27",
            "term": "Autumn",
            "anonymous_marking": False,
        },
        headers=auth_headers(
            user,
        ),
    )

    assert response.status_code == 201, response.text

    return response.json()


async def _create_section(
    client: AsyncClient,
    *,
    assessment_id: int,
    user,
    auth_headers,
    title: str = "Section A",
    description: str | None = "Core questions.",
    order: int = 1,
    is_optional: bool = False,
) -> dict:
    """
    Create an assessment section through the public API.
    """

    response = await client.post(
        f"/api/v1/assessments/{assessment_id}/sections",
        json={
            "title": title,
            "description": description,
            "order": order,
            "is_optional": is_optional,
        },
        headers=auth_headers(
            user,
        ),
    )

    assert response.status_code == 201, response.text

    return response.json()


async def _create_question(
    client: AsyncClient,
    *,
    assessment_id: int,
    user,
    auth_headers,
    question_number: str = "1",
    maximum_mark: Decimal = Decimal("10.00"),
    section_id: int | None = None,
    parent_question_id: int | None = None,
    title: str | None = "Question 1",
    prompt: str | None = "Answer the question.",
    order: int = 1,
    is_markable: bool = True,
) -> dict:
    """
    Create an assessment question through the public API.
    """

    response = await client.post(
        f"/api/v1/assessments/{assessment_id}/questions",
        json={
            "section_id": section_id,
            "parent_question_id": parent_question_id,
            "question_number": question_number,
            "title": title,
            "prompt": prompt,
            "maximum_mark": str(
                maximum_mark,
            ),
            "order": order,
            "is_markable": is_markable,
        },
        headers=auth_headers(
            user,
        ),
    )

    assert response.status_code == 201, response.text

    return response.json()


@pytest.mark.asyncio
async def test_teacher_can_create_and_list_assessment_sections(
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

    assessment = await _create_assessment(
        client,
        course_id=course.id,
        user=teacher_user,
        auth_headers=auth_headers,
    )

    first_section = await _create_section(
        client,
        assessment_id=assessment["id"],
        user=teacher_user,
        auth_headers=auth_headers,
        title="Section A",
        order=1,
    )

    second_section = await _create_section(
        client,
        assessment_id=assessment["id"],
        user=teacher_user,
        auth_headers=auth_headers,
        title="Section B",
        description="Optional questions.",
        order=2,
        is_optional=True,
    )

    response = await client.get(
        f"/api/v1/assessments/{assessment['id']}/sections",
        headers=auth_headers(
            teacher_user,
        ),
    )

    assert response.status_code == 200, response.text

    data = response.json()

    assert len(data) == 2

    assert data[0]["id"] == first_section["id"]
    assert data[0]["title"] == "Section A"
    assert data[0]["order"] == 1
    assert data[0]["is_optional"] is False

    assert data[1]["id"] == second_section["id"]
    assert data[1]["title"] == "Section B"
    assert data[1]["order"] == 2
    assert data[1]["is_optional"] is True


@pytest.mark.asyncio
async def test_teacher_can_update_section_and_clear_description(
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

    assessment = await _create_assessment(
        client,
        course_id=course.id,
        user=teacher_user,
        auth_headers=auth_headers,
    )

    section = await _create_section(
        client,
        assessment_id=assessment["id"],
        user=teacher_user,
        auth_headers=auth_headers,
        description="Description to clear.",
    )

    response = await client.patch(
        (f"/api/v1/assessments/{assessment['id']}" f"/sections/{section['id']}"),
        json={
            "title": "Updated Section",
            "description": None,
            "is_optional": True,
        },
        headers=auth_headers(
            teacher_user,
        ),
    )

    assert response.status_code == 200, response.text

    data = response.json()

    assert data["title"] == "Updated Section"
    assert data["description"] is None
    assert data["is_optional"] is True
    assert data["order"] == 1


@pytest.mark.asyncio
async def test_section_order_must_be_unique_within_assessment(
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

    assessment = await _create_assessment(
        client,
        course_id=course.id,
        user=teacher_user,
        auth_headers=auth_headers,
    )

    await _create_section(
        client,
        assessment_id=assessment["id"],
        user=teacher_user,
        auth_headers=auth_headers,
        title="First Section",
        order=1,
    )

    response = await client.post(
        f"/api/v1/assessments/{assessment['id']}/sections",
        json={
            "title": "Duplicate Order",
            "order": 1,
            "is_optional": False,
        },
        headers=auth_headers(
            teacher_user,
        ),
    )

    assert response.status_code == 409


@pytest.mark.asyncio
async def test_teacher_can_create_question_with_section_and_parent(
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

    assessment = await _create_assessment(
        client,
        course_id=course.id,
        user=teacher_user,
        auth_headers=auth_headers,
    )

    section = await _create_section(
        client,
        assessment_id=assessment["id"],
        user=teacher_user,
        auth_headers=auth_headers,
    )

    parent = await _create_question(
        client,
        assessment_id=assessment["id"],
        user=teacher_user,
        auth_headers=auth_headers,
        question_number="1",
        maximum_mark=Decimal("0.00"),
        section_id=section["id"],
        title="Question 1",
        prompt="Main question.",
        order=1,
        is_markable=False,
    )

    child = await _create_question(
        client,
        assessment_id=assessment["id"],
        user=teacher_user,
        auth_headers=auth_headers,
        question_number="1(a)",
        maximum_mark=Decimal("5.00"),
        section_id=section["id"],
        parent_question_id=parent["id"],
        title="Part A",
        prompt="Calculate the acceleration.",
        order=2,
        is_markable=True,
    )

    response = await client.get(
        f"/api/v1/assessments/{assessment['id']}/questions",
        headers=auth_headers(
            teacher_user,
        ),
    )

    assert response.status_code == 200, response.text

    data = response.json()

    assert len(data) == 2

    child_data = next(question for question in data if question["id"] == child["id"])

    assert child_data["section_id"] == section["id"]
    assert child_data["parent_question_id"] == parent["id"]
    assert child_data["question_number"] == "1(a)"
    assert Decimal(
        child_data["maximum_mark"],
    ) == Decimal("5.00")
    assert child_data["is_markable"] is True


@pytest.mark.asyncio
async def test_question_number_must_be_unique_within_assessment(
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

    assessment = await _create_assessment(
        client,
        course_id=course.id,
        user=teacher_user,
        auth_headers=auth_headers,
    )

    await _create_question(
        client,
        assessment_id=assessment["id"],
        user=teacher_user,
        auth_headers=auth_headers,
        question_number="1",
    )

    response = await client.post(
        f"/api/v1/assessments/{assessment['id']}/questions",
        json={
            "question_number": "1",
            "maximum_mark": "5.00",
            "order": 2,
            "is_markable": True,
        },
        headers=auth_headers(
            teacher_user,
        ),
    )

    assert response.status_code == 409


@pytest.mark.asyncio
async def test_question_rejects_section_from_another_assessment(
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

    first_assessment = await _create_assessment(
        client,
        course_id=course.id,
        user=teacher_user,
        auth_headers=auth_headers,
        title="First Assessment",
    )

    second_assessment = await _create_assessment(
        client,
        course_id=course.id,
        user=teacher_user,
        auth_headers=auth_headers,
        title="Second Assessment",
    )

    foreign_section = await _create_section(
        client,
        assessment_id=second_assessment["id"],
        user=teacher_user,
        auth_headers=auth_headers,
    )

    response = await client.post(
        f"/api/v1/assessments/{first_assessment['id']}/questions",
        json={
            "section_id": foreign_section["id"],
            "question_number": "1",
            "maximum_mark": "5.00",
            "order": 1,
            "is_markable": True,
        },
        headers=auth_headers(
            teacher_user,
        ),
    )

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_question_rejects_parent_from_another_assessment(
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

    first_assessment = await _create_assessment(
        client,
        course_id=course.id,
        user=teacher_user,
        auth_headers=auth_headers,
        title="First Parent Assessment",
    )

    second_assessment = await _create_assessment(
        client,
        course_id=course.id,
        user=teacher_user,
        auth_headers=auth_headers,
        title="Second Parent Assessment",
    )

    foreign_parent = await _create_question(
        client,
        assessment_id=second_assessment["id"],
        user=teacher_user,
        auth_headers=auth_headers,
        question_number="1",
    )

    response = await client.post(
        f"/api/v1/assessments/{first_assessment['id']}/questions",
        json={
            "parent_question_id": foreign_parent["id"],
            "question_number": "1",
            "maximum_mark": "5.00",
            "order": 1,
            "is_markable": True,
        },
        headers=auth_headers(
            teacher_user,
        ),
    )

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_question_patch_can_clear_nullable_fields_and_relationships(
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

    assessment = await _create_assessment(
        client,
        course_id=course.id,
        user=teacher_user,
        auth_headers=auth_headers,
    )

    section = await _create_section(
        client,
        assessment_id=assessment["id"],
        user=teacher_user,
        auth_headers=auth_headers,
    )

    parent = await _create_question(
        client,
        assessment_id=assessment["id"],
        user=teacher_user,
        auth_headers=auth_headers,
        question_number="1",
        maximum_mark=Decimal("0.00"),
        order=1,
        is_markable=False,
    )

    child = await _create_question(
        client,
        assessment_id=assessment["id"],
        user=teacher_user,
        auth_headers=auth_headers,
        question_number="1(a)",
        maximum_mark=Decimal("5.00"),
        section_id=section["id"],
        parent_question_id=parent["id"],
        title="Title to clear",
        prompt="Prompt to clear",
        order=2,
    )

    response = await client.patch(
        (f"/api/v1/assessments/{assessment['id']}" f"/questions/{child['id']}"),
        json={
            "section_id": None,
            "parent_question_id": None,
            "title": None,
            "prompt": None,
        },
        headers=auth_headers(
            teacher_user,
        ),
    )

    assert response.status_code == 200, response.text

    data = response.json()

    assert data["section_id"] is None
    assert data["parent_question_id"] is None
    assert data["title"] is None
    assert data["prompt"] is None

    assert data["question_number"] == "1(a)"
    assert Decimal(
        data["maximum_mark"],
    ) == Decimal("5.00")


@pytest.mark.asyncio
async def test_question_parent_cycle_is_rejected(
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

    assessment = await _create_assessment(
        client,
        course_id=course.id,
        user=teacher_user,
        auth_headers=auth_headers,
    )

    parent = await _create_question(
        client,
        assessment_id=assessment["id"],
        user=teacher_user,
        auth_headers=auth_headers,
        question_number="1",
        maximum_mark=Decimal("0.00"),
        order=1,
        is_markable=False,
    )

    child = await _create_question(
        client,
        assessment_id=assessment["id"],
        user=teacher_user,
        auth_headers=auth_headers,
        question_number="1(a)",
        maximum_mark=Decimal("5.00"),
        parent_question_id=parent["id"],
        order=2,
    )

    response = await client.patch(
        (f"/api/v1/assessments/{assessment['id']}" f"/questions/{parent['id']}"),
        json={
            "parent_question_id": child["id"],
        },
        headers=auth_headers(
            teacher_user,
        ),
    )

    assert response.status_code == 409


@pytest.mark.asyncio
async def test_deleting_section_leaves_questions_unsectioned(
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

    assessment = await _create_assessment(
        client,
        course_id=course.id,
        user=teacher_user,
        auth_headers=auth_headers,
    )

    section = await _create_section(
        client,
        assessment_id=assessment["id"],
        user=teacher_user,
        auth_headers=auth_headers,
    )

    question = await _create_question(
        client,
        assessment_id=assessment["id"],
        user=teacher_user,
        auth_headers=auth_headers,
        section_id=section["id"],
    )

    response = await client.delete(
        (f"/api/v1/assessments/{assessment['id']}" f"/sections/{section['id']}"),
        headers=auth_headers(
            teacher_user,
        ),
    )

    assert response.status_code == 200, response.text

    assessment_data = response.json()

    assert assessment_data["sections"] == []

    question_data = next(
        item for item in assessment_data["questions"] if item["id"] == question["id"]
    )

    assert question_data["section_id"] is None


@pytest.mark.asyncio
async def test_published_assessment_structure_cannot_be_modified(
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

    assessment = await _create_assessment(
        client,
        course_id=course.id,
        user=teacher_user,
        auth_headers=auth_headers,
    )

    question = await _create_question(
        client,
        assessment_id=assessment["id"],
        user=teacher_user,
        auth_headers=auth_headers,
        question_number="1",
        maximum_mark=Decimal("10.00"),
    )

    publish_response = await client.post(
        f"/api/v1/assessments/{assessment['id']}/publish",
        headers=auth_headers(
            teacher_user,
        ),
    )

    assert publish_response.status_code == 200, publish_response.text
    assert publish_response.json()["status"] == AssessmentStatus.PUBLISHED.value

    section_response = await client.post(
        f"/api/v1/assessments/{assessment['id']}/sections",
        json={
            "title": "Late Section",
            "order": 1,
        },
        headers=auth_headers(
            teacher_user,
        ),
    )

    assert section_response.status_code == 409

    question_response = await client.patch(
        (f"/api/v1/assessments/{assessment['id']}" f"/questions/{question['id']}"),
        json={
            "maximum_mark": "20.00",
        },
        headers=auth_headers(
            teacher_user,
        ),
    )

    assert question_response.status_code == 409

    delete_response = await client.delete(
        (f"/api/v1/assessments/{assessment['id']}" f"/questions/{question['id']}"),
        headers=auth_headers(
            teacher_user,
        ),
    )

    assert delete_response.status_code == 409


@pytest.mark.asyncio
async def test_teacher_cannot_manage_other_teachers_assessment_structure(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
):
    other_teacher = await create_test_user(
        db_session,
        email="assessment.structure.owner@example.com",
        roles=[
            UserRole.TEACHER,
        ],
        school_id=teacher_user.school_id,
    )

    course = await _create_course(
        db_session,
        teacher_id=other_teacher.id,
        school_id=other_teacher.school_id,
        title="Other Teacher Structure Course",
    )

    assessment = await _create_assessment(
        client,
        course_id=course.id,
        user=other_teacher,
        auth_headers=auth_headers,
        title="Other Teacher Assessment",
    )

    response = await client.post(
        f"/api/v1/assessments/{assessment['id']}/sections",
        json={
            "title": "Forbidden Section",
            "order": 1,
        },
        headers=auth_headers(
            teacher_user,
        ),
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_deleting_parent_question_removes_child_questions(
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

    assessment = await _create_assessment(
        client,
        course_id=course.id,
        user=teacher_user,
        auth_headers=auth_headers,
    )

    parent = await _create_question(
        client,
        assessment_id=assessment["id"],
        user=teacher_user,
        auth_headers=auth_headers,
        question_number="1",
        maximum_mark=Decimal("0.00"),
        order=1,
        is_markable=False,
    )

    child = await _create_question(
        client,
        assessment_id=assessment["id"],
        user=teacher_user,
        auth_headers=auth_headers,
        question_number="1(a)",
        maximum_mark=Decimal("5.00"),
        parent_question_id=parent["id"],
        order=2,
    )

    response = await client.delete(
        (f"/api/v1/assessments/{assessment['id']}" f"/questions/{parent['id']}"),
        headers=auth_headers(
            teacher_user,
        ),
    )

    assert response.status_code == 200, response.text

    data = response.json()

    remaining_ids = {question["id"] for question in data["questions"]}

    assert parent["id"] not in remaining_ids
    assert child["id"] not in remaining_ids
