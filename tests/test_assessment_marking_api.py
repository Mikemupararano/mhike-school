from __future__ import annotations

from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.assessment import Assessment, AssessmentStatus
from app.models.assessment_candidate import (
    AssessmentCandidate,
    AssessmentCandidateStatus,
    AssessmentScript,
    AssessmentScriptStatus,
)
from app.models.assessment_question import AssessmentQuestion
from app.models.assessment_response import (
    AssessmentResponseStatus,
    MarkingDecision,
    MarkingDecisionStatus,
)
from app.models.course import Course
from app.models.mark_scheme import (
    MarkScheme,
    MarkSchemeItem,
    MarkSchemeItemType,
)
from app.models.user import UserRole
from app.services.assessment_marking_palette_service import (
    ensure_default_marking_palette,
)
from tests.conftest import create_test_user

# ---------------------------------------------------------------------------
# Test-data helpers
# ---------------------------------------------------------------------------


async def _create_course(
    db_session: AsyncSession,
    *,
    teacher_id: int,
    school_id: int,
    title: str = "Assessment Marking API Course",
) -> Course:
    """
    Create and persist a teacher-owned course.
    """

    course = Course(
        title=title,
        description="Course used by assessment marking API tests.",
        teacher_id=teacher_id,
        school_id=school_id,
        published=True,
    )

    db_session.add(course)

    await db_session.commit()
    await db_session.refresh(course)

    return course


async def _create_assessment(
    db_session: AsyncSession,
    *,
    teacher_id: int,
    school_id: int,
    course_id: int,
    title: str = "Assessment Marking API Assessment",
) -> Assessment:
    """
    Create and persist a published assessment.
    """

    assessment = Assessment(
        school_id=school_id,
        course_id=course_id,
        created_by_id=teacher_id,
        title=title,
        description="Assessment marking API test.",
        assessment_type="test",
        academic_year="2026/27",
        term="Autumn",
        status=AssessmentStatus.PUBLISHED,
        anonymous_marking=False,
    )

    db_session.add(assessment)

    await db_session.commit()
    await db_session.refresh(assessment)

    return assessment


async def _create_question(
    db_session: AsyncSession,
    *,
    assessment_id: int,
    question_number: str = "1",
    maximum_mark: Decimal = Decimal("5.00"),
    order: int = 1,
    is_markable: bool = True,
) -> AssessmentQuestion:
    """
    Create and persist an assessment question.
    """

    question = AssessmentQuestion(
        assessment_id=assessment_id,
        question_number=question_number,
        prompt=f"Question {question_number}",
        maximum_mark=maximum_mark,
        order=order,
        is_markable=is_markable,
    )

    db_session.add(question)

    await db_session.commit()
    await db_session.refresh(question)

    return question


async def _create_mark_scheme(
    db_session: AsyncSession,
    *,
    question_id: int,
) -> tuple[MarkScheme, MarkSchemeItem, MarkSchemeItem]:
    """
    Create a mark scheme with two one-mark criteria.
    """

    mark_scheme = MarkScheme(
        question_id=question_id,
        title="API Test Mark Scheme",
        general_guidance="Award marks according to the criteria.",
        allow_alternative_answers=True,
    )

    db_session.add(mark_scheme)
    await db_session.flush()

    first_item = MarkSchemeItem(
        mark_scheme_id=mark_scheme.id,
        code="M1",
        item_type=MarkSchemeItemType.METHOD,
        description="Uses the correct method.",
        marks=Decimal("1.00"),
        order=1,
        is_optional=False,
    )

    second_item = MarkSchemeItem(
        mark_scheme_id=mark_scheme.id,
        code="A1",
        item_type=MarkSchemeItemType.ACCURACY,
        description="Obtains the correct answer.",
        marks=Decimal("1.00"),
        order=2,
        is_optional=False,
    )

    db_session.add_all(
        [
            first_item,
            second_item,
        ]
    )

    await db_session.commit()
    await db_session.refresh(mark_scheme)
    await db_session.refresh(first_item)
    await db_session.refresh(second_item)

    return mark_scheme, first_item, second_item


async def _create_candidate_and_script(
    db_session: AsyncSession,
    *,
    assessment_id: int,
    student_id: int,
) -> tuple[AssessmentCandidate, AssessmentScript]:
    """
    Create a submitted candidate allocation and submitted script.
    """

    candidate = AssessmentCandidate(
        assessment_id=assessment_id,
        student_id=student_id,
        status=AssessmentCandidateStatus.SUBMITTED,
        candidate_number="MARK-API-001",
    )

    db_session.add(candidate)
    await db_session.flush()

    script = AssessmentScript(
        candidate_id=candidate.id,
        version=1,
        status=AssessmentScriptStatus.SUBMITTED,
        source_type="pdf_upload",
        source_filename="candidate-script.pdf",
        storage_key="assessment-marking/candidate-script.pdf",
        mime_type="application/pdf",
        checksum="marking-api-checksum",
    )

    db_session.add(script)

    await db_session.commit()
    await db_session.refresh(candidate)
    await db_session.refresh(script)

    return candidate, script


async def _build_marking_context(
    db_session: AsyncSession,
    teacher_user,
    *,
    maximum_mark: Decimal = Decimal("5.00"),
    is_markable: bool = True,
):
    """
    Build a complete marking context for one teacher.
    """

    course = await _create_course(
        db_session,
        teacher_id=teacher_user.id,
        school_id=teacher_user.school_id,
    )

    assessment = await _create_assessment(
        db_session,
        teacher_id=teacher_user.id,
        school_id=teacher_user.school_id,
        course_id=course.id,
    )

    question = await _create_question(
        db_session,
        assessment_id=assessment.id,
        maximum_mark=maximum_mark,
        is_markable=is_markable,
    )

    student = await create_test_user(
        db_session,
        email=f"marking.api.student.{assessment.id}@example.com",
        roles=[UserRole.STUDENT],
        school_id=teacher_user.school_id,
    )

    candidate, script = await _create_candidate_and_script(
        db_session,
        assessment_id=assessment.id,
        student_id=student.id,
    )

    return {
        "course": course,
        "assessment": assessment,
        "question": question,
        "student": student,
        "candidate": candidate,
        "script": script,
    }


