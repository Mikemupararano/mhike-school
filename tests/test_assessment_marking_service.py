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
    AssessmentResponseStatus,
    MarkingDecisionStatus,
)
from app.models.course import Course
from app.models.mark_scheme import (
    MarkScheme,
    MarkSchemeItem,
    MarkSchemeItemType,
)
from app.models.user import UserRole
from app.services.assessment_marking_service import (
    award_mark_scheme_item,
    complete_marking,
    create_marking_decision,
    create_response,
    delete_mark_scheme_item_award,
    delete_marking_decision,
    delete_response,
    finalise_marking,
    get_marking_decision,
    get_response,
    list_script_marking_decisions,
    list_script_responses,
    review_marking,
    start_marking,
    submit_response,
    transition_marking_decision_status,
    transition_response_status,
    update_marking_decision,
    update_response,
    void_response,
)
from tests.conftest import create_test_user


async def _create_course(
    db_session: AsyncSession,
    *,
    teacher_id: int,
    school_id: int,
    title: str = "Assessment Marking Test Course",
) -> Course:
    course = Course(
        title=title,
        description="Course used by assessment marking service tests.",
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
    title: str = "Assessment Marking Test",
) -> Assessment:
    assessment = Assessment(
        school_id=school_id,
        course_id=course_id,
        created_by_id=teacher_id,
        title=title,
        description="Assessment marking service test.",
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
    is_markable: bool = True,
) -> AssessmentQuestion:
    question = AssessmentQuestion(
        assessment_id=assessment_id,
        question_number=question_number,
        prompt="Assessment marking test question.",
        maximum_mark=maximum_mark,
        order=1,
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
    mark_scheme = MarkScheme(
        question_id=question_id,
        title="Test mark scheme",
        general_guidance="Award according to the criteria.",
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
    candidate = AssessmentCandidate(
        assessment_id=assessment_id,
        student_id=student_id,
        status=AssessmentCandidateStatus.SUBMITTED,
        candidate_number="MARK-001",
    )

    db_session.add(candidate)
    await db_session.flush()

    script = AssessmentScript(
        candidate_id=candidate.id,
        version=1,
        status=AssessmentScriptStatus.SUBMITTED,
        source_type="pdf_upload",
        source_filename="candidate.pdf",
        mime_type="application/pdf",
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
        email=f"marking.student.{assessment.id}@example.com",
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


# ----------------------------------------------------------------------
# Response capture
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_teacher_can_create_response(
    db_session: AsyncSession,
    teacher_user,
):
    context = await _build_marking_context(
        db_session,
        teacher_user,
    )

    response = await create_response(
        db=db_session,
        current_user=teacher_user,
        script_id=context["script"].id,
        question_id=context["question"].id,
        response_text="v = u + at",
    )

    assert response.id is not None
    assert response.script_id == context["script"].id
    assert response.question_id == context["question"].id
    assert response.status == AssessmentResponseStatus.IN_PROGRESS
    assert response.response_text == "v = u + at"


@pytest.mark.asyncio
async def test_empty_response_starts_not_started(
    db_session: AsyncSession,
    teacher_user,
):
    context = await _build_marking_context(
        db_session,
        teacher_user,
    )

    response = await create_response(
        db=db_session,
        current_user=teacher_user,
        script_id=context["script"].id,
        question_id=context["question"].id,
    )

    assert response.status == AssessmentResponseStatus.NOT_STARTED


@pytest.mark.asyncio
async def test_duplicate_response_is_rejected(
    db_session: AsyncSession,
    teacher_user,
):
    context = await _build_marking_context(
        db_session,
        teacher_user,
    )

    await create_response(
        db=db_session,
        current_user=teacher_user,
        script_id=context["script"].id,
        question_id=context["question"].id,
        response_text="First",
    )

    with pytest.raises(HTTPException) as exc:
        await create_response(
            db=db_session,
            current_user=teacher_user,
            script_id=context["script"].id,
            question_id=context["question"].id,
            response_text="Second",
        )

    assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_response_rejects_question_from_other_assessment(
    db_session: AsyncSession,
    teacher_user,
):
    context = await _build_marking_context(
        db_session,
        teacher_user,
    )

    second_course = await _create_course(
        db_session,
        teacher_id=teacher_user.id,
        school_id=teacher_user.school_id,
        title="Second marking course",
    )

    second_assessment = await _create_assessment(
        db_session,
        teacher_id=teacher_user.id,
        school_id=teacher_user.school_id,
        course_id=second_course.id,
        title="Second marking assessment",
    )

    other_question = await _create_question(
        db_session,
        assessment_id=second_assessment.id,
        question_number="2",
    )

    with pytest.raises(HTTPException) as exc:
        await create_response(
            db=db_session,
            current_user=teacher_user,
            script_id=context["script"].id,
            question_id=other_question.id,
            response_text="Invalid scope",
        )

    assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_non_markable_question_rejects_response(
    db_session: AsyncSession,
    teacher_user,
):
    context = await _build_marking_context(
        db_session,
        teacher_user,
        is_markable=False,
    )

    with pytest.raises(HTTPException) as exc:
        await create_response(
            db=db_session,
            current_user=teacher_user,
            script_id=context["script"].id,
            question_id=context["question"].id,
            response_text="Should fail",
        )

    assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_teacher_can_update_response(
    db_session: AsyncSession,
    teacher_user,
):
    context = await _build_marking_context(
        db_session,
        teacher_user,
    )

    response = await create_response(
        db=db_session,
        current_user=teacher_user,
        script_id=context["script"].id,
        question_id=context["question"].id,
    )

    updated = await update_response(
        db=db_session,
        current_user=teacher_user,
        response_id=response.id,
        response_text="Updated response",
        response_data='{"value": 42}',
        source_reference="page-1",
    )

    assert updated.status == AssessmentResponseStatus.IN_PROGRESS
    assert updated.response_text == "Updated response"
    assert updated.response_data == '{"value": 42}'
    assert updated.source_reference == "page-1"


@pytest.mark.asyncio
async def test_teacher_can_list_script_responses(
    db_session: AsyncSession,
    teacher_user,
):
    context = await _build_marking_context(
        db_session,
        teacher_user,
    )

    await create_response(
        db=db_session,
        current_user=teacher_user,
        script_id=context["script"].id,
        question_id=context["question"].id,
        response_text="Answer",
    )

    responses = await list_script_responses(
        db=db_session,
        current_user=teacher_user,
        script_id=context["script"].id,
    )

    assert len(responses) == 1
    assert responses[0].question_id == context["question"].id


# ----------------------------------------------------------------------
# Response lifecycle
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_response_can_be_submitted(
    db_session: AsyncSession,
    teacher_user,
):
    context = await _build_marking_context(
        db_session,
        teacher_user,
    )

    response = await create_response(
        db=db_session,
        current_user=teacher_user,
        script_id=context["script"].id,
        question_id=context["question"].id,
        response_text="Answer",
    )

    submitted = await submit_response(
        db=db_session,
        current_user=teacher_user,
        response_id=response.id,
    )

    assert submitted.status == AssessmentResponseStatus.SUBMITTED
    assert submitted.submitted_at is not None


@pytest.mark.asyncio
async def test_response_can_be_voided(
    db_session: AsyncSession,
    teacher_user,
):
    context = await _build_marking_context(
        db_session,
        teacher_user,
    )

    response = await create_response(
        db=db_session,
        current_user=teacher_user,
        script_id=context["script"].id,
        question_id=context["question"].id,
        response_text="Answer",
    )

    voided = await void_response(
        db=db_session,
        current_user=teacher_user,
        response_id=response.id,
    )

    assert voided.status == AssessmentResponseStatus.VOID


@pytest.mark.asyncio
async def test_void_response_cannot_transition_again(
    db_session: AsyncSession,
    teacher_user,
):
    context = await _build_marking_context(
        db_session,
        teacher_user,
    )

    response = await create_response(
        db=db_session,
        current_user=teacher_user,
        script_id=context["script"].id,
        question_id=context["question"].id,
    )

    voided = await void_response(
        db=db_session,
        current_user=teacher_user,
        response_id=response.id,
    )

    with pytest.raises(HTTPException) as exc:
        await transition_response_status(
            db=db_session,
            current_user=teacher_user,
            response_id=voided.id,
            new_status=AssessmentResponseStatus.SUBMITTED,
        )

    assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_untouched_response_can_be_deleted(
    db_session: AsyncSession,
    teacher_user,
):
    context = await _build_marking_context(
        db_session,
        teacher_user,
    )

    response = await create_response(
        db=db_session,
        current_user=teacher_user,
        script_id=context["script"].id,
        question_id=context["question"].id,
    )

    response_id = response.id

    await delete_response(
        db=db_session,
        current_user=teacher_user,
        response_id=response_id,
    )

    with pytest.raises(HTTPException) as exc:
        await get_response(
            db=db_session,
            current_user=teacher_user,
            response_id=response_id,
        )

    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_response_with_content_cannot_be_deleted(
    db_session: AsyncSession,
    teacher_user,
):
    context = await _build_marking_context(
        db_session,
        teacher_user,
    )

    response = await create_response(
        db=db_session,
        current_user=teacher_user,
        script_id=context["script"].id,
        question_id=context["question"].id,
        response_text="Answer",
    )

    with pytest.raises(HTTPException) as exc:
        await delete_response(
            db=db_session,
            current_user=teacher_user,
            response_id=response.id,
        )

    assert exc.value.status_code == 409


# ----------------------------------------------------------------------
# Marking decision creation
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_teacher_can_create_marking_decision_for_submitted_response(
    db_session: AsyncSession,
    teacher_user,
):
    context = await _build_marking_context(
        db_session,
        teacher_user,
    )

    response = await create_response(
        db=db_session,
        current_user=teacher_user,
        script_id=context["script"].id,
        question_id=context["question"].id,
        response_text="Answer",
    )

    await submit_response(
        db=db_session,
        current_user=teacher_user,
        response_id=response.id,
    )

    decision = await create_marking_decision(
        db=db_session,
        current_user=teacher_user,
        response_id=response.id,
        marker_comment="Initial marking.",
    )

    assert decision.id is not None
    assert decision.response_id == response.id
    assert decision.marker_id == teacher_user.id
    assert decision.status == MarkingDecisionStatus.UNMARKED


@pytest.mark.asyncio
async def test_unsubmitted_response_cannot_be_marked(
    db_session: AsyncSession,
    teacher_user,
):
    context = await _build_marking_context(
        db_session,
        teacher_user,
    )

    response = await create_response(
        db=db_session,
        current_user=teacher_user,
        script_id=context["script"].id,
        question_id=context["question"].id,
        response_text="Answer",
    )

    with pytest.raises(HTTPException) as exc:
        await create_marking_decision(
            db=db_session,
            current_user=teacher_user,
            response_id=response.id,
        )

    assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_duplicate_marking_decision_is_rejected(
    db_session: AsyncSession,
    teacher_user,
):
    context = await _build_marking_context(
        db_session,
        teacher_user,
    )

    response = await create_response(
        db=db_session,
        current_user=teacher_user,
        script_id=context["script"].id,
        question_id=context["question"].id,
        response_text="Answer",
    )

    await submit_response(
        db=db_session,
        current_user=teacher_user,
        response_id=response.id,
    )

    await create_marking_decision(
        db=db_session,
        current_user=teacher_user,
        response_id=response.id,
    )

    with pytest.raises(HTTPException) as exc:
        await create_marking_decision(
            db=db_session,
            current_user=teacher_user,
            response_id=response.id,
        )

    assert exc.value.status_code == 409


# ----------------------------------------------------------------------
# Question-level marks
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_teacher_can_update_question_level_mark(
    db_session: AsyncSession,
    teacher_user,
):
    context = await _build_marking_context(
        db_session,
        teacher_user,
        maximum_mark=Decimal("5.00"),
    )

    response = await create_response(
        db=db_session,
        current_user=teacher_user,
        script_id=context["script"].id,
        question_id=context["question"].id,
        response_text="Answer",
    )

    await submit_response(
        db=db_session,
        current_user=teacher_user,
        response_id=response.id,
    )

    decision = await create_marking_decision(
        db=db_session,
        current_user=teacher_user,
        response_id=response.id,
    )

    updated = await update_marking_decision(
        db=db_session,
        current_user=teacher_user,
        decision_id=decision.id,
        mark_awarded=Decimal("4.00"),
        marker_comment="Good answer.",
    )

    assert updated.mark_awarded == Decimal("4.00")
    assert updated.marker_comment == "Good answer."
    assert updated.status == MarkingDecisionStatus.IN_PROGRESS


@pytest.mark.asyncio
async def test_mark_above_question_maximum_is_rejected(
    db_session: AsyncSession,
    teacher_user,
):
    context = await _build_marking_context(
        db_session,
        teacher_user,
        maximum_mark=Decimal("5.00"),
    )

    response = await create_response(
        db=db_session,
        current_user=teacher_user,
        script_id=context["script"].id,
        question_id=context["question"].id,
        response_text="Answer",
    )

    await submit_response(
        db=db_session,
        current_user=teacher_user,
        response_id=response.id,
    )

    decision = await create_marking_decision(
        db=db_session,
        current_user=teacher_user,
        response_id=response.id,
    )

    with pytest.raises(HTTPException) as exc:
        await update_marking_decision(
            db=db_session,
            current_user=teacher_user,
            decision_id=decision.id,
            mark_awarded=Decimal("6.00"),
        )

    assert exc.value.status_code == 422


@pytest.mark.asyncio
async def test_negative_question_mark_is_rejected(
    db_session: AsyncSession,
    teacher_user,
):
    context = await _build_marking_context(
        db_session,
        teacher_user,
    )

    response = await create_response(
        db=db_session,
        current_user=teacher_user,
        script_id=context["script"].id,
        question_id=context["question"].id,
        response_text="Answer",
    )

    await submit_response(
        db=db_session,
        current_user=teacher_user,
        response_id=response.id,
    )

    decision = await create_marking_decision(
        db=db_session,
        current_user=teacher_user,
        response_id=response.id,
    )

    with pytest.raises(HTTPException) as exc:
        await update_marking_decision(
            db=db_session,
            current_user=teacher_user,
            decision_id=decision.id,
            mark_awarded=Decimal("-1.00"),
        )

    assert exc.value.status_code == 422


# ----------------------------------------------------------------------
# Criterion-level awards
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_teacher_can_award_mark_scheme_item(
    db_session: AsyncSession,
    teacher_user,
):
    context = await _build_marking_context(
        db_session,
        teacher_user,
    )

    _, first_item, _ = await _create_mark_scheme(
        db_session,
        question_id=context["question"].id,
    )

    response = await create_response(
        db=db_session,
        current_user=teacher_user,
        script_id=context["script"].id,
        question_id=context["question"].id,
        response_text="Answer",
    )

    await submit_response(
        db=db_session,
        current_user=teacher_user,
        response_id=response.id,
    )

    decision = await create_marking_decision(
        db=db_session,
        current_user=teacher_user,
        response_id=response.id,
    )

    award = await award_mark_scheme_item(
        db=db_session,
        current_user=teacher_user,
        decision_id=decision.id,
        mark_scheme_item_id=first_item.id,
        marks_awarded=Decimal("1.00"),
        marker_note="Method awarded.",
    )

    assert award.id is not None
    assert award.marking_decision_id == decision.id
    assert award.mark_scheme_item_id == first_item.id
    assert award.marks_awarded == Decimal("1.00")
    assert award.awarded_by_id == teacher_user.id


@pytest.mark.asyncio
async def test_criterion_award_above_item_maximum_is_rejected(
    db_session: AsyncSession,
    teacher_user,
):
    context = await _build_marking_context(
        db_session,
        teacher_user,
    )

    _, first_item, _ = await _create_mark_scheme(
        db_session,
        question_id=context["question"].id,
    )

    response = await create_response(
        db=db_session,
        current_user=teacher_user,
        script_id=context["script"].id,
        question_id=context["question"].id,
        response_text="Answer",
    )

    await submit_response(
        db=db_session,
        current_user=teacher_user,
        response_id=response.id,
    )

    decision = await create_marking_decision(
        db=db_session,
        current_user=teacher_user,
        response_id=response.id,
    )

    with pytest.raises(HTTPException) as exc:
        await award_mark_scheme_item(
            db=db_session,
            current_user=teacher_user,
            decision_id=decision.id,
            mark_scheme_item_id=first_item.id,
            marks_awarded=Decimal("2.00"),
        )

    assert exc.value.status_code == 422


@pytest.mark.asyncio
async def test_criterion_from_other_question_is_rejected(
    db_session: AsyncSession,
    teacher_user,
):
    context = await _build_marking_context(
        db_session,
        teacher_user,
    )

    other_question = await _create_question(
        db_session,
        assessment_id=context["assessment"].id,
        question_number="2",
    )

    _, other_item, _ = await _create_mark_scheme(
        db_session,
        question_id=other_question.id,
    )

    response = await create_response(
        db=db_session,
        current_user=teacher_user,
        script_id=context["script"].id,
        question_id=context["question"].id,
        response_text="Answer",
    )

    await submit_response(
        db=db_session,
        current_user=teacher_user,
        response_id=response.id,
    )

    decision = await create_marking_decision(
        db=db_session,
        current_user=teacher_user,
        response_id=response.id,
    )

    with pytest.raises(HTTPException) as exc:
        await award_mark_scheme_item(
            db=db_session,
            current_user=teacher_user,
            decision_id=decision.id,
            mark_scheme_item_id=other_item.id,
            marks_awarded=Decimal("1.00"),
        )

    assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_existing_criterion_award_is_updated_not_duplicated(
    db_session: AsyncSession,
    teacher_user,
):
    context = await _build_marking_context(
        db_session,
        teacher_user,
    )

    _, first_item, _ = await _create_mark_scheme(
        db_session,
        question_id=context["question"].id,
    )

    response = await create_response(
        db=db_session,
        current_user=teacher_user,
        script_id=context["script"].id,
        question_id=context["question"].id,
        response_text="Answer",
    )

    await submit_response(
        db=db_session,
        current_user=teacher_user,
        response_id=response.id,
    )

    decision = await create_marking_decision(
        db=db_session,
        current_user=teacher_user,
        response_id=response.id,
    )

    first_award = await award_mark_scheme_item(
        db=db_session,
        current_user=teacher_user,
        decision_id=decision.id,
        mark_scheme_item_id=first_item.id,
        marks_awarded=Decimal("0.00"),
    )

    updated_award = await award_mark_scheme_item(
        db=db_session,
        current_user=teacher_user,
        decision_id=decision.id,
        mark_scheme_item_id=first_item.id,
        marks_awarded=Decimal("1.00"),
        marker_note="Awarded after review.",
    )

    assert updated_award.id == first_award.id
    assert updated_award.marks_awarded == Decimal("1.00")
    assert updated_award.marker_note == "Awarded after review."


@pytest.mark.asyncio
async def test_criterion_award_can_be_deleted_before_finalisation(
    db_session: AsyncSession,
    teacher_user,
):
    context = await _build_marking_context(
        db_session,
        teacher_user,
    )

    _, first_item, _ = await _create_mark_scheme(
        db_session,
        question_id=context["question"].id,
    )

    response = await create_response(
        db=db_session,
        current_user=teacher_user,
        script_id=context["script"].id,
        question_id=context["question"].id,
        response_text="Answer",
    )

    await submit_response(
        db=db_session,
        current_user=teacher_user,
        response_id=response.id,
    )

    decision = await create_marking_decision(
        db=db_session,
        current_user=teacher_user,
        response_id=response.id,
    )

    award = await award_mark_scheme_item(
        db=db_session,
        current_user=teacher_user,
        decision_id=decision.id,
        mark_scheme_item_id=first_item.id,
        marks_awarded=Decimal("1.00"),
    )

    await delete_mark_scheme_item_award(
        db=db_session,
        current_user=teacher_user,
        award_id=award.id,
    )

    loaded_decision = await get_marking_decision(
        db=db_session,
        current_user=teacher_user,
        decision_id=decision.id,
    )

    assert loaded_decision.item_awards == []


# ----------------------------------------------------------------------
# Marking lifecycle
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_marking_can_progress_to_marked(
    db_session: AsyncSession,
    teacher_user,
):
    context = await _build_marking_context(
        db_session,
        teacher_user,
    )

    response = await create_response(
        db=db_session,
        current_user=teacher_user,
        script_id=context["script"].id,
        question_id=context["question"].id,
        response_text="Answer",
    )

    await submit_response(
        db=db_session,
        current_user=teacher_user,
        response_id=response.id,
    )

    decision = await create_marking_decision(
        db=db_session,
        current_user=teacher_user,
        response_id=response.id,
    )

    started = await start_marking(
        db=db_session,
        current_user=teacher_user,
        decision_id=decision.id,
    )

    assert started.status == MarkingDecisionStatus.IN_PROGRESS

    await update_marking_decision(
        db=db_session,
        current_user=teacher_user,
        decision_id=decision.id,
        mark_awarded=Decimal("3.00"),
    )

    marked = await complete_marking(
        db=db_session,
        current_user=teacher_user,
        decision_id=decision.id,
    )

    assert marked.status == MarkingDecisionStatus.MARKED
    assert marked.marked_at is not None


@pytest.mark.asyncio
async def test_marking_cannot_complete_without_question_level_mark(
    db_session: AsyncSession,
    teacher_user,
):
    context = await _build_marking_context(
        db_session,
        teacher_user,
    )

    response = await create_response(
        db=db_session,
        current_user=teacher_user,
        script_id=context["script"].id,
        question_id=context["question"].id,
        response_text="Answer",
    )

    await submit_response(
        db=db_session,
        current_user=teacher_user,
        response_id=response.id,
    )

    decision = await create_marking_decision(
        db=db_session,
        current_user=teacher_user,
        response_id=response.id,
    )

    await start_marking(
        db=db_session,
        current_user=teacher_user,
        decision_id=decision.id,
    )

    with pytest.raises(HTTPException) as exc:
        await complete_marking(
            db=db_session,
            current_user=teacher_user,
            decision_id=decision.id,
        )

    assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_school_admin_can_review_marked_decision(
    db_session: AsyncSession,
    teacher_user,
):
    context = await _build_marking_context(
        db_session,
        teacher_user,
    )

    school_admin = await create_test_user(
        db_session,
        email="marking.school.admin@example.com",
        roles=[UserRole.SCHOOL_ADMIN],
        school_id=teacher_user.school_id,
    )

    response = await create_response(
        db=db_session,
        current_user=teacher_user,
        script_id=context["script"].id,
        question_id=context["question"].id,
        response_text="Answer",
    )

    await submit_response(
        db=db_session,
        current_user=teacher_user,
        response_id=response.id,
    )

    decision = await create_marking_decision(
        db=db_session,
        current_user=teacher_user,
        response_id=response.id,
    )

    await start_marking(
        db=db_session,
        current_user=teacher_user,
        decision_id=decision.id,
    )

    await update_marking_decision(
        db=db_session,
        current_user=teacher_user,
        decision_id=decision.id,
        mark_awarded=Decimal("4.00"),
    )

    await complete_marking(
        db=db_session,
        current_user=teacher_user,
        decision_id=decision.id,
    )

    reviewed = await review_marking(
        db=db_session,
        current_user=school_admin,
        decision_id=decision.id,
        moderation_comment="Checked and agreed.",
    )

    assert reviewed.status == MarkingDecisionStatus.REVIEWED
    assert reviewed.reviewed_at is not None
    assert reviewed.moderation_comment == "Checked and agreed."


@pytest.mark.asyncio
async def test_teacher_cannot_review_marked_decision(
    db_session: AsyncSession,
    teacher_user,
):
    context = await _build_marking_context(
        db_session,
        teacher_user,
    )

    response = await create_response(
        db=db_session,
        current_user=teacher_user,
        script_id=context["script"].id,
        question_id=context["question"].id,
        response_text="Answer",
    )

    await submit_response(
        db=db_session,
        current_user=teacher_user,
        response_id=response.id,
    )

    decision = await create_marking_decision(
        db=db_session,
        current_user=teacher_user,
        response_id=response.id,
    )

    await start_marking(
        db=db_session,
        current_user=teacher_user,
        decision_id=decision.id,
    )

    await update_marking_decision(
        db=db_session,
        current_user=teacher_user,
        decision_id=decision.id,
        mark_awarded=Decimal("4.00"),
    )

    await complete_marking(
        db=db_session,
        current_user=teacher_user,
        decision_id=decision.id,
    )

    with pytest.raises(HTTPException) as exc:
        await review_marking(
            db=db_session,
            current_user=teacher_user,
            decision_id=decision.id,
        )

    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_school_admin_can_finalise_marked_decision(
    db_session: AsyncSession,
    teacher_user,
):
    context = await _build_marking_context(
        db_session,
        teacher_user,
    )

    school_admin = await create_test_user(
        db_session,
        email="marking.finalise.admin@example.com",
        roles=[UserRole.SCHOOL_ADMIN],
        school_id=teacher_user.school_id,
    )

    response = await create_response(
        db=db_session,
        current_user=teacher_user,
        script_id=context["script"].id,
        question_id=context["question"].id,
        response_text="Answer",
    )

    await submit_response(
        db=db_session,
        current_user=teacher_user,
        response_id=response.id,
    )

    decision = await create_marking_decision(
        db=db_session,
        current_user=teacher_user,
        response_id=response.id,
    )

    await start_marking(
        db=db_session,
        current_user=teacher_user,
        decision_id=decision.id,
    )

    await update_marking_decision(
        db=db_session,
        current_user=teacher_user,
        decision_id=decision.id,
        mark_awarded=Decimal("4.00"),
    )

    await complete_marking(
        db=db_session,
        current_user=teacher_user,
        decision_id=decision.id,
    )

    finalised = await finalise_marking(
        db=db_session,
        current_user=school_admin,
        decision_id=decision.id,
    )

    assert finalised.status == MarkingDecisionStatus.FINALISED
    assert finalised.finalised_at is not None


@pytest.mark.asyncio
async def test_finalised_decision_cannot_be_changed(
    db_session: AsyncSession,
    teacher_user,
):
    context = await _build_marking_context(
        db_session,
        teacher_user,
    )

    school_admin = await create_test_user(
        db_session,
        email="marking.locked.admin@example.com",
        roles=[UserRole.SCHOOL_ADMIN],
        school_id=teacher_user.school_id,
    )

    response = await create_response(
        db=db_session,
        current_user=teacher_user,
        script_id=context["script"].id,
        question_id=context["question"].id,
        response_text="Answer",
    )

    await submit_response(
        db=db_session,
        current_user=teacher_user,
        response_id=response.id,
    )

    decision = await create_marking_decision(
        db=db_session,
        current_user=teacher_user,
        response_id=response.id,
    )

    await start_marking(
        db=db_session,
        current_user=teacher_user,
        decision_id=decision.id,
    )

    await update_marking_decision(
        db=db_session,
        current_user=teacher_user,
        decision_id=decision.id,
        mark_awarded=Decimal("4.00"),
    )

    await complete_marking(
        db=db_session,
        current_user=teacher_user,
        decision_id=decision.id,
    )

    await finalise_marking(
        db=db_session,
        current_user=school_admin,
        decision_id=decision.id,
    )

    with pytest.raises(HTTPException) as exc:
        await update_marking_decision(
            db=db_session,
            current_user=teacher_user,
            decision_id=decision.id,
            mark_awarded=Decimal("5.00"),
        )

    assert exc.value.status_code == 409


# ----------------------------------------------------------------------
# Marker ownership and course isolation
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_other_teacher_cannot_change_marking_decision(
    db_session: AsyncSession,
    teacher_user,
):
    context = await _build_marking_context(
        db_session,
        teacher_user,
    )

    other_teacher = await create_test_user(
        db_session,
        email="marking.other.teacher@example.com",
        roles=[UserRole.TEACHER],
        school_id=teacher_user.school_id,
    )

    response = await create_response(
        db=db_session,
        current_user=teacher_user,
        script_id=context["script"].id,
        question_id=context["question"].id,
        response_text="Answer",
    )

    await submit_response(
        db=db_session,
        current_user=teacher_user,
        response_id=response.id,
    )

    decision = await create_marking_decision(
        db=db_session,
        current_user=teacher_user,
        response_id=response.id,
    )

    with pytest.raises(HTTPException) as exc:
        await update_marking_decision(
            db=db_session,
            current_user=other_teacher,
            decision_id=decision.id,
            mark_awarded=Decimal("2.00"),
        )

    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_other_course_teacher_cannot_access_response(
    db_session: AsyncSession,
    teacher_user,
):
    context = await _build_marking_context(
        db_session,
        teacher_user,
    )

    other_teacher = await create_test_user(
        db_session,
        email="marking.other.course.teacher@example.com",
        roles=[UserRole.TEACHER],
        school_id=teacher_user.school_id,
    )

    response = await create_response(
        db=db_session,
        current_user=teacher_user,
        script_id=context["script"].id,
        question_id=context["question"].id,
        response_text="Answer",
    )

    with pytest.raises(HTTPException) as exc:
        await get_response(
            db=db_session,
            current_user=other_teacher,
            response_id=response.id,
        )

    assert exc.value.status_code == 403


# ----------------------------------------------------------------------
# Decision listing and deletion
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_teacher_can_list_script_marking_decisions(
    db_session: AsyncSession,
    teacher_user,
):
    context = await _build_marking_context(
        db_session,
        teacher_user,
    )

    response = await create_response(
        db=db_session,
        current_user=teacher_user,
        script_id=context["script"].id,
        question_id=context["question"].id,
        response_text="Answer",
    )

    await submit_response(
        db=db_session,
        current_user=teacher_user,
        response_id=response.id,
    )

    decision = await create_marking_decision(
        db=db_session,
        current_user=teacher_user,
        response_id=response.id,
    )

    decisions = await list_script_marking_decisions(
        db=db_session,
        current_user=teacher_user,
        script_id=context["script"].id,
    )

    assert len(decisions) == 1
    assert decisions[0].id == decision.id


@pytest.mark.asyncio
async def test_untouched_marking_decision_can_be_deleted(
    db_session: AsyncSession,
    teacher_user,
):
    context = await _build_marking_context(
        db_session,
        teacher_user,
    )

    response = await create_response(
        db=db_session,
        current_user=teacher_user,
        script_id=context["script"].id,
        question_id=context["question"].id,
        response_text="Answer",
    )

    await submit_response(
        db=db_session,
        current_user=teacher_user,
        response_id=response.id,
    )

    decision = await create_marking_decision(
        db=db_session,
        current_user=teacher_user,
        response_id=response.id,
    )

    decision_id = decision.id

    await delete_marking_decision(
        db=db_session,
        current_user=teacher_user,
        decision_id=decision_id,
    )

    with pytest.raises(HTTPException) as exc:
        await get_marking_decision(
            db=db_session,
            current_user=teacher_user,
            decision_id=decision_id,
        )

    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_started_marking_decision_cannot_be_deleted(
    db_session: AsyncSession,
    teacher_user,
):
    context = await _build_marking_context(
        db_session,
        teacher_user,
    )

    response = await create_response(
        db=db_session,
        current_user=teacher_user,
        script_id=context["script"].id,
        question_id=context["question"].id,
        response_text="Answer",
    )

    await submit_response(
        db=db_session,
        current_user=teacher_user,
        response_id=response.id,
    )

    decision = await create_marking_decision(
        db=db_session,
        current_user=teacher_user,
        response_id=response.id,
    )

    await start_marking(
        db=db_session,
        current_user=teacher_user,
        decision_id=decision.id,
    )

    with pytest.raises(HTTPException) as exc:
        await delete_marking_decision(
            db=db_session,
            current_user=teacher_user,
            decision_id=decision.id,
        )

    assert exc.value.status_code == 409
