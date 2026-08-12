from __future__ import annotations

from decimal import Decimal

import pytest
from fastapi import HTTPException
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
from app.models.assessment_grading import (
    AssessmentGradingBasis,
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
from app.services.assessment_grading_service import (
    create_grade_boundary,
    create_grading_scheme,
    delete_grade_boundary,
    delete_grading_scheme,
    get_grading_scheme,
    grade_candidate_latest_result,
    grade_script_result,
    list_grade_boundaries,
    resolve_grade,
    update_grade_boundary,
    update_grading_scheme,
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
    title: str = "Assessment Grading Test Course",
) -> Course:
    """
    Create and persist a teacher-owned course.
    """

    course = Course(
        title=title,
        description="Course used by assessment grading service tests.",
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
    title: str = "Assessment Grading Test",
) -> Assessment:
    """
    Create and persist one assessment.
    """

    assessment = Assessment(
        school_id=school_id,
        course_id=course_id,
        created_by_id=teacher_id,
        title=title,
        description="Assessment grading service test.",
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
) -> AssessmentQuestion:
    """
    Create and persist one assessment question.
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


async def _create_candidate(
    db_session: AsyncSession,
    *,
    assessment_id: int,
    student_id: int,
    candidate_number: str,
) -> AssessmentCandidate:
    """
    Create and persist one assessment candidate.
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
    Create and persist one script version.
    """

    script = AssessmentScript(
        candidate_id=candidate_id,
        version=version,
        status=script_status,
        source_type="pdf_upload",
        source_filename=f"grading-script-v{version}.pdf",
        storage_key=f"assessment-grading/grading-script-v{version}.pdf",
        mime_type="application/pdf",
        checksum=f"grading-{candidate_id}-{version}",
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
) -> tuple[AssessmentResponse, MarkingDecision]:
    """
    Create a submitted response and authoritative marking decision.
    """

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


async def _build_grading_context(
    db_session: AsyncSession,
    teacher_user,
):
    """
    Build a complete grading context with an eight-mark assessment.
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
        email=f"grading.student.{assessment.id}@example.com",
        roles=[UserRole.STUDENT],
        school_id=teacher_user.school_id,
    )

    candidate = await _create_candidate(
        db_session,
        assessment_id=assessment.id,
        student_id=student.id,
        candidate_number="GRADE-001",
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


async def _create_percentage_scheme(
    db_session: AsyncSession,
    teacher_user,
    *,
    assessment_id: int,
):
    """
    Create a percentage grading scheme.
    """

    return await create_grading_scheme(
        db=db_session,
        current_user=teacher_user,
        assessment_id=assessment_id,
        name="GCSE 9-1",
        basis=AssessmentGradingBasis.PERCENTAGE,
        description="Percentage grading scheme.",
    )


async def _create_percentage_boundaries(
    db_session: AsyncSession,
    teacher_user,
    *,
    scheme_id: int,
):
    """
    Create representative percentage grade boundaries.
    """

    grade_9 = await create_grade_boundary(
        db=db_session,
        current_user=teacher_user,
        scheme_id=scheme_id,
        grade_label="9",
        minimum_value=Decimal("80.00"),
        order=1,
        grade_points=Decimal("9.00"),
        is_pass=True,
    )

    grade_8 = await create_grade_boundary(
        db=db_session,
        current_user=teacher_user,
        scheme_id=scheme_id,
        grade_label="8",
        minimum_value=Decimal("70.00"),
        order=2,
        grade_points=Decimal("8.00"),
        is_pass=True,
    )

    grade_7 = await create_grade_boundary(
        db=db_session,
        current_user=teacher_user,
        scheme_id=scheme_id,
        grade_label="7",
        minimum_value=Decimal("60.00"),
        order=3,
        grade_points=Decimal("7.00"),
        is_pass=True,
    )

    return grade_9, grade_8, grade_7


# ---------------------------------------------------------------------------
# Scheme creation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_teacher_can_create_percentage_grading_scheme(
    db_session: AsyncSession,
    teacher_user,
):
    context = await _build_grading_context(
        db_session,
        teacher_user,
    )

    scheme = await create_grading_scheme(
        db=db_session,
        current_user=teacher_user,
        assessment_id=context["assessment"].id,
        name=" GCSE 9-1 ",
        basis=AssessmentGradingBasis.PERCENTAGE,
        description=" Percentage boundaries ",
    )

    assert scheme.id is not None
    assert scheme.assessment_id == context["assessment"].id
    assert scheme.name == "GCSE 9-1"
    assert scheme.description == "Percentage boundaries"
    assert scheme.basis == AssessmentGradingBasis.PERCENTAGE
    assert scheme.is_active is True
    assert scheme.created_by_id == teacher_user.id
    assert scheme.boundaries == []