async def _create_response_via_api(
    client: AsyncClient,
    *,
    script_id: int,
    question_id: int,
    user,
    auth_headers,
    response_text: str | None = "Candidate answer",
) -> dict:
    """
    Create one assessment response through the public API.
    """

    response = await client.post(
        f"/api/v1/assessment-marking/scripts/{script_id}/responses",
        json={
            "question_id": question_id,
            "response_text": response_text,
            "response_data": None,
            "source_reference": None,
        },
        headers=auth_headers(user),
    )

    assert response.status_code == 201, response.text

    return response.json()


async def _submit_response_via_api(
    client: AsyncClient,
    *,
    response_id: int,
    user,
    auth_headers,
) -> dict:
    """
    Submit one assessment response.
    """

    response = await client.post(
        f"/api/v1/assessment-marking/responses/{response_id}/submit",
        headers=auth_headers(user),
    )

    assert response.status_code == 200, response.text

    return response.json()


async def _create_decision_via_api(
    client: AsyncClient,
    *,
    response_id: int,
    user,
    auth_headers,
) -> dict:
    """
    Create a marking decision through the public API.
    """

    response = await client.post(
        f"/api/v1/assessment-marking/responses/{response_id}/decision",
        json={
            "marker_comment": "Initial API marking.",
        },
        headers=auth_headers(user),
    )

    assert response.status_code == 201, response.text

    return response.json()


# ---------------------------------------------------------------------------
# Response creation and retrieval
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_teacher_can_create_assessment_response(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
):
    context = await _build_marking_context(
        db_session,
        teacher_user,
    )

    response = await client.post(
        f"/api/v1/assessment-marking/scripts/{context['script'].id}/responses",
        json={
            "question_id": context["question"].id,
            "response_text": "v = u + at",
            "response_data": '{"method": "kinematics"}',
            "source_reference": "page-1",
        },
        headers=auth_headers(teacher_user),
    )

    assert response.status_code == 201, response.text

    data = response.json()

    assert data["id"] is not None
    assert data["script_id"] == context["script"].id
    assert data["question_id"] == context["question"].id
    assert data["status"] == AssessmentResponseStatus.IN_PROGRESS.value
    assert data["response_text"] == "v = u + at"
    assert data["response_data"] == '{"method": "kinematics"}'
    assert data["source_reference"] == "page-1"
    assert data["marking_decision"] is None


@pytest.mark.asyncio
async def test_empty_response_is_not_started(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
):
    context = await _build_marking_context(
        db_session,
        teacher_user,
    )

    response = await client.post(
        f"/api/v1/assessment-marking/scripts/{context['script'].id}/responses",
        json={
            "question_id": context["question"].id,
        },
        headers=auth_headers(teacher_user),
    )

    assert response.status_code == 201, response.text

    assert response.json()["status"] == AssessmentResponseStatus.NOT_STARTED.value


@pytest.mark.asyncio
async def test_duplicate_response_is_rejected(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
):
    context = await _build_marking_context(
        db_session,
        teacher_user,
    )

    await _create_response_via_api(
        client,
        script_id=context["script"].id,
        question_id=context["question"].id,
        user=teacher_user,
        auth_headers=auth_headers,
    )

    response = await client.post(
        f"/api/v1/assessment-marking/scripts/{context['script'].id}/responses",
        json={
            "question_id": context["question"].id,
            "response_text": "Duplicate answer",
        },
        headers=auth_headers(teacher_user),
    )

    assert response.status_code == 409


@pytest.mark.asyncio
async def test_response_rejects_question_from_other_assessment(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
):
    context = await _build_marking_context(
        db_session,
        teacher_user,
    )

    other_course = await _create_course(
        db_session,
        teacher_id=teacher_user.id,
        school_id=teacher_user.school_id,
        title="Other Marking API Course",
    )

    other_assessment = await _create_assessment(
        db_session,
        teacher_id=teacher_user.id,
        school_id=teacher_user.school_id,
        course_id=other_course.id,
        title="Other Marking API Assessment",
    )

    other_question = await _create_question(
        db_session,
        assessment_id=other_assessment.id,
        question_number="2",
    )

    response = await client.post(
        f"/api/v1/assessment-marking/scripts/{context['script'].id}/responses",
        json={
            "question_id": other_question.id,
            "response_text": "Wrong assessment.",
        },
        headers=auth_headers(teacher_user),
    )

    assert response.status_code == 409


@pytest.mark.asyncio
async def test_teacher_can_get_assessment_response(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
):
    context = await _build_marking_context(
        db_session,
        teacher_user,
    )

    created = await _create_response_via_api(
        client,
        script_id=context["script"].id,
        question_id=context["question"].id,
        user=teacher_user,
        auth_headers=auth_headers,
    )

    response = await client.get(
        f"/api/v1/assessment-marking/responses/{created['id']}",
        headers=auth_headers(teacher_user),
    )

    assert response.status_code == 200, response.text
    assert response.json()["id"] == created["id"]


@pytest.mark.asyncio
async def test_teacher_can_list_script_responses(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
):
    context = await _build_marking_context(
        db_session,
        teacher_user,
    )

    created = await _create_response_via_api(
        client,
        script_id=context["script"].id,
        question_id=context["question"].id,
        user=teacher_user,
        auth_headers=auth_headers,
    )

    response = await client.get(
        f"/api/v1/assessment-marking/scripts/{context['script'].id}/responses",
        headers=auth_headers(teacher_user),
    )

    assert response.status_code == 200, response.text

    data = response.json()

    assert len(data) == 1
    assert data[0]["id"] == created["id"]


@pytest.mark.asyncio
async def test_teacher_can_update_response(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
):
    context = await _build_marking_context(
        db_session,
        teacher_user,
    )

    created = await _create_response_via_api(
        client,
        script_id=context["script"].id,
        question_id=context["question"].id,
        user=teacher_user,
        auth_headers=auth_headers,
        response_text=None,
    )

    response = await client.patch(
        f"/api/v1/assessment-marking/responses/{created['id']}",
        json={
            "response_text": "Updated answer",
            "response_data": '{"value": 42}',
            "source_reference": "page-2",
        },
        headers=auth_headers(teacher_user),
    )

    assert response.status_code == 200, response.text

    data = response.json()

    assert data["status"] == AssessmentResponseStatus.IN_PROGRESS.value
    assert data["response_text"] == "Updated answer"
    assert data["response_data"] == '{"value": 42}'
    assert data["source_reference"] == "page-2"


