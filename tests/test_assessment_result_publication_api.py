from __future__ import annotations

from datetime import datetime, timedelta, timezone
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
    title: str = "Assessment Publication API Course",
) -> Course:
    course = Course(
        title=title,
        description="Course used by assessment publication API tests.",
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
        description="Assessment publication API test.",
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
        source_filename=f"publication-api-v{version}.pdf",
        storage_key=f"assessment-publication/publication-api-v{version}.pdf",
        mime_type="application/pdf",
        checksum=f"publication-api-{candidate_id}-{version}",
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
        email=f"publication.api.student.{assessment.id}@example.com",
        roles=[UserRole.STUDENT],
        school_id=teacher_user.school_id,
    )

    candidate = await _create_candidate(
        db_session,
        assessment_id=assessment.id,
        student_id=student.id,
        candidate_number="PUB-API-001",
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


async def _create_publication_via_api(
    client: AsyncClient,
    *,
    assessment_id: int,
    headers: dict[str, str],
    requires_approval: bool = False,
    visible_to_students: bool = True,
    visible_to_parents: bool = True,
):
    response = await client.post(
        ("/api/v1/assessment-result-publication/assessments/" f"{assessment_id}"),
        json={
            "requires_approval": requires_approval,
            "visible_to_students": visible_to_students,
            "visible_to_parents": visible_to_parents,
            "include_mark": True,
            "include_percentage": True,
            "include_grade": True,
            "include_question_breakdown": False,
            "release_message": "Results are available.",
        },
        headers=headers,
    )

    assert response.status_code == 201, response.text

    return response.json()


# ---------------------------------------------------------------------------
# Configuration API
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_teacher_can_create_publication_configuration(
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
            "/api/v1/assessment-result-publication/assessments/"
            f"{context['assessment'].id}"
        ),
        json={
            "requires_approval": False,
            "visible_to_students": True,
            "visible_to_parents": True,
            "include_mark": True,
            "include_percentage": True,
            "include_grade": True,
            "include_question_breakdown": False,
            "release_message": " End of topic results ",
        },
        headers=auth_headers(teacher_user),
    )

    assert response.status_code == 201, response.text

    data = response.json()

    assert data["assessment_id"] == context["assessment"].id
    assert data["status"] == "unreleased"
    assert data["requires_approval"] is False
    assert data["visible_to_students"] is True
    assert data["visible_to_parents"] is True
    assert data["include_mark"] is True
    assert data["include_percentage"] is True
    assert data["include_grade"] is True
    assert data["include_question_breakdown"] is False
    assert data["release_message"] == "End of topic results"
    assert data["created_by_id"] == teacher_user.id
    assert data["is_published"] is False
    assert data["is_approved"] is True
    assert data["can_release"] is True