@pytest.mark.asyncio
async def test_teacher_can_create_raw_mark_grading_scheme(
    db_session: AsyncSession,
    teacher_user,
):
    context = await _build_grading_context(
        db_session,
        teacher_user,
    )

    scheme = await create_grading_scheme(
        db=db_session,
        current_user=teacher_user,
        assessment_id=context["assessment"].id,
        name="Raw mark scheme",
        basis=AssessmentGradingBasis.RAW_MARK,
    )

    assert scheme.basis == AssessmentGradingBasis.RAW_MARK


@pytest.mark.asyncio
async def test_raw_mark_scheme_requires_positive_assessment_maximum(
    db_session: AsyncSession,
    teacher_user,
):
    course = await _create_course(
        db_session,
        teacher_id=teacher_user.id,
        school_id=teacher_user.school_id,
        title="Zero Maximum Grading Course",
    )

    assessment = await _create_assessment(
        db_session,
        teacher_id=teacher_user.id,
        school_id=teacher_user.school_id,
        course_id=course.id,
        title="Zero Maximum Grading Assessment",
    )

    with pytest.raises(HTTPException) as exc:
        await create_grading_scheme(
            db=db_session,
            current_user=teacher_user,
            assessment_id=assessment.id,
            name="Raw Mark",
            basis=AssessmentGradingBasis.RAW_MARK,
        )

    assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_duplicate_scheme_for_assessment_is_rejected(
    db_session: AsyncSession,
    teacher_user,
):
    context = await _build_grading_context(
        db_session,
        teacher_user,
    )

    await _create_percentage_scheme(
        db_session,
        teacher_user,
        assessment_id=context["assessment"].id,
    )

    with pytest.raises(HTTPException) as exc:
        await create_grading_scheme(
            db=db_session,
            current_user=teacher_user,
            assessment_id=context["assessment"].id,
            name="Second Scheme",
            basis=AssessmentGradingBasis.PERCENTAGE,
        )

    assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_blank_scheme_name_is_rejected(
    db_session: AsyncSession,
    teacher_user,
):
    context = await _build_grading_context(
        db_session,
        teacher_user,
    )

    with pytest.raises(HTTPException) as exc:
        await create_grading_scheme(
            db=db_session,
            current_user=teacher_user,
            assessment_id=context["assessment"].id,
            name="   ",
            basis=AssessmentGradingBasis.PERCENTAGE,
        )

    assert exc.value.status_code == 422


# ---------------------------------------------------------------------------
# Scheme retrieval and update
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_teacher_can_get_grading_scheme(
    db_session: AsyncSession,
    teacher_user,
):
    context = await _build_grading_context(
        db_session,
        teacher_user,
    )

    created = await _create_percentage_scheme(
        db_session,
        teacher_user,
        assessment_id=context["assessment"].id,
    )

    scheme = await get_grading_scheme(
        db=db_session,
        current_user=teacher_user,
        assessment_id=context["assessment"].id,
    )

    assert scheme.id == created.id


@pytest.mark.asyncio
async def test_teacher_can_update_grading_scheme(
    db_session: AsyncSession,
    teacher_user,
):
    context = await _build_grading_context(
        db_session,
        teacher_user,
    )

    scheme = await _create_percentage_scheme(
        db_session,
        teacher_user,
        assessment_id=context["assessment"].id,
    )

    updated = await update_grading_scheme(
        db=db_session,
        current_user=teacher_user,
        scheme_id=scheme.id,
        name="Updated Scheme",
        description="Updated description",
        is_active=False,
    )

    assert updated.name == "Updated Scheme"
    assert updated.description == "Updated description"
    assert updated.is_active is False


@pytest.mark.asyncio
async def test_scheme_description_can_be_cleared(
    db_session: AsyncSession,
    teacher_user,
):
    context = await _build_grading_context(
        db_session,
        teacher_user,
    )

    scheme = await create_grading_scheme(
        db=db_session,
        current_user=teacher_user,
        assessment_id=context["assessment"].id,
        name="Scheme",
        basis=AssessmentGradingBasis.PERCENTAGE,
        description="Description",
    )

    updated = await update_grading_scheme(
        db=db_session,
        current_user=teacher_user,
        scheme_id=scheme.id,
        description=None,
    )

    assert updated.description is None