# ---------------------------------------------------------------------------
# Response lifecycle
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_response_can_be_submitted_via_api(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
):
    context = await _build_marking_context(
        db_session,
        teacher_user,
    )

    created = await _create_response_via_api(
        client,
        script_id=context["script"].id,
        question_id=context["question"].id,
        user=teacher_user,
        auth_headers=auth_headers,
    )

    response = await client.post(
        f"/api/v1/assessment-marking/responses/{created['id']}/submit",
        headers=auth_headers(teacher_user),
    )

    assert response.status_code == 200, response.text

    data = response.json()

    assert data["status"] == AssessmentResponseStatus.SUBMITTED.value
    assert data["submitted_at"] is not None


@pytest.mark.asyncio
async def test_response_can_be_voided_via_api(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
):
    context = await _build_marking_context(
        db_session,
        teacher_user,
    )

    created = await _create_response_via_api(
        client,
        script_id=context["script"].id,
        question_id=context["question"].id,
        user=teacher_user,
        auth_headers=auth_headers,
    )

    response = await client.post(
        f"/api/v1/assessment-marking/responses/{created['id']}/void",
        headers=auth_headers(teacher_user),
    )

    assert response.status_code == 200, response.text

    assert response.json()["status"] == AssessmentResponseStatus.VOID.value


@pytest.mark.asyncio
async def test_generic_response_status_endpoint_rejects_invalid_transition(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
):
    context = await _build_marking_context(
        db_session,
        teacher_user,
    )

    created = await _create_response_via_api(
        client,
        script_id=context["script"].id,
        question_id=context["question"].id,
        user=teacher_user,
        auth_headers=auth_headers,
    )

    void_response = await client.post(
        f"/api/v1/assessment-marking/responses/{created['id']}/void",
        headers=auth_headers(teacher_user),
    )

    assert void_response.status_code == 200, void_response.text

    response = await client.patch(
        f"/api/v1/assessment-marking/responses/{created['id']}/status",
        json={
            "status": AssessmentResponseStatus.SUBMITTED.value,
        },
        headers=auth_headers(teacher_user),
    )

    assert response.status_code == 409


@pytest.mark.asyncio
async def test_untouched_response_can_be_deleted_via_api(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
):
    context = await _build_marking_context(
        db_session,
        teacher_user,
    )

    created = await _create_response_via_api(
        client,
        script_id=context["script"].id,
        question_id=context["question"].id,
        user=teacher_user,
        auth_headers=auth_headers,
        response_text=None,
    )

    response = await client.delete(
        f"/api/v1/assessment-marking/responses/{created['id']}",
        headers=auth_headers(teacher_user),
    )

    assert response.status_code == 204


@pytest.mark.asyncio
async def test_response_with_content_cannot_be_deleted(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
):
    context = await _build_marking_context(
        db_session,
        teacher_user,
    )

    created = await _create_response_via_api(
        client,
        script_id=context["script"].id,
        question_id=context["question"].id,
        user=teacher_user,
        auth_headers=auth_headers,
    )

    response = await client.delete(
        f"/api/v1/assessment-marking/responses/{created['id']}",
        headers=auth_headers(teacher_user),
    )

    assert response.status_code == 409


# ---------------------------------------------------------------------------
# Marking decision creation and retrieval
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_teacher_can_create_marking_decision(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
):
    context = await _build_marking_context(
        db_session,
        teacher_user,
    )

    response_data = await _create_response_via_api(
        client,
        script_id=context["script"].id,
        question_id=context["question"].id,
        user=teacher_user,
        auth_headers=auth_headers,
    )

    await _submit_response_via_api(
        client,
        response_id=response_data["id"],
        user=teacher_user,
        auth_headers=auth_headers,
    )

    response = await client.post(
        f"/api/v1/assessment-marking/responses/{response_data['id']}/decision",
        json={
            "marker_comment": "Initial assessment.",
        },
        headers=auth_headers(teacher_user),
    )

    assert response.status_code == 201, response.text

    data = response.json()

    assert data["id"] is not None
    assert data["response_id"] == response_data["id"]
    assert data["marker_id"] == teacher_user.id
    assert data["status"] == MarkingDecisionStatus.UNMARKED.value
    assert data["mark_awarded"] is None
    assert data["marker_comment"] == "Initial assessment."
    assert data["item_awards"] == []


@pytest.mark.asyncio
async def test_unsubmitted_response_cannot_receive_marking_decision(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
):
    context = await _build_marking_context(
        db_session,
        teacher_user,
    )

    response_data = await _create_response_via_api(
        client,
        script_id=context["script"].id,
        question_id=context["question"].id,
        user=teacher_user,
        auth_headers=auth_headers,
    )

    response = await client.post(
        f"/api/v1/assessment-marking/responses/{response_data['id']}/decision",
        json={},
        headers=auth_headers(teacher_user),
    )

    assert response.status_code == 409


@pytest.mark.asyncio
async def test_duplicate_marking_decision_is_rejected(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
):
    context = await _build_marking_context(
        db_session,
        teacher_user,
    )

    response_data = await _create_response_via_api(
        client,
        script_id=context["script"].id,
        question_id=context["question"].id,
        user=teacher_user,
        auth_headers=auth_headers,
    )

    await _submit_response_via_api(
        client,
        response_id=response_data["id"],
        user=teacher_user,
        auth_headers=auth_headers,
    )

    await _create_decision_via_api(
        client,
        response_id=response_data["id"],
        user=teacher_user,
        auth_headers=auth_headers,
    )

    response = await client.post(
        f"/api/v1/assessment-marking/responses/{response_data['id']}/decision",
        json={},
        headers=auth_headers(teacher_user),
    )

    assert response.status_code == 409


@pytest.mark.asyncio
async def test_teacher_can_get_marking_decision(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
):
    context = await _build_marking_context(
        db_session,
        teacher_user,
    )

    response_data = await _create_response_via_api(
        client,
        script_id=context["script"].id,
        question_id=context["question"].id,
        user=teacher_user,
        auth_headers=auth_headers,
    )

    await _submit_response_via_api(
        client,
        response_id=response_data["id"],
        user=teacher_user,
        auth_headers=auth_headers,
    )

    decision = await _create_decision_via_api(
        client,
        response_id=response_data["id"],
        user=teacher_user,
        auth_headers=auth_headers,
    )

    response = await client.get(
        f"/api/v1/assessment-marking/decisions/{decision['id']}",
        headers=auth_headers(teacher_user),
    )

    assert response.status_code == 200, response.text
    assert response.json()["id"] == decision["id"]


