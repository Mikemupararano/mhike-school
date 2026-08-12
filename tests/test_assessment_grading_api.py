from __future__ import annotations

from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.assessment import (
    Assessment,
    AssessmentStatus,
)
from app.models.assessment_candidate import (
    AssessmentCandidate,
    AssessmentCandidateStatus,
    AssessmentScript,
    AssessmentScriptStatus,
)
from app.models.assessment_grading import AssessmentGradingBasis
from app.models.assessment_question import AssessmentQuestion
from app.models.assessment_response import (
    AssessmentResponse,
    AssessmentResponseStatus,
    MarkingDecision,
    MarkingDecisionStatus,
)
from app.models.course import Course
from app.models.user import UserRole
from tests.conftest import create_test_user

# ---------------------------------------------------------------------------
# Test-data helpers
# ---------------------------------------------------------------------------


async def _create_course(
    db_session: AsyncSession,
    *,
    teacher_id: int,
    school_id: int,
    title: str = "Assessment Grading API Course",
) -> Course:
    course = Course(
        title=title,
        description="Course used by assessment grading API tests.",
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
    title: str = "Assessment Grading API Assessment",
) -> Assessment:
    assessment = Assessment(
        school_id=school_id,
        course_id=course_id,
        created_by_id=teacher_id,
        title=title,
        description="Assessment grading API test.",
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
    question_number: str,
    maximum_mark: Decimal,
    order: int,
) -> AssessmentQuestion:
    question = AssessmentQuestion(
        assessment_id=assessment_id,
        question_number=question_number,
        prompt=f"Question {question_number}",
        maximum_mark=maximum_mark,
        order=order,
        is_markable=True,
    )

    db_session.add(question)
    await db_session.commit()
    await db_session.refresh(question)

    return question


async def _create_candidate(
    db_session: AsyncSession,
    *,
    assessment_id: int,
    student_id: int,
    candidate_number: str,
) -> AssessmentCandidate:
    candidate = AssessmentCandidate(
        assessment_id=assessment_id,
        student_id=student_id,
        status=AssessmentCandidateStatus.SUBMITTED,
        candidate_number=candidate_number,
    )

    db_session.add(candidate)
    await db_session.commit()
    await db_session.refresh(candidate)

    return candidate


async def _create_script(
    db_session: AsyncSession,
    *,
    candidate_id: int,
    version: int = 1,
) -> AssessmentScript:
    script = AssessmentScript(
        candidate_id=candidate_id,
        version=version,
        status=AssessmentScriptStatus.SUBMITTED,
        source_type="pdf_upload",
        source_filename=f"grading-api-v{version}.pdf",
        storage_key=f"assessment-grading/grading-api-v{version}.pdf",
        mime_type="application/pdf",
        checksum=f"grading-api-{candidate_id}-{version}",
    )

    db_session.add(script)
    await db_session.commit()
    await db_session.refresh(script)

    return script


async def _create_response_and_decision(
    db_session: AsyncSession,
    *,
    script_id: int,
    question_id: int,
    marker_id: int,
    mark_awarded: Decimal,
    decision_status: MarkingDecisionStatus,
) -> tuple[AssessmentResponse, MarkingDecision]:
    response = AssessmentResponse(
        script_id=script_id,
        question_id=question_id,
        status=AssessmentResponseStatus.SUBMITTED,
        response_text="Candidate response",
    )

    db_session.add(response)
    await db_session.flush()

    decision = MarkingDecision(
        response_id=response.id,
        marker_id=marker_id,
        status=decision_status,
        mark_awarded=mark_awarded,
    )

    db_session.add(decision)
    await db_session.commit()
    await db_session.refresh(response)
    await db_session.refresh(decision)

    return response, decision


async def _build_context(
    db_session: AsyncSession,
    teacher_user,
):
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

    question_one = await _create_question(
        db_session,
        assessment_id=assessment.id,
        question_number="1",
        maximum_mark=Decimal("5"),
        order=1,
    )

    question_two = await _create_question(
        db_session,
        assessment_id=assessment.id,
        question_number="2",
        maximum_mark=Decimal("3"),
        order=2,
    )

    student = await create_test_user(
        db_session,
        email=f"grading.api.student.{assessment.id}@example.com",
        roles=[UserRole.STUDENT],
        school_id=teacher_user.school_id,
    )

    candidate = await _create_candidate(
        db_session,
        assessment_id=assessment.id,
        student_id=student.id,
        candidate_number="GRADE-API-001",
    )

    script = await _create_script(
        db_session,
        candidate_id=candidate.id,
    )

    return {
        "course": course,
        "assessment": assessment,
        "question_one": question_one,
        "question_two": question_two,
        "student": student,
        "candidate": candidate,
        "script": script,
    }