# ---------------------------------------------------------------------------
# Boundary creation and validation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_teacher_can_create_percentage_boundary(
    db_session: AsyncSession,
    teacher_user,
):
    context = await _build_grading_context(
        db_session,
        teacher_user,
    )

    scheme = await _create_percentage_scheme(
        db_session,
        teacher_user,
        assessment_id=context["assessment"].id,
    )

    boundary = await create_grade_boundary(
        db=db_session,
        current_user=teacher_user,
        scheme_id=scheme.id,
        grade_label=" 9 ",
        minimum_value="80",
        order=1,
        description=" Highest grade ",
        grade_points="9",
        is_pass=True,
    )

    assert boundary.grade_label == "9"
    assert boundary.minimum_value == Decimal("80.0000")
    assert boundary.order == 1
    assert boundary.description == "Highest grade"
    assert boundary.grade_points == Decimal("9.00")
    assert boundary.is_pass is True


@pytest.mark.asyncio
async def test_percentage_boundary_above_100_is_rejected(
    db_session: AsyncSession,
    teacher_user,
):
    context = await _build_grading_context(
        db_session,
        teacher_user,
    )

    scheme = await _create_percentage_scheme(
        db_session,
        teacher_user,
        assessment_id=context["assessment"].id,
    )

    with pytest.raises(HTTPException) as exc:
        await create_grade_boundary(
            db=db_session,
            current_user=teacher_user,
            scheme_id=scheme.id,
            grade_label="Invalid",
            minimum_value=Decimal("101"),
            order=1,
        )

    assert exc.value.status_code == 422


@pytest.mark.asyncio
async def test_negative_boundary_is_rejected(
    db_session: AsyncSession,
    teacher_user,
):
    context = await _build_grading_context(
        db_session,
        teacher_user,
    )

    scheme = await _create_percentage_scheme(
        db_session,
        teacher_user,
        assessment_id=context["assessment"].id,
    )

    with pytest.raises(HTTPException) as exc:
        await create_grade_boundary(
            db=db_session,
            current_user=teacher_user,
            scheme_id=scheme.id,
            grade_label="Invalid",
            minimum_value=Decimal("-1"),
            order=1,
        )

    assert exc.value.status_code == 422


@pytest.mark.asyncio
async def test_raw_mark_boundary_cannot_exceed_assessment_maximum(
    db_session: AsyncSession,
    teacher_user,
):
    context = await _build_grading_context(
        db_session,
        teacher_user,
    )

    scheme = await create_grading_scheme(
        db=db_session,
        current_user=teacher_user,
        assessment_id=context["assessment"].id,
        name="Raw Marks",
        basis=AssessmentGradingBasis.RAW_MARK,
    )

    with pytest.raises(HTTPException) as exc:
        await create_grade_boundary(
            db=db_session,
            current_user=teacher_user,
            scheme_id=scheme.id,
            grade_label="A*",
            minimum_value=Decimal("9"),
            order=1,
        )

    assert exc.value.status_code == 422


@pytest.mark.asyncio
async def test_raw_mark_boundary_can_equal_assessment_maximum(
    db_session: AsyncSession,
    teacher_user,
):
    context = await _build_grading_context(
        db_session,
        teacher_user,
    )

    scheme = await create_grading_scheme(
        db=db_session,
        current_user=teacher_user,
        assessment_id=context["assessment"].id,
        name="Raw Marks",
        basis=AssessmentGradingBasis.RAW_MARK,
    )

    boundary = await create_grade_boundary(
        db=db_session,
        current_user=teacher_user,
        scheme_id=scheme.id,
        grade_label="Full Marks",
        minimum_value=Decimal("8"),
        order=1,
    )

    assert boundary.minimum_value == Decimal("8.0000")