# ---------------------------------------------------------------------------
# Question-level marking
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_teacher_can_update_question_level_mark(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
):
    context = await _build_marking_context(
        db_session,
        teacher_user,
        maximum_mark=Decimal("5.00"),
    )

    response_data = await _create_response_via_api(
        client,
        script_id=context["script"].id,
        question_id=context["question"].id,
        user=teacher_user,
        auth_headers=auth_headers,
    )

    await _submit_response_via_api(
        client,
        response_id=response_data["id"],
        user=teacher_user,
        auth_headers=auth_headers,
    )

    decision = await _create_decision_via_api(
        client,
        response_id=response_data["id"],
        user=teacher_user,
        auth_headers=auth_headers,
    )

    response = await client.patch(
        f"/api/v1/assessment-marking/decisions/{decision['id']}",
        json={
            "mark_awarded": "4.00",
            "marker_comment": "Good answer.",
        },
        headers=auth_headers(teacher_user),
    )

    assert response.status_code == 200, response.text

    data = response.json()

    assert Decimal(data["mark_awarded"]) == Decimal("4.00")
    assert data["marker_comment"] == "Good answer."
    assert data["status"] == MarkingDecisionStatus.IN_PROGRESS.value


@pytest.mark.asyncio
async def test_mark_above_question_maximum_is_rejected_by_api(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
):
    context = await _build_marking_context(
        db_session,
        teacher_user,
        maximum_mark=Decimal("5.00"),
    )

    response_data = await _create_response_via_api(
        client,
        script_id=context["script"].id,
        question_id=context["question"].id,
        user=teacher_user,
        auth_headers=auth_headers,
    )

    await _submit_response_via_api(
        client,
        response_id=response_data["id"],
        user=teacher_user,
        auth_headers=auth_headers,
    )

    decision = await _create_decision_via_api(
        client,
        response_id=response_data["id"],
        user=teacher_user,
        auth_headers=auth_headers,
    )

    response = await client.patch(
        f"/api/v1/assessment-marking/decisions/{decision['id']}",
        json={
            "mark_awarded": "6.00",
        },
        headers=auth_headers(teacher_user),
    )

    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Criterion-level awards
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_teacher_can_award_mark_scheme_item_via_api(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
):
    context = await _build_marking_context(
        db_session,
        teacher_user,
    )

    _, first_item, _ = await _create_mark_scheme(
        db_session,
        question_id=context["question"].id,
    )

    response_data = await _create_response_via_api(
        client,
        script_id=context["script"].id,
        question_id=context["question"].id,
        user=teacher_user,
        auth_headers=auth_headers,
    )

    await _submit_response_via_api(
        client,
        response_id=response_data["id"],
        user=teacher_user,
        auth_headers=auth_headers,
    )

    decision = await _create_decision_via_api(
        client,
        response_id=response_data["id"],
        user=teacher_user,
        auth_headers=auth_headers,
    )

    response = await client.put(
        f"/api/v1/assessment-marking/decisions/{decision['id']}/awards",
        json={
            "mark_scheme_item_id": first_item.id,
            "marks_awarded": "1.00",
            "marker_note": "Method awarded.",
        },
        headers=auth_headers(teacher_user),
    )

    assert response.status_code == 200, response.text

    data = response.json()

    assert data["marking_decision_id"] == decision["id"]
    assert data["mark_scheme_item_id"] == first_item.id
    assert Decimal(data["marks_awarded"]) == Decimal("1.00")
    assert data["awarded_by_id"] == teacher_user.id
    assert data["marker_note"] == "Method awarded."
    assert data["mark_scheme_item"]["id"] == first_item.id


@pytest.mark.asyncio
async def test_existing_criterion_award_is_updated_via_api(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
):
    context = await _build_marking_context(
        db_session,
        teacher_user,
    )

    _, first_item, _ = await _create_mark_scheme(
        db_session,
        question_id=context["question"].id,
    )

    response_data = await _create_response_via_api(
        client,
        script_id=context["script"].id,
        question_id=context["question"].id,
        user=teacher_user,
        auth_headers=auth_headers,
    )

    await _submit_response_via_api(
        client,
        response_id=response_data["id"],
        user=teacher_user,
        auth_headers=auth_headers,
    )

    decision = await _create_decision_via_api(
        client,
        response_id=response_data["id"],
        user=teacher_user,
        auth_headers=auth_headers,
    )

    first_response = await client.put(
        f"/api/v1/assessment-marking/decisions/{decision['id']}/awards",
        json={
            "mark_scheme_item_id": first_item.id,
            "marks_awarded": "0.00",
        },
        headers=auth_headers(teacher_user),
    )

    assert first_response.status_code == 200, first_response.text

    updated_response = await client.put(
        f"/api/v1/assessment-marking/decisions/{decision['id']}/awards",
        json={
            "mark_scheme_item_id": first_item.id,
            "marks_awarded": "1.00",
            "marker_note": "Awarded after review.",
        },
        headers=auth_headers(teacher_user),
    )

    assert updated_response.status_code == 200, updated_response.text

    first_data = first_response.json()
    updated_data = updated_response.json()

    assert updated_data["id"] == first_data["id"]
    assert Decimal(updated_data["marks_awarded"]) == Decimal("1.00")
    assert updated_data["marker_note"] == "Awarded after review."