async def _create_scheme_via_api(
    client: AsyncClient,
    *,
    assessment_id: int,
    headers: dict[str, str],
    basis: str = "percentage",
):
    response = await client.post(
        f"/api/v1/assessment-grading/assessments/{assessment_id}/scheme",
        json={
            "name": "GCSE 9-1",
            "description": "Assessment grading scheme",
            "basis": basis,
            "is_active": True,
        },
        headers=headers,
    )

    assert response.status_code == 201, response.text

    return response.json()


async def _create_boundary_via_api(
    client: AsyncClient,
    *,
    scheme_id: int,
    headers: dict[str, str],
    grade_label: str,
    minimum_value: str,
    order: int,
    grade_points: str | None = None,
    is_pass: bool | None = None,
):
    payload: dict[str, object] = {
        "grade_label": grade_label,
        "minimum_value": minimum_value,
        "order": order,
    }

    if grade_points is not None:
        payload["grade_points"] = grade_points

    if is_pass is not None:
        payload["is_pass"] = is_pass

    response = await client.post(
        f"/api/v1/assessment-grading/schemes/{scheme_id}/boundaries",
        json=payload,
        headers=headers,
    )

    assert response.status_code == 201, response.text

    return response.json()


# ---------------------------------------------------------------------------
# Scheme API
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_teacher_can_create_grading_scheme(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
):
    context = await _build_context(
        db_session,
        teacher_user,
    )

    response = await client.post(
        (
            "/api/v1/assessment-grading/assessments/"
            f"{context['assessment'].id}/scheme"
        ),
        json={
            "name": " GCSE 9-1 ",
            "description": " Percentage boundaries ",
            "basis": "percentage",
            "is_active": True,
        },
        headers=auth_headers(teacher_user),
    )

    assert response.status_code == 201, response.text

    data = response.json()

    assert data["assessment_id"] == context["assessment"].id
    assert data["name"] == "GCSE 9-1"
    assert data["description"] == "Percentage boundaries"
    assert data["basis"] == "percentage"
    assert data["is_active"] is True
    assert data["created_by_id"] == teacher_user.id
    assert data["boundaries"] == []


@pytest.mark.asyncio
async def test_duplicate_scheme_is_rejected(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
):
    context = await _build_context(
        db_session,
        teacher_user,
    )

    headers = auth_headers(teacher_user)

    await _create_scheme_via_api(
        client,
        assessment_id=context["assessment"].id,
        headers=headers,
    )

    response = await client.post(
        (
            "/api/v1/assessment-grading/assessments/"
            f"{context['assessment'].id}/scheme"
        ),
        json={
            "name": "Second Scheme",
            "basis": "percentage",
        },
        headers=headers,
    )

    assert response.status_code == 409


@pytest.mark.asyncio
async def test_teacher_can_get_grading_scheme(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
):
    context = await _build_context(
        db_session,
        teacher_user,
    )

    headers = auth_headers(teacher_user)

    created = await _create_scheme_via_api(
        client,
        assessment_id=context["assessment"].id,
        headers=headers,
    )

    response = await client.get(
        (
            "/api/v1/assessment-grading/assessments/"
            f"{context['assessment'].id}/scheme"
        ),
        headers=headers,
    )

    assert response.status_code == 200, response.text
    assert response.json()["id"] == created["id"]


@pytest.mark.asyncio
async def test_teacher_can_update_scheme(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
):
    context = await _build_context(
        db_session,
        teacher_user,
    )

    headers = auth_headers(teacher_user)

    scheme = await _create_scheme_via_api(
        client,
        assessment_id=context["assessment"].id,
        headers=headers,
    )

    response = await client.patch(
        f"/api/v1/assessment-grading/schemes/{scheme['id']}",
        json={
            "name": "Updated Scheme",
            "description": "Updated",
            "is_active": False,
        },
        headers=headers,
    )

    assert response.status_code == 200, response.text

    data = response.json()

    assert data["name"] == "Updated Scheme"
    assert data["description"] == "Updated"
    assert data["is_active"] is False


