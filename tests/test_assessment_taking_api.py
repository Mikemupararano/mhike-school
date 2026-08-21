from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.assessment import Assessment, AssessmentStatus
from app.models.assessment_candidate import (
    AssessmentCandidate,
    AssessmentCandidateStatus,
    AssessmentScript,
    AssessmentScriptStatus,
)
from app.models.assessment_question import (
    AssessmentQuestion,
    AssessmentQuestionAsset,
    AssessmentQuestionAssetType,
    AssessmentQuestionType,
)
from app.models.assessment_response import (
    AssessmentResponse,
    AssessmentResponseStatus,
)
from app.models.course import Course
from app.models.user import UserRole
from app.services import assessment_document_service
from tests.conftest import create_test_user


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


async def _create_course(
    db_session: AsyncSession,
    *,
    teacher_id: int,
    school_id: int,
    title: str = "Assessment Taking API Course",
) -> Course:
    course = Course(
        title=title,
        description="Course used by student assessment-taking API tests.",
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
    title: str = "Assessment Taking API Assessment",
    assessment_status: AssessmentStatus = AssessmentStatus.PUBLISHED,
    scheduled_at: datetime | None = None,
    closes_at: datetime | None = None,
) -> Assessment:
    assessment = Assessment(
        school_id=school_id,
        course_id=course_id,
        created_by_id=teacher_id,
        title=title,
        description="Student assessment-taking API test.",
        assessment_type="class_test",
        academic_year="2026/27",
        term="Autumn",
        status=assessment_status,
        anonymous_marking=False,
        scheduled_at=scheduled_at,
        closes_at=closes_at,
    )
    db_session.add(assessment)
    await db_session.commit()
    await db_session.refresh(assessment)
    return assessment


async def _create_assessment_for_teacher(
    db_session: AsyncSession,
    teacher_user,
    *,
    title: str = "Assessment Taking API Assessment",
    assessment_status: AssessmentStatus = AssessmentStatus.PUBLISHED,
    scheduled_at: datetime | None = None,
    closes_at: datetime | None = None,
) -> Assessment:
    course = await _create_course(
        db_session,
        teacher_id=teacher_user.id,
        school_id=teacher_user.school_id,
        title=f"{title} Course",
    )
    return await _create_assessment(
        db_session,
        teacher_id=teacher_user.id,
        school_id=teacher_user.school_id,
        course_id=course.id,
        title=title,
        assessment_status=assessment_status,
        scheduled_at=scheduled_at,
        closes_at=closes_at,
    )


async def _create_student(
    db_session: AsyncSession,
    *,
    school_id: int,
    email: str,
    is_active: bool = True,
):
    return await create_test_user(
        db_session,
        email=email,
        roles=[UserRole.STUDENT],
        school_id=school_id,
        is_active=is_active,
    )


async def _allocate_candidate(
    db_session: AsyncSession,
    *,
    assessment_id: int,
    student_id: int,
    candidate_number: str = "TAKE-001",
    candidate_status: AssessmentCandidateStatus = AssessmentCandidateStatus.ALLOCATED,
) -> AssessmentCandidate:
    candidate = AssessmentCandidate(
        assessment_id=assessment_id,
        student_id=student_id,
        status=candidate_status,
        candidate_number=candidate_number,
        access_arrangements=None,
    )
    db_session.add(candidate)
    await db_session.commit()
    await db_session.refresh(candidate)
    return candidate


async def _create_question(
    db_session: AsyncSession,
    *,
    assessment_id: int,
    question_number: str = "1",
    prompt: str = "State the relative charge of an electron.",
    question_type: AssessmentQuestionType = AssessmentQuestionType.WRITTEN,
    order: int = 1,
    is_markable: bool = True,
    interaction_config: dict | None = None,
) -> AssessmentQuestion:
    question = AssessmentQuestion(
        assessment_id=assessment_id,
        section_id=None,
        parent_question_id=None,
        question_number=question_number,
        title=None,
        prompt=prompt,
        question_type=question_type.value,
        maximum_mark=Decimal("1"),
        order=order,
        is_markable=is_markable,
        interaction_config=interaction_config,
    )
    db_session.add(question)
    await db_session.commit()
    await db_session.refresh(question)
    return question


async def _create_asset(
    db_session: AsyncSession,
    *,
    question_id: int,
    storage_path: Path,
    candidate_visible: bool = True,
    order: int = 1,
) -> AssessmentQuestionAsset:
    asset = AssessmentQuestionAsset(
        question_id=question_id,
        asset_type=AssessmentQuestionAssetType.FIGURE.value,
        storage_path=str(storage_path),
        original_filename=storage_path.name,
        mime_type="image/png",
        file_size_bytes=storage_path.stat().st_size if storage_path.exists() else None,
        alt_text="Assessment diagram.",
        caption=None,
        order=order,
        candidate_visible=candidate_visible,
        source_document_id=None,
        source_page_number=None,
        source_bbox=None,
    )
    db_session.add(asset)
    await db_session.commit()
    await db_session.refresh(asset)
    return asset


async def _start_attempt(
    client: AsyncClient,
    *,
    assessment_id: int,
    student,
    auth_headers,
):
    response = await client.post(
        f"/api/v1/student-assessments/{assessment_id}/start",
        headers=auth_headers(student),
    )
    assert response.status_code == 200, response.text
    return response


