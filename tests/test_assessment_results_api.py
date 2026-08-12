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
    title: str = "Assessment Results API Course",
) -> Course:
    """
    Create and persist a teacher-owned course.
    """

    course = Course(
        title=title,
        description="Course used by assessment results API tests.",
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
    title: str = "Assessment Results API Assessment",
) -> Assessment:
    """
    Create and persist a published assessment.
    """

    assessment = Assessment(
        school_id=school_id,
        course_id=course_id,
        created_by_id=teacher_id,
        title=title,
        description="Assessment results API test.",
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
    is_markable: bool = True,
    parent_question_id: int | None = None,
) -> AssessmentQuestion:
    """
    Create and persist an assessment question.
    """

    question = AssessmentQuestion(
        assessment_id=assessment_id,
        parent_question_id=parent_question_id,
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


async def _create_candidate(
    db_session: AsyncSession,
    *,
    assessment_id: int,
    student_id: int,
    candidate_number: str,
) -> AssessmentCandidate:
    """
    Create and persist an assessment candidate.
    """

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
    script_status: AssessmentScriptStatus = AssessmentScriptStatus.SUBMITTED,
) -> AssessmentScript:
    """
    Create and persist one assessment script version.
    """

    script = AssessmentScript(
        candidate_id=candidate_id,
        version=version,
        status=script_status,
        source_type="pdf_upload",
        source_filename=f"results-api-v{version}.pdf",
        storage_key=f"assessment-results/results-api-v{version}.pdf",
        mime_type="application/pdf",
        checksum=f"results-api-{candidate_id}-{version}",
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
    mark_awarded: Decimal | None,
    decision_status: MarkingDecisionStatus,
    response_status: AssessmentResponseStatus = AssessmentResponseStatus.SUBMITTED,
) -> tuple[AssessmentResponse, MarkingDecision]:
    """
    Create one response and its authoritative question-level marking decision.
    """

    response = AssessmentResponse(
        script_id=script_id,
        question_id=question_id,
        status=response_status,
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


async def _build_results_context(
    db_session: AsyncSession,
    teacher_user,
):
    """
    Build one complete assessment-results context.
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

    question_one = await _create_question(
        db_session,
        assessment_id=assessment.id,
        question_number="1",
        maximum_mark=Decimal("5.00"),
        order=1,
    )

    question_two = await _create_question(
        db_session,
        assessment_id=assessment.id,
        question_number="2",
        maximum_mark=Decimal("3.00"),
        order=2,
    )

    student = await create_test_user(
        db_session,
        email=f"results.api.student.{assessment.id}@example.com",
        roles=[UserRole.STUDENT],
        school_id=teacher_user.school_id,
    )

    candidate = await _create_candidate(
        db_session,
        assessment_id=assessment.id,
        student_id=student.id,
        candidate_number="RESULT-API-001",
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


# ---------------------------------------------------------------------------
# Script result API
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_teacher_can_get_script_result(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
):
    context = await _build_results_context(
        db_session,
        teacher_user,
    )

    await _create_response_and_decision(
        db_session,
        script_id=context["script"].id,
        question_id=context["question_one"].id,
        marker_id=teacher_user.id,
        mark_awarded=Decimal("4.00"),
        decision_status=MarkingDecisionStatus.MARKED,
    )

    response = await client.get(
        f"/api/v1/assessment-results/scripts/{context['script'].id}",
        headers=auth_headers(teacher_user),
    )

    assert response.status_code == 200, response.text

    data = response.json()

    assert data["assessment_id"] == context["assessment"].id
    assert data["candidate_id"] == context["candidate"].id
    assert data["student_id"] == context["student"].id
    assert data["script_id"] == context["script"].id
    assert data["script_version"] == 1

    assert Decimal(data["maximum_mark"]) == Decimal("8.00")
    assert Decimal(data["mark_awarded"]) == Decimal("4.00")
    assert Decimal(data["completed_mark_awarded"]) == Decimal("4.00")
    assert Decimal(data["finalised_mark_awarded"]) == Decimal("0")

    assert Decimal(data["percentage"]) == Decimal("50.00")
    assert data["markable_question_count"] == 2
    assert data["marked_question_count"] == 1

    assert Decimal(data["marking_completion_percentage"]) == Decimal("50.00")

    assert data["is_fully_marked"] is False


@pytest.mark.asyncio
async def test_script_result_distinguishes_provisional_completed_and_final_marks(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
):
    context = await _build_results_context(
        db_session,
        teacher_user,
    )

    await _create_response_and_decision(
        db_session,
        script_id=context["script"].id,
        question_id=context["question_one"].id,
        marker_id=teacher_user.id,
        mark_awarded=Decimal("4.00"),
        decision_status=MarkingDecisionStatus.IN_PROGRESS,
    )

    await _create_response_and_decision(
        db_session,
        script_id=context["script"].id,
        question_id=context["question_two"].id,
        marker_id=teacher_user.id,
        mark_awarded=Decimal("2.00"),
        decision_status=MarkingDecisionStatus.FINALISED,
    )

    response = await client.get(
        f"/api/v1/assessment-results/scripts/{context['script'].id}",
        headers=auth_headers(teacher_user),
    )

    assert response.status_code == 200, response.text

    data = response.json()

    assert Decimal(data["mark_awarded"]) == Decimal("6.00")
    assert Decimal(data["completed_mark_awarded"]) == Decimal("2.00")
    assert Decimal(data["finalised_mark_awarded"]) == Decimal("2.00")

    assert Decimal(data["percentage"]) == Decimal("75.00")
    assert Decimal(data["completed_percentage"]) == Decimal("25.00")
    assert Decimal(data["finalised_percentage"]) == Decimal("25.00")


@pytest.mark.asyncio
async def test_script_result_includes_unanswered_questions(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
):
    context = await _build_results_context(
        db_session,
        teacher_user,
    )

    await _create_response_and_decision(
        db_session,
        script_id=context["script"].id,
        question_id=context["question_one"].id,
        marker_id=teacher_user.id,
        mark_awarded=Decimal("5.00"),
        decision_status=MarkingDecisionStatus.MARKED,
    )

    response = await client.get(
        f"/api/v1/assessment-results/scripts/{context['script'].id}",
        headers=auth_headers(teacher_user),
    )

    assert response.status_code == 200, response.text

    questions = response.json()["questions"]

    assert len(questions) == 2

    second = next(
        question
        for question in questions
        if question["question_id"] == context["question_two"].id
    )

    assert second["response_id"] is None
    assert second["response_status"] is None
    assert second["decision_id"] is None
    assert second["decision_status"] is None
    assert second["mark_awarded"] is None
    assert second["percentage"] is None
    assert second["is_marked"] is False
    assert second["is_finalised"] is False


@pytest.mark.asyncio
async def test_non_markable_question_is_excluded_from_script_maximum(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
):
    context = await _build_results_context(
        db_session,
        teacher_user,
    )

    await _create_question(
        db_session,
        assessment_id=context["assessment"].id,
        question_number="3",
        maximum_mark=Decimal("20.00"),
        order=3,
        is_markable=False,
    )

    response = await client.get(
        f"/api/v1/assessment-results/scripts/{context['script'].id}",
        headers=auth_headers(teacher_user),
    )

    assert response.status_code == 200, response.text

    data = response.json()

    assert Decimal(data["maximum_mark"]) == Decimal("8.00")
    assert data["markable_question_count"] == 2
    assert len(data["questions"]) == 2


@pytest.mark.asyncio
async def test_markable_parent_and_child_both_contribute_via_api(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
):
    context = await _build_results_context(
        db_session,
        teacher_user,
    )

    parent = await _create_question(
        db_session,
        assessment_id=context["assessment"].id,
        question_number="3",
        maximum_mark=Decimal("2.00"),
        order=3,
        is_markable=True,
    )

    await _create_question(
        db_session,
        assessment_id=context["assessment"].id,
        question_number="3(a)",
        maximum_mark=Decimal("1.00"),
        order=4,
        is_markable=True,
        parent_question_id=parent.id,
    )

    response = await client.get(
        f"/api/v1/assessment-results/scripts/{context['script'].id}",
        headers=auth_headers(teacher_user),
    )

    assert response.status_code == 200, response.text

    data = response.json()

    assert Decimal(data["maximum_mark"]) == Decimal("11.00")
    assert data["markable_question_count"] == 4


@pytest.mark.asyncio
async def test_missing_script_returns_404(
    client: AsyncClient,
    teacher_user,
    auth_headers,
):
    response = await client.get(
        "/api/v1/assessment-results/scripts/999999999",
        headers=auth_headers(teacher_user),
    )

    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Candidate result API
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_teacher_can_get_candidate_result(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
):
    context = await _build_results_context(
        db_session,
        teacher_user,
    )

    response = await client.get(
        f"/api/v1/assessment-results/candidates/{context['candidate'].id}",
        headers=auth_headers(teacher_user),
    )

    assert response.status_code == 200, response.text

    data = response.json()

    assert data["assessment_id"] == context["assessment"].id
    assert data["candidate_id"] == context["candidate"].id
    assert data["student_id"] == context["student"].id
    assert data["candidate_number"] == "RESULT-API-001"
    assert data["candidate_status"] == AssessmentCandidateStatus.SUBMITTED.value

    assert data["script_count"] == 1
    assert len(data["scripts"]) == 1
    assert data["latest_script_result"]["script_id"] == context["script"].id


@pytest.mark.asyncio
async def test_candidate_result_preserves_multiple_script_versions(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
):
    context = await _build_results_context(
        db_session,
        teacher_user,
    )

    second_script = await _create_script(
        db_session,
        candidate_id=context["candidate"].id,
        version=2,
    )

    response = await client.get(
        f"/api/v1/assessment-results/candidates/{context['candidate'].id}",
        headers=auth_headers(teacher_user),
    )

    assert response.status_code == 200, response.text

    data = response.json()

    assert data["script_count"] == 2
    assert [script["script_version"] for script in data["scripts"]] == [
        1,
        2,
    ]

    assert data["latest_script_result"]["script_id"] == second_script.id


@pytest.mark.asyncio
async def test_candidate_without_script_has_null_latest_result(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
):
    course = await _create_course(
        db_session,
        teacher_id=teacher_user.id,
        school_id=teacher_user.school_id,
        title="Assessment Results Empty Candidate Course",
    )

    assessment = await _create_assessment(
        db_session,
        teacher_id=teacher_user.id,
        school_id=teacher_user.school_id,
        course_id=course.id,
        title="Assessment Results Empty Candidate",
    )

    student = await create_test_user(
        db_session,
        email="assessment.results.api.no.script@example.com",
        roles=[UserRole.STUDENT],
        school_id=teacher_user.school_id,
    )

    candidate = AssessmentCandidate(
        assessment_id=assessment.id,
        student_id=student.id,
        status=AssessmentCandidateStatus.ALLOCATED,
        candidate_number="NO-SCRIPT",
    )

    db_session.add(candidate)

    await db_session.commit()
    await db_session.refresh(candidate)

    response = await client.get(
        f"/api/v1/assessment-results/candidates/{candidate.id}",
        headers=auth_headers(teacher_user),
    )

    assert response.status_code == 200, response.text

    data = response.json()

    assert data["script_count"] == 0
    assert data["scripts"] == []
    assert data["latest_script_result"] is None


@pytest.mark.asyncio
async def test_missing_candidate_result_returns_404(
    client: AsyncClient,
    teacher_user,
    auth_headers,
):
    response = await client.get(
        "/api/v1/assessment-results/candidates/999999999",
        headers=auth_headers(teacher_user),
    )

    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Assessment result grid API
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_teacher_can_get_assessment_result_grid(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
):
    context = await _build_results_context(
        db_session,
        teacher_user,
    )

    await _create_response_and_decision(
        db_session,
        script_id=context["script"].id,
        question_id=context["question_one"].id,
        marker_id=teacher_user.id,
        mark_awarded=Decimal("4.00"),
        decision_status=MarkingDecisionStatus.MARKED,
    )

    response = await client.get(
        ("/api/v1/assessment-results/assessments/" f"{context['assessment'].id}/grid"),
        headers=auth_headers(teacher_user),
    )

    assert response.status_code == 200, response.text

    data = response.json()

    assert data["assessment_id"] == context["assessment"].id
    assert data["title"] == context["assessment"].title
    assert data["status"] == AssessmentStatus.PUBLISHED.value

    assert Decimal(data["maximum_mark"]) == Decimal("8.00")
    assert data["markable_question_count"] == 2
    assert data["script_count"] == 1

    row = data["scripts"][0]

    assert row["script_id"] == context["script"].id
    assert row["candidate_id"] == context["candidate"].id
    assert row["version"] == 1
    assert Decimal(row["mark_awarded"]) == Decimal("4.00")
    assert Decimal(row["percentage"]) == Decimal("50.00")
    assert row["completed_decision_count"] == 1

    assert Decimal(row["marking_completion_percentage"]) == Decimal("50.00")


@pytest.mark.asyncio
async def test_result_grid_preserves_multiple_script_versions(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
):
    context = await _build_results_context(
        db_session,
        teacher_user,
    )

    await _create_script(
        db_session,
        candidate_id=context["candidate"].id,
        version=2,
    )

    response = await client.get(
        ("/api/v1/assessment-results/assessments/" f"{context['assessment'].id}/grid"),
        headers=auth_headers(teacher_user),
    )

    assert response.status_code == 200, response.text

    data = response.json()

    assert data["script_count"] == 2
    assert [script["version"] for script in data["scripts"]] == [
        1,
        2,
    ]


@pytest.mark.asyncio
async def test_empty_assessment_result_grid_has_no_scripts(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
):
    course = await _create_course(
        db_session,
        teacher_id=teacher_user.id,
        school_id=teacher_user.school_id,
        title="Empty Results Grid Course",
    )

    assessment = await _create_assessment(
        db_session,
        teacher_id=teacher_user.id,
        school_id=teacher_user.school_id,
        course_id=course.id,
        title="Empty Results Grid Assessment",
    )

    await _create_question(
        db_session,
        assessment_id=assessment.id,
        question_number="1",
        maximum_mark=Decimal("10.00"),
        order=1,
    )

    response = await client.get(
        ("/api/v1/assessment-results/assessments/" f"{assessment.id}/grid"),
        headers=auth_headers(teacher_user),
    )

    assert response.status_code == 200, response.text

    data = response.json()

    assert data["script_count"] == 0
    assert data["scripts"] == []
    assert Decimal(data["maximum_mark"]) == Decimal("10.00")


# ---------------------------------------------------------------------------
# Assessment summary API
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_teacher_can_get_assessment_results_summary(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
):
    context = await _build_results_context(
        db_session,
        teacher_user,
    )

    await _create_response_and_decision(
        db_session,
        script_id=context["script"].id,
        question_id=context["question_one"].id,
        marker_id=teacher_user.id,
        mark_awarded=Decimal("4.00"),
        decision_status=MarkingDecisionStatus.MARKED,
    )

    await _create_response_and_decision(
        db_session,
        script_id=context["script"].id,
        question_id=context["question_two"].id,
        marker_id=teacher_user.id,
        mark_awarded=Decimal("2.00"),
        decision_status=MarkingDecisionStatus.FINALISED,
    )

    response = await client.get(
        (
            "/api/v1/assessment-results/assessments/"
            f"{context['assessment'].id}/summary"
        ),
        headers=auth_headers(teacher_user),
    )

    assert response.status_code == 200, response.text

    data = response.json()

    assert data["assessment_id"] == context["assessment"].id
    assert Decimal(data["maximum_mark"]) == Decimal("8.00")

    assert data["markable_question_count"] == 2
    assert data["candidate_count"] == 1
    assert data["script_count"] == 1
    assert data["expected_question_decisions"] == 2

    assert data["completed_decision_count"] == 2
    assert data["finalised_decision_count"] == 1

    assert Decimal(data["marking_completion_percentage"]) == Decimal("100.00")

    assert Decimal(data["finalisation_completion_percentage"]) == Decimal("50.00")

    assert Decimal(data["total_awarded_marks"]) == Decimal("6.00")
    assert Decimal(data["completed_awarded_marks"]) == Decimal("6.00")
    assert Decimal(data["finalised_awarded_marks"]) == Decimal("2.00")


@pytest.mark.asyncio
async def test_assessment_summary_reports_zero_completion_when_scripts_exist_but_unmarked(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
):
    context = await _build_results_context(
        db_session,
        teacher_user,
    )

    response = await client.get(
        (
            "/api/v1/assessment-results/assessments/"
            f"{context['assessment'].id}/summary"
        ),
        headers=auth_headers(teacher_user),
    )

    assert response.status_code == 200, response.text

    data = response.json()

    assert data["expected_question_decisions"] == 2
    assert data["completed_decision_count"] == 0
    assert data["finalised_decision_count"] == 0

    assert Decimal(data["marking_completion_percentage"]) == Decimal("0.00")

    assert Decimal(data["finalisation_completion_percentage"]) == Decimal("0.00")


@pytest.mark.asyncio
async def test_missing_assessment_summary_returns_404(
    client: AsyncClient,
    teacher_user,
    auth_headers,
):
    response = await client.get(
        "/api/v1/assessment-results/assessments/999999999/summary",
        headers=auth_headers(teacher_user),
    )

    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Question-level analysis / QLA API
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_teacher_can_get_completed_question_analysis(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
):
    context = await _build_results_context(
        db_session,
        teacher_user,
    )

    second_student = await create_test_user(
        db_session,
        email="results.api.qla.second.student@example.com",
        roles=[UserRole.STUDENT],
        school_id=teacher_user.school_id,
    )

    second_candidate = await _create_candidate(
        db_session,
        assessment_id=context["assessment"].id,
        student_id=second_student.id,
        candidate_number="RESULT-API-002",
    )

    second_script = await _create_script(
        db_session,
        candidate_id=second_candidate.id,
    )

    await _create_response_and_decision(
        db_session,
        script_id=context["script"].id,
        question_id=context["question_one"].id,
        marker_id=teacher_user.id,
        mark_awarded=Decimal("4.00"),
        decision_status=MarkingDecisionStatus.MARKED,
    )

    await _create_response_and_decision(
        db_session,
        script_id=second_script.id,
        question_id=context["question_one"].id,
        marker_id=teacher_user.id,
        mark_awarded=Decimal("2.00"),
        decision_status=MarkingDecisionStatus.FINALISED,
    )

    response = await client.get(
        (
            "/api/v1/assessment-results/assessments/"
            f"{context['assessment'].id}/questions"
        ),
        headers=auth_headers(teacher_user),
    )

    assert response.status_code == 200, response.text

    data = response.json()

    assert data["assessment_id"] == context["assessment"].id
    assert data["completed_only"] is True
    assert len(data["questions"]) == 2

    question_one = next(
        question
        for question in data["questions"]
        if question["question_id"] == context["question_one"].id
    )

    assert question_one["response_count"] == 2
    assert question_one["marked_count"] == 2

    assert Decimal(question_one["mark_sum"]) == Decimal("6.00")
    assert Decimal(question_one["mark_average"]) == Decimal("3.0")
    assert Decimal(question_one["mark_minimum"]) == Decimal("2.00")
    assert Decimal(question_one["mark_maximum"]) == Decimal("4.00")

    assert Decimal(question_one["average_percentage"]) == Decimal("60.00")

    assert Decimal(question_one["marking_completion_percentage"]) == Decimal("100.00")


@pytest.mark.asyncio
async def test_question_analysis_completed_only_excludes_provisional_mark(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
):
    context = await _build_results_context(
        db_session,
        teacher_user,
    )

    await _create_response_and_decision(
        db_session,
        script_id=context["script"].id,
        question_id=context["question_one"].id,
        marker_id=teacher_user.id,
        mark_awarded=Decimal("4.00"),
        decision_status=MarkingDecisionStatus.IN_PROGRESS,
    )

    response = await client.get(
        (
            "/api/v1/assessment-results/assessments/"
            f"{context['assessment'].id}/questions"
        ),
        headers=auth_headers(teacher_user),
    )

    assert response.status_code == 200, response.text

    data = response.json()

    assert data["completed_only"] is True

    question_one = next(
        question
        for question in data["questions"]
        if question["question_id"] == context["question_one"].id
    )

    assert question_one["marked_count"] == 0
    assert Decimal(question_one["mark_sum"]) == Decimal("0")
    assert question_one["mark_average"] is None
    assert question_one["average_percentage"] is None


@pytest.mark.asyncio
async def test_question_analysis_can_include_provisional_marks(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
):
    context = await _build_results_context(
        db_session,
        teacher_user,
    )

    await _create_response_and_decision(
        db_session,
        script_id=context["script"].id,
        question_id=context["question_one"].id,
        marker_id=teacher_user.id,
        mark_awarded=Decimal("4.00"),
        decision_status=MarkingDecisionStatus.IN_PROGRESS,
    )

    response = await client.get(
        (
            "/api/v1/assessment-results/assessments/"
            f"{context['assessment'].id}/questions"
        ),
        params={
            "completed_only": "false",
        },
        headers=auth_headers(teacher_user),
    )

    assert response.status_code == 200, response.text

    data = response.json()

    assert data["completed_only"] is False

    question_one = next(
        question
        for question in data["questions"]
        if question["question_id"] == context["question_one"].id
    )

    assert question_one["response_count"] == 1
    assert question_one["marked_count"] == 1

    assert Decimal(question_one["mark_sum"]) == Decimal("4.00")
    assert Decimal(question_one["mark_average"]) == Decimal("4.0")

    assert Decimal(question_one["average_percentage"]) == Decimal("80.00")


# ---------------------------------------------------------------------------
# Access control and school/course isolation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_other_teacher_cannot_view_script_result(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
):
    context = await _build_results_context(
        db_session,
        teacher_user,
    )

    other_teacher = await create_test_user(
        db_session,
        email="results.api.other.teacher@example.com",
        roles=[UserRole.TEACHER],
        school_id=teacher_user.school_id,
    )

    response = await client.get(
        f"/api/v1/assessment-results/scripts/{context['script'].id}",
        headers=auth_headers(other_teacher),
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_other_teacher_cannot_view_candidate_result(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
):
    context = await _build_results_context(
        db_session,
        teacher_user,
    )

    other_teacher = await create_test_user(
        db_session,
        email="results.api.other.candidate.teacher@example.com",
        roles=[UserRole.TEACHER],
        school_id=teacher_user.school_id,
    )

    response = await client.get(
        f"/api/v1/assessment-results/candidates/{context['candidate'].id}",
        headers=auth_headers(other_teacher),
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_other_teacher_cannot_view_assessment_grid(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
):
    context = await _build_results_context(
        db_session,
        teacher_user,
    )

    other_teacher = await create_test_user(
        db_session,
        email="results.api.other.grid.teacher@example.com",
        roles=[UserRole.TEACHER],
        school_id=teacher_user.school_id,
    )

    response = await client.get(
        ("/api/v1/assessment-results/assessments/" f"{context['assessment'].id}/grid"),
        headers=auth_headers(other_teacher),
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_other_teacher_cannot_view_assessment_summary(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
):
    context = await _build_results_context(
        db_session,
        teacher_user,
    )

    other_teacher = await create_test_user(
        db_session,
        email="results.api.other.summary.teacher@example.com",
        roles=[UserRole.TEACHER],
        school_id=teacher_user.school_id,
    )

    response = await client.get(
        (
            "/api/v1/assessment-results/assessments/"
            f"{context['assessment'].id}/summary"
        ),
        headers=auth_headers(other_teacher),
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_school_admin_can_view_assessment_results(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
):
    context = await _build_results_context(
        db_session,
        teacher_user,
    )

    school_admin = await create_test_user(
        db_session,
        email="results.api.school.admin@example.com",
        roles=[UserRole.SCHOOL_ADMIN],
        school_id=teacher_user.school_id,
    )

    response = await client.get(
        (
            "/api/v1/assessment-results/assessments/"
            f"{context['assessment'].id}/summary"
        ),
        headers=auth_headers(school_admin),
    )

    assert response.status_code == 200, response.text

    assert response.json()["assessment_id"] == context["assessment"].id


@pytest.mark.asyncio
async def test_student_cannot_access_assessment_results_api(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
):
    context = await _build_results_context(
        db_session,
        teacher_user,
    )

    student = await create_test_user(
        db_session,
        email="results.api.unauthorised.student@example.com",
        roles=[UserRole.STUDENT],
        school_id=teacher_user.school_id,
    )

    response = await client.get(
        (
            "/api/v1/assessment-results/assessments/"
            f"{context['assessment'].id}/summary"
        ),
        headers=auth_headers(student),
    )

    assert response.status_code == 403