@pytest.mark.asyncio
async def test_scheme_description_can_be_cleared_via_api(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
):
    context = await _build_context(
        db_session,
        teacher_user,
    )

    headers = auth_headers(teacher_user)

    scheme = await _create_scheme_via_api(
        client,
        assessment_id=context["assessment"].id,
        headers=headers,
    )

    response = await client.patch(
        f"/api/v1/assessment-grading/schemes/{scheme['id']}",
        json={
            "description": None,
        },
        headers=headers,
    )

    assert response.status_code == 200, response.text
    assert response.json()["description"] is None


@pytest.mark.asyncio
async def test_teacher_can_delete_scheme(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
):
    context = await _build_context(
        db_session,
        teacher_user,
    )

    headers = auth_headers(teacher_user)

    scheme = await _create_scheme_via_api(
        client,
        assessment_id=context["assessment"].id,
        headers=headers,
    )

    response = await client.delete(
        f"/api/v1/assessment-grading/schemes/{scheme['id']}",
        headers=headers,
    )

    assert response.status_code == 204


# ---------------------------------------------------------------------------
# Boundary API
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_teacher_can_create_boundary(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
):
    context = await _build_context(
        db_session,
        teacher_user,
    )

    headers = auth_headers(teacher_user)

    scheme = await _create_scheme_via_api(
        client,
        assessment_id=context["assessment"].id,
        headers=headers,
    )

    response = await client.post(
        f"/api/v1/assessment-grading/schemes/{scheme['id']}/boundaries",
        json={
            "grade_label": " 9 ",
            "minimum_value": "80",
            "order": 1,
            "description": " Highest grade ",
            "grade_points": "9",
            "is_pass": True,
        },
        headers=headers,
    )

    assert response.status_code == 201, response.text

    data = response.json()

    assert data["grade_label"] == "9"
    assert Decimal(data["minimum_value"]) == Decimal("80.0000")
    assert data["order"] == 1
    assert data["description"] == "Highest grade"
    assert Decimal(data["grade_points"]) == Decimal("9.00")
    assert data["is_pass"] is True