@pytest.fixture
def assessment_upload_root(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> Path:
    upload_root = tmp_path / "assessment_taking_api_uploads"
    monkeypatch.setattr(
        assessment_document_service,
        "ASSESSMENT_UPLOAD_ROOT",
        upload_root,
    )
    return upload_root


@pytest.mark.asyncio
async def test_student_can_list_only_own_assessment_allocations(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
):
    own_assessment = await _create_assessment_for_teacher(
        db_session,
        teacher_user,
        title="Own Student Assessment",
    )
    other_assessment = await _create_assessment_for_teacher(
        db_session,
        teacher_user,
        title="Other Student Assessment",
    )
    student = await _create_student(
        db_session,
        school_id=teacher_user.school_id,
        email="taking.list.own@example.com",
    )
    other_student = await _create_student(
        db_session,
        school_id=teacher_user.school_id,
        email="taking.list.other@example.com",
    )
    await _allocate_candidate(
        db_session,
        assessment_id=own_assessment.id,
        student_id=student.id,
        candidate_number="OWN-001",
    )
    await _allocate_candidate(
        db_session,
        assessment_id=other_assessment.id,
        student_id=other_student.id,
        candidate_number="OTHER-001",
    )

    response = await client.get(
        "/api/v1/student-assessments",
        headers=auth_headers(student),
    )
    assert response.status_code == 200, response.text

    data = response.json()
    assert len(data) == 1
    assert data[0]["assessment_id"] == own_assessment.id
    assert data[0]["candidate_status"] == AssessmentCandidateStatus.ALLOCATED.value
    assert data[0]["can_start"] is True
    assert "candidate_number" not in data[0]
    assert "access_arrangements" not in data[0]
    assert "student_id" not in data[0]


@pytest.mark.asyncio
async def test_teacher_cannot_use_student_assessment_routes(
    client: AsyncClient,
    teacher_user,
    auth_headers,
):
    response = await client.get(
        "/api/v1/student-assessments",
        headers=auth_headers(teacher_user),
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_student_cannot_read_another_students_allocation(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
):
    assessment = await _create_assessment_for_teacher(
        db_session,
        teacher_user,
        title="Ownership Boundary Assessment",
    )
    owner = await _create_student(
        db_session,
        school_id=teacher_user.school_id,
        email="taking.owner@example.com",
    )
    other_student = await _create_student(
        db_session,
        school_id=teacher_user.school_id,
        email="taking.nonowner@example.com",
    )
    await _allocate_candidate(
        db_session,
        assessment_id=assessment.id,
        student_id=owner.id,
    )

    response = await client.get(
        f"/api/v1/student-assessments/{assessment.id}",
        headers=auth_headers(other_student),
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_student_cannot_start_draft_or_outside_time_window(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
):
    student = await _create_student(
        db_session,
        school_id=teacher_user.school_id,
        email="taking.window@example.com",
    )
    student_id = student.id
    student_headers = auth_headers(student)

    draft = await _create_assessment_for_teacher(
        db_session,
        teacher_user,
        title="Draft Student Assessment",
        assessment_status=AssessmentStatus.DRAFT,
    )
    draft_id = draft.id

    future = await _create_assessment_for_teacher(
        db_session,
        teacher_user,
        title="Future Student Assessment",
        scheduled_at=_utc_now() + timedelta(hours=2),
    )
    future_id = future.id

    closed = await _create_assessment_for_teacher(
        db_session,
        teacher_user,
        title="Closed Student Assessment",
        scheduled_at=_utc_now() - timedelta(hours=2),
        closes_at=_utc_now() - timedelta(minutes=1),
    )
    closed_id = closed.id

    for assessment_id in (draft_id, future_id, closed_id):
        await _allocate_candidate(
            db_session,
            assessment_id=assessment_id,
            student_id=student_id,
            candidate_number=f"TAKE-{assessment_id}",
        )
        response = await client.post(
            f"/api/v1/student-assessments/{assessment_id}/start",
            headers=student_headers,
        )
        assert response.status_code == 409


@pytest.mark.asyncio
async def test_student_start_is_idempotent_and_reuses_browser_script(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
):
    assessment = await _create_assessment_for_teacher(
        db_session,
        teacher_user,
        title="Idempotent Student Assessment",
    )
    await _create_question(
        db_session,
        assessment_id=assessment.id,
    )
    student = await _create_student(
        db_session,
        school_id=teacher_user.school_id,
        email="taking.start.idempotent@example.com",
    )
    candidate = await _allocate_candidate(
        db_session,
        assessment_id=assessment.id,
        student_id=student.id,
    )

    first = (
        await _start_attempt(
            client,
            assessment_id=assessment.id,
            student=student,
            auth_headers=auth_headers,
        )
    ).json()
    second = (
        await _start_attempt(
            client,
            assessment_id=assessment.id,
            student=student,
            auth_headers=auth_headers,
        )
    ).json()

    assert first["message"] == "Assessment started."
    assert second["message"] == "Assessment resumed."
    assert second["script"]["id"] == first["script"]["id"]
    assert second["script"]["version"] == first["script"]["version"]

    result = await db_session.execute(
        select(AssessmentScript).where(
            AssessmentScript.candidate_id == candidate.id,
        )
    )
    scripts = list(result.scalars().all())
    assert len(scripts) == 1
    assert scripts[0].source_type == "browser"


@pytest.mark.asyncio
async def test_attempt_exposes_safe_asset_metadata_only(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
    assessment_upload_root: Path,
):
    assessment = await _create_assessment_for_teacher(
        db_session,
        teacher_user,
        title="Safe Payload Assessment",
    )
    question = await _create_question(
        db_session,
        assessment_id=assessment.id,
        prompt="Use the diagram.",
    )
    asset_path = (
        assessment_upload_root
        / str(teacher_user.school_id)
        / str(assessment.id)
        / "question-extraction-assets"
        / "document-1"
        / "v1"
        / "safe.png"
    )
    asset_path.parent.mkdir(parents=True, exist_ok=True)
    asset_path.write_bytes(b"safe-asset")
    asset = await _create_asset(
        db_session,
        question_id=question.id,
        storage_path=asset_path,
    )

    assessment_id = assessment.id
    question_id = question.id
    asset_id = asset.id

    student = await _create_student(
        db_session,
        school_id=teacher_user.school_id,
        email="taking.payload.safe@example.com",
    )
    student_headers = auth_headers(student)

    await _allocate_candidate(
        db_session,
        assessment_id=assessment_id,
        student_id=student.id,
    )
    await db_session.refresh(student)
    student_headers = auth_headers(student)

    await _start_attempt(
        client,
        assessment_id=assessment_id,
        student=student,
        auth_headers=auth_headers,
    )
    await db_session.refresh(student)
    student_headers = auth_headers(student)

    response = await client.get(
        f"/api/v1/student-assessments/{assessment_id}/attempt",
        headers=student_headers,
    )
    assert response.status_code == 200, response.text

    asset_data = response.json()["questions"][0]["assets"][0]
    assert asset_data["id"] == asset_id
    assert asset_data["content_url"] == (
        f"/api/v1/student-assessments/{assessment_id}"
        f"/questions/{question_id}/assets/{asset_id}/content"
    )
    for forbidden in (
        "storage_path",
        "original_filename",
        "mime_type",
        "source_document_id",
        "source_page_number",
        "source_bbox",
    ):
        assert forbidden not in asset_data


@pytest.mark.asyncio
async def test_student_can_autosave_written_response(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
):
    assessment = await _create_assessment_for_teacher(
        db_session,
        teacher_user,
        title="Written Autosave Assessment",
    )
    question = await _create_question(
        db_session,
        assessment_id=assessment.id,
        prompt="Explain why isotopes have similar chemical properties.",
    )
    student = await _create_student(
        db_session,
        school_id=teacher_user.school_id,
        email="taking.autosave.written@example.com",
    )
    await _allocate_candidate(
        db_session,
        assessment_id=assessment.id,
        student_id=student.id,
    )
    await _start_attempt(
        client,
        assessment_id=assessment.id,
        student=student,
        auth_headers=auth_headers,
    )

    response = await client.put(
        f"/api/v1/student-assessments/{assessment.id}/responses/{question.id}",
        json={
            "response_text": "They have the same electron arrangement.",
            "response_data": None,
        },
        headers=auth_headers(student),
    )
    assert response.status_code == 200, response.text

    data = response.json()
    assert data["question_id"] == question.id
    assert data["status"] == AssessmentResponseStatus.IN_PROGRESS.value
    assert data["response_text"] == "They have the same electron arrangement."
    assert "script_id" not in data
    assert "source_reference" not in data
    assert "marking_decision" not in data


@pytest.mark.asyncio
async def test_diagram_annotation_enforces_exact_visible_asset(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
    assessment_upload_root: Path,
):
    assessment = await _create_assessment_for_teacher(
        db_session,
        teacher_user,
        title="Diagram Integrity Assessment",
    )
    diagram_question = await _create_question(
        db_session,
        assessment_id=assessment.id,
        question_number="1",
        prompt="Place the particle symbol.",
        question_type=AssessmentQuestionType.DIAGRAM_ANNOTATION,
        order=1,
    )
    other_question = await _create_question(
        db_session,
        assessment_id=assessment.id,
        question_number="2",
        prompt="Other question.",
        order=2,
    )

    root = (
        assessment_upload_root
        / str(teacher_user.school_id)
        / str(assessment.id)
    )
    root.mkdir(parents=True, exist_ok=True)

    good_path = root / "good.png"
    bad_path = root / "other.png"
    good_path.write_bytes(b"good")
    bad_path.write_bytes(b"other")

    good_asset = await _create_asset(
        db_session,
        question_id=diagram_question.id,
        storage_path=good_path,
    )
    other_asset = await _create_asset(
        db_session,
        question_id=other_question.id,
        storage_path=bad_path,
    )

    assessment_id = assessment.id
    diagram_question_id = diagram_question.id
    good_asset_id = good_asset.id
    other_asset_id = other_asset.id

    student = await _create_student(
        db_session,
        school_id=teacher_user.school_id,
        email="taking.diagram@example.com",
    )
    student_id = student.id
    student_headers = auth_headers(student)

    await _allocate_candidate(
        db_session,
        assessment_id=assessment_id,
        student_id=student_id,
    )
    await _start_attempt(
        client,
        assessment_id=assessment_id,
        student=student,
        auth_headers=auth_headers,
    )

    # _start_attempt may commit, so build a fresh reusable header while the
    # student object is still valid inside the completed async operation.
    await db_session.refresh(student)
    student_headers = auth_headers(student)

    bad_response = await client.put(
        f"/api/v1/student-assessments/{assessment_id}/responses/{diagram_question_id}",
        json={
            "response_data": {
                "type": "diagram_annotation",
                "version": 1,
                "asset_id": other_asset_id,
                "annotations": [
                    {
                        "id": "annotation-1",
                        "symbol": "electron",
                        "x": 0.25,
                        "y": 0.50,
                    }
                ],
            },
        },
        headers=student_headers,
    )
    assert bad_response.status_code == 422

    good_response = await client.put(
        f"/api/v1/student-assessments/{assessment_id}/responses/{diagram_question_id}",
        json={
            "response_data": {
                "type": "diagram_annotation",
                "version": 1,
                "asset_id": good_asset_id,
                "annotations": [
                    {
                        "id": "annotation-1",
                        "symbol": "electron",
                        "x": 0.31,
                        "y": 0.20,
                    }
                ],
            },
        },
        headers=student_headers,
    )
    assert good_response.status_code == 200, good_response.text

    stored = json.loads(good_response.json()["response_data"])
    assert stored["asset_id"] == good_asset_id
    assert stored["annotations"][0]["symbol"] == "electron"


@pytest.mark.asyncio
async def test_student_can_read_visible_asset_during_active_attempt(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
    assessment_upload_root: Path,
):
    assessment = await _create_assessment_for_teacher(
        db_session,
        teacher_user,
        title="Secure Asset Delivery Assessment",
    )
    question = await _create_question(
        db_session,
        assessment_id=assessment.id,
    )

    asset_bytes = b"candidate-visible-canonical-asset"
    asset_path = (
        assessment_upload_root
        / str(teacher_user.school_id)
        / str(assessment.id)
        / "question-extraction-assets"
        / "document-1"
        / "v1"
        / "delivery.png"
    )
    asset_path.parent.mkdir(parents=True, exist_ok=True)
    asset_path.write_bytes(asset_bytes)

    asset = await _create_asset(
        db_session,
        question_id=question.id,
        storage_path=asset_path,
    )

    student = await _create_student(
        db_session,
        school_id=teacher_user.school_id,
        email="taking.asset.allowed@example.com",
    )
    await _allocate_candidate(
        db_session,
        assessment_id=assessment.id,
        student_id=student.id,
    )
    await _start_attempt(
        client,
        assessment_id=assessment.id,
        student=student,
        auth_headers=auth_headers,
    )

    response = await client.get(
        (
            f"/api/v1/student-assessments/{assessment.id}"
            f"/questions/{question.id}/assets/{asset.id}/content"
        ),
        headers=auth_headers(student),
    )
    assert response.status_code == 200, response.text
    assert response.content == asset_bytes
    assert response.headers["content-type"].startswith("image/png")


@pytest.mark.asyncio
async def test_asset_delivery_rejects_hidden_or_outside_asset(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
    assessment_upload_root: Path,
    tmp_path: Path,
):
    assessment = await _create_assessment_for_teacher(
        db_session,
        teacher_user,
        title="Asset Security Assessment",
    )
    question = await _create_question(
        db_session,
        assessment_id=assessment.id,
    )

    inside = (
        assessment_upload_root
        / str(teacher_user.school_id)
        / str(assessment.id)
        / "hidden.png"
    )
    inside.parent.mkdir(parents=True, exist_ok=True)
    inside.write_bytes(b"hidden")

    hidden_asset = await _create_asset(
        db_session,
        question_id=question.id,
        storage_path=inside,
        candidate_visible=False,
    )

    outside = tmp_path / "outside.png"
    outside.write_bytes(b"outside")

    outside_asset = await _create_asset(
        db_session,
        question_id=question.id,
        storage_path=outside,
        candidate_visible=True,
        order=2,
    )

    student = await _create_student(
        db_session,
        school_id=teacher_user.school_id,
        email="taking.asset.security@example.com",
    )
    await _allocate_candidate(
        db_session,
        assessment_id=assessment.id,
        student_id=student.id,
    )
    await _start_attempt(
        client,
        assessment_id=assessment.id,
        student=student,
        auth_headers=auth_headers,
    )

    hidden_response = await client.get(
        (
            f"/api/v1/student-assessments/{assessment.id}"
            f"/questions/{question.id}/assets/{hidden_asset.id}/content"
        ),
        headers=auth_headers(student),
    )
    assert hidden_response.status_code == 404

    outside_response = await client.get(
        (
            f"/api/v1/student-assessments/{assessment.id}"
            f"/questions/{question.id}/assets/{outside_asset.id}/content"
        ),
        headers=auth_headers(student),
    )
    assert outside_response.status_code == 409


@pytest.mark.asyncio
async def test_submit_closes_candidate_script_responses_and_blocks_later_writes(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
):
    assessment = await _create_assessment_for_teacher(
        db_session,
        teacher_user,
        title="Submission Lifecycle Assessment",
    )
    first_question = await _create_question(
        db_session,
        assessment_id=assessment.id,
        question_number="1",
        order=1,
    )
    second_question = await _create_question(
        db_session,
        assessment_id=assessment.id,
        question_number="2",
        order=2,
    )

    student = await _create_student(
        db_session,
        school_id=teacher_user.school_id,
        email="taking.submit@example.com",
    )
    student_headers = auth_headers(student)

    candidate = await _allocate_candidate(
        db_session,
        assessment_id=assessment.id,
        student_id=student.id,
    )

    assessment_id = assessment.id
    candidate_id = candidate.id
    first_question_id = first_question.id
    second_question_id = second_question.id

    await db_session.refresh(student)
    student_headers = auth_headers(student)

    start = await _start_attempt(
        client,
        assessment_id=assessment_id,
        student=student,
        auth_headers=auth_headers,
    )
    script_id = start.json()["script"]["id"]

    save = await client.put(
        f"/api/v1/student-assessments/{assessment_id}/responses/{first_question_id}",
        json={"response_text": "+1"},
        headers=student_headers,
    )
    assert save.status_code == 200, save.text

    submit = await client.post(
        f"/api/v1/student-assessments/{assessment_id}/submit",
        headers=student_headers,
    )
    assert submit.status_code == 200, submit.text
    assert submit.json()["candidate_status"] == AssessmentCandidateStatus.SUBMITTED.value
    assert submit.json()["script_status"] == AssessmentScriptStatus.SUBMITTED.value

    candidate_result = await db_session.execute(
        select(AssessmentCandidate).where(
            AssessmentCandidate.id == candidate_id,
        )
    )
    stored_candidate = candidate_result.scalar_one()

    script_result = await db_session.execute(
        select(AssessmentScript).where(
            AssessmentScript.id == script_id,
        )
    )
    stored_script = script_result.scalar_one()

    responses_result = await db_session.execute(
        select(AssessmentResponse).where(
            AssessmentResponse.script_id == script_id,
        )
    )
    stored_responses = list(responses_result.scalars().all())

    assert stored_candidate.status == AssessmentCandidateStatus.SUBMITTED
    assert stored_script.status == AssessmentScriptStatus.SUBMITTED
    assert len(stored_responses) == 2
    assert {r.question_id for r in stored_responses} == {
        first_question_id,
        second_question_id,
    }
    assert all(
        r.status == AssessmentResponseStatus.SUBMITTED
        for r in stored_responses
    )

    late_save = await client.put(
        f"/api/v1/student-assessments/{assessment_id}/responses/{second_question_id}",
        json={"response_text": "Late change."},
        headers=student_headers,
    )
    assert late_save.status_code == 409

    attempt_after_submit = await client.get(
        f"/api/v1/student-assessments/{assessment_id}/attempt",
        headers=student_headers,
    )
    assert attempt_after_submit.status_code == 409
# ---------------------------------------------------------------------------
# Second security / edge-case layer
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_inactive_student_cannot_use_student_assessment_routes(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
):
    assessment = await _create_assessment_for_teacher(
        db_session,
        teacher_user,
        title="Inactive Student Assessment",
    )
    assessment_id = assessment.id

    student = await _create_student(
        db_session,
        school_id=teacher_user.school_id,
        email="taking.inactive@example.com",
        is_active=False,
    )
    student_headers = auth_headers(student)

    await _allocate_candidate(
        db_session,
        assessment_id=assessment_id,
        student_id=student.id,
    )

    response = await client.get(
        f"/api/v1/student-assessments/{assessment_id}",
        headers=student_headers,
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_cross_school_allocation_is_hidden_from_student(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
):
    student = await _create_student(
        db_session,
        school_id=teacher_user.school_id,
        email="taking.cross.school@example.com",
    )
    student_id = student.id
    student_headers = auth_headers(student)

    other_teacher = await create_test_user(
        db_session,
        email="taking.cross.school.teacher@example.com",
        roles=[UserRole.TEACHER],
        school_id=2,
    )

    other_assessment = await _create_assessment_for_teacher(
        db_session,
        other_teacher,
        title="Other School Student Assessment",
    )
    other_assessment_id = other_assessment.id

    # Deliberately construct an inconsistent allocation to prove the learner
    # query still enforces assessment-school scope as a defence-in-depth boundary.
    await _allocate_candidate(
        db_session,
        assessment_id=other_assessment_id,
        student_id=student_id,
    )

    response = await client.get(
        f"/api/v1/student-assessments/{other_assessment_id}",
        headers=student_headers,
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_withdrawn_and_absent_candidates_cannot_start(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
):
    student = await _create_student(
        db_session,
        school_id=teacher_user.school_id,
        email="taking.terminal.candidate@example.com",
    )
    student_id = student.id
    student_headers = auth_headers(student)

    withdrawn_assessment = await _create_assessment_for_teacher(
        db_session,
        teacher_user,
        title="Withdrawn Candidate Assessment",
    )
    withdrawn_assessment_id = withdrawn_assessment.id

    absent_assessment = await _create_assessment_for_teacher(
        db_session,
        teacher_user,
        title="Absent Candidate Assessment",
    )
    absent_assessment_id = absent_assessment.id

    await _allocate_candidate(
        db_session,
        assessment_id=withdrawn_assessment_id,
        student_id=student_id,
        candidate_number="WITHDRAWN-001",
        candidate_status=AssessmentCandidateStatus.WITHDRAWN,
    )
    await _allocate_candidate(
        db_session,
        assessment_id=absent_assessment_id,
        student_id=student_id,
        candidate_number="ABSENT-001",
        candidate_status=AssessmentCandidateStatus.ABSENT,
    )

    for assessment_id in (
        withdrawn_assessment_id,
        absent_assessment_id,
    ):
        response = await client.post(
            f"/api/v1/student-assessments/{assessment_id}/start",
            headers=student_headers,
        )
        assert response.status_code == 409


@pytest.mark.asyncio
async def test_non_markable_question_rejects_student_response(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
):
    assessment = await _create_assessment_for_teacher(
        db_session,
        teacher_user,
        title="Non-Markable Item Assessment",
    )
    assessment_id = assessment.id

    question = await _create_question(
        db_session,
        assessment_id=assessment_id,
        question_number="1",
        prompt="Section heading only.",
        is_markable=False,
    )
    question_id = question.id

    student = await _create_student(
        db_session,
        school_id=teacher_user.school_id,
        email="taking.nonmarkable@example.com",
    )
    student_headers = auth_headers(student)

    await _allocate_candidate(
        db_session,
        assessment_id=assessment_id,
        student_id=student.id,
    )
    await db_session.refresh(student)

    await _start_attempt(
        client,
        assessment_id=assessment_id,
        student=student,
        auth_headers=auth_headers,
    )
    await db_session.refresh(student)
    student_headers = auth_headers(student)

    response = await client.put(
        f"/api/v1/student-assessments/{assessment_id}/responses/{question_id}",
        json={"response_text": "Should not be accepted."},
        headers=student_headers,
    )

    assert response.status_code == 409


@pytest.mark.asyncio
async def test_question_from_another_assessment_cannot_be_autosaved(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
):
    first_assessment = await _create_assessment_for_teacher(
        db_session,
        teacher_user,
        title="First Scoped Assessment",
    )
    first_assessment_id = first_assessment.id

    second_assessment = await _create_assessment_for_teacher(
        db_session,
        teacher_user,
        title="Second Scoped Assessment",
    )
    second_assessment_id = second_assessment.id

    first_question = await _create_question(
        db_session,
        assessment_id=first_assessment_id,
        question_number="1",
    )
    first_question_id = first_question.id

    await _create_question(
        db_session,
        assessment_id=second_assessment_id,
        question_number="1",
    )

    student = await _create_student(
        db_session,
        school_id=teacher_user.school_id,
        email="taking.question.scope@example.com",
    )
    student_headers = auth_headers(student)

    await _allocate_candidate(
        db_session,
        assessment_id=second_assessment_id,
        student_id=student.id,
    )
    await db_session.refresh(student)

    await _start_attempt(
        client,
        assessment_id=second_assessment_id,
        student=student,
        auth_headers=auth_headers,
    )
    await db_session.refresh(student)
    student_headers = auth_headers(student)

    response = await client.put(
        (
            f"/api/v1/student-assessments/{second_assessment_id}"
            f"/responses/{first_question_id}"
        ),
        json={"response_text": "Cross-assessment spoof."},
        headers=student_headers,
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_written_question_rejects_diagram_annotation_payload(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
):
    assessment = await _create_assessment_for_teacher(
        db_session,
        teacher_user,
        title="Wrong Response Type Assessment",
    )
    assessment_id = assessment.id

    question = await _create_question(
        db_session,
        assessment_id=assessment_id,
        question_number="1",
        question_type=AssessmentQuestionType.WRITTEN,
    )
    question_id = question.id

    student = await _create_student(
        db_session,
        school_id=teacher_user.school_id,
        email="taking.wrong.response.type@example.com",
    )
    student_headers = auth_headers(student)

    await _allocate_candidate(
        db_session,
        assessment_id=assessment_id,
        student_id=student.id,
    )
    await db_session.refresh(student)

    await _start_attempt(
        client,
        assessment_id=assessment_id,
        student=student,
        auth_headers=auth_headers,
    )
    await db_session.refresh(student)
    student_headers = auth_headers(student)

    response = await client.put(
        f"/api/v1/student-assessments/{assessment_id}/responses/{question_id}",
        json={
            "response_data": {
                "type": "diagram_annotation",
                "version": 1,
                "asset_id": 1,
                "annotations": [],
            }
        },
        headers=student_headers,
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_diagram_question_rejects_response_text_and_hidden_asset(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
    assessment_upload_root: Path,
):
    assessment = await _create_assessment_for_teacher(
        db_session,
        teacher_user,
        title="Diagram Validation Assessment",
    )
    assessment_id = assessment.id

    question = await _create_question(
        db_session,
        assessment_id=assessment_id,
        question_number="1",
        prompt="Annotate the diagram.",
        question_type=AssessmentQuestionType.DIAGRAM_ANNOTATION,
    )
    question_id = question.id

    root = (
        assessment_upload_root
        / str(teacher_user.school_id)
        / str(assessment_id)
    )
    root.mkdir(parents=True, exist_ok=True)

    visible_path = root / "visible-diagram.png"
    hidden_path = root / "hidden-diagram.png"
    visible_path.write_bytes(b"visible")
    hidden_path.write_bytes(b"hidden")

    visible_asset = await _create_asset(
        db_session,
        question_id=question_id,
        storage_path=visible_path,
        candidate_visible=True,
        order=1,
    )
    hidden_asset = await _create_asset(
        db_session,
        question_id=question_id,
        storage_path=hidden_path,
        candidate_visible=False,
        order=2,
    )

    visible_asset_id = visible_asset.id
    hidden_asset_id = hidden_asset.id

    student = await _create_student(
        db_session,
        school_id=teacher_user.school_id,
        email="taking.diagram.validation@example.com",
    )
    student_headers = auth_headers(student)

    await _allocate_candidate(
        db_session,
        assessment_id=assessment_id,
        student_id=student.id,
    )
    await db_session.refresh(student)

    await _start_attempt(
        client,
        assessment_id=assessment_id,
        student=student,
        auth_headers=auth_headers,
    )
    await db_session.refresh(student)
    student_headers = auth_headers(student)

    response_text_attempt = await client.put(
        f"/api/v1/student-assessments/{assessment_id}/responses/{question_id}",
        json={
            "response_text": "Text is not allowed.",
            "response_data": {
                "type": "diagram_annotation",
                "version": 1,
                "asset_id": visible_asset_id,
                "annotations": [],
            },
        },
        headers=student_headers,
    )
    assert response_text_attempt.status_code == 422

    # The expected 422 rolls back the request transaction, so continue with the
    # already-frozen bearer header and scalar identifiers.
    hidden_asset_attempt = await client.put(
        f"/api/v1/student-assessments/{assessment_id}/responses/{question_id}",
        json={
            "response_data": {
                "type": "diagram_annotation",
                "version": 1,
                "asset_id": hidden_asset_id,
                "annotations": [],
            }
        },
        headers=student_headers,
    )
    assert hidden_asset_attempt.status_code == 422


@pytest.mark.asyncio
async def test_asset_delivery_returns_404_when_backing_file_is_missing(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
    assessment_upload_root: Path,
):
    assessment = await _create_assessment_for_teacher(
        db_session,
        teacher_user,
        title="Missing Asset File Assessment",
    )
    assessment_id = assessment.id

    question = await _create_question(
        db_session,
        assessment_id=assessment_id,
    )
    question_id = question.id

    missing_path = (
        assessment_upload_root
        / str(teacher_user.school_id)
        / str(assessment_id)
        / "missing.png"
    )

    asset = await _create_asset(
        db_session,
        question_id=question_id,
        storage_path=missing_path,
        candidate_visible=True,
    )
    asset_id = asset.id

    student = await _create_student(
        db_session,
        school_id=teacher_user.school_id,
        email="taking.asset.missing@example.com",
    )
    student_headers = auth_headers(student)

    await _allocate_candidate(
        db_session,
        assessment_id=assessment_id,
        student_id=student.id,
    )
    await db_session.refresh(student)

    await _start_attempt(
        client,
        assessment_id=assessment_id,
        student=student,
        auth_headers=auth_headers,
    )
    await db_session.refresh(student)
    student_headers = auth_headers(student)

    response = await client.get(
        (
            f"/api/v1/student-assessments/{assessment_id}"
            f"/questions/{question_id}/assets/{asset_id}/content"
        ),
        headers=student_headers,
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_submitted_assessment_summary_is_read_only(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
):
    assessment = await _create_assessment_for_teacher(
        db_session,
        teacher_user,
        title="Submitted Summary Assessment",
    )
    assessment_id = assessment.id

    await _create_question(
        db_session,
        assessment_id=assessment_id,
    )

    student = await _create_student(
        db_session,
        school_id=teacher_user.school_id,
        email="taking.submitted.summary@example.com",
    )
    student_headers = auth_headers(student)

    await _allocate_candidate(
        db_session,
        assessment_id=assessment_id,
        student_id=student.id,
    )
    await db_session.refresh(student)

    await _start_attempt(
        client,
        assessment_id=assessment_id,
        student=student,
        auth_headers=auth_headers,
    )
    await db_session.refresh(student)
    student_headers = auth_headers(student)

    submit = await client.post(
        f"/api/v1/student-assessments/{assessment_id}/submit",
        headers=student_headers,
    )
    assert submit.status_code == 200, submit.text

    summary = await client.get(
        f"/api/v1/student-assessments/{assessment_id}",
        headers=student_headers,
    )
    assert summary.status_code == 200, summary.text

    data = summary.json()
    assert data["candidate_status"] == AssessmentCandidateStatus.SUBMITTED.value
    assert data["is_submitted"] is True
    assert data["can_start"] is False
    assert data["can_resume"] is False

@pytest.mark.asyncio
async def test_diagram_palette_accepts_configured_symbol(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
    assessment_upload_root: Path,
):
    assessment = await _create_assessment_for_teacher(
        db_session,
        teacher_user,
        title="Configured Diagram Palette Allowed Symbol",
    )

    question = await _create_question(
        db_session,
        assessment_id=assessment.id,
        prompt="Complete the atomic structure diagram.",
        question_type=AssessmentQuestionType.DIAGRAM_ANNOTATION,
        interaction_config={
            "version": 1,
            "mode": "visual_annotation",
            "palette_id": "chemistry.atomic_structure",
            "palette_label": "Atomic structure",
            "coordinate_system": "normalized",
            "tools": [
                {
                    "tool_id": "electron",
                    "tool_type": "symbol",
                    "label": "Electron",
                    "symbol": "×",
                },
                {
                    "tool_id": "neutron",
                    "tool_type": "symbol",
                    "label": "Neutron",
                    "symbol": "●",
                },
                {
                    "tool_id": "proton",
                    "tool_type": "symbol",
                    "label": "Proton",
                    "symbol": "○",
                },
            ],
        },
    )

    asset_path = (
        assessment_upload_root
        / str(teacher_user.school_id)
        / str(assessment.id)
        / "palette-allowed.png"
    )
    asset_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    asset_path.write_bytes(b"palette-allowed")

    asset = await _create_asset(
        db_session,
        question_id=question.id,
        storage_path=asset_path,
    )

    student = await _create_student(
        db_session,
        school_id=teacher_user.school_id,
        email="taking.palette.allowed@example.com",
    )
    student_headers = auth_headers(student)

    await _allocate_candidate(
        db_session,
        assessment_id=assessment.id,
        student_id=student.id,
    )
    await _start_attempt(
        client,
        assessment_id=assessment.id,
        student=student,
        auth_headers=auth_headers,
    )

    response = await client.put(
        f"/api/v1/student-assessments/{assessment.id}/responses/{question.id}",
        json={
            "response_data": {
                "type": "diagram_annotation",
                "version": 1,
                "asset_id": asset.id,
                "annotations": [
                    {
                        "id": "annotation-electron",
                        "symbol": "×",
                        "x": 0.25,
                        "y": 0.35,
                    },
                    {
                        "id": "annotation-proton",
                        "symbol": "○",
                        "x": 0.50,
                        "y": 0.50,
                    },
                ],
            },
        },
        headers=student_headers,
    )

    assert response.status_code == 200, response.text

    stored = json.loads(
        response.json()["response_data"],
    )
    assert [
        annotation["symbol"]
        for annotation in stored["annotations"]
    ] == ["×", "○"]


@pytest.mark.asyncio
async def test_diagram_palette_rejects_unconfigured_symbol(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
    assessment_upload_root: Path,
):
    assessment = await _create_assessment_for_teacher(
        db_session,
        teacher_user,
        title="Configured Diagram Palette Rejects Tampering",
    )

    question = await _create_question(
        db_session,
        assessment_id=assessment.id,
        prompt="Complete the atomic structure diagram.",
        question_type=AssessmentQuestionType.DIAGRAM_ANNOTATION,
        interaction_config={
            "version": 1,
            "mode": "visual_annotation",
            "palette_id": "chemistry.atomic_structure",
            "palette_label": "Atomic structure",
            "coordinate_system": "normalized",
            "tools": [
                {
                    "tool_id": "electron",
                    "tool_type": "symbol",
                    "label": "Electron",
                    "symbol": "×",
                },
                {
                    "tool_id": "neutron",
                    "tool_type": "symbol",
                    "label": "Neutron",
                    "symbol": "●",
                },
                {
                    "tool_id": "proton",
                    "tool_type": "symbol",
                    "label": "Proton",
                    "symbol": "○",
                },
            ],
        },
    )

    asset_path = (
        assessment_upload_root
        / str(teacher_user.school_id)
        / str(assessment.id)
        / "palette-rejected.png"
    )
    asset_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    asset_path.write_bytes(b"palette-rejected")

    asset = await _create_asset(
        db_session,
        question_id=question.id,
        storage_path=asset_path,
    )

    student = await _create_student(
        db_session,
        school_id=teacher_user.school_id,
        email="taking.palette.rejected@example.com",
    )
    student_headers = auth_headers(student)

    await _allocate_candidate(
        db_session,
        assessment_id=assessment.id,
        student_id=student.id,
    )
    await _start_attempt(
        client,
        assessment_id=assessment.id,
        student=student,
        auth_headers=auth_headers,
    )

    response = await client.put(
        f"/api/v1/student-assessments/{assessment.id}/responses/{question.id}",
        json={
            "response_data": {
                "type": "diagram_annotation",
                "version": 1,
                "asset_id": asset.id,
                "annotations": [
                    {
                        "id": "annotation-tampered",
                        "symbol": "electron",
                        "x": 0.25,
                        "y": 0.35,
                    }
                ],
            },
        },
        headers=student_headers,
    )

    assert response.status_code == 422
    assert (
        "Diagram annotation contains a symbol that is not "
        "permitted for this question."
    ) in response.text


@pytest.mark.asyncio
async def test_legacy_diagram_without_interaction_config_accepts_existing_symbol(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
    assessment_upload_root: Path,
):
    assessment = await _create_assessment_for_teacher(
        db_session,
        teacher_user,
        title="Legacy Diagram Palette Compatibility",
    )

    question = await _create_question(
        db_session,
        assessment_id=assessment.id,
        prompt="Place the required symbol.",
        question_type=AssessmentQuestionType.DIAGRAM_ANNOTATION,
        interaction_config=None,
    )

    asset_path = (
        assessment_upload_root
        / str(teacher_user.school_id)
        / str(assessment.id)
        / "legacy-diagram.png"
    )
    asset_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    asset_path.write_bytes(b"legacy-diagram")

    asset = await _create_asset(
        db_session,
        question_id=question.id,
        storage_path=asset_path,
    )

    student = await _create_student(
        db_session,
        school_id=teacher_user.school_id,
        email="taking.palette.legacy@example.com",
    )
    student_headers = auth_headers(student)

    await _allocate_candidate(
        db_session,
        assessment_id=assessment.id,
        student_id=student.id,
    )
    await _start_attempt(
        client,
        assessment_id=assessment.id,
        student=student,
        auth_headers=auth_headers,
    )

    response = await client.put(
        f"/api/v1/student-assessments/{assessment.id}/responses/{question.id}",
        json={
            "response_data": {
                "type": "diagram_annotation",
                "version": 1,
                "asset_id": asset.id,
                "annotations": [
                    {
                        "id": "annotation-legacy",
                        "symbol": "legacy-custom-symbol",
                        "x": 0.40,
                        "y": 0.60,
                    }
                ],
            },
        },
        headers=student_headers,
    )

    assert response.status_code == 200, response.text

    stored = json.loads(
        response.json()["response_data"],
    )
    assert stored["annotations"][0]["symbol"] == "legacy-custom-symbol"

