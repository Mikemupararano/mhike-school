from __future__ import annotations

from decimal import Decimal

import pytest
from fastapi import HTTPException
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
from app.services.assessment_results_service import (
    get_assessment_question_analysis,
    get_assessment_result_grid,
    get_assessment_results_summary,
    get_candidate_result,
    get_script_result,
)
from tests.conftest import create_test_user


async def _create_course(
    db_session: AsyncSession,
    *,
    teacher_id: int,
    school_id: int,
    title: str = "Assessment Results Test Course",
) -> Course:
    course = Course(
        title=title,
        description="Course used by assessment results service tests.",
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
    title: str = "Assessment Results Test",
) -> Assessment:
    assessment = Assessment(
        school_id=school_id,
        course_id=course_id,
        created_by_id=teacher_id,
        title=title,
        description="Assessment results service test.",
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


async def _create_candidate_and_script(
    db_session: AsyncSession,
    *,
    assessment_id: int,
    student_id: int,
    version: int = 1,
    script_status: AssessmentScriptStatus = AssessmentScriptStatus.SUBMITTED,
) -> tuple[AssessmentCandidate, AssessmentScript]:
    candidate = AssessmentCandidate(
        assessment_id=assessment_id,
        student_id=student_id,
        status=AssessmentCandidateStatus.SUBMITTED,
        candidate_number=f"RESULT-{student_id}",
    )

    db_session.add(candidate)
    await db_session.flush()

    script = AssessmentScript(
        candidate_id=candidate.id,
        version=version,
        status=script_status,
        source_type="pdf_upload",
        source_filename=f"result-script-v{version}.pdf",
        mime_type="application/pdf",
    )

    db_session.add(script)
    await db_session.commit()
    await db_session.refresh(candidate)
    await db_session.refresh(script)

    return candidate, script


async def _create_additional_script(
    db_session: AsyncSession,
    *,
    candidate_id: int,
    version: int,
    script_status: AssessmentScriptStatus = AssessmentScriptStatus.SUBMITTED,
) -> AssessmentScript:
    script = AssessmentScript(
        candidate_id=candidate_id,
        version=version,
        status=script_status,
        source_type="pdf_upload",
        source_filename=f"result-script-v{version}.pdf",
        mime_type="application/pdf",
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
        email=f"results.student.{assessment.id}@example.com",
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
        "question_one": question_one,
        "question_two": question_two,
        "student": student,
        "candidate": candidate,
        "script": script,
    }


# ----------------------------------------------------------------------
# Assessment maximum rules
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_script_result_uses_sum_of_markable_question_maxima(
    db_session: AsyncSession,
    teacher_user,
):
    context = await _build_results_context(
        db_session,
        teacher_user,
    )

    result = await get_script_result(
        db=db_session,
        current_user=teacher_user,
        script_id=context["script"].id,
    )

    assert result["maximum_mark"] == Decimal("8.00")
    assert result["markable_question_count"] == 2


@pytest.mark.asyncio
async def test_non_markable_question_is_excluded_from_assessment_maximum(
    db_session: AsyncSession,
    teacher_user,
):
    context = await _build_results_context(
        db_session,
        teacher_user,
    )

    await _create_question(
        db_session,
        assessment_id=context["assessment"].id,
        question_number="3",
        maximum_mark=Decimal("10.00"),
        order=3,
        is_markable=False,
    )

    result = await get_script_result(
        db=db_session,
        current_user=teacher_user,
        script_id=context["script"].id,
    )

    assert result["maximum_mark"] == Decimal("8.00")
    assert result["markable_question_count"] == 2


@pytest.mark.asyncio
async def test_markable_parent_and_child_both_contribute_to_maximum(
    db_session: AsyncSession,
    teacher_user,
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

    result = await get_script_result(
        db=db_session,
        current_user=teacher_user,
        script_id=context["script"].id,
    )

    assert result["maximum_mark"] == Decimal("11.00")
    assert result["markable_question_count"] == 4


# ----------------------------------------------------------------------
# Script totals and percentages
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_script_result_sums_provisional_marks(
    db_session: AsyncSession,
    teacher_user,
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
        decision_status=MarkingDecisionStatus.MARKED,
    )

    result = await get_script_result(
        db=db_session,
        current_user=teacher_user,
        script_id=context["script"].id,
    )

    assert result["mark_awarded"] == Decimal("6.00")
    assert result["percentage"] == Decimal("75.00")


@pytest.mark.asyncio
async def test_completed_mark_total_excludes_in_progress_decision(
    db_session: AsyncSession,
    teacher_user,
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
        decision_status=MarkingDecisionStatus.MARKED,
    )

    result = await get_script_result(
        db=db_session,
        current_user=teacher_user,
        script_id=context["script"].id,
    )

    assert result["completed_mark_awarded"] == Decimal("2.00")
    assert result["completed_percentage"] == Decimal("25.00")


@pytest.mark.asyncio
async def test_finalised_mark_total_counts_only_finalised_decisions(
    db_session: AsyncSession,
    teacher_user,
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
        decision_status=MarkingDecisionStatus.REVIEWED,
    )

    await _create_response_and_decision(
        db_session,
        script_id=context["script"].id,
        question_id=context["question_two"].id,
        marker_id=teacher_user.id,
        mark_awarded=Decimal("2.00"),
        decision_status=MarkingDecisionStatus.FINALISED,
    )

    result = await get_script_result(
        db=db_session,
        current_user=teacher_user,
        script_id=context["script"].id,
    )

    assert result["completed_mark_awarded"] == Decimal("6.00")
    assert result["finalised_mark_awarded"] == Decimal("2.00")
    assert result["finalised_percentage"] == Decimal("25.00")


@pytest.mark.asyncio
async def test_zero_maximum_returns_none_percentage(
    db_session: AsyncSession,
    teacher_user,
):
    course = await _create_course(
        db_session,
        teacher_id=teacher_user.id,
        school_id=teacher_user.school_id,
        title="Zero Maximum Course",
    )

    assessment = await _create_assessment(
        db_session,
        teacher_id=teacher_user.id,
        school_id=teacher_user.school_id,
        course_id=course.id,
        title="Zero Maximum Assessment",
    )

    student = await create_test_user(
        db_session,
        email="results.zero.maximum@example.com",
        roles=[UserRole.STUDENT],
        school_id=teacher_user.school_id,
    )

    _, script = await _create_candidate_and_script(
        db_session,
        assessment_id=assessment.id,
        student_id=student.id,
    )

    result = await get_script_result(
        db=db_session,
        current_user=teacher_user,
        script_id=script.id,
    )

    assert result["maximum_mark"] == Decimal("0")
    assert result["percentage"] is None
    assert result["marking_completion_percentage"] is None


# ----------------------------------------------------------------------
# Completion metrics
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_response_completion_percentage_is_derived_from_markable_questions(
    db_session: AsyncSession,
    teacher_user,
):
    context = await _build_results_context(
        db_session,
        teacher_user,
    )

    response = AssessmentResponse(
        script_id=context["script"].id,
        question_id=context["question_one"].id,
        status=AssessmentResponseStatus.SUBMITTED,
        response_text="Answer",
    )

    db_session.add(response)
    await db_session.commit()

    result = await get_script_result(
        db=db_session,
        current_user=teacher_user,
        script_id=context["script"].id,
    )

    assert result["response_count"] == 1
    assert result["response_completion_percentage"] == Decimal("50.00")
    assert result["is_fully_responded"] is False


@pytest.mark.asyncio
async def test_void_response_is_excluded_from_response_completion(
    db_session: AsyncSession,
    teacher_user,
):
    context = await _build_results_context(
        db_session,
        teacher_user,
    )

    response = AssessmentResponse(
        script_id=context["script"].id,
        question_id=context["question_one"].id,
        status=AssessmentResponseStatus.VOID,
    )

    db_session.add(response)
    await db_session.commit()

    result = await get_script_result(
        db=db_session,
        current_user=teacher_user,
        script_id=context["script"].id,
    )

    assert result["response_count"] == 0
    assert result["response_completion_percentage"] == Decimal("0.00")


@pytest.mark.asyncio
async def test_marking_completion_counts_marked_reviewed_and_finalised(
    db_session: AsyncSession,
    teacher_user,
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

    await _create_response_and_decision(
        db_session,
        script_id=context["script"].id,
        question_id=context["question_two"].id,
        marker_id=teacher_user.id,
        mark_awarded=Decimal("3.00"),
        decision_status=MarkingDecisionStatus.FINALISED,
    )

    result = await get_script_result(
        db=db_session,
        current_user=teacher_user,
        script_id=context["script"].id,
    )

    assert result["marked_question_count"] == 2
    assert result["marking_completion_percentage"] == Decimal("100.00")
    assert result["is_fully_marked"] is True


@pytest.mark.asyncio
async def test_finalisation_completion_counts_only_finalised(
    db_session: AsyncSession,
    teacher_user,
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
        decision_status=MarkingDecisionStatus.REVIEWED,
    )

    await _create_response_and_decision(
        db_session,
        script_id=context["script"].id,
        question_id=context["question_two"].id,
        marker_id=teacher_user.id,
        mark_awarded=Decimal("3.00"),
        decision_status=MarkingDecisionStatus.FINALISED,
    )

    result = await get_script_result(
        db=db_session,
        current_user=teacher_user,
        script_id=context["script"].id,
    )

    assert result["finalised_question_count"] == 1
    assert result["finalisation_completion_percentage"] == Decimal("50.00")
    assert result["is_fully_finalised"] is False


# ----------------------------------------------------------------------
# Question-level results
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_script_result_includes_unanswered_markable_questions(
    db_session: AsyncSession,
    teacher_user,
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

    result = await get_script_result(
        db=db_session,
        current_user=teacher_user,
        script_id=context["script"].id,
    )

    assert len(result["questions"]) == 2

    first = result["questions"][0]
    second = result["questions"][1]

    assert first["question_id"] == context["question_one"].id
    assert first["mark_awarded"] == Decimal("4.00")

    assert second["question_id"] == context["question_two"].id
    assert second["response_id"] is None
    assert second["decision_id"] is None
    assert second["mark_awarded"] is None


@pytest.mark.asyncio
async def test_question_result_percentage_uses_question_maximum(
    db_session: AsyncSession,
    teacher_user,
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
        mark_awarded=Decimal("2.50"),
        decision_status=MarkingDecisionStatus.MARKED,
    )

    result = await get_script_result(
        db=db_session,
        current_user=teacher_user,
        script_id=context["script"].id,
    )

    question_result = next(
        row
        for row in result["questions"]
        if row["question_id"] == context["question_one"].id
    )

    assert question_result["percentage"] == Decimal("50.00")


# ----------------------------------------------------------------------
# Candidate result and version history
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_candidate_result_reports_all_script_versions(
    db_session: AsyncSession,
    teacher_user,
):
    context = await _build_results_context(
        db_session,
        teacher_user,
    )

    second_script = await _create_additional_script(
        db_session,
        candidate_id=context["candidate"].id,
        version=2,
    )

    result = await get_candidate_result(
        db=db_session,
        current_user=teacher_user,
        candidate_id=context["candidate"].id,
    )

    assert result["script_count"] == 2
    assert [row["script_version"] for row in result["scripts"]] == [1, 2]
    assert result["latest_script_result"]["script_id"] == second_script.id


@pytest.mark.asyncio
async def test_candidate_without_scripts_returns_no_latest_result(
    db_session: AsyncSession,
    teacher_user,
):
    course = await _create_course(
        db_session,
        teacher_id=teacher_user.id,
        school_id=teacher_user.school_id,
        title="No Script Course",
    )

    assessment = await _create_assessment(
        db_session,
        teacher_id=teacher_user.id,
        school_id=teacher_user.school_id,
        course_id=course.id,
        title="No Script Assessment",
    )

    student = await create_test_user(
        db_session,
        email="results.no.script@example.com",
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

    result = await get_candidate_result(
        db=db_session,
        current_user=teacher_user,
        candidate_id=candidate.id,
    )

    assert result["script_count"] == 0
    assert result["scripts"] == []
    assert result["latest_script_result"] is None


# ----------------------------------------------------------------------
# Assessment result grid
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_assessment_result_grid_returns_script_totals(
    db_session: AsyncSession,
    teacher_user,
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

    grid = await get_assessment_result_grid(
        db=db_session,
        current_user=teacher_user,
        assessment_id=context["assessment"].id,
    )

    assert grid["assessment_id"] == context["assessment"].id
    assert grid["maximum_mark"] == Decimal("8.00")
    assert grid["markable_question_count"] == 2
    assert grid["script_count"] == 1

    row = grid["scripts"][0]

    assert row["script_id"] == context["script"].id
    assert row["mark_awarded"] == Decimal("4.00")
    assert row["percentage"] == Decimal("50.00")
    assert row["completed_decision_count"] == 1
    assert row["marking_completion_percentage"] == Decimal("50.00")


@pytest.mark.asyncio
async def test_assessment_result_grid_preserves_multiple_versions(
    db_session: AsyncSession,
    teacher_user,
):
    context = await _build_results_context(
        db_session,
        teacher_user,
    )

    await _create_additional_script(
        db_session,
        candidate_id=context["candidate"].id,
        version=2,
    )

    grid = await get_assessment_result_grid(
        db=db_session,
        current_user=teacher_user,
        assessment_id=context["assessment"].id,
    )

    assert grid["script_count"] == 2
    assert [row["version"] for row in grid["scripts"]] == [1, 2]


# ----------------------------------------------------------------------
# Assessment-wide summary
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_assessment_summary_reports_counts_and_totals(
    db_session: AsyncSession,
    teacher_user,
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

    summary = await get_assessment_results_summary(
        db=db_session,
        current_user=teacher_user,
        assessment_id=context["assessment"].id,
    )

    assert summary["maximum_mark"] == Decimal("8.00")
    assert summary["markable_question_count"] == 2
    assert summary["candidate_count"] == 1
    assert summary["script_count"] == 1
    assert summary["expected_question_decisions"] == 2
    assert summary["completed_decision_count"] == 2
    assert summary["finalised_decision_count"] == 1
    assert summary["marking_completion_percentage"] == Decimal("100.00")
    assert summary["finalisation_completion_percentage"] == Decimal("50.00")
    assert summary["total_awarded_marks"] == Decimal("6.00")
    assert summary["completed_awarded_marks"] == Decimal("6.00")
    assert summary["finalised_awarded_marks"] == Decimal("2.00")


# ----------------------------------------------------------------------
# Question-level analysis
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_question_analysis_reports_average_and_percentage(
    db_session: AsyncSession,
    teacher_user,
):
    context = await _build_results_context(
        db_session,
        teacher_user,
    )

    second_student = await create_test_user(
        db_session,
        email="results.analysis.second.student@example.com",
        roles=[UserRole.STUDENT],
        school_id=teacher_user.school_id,
    )

    _, second_script = await _create_candidate_and_script(
        db_session,
        assessment_id=context["assessment"].id,
        student_id=second_student.id,
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

    analysis = await get_assessment_question_analysis(
        db=db_session,
        current_user=teacher_user,
        assessment_id=context["assessment"].id,
    )

    question_one = next(
        row for row in analysis if row["question_id"] == context["question_one"].id
    )

    assert question_one["response_count"] == 2
    assert question_one["marked_count"] == 2
    assert question_one["mark_sum"] == Decimal("6.00")
    assert question_one["mark_average"] == Decimal("3.0")
    assert question_one["mark_minimum"] == Decimal("2.00")
    assert question_one["mark_maximum"] == Decimal("4.00")
    assert question_one["average_percentage"] == Decimal("60.00")
    assert question_one["marking_completion_percentage"] == Decimal("100.00")


@pytest.mark.asyncio
async def test_question_analysis_completed_only_excludes_in_progress_marks(
    db_session: AsyncSession,
    teacher_user,
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

    analysis = await get_assessment_question_analysis(
        db=db_session,
        current_user=teacher_user,
        assessment_id=context["assessment"].id,
        completed_only=True,
    )

    question_one = next(
        row for row in analysis if row["question_id"] == context["question_one"].id
    )

    assert question_one["marked_count"] == 0
    assert question_one["mark_sum"] == Decimal("0")
    assert question_one["mark_average"] is None


@pytest.mark.asyncio
async def test_question_analysis_can_include_provisional_marks(
    db_session: AsyncSession,
    teacher_user,
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

    analysis = await get_assessment_question_analysis(
        db=db_session,
        current_user=teacher_user,
        assessment_id=context["assessment"].id,
        completed_only=False,
    )

    question_one = next(
        row for row in analysis if row["question_id"] == context["question_one"].id
    )

    assert question_one["marked_count"] == 1
    assert question_one["mark_sum"] == Decimal("4.00")
    assert question_one["mark_average"] == Decimal("4.0")
    assert question_one["average_percentage"] == Decimal("80.00")


# ----------------------------------------------------------------------
# Access control
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_other_teacher_cannot_view_script_result(
    db_session: AsyncSession,
    teacher_user,
):
    context = await _build_results_context(
        db_session,
        teacher_user,
    )

    other_teacher = await create_test_user(
        db_session,
        email="results.other.teacher@example.com",
        roles=[UserRole.TEACHER],
        school_id=teacher_user.school_id,
    )

    with pytest.raises(HTTPException) as exc:
        await get_script_result(
            db=db_session,
            current_user=other_teacher,
            script_id=context["script"].id,
        )

    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_other_teacher_cannot_view_assessment_result_grid(
    db_session: AsyncSession,
    teacher_user,
):
    context = await _build_results_context(
        db_session,
        teacher_user,
    )

    other_teacher = await create_test_user(
        db_session,
        email="results.grid.other.teacher@example.com",
        roles=[UserRole.TEACHER],
        school_id=teacher_user.school_id,
    )

    with pytest.raises(HTTPException) as exc:
        await get_assessment_result_grid(
            db=db_session,
            current_user=other_teacher,
            assessment_id=context["assessment"].id,
        )

    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_school_admin_can_view_assessment_results(
    db_session: AsyncSession,
    teacher_user,
):
    context = await _build_results_context(
        db_session,
        teacher_user,
    )

    school_admin = await create_test_user(
        db_session,
        email="results.school.admin@example.com",
        roles=[UserRole.SCHOOL_ADMIN],
        school_id=teacher_user.school_id,
    )

    summary = await get_assessment_results_summary(
        db=db_session,
        current_user=school_admin,
        assessment_id=context["assessment"].id,
    )

    assert summary["assessment_id"] == context["assessment"].id


@pytest.mark.asyncio
async def test_student_cannot_view_staff_results_service(
    db_session: AsyncSession,
    teacher_user,
):
    context = await _build_results_context(
        db_session,
        teacher_user,
    )

    student = await create_test_user(
        db_session,
        email="results.unauthorised.student@example.com",
        roles=[UserRole.STUDENT],
        school_id=teacher_user.school_id,
    )

    with pytest.raises(HTTPException) as exc:
        await get_assessment_results_summary(
            db=db_session,
            current_user=student,
            assessment_id=context["assessment"].id,
        )

    assert exc.value.status_code == 403