@pytest.mark.asyncio
async def test_percentage_boundary_above_100_is_rejected_via_api(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
):
    context = await _build_context(
        db_session,
        teacher_user,
    )

    headers = auth_headers(teacher_user)

    scheme = await _create_scheme_via_api(
        client,
        assessment_id=context["assessment"].id,
        headers=headers,
    )

    response = await client.post(
        f"/api/v1/assessment-grading/schemes/{scheme['id']}/boundaries",
        json={
            "grade_label": "Invalid",
            "minimum_value": "101",
            "order": 1,
        },
        headers=headers,
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_duplicate_boundary_label_is_rejected_via_api(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
):
    context = await _build_context(
        db_session,
        teacher_user,
    )

    headers = auth_headers(teacher_user)

    scheme = await _create_scheme_via_api(
        client,
        assessment_id=context["assessment"].id,
        headers=headers,
    )

    await _create_boundary_via_api(
        client,
        scheme_id=scheme["id"],
        headers=headers,
        grade_label="9",
        minimum_value="80",
        order=1,
    )

    response = await client.post(
        f"/api/v1/assessment-grading/schemes/{scheme['id']}/boundaries",
        json={
            "grade_label": "9",
            "minimum_value": "70",
            "order": 2,
        },
        headers=headers,
    )

    assert response.status_code == 409


@pytest.mark.asyncio
async def test_boundaries_are_returned_highest_threshold_first(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
):
    context = await _build_context(
        db_session,
        teacher_user,
    )

    headers = auth_headers(teacher_user)

    scheme = await _create_scheme_via_api(
        client,
        assessment_id=context["assessment"].id,
        headers=headers,
    )

    await _create_boundary_via_api(
        client,
        scheme_id=scheme["id"],
        headers=headers,
        grade_label="7",
        minimum_value="60",
        order=3,
    )

    await _create_boundary_via_api(
        client,
        scheme_id=scheme["id"],
        headers=headers,
        grade_label="9",
        minimum_value="80",
        order=1,
    )

    await _create_boundary_via_api(
        client,
        scheme_id=scheme["id"],
        headers=headers,
        grade_label="8",
        minimum_value="70",
        order=2,
    )

    response = await client.get(
        f"/api/v1/assessment-grading/schemes/{scheme['id']}/boundaries",
        headers=headers,
    )

    assert response.status_code == 200, response.text

    data = response.json()

    assert data["grading_scheme_id"] == scheme["id"]
    assert [boundary["grade_label"] for boundary in data["boundaries"]] == [
        "9",
        "8",
        "7",
    ]


@pytest.mark.asyncio
async def test_teacher_can_update_boundary_and_clear_metadata(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
):
    context = await _build_context(
        db_session,
        teacher_user,
    )

    headers = auth_headers(teacher_user)

    scheme = await _create_scheme_via_api(
        client,
        assessment_id=context["assessment"].id,
        headers=headers,
    )

    boundary = await _create_boundary_via_api(
        client,
        scheme_id=scheme["id"],
        headers=headers,
        grade_label="9",
        minimum_value="80",
        order=1,
        grade_points="9",
        is_pass=True,
    )

    response = await client.patch(
        f"/api/v1/assessment-grading/boundaries/{boundary['id']}",
        json={
            "grade_label": "9*",
            "minimum_value": "85",
            "description": None,
            "grade_points": None,
            "is_pass": None,
        },
        headers=headers,
    )

    assert response.status_code == 200, response.text

    data = response.json()

    assert data["grade_label"] == "9*"
    assert Decimal(data["minimum_value"]) == Decimal("85.0000")
    assert data["description"] is None
    assert data["grade_points"] is None
    assert data["is_pass"] is None


@pytest.mark.asyncio
async def test_teacher_can_delete_boundary(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
):
    context = await _build_context(
        db_session,
        teacher_user,
    )

    headers = auth_headers(teacher_user)

    scheme = await _create_scheme_via_api(
        client,
        assessment_id=context["assessment"].id,
        headers=headers,
    )

    boundary = await _create_boundary_via_api(
        client,
        scheme_id=scheme["id"],
        headers=headers,
        grade_label="9",
        minimum_value="80",
        order=1,
    )

    response = await client.delete(
        f"/api/v1/assessment-grading/boundaries/{boundary['id']}",
        headers=headers,
    )

    assert response.status_code == 204


# ---------------------------------------------------------------------------
# Explicit grade resolution API
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_explicit_grade_resolution_is_inclusive(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
):
    context = await _build_context(
        db_session,
        teacher_user,
    )

    headers = auth_headers(teacher_user)

    scheme = await _create_scheme_via_api(
        client,
        assessment_id=context["assessment"].id,
        headers=headers,
    )

    await _create_boundary_via_api(
        client,
        scheme_id=scheme["id"],
        headers=headers,
        grade_label="9",
        minimum_value="80",
        order=1,
        grade_points="9",
        is_pass=True,
    )

    await _create_boundary_via_api(
        client,
        scheme_id=scheme["id"],
        headers=headers,
        grade_label="8",
        minimum_value="70",
        order=2,
        grade_points="8",
        is_pass=True,
    )

    response = await client.post(
        (
            "/api/v1/assessment-grading/assessments/"
            f"{context['assessment'].id}/resolve"
        ),
        json={
            "value": "70",
        },
        headers=headers,
    )

    assert response.status_code == 200, response.text

    data = response.json()

    assert data["grade"] == "8"
    assert Decimal(data["value"]) == Decimal("70")
    assert Decimal(data["minimum_value"]) == Decimal("70.0000")
    assert Decimal(data["grade_points"]) == Decimal("8.00")
    assert data["is_pass"] is True


@pytest.mark.asyncio
async def test_value_below_all_boundaries_returns_no_grade_via_api(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
):
    context = await _build_context(
        db_session,
        teacher_user,
    )

    headers = auth_headers(teacher_user)

    scheme = await _create_scheme_via_api(
        client,
        assessment_id=context["assessment"].id,
        headers=headers,
    )

    await _create_boundary_via_api(
        client,
        scheme_id=scheme["id"],
        headers=headers,
        grade_label="Pass",
        minimum_value="50",
        order=1,
    )

    response = await client.post(
        (
            "/api/v1/assessment-grading/assessments/"
            f"{context['assessment'].id}/resolve"
        ),
        json={
            "value": "40",
        },
        headers=headers,
    )

    assert response.status_code == 200, response.text

    data = response.json()

    assert data["grade"] is None
    assert data["boundary_id"] is None


# ---------------------------------------------------------------------------
# Derived script grading API
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_script_can_be_graded_from_completed_results(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
):
    context = await _build_context(
        db_session,
        teacher_user,
    )

    headers = auth_headers(teacher_user)

    scheme = await _create_scheme_via_api(
        client,
        assessment_id=context["assessment"].id,
        headers=headers,
    )

    await _create_boundary_via_api(
        client,
        scheme_id=scheme["id"],
        headers=headers,
        grade_label="9",
        minimum_value="80",
        order=1,
    )

    await _create_boundary_via_api(
        client,
        scheme_id=scheme["id"],
        headers=headers,
        grade_label="8",
        minimum_value="70",
        order=2,
    )

    await _create_response_and_decision(
        db_session,
        script_id=context["script"].id,
        question_id=context["question_one"].id,
        marker_id=teacher_user.id,
        mark_awarded=Decimal("4"),
        decision_status=MarkingDecisionStatus.MARKED,
    )

    await _create_response_and_decision(
        db_session,
        script_id=context["script"].id,
        question_id=context["question_two"].id,
        marker_id=teacher_user.id,
        mark_awarded=Decimal("2"),
        decision_status=MarkingDecisionStatus.FINALISED,
    )

    response = await client.get(
        f"/api/v1/assessment-grading/scripts/{context['script'].id}",
        params={
            "result_stage": "completed",
        },
        headers=headers,
    )

    assert response.status_code == 200, response.text

    data = response.json()

    assert data["script_id"] == context["script"].id
    assert data["result_stage"] == "completed"
    assert data["basis"] == "percentage"
    assert Decimal(data["value"]) == Decimal("75.00")
    assert data["grade"] == "8"


@pytest.mark.asyncio
async def test_script_grading_defaults_to_finalised_stage(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
):
    context = await _build_context(
        db_session,
        teacher_user,
    )

    headers = auth_headers(teacher_user)

    scheme = await _create_scheme_via_api(
        client,
        assessment_id=context["assessment"].id,
        headers=headers,
    )

    await _create_boundary_via_api(
        client,
        scheme_id=scheme["id"],
        headers=headers,
        grade_label="Pass",
        minimum_value="50",
        order=1,
    )

    await _create_response_and_decision(
        db_session,
        script_id=context["script"].id,
        question_id=context["question_one"].id,
        marker_id=teacher_user.id,
        mark_awarded=Decimal("5"),
        decision_status=MarkingDecisionStatus.FINALISED,
    )

    response = await client.get(
        f"/api/v1/assessment-grading/scripts/{context['script'].id}",
        headers=headers,
    )

    assert response.status_code == 200, response.text

    data = response.json()

    assert data["result_stage"] == "finalised"
    assert Decimal(data["value"]) == Decimal("62.50")
    assert data["grade"] == "Pass"


@pytest.mark.asyncio
async def test_invalid_script_result_stage_is_rejected(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
):
    context = await _build_context(
        db_session,
        teacher_user,
    )

    headers = auth_headers(teacher_user)

    await _create_scheme_via_api(
        client,
        assessment_id=context["assessment"].id,
        headers=headers,
    )

    response = await client.get(
        f"/api/v1/assessment-grading/scripts/{context['script'].id}",
        params={
            "result_stage": "published",
        },
        headers=headers,
    )

    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Candidate grading API
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_candidate_grade_uses_latest_script_version(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
):
    context = await _build_context(
        db_session,
        teacher_user,
    )

    headers = auth_headers(teacher_user)

    scheme = await _create_scheme_via_api(
        client,
        assessment_id=context["assessment"].id,
        headers=headers,
    )

    await _create_boundary_via_api(
        client,
        scheme_id=scheme["id"],
        headers=headers,
        grade_label="9",
        minimum_value="80",
        order=1,
    )

    second_script = await _create_script(
        db_session,
        candidate_id=context["candidate"].id,
        version=2,
    )

    await _create_response_and_decision(
        db_session,
        script_id=second_script.id,
        question_id=context["question_one"].id,
        marker_id=teacher_user.id,
        mark_awarded=Decimal("5"),
        decision_status=MarkingDecisionStatus.FINALISED,
    )

    await _create_response_and_decision(
        db_session,
        script_id=second_script.id,
        question_id=context["question_two"].id,
        marker_id=teacher_user.id,
        mark_awarded=Decimal("3"),
        decision_status=MarkingDecisionStatus.FINALISED,
    )

    response = await client.get(
        f"/api/v1/assessment-grading/candidates/{context['candidate'].id}",
        headers=headers,
    )

    assert response.status_code == 200, response.text

    data = response.json()

    assert data["script_id"] == second_script.id
    assert data["script_version"] == 2
    assert Decimal(data["value"]) == Decimal("100.00")
    assert data["grade"] == "9"


# ---------------------------------------------------------------------------
# Access control
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_other_teacher_cannot_create_grading_scheme(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
):
    context = await _build_context(
        db_session,
        teacher_user,
    )

    other_teacher = await create_test_user(
        db_session,
        email="grading.api.other.teacher@example.com",
        roles=[UserRole.TEACHER],
        school_id=teacher_user.school_id,
    )

    response = await client.post(
        (
            "/api/v1/assessment-grading/assessments/"
            f"{context['assessment'].id}/scheme"
        ),
        json={
            "name": "Unauthorised Scheme",
            "basis": "percentage",
        },
        headers=auth_headers(other_teacher),
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_other_teacher_cannot_view_grading_scheme(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
):
    context = await _build_context(
        db_session,
        teacher_user,
    )

    headers = auth_headers(teacher_user)

    await _create_scheme_via_api(
        client,
        assessment_id=context["assessment"].id,
        headers=headers,
    )

    other_teacher = await create_test_user(
        db_session,
        email="grading.api.other.viewer@example.com",
        roles=[UserRole.TEACHER],
        school_id=teacher_user.school_id,
    )

    response = await client.get(
        (
            "/api/v1/assessment-grading/assessments/"
            f"{context['assessment'].id}/scheme"
        ),
        headers=auth_headers(other_teacher),
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_school_admin_can_manage_grading_scheme(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
):
    context = await _build_context(
        db_session,
        teacher_user,
    )

    school_admin = await create_test_user(
        db_session,
        email="grading.api.school.admin@example.com",
        roles=[UserRole.SCHOOL_ADMIN],
        school_id=teacher_user.school_id,
    )

    response = await client.post(
        (
            "/api/v1/assessment-grading/assessments/"
            f"{context['assessment'].id}/scheme"
        ),
        json={
            "name": "Admin Scheme",
            "basis": "percentage",
        },
        headers=auth_headers(school_admin),
    )

    assert response.status_code == 201, response.text
    assert response.json()["created_by_id"] == school_admin.id


@pytest.mark.asyncio
async def test_student_cannot_access_assessment_grading_api(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
):
    context = await _build_context(
        db_session,
        teacher_user,
    )

    student = await create_test_user(
        db_session,
        email="grading.api.unauthorised.student@example.com",
        roles=[UserRole.STUDENT],
        school_id=teacher_user.school_id,
    )

    response = await client.get(
        (
            "/api/v1/assessment-grading/assessments/"
            f"{context['assessment'].id}/scheme"
        ),
        headers=auth_headers(student),
    )

    assert response.status_code == 403


# ---------------------------------------------------------------------------
# Missing-resource behaviour
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_missing_scheme_returns_404(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
):
    context = await _build_context(
        db_session,
        teacher_user,
    )

    response = await client.get(
        (
            "/api/v1/assessment-grading/assessments/"
            f"{context['assessment'].id}/scheme"
        ),
        headers=auth_headers(teacher_user),
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_missing_boundary_returns_404(
    client: AsyncClient,
    teacher_user,
    auth_headers,
):
    response = await client.patch(
        "/api/v1/assessment-grading/boundaries/999999999",
        json={
            "grade_label": "X",
        },
        headers=auth_headers(teacher_user),
    )

    assert response.status_code == 404