@pytest.mark.asyncio
async def test_duplicate_boundary_label_is_rejected(
    db_session: AsyncSession,
    teacher_user,
):
    context = await _build_grading_context(
        db_session,
        teacher_user,
    )

    scheme = await _create_percentage_scheme(
        db_session,
        teacher_user,
        assessment_id=context["assessment"].id,
    )

    await create_grade_boundary(
        db=db_session,
        current_user=teacher_user,
        scheme_id=scheme.id,
        grade_label="9",
        minimum_value=Decimal("80"),
        order=1,
    )

    with pytest.raises(HTTPException) as exc:
        await create_grade_boundary(
            db=db_session,
            current_user=teacher_user,
            scheme_id=scheme.id,
            grade_label="9",
            minimum_value=Decimal("70"),
            order=2,
        )

    assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_duplicate_boundary_minimum_is_rejected(
    db_session: AsyncSession,
    teacher_user,
):
    context = await _build_grading_context(
        db_session,
        teacher_user,
    )

    scheme = await _create_percentage_scheme(
        db_session,
        teacher_user,
        assessment_id=context["assessment"].id,
    )

    await create_grade_boundary(
        db=db_session,
        current_user=teacher_user,
        scheme_id=scheme.id,
        grade_label="9",
        minimum_value=Decimal("80"),
        order=1,
    )

    with pytest.raises(HTTPException) as exc:
        await create_grade_boundary(
            db=db_session,
            current_user=teacher_user,
            scheme_id=scheme.id,
            grade_label="8",
            minimum_value=Decimal("80"),
            order=2,
        )

    assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_duplicate_boundary_order_is_rejected(
    db_session: AsyncSession,
    teacher_user,
):
    context = await _build_grading_context(
        db_session,
        teacher_user,
    )

    scheme = await _create_percentage_scheme(
        db_session,
        teacher_user,
        assessment_id=context["assessment"].id,
    )

    await create_grade_boundary(
        db=db_session,
        current_user=teacher_user,
        scheme_id=scheme.id,
        grade_label="9",
        minimum_value=Decimal("80"),
        order=1,
    )

    with pytest.raises(HTTPException) as exc:
        await create_grade_boundary(
            db=db_session,
            current_user=teacher_user,
            scheme_id=scheme.id,
            grade_label="8",
            minimum_value=Decimal("70"),
            order=1,
        )

    assert exc.value.status_code == 409


# ---------------------------------------------------------------------------
# Boundary listing and update
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_boundaries_are_listed_highest_threshold_first(
    db_session: AsyncSession,
    teacher_user,
):
    context = await _build_grading_context(
        db_session,
        teacher_user,
    )

    scheme = await _create_percentage_scheme(
        db_session,
        teacher_user,
        assessment_id=context["assessment"].id,
    )

    await _create_percentage_boundaries(
        db_session,
        teacher_user,
        scheme_id=scheme.id,
    )

    boundaries = await list_grade_boundaries(
        db=db_session,
        current_user=teacher_user,
        scheme_id=scheme.id,
    )

    assert [boundary.grade_label for boundary in boundaries] == [
        "9",
        "8",
        "7",
    ]


@pytest.mark.asyncio
async def test_teacher_can_update_boundary(
    db_session: AsyncSession,
    teacher_user,
):
    context = await _build_grading_context(
        db_session,
        teacher_user,
    )

    scheme = await _create_percentage_scheme(
        db_session,
        teacher_user,
        assessment_id=context["assessment"].id,
    )

    boundary = await create_grade_boundary(
        db=db_session,
        current_user=teacher_user,
        scheme_id=scheme.id,
        grade_label="9",
        minimum_value=Decimal("80"),
        order=1,
        grade_points=Decimal("9"),
        is_pass=True,
    )

    updated = await update_grade_boundary(
        db=db_session,
        current_user=teacher_user,
        boundary_id=boundary.id,
        grade_label="9*",
        minimum_value=Decimal("85"),
        description="Exceptional performance",
        grade_points=Decimal("10"),
        is_pass=False,
    )

    assert updated.grade_label == "9*"
    assert updated.minimum_value == Decimal("85.0000")
    assert updated.description == "Exceptional performance"
    assert updated.grade_points == Decimal("10.00")
    assert updated.is_pass is False


@pytest.mark.asyncio
async def test_nullable_boundary_metadata_can_be_cleared(
    db_session: AsyncSession,
    teacher_user,
):
    context = await _build_grading_context(
        db_session,
        teacher_user,
    )

    scheme = await _create_percentage_scheme(
        db_session,
        teacher_user,
        assessment_id=context["assessment"].id,
    )

    boundary = await create_grade_boundary(
        db=db_session,
        current_user=teacher_user,
        scheme_id=scheme.id,
        grade_label="9",
        minimum_value=Decimal("80"),
        order=1,
        description="Description",
        grade_points=Decimal("9"),
        is_pass=True,
    )

    updated = await update_grade_boundary(
        db=db_session,
        current_user=teacher_user,
        boundary_id=boundary.id,
        description=None,
        grade_points=None,
        is_pass=None,
    )

    assert updated.description is None
    assert updated.grade_points is None
    assert updated.is_pass is None


