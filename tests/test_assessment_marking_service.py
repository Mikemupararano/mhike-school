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
from app.models.assessment_question_snapshot import AssessmentQuestionSnapshot
from app.models.assessment_response import (
    AssessmentResponseStatus,
    MarkingDecision,
    MarkingDecisionStatus,
)
from app.models.marking_decision_revision import (
    MarkingDecisionRevision,
    MarkingDecisionRevisionChangeType,
    MarkingDecisionRevisionSource,
)
from app.models.course import Course
from app.models.mark_scheme import (
    MarkScheme,
    MarkSchemeItem,
    MarkSchemeItemType,
)
from app.models.user import UserRole
from app.repositories.assessment_marking import (
    AssessmentMarkingRepository,
)
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
    instant_mark_decision,
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


async def _create_question_snapshot(
    db_session: AsyncSession,
    *,
    script_id: int,
    question: AssessmentQuestion,
    maximum_mark: Decimal,
) -> AssessmentQuestionSnapshot:
    """
    Create the immutable question snapshot governing one script response.
    """

    snapshot = AssessmentQuestionSnapshot(
        script_id=script_id,
        question_id=question.id,
        parent_question_id_snapshot=None,
        question_number=question.question_number,
        title=None,
        prompt=question.prompt,
        question_type="written",
        interaction_config_snapshot=None,
        maximum_mark=maximum_mark,
        order=question.order,
        is_markable=question.is_markable,
        section_snapshot=None,
        options_snapshot=[],
        assets_snapshot=[],
    )

    db_session.add(snapshot)
    await db_session.commit()
    await db_session.refresh(snapshot)

    return snapshot


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
# Marking decision revision persistence
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_repository_appends_first_marking_decision_revision(
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

    await submit_response(
        db=db_session,
        current_user=teacher_user,
        response_id=response.id,
    )

    decision = MarkingDecision(
        response_id=response.id,
        marker_id=teacher_user.id,
        status=MarkingDecisionStatus.UNMARKED,
        revision=0,
    )

    repository = AssessmentMarkingRepository(
        db_session,
    )

    decision = await repository.create_decision(
        decision,
    )
    await db_session.commit()

    revision = await repository.update_decision_with_revision(
        decision.id,
        0,
        values={
            "status": MarkingDecisionStatus.MARKED,
            "mark_awarded": Decimal("3.00"),
        },
        changed_by_id=teacher_user.id,
        change_type=MarkingDecisionRevisionChangeType.INSTANT_MARKED,
        source=MarkingDecisionRevisionSource.QUICK_MARK,
    )

    assert revision is not None

    await db_session.commit()

    await db_session.refresh(
        decision,
    )

    assert decision.revision == 1
    assert decision.status == MarkingDecisionStatus.MARKED
    assert decision.mark_awarded == Decimal("3.00")

    stored_revision = await db_session.get(
        MarkingDecisionRevision,
        revision.id,
    )

    assert stored_revision is not None
    assert stored_revision.marking_decision_id == decision.id
    assert stored_revision.response_id == response.id
    assert stored_revision.revision == 1
    assert stored_revision.changed_by_id == teacher_user.id
    assert (
        stored_revision.change_type
        == MarkingDecisionRevisionChangeType.INSTANT_MARKED
    )
    assert (
        stored_revision.source
        == MarkingDecisionRevisionSource.QUICK_MARK
    )
    assert stored_revision.marker_id == teacher_user.id
    assert stored_revision.status == MarkingDecisionStatus.MARKED
    assert stored_revision.mark_awarded == Decimal("3.00")


@pytest.mark.asyncio
async def test_repository_rejects_stale_marking_decision_revision(
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

    await submit_response(
        db=db_session,
        current_user=teacher_user,
        response_id=response.id,
    )

    decision = MarkingDecision(
        response_id=response.id,
        marker_id=teacher_user.id,
        status=MarkingDecisionStatus.UNMARKED,
        revision=0,
    )

    repository = AssessmentMarkingRepository(
        db_session,
    )

    decision = await repository.create_decision(
        decision,
    )
    await db_session.commit()

    first_revision = await repository.update_decision_with_revision(
        decision.id,
        0,
        values={
            "status": MarkingDecisionStatus.MARKED,
            "mark_awarded": Decimal("3.00"),
        },
        changed_by_id=teacher_user.id,
        change_type=MarkingDecisionRevisionChangeType.INSTANT_MARKED,
        source=MarkingDecisionRevisionSource.QUICK_MARK,
    )

    assert first_revision is not None

    await db_session.commit()

    stale_revision = await repository.update_decision_with_revision(
        decision.id,
        0,
        values={
            "mark_awarded": Decimal("4.00"),
        },
        changed_by_id=teacher_user.id,
        change_type=MarkingDecisionRevisionChangeType.INSTANT_MARKED,
        source=MarkingDecisionRevisionSource.QUICK_MARK,
    )

    assert stale_revision is None

    await db_session.commit()
    await db_session.refresh(
        decision,
    )

    assert decision.revision == 1
    assert decision.mark_awarded == Decimal("3.00")

    from sqlalchemy import select

    result = await db_session.execute(
        select(
            MarkingDecisionRevision,
        ).where(
            MarkingDecisionRevision.marking_decision_id == decision.id,
        )
    )

    revisions = list(
        result.scalars().all(),
    )

    assert len(revisions) == 1
    assert revisions[0].revision == 1
    assert revisions[0].mark_awarded == Decimal("3.00")


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
        expected_revision=decision.revision,
    )

    assert updated.mark_awarded == Decimal("4.00")
    assert updated.marker_comment == "Good answer."
    assert updated.status == MarkingDecisionStatus.IN_PROGRESS


@pytest.mark.asyncio
async def test_manual_marking_update_tracks_revision_and_rejects_stale_write(
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

    decision_id = decision.id

    first = await update_marking_decision(
        db=db_session,
        current_user=teacher_user,
        decision_id=decision_id,
        mark_awarded=Decimal("3.00"),
        marker_comment="First manual mark.",
        expected_revision=0,
    )

    assert first.revision == 1
    assert first.mark_awarded == Decimal("3.00")
    assert first.marker_comment == "First manual mark."
    assert first.status == MarkingDecisionStatus.IN_PROGRESS

    second = await update_marking_decision(
        db=db_session,
        current_user=teacher_user,
        decision_id=decision_id,
        mark_awarded=Decimal("4.00"),
        marker_comment="Corrected manual mark.",
        expected_revision=first.revision,
    )

    assert second.revision == 2
    assert second.mark_awarded == Decimal("4.00")
    assert second.marker_comment == "Corrected manual mark."

    with pytest.raises(HTTPException) as exc:
        await update_marking_decision(
            db=db_session,
            current_user=teacher_user,
            decision_id=decision_id,
            mark_awarded=Decimal("2.00"),
            marker_comment="Stale overwrite.",
            expected_revision=0,
        )

    assert exc.value.status_code == 409
    assert (
        exc.value.detail
        == (
            "Marking decision has changed since it was loaded. "
            "Refresh the decision and try again."
        )
    )

    current = await get_marking_decision(
        db=db_session,
        current_user=teacher_user,
        decision_id=decision_id,
    )

    assert current.revision == 2
    assert current.mark_awarded == Decimal("4.00")
    assert current.marker_comment == "Corrected manual mark."


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
            expected_revision=decision.revision,
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
            expected_revision=decision.revision,
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
        expected_revision=decision.revision,
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
            expected_revision=decision.revision,
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
            expected_revision=decision.revision,
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
        expected_revision=decision.revision,
        mark_scheme_item_id=first_item.id,
        marks_awarded=Decimal("0.00"),
    )

    updated_award = await award_mark_scheme_item(
        db=db_session,
        current_user=teacher_user,
        decision_id=decision.id,
        expected_revision=decision.revision,
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
        expected_revision=decision.revision,
        mark_scheme_item_id=first_item.id,
        marks_awarded=Decimal("1.00"),
    )

    await delete_mark_scheme_item_award(
        db=db_session,
        current_user=teacher_user,
        award_id=award.id,
        expected_revision=decision.revision,
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
        expected_revision=decision.revision,
    )

    assert started.status == MarkingDecisionStatus.IN_PROGRESS

    await update_marking_decision(
        db=db_session,
        current_user=teacher_user,
        decision_id=decision.id,
        mark_awarded=Decimal("3.00"),
        expected_revision=decision.revision,
    )

    marked = await complete_marking(
        db=db_session,
        current_user=teacher_user,
        decision_id=decision.id,
        expected_revision=decision.revision,
    )

    assert marked.status == MarkingDecisionStatus.MARKED
    assert marked.marked_at is not None


@pytest.mark.asyncio
async def test_marking_lifecycle_revisions_and_stale_transition_are_enforced(
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

    decision_id = decision.id

    started = await start_marking(
        db=db_session,
        current_user=teacher_user,
        decision_id=decision_id,
        expected_revision=0,
    )

    assert started.revision == 1
    assert started.status == MarkingDecisionStatus.IN_PROGRESS

    stale_revision = started.revision

    updated = await update_marking_decision(
        db=db_session,
        current_user=teacher_user,
        decision_id=decision_id,
        mark_awarded=Decimal("4.00"),
        marker_comment="Ready to complete.",
        expected_revision=stale_revision,
    )

    assert updated.revision == 2
    assert updated.mark_awarded == Decimal("4.00")

    with pytest.raises(HTTPException) as exc:
        await complete_marking(
            db=db_session,
            current_user=teacher_user,
            decision_id=decision_id,
            expected_revision=stale_revision,
        )

    assert exc.value.status_code == 409
    assert (
        exc.value.detail
        == (
            "Marking decision has changed since it was loaded. "
            "Refresh the decision and try again."
        )
    )

    current = await db_session.get(
        type(decision),
        decision_id,
    )

    assert current is not None
    assert current.revision == 2
    assert current.status == MarkingDecisionStatus.IN_PROGRESS
    assert current.mark_awarded == Decimal("4.00")

    await db_session.refresh(
        teacher_user,
    )

    marked = await complete_marking(
        db=db_session,
        current_user=teacher_user,
        decision_id=decision_id,
        expected_revision=current.revision,
    )

    assert marked.revision == 3
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
        expected_revision=decision.revision,
    )

    with pytest.raises(HTTPException) as exc:
        await complete_marking(
            db=db_session,
            current_user=teacher_user,
            decision_id=decision.id,
            expected_revision=decision.revision,
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
        expected_revision=decision.revision,
    )

    await update_marking_decision(
        db=db_session,
        current_user=teacher_user,
        decision_id=decision.id,
        mark_awarded=Decimal("4.00"),
        expected_revision=decision.revision,
    )

    await complete_marking(
        db=db_session,
        current_user=teacher_user,
        decision_id=decision.id,
        expected_revision=decision.revision,
    )

    reviewed = await review_marking(
        db=db_session,
        current_user=school_admin,
        decision_id=decision.id,
        moderation_comment="Checked and agreed.",
        expected_revision=decision.revision,
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
        expected_revision=decision.revision,
    )

    await update_marking_decision(
        db=db_session,
        current_user=teacher_user,
        decision_id=decision.id,
        mark_awarded=Decimal("4.00"),
        expected_revision=decision.revision,
    )

    await complete_marking(
        db=db_session,
        current_user=teacher_user,
        decision_id=decision.id,
        expected_revision=decision.revision,
    )

    with pytest.raises(HTTPException) as exc:
        await review_marking(
            db=db_session,
            current_user=teacher_user,
            decision_id=decision.id,
            expected_revision=decision.revision,
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
        expected_revision=decision.revision,
    )

    await update_marking_decision(
        db=db_session,
        current_user=teacher_user,
        decision_id=decision.id,
        mark_awarded=Decimal("4.00"),
        expected_revision=decision.revision,
    )

    await complete_marking(
        db=db_session,
        current_user=teacher_user,
        decision_id=decision.id,
        expected_revision=decision.revision,
    )

    finalised = await finalise_marking(
        db=db_session,
        current_user=school_admin,
        decision_id=decision.id,
        expected_revision=decision.revision,
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
        expected_revision=decision.revision,
    )

    await update_marking_decision(
        db=db_session,
        current_user=teacher_user,
        decision_id=decision.id,
        mark_awarded=Decimal("4.00"),
        expected_revision=decision.revision,
    )

    await complete_marking(
        db=db_session,
        current_user=teacher_user,
        decision_id=decision.id,
        expected_revision=decision.revision,
    )

    await finalise_marking(
        db=db_session,
        current_user=school_admin,
        decision_id=decision.id,
        expected_revision=decision.revision,
    )

    with pytest.raises(HTTPException) as exc:
        await update_marking_decision(
            db=db_session,
            current_user=teacher_user,
            decision_id=decision.id,
            mark_awarded=Decimal("5.00"),
            expected_revision=decision.revision,
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
            expected_revision=decision.revision,
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
async def test_marking_decision_with_revision_history_cannot_be_deleted(
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

    decision = await start_marking(
        db=db_session,
        current_user=teacher_user,
        decision_id=decision.id,
        expected_revision=decision.revision,
    )

    assert decision.revision == 1

    decision_id = decision.id

    # Simulate live-state drift without removing immutable history.
    decision.status = MarkingDecisionStatus.UNMARKED
    decision.mark_awarded = None

    await db_session.commit()

    with pytest.raises(HTTPException) as exc:
        await delete_marking_decision(
            db=db_session,
            current_user=teacher_user,
            decision_id=decision_id,
        )

    assert exc.value.status_code == 409
    assert exc.value.detail == (
        "Marking decision cannot be deleted after "
        "marking history exists"
    )

    # The service rollback expires ORM state, so refresh explicitly
    # before asserting that the audited decision still exists.
    await db_session.refresh(decision)

    assert decision.id == decision_id
    assert decision.revision == 1
    assert decision.status == MarkingDecisionStatus.UNMARKED


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
        expected_revision=decision.revision,
    )

    with pytest.raises(HTTPException) as exc:
        await delete_marking_decision(
            db=db_session,
            current_user=teacher_user,
            decision_id=decision.id,
        )

    assert exc.value.status_code == 409

# ----------------------------------------------------------------------
# Immutable question-snapshot marking integrity
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_snapshot_maximum_mark_remains_authoritative_after_canonical_lowered(
    db_session: AsyncSession,
    teacher_user,
):
    context = await _build_marking_context(
        db_session,
        teacher_user,
        maximum_mark=Decimal("5.00"),
    )

    snapshot = await _create_question_snapshot(
        db_session,
        script_id=context["script"].id,
        question=context["question"],
        maximum_mark=Decimal("5.00"),
    )

    response = await create_response(
        db=db_session,
        current_user=teacher_user,
        script_id=context["script"].id,
        question_id=context["question"].id,
        response_text="Answer",
    )

    response.question_snapshot_id = snapshot.id
    await db_session.commit()

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

    # Later editing the canonical question must not change the frozen attempt.
    context["question"].maximum_mark = Decimal("2.00")
    await db_session.commit()

    updated = await update_marking_decision(
        db=db_session,
        current_user=teacher_user,
        decision_id=decision.id,
        mark_awarded=Decimal("5.00"),
        expected_revision=decision.revision,
    )

    assert updated.mark_awarded == Decimal("5.00")


@pytest.mark.asyncio
async def test_mark_above_snapshot_maximum_is_rejected_even_if_canonical_increased(
    db_session: AsyncSession,
    teacher_user,
):
    context = await _build_marking_context(
        db_session,
        teacher_user,
        maximum_mark=Decimal("5.00"),
    )

    snapshot = await _create_question_snapshot(
        db_session,
        script_id=context["script"].id,
        question=context["question"],
        maximum_mark=Decimal("5.00"),
    )

    response = await create_response(
        db=db_session,
        current_user=teacher_user,
        script_id=context["script"].id,
        question_id=context["question"].id,
        response_text="Answer",
    )

    response.question_snapshot_id = snapshot.id
    await db_session.commit()

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

    # Increasing the mutable canonical maximum must not expand the frozen attempt.
    context["question"].maximum_mark = Decimal("10.00")
    await db_session.commit()

    with pytest.raises(HTTPException) as exc:
        await update_marking_decision(
            db=db_session,
            current_user=teacher_user,
            decision_id=decision.id,
            mark_awarded=Decimal("6.00"),
            expected_revision=decision.revision,
        )

    assert exc.value.status_code == 422
    assert "5.00" in str(exc.value.detail)


@pytest.mark.asyncio
async def test_complete_marking_validates_against_snapshot_maximum(
    db_session: AsyncSession,
    teacher_user,
):
    context = await _build_marking_context(
        db_session,
        teacher_user,
        maximum_mark=Decimal("10.00"),
    )

    snapshot = await _create_question_snapshot(
        db_session,
        script_id=context["script"].id,
        question=context["question"],
        maximum_mark=Decimal("5.00"),
    )

    response = await create_response(
        db=db_session,
        current_user=teacher_user,
        script_id=context["script"].id,
        question_id=context["question"].id,
        response_text="Answer",
    )

    response.question_snapshot_id = snapshot.id
    await db_session.commit()

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
        expected_revision=decision.revision,
    )

    # Simulate historical/imported inconsistent data so the lifecycle
    # transition itself must enforce the immutable maximum.
    started.mark_awarded = Decimal("6.00")
    await db_session.commit()

    with pytest.raises(HTTPException) as exc:
        await complete_marking(
            db=db_session,
            current_user=teacher_user,
            decision_id=decision.id,
            expected_revision=decision.revision,
        )

    assert exc.value.status_code == 409
    assert exc.value.detail == "Awarded mark exceeds the question maximum"


@pytest.mark.asyncio
async def test_legacy_response_without_snapshot_uses_canonical_maximum(
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
        response_text="Legacy answer",
    )

    assert response.question_snapshot_id is None

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
            expected_revision=decision.revision,
        )

    assert exc.value.status_code == 422
    assert "5.00" in str(exc.value.detail)