@pytest.mark.asyncio
async def test_criterion_award_above_item_maximum_is_rejected(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
):
    context = await _build_marking_context(
        db_session,
        teacher_user,
    )

    _, first_item, _ = await _create_mark_scheme(
        db_session,
        question_id=context["question"].id,
    )

    response_data = await _create_response_via_api(
        client,
        script_id=context["script"].id,
        question_id=context["question"].id,
        user=teacher_user,
        auth_headers=auth_headers,
    )

    await _submit_response_via_api(
        client,
        response_id=response_data["id"],
        user=teacher_user,
        auth_headers=auth_headers,
    )

    decision = await _create_decision_via_api(
        client,
        response_id=response_data["id"],
        user=teacher_user,
        auth_headers=auth_headers,
    )

    response = await client.put(
        f"/api/v1/assessment-marking/decisions/{decision['id']}/awards",
        json={
            "mark_scheme_item_id": first_item.id,
            "marks_awarded": "2.00",
        },
        headers=auth_headers(teacher_user),
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_criterion_from_other_question_is_rejected(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
):
    context = await _build_marking_context(
        db_session,
        teacher_user,
    )

    other_question = await _create_question(
        db_session,
        assessment_id=context["assessment"].id,
        question_number="2",
        order=2,
    )

    _, other_item, _ = await _create_mark_scheme(
        db_session,
        question_id=other_question.id,
    )

    response_data = await _create_response_via_api(
        client,
        script_id=context["script"].id,
        question_id=context["question"].id,
        user=teacher_user,
        auth_headers=auth_headers,
    )

    await _submit_response_via_api(
        client,
        response_id=response_data["id"],
        user=teacher_user,
        auth_headers=auth_headers,
    )

    decision = await _create_decision_via_api(
        client,
        response_id=response_data["id"],
        user=teacher_user,
        auth_headers=auth_headers,
    )

    response = await client.put(
        f"/api/v1/assessment-marking/decisions/{decision['id']}/awards",
        json={
            "mark_scheme_item_id": other_item.id,
            "marks_awarded": "1.00",
        },
        headers=auth_headers(teacher_user),
    )

    assert response.status_code == 409


@pytest.mark.asyncio
async def test_criterion_award_can_be_deleted_via_api(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
):
    context = await _build_marking_context(
        db_session,
        teacher_user,
    )

    _, first_item, _ = await _create_mark_scheme(
        db_session,
        question_id=context["question"].id,
    )

    response_data = await _create_response_via_api(
        client,
        script_id=context["script"].id,
        question_id=context["question"].id,
        user=teacher_user,
        auth_headers=auth_headers,
    )

    await _submit_response_via_api(
        client,
        response_id=response_data["id"],
        user=teacher_user,
        auth_headers=auth_headers,
    )

    decision = await _create_decision_via_api(
        client,
        response_id=response_data["id"],
        user=teacher_user,
        auth_headers=auth_headers,
    )

    award_response = await client.put(
        f"/api/v1/assessment-marking/decisions/{decision['id']}/awards",
        json={
            "mark_scheme_item_id": first_item.id,
            "marks_awarded": "1.00",
        },
        headers=auth_headers(teacher_user),
    )

    assert award_response.status_code == 200, award_response.text

    award = award_response.json()

    delete_response = await client.delete(
        f"/api/v1/assessment-marking/awards/{award['id']}",
        headers=auth_headers(teacher_user),
    )

    assert delete_response.status_code == 204


# ---------------------------------------------------------------------------
# Marking lifecycle
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_marking_can_progress_to_marked_via_api(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
):
    context = await _build_marking_context(
        db_session,
        teacher_user,
    )

    response_data = await _create_response_via_api(
        client,
        script_id=context["script"].id,
        question_id=context["question"].id,
        user=teacher_user,
        auth_headers=auth_headers,
    )

    await _submit_response_via_api(
        client,
        response_id=response_data["id"],
        user=teacher_user,
        auth_headers=auth_headers,
    )

    decision = await _create_decision_via_api(
        client,
        response_id=response_data["id"],
        user=teacher_user,
        auth_headers=auth_headers,
    )

    start_response = await client.post(
        f"/api/v1/assessment-marking/decisions/{decision['id']}/start",
        headers=auth_headers(teacher_user),
    )

    assert start_response.status_code == 200, start_response.text
    assert start_response.json()["status"] == MarkingDecisionStatus.IN_PROGRESS.value

    mark_response = await client.patch(
        f"/api/v1/assessment-marking/decisions/{decision['id']}",
        json={
            "mark_awarded": "3.00",
            "marker_comment": "Marked.",
        },
        headers=auth_headers(teacher_user),
    )

    assert mark_response.status_code == 200, mark_response.text

    complete_response = await client.post(
        f"/api/v1/assessment-marking/decisions/{decision['id']}/complete",
        headers=auth_headers(teacher_user),
    )

    assert complete_response.status_code == 200, complete_response.text

    data = complete_response.json()

    assert data["status"] == MarkingDecisionStatus.MARKED.value
    assert data["marked_at"] is not None


@pytest.mark.asyncio
async def test_marking_cannot_complete_without_question_level_mark(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
):
    context = await _build_marking_context(
        db_session,
        teacher_user,
    )

    response_data = await _create_response_via_api(
        client,
        script_id=context["script"].id,
        question_id=context["question"].id,
        user=teacher_user,
        auth_headers=auth_headers,
    )

    await _submit_response_via_api(
        client,
        response_id=response_data["id"],
        user=teacher_user,
        auth_headers=auth_headers,
    )

    decision = await _create_decision_via_api(
        client,
        response_id=response_data["id"],
        user=teacher_user,
        auth_headers=auth_headers,
    )

    start_response = await client.post(
        f"/api/v1/assessment-marking/decisions/{decision['id']}/start",
        headers=auth_headers(teacher_user),
    )

    assert start_response.status_code == 200, start_response.text

    response = await client.post(
        f"/api/v1/assessment-marking/decisions/{decision['id']}/complete",
        headers=auth_headers(teacher_user),
    )

    assert response.status_code == 409


@pytest.mark.asyncio
async def test_school_admin_can_review_marked_decision_via_api(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
):
    context = await _build_marking_context(
        db_session,
        teacher_user,
    )

    school_admin = await create_test_user(
        db_session,
        email="marking.api.review.admin@example.com",
        roles=[UserRole.SCHOOL_ADMIN],
        school_id=teacher_user.school_id,
    )

    response_data = await _create_response_via_api(
        client,
        script_id=context["script"].id,
        question_id=context["question"].id,
        user=teacher_user,
        auth_headers=auth_headers,
    )

    await _submit_response_via_api(
        client,
        response_id=response_data["id"],
        user=teacher_user,
        auth_headers=auth_headers,
    )

    decision = await _create_decision_via_api(
        client,
        response_id=response_data["id"],
        user=teacher_user,
        auth_headers=auth_headers,
    )

    await client.post(
        f"/api/v1/assessment-marking/decisions/{decision['id']}/start",
        headers=auth_headers(teacher_user),
    )

    await client.patch(
        f"/api/v1/assessment-marking/decisions/{decision['id']}",
        json={
            "mark_awarded": "4.00",
        },
        headers=auth_headers(teacher_user),
    )

    complete_response = await client.post(
        f"/api/v1/assessment-marking/decisions/{decision['id']}/complete",
        headers=auth_headers(teacher_user),
    )

    assert complete_response.status_code == 200, complete_response.text

    response = await client.post(
        f"/api/v1/assessment-marking/decisions/{decision['id']}/review",
        json={
            "moderation_comment": "Checked and agreed.",
        },
        headers=auth_headers(school_admin),
    )

    assert response.status_code == 200, response.text

    data = response.json()

    assert data["status"] == MarkingDecisionStatus.REVIEWED.value
    assert data["reviewed_at"] is not None
    assert data["moderation_comment"] == "Checked and agreed."


@pytest.mark.asyncio
async def test_teacher_cannot_review_marked_decision(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
):
    context = await _build_marking_context(
        db_session,
        teacher_user,
    )

    response_data = await _create_response_via_api(
        client,
        script_id=context["script"].id,
        question_id=context["question"].id,
        user=teacher_user,
        auth_headers=auth_headers,
    )

    await _submit_response_via_api(
        client,
        response_id=response_data["id"],
        user=teacher_user,
        auth_headers=auth_headers,
    )

    decision = await _create_decision_via_api(
        client,
        response_id=response_data["id"],
        user=teacher_user,
        auth_headers=auth_headers,
    )

    await client.post(
        f"/api/v1/assessment-marking/decisions/{decision['id']}/start",
        headers=auth_headers(teacher_user),
    )

    await client.patch(
        f"/api/v1/assessment-marking/decisions/{decision['id']}",
        json={
            "mark_awarded": "4.00",
        },
        headers=auth_headers(teacher_user),
    )

    complete_response = await client.post(
        f"/api/v1/assessment-marking/decisions/{decision['id']}/complete",
        headers=auth_headers(teacher_user),
    )

    assert complete_response.status_code == 200, complete_response.text

    response = await client.post(
        f"/api/v1/assessment-marking/decisions/{decision['id']}/review",
        json={
            "moderation_comment": "Teacher should not moderate.",
        },
        headers=auth_headers(teacher_user),
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_school_admin_can_finalise_marked_decision_via_api(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
):
    context = await _build_marking_context(
        db_session,
        teacher_user,
    )

    school_admin = await create_test_user(
        db_session,
        email="marking.api.finalise.admin@example.com",
        roles=[UserRole.SCHOOL_ADMIN],
        school_id=teacher_user.school_id,
    )

    response_data = await _create_response_via_api(
        client,
        script_id=context["script"].id,
        question_id=context["question"].id,
        user=teacher_user,
        auth_headers=auth_headers,
    )

    await _submit_response_via_api(
        client,
        response_id=response_data["id"],
        user=teacher_user,
        auth_headers=auth_headers,
    )

    decision = await _create_decision_via_api(
        client,
        response_id=response_data["id"],
        user=teacher_user,
        auth_headers=auth_headers,
    )

    await client.post(
        f"/api/v1/assessment-marking/decisions/{decision['id']}/start",
        headers=auth_headers(teacher_user),
    )

    await client.patch(
        f"/api/v1/assessment-marking/decisions/{decision['id']}",
        json={
            "mark_awarded": "4.00",
        },
        headers=auth_headers(teacher_user),
    )

    complete_response = await client.post(
        f"/api/v1/assessment-marking/decisions/{decision['id']}/complete",
        headers=auth_headers(teacher_user),
    )

    assert complete_response.status_code == 200, complete_response.text

    response = await client.post(
        f"/api/v1/assessment-marking/decisions/{decision['id']}/finalise",
        headers=auth_headers(school_admin),
    )

    assert response.status_code == 200, response.text

    data = response.json()

    assert data["status"] == MarkingDecisionStatus.FINALISED.value
    assert data["finalised_at"] is not None


@pytest.mark.asyncio
async def test_finalised_decision_cannot_be_changed_via_api(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
):
    context = await _build_marking_context(
        db_session,
        teacher_user,
    )

    school_admin = await create_test_user(
        db_session,
        email="marking.api.lock.admin@example.com",
        roles=[UserRole.SCHOOL_ADMIN],
        school_id=teacher_user.school_id,
    )

    response_data = await _create_response_via_api(
        client,
        script_id=context["script"].id,
        question_id=context["question"].id,
        user=teacher_user,
        auth_headers=auth_headers,
    )

    await _submit_response_via_api(
        client,
        response_id=response_data["id"],
        user=teacher_user,
        auth_headers=auth_headers,
    )

    decision = await _create_decision_via_api(
        client,
        response_id=response_data["id"],
        user=teacher_user,
        auth_headers=auth_headers,
    )

    await client.post(
        f"/api/v1/assessment-marking/decisions/{decision['id']}/start",
        headers=auth_headers(teacher_user),
    )

    await client.patch(
        f"/api/v1/assessment-marking/decisions/{decision['id']}",
        json={
            "mark_awarded": "4.00",
        },
        headers=auth_headers(teacher_user),
    )

    await client.post(
        f"/api/v1/assessment-marking/decisions/{decision['id']}/complete",
        headers=auth_headers(teacher_user),
    )

    finalise_response = await client.post(
        f"/api/v1/assessment-marking/decisions/{decision['id']}/finalise",
        headers=auth_headers(school_admin),
    )

    assert finalise_response.status_code == 200, finalise_response.text

    response = await client.patch(
        f"/api/v1/assessment-marking/decisions/{decision['id']}",
        json={
            "mark_awarded": "5.00",
        },
        headers=auth_headers(teacher_user),
    )

    assert response.status_code == 409


# ---------------------------------------------------------------------------
# Ownership and isolation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_other_teacher_cannot_access_response(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
):
    context = await _build_marking_context(
        db_session,
        teacher_user,
    )

    other_teacher = await create_test_user(
        db_session,
        email="marking.api.other.teacher@example.com",
        roles=[UserRole.TEACHER],
        school_id=teacher_user.school_id,
    )

    created = await _create_response_via_api(
        client,
        script_id=context["script"].id,
        question_id=context["question"].id,
        user=teacher_user,
        auth_headers=auth_headers,
    )

    response = await client.get(
        f"/api/v1/assessment-marking/responses/{created['id']}",
        headers=auth_headers(other_teacher),
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_other_teacher_cannot_change_marking_decision(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
):
    context = await _build_marking_context(
        db_session,
        teacher_user,
    )

    other_teacher = await create_test_user(
        db_session,
        email="marking.api.other.marker@example.com",
        roles=[UserRole.TEACHER],
        school_id=teacher_user.school_id,
    )

    response_data = await _create_response_via_api(
        client,
        script_id=context["script"].id,
        question_id=context["question"].id,
        user=teacher_user,
        auth_headers=auth_headers,
    )

    await _submit_response_via_api(
        client,
        response_id=response_data["id"],
        user=teacher_user,
        auth_headers=auth_headers,
    )

    decision = await _create_decision_via_api(
        client,
        response_id=response_data["id"],
        user=teacher_user,
        auth_headers=auth_headers,
    )

    response = await client.patch(
        f"/api/v1/assessment-marking/decisions/{decision['id']}",
        json={
            "mark_awarded": "2.00",
        },
        headers=auth_headers(other_teacher),
    )

    assert response.status_code == 403


# ---------------------------------------------------------------------------
# Decision listing and deletion
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_teacher_can_list_script_marking_decisions_via_api(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
):
    context = await _build_marking_context(
        db_session,
        teacher_user,
    )

    response_data = await _create_response_via_api(
        client,
        script_id=context["script"].id,
        question_id=context["question"].id,
        user=teacher_user,
        auth_headers=auth_headers,
    )

    await _submit_response_via_api(
        client,
        response_id=response_data["id"],
        user=teacher_user,
        auth_headers=auth_headers,
    )

    decision = await _create_decision_via_api(
        client,
        response_id=response_data["id"],
        user=teacher_user,
        auth_headers=auth_headers,
    )

    response = await client.get(
        f"/api/v1/assessment-marking/scripts/{context['script'].id}/decisions",
        headers=auth_headers(teacher_user),
    )

    assert response.status_code == 200, response.text

    data = response.json()

    assert len(data) == 1
    assert data[0]["id"] == decision["id"]


@pytest.mark.asyncio
async def test_untouched_marking_decision_can_be_deleted_via_api(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
):
    context = await _build_marking_context(
        db_session,
        teacher_user,
    )

    response_data = await _create_response_via_api(
        client,
        script_id=context["script"].id,
        question_id=context["question"].id,
        user=teacher_user,
        auth_headers=auth_headers,
    )

    await _submit_response_via_api(
        client,
        response_id=response_data["id"],
        user=teacher_user,
        auth_headers=auth_headers,
    )

    decision = await _create_decision_via_api(
        client,
        response_id=response_data["id"],
        user=teacher_user,
        auth_headers=auth_headers,
    )

    response = await client.delete(
        f"/api/v1/assessment-marking/decisions/{decision['id']}",
        headers=auth_headers(teacher_user),
    )

    assert response.status_code == 204


@pytest.mark.asyncio
async def test_started_marking_decision_cannot_be_deleted_via_api(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
):
    context = await _build_marking_context(
        db_session,
        teacher_user,
    )

    response_data = await _create_response_via_api(
        client,
        script_id=context["script"].id,
        question_id=context["question"].id,
        user=teacher_user,
        auth_headers=auth_headers,
    )

    await _submit_response_via_api(
        client,
        response_id=response_data["id"],
        user=teacher_user,
        auth_headers=auth_headers,
    )

    decision = await _create_decision_via_api(
        client,
        response_id=response_data["id"],
        user=teacher_user,
        auth_headers=auth_headers,
    )

    start_response = await client.post(
        f"/api/v1/assessment-marking/decisions/{decision['id']}/start",
        headers=auth_headers(teacher_user),
    )

    assert start_response.status_code == 200, start_response.text

    response = await client.delete(
        f"/api/v1/assessment-marking/decisions/{decision['id']}",
        headers=auth_headers(teacher_user),
    )

    assert response.status_code == 409

# ---------------------------------------------------------------------------
# Examiner annotation API
# ---------------------------------------------------------------------------


async def _build_annotation_api_context(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
) -> dict:
    """
    Build one submitted response with a marking decision and default palette.
    """

    context = await _build_marking_context(
        db_session,
        teacher_user,
    )

    create_response = await client.post(
        f"/api/v1/assessment-marking/scripts/{context['script'].id}/responses",
        json={
            "question_id": context["question"].id,
            "response_text": "Candidate response for annotation marking.",
        },
        headers=auth_headers(teacher_user),
    )

    assert create_response.status_code == 201, create_response.text

    response_data = create_response.json()

    submit_response = await client.post(
        f"/api/v1/assessment-marking/responses/{response_data['id']}/submit",
        headers=auth_headers(teacher_user),
    )

    assert submit_response.status_code == 200, submit_response.text

    decision_response = await client.post(
        f"/api/v1/assessment-marking/responses/{response_data['id']}/decision",
        json={},
        headers=auth_headers(teacher_user),
    )

    assert decision_response.status_code == 201, decision_response.text

    palette = await ensure_default_marking_palette(
        db_session,
        teacher_user.school_id,
    )

    tick_tool = next(
        tool
        for tool in palette.tools
        if tool.value == "✓"
    )

    return {
        **context,
        "response": response_data,
        "decision": decision_response.json(),
        "palette": palette,
        "tick_tool": tick_tool,
    }


@pytest.mark.asyncio
async def test_teacher_can_create_list_and_get_marking_annotation(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
):
    context = await _build_annotation_api_context(
        client,
        db_session,
        teacher_user,
        auth_headers,
    )

    create_response = await client.post(
        f"/api/v1/assessment-marking/responses/{context['response']['id']}/annotations",
        json={
            "palette_tool_id": context["tick_tool"].id,
            "x": "0.25",
            "y": "0.75",
        },
        headers=auth_headers(teacher_user),
    )

    assert create_response.status_code == 201, create_response.text

    annotation = create_response.json()

    assert annotation["response_id"] == context["response"]["id"]
    assert annotation["marker_id"] == teacher_user.id
    assert annotation["palette_tool_id"] == context["tick_tool"].id
    assert annotation["annotation_type"] == "symbol"
    assert annotation["value"] == "✓"
    assert annotation["label_snapshot"] == "Correct / credit"
    assert annotation["surface_type"] == "response"
    assert annotation["revision"] == 1
    assert annotation["deleted_at"] is None

    list_response = await client.get(
        f"/api/v1/assessment-marking/responses/{context['response']['id']}/annotations",
        headers=auth_headers(teacher_user),
    )

    assert list_response.status_code == 200, list_response.text
    assert [item["id"] for item in list_response.json()] == [
        annotation["id"],
    ]

    get_response = await client.get(
        f"/api/v1/assessment-marking/annotations/{annotation['id']}",
        headers=auth_headers(teacher_user),
    )

    assert get_response.status_code == 200, get_response.text
    assert get_response.json()["id"] == annotation["id"]


@pytest.mark.asyncio
async def test_teacher_can_update_marking_annotation_with_revision(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
):
    context = await _build_annotation_api_context(
        client,
        db_session,
        teacher_user,
        auth_headers,
    )

    create_response = await client.post(
        f"/api/v1/assessment-marking/responses/{context['response']['id']}/annotations",
        json={
            "palette_tool_id": context["tick_tool"].id,
            "x": "0.10",
            "y": "0.20",
        },
        headers=auth_headers(teacher_user),
    )

    assert create_response.status_code == 201, create_response.text

    annotation = create_response.json()

    update_response = await client.patch(
        f"/api/v1/assessment-marking/annotations/{annotation['id']}",
        json={
            "revision": annotation["revision"],
            "x": "0.60",
            "y": "0.70",
        },
        headers=auth_headers(teacher_user),
    )

    assert update_response.status_code == 200, update_response.text

    updated = update_response.json()

    assert updated["revision"] == 2
    assert Decimal(updated["x"]) == Decimal("0.600000")
    assert Decimal(updated["y"]) == Decimal("0.700000")


@pytest.mark.asyncio
async def test_stale_marking_annotation_revision_returns_409(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
):
    context = await _build_annotation_api_context(
        client,
        db_session,
        teacher_user,
        auth_headers,
    )

    create_response = await client.post(
        f"/api/v1/assessment-marking/responses/{context['response']['id']}/annotations",
        json={
            "palette_tool_id": context["tick_tool"].id,
            "x": "0.10",
            "y": "0.20",
        },
        headers=auth_headers(teacher_user),
    )

    assert create_response.status_code == 201, create_response.text

    annotation = create_response.json()

    first_update = await client.patch(
        f"/api/v1/assessment-marking/annotations/{annotation['id']}",
        json={
            "revision": 1,
            "x": "0.30",
        },
        headers=auth_headers(teacher_user),
    )

    assert first_update.status_code == 200, first_update.text

    stale_update = await client.patch(
        f"/api/v1/assessment-marking/annotations/{annotation['id']}",
        json={
            "revision": 1,
            "x": "0.40",
        },
        headers=auth_headers(teacher_user),
    )

    assert stale_update.status_code == 409, stale_update.text


@pytest.mark.asyncio
async def test_marking_annotation_can_be_soft_deleted_via_api(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
):
    context = await _build_annotation_api_context(
        client,
        db_session,
        teacher_user,
        auth_headers,
    )

    create_response = await client.post(
        f"/api/v1/assessment-marking/responses/{context['response']['id']}/annotations",
        json={
            "palette_tool_id": context["tick_tool"].id,
            "x": "0.10",
            "y": "0.20",
        },
        headers=auth_headers(teacher_user),
    )

    assert create_response.status_code == 201, create_response.text

    annotation = create_response.json()

    delete_response = await client.delete(
        f"/api/v1/assessment-marking/annotations/{annotation['id']}",
        params={
            "revision": annotation["revision"],
        },
        headers=auth_headers(teacher_user),
    )

    assert delete_response.status_code == 200, delete_response.text

    deleted = delete_response.json()

    assert deleted["revision"] == 2
    assert deleted["deleted_at"] is not None
    assert deleted["deleted_by_id"] == teacher_user.id

    default_list = await client.get(
        f"/api/v1/assessment-marking/responses/{context['response']['id']}/annotations",
        headers=auth_headers(teacher_user),
    )

    assert default_list.status_code == 200, default_list.text
    assert default_list.json() == []

    audit_list = await client.get(
        f"/api/v1/assessment-marking/responses/{context['response']['id']}/annotations",
        params={
            "include_deleted": True,
        },
        headers=auth_headers(teacher_user),
    )

    assert audit_list.status_code == 200, audit_list.text
    assert len(audit_list.json()) == 1
    assert audit_list.json()[0]["id"] == annotation["id"]
    assert audit_list.json()[0]["deleted_at"] is not None


@pytest.mark.asyncio
async def test_marking_annotation_schema_rejects_invalid_coordinate(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
):
    context = await _build_annotation_api_context(
        client,
        db_session,
        teacher_user,
        auth_headers,
    )

    response = await client.post(
        f"/api/v1/assessment-marking/responses/{context['response']['id']}/annotations",
        json={
            "palette_tool_id": context["tick_tool"].id,
            "x": "1.01",
            "y": "0.50",
        },
        headers=auth_headers(teacher_user),
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_marking_annotation_update_rejects_surface_mutation(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
):
    context = await _build_annotation_api_context(
        client,
        db_session,
        teacher_user,
        auth_headers,
    )

    create_response = await client.post(
        f"/api/v1/assessment-marking/responses/{context['response']['id']}/annotations",
        json={
            "palette_tool_id": context["tick_tool"].id,
            "x": "0.10",
            "y": "0.20",
        },
        headers=auth_headers(teacher_user),
    )

    assert create_response.status_code == 201, create_response.text

    annotation = create_response.json()

    response = await client.patch(
        f"/api/v1/assessment-marking/annotations/{annotation['id']}",
        json={
            "revision": annotation["revision"],
            "surface_type": "script_page",
            "page_number": 2,
        },
        headers=auth_headers(teacher_user),
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_finalised_decision_blocks_annotation_mutation_via_api(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
):
    context = await _build_annotation_api_context(
        client,
        db_session,
        teacher_user,
        auth_headers,
    )

    create_response = await client.post(
        f"/api/v1/assessment-marking/responses/{context['response']['id']}/annotations",
        json={
            "palette_tool_id": context["tick_tool"].id,
            "x": "0.10",
            "y": "0.20",
        },
        headers=auth_headers(teacher_user),
    )

    assert create_response.status_code == 201, create_response.text

    annotation = create_response.json()

    decision = await db_session.get(
        MarkingDecision,
        context["decision"]["id"],
    )

    assert decision is not None

    decision.status = MarkingDecisionStatus.FINALISED
    await db_session.commit()

    create_after_finalise = await client.post(
        f"/api/v1/assessment-marking/responses/{context['response']['id']}/annotations",
        json={
            "palette_tool_id": context["tick_tool"].id,
            "x": "0.30",
            "y": "0.40",
        },
        headers=auth_headers(teacher_user),
    )

    assert create_after_finalise.status_code == 409

    update_after_finalise = await client.patch(
        f"/api/v1/assessment-marking/annotations/{annotation['id']}",
        json={
            "revision": annotation["revision"],
            "x": "0.50",
        },
        headers=auth_headers(teacher_user),
    )

    assert update_after_finalise.status_code == 409

    delete_after_finalise = await client.delete(
        f"/api/v1/assessment-marking/annotations/{annotation['id']}",
        params={
            "revision": annotation["revision"],
        },
        headers=auth_headers(teacher_user),
    )

    assert delete_after_finalise.status_code == 409
