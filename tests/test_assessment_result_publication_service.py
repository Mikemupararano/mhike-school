from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

import app.services.assessment_result_publication_service as publication_service
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
from app.models.assessment_question import AssessmentQuestion
from app.models.assessment_response import (
    AssessmentResponse,
    AssessmentResponseStatus,
    MarkingDecision,
    MarkingDecisionStatus,
)
from app.models.assessment_result_publication import (
    AssessmentResultPublicationStatus,
)
from app.models.course import Course
from app.models.user import UserRole
from app.services.assessment_result_publication_service import (
    approve_result_publication,
    can_parent_view_results,
    can_student_view_results,
    create_result_publication,
    delete_result_publication,
    get_published_result_visibility,
    get_result_publication,
    publish_due_scheduled_results,
    publish_results,
    revoke_result_publication_approval,
    schedule_results_publication,
    update_result_publication,
    withdraw_results,
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
    title: str = "Assessment Publication Test Course",
) -> Course:
    course = Course(
        title=title,
        description="Course used by assessment publication tests.",
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
    title: str = "End of Topic Test",
) -> Assessment:
    assessment = Assessment(
        school_id=school_id,
        course_id=course_id,
        created_by_id=teacher_id,
        title=title,
        description="Assessment result publication service test.",
        assessment_type="end_of_topic_test",
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
        source_filename=f"publication-script-v{version}.pdf",
        storage_key=f"assessment-publication/publication-script-v{version}.pdf",
        mime_type="application/pdf",
        checksum=f"publication-{candidate_id}-{version}",
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


async def _build_publication_context(
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
        email=f"publication.student.{assessment.id}@example.com",
        roles=[UserRole.STUDENT],
        school_id=teacher_user.school_id,
    )

    candidate = await _create_candidate(
        db_session,
        assessment_id=assessment.id,
        student_id=student.id,
        candidate_number="PUB-001",
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


async def _finalise_all_marks(
    db_session: AsyncSession,
    teacher_user,
    context,
) -> None:
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


# ---------------------------------------------------------------------------
# Configuration creation and retrieval
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_teacher_can_create_default_publication_configuration(
    db_session: AsyncSession,
    teacher_user,
):
    context = await _build_publication_context(
        db_session,
        teacher_user,
    )

    publication = await create_result_publication(
        db=db_session,
        current_user=teacher_user,
        assessment_id=context["assessment"].id,
    )

    assert publication.id is not None
    assert publication.assessment_id == context["assessment"].id
    assert publication.status == AssessmentResultPublicationStatus.UNRELEASED
    assert publication.requires_approval is False
    assert publication.visible_to_students is True
    assert publication.visible_to_parents is True
    assert publication.include_mark is True
    assert publication.include_percentage is True
    assert publication.include_grade is True
    assert publication.include_question_breakdown is False
    assert publication.created_by_id == teacher_user.id


@pytest.mark.asyncio
async def test_duplicate_publication_configuration_is_rejected(
    db_session: AsyncSession,
    teacher_user,
):
    context = await _build_publication_context(
        db_session,
        teacher_user,
    )

    await create_result_publication(
        db=db_session,
        current_user=teacher_user,
        assessment_id=context["assessment"].id,
    )

    with pytest.raises(HTTPException) as exc:
        await create_result_publication(
            db=db_session,
            current_user=teacher_user,
            assessment_id=context["assessment"].id,
        )

    assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_teacher_can_get_publication_configuration(
    db_session: AsyncSession,
    teacher_user,
):
    context = await _build_publication_context(
        db_session,
        teacher_user,
    )

    created = await create_result_publication(
        db=db_session,
        current_user=teacher_user,
        assessment_id=context["assessment"].id,
    )

    publication = await get_result_publication(
        db=db_session,
        current_user=teacher_user,
        assessment_id=context["assessment"].id,
    )

    assert publication.id == created.id


# ---------------------------------------------------------------------------
# Configuration updates
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_teacher_can_update_publication_visibility(
    db_session: AsyncSession,
    teacher_user,
):
    context = await _build_publication_context(
        db_session,
        teacher_user,
    )

    publication = await create_result_publication(
        db=db_session,
        current_user=teacher_user,
        assessment_id=context["assessment"].id,
    )

    updated = await update_result_publication(
        db=db_session,
        current_user=teacher_user,
        publication_id=publication.id,
        visible_to_students=False,
        visible_to_parents=True,
        include_question_breakdown=True,
        release_message="Results are now available.",
    )

    assert updated.visible_to_students is False
    assert updated.visible_to_parents is True
    assert updated.include_question_breakdown is True
    assert updated.release_message == "Results are now available."


@pytest.mark.asyncio
async def test_release_message_can_be_cleared(
    db_session: AsyncSession,
    teacher_user,
):
    context = await _build_publication_context(
        db_session,
        teacher_user,
    )

    publication = await create_result_publication(
        db=db_session,
        current_user=teacher_user,
        assessment_id=context["assessment"].id,
        release_message="Initial release message",
    )

    updated = await update_result_publication(
        db=db_session,
        current_user=teacher_user,
        publication_id=publication.id,
        release_message=None,
    )

    assert updated.release_message is None


# ---------------------------------------------------------------------------
# Teacher publication without SMT approval
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_course_teacher_can_publish_end_of_topic_results_without_smt_approval(
    db_session: AsyncSession,
    teacher_user,
):
    context = await _build_publication_context(
        db_session,
        teacher_user,
    )

    await _finalise_all_marks(
        db_session,
        teacher_user,
        context,
    )

    publication = await create_result_publication(
        db=db_session,
        current_user=teacher_user,
        assessment_id=context["assessment"].id,
        requires_approval=False,
    )

    published = await publish_results(
        db=db_session,
        current_user=teacher_user,
        publication_id=publication.id,
    )

    assert published.status == AssessmentResultPublicationStatus.PUBLISHED
    assert published.requires_approval is False
    assert published.approved_at is None
    assert published.approved_by_id is None
    assert published.published_by_id == teacher_user.id
    assert published.published_at is not None


@pytest.mark.asyncio
async def test_course_teacher_cannot_publish_before_all_marks_are_finalised(
    db_session: AsyncSession,
    teacher_user,
):
    context = await _build_publication_context(
        db_session,
        teacher_user,
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
        decision_status=MarkingDecisionStatus.MARKED,
    )

    publication = await create_result_publication(
        db=db_session,
        current_user=teacher_user,
        assessment_id=context["assessment"].id,
    )

    with pytest.raises(HTTPException) as exc:
        await publish_results(
            db=db_session,
            current_user=teacher_user,
            publication_id=publication.id,
        )

    assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_results_cannot_be_published_when_no_scripts_exist(
    db_session: AsyncSession,
    teacher_user,
):
    course = await _create_course(
        db_session,
        teacher_id=teacher_user.id,
        school_id=teacher_user.school_id,
        title="No Script Publication Course",
    )

    assessment = await _create_assessment(
        db_session,
        teacher_id=teacher_user.id,
        school_id=teacher_user.school_id,
        course_id=course.id,
        title="No Script Assessment",
    )

    await _create_question(
        db_session,
        assessment_id=assessment.id,
        question_number="1",
        maximum_mark=Decimal("10"),
        order=1,
    )

    publication = await create_result_publication(
        db=db_session,
        current_user=teacher_user,
        assessment_id=assessment.id,
    )

    with pytest.raises(HTTPException) as exc:
        await publish_results(
            db=db_session,
            current_user=teacher_user,
            publication_id=publication.id,
        )

    assert exc.value.status_code == 409


# ---------------------------------------------------------------------------
# Controlled approval workflow
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_controlled_assessment_cannot_publish_without_approval(
    db_session: AsyncSession,
    teacher_user,
):
    context = await _build_publication_context(
        db_session,
        teacher_user,
    )

    await _finalise_all_marks(
        db_session,
        teacher_user,
        context,
    )

    publication = await create_result_publication(
        db=db_session,
        current_user=teacher_user,
        assessment_id=context["assessment"].id,
        requires_approval=True,
    )

    with pytest.raises(HTTPException) as exc:
        await publish_results(
            db=db_session,
            current_user=teacher_user,
            publication_id=publication.id,
        )

    assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_teacher_cannot_approve_controlled_assessment(
    db_session: AsyncSession,
    teacher_user,
):
    context = await _build_publication_context(
        db_session,
        teacher_user,
    )

    publication = await create_result_publication(
        db=db_session,
        current_user=teacher_user,
        assessment_id=context["assessment"].id,
        requires_approval=True,
    )

    with pytest.raises(HTTPException) as exc:
        await approve_result_publication(
            db=db_session,
            current_user=teacher_user,
            publication_id=publication.id,
        )

    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_school_admin_can_approve_controlled_assessment(
    db_session: AsyncSession,
    teacher_user,
):
    context = await _build_publication_context(
        db_session,
        teacher_user,
    )

    school_admin = await create_test_user(
        db_session,
        email="publication.school.admin@example.com",
        roles=[UserRole.SCHOOL_ADMIN],
        school_id=teacher_user.school_id,
    )

    publication = await create_result_publication(
        db=db_session,
        current_user=teacher_user,
        assessment_id=context["assessment"].id,
        requires_approval=True,
    )

    approved = await approve_result_publication(
        db=db_session,
        current_user=school_admin,
        publication_id=publication.id,
        approval_note="Approved for release.",
    )

    assert approved.approved_at is not None
    assert approved.approved_by_id == school_admin.id
    assert approved.approval_note == "Approved for release."


@pytest.mark.asyncio
async def test_controlled_assessment_can_publish_after_approval(
    db_session: AsyncSession,
    teacher_user,
):
    context = await _build_publication_context(
        db_session,
        teacher_user,
    )

    await _finalise_all_marks(
        db_session,
        teacher_user,
        context,
    )

    school_admin = await create_test_user(
        db_session,
        email="publication.approval.admin@example.com",
        roles=[UserRole.SCHOOL_ADMIN],
        school_id=teacher_user.school_id,
    )

    publication = await create_result_publication(
        db=db_session,
        current_user=teacher_user,
        assessment_id=context["assessment"].id,
        requires_approval=True,
    )

    await approve_result_publication(
        db=db_session,
        current_user=school_admin,
        publication_id=publication.id,
    )

    published = await publish_results(
        db=db_session,
        current_user=teacher_user,
        publication_id=publication.id,
    )

    assert published.status == AssessmentResultPublicationStatus.PUBLISHED
    assert published.published_by_id == teacher_user.id
    assert published.approved_by_id == school_admin.id


@pytest.mark.asyncio
async def test_approval_can_be_revoked_before_publication(
    db_session: AsyncSession,
    teacher_user,
):
    context = await _build_publication_context(
        db_session,
        teacher_user,
    )

    school_admin = await create_test_user(
        db_session,
        email="publication.revoke.admin@example.com",
        roles=[UserRole.SCHOOL_ADMIN],
        school_id=teacher_user.school_id,
    )

    publication = await create_result_publication(
        db=db_session,
        current_user=teacher_user,
        assessment_id=context["assessment"].id,
        requires_approval=True,
    )

    await approve_result_publication(
        db=db_session,
        current_user=school_admin,
        publication_id=publication.id,
    )

    revoked = await revoke_result_publication_approval(
        db=db_session,
        current_user=school_admin,
        publication_id=publication.id,
    )

    assert revoked.approved_at is None
    assert revoked.approved_by_id is None
    assert revoked.approval_note is None


# ---------------------------------------------------------------------------
# Scheduled publication
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_teacher_can_schedule_completed_results(
    db_session: AsyncSession,
    teacher_user,
):
    context = await _build_publication_context(
        db_session,
        teacher_user,
    )

    await _finalise_all_marks(
        db_session,
        teacher_user,
        context,
    )

    publication = await create_result_publication(
        db=db_session,
        current_user=teacher_user,
        assessment_id=context["assessment"].id,
    )

    scheduled_for = datetime.now(timezone.utc) + timedelta(hours=1)

    scheduled = await schedule_results_publication(
        db=db_session,
        current_user=teacher_user,
        publication_id=publication.id,
        scheduled_for=scheduled_for,
    )

    assert scheduled.status == AssessmentResultPublicationStatus.SCHEDULED
    assert scheduled.scheduled_for is not None


@pytest.mark.asyncio
async def test_schedule_time_must_be_in_future(
    db_session: AsyncSession,
    teacher_user,
):
    context = await _build_publication_context(
        db_session,
        teacher_user,
    )

    await _finalise_all_marks(
        db_session,
        teacher_user,
        context,
    )

    publication = await create_result_publication(
        db=db_session,
        current_user=teacher_user,
        assessment_id=context["assessment"].id,
    )

    with pytest.raises(HTTPException) as exc:
        await schedule_results_publication(
            db=db_session,
            current_user=teacher_user,
            publication_id=publication.id,
            scheduled_for=datetime.now(timezone.utc) - timedelta(minutes=1),
        )

    assert exc.value.status_code == 422


@pytest.mark.asyncio
async def test_due_scheduled_results_are_published(
    db_session: AsyncSession,
    teacher_user,
):
    context = await _build_publication_context(
        db_session,
        teacher_user,
    )

    await _finalise_all_marks(
        db_session,
        teacher_user,
        context,
    )

    publication = await create_result_publication(
        db=db_session,
        current_user=teacher_user,
        assessment_id=context["assessment"].id,
    )

    scheduled_for = datetime.now(timezone.utc) + timedelta(minutes=5)

    await schedule_results_publication(
        db=db_session,
        current_user=teacher_user,
        publication_id=publication.id,
        scheduled_for=scheduled_for,
    )

    published = await publish_due_scheduled_results(
        db=db_session,
        now=scheduled_for + timedelta(seconds=1),
    )

    assert len(published) == 1
    assert published[0].id == publication.id
    assert published[0].status == AssessmentResultPublicationStatus.PUBLISHED


# ---------------------------------------------------------------------------
# Publication notifications
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_authoritative_student_recipient_lookup_is_deduplicated_and_sorted(
    monkeypatch,
):
    calls: list[dict] = []

    class FakeOutcomeRepository:
        def __init__(
            self,
            db,
        ):
            self.db = db

        async def list_for_assessment(
            self,
            assessment_id,
            *,
            school_id,
            authoritative_only,
            include_relationships,
        ):
            calls.append(
                {
                    "assessment_id": assessment_id,
                    "school_id": school_id,
                    "authoritative_only": authoritative_only,
                    "include_relationships": include_relationships,
                }
            )

            class Candidate:
                def __init__(
                    self,
                    student_id,
                ):
                    self.student_id = student_id

            class Outcome:
                def __init__(
                    self,
                    student_id,
                ):
                    self.candidate = Candidate(
                        student_id,
                    )

            return [
                Outcome(103),
                Outcome(101),
                Outcome(103),
                Outcome(102),
            ]

    monkeypatch.setattr(
        publication_service,
        "AssessmentResultOutcomeRepository",
        FakeOutcomeRepository,
    )

    student_ids = (
        await publication_service._get_authoritative_student_ids_for_assessment(
            object(),
            assessment_id=50,
            school_id=1,
        )
    )

    assert student_ids == [
        101,
        102,
        103,
    ]

    assert calls == [
        {
            "assessment_id": 50,
            "school_id": 1,
            "authoritative_only": True,
            "include_relationships": True,
        }
    ]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    (
        "visible_to_students",
        "visible_to_parents",
        "expected_notify_students",
        "expected_notify_parents",
    ),
    [
        (
            True,
            False,
            True,
            False,
        ),
        (
            False,
            True,
            False,
            True,
        ),
        (
            True,
            True,
            True,
            True,
        ),
    ],
)
async def test_publication_notification_maps_audience_visibility_exactly(
    monkeypatch,
    visible_to_students,
    visible_to_parents,
    expected_notify_students,
    expected_notify_parents,
):
    calls: list[dict] = []

    publication = type(
        "Publication",
        (),
        {
            "id": 7,
            "assessment_id": 50,
            "visible_to_students": visible_to_students,
            "visible_to_parents": visible_to_parents,
            "assessment": type(
                "Assessment",
                (),
                {
                    "id": 50,
                    "school_id": 1,
                    "title": "Physics Forces Test",
                },
            )(),
        },
    )()

    async def fake_student_ids(
        db,
        *,
        assessment_id,
        school_id,
    ):
        assert assessment_id == 50
        assert school_id == 1

        return [
            101,
            102,
        ]

    class FakeAssessmentNotificationService:
        def __init__(
            self,
            db,
        ):
            self.db = db

        async def notify_results_published(
            self,
            **kwargs,
        ):
            calls.append(
                kwargs,
            )
            return []

    monkeypatch.setattr(
        publication_service,
        "_get_authoritative_student_ids_for_assessment",
        fake_student_ids,
    )
    monkeypatch.setattr(
        publication_service,
        "AssessmentNotificationService",
        FakeAssessmentNotificationService,
    )

    await publication_service._notify_results_published_best_effort(
        object(),
        publication=publication,
    )

    assert calls == [
        {
            "assessment_id": 50,
            "assessment_title": "Physics Forces Test",
            "school_id": 1,
            "student_ids": [
                101,
                102,
            ],
            "notify_students": expected_notify_students,
            "notify_parents": expected_notify_parents,
        }
    ]


@pytest.mark.asyncio
async def test_publication_notification_is_silent_when_no_audience_is_visible(
    monkeypatch,
):
    publication = type(
        "Publication",
        (),
        {
            "id": 7,
            "assessment_id": 50,
            "visible_to_students": False,
            "visible_to_parents": False,
            "assessment": type(
                "Assessment",
                (),
                {
                    "id": 50,
                    "school_id": 1,
                    "title": "Physics Forces Test",
                },
            )(),
        },
    )()

    lookup_calls: list[tuple] = []

    async def fake_student_ids(
        db,
        *,
        assessment_id,
        school_id,
    ):
        lookup_calls.append(
            (
                assessment_id,
                school_id,
            )
        )
        return [
            101,
        ]

    monkeypatch.setattr(
        publication_service,
        "_get_authoritative_student_ids_for_assessment",
        fake_student_ids,
    )

    await publication_service._notify_results_published_best_effort(
        object(),
        publication=publication,
    )

    assert lookup_calls == []


@pytest.mark.asyncio
async def test_publication_notification_failure_does_not_fail_committed_release(
    monkeypatch,
):
    class FakeDB:
        def __init__(
            self,
        ):
            self.rolled_back = False

        async def rollback(
            self,
        ):
            self.rolled_back = True

    db = FakeDB()

    publication = type(
        "Publication",
        (),
        {
            "id": 7,
            "assessment_id": 50,
            "visible_to_students": True,
            "visible_to_parents": True,
            "assessment": type(
                "Assessment",
                (),
                {
                    "id": 50,
                    "school_id": 1,
                    "title": "Physics Forces Test",
                },
            )(),
        },
    )()

    async def fake_student_ids(
        db,
        *,
        assessment_id,
        school_id,
    ):
        return [
            101,
        ]

    class FailingAssessmentNotificationService:
        def __init__(
            self,
            db,
        ):
            self.db = db

        async def notify_results_published(
            self,
            **kwargs,
        ):
            raise RuntimeError(
                "notification unavailable",
            )

    monkeypatch.setattr(
        publication_service,
        "_get_authoritative_student_ids_for_assessment",
        fake_student_ids,
    )
    monkeypatch.setattr(
        publication_service,
        "AssessmentNotificationService",
        FailingAssessmentNotificationService,
    )

    await publication_service._notify_results_published_best_effort(
        db,
        publication=publication,
    )

    assert db.rolled_back is True


@pytest.mark.asyncio
async def test_immediate_publication_runs_notification_after_successful_release(
    db_session: AsyncSession,
    teacher_user,
    monkeypatch,
):
    context = await _build_publication_context(
        db_session,
        teacher_user,
    )

    await _finalise_all_marks(
        db_session,
        teacher_user,
        context,
    )

    publication = await create_result_publication(
        db=db_session,
        current_user=teacher_user,
        assessment_id=context["assessment"].id,
        visible_to_students=True,
        visible_to_parents=False,
    )

    notification_calls: list[dict] = []

    async def fake_notify(
        db,
        *,
        publication,
    ):
        notification_calls.append(
            {
                "publication_id": publication.id,
                "status": publication.status,
                "visible_to_students": publication.visible_to_students,
                "visible_to_parents": publication.visible_to_parents,
            }
        )

    monkeypatch.setattr(
        publication_service,
        "_notify_results_published_best_effort",
        fake_notify,
    )

    published = await publish_results(
        db=db_session,
        current_user=teacher_user,
        publication_id=publication.id,
    )

    assert published.status == AssessmentResultPublicationStatus.PUBLISHED

    assert notification_calls == [
        {
            "publication_id": publication.id,
            "status": AssessmentResultPublicationStatus.PUBLISHED,
            "visible_to_students": True,
            "visible_to_parents": False,
        }
    ]


@pytest.mark.asyncio
async def test_scheduled_publication_runs_notification_after_successful_release(
    db_session: AsyncSession,
    teacher_user,
    monkeypatch,
):
    context = await _build_publication_context(
        db_session,
        teacher_user,
    )

    await _finalise_all_marks(
        db_session,
        teacher_user,
        context,
    )

    publication = await create_result_publication(
        db=db_session,
        current_user=teacher_user,
        assessment_id=context["assessment"].id,
        visible_to_students=False,
        visible_to_parents=True,
    )

    scheduled_for = datetime.now(
        timezone.utc,
    ) + timedelta(
        minutes=5,
    )

    await schedule_results_publication(
        db=db_session,
        current_user=teacher_user,
        publication_id=publication.id,
        scheduled_for=scheduled_for,
    )

    notification_calls: list[dict] = []

    async def fake_notify(
        db,
        *,
        publication,
    ):
        notification_calls.append(
            {
                "publication_id": publication.id,
                "status": publication.status,
                "visible_to_students": publication.visible_to_students,
                "visible_to_parents": publication.visible_to_parents,
            }
        )

    monkeypatch.setattr(
        publication_service,
        "_notify_results_published_best_effort",
        fake_notify,
    )

    published = await publish_due_scheduled_results(
        db=db_session,
        now=scheduled_for
        + timedelta(
            seconds=1,
        ),
    )

    assert (
        len(
            published,
        )
        == 1
    )
    assert published[0].id == publication.id
    assert published[0].status == AssessmentResultPublicationStatus.PUBLISHED

    assert notification_calls == [
        {
            "publication_id": publication.id,
            "status": AssessmentResultPublicationStatus.PUBLISHED,
            "visible_to_students": False,
            "visible_to_parents": True,
        }
    ]


# ---------------------------------------------------------------------------
# Withdrawal
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_teacher_can_withdraw_published_results(
    db_session: AsyncSession,
    teacher_user,
):
    context = await _build_publication_context(
        db_session,
        teacher_user,
    )

    await _finalise_all_marks(
        db_session,
        teacher_user,
        context,
    )

    publication = await create_result_publication(
        db=db_session,
        current_user=teacher_user,
        assessment_id=context["assessment"].id,
    )

    await publish_results(
        db=db_session,
        current_user=teacher_user,
        publication_id=publication.id,
    )

    withdrawn = await withdraw_results(
        db=db_session,
        current_user=teacher_user,
        publication_id=publication.id,
        withdrawal_reason="Marking correction required.",
    )

    assert withdrawn.status == AssessmentResultPublicationStatus.WITHDRAWN
    assert withdrawn.withdrawn_by_id == teacher_user.id
    assert withdrawn.withdrawn_at is not None
    assert withdrawn.withdrawal_reason == "Marking correction required."


@pytest.mark.asyncio
async def test_unreleased_results_cannot_be_withdrawn(
    db_session: AsyncSession,
    teacher_user,
):
    context = await _build_publication_context(
        db_session,
        teacher_user,
    )

    publication = await create_result_publication(
        db=db_session,
        current_user=teacher_user,
        assessment_id=context["assessment"].id,
    )

    with pytest.raises(HTTPException) as exc:
        await withdraw_results(
            db=db_session,
            current_user=teacher_user,
            publication_id=publication.id,
        )

    assert exc.value.status_code == 409


# ---------------------------------------------------------------------------
# Student and parent visibility
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_published_results_can_be_visible_to_students_and_parents(
    db_session: AsyncSession,
    teacher_user,
):
    context = await _build_publication_context(
        db_session,
        teacher_user,
    )

    await _finalise_all_marks(
        db_session,
        teacher_user,
        context,
    )

    publication = await create_result_publication(
        db=db_session,
        current_user=teacher_user,
        assessment_id=context["assessment"].id,
        visible_to_students=True,
        visible_to_parents=True,
    )

    await publish_results(
        db=db_session,
        current_user=teacher_user,
        publication_id=publication.id,
    )

    assert (
        await can_student_view_results(
            db_session,
            assessment_id=context["assessment"].id,
        )
        is True
    )

    assert (
        await can_parent_view_results(
            db_session,
            assessment_id=context["assessment"].id,
        )
        is True
    )


@pytest.mark.asyncio
async def test_student_visibility_can_be_disabled(
    db_session: AsyncSession,
    teacher_user,
):
    context = await _build_publication_context(
        db_session,
        teacher_user,
    )

    await _finalise_all_marks(
        db_session,
        teacher_user,
        context,
    )

    publication = await create_result_publication(
        db=db_session,
        current_user=teacher_user,
        assessment_id=context["assessment"].id,
        visible_to_students=False,
        visible_to_parents=True,
    )

    await publish_results(
        db=db_session,
        current_user=teacher_user,
        publication_id=publication.id,
    )

    assert (
        await can_student_view_results(
            db_session,
            assessment_id=context["assessment"].id,
        )
        is False
    )

    assert (
        await can_parent_view_results(
            db_session,
            assessment_id=context["assessment"].id,
        )
        is True
    )


@pytest.mark.asyncio
async def test_withdrawn_results_are_no_longer_visible(
    db_session: AsyncSession,
    teacher_user,
):
    context = await _build_publication_context(
        db_session,
        teacher_user,
    )

    await _finalise_all_marks(
        db_session,
        teacher_user,
        context,
    )

    publication = await create_result_publication(
        db=db_session,
        current_user=teacher_user,
        assessment_id=context["assessment"].id,
    )

    await publish_results(
        db=db_session,
        current_user=teacher_user,
        publication_id=publication.id,
    )

    await withdraw_results(
        db=db_session,
        current_user=teacher_user,
        publication_id=publication.id,
    )

    assert (
        await get_published_result_visibility(
            db_session,
            assessment_id=context["assessment"].id,
        )
        is None
    )

    assert (
        await can_student_view_results(
            db_session,
            assessment_id=context["assessment"].id,
        )
        is False
    )

    assert (
        await can_parent_view_results(
            db_session,
            assessment_id=context["assessment"].id,
        )
        is False
    )


# ---------------------------------------------------------------------------
# Access control
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_other_teacher_cannot_create_publication_for_assessment(
    db_session: AsyncSession,
    teacher_user,
):
    context = await _build_publication_context(
        db_session,
        teacher_user,
    )

    other_teacher = await create_test_user(
        db_session,
        email="publication.other.teacher@example.com",
        roles=[UserRole.TEACHER],
        school_id=teacher_user.school_id,
    )

    with pytest.raises(HTTPException) as exc:
        await create_result_publication(
            db=db_session,
            current_user=other_teacher,
            assessment_id=context["assessment"].id,
        )

    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_school_admin_can_create_publication_configuration(
    db_session: AsyncSession,
    teacher_user,
):
    context = await _build_publication_context(
        db_session,
        teacher_user,
    )

    school_admin = await create_test_user(
        db_session,
        email="publication.manage.admin@example.com",
        roles=[UserRole.SCHOOL_ADMIN],
        school_id=teacher_user.school_id,
    )

    publication = await create_result_publication(
        db=db_session,
        current_user=school_admin,
        assessment_id=context["assessment"].id,
    )

    assert publication.created_by_id == school_admin.id


@pytest.mark.asyncio
async def test_student_cannot_manage_publication_configuration(
    db_session: AsyncSession,
    teacher_user,
):
    context = await _build_publication_context(
        db_session,
        teacher_user,
    )

    student = await create_test_user(
        db_session,
        email="publication.unauthorised.student@example.com",
        roles=[UserRole.STUDENT],
        school_id=teacher_user.school_id,
    )

    with pytest.raises(HTTPException) as exc:
        await create_result_publication(
            db=db_session,
            current_user=student,
            assessment_id=context["assessment"].id,
        )

    assert exc.value.status_code == 403


# ---------------------------------------------------------------------------
# Deletion
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_unreleased_publication_configuration_can_be_deleted(
    db_session: AsyncSession,
    teacher_user,
):
    context = await _build_publication_context(
        db_session,
        teacher_user,
    )

    publication = await create_result_publication(
        db=db_session,
        current_user=teacher_user,
        assessment_id=context["assessment"].id,
    )

    await delete_result_publication(
        db=db_session,
        current_user=teacher_user,
        publication_id=publication.id,
    )

    with pytest.raises(HTTPException) as exc:
        await get_result_publication(
            db=db_session,
            current_user=teacher_user,
            assessment_id=context["assessment"].id,
        )

    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_published_publication_must_be_withdrawn_before_delete(
    db_session: AsyncSession,
    teacher_user,
):
    context = await _build_publication_context(
        db_session,
        teacher_user,
    )

    await _finalise_all_marks(
        db_session,
        teacher_user,
        context,
    )

    publication = await create_result_publication(
        db=db_session,
        current_user=teacher_user,
        assessment_id=context["assessment"].id,
    )

    await publish_results(
        db=db_session,
        current_user=teacher_user,
        publication_id=publication.id,
    )

    with pytest.raises(HTTPException) as exc:
        await delete_result_publication(
            db=db_session,
            current_user=teacher_user,
            publication_id=publication.id,
        )

    assert exc.value.status_code == 409