@pytest.mark.asyncio
async def test_duplicate_publication_configuration_is_rejected_via_api(
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

    await _create_publication_via_api(
        client,
        assessment_id=context["assessment"].id,
        headers=headers,
    )

    response = await client.post(
        (
            "/api/v1/assessment-result-publication/assessments/"
            f"{context['assessment'].id}"
        ),
        json={},
        headers=headers,
    )

    assert response.status_code == 409


@pytest.mark.asyncio
async def test_teacher_can_get_publication_configuration(
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

    created = await _create_publication_via_api(
        client,
        assessment_id=context["assessment"].id,
        headers=headers,
    )

    response = await client.get(
        (
            "/api/v1/assessment-result-publication/assessments/"
            f"{context['assessment'].id}"
        ),
        headers=headers,
    )

    assert response.status_code == 200, response.text
    assert response.json()["id"] == created["id"]


@pytest.mark.asyncio
async def test_missing_publication_configuration_returns_404(
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
            "/api/v1/assessment-result-publication/assessments/"
            f"{context['assessment'].id}"
        ),
        headers=auth_headers(teacher_user),
    )

    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Update API
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_teacher_can_update_publication_configuration(
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

    publication = await _create_publication_via_api(
        client,
        assessment_id=context["assessment"].id,
        headers=headers,
    )

    response = await client.patch(
        ("/api/v1/assessment-result-publication/publications/" f"{publication['id']}"),
        json={
            "visible_to_students": False,
            "visible_to_parents": True,
            "include_mark": False,
            "include_percentage": True,
            "include_grade": True,
            "include_question_breakdown": True,
            "release_message": "Updated release message",
        },
        headers=headers,
    )

    assert response.status_code == 200, response.text

    data = response.json()

    assert data["visible_to_students"] is False
    assert data["visible_to_parents"] is True
    assert data["include_mark"] is False
    assert data["include_percentage"] is True
    assert data["include_grade"] is True
    assert data["include_question_breakdown"] is True
    assert data["release_message"] == "Updated release message"


@pytest.mark.asyncio
async def test_release_message_can_be_cleared_via_api(
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

    publication = await _create_publication_via_api(
        client,
        assessment_id=context["assessment"].id,
        headers=headers,
    )

    response = await client.patch(
        ("/api/v1/assessment-result-publication/publications/" f"{publication['id']}"),
        json={
            "release_message": None,
        },
        headers=headers,
    )

    assert response.status_code == 200, response.text
    assert response.json()["release_message"] is None


# ---------------------------------------------------------------------------
# Direct teacher publication
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_course_teacher_can_publish_end_of_topic_results_without_smt(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
):
    context = await _build_context(
        db_session,
        teacher_user,
    )

    await _finalise_all_marks(
        db_session,
        teacher_user,
        context,
    )

    headers = auth_headers(teacher_user)

    publication = await _create_publication_via_api(
        client,
        assessment_id=context["assessment"].id,
        headers=headers,
        requires_approval=False,
    )

    response = await client.post(
        (
            "/api/v1/assessment-result-publication/publications/"
            f"{publication['id']}/publish"
        ),
        headers=headers,
    )

    assert response.status_code == 200, response.text

    data = response.json()

    assert data["status"] == "published"
    assert data["requires_approval"] is False
    assert data["approved_at"] is None
    assert data["approved_by_id"] is None
    assert data["published_by_id"] == teacher_user.id
    assert data["published_at"] is not None
    assert data["is_published"] is True


@pytest.mark.asyncio
async def test_teacher_cannot_publish_until_all_marks_finalised(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
):
    context = await _build_context(
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

    headers = auth_headers(teacher_user)

    publication = await _create_publication_via_api(
        client,
        assessment_id=context["assessment"].id,
        headers=headers,
    )

    response = await client.post(
        (
            "/api/v1/assessment-result-publication/publications/"
            f"{publication['id']}/publish"
        ),
        headers=headers,
    )

    assert response.status_code == 409


@pytest.mark.asyncio
async def test_publishing_already_published_results_is_rejected(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
):
    context = await _build_context(
        db_session,
        teacher_user,
    )

    await _finalise_all_marks(
        db_session,
        teacher_user,
        context,
    )

    headers = auth_headers(teacher_user)

    publication = await _create_publication_via_api(
        client,
        assessment_id=context["assessment"].id,
        headers=headers,
    )

    url = (
        "/api/v1/assessment-result-publication/publications/"
        f"{publication['id']}/publish"
    )

    first = await client.post(
        url,
        headers=headers,
    )

    assert first.status_code == 200, first.text

    second = await client.post(
        url,
        headers=headers,
    )

    assert second.status_code == 409


# ---------------------------------------------------------------------------
# Controlled approval API
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_controlled_results_cannot_publish_without_approval_via_api(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
):
    context = await _build_context(
        db_session,
        teacher_user,
    )

    await _finalise_all_marks(
        db_session,
        teacher_user,
        context,
    )

    headers = auth_headers(teacher_user)

    publication = await _create_publication_via_api(
        client,
        assessment_id=context["assessment"].id,
        headers=headers,
        requires_approval=True,
    )

    response = await client.post(
        (
            "/api/v1/assessment-result-publication/publications/"
            f"{publication['id']}/publish"
        ),
        headers=headers,
    )

    assert response.status_code == 409


@pytest.mark.asyncio
async def test_teacher_cannot_approve_controlled_results_via_api(
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

    publication = await _create_publication_via_api(
        client,
        assessment_id=context["assessment"].id,
        headers=headers,
        requires_approval=True,
    )

    response = await client.post(
        (
            "/api/v1/assessment-result-publication/publications/"
            f"{publication['id']}/approve"
        ),
        json={
            "approval_note": "Teacher self approval",
        },
        headers=headers,
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_school_admin_can_approve_controlled_results_via_api(
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
        email="publication.api.school.admin@example.com",
        roles=[UserRole.SCHOOL_ADMIN],
        school_id=teacher_user.school_id,
    )

    teacher_headers = auth_headers(teacher_user)

    publication = await _create_publication_via_api(
        client,
        assessment_id=context["assessment"].id,
        headers=teacher_headers,
        requires_approval=True,
    )

    response = await client.post(
        (
            "/api/v1/assessment-result-publication/publications/"
            f"{publication['id']}/approve"
        ),
        json={
            "approval_note": "Approved for publication.",
        },
        headers=auth_headers(school_admin),
    )

    assert response.status_code == 200, response.text

    data = response.json()

    assert data["approved_by_id"] == school_admin.id
    assert data["approved_at"] is not None
    assert data["approval_note"] == "Approved for publication."
    assert data["is_approved"] is True


@pytest.mark.asyncio
async def test_teacher_can_publish_controlled_results_after_admin_approval(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
):
    context = await _build_context(
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
        email="publication.api.approval.admin@example.com",
        roles=[UserRole.SCHOOL_ADMIN],
        school_id=teacher_user.school_id,
    )

    teacher_headers = auth_headers(teacher_user)

    publication = await _create_publication_via_api(
        client,
        assessment_id=context["assessment"].id,
        headers=teacher_headers,
        requires_approval=True,
    )

    approval_response = await client.post(
        (
            "/api/v1/assessment-result-publication/publications/"
            f"{publication['id']}/approve"
        ),
        json={},
        headers=auth_headers(school_admin),
    )

    assert approval_response.status_code == 200, approval_response.text

    publish_response = await client.post(
        (
            "/api/v1/assessment-result-publication/publications/"
            f"{publication['id']}/publish"
        ),
        headers=teacher_headers,
    )

    assert publish_response.status_code == 200, publish_response.text

    data = publish_response.json()

    assert data["status"] == "published"
    assert data["published_by_id"] == teacher_user.id
    assert data["approved_by_id"] == school_admin.id


@pytest.mark.asyncio
async def test_school_admin_can_revoke_approval_before_publication(
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
        email="publication.api.revoke.admin@example.com",
        roles=[UserRole.SCHOOL_ADMIN],
        school_id=teacher_user.school_id,
    )

    teacher_headers = auth_headers(teacher_user)
    admin_headers = auth_headers(school_admin)

    publication = await _create_publication_via_api(
        client,
        assessment_id=context["assessment"].id,
        headers=teacher_headers,
        requires_approval=True,
    )

    approval_response = await client.post(
        (
            "/api/v1/assessment-result-publication/publications/"
            f"{publication['id']}/approve"
        ),
        json={},
        headers=admin_headers,
    )

    assert approval_response.status_code == 200, approval_response.text

    response = await client.post(
        (
            "/api/v1/assessment-result-publication/publications/"
            f"{publication['id']}/revoke-approval"
        ),
        headers=admin_headers,
    )

    assert response.status_code == 200, response.text

    data = response.json()

    assert data["approved_at"] is None
    assert data["approved_by_id"] is None
    assert data["approval_note"] is None
    assert data["is_approved"] is False


# ---------------------------------------------------------------------------
# Scheduling API
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_teacher_can_schedule_completed_results(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
):
    context = await _build_context(
        db_session,
        teacher_user,
    )

    await _finalise_all_marks(
        db_session,
        teacher_user,
        context,
    )

    headers = auth_headers(teacher_user)

    publication = await _create_publication_via_api(
        client,
        assessment_id=context["assessment"].id,
        headers=headers,
    )

    scheduled_for = datetime.now(timezone.utc) + timedelta(hours=1)

    response = await client.post(
        (
            "/api/v1/assessment-result-publication/publications/"
            f"{publication['id']}/schedule"
        ),
        json={
            "scheduled_for": scheduled_for.isoformat(),
        },
        headers=headers,
    )

    assert response.status_code == 200, response.text

    data = response.json()

    assert data["status"] == "scheduled"
    assert data["scheduled_for"] is not None
    assert data["is_scheduled"] is True


@pytest.mark.asyncio
async def test_schedule_time_in_past_is_rejected_via_api(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
):
    context = await _build_context(
        db_session,
        teacher_user,
    )

    await _finalise_all_marks(
        db_session,
        teacher_user,
        context,
    )

    headers = auth_headers(teacher_user)

    publication = await _create_publication_via_api(
        client,
        assessment_id=context["assessment"].id,
        headers=headers,
    )

    scheduled_for = datetime.now(timezone.utc) - timedelta(minutes=1)

    response = await client.post(
        (
            "/api/v1/assessment-result-publication/publications/"
            f"{publication['id']}/schedule"
        ),
        json={
            "scheduled_for": scheduled_for.isoformat(),
        },
        headers=headers,
    )

    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Withdrawal API
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_teacher_can_withdraw_published_results(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
):
    context = await _build_context(
        db_session,
        teacher_user,
    )

    await _finalise_all_marks(
        db_session,
        teacher_user,
        context,
    )

    headers = auth_headers(teacher_user)

    publication = await _create_publication_via_api(
        client,
        assessment_id=context["assessment"].id,
        headers=headers,
    )

    publish_response = await client.post(
        (
            "/api/v1/assessment-result-publication/publications/"
            f"{publication['id']}/publish"
        ),
        headers=headers,
    )

    assert publish_response.status_code == 200, publish_response.text

    response = await client.post(
        (
            "/api/v1/assessment-result-publication/publications/"
            f"{publication['id']}/withdraw"
        ),
        json={
            "withdrawal_reason": " Marking correction required. ",
        },
        headers=headers,
    )

    assert response.status_code == 200, response.text

    data = response.json()

    assert data["status"] == "withdrawn"
    assert data["withdrawn_by_id"] == teacher_user.id
    assert data["withdrawn_at"] is not None
    assert data["withdrawal_reason"] == "Marking correction required."
    assert data["is_published"] is False


@pytest.mark.asyncio
async def test_unreleased_results_cannot_be_withdrawn_via_api(
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

    publication = await _create_publication_via_api(
        client,
        assessment_id=context["assessment"].id,
        headers=headers,
    )

    response = await client.post(
        (
            "/api/v1/assessment-result-publication/publications/"
            f"{publication['id']}/withdraw"
        ),
        json={},
        headers=headers,
    )

    assert response.status_code == 409


# ---------------------------------------------------------------------------
# Published visibility API
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_published_visibility_returns_release_settings(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
):
    context = await _build_context(
        db_session,
        teacher_user,
    )

    await _finalise_all_marks(
        db_session,
        teacher_user,
        context,
    )

    headers = auth_headers(teacher_user)

    publication = await _create_publication_via_api(
        client,
        assessment_id=context["assessment"].id,
        headers=headers,
        visible_to_students=True,
        visible_to_parents=False,
    )

    publish_response = await client.post(
        (
            "/api/v1/assessment-result-publication/publications/"
            f"{publication['id']}/publish"
        ),
        headers=headers,
    )

    assert publish_response.status_code == 200, publish_response.text

    response = await client.get(
        (
            "/api/v1/assessment-result-publication/assessments/"
            f"{context['assessment'].id}/published-visibility"
        ),
        headers=headers,
    )

    assert response.status_code == 200, response.text

    data = response.json()

    assert data["assessment_id"] == context["assessment"].id
    assert data["status"] == "published"
    assert data["visible_to_students"] is True
    assert data["visible_to_parents"] is False
    assert data["include_mark"] is True
    assert data["include_percentage"] is True
    assert data["include_grade"] is True
    assert data["include_question_breakdown"] is False
    assert data["published_at"] is not None


@pytest.mark.asyncio
async def test_published_visibility_returns_null_when_not_published(
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

    await _create_publication_via_api(
        client,
        assessment_id=context["assessment"].id,
        headers=headers,
    )

    response = await client.get(
        (
            "/api/v1/assessment-result-publication/assessments/"
            f"{context['assessment'].id}/published-visibility"
        ),
        headers=headers,
    )

    assert response.status_code == 200, response.text
    assert response.json() is None


# ---------------------------------------------------------------------------
# Access control
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_other_teacher_cannot_create_publication_configuration(
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
        email="publication.api.other.teacher@example.com",
        roles=[UserRole.TEACHER],
        school_id=teacher_user.school_id,
    )

    response = await client.post(
        (
            "/api/v1/assessment-result-publication/assessments/"
            f"{context['assessment'].id}"
        ),
        json={},
        headers=auth_headers(other_teacher),
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_other_teacher_cannot_view_publication_configuration(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
):
    context = await _build_context(
        db_session,
        teacher_user,
    )

    teacher_headers = auth_headers(teacher_user)

    await _create_publication_via_api(
        client,
        assessment_id=context["assessment"].id,
        headers=teacher_headers,
    )

    other_teacher = await create_test_user(
        db_session,
        email="publication.api.other.viewer@example.com",
        roles=[UserRole.TEACHER],
        school_id=teacher_user.school_id,
    )

    response = await client.get(
        (
            "/api/v1/assessment-result-publication/assessments/"
            f"{context['assessment'].id}"
        ),
        headers=auth_headers(other_teacher),
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_school_admin_can_create_publication_configuration(
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
        email="publication.api.manage.admin@example.com",
        roles=[UserRole.SCHOOL_ADMIN],
        school_id=teacher_user.school_id,
    )

    response = await client.post(
        (
            "/api/v1/assessment-result-publication/assessments/"
            f"{context['assessment'].id}"
        ),
        json={},
        headers=auth_headers(school_admin),
    )

    assert response.status_code == 201, response.text
    assert response.json()["created_by_id"] == school_admin.id


@pytest.mark.asyncio
async def test_student_cannot_manage_publication_configuration(
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
        email="publication.api.unauthorised.student@example.com",
        roles=[UserRole.STUDENT],
        school_id=teacher_user.school_id,
    )

    response = await client.post(
        (
            "/api/v1/assessment-result-publication/assessments/"
            f"{context['assessment'].id}"
        ),
        json={},
        headers=auth_headers(student),
    )

    assert response.status_code == 403


# ---------------------------------------------------------------------------
# Deletion API
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_teacher_can_delete_unreleased_publication_configuration(
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

    publication = await _create_publication_via_api(
        client,
        assessment_id=context["assessment"].id,
        headers=headers,
    )

    response = await client.delete(
        ("/api/v1/assessment-result-publication/publications/" f"{publication['id']}"),
        headers=headers,
    )

    assert response.status_code == 204

    get_response = await client.get(
        (
            "/api/v1/assessment-result-publication/assessments/"
            f"{context['assessment'].id}"
        ),
        headers=headers,
    )

    assert get_response.status_code == 404


@pytest.mark.asyncio
async def test_published_configuration_must_be_withdrawn_before_delete_via_api(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
):
    context = await _build_context(
        db_session,
        teacher_user,
    )

    await _finalise_all_marks(
        db_session,
        teacher_user,
        context,
    )

    headers = auth_headers(teacher_user)

    publication = await _create_publication_via_api(
        client,
        assessment_id=context["assessment"].id,
        headers=headers,
    )

    publish_response = await client.post(
        (
            "/api/v1/assessment-result-publication/publications/"
            f"{publication['id']}/publish"
        ),
        headers=headers,
    )

    assert publish_response.status_code == 200, publish_response.text

    response = await client.delete(
        ("/api/v1/assessment-result-publication/publications/" f"{publication['id']}"),
        headers=headers,
    )

    assert response.status_code == 409