# ---------------------------------------------------------------------------
# Basis changes
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_scheme_basis_can_change_when_boundaries_remain_valid(
    db_session: AsyncSession,
    teacher_user,
):
    context = await _build_grading_context(
        db_session,
        teacher_user,
    )

    scheme = await _create_percentage_scheme(
        db_session,
        teacher_user,
        assessment_id=context["assessment"].id,
    )

    await create_grade_boundary(
        db=db_session,
        current_user=teacher_user,
        scheme_id=scheme.id,
        grade_label="Pass",
        minimum_value=Decimal("5"),
        order=1,
    )

    updated = await update_grading_scheme(
        db=db_session,
        current_user=teacher_user,
        scheme_id=scheme.id,
        basis=AssessmentGradingBasis.RAW_MARK,
    )

    assert updated.basis == AssessmentGradingBasis.RAW_MARK


@pytest.mark.asyncio
async def test_scheme_basis_change_is_rejected_when_boundary_exceeds_raw_maximum(
    db_session: AsyncSession,
    teacher_user,
):
    context = await _build_grading_context(
        db_session,
        teacher_user,
    )

    scheme = await _create_percentage_scheme(
        db_session,
        teacher_user,
        assessment_id=context["assessment"].id,
    )

    await create_grade_boundary(
        db=db_session,
        current_user=teacher_user,
        scheme_id=scheme.id,
        grade_label="9",
        minimum_value=Decimal("80"),
        order=1,
    )

    with pytest.raises(HTTPException) as exc:
        await update_grading_scheme(
            db=db_session,
            current_user=teacher_user,
            scheme_id=scheme.id,
            basis=AssessmentGradingBasis.RAW_MARK,
        )

    assert exc.value.status_code == 422


# ---------------------------------------------------------------------------
# Explicit grade resolution
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_percentage_boundary_is_inclusive(
    db_session: AsyncSession,
    teacher_user,
):
    context = await _build_grading_context(
        db_session,
        teacher_user,
    )

    scheme = await _create_percentage_scheme(
        db_session,
        teacher_user,
        assessment_id=context["assessment"].id,
    )

    await _create_percentage_boundaries(
        db_session,
        teacher_user,
        scheme_id=scheme.id,
    )

    result = await resolve_grade(
        db=db_session,
        current_user=teacher_user,
        assessment_id=context["assessment"].id,
        value=Decimal("70"),
    )

    assert result["grade"] == "8"
    assert result["minimum_value"] == Decimal("70.0000")
    assert result["grade_points"] == Decimal("8.00")
    assert result["is_pass"] is True


@pytest.mark.asyncio
async def test_grade_resolution_uses_highest_matching_boundary(
    db_session: AsyncSession,
    teacher_user,
):
    context = await _build_grading_context(
        db_session,
        teacher_user,
    )

    scheme = await _create_percentage_scheme(
        db_session,
        teacher_user,
        assessment_id=context["assessment"].id,
    )

    await _create_percentage_boundaries(
        db_session,
        teacher_user,
        scheme_id=scheme.id,
    )

    result = await resolve_grade(
        db=db_session,
        current_user=teacher_user,
        assessment_id=context["assessment"].id,
        value=Decimal("88"),
    )

    assert result["grade"] == "9"


@pytest.mark.asyncio
async def test_value_below_all_boundaries_returns_no_grade(
    db_session: AsyncSession,
    teacher_user,
):
    context = await _build_grading_context(
        db_session,
        teacher_user,
    )

    scheme = await _create_percentage_scheme(
        db_session,
        teacher_user,
        assessment_id=context["assessment"].id,
    )

    await _create_percentage_boundaries(
        db_session,
        teacher_user,
        scheme_id=scheme.id,
    )

    result = await resolve_grade(
        db=db_session,
        current_user=teacher_user,
        assessment_id=context["assessment"].id,
        value=Decimal("40"),
    )

    assert result["grade"] is None
    assert result["boundary_id"] is None


@pytest.mark.asyncio
async def test_percentage_resolution_above_100_is_rejected(
    db_session: AsyncSession,
    teacher_user,
):
    context = await _build_grading_context(
        db_session,
        teacher_user,
    )

    await _create_percentage_scheme(
        db_session,
        teacher_user,
        assessment_id=context["assessment"].id,
    )

    with pytest.raises(HTTPException) as exc:
        await resolve_grade(
            db=db_session,
            current_user=teacher_user,
            assessment_id=context["assessment"].id,
            value=Decimal("101"),
        )

    assert exc.value.status_code == 422