# ----------------------------------------------------------------------
# Instant marking
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_instant_mark_awards_mark_and_completes_decision(
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

    marked = await instant_mark_decision(
        db=db_session,
        current_user=teacher_user,
        decision_id=decision.id,
        mark_awarded=Decimal("4.00"),
        expected_revision=decision.revision,
    )

    assert marked.mark_awarded == Decimal("4.00")
    assert marked.status == MarkingDecisionStatus.MARKED
    assert marked.marked_at is not None
    assert marked.revision == 1


@pytest.mark.asyncio
async def test_instant_mark_enforces_snapshot_maximum(
    db_session: AsyncSession,
    teacher_user,
):
    context = await _build_marking_context(
        db_session,
        teacher_user,
        maximum_mark=Decimal("10.00"),
    )

    snapshot = await _create_question_snapshot(
        db_session,
        script_id=context["script"].id,
        question=context["question"],
        maximum_mark=Decimal("5.00"),
    )

    response = await create_response(
        db=db_session,
        current_user=teacher_user,
        script_id=context["script"].id,
        question_id=context["question"].id,
        response_text="Answer",
    )

    response.question_snapshot_id = snapshot.id
    await db_session.commit()

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
        await instant_mark_decision(
            db=db_session,
            current_user=teacher_user,
            decision_id=decision.id,
            mark_awarded=Decimal("6.00"),
            expected_revision=decision.revision,
        )

    assert exc.value.status_code == 422
    assert "5.00" in str(exc.value.detail)


@pytest.mark.asyncio
async def test_instant_mark_can_correct_marked_decision_before_finalisation(
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

    first = await instant_mark_decision(
        db=db_session,
        current_user=teacher_user,
        decision_id=decision.id,
        mark_awarded=Decimal("3.00"),
        expected_revision=decision.revision,
    )

    first_marked_at = first.marked_at

    assert first.revision == 1

    corrected = await instant_mark_decision(
        db=db_session,
        current_user=teacher_user,
        decision_id=decision.id,
        mark_awarded=Decimal("4.00"),
        expected_revision=first.revision,
    )

    assert corrected.mark_awarded == Decimal("4.00")
    assert corrected.status == MarkingDecisionStatus.MARKED
    assert corrected.marked_at == first_marked_at
    assert corrected.revision == 2


@pytest.mark.asyncio
async def test_instant_mark_rejects_stale_expected_revision(
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

    decision_id = decision.id

    first = await instant_mark_decision(
        db=db_session,
        current_user=teacher_user,
        decision_id=decision_id,
        mark_awarded=Decimal("3.00"),
        expected_revision=0,
    )

    assert first.revision == 1

    with pytest.raises(HTTPException) as exc:
        await instant_mark_decision(
            db=db_session,
            current_user=teacher_user,
            decision_id=decision_id,
            mark_awarded=Decimal("4.00"),
            expected_revision=0,
        )

    assert exc.value.status_code == 409
    assert (
        exc.value.detail
        == (
            "Marking decision has changed since it was loaded. "
            "Refresh the decision and try again."
        )
    )

    current = await get_marking_decision(
        db=db_session,
        current_user=teacher_user,
        decision_id=decision_id,
    )

    assert current.revision == 1
    assert current.mark_awarded == Decimal("3.00")


@pytest.mark.asyncio
async def test_reviewed_decision_cannot_be_instant_marked(
    db_session: AsyncSession,
    teacher_user,
):
    context = await _build_marking_context(
        db_session,
        teacher_user,
        maximum_mark=Decimal("5.00"),
    )

    school_admin = await create_test_user(
        db_session,
        email=f"instant.review.admin.{context['assessment'].id}@example.com",
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

    await instant_mark_decision(
        db=db_session,
        current_user=teacher_user,
        decision_id=decision.id,
        mark_awarded=Decimal("3.00"),
        expected_revision=decision.revision,
    )

    reviewed = await review_marking(
        db=db_session,
        current_user=school_admin,
        decision_id=decision.id,
        moderation_comment="Reviewed.",
        expected_revision=decision.revision,
    )

    assert reviewed.status == MarkingDecisionStatus.REVIEWED

    with pytest.raises(HTTPException) as exc:
        await instant_mark_decision(
            db=db_session,
            current_user=teacher_user,
            decision_id=decision.id,
            mark_awarded=Decimal("4.00"),
            expected_revision=reviewed.revision,
        )

    assert exc.value.status_code == 409
    assert exc.value.detail == "Reviewed marking decisions cannot be instant-marked"


@pytest.mark.asyncio
async def test_finalised_decision_cannot_be_instant_marked(
    db_session: AsyncSession,
    teacher_user,
):
    context = await _build_marking_context(
        db_session,
        teacher_user,
        maximum_mark=Decimal("5.00"),
    )

    school_admin = await create_test_user(
        db_session,
        email=f"instant.finalise.admin.{context['assessment'].id}@example.com",
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

    await instant_mark_decision(
        db=db_session,
        current_user=teacher_user,
        decision_id=decision.id,
        mark_awarded=Decimal("3.00"),
        expected_revision=decision.revision,
    )

    finalised = await finalise_marking(
        db=db_session,
        current_user=school_admin,
        decision_id=decision.id,
        expected_revision=decision.revision,
    )

    assert finalised.status == MarkingDecisionStatus.FINALISED

    with pytest.raises(HTTPException) as exc:
        await instant_mark_decision(
            db=db_session,
            current_user=teacher_user,
            decision_id=decision.id,
            mark_awarded=Decimal("4.00"),
            expected_revision=finalised.revision,
        )

    assert exc.value.status_code == 409
    assert exc.value.detail == "Finalised marking decisions cannot be changed"