@pytest.mark.asyncio
async def test_inactive_scheme_cannot_be_used_for_grade_resolution(
    db_session: AsyncSession,
    teacher_user,
):
    context = await _build_grading_context(
        db_session,
        teacher_user,
    )

    scheme = await _create_percentage_scheme(
        db_session,
        teacher_user,
        assessment_id=context["assessment"].id,
    )

    await update_grading_scheme(
        db=db_session,
        current_user=teacher_user,
        scheme_id=scheme.id,
        is_active=False,
    )

    with pytest.raises(HTTPException) as exc:
        await resolve_grade(
            db=db_session,
            current_user=teacher_user,
            assessment_id=context["assessment"].id,
            value=Decimal("80"),
        )

    assert exc.value.status_code == 404


# ---------------------------------------------------------------------------
# Grading derived script results
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_script_can_be_graded_from_completed_percentage(
    db_session: AsyncSession,
    teacher_user,
):
    context = await _build_grading_context(
        db_session,
        teacher_user,
    )

    scheme = await _create_percentage_scheme(
        db_session,
        teacher_user,
        assessment_id=context["assessment"].id,
    )

    await _create_percentage_boundaries(
        db_session,
        teacher_user,
        scheme_id=scheme.id,
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

    result = await grade_script_result(
        db=db_session,
        current_user=teacher_user,
        script_id=context["script"].id,
        result_stage="completed",
    )

    assert result["assessment_id"] == context["assessment"].id
    assert result["script_id"] == context["script"].id
    assert result["result_stage"] == "completed"
    assert result["basis"] == AssessmentGradingBasis.PERCENTAGE

    assert result["value"] == Decimal("75.00")
    assert result["grade"] == "8"


@pytest.mark.asyncio
async def test_script_can_be_graded_from_raw_mark(
    db_session: AsyncSession,
    teacher_user,
):
    context = await _build_grading_context(
        db_session,
        teacher_user,
    )

    scheme = await create_grading_scheme(
        db=db_session,
        current_user=teacher_user,
        assessment_id=context["assessment"].id,
        name="Raw Mark Grades",
        basis=AssessmentGradingBasis.RAW_MARK,
    )

    await create_grade_boundary(
        db=db_session,
        current_user=teacher_user,
        scheme_id=scheme.id,
        grade_label="A",
        minimum_value=Decimal("6"),
        order=1,
    )

    await create_grade_boundary(
        db=db_session,
        current_user=teacher_user,
        scheme_id=scheme.id,
        grade_label="B",
        minimum_value=Decimal("4"),
        order=2,
    )

    await _create_response_and_decision(
        db_session,
        script_id=context["script"].id,
        question_id=context["question_one"].id,
        marker_id=teacher_user.id,
        mark_awarded=Decimal("4"),
        decision_status=MarkingDecisionStatus.FINALISED,
    )

    await _create_response_and_decision(
        db_session,
        script_id=context["script"].id,
        question_id=context["question_two"].id,
        marker_id=teacher_user.id,
        mark_awarded=Decimal("2"),
        decision_status=MarkingDecisionStatus.FINALISED,
    )

    result = await grade_script_result(
        db=db_session,
        current_user=teacher_user,
        script_id=context["script"].id,
        result_stage="finalised",
    )

    assert result["value"] == Decimal("6")
    assert result["grade"] == "A"


@pytest.mark.asyncio
async def test_current_stage_includes_provisional_mark(
    db_session: AsyncSession,
    teacher_user,
):
    context = await _build_grading_context(
        db_session,
        teacher_user,
    )

    scheme = await _create_percentage_scheme(
        db_session,
        teacher_user,
        assessment_id=context["assessment"].id,
    )

    await _create_percentage_boundaries(
        db_session,
        teacher_user,
        scheme_id=scheme.id,
    )

    await _create_response_and_decision(
        db_session,
        script_id=context["script"].id,
        question_id=context["question_one"].id,
        marker_id=teacher_user.id,
        mark_awarded=Decimal("4"),
        decision_status=MarkingDecisionStatus.IN_PROGRESS,
    )

    await _create_response_and_decision(
        db_session,
        script_id=context["script"].id,
        question_id=context["question_two"].id,
        marker_id=teacher_user.id,
        mark_awarded=Decimal("2"),
        decision_status=MarkingDecisionStatus.MARKED,
    )

    result = await grade_script_result(
        db=db_session,
        current_user=teacher_user,
        script_id=context["script"].id,
        result_stage="current",
    )

    assert result["value"] == Decimal("75.00")
    assert result["grade"] == "8"


@pytest.mark.asyncio
async def test_completed_stage_excludes_in_progress_mark(
    db_session: AsyncSession,
    teacher_user,
):
    context = await _build_grading_context(
        db_session,
        teacher_user,
    )

    scheme = await _create_percentage_scheme(
        db_session,
        teacher_user,
        assessment_id=context["assessment"].id,
    )

    await _create_percentage_boundaries(
        db_session,
        teacher_user,
        scheme_id=scheme.id,
    )

    await _create_response_and_decision(
        db_session,
        script_id=context["script"].id,
        question_id=context["question_one"].id,
        marker_id=teacher_user.id,
        mark_awarded=Decimal("4"),
        decision_status=MarkingDecisionStatus.IN_PROGRESS,
    )

    await _create_response_and_decision(
        db_session,
        script_id=context["script"].id,
        question_id=context["question_two"].id,
        marker_id=teacher_user.id,
        mark_awarded=Decimal("2"),
        decision_status=MarkingDecisionStatus.MARKED,
    )

    result = await grade_script_result(
        db=db_session,
        current_user=teacher_user,
        script_id=context["script"].id,
        result_stage="completed",
    )

    assert result["value"] == Decimal("25.00")
    assert result["grade"] is None


@pytest.mark.asyncio
async def test_invalid_result_stage_is_rejected(
    db_session: AsyncSession,
    teacher_user,
):
    context = await _build_grading_context(
        db_session,
        teacher_user,
    )

    await _create_percentage_scheme(
        db_session,
        teacher_user,
        assessment_id=context["assessment"].id,
    )

    with pytest.raises(HTTPException) as exc:
        await grade_script_result(
            db=db_session,
            current_user=teacher_user,
            script_id=context["script"].id,
            result_stage="published",
        )

    assert exc.value.status_code == 422


# ---------------------------------------------------------------------------
# Candidate latest-result grading
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_candidate_grading_uses_latest_script_version(
    db_session: AsyncSession,
    teacher_user,
):
    context = await _build_grading_context(
        db_session,
        teacher_user,
    )

    scheme = await _create_percentage_scheme(
        db_session,
        teacher_user,
        assessment_id=context["assessment"].id,
    )

    await _create_percentage_boundaries(
        db_session,
        teacher_user,
        scheme_id=scheme.id,
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

    result = await grade_candidate_latest_result(
        db=db_session,
        current_user=teacher_user,
        candidate_id=context["candidate"].id,
    )

    assert result["script_id"] == second_script.id
    assert result["script_version"] == 2
    assert result["value"] == Decimal("100.00")
    assert result["grade"] == "9"


@pytest.mark.asyncio
async def test_candidate_without_script_cannot_be_graded(
    db_session: AsyncSession,
    teacher_user,
):
    course = await _create_course(
        db_session,
        teacher_id=teacher_user.id,
        school_id=teacher_user.school_id,
        title="Candidate Without Script Course",
    )

    assessment = await _create_assessment(
        db_session,
        teacher_id=teacher_user.id,
        school_id=teacher_user.school_id,
        course_id=course.id,
        title="Candidate Without Script",
    )

    await _create_question(
        db_session,
        assessment_id=assessment.id,
        question_number="1",
        maximum_mark=Decimal("10"),
        order=1,
    )

    student = await create_test_user(
        db_session,
        email="grading.no.script@example.com",
        roles=[UserRole.STUDENT],
        school_id=teacher_user.school_id,
    )

    candidate = AssessmentCandidate(
        assessment_id=assessment.id,
        student_id=student.id,
        status=AssessmentCandidateStatus.ALLOCATED,
        candidate_number="NO-GRADE-SCRIPT",
    )

    db_session.add(candidate)
    await db_session.commit()
    await db_session.refresh(candidate)

    scheme = await _create_percentage_scheme(
        db_session,
        teacher_user,
        assessment_id=assessment.id,
    )

    await create_grade_boundary(
        db=db_session,
        current_user=teacher_user,
        scheme_id=scheme.id,
        grade_label="Pass",
        minimum_value=Decimal("50"),
        order=1,
    )

    with pytest.raises(HTTPException) as exc:
        await grade_candidate_latest_result(
            db=db_session,
            current_user=teacher_user,
            candidate_id=candidate.id,
        )

    assert exc.value.status_code == 409


# ---------------------------------------------------------------------------
# Deletion
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_teacher_can_delete_grade_boundary(
    db_session: AsyncSession,
    teacher_user,
):
    context = await _build_grading_context(
        db_session,
        teacher_user,
    )

    scheme = await _create_percentage_scheme(
        db_session,
        teacher_user,
        assessment_id=context["assessment"].id,
    )

    boundary = await create_grade_boundary(
        db=db_session,
        current_user=teacher_user,
        scheme_id=scheme.id,
        grade_label="9",
        minimum_value=Decimal("80"),
        order=1,
    )

    await delete_grade_boundary(
        db=db_session,
        current_user=teacher_user,
        boundary_id=boundary.id,
    )

    boundaries = await list_grade_boundaries(
        db=db_session,
        current_user=teacher_user,
        scheme_id=scheme.id,
    )

    assert boundaries == []


@pytest.mark.asyncio
async def test_deleting_scheme_cascades_to_boundaries(
    db_session: AsyncSession,
    teacher_user,
):
    context = await _build_grading_context(
        db_session,
        teacher_user,
    )

    scheme = await _create_percentage_scheme(
        db_session,
        teacher_user,
        assessment_id=context["assessment"].id,
    )

    await create_grade_boundary(
        db=db_session,
        current_user=teacher_user,
        scheme_id=scheme.id,
        grade_label="9",
        minimum_value=Decimal("80"),
        order=1,
    )

    await delete_grading_scheme(
        db=db_session,
        current_user=teacher_user,
        scheme_id=scheme.id,
    )

    with pytest.raises(HTTPException) as exc:
        await get_grading_scheme(
            db=db_session,
            current_user=teacher_user,
            assessment_id=context["assessment"].id,
        )

    assert exc.value.status_code == 404


# ---------------------------------------------------------------------------
# Access control
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_other_teacher_cannot_create_scheme_for_course(
    db_session: AsyncSession,
    teacher_user,
):
    context = await _build_grading_context(
        db_session,
        teacher_user,
    )

    other_teacher = await create_test_user(
        db_session,
        email="grading.other.teacher@example.com",
        roles=[UserRole.TEACHER],
        school_id=teacher_user.school_id,
    )

    with pytest.raises(HTTPException) as exc:
        await create_grading_scheme(
            db=db_session,
            current_user=other_teacher,
            assessment_id=context["assessment"].id,
            name="Unauthorised Scheme",
            basis=AssessmentGradingBasis.PERCENTAGE,
        )

    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_other_teacher_cannot_view_scheme(
    db_session: AsyncSession,
    teacher_user,
):
    context = await _build_grading_context(
        db_session,
        teacher_user,
    )

    await _create_percentage_scheme(
        db_session,
        teacher_user,
        assessment_id=context["assessment"].id,
    )

    other_teacher = await create_test_user(
        db_session,
        email="grading.other.viewer@example.com",
        roles=[UserRole.TEACHER],
        school_id=teacher_user.school_id,
    )

    with pytest.raises(HTTPException) as exc:
        await get_grading_scheme(
            db=db_session,
            current_user=other_teacher,
            assessment_id=context["assessment"].id,
        )

    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_school_admin_can_manage_grading_scheme(
    db_session: AsyncSession,
    teacher_user,
):
    context = await _build_grading_context(
        db_session,
        teacher_user,
    )

    school_admin = await create_test_user(
        db_session,
        email="grading.school.admin@example.com",
        roles=[UserRole.SCHOOL_ADMIN],
        school_id=teacher_user.school_id,
    )

    scheme = await create_grading_scheme(
        db=db_session,
        current_user=school_admin,
        assessment_id=context["assessment"].id,
        name="Admin Scheme",
        basis=AssessmentGradingBasis.PERCENTAGE,
    )

    assert scheme.created_by_id == school_admin.id


@pytest.mark.asyncio
async def test_student_cannot_manage_grading_scheme(
    db_session: AsyncSession,
    teacher_user,
):
    context = await _build_grading_context(
        db_session,
        teacher_user,
    )

    student = await create_test_user(
        db_session,
        email="grading.unauthorised.student@example.com",
        roles=[UserRole.STUDENT],
        school_id=teacher_user.school_id,
    )

    with pytest.raises(HTTPException) as exc:
        await create_grading_scheme(
            db=db_session,
            current_user=student,
            assessment_id=context["assessment"].id,
            name="Student Scheme",
            basis=AssessmentGradingBasis.PERCENTAGE,
        )

    assert exc.value.status_code == 403
