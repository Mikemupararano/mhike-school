from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.assessment import Assessment, AssessmentStatus
from app.models.assessment_candidate import (
    AssessmentCandidateStatus,
    AssessmentScriptStatus,
)
from app.models.course import Course
from app.models.user import UserRole
from tests.conftest import create_test_user


SCANNED_SCRIPT_PDF = b"%PDF-1.4\nMHike scanned assessment script\n%%EOF\n"


@pytest.fixture
def assessment_script_upload_root(
    tmp_path: Path,
    monkeypatch,
) -> Path:
    """
    Isolate scanned assessment-script storage for API tests.
    """

    from app.services import assessment_script_upload_service

    upload_root = (
        tmp_path
        / "assessment-scripts"
    )

    monkeypatch.setattr(
        assessment_script_upload_service,
        "ASSESSMENT_SCRIPT_UPLOAD_ROOT",
        upload_root,
    )

    return upload_root


async def _create_course(
    db_session: AsyncSession,
    *,
    teacher_id: int,
    school_id: int,
    title: str = "Assessment Candidate API Course",
) -> Course:
    """
    Create and persist a course for candidate API tests.
    """

    course = Course(
        title=title,
        description="Course used by assessment candidate API tests.",
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
    title: str = "Assessment Candidate API Assessment",
    assessment_status: AssessmentStatus = AssessmentStatus.DRAFT,
) -> Assessment:
    """
    Create and persist an assessment for candidate API tests.
    """

    assessment = Assessment(
        school_id=school_id,
        course_id=course_id,
        created_by_id=teacher_id,
        title=title,
        description="Assessment candidate API test.",
        assessment_type="test",
        academic_year="2026/27",
        term="Autumn",
        status=assessment_status,
        anonymous_marking=False,
    )

    db_session.add(assessment)

    await db_session.commit()
    await db_session.refresh(assessment)

    return assessment


async def _create_assessment_for_teacher(
    db_session: AsyncSession,
    teacher_user,
    *,
    title: str = "Assessment Candidate API Assessment",
    assessment_status: AssessmentStatus = AssessmentStatus.DRAFT,
) -> tuple[Course, Assessment]:
    """
    Create a teacher-owned course and assessment.
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
        title=title,
        assessment_status=assessment_status,
    )

    return course, assessment


async def _create_student(
    db_session: AsyncSession,
    *,
    school_id: int,
    email: str,
):
    """
    Create a student in the supplied school.
    """

    return await create_test_user(
        db_session,
        email=email,
        roles=[UserRole.STUDENT],
        school_id=school_id,
    )


async def _allocate_candidate_via_api(
    client: AsyncClient,
    *,
    assessment_id: int,
    student_id: int,
    user,
    auth_headers,
    candidate_number: str = "CAND-001",
) -> dict:
    """
    Allocate a candidate through the API.
    """

    response = await client.post(
        f"/api/v1/assessment-candidates/assessment/{assessment_id}",
        json={
            "student_id": student_id,
            "candidate_number": candidate_number,
            "access_arrangements": "25% extra time",
        },
        headers=auth_headers(user),
    )

    assert response.status_code == 201, response.text

    return response.json()


async def _create_script_via_api(
    client: AsyncClient,
    *,
    candidate_id: int,
    user,
    auth_headers,
) -> dict:
    """
    Create a script version through the API.
    """

    response = await client.post(
        f"/api/v1/assessment-candidates/{candidate_id}/scripts",
        json={
            "source_type": "pdf_upload",
            "source_filename": "candidate-script.pdf",
            "storage_key": "assessment-scripts/candidate-script.pdf",
            "mime_type": "application/pdf",
            "checksum": "abc123",
        },
        headers=auth_headers(user),
    )

    assert response.status_code == 201, response.text

    return response.json()


# ---------------------------------------------------------------------------
# Candidate allocation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_teacher_can_allocate_candidate_to_own_assessment(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
):
    _, assessment = await _create_assessment_for_teacher(
        db_session,
        teacher_user,
    )

    student = await _create_student(
        db_session,
        school_id=teacher_user.school_id,
        email="candidate.api.allocate@example.com",
    )

    response = await client.post(
        f"/api/v1/assessment-candidates/assessment/{assessment.id}",
        json={
            "student_id": student.id,
            "candidate_number": "P001",
            "access_arrangements": "Reader",
        },
        headers=auth_headers(teacher_user),
    )

    assert response.status_code == 201, response.text

    data = response.json()

    assert data["id"] is not None
    assert data["assessment_id"] == assessment.id
    assert data["student_id"] == student.id
    assert data["status"] == AssessmentCandidateStatus.ALLOCATED.value
    assert data["candidate_number"] == "P001"
    assert data["access_arrangements"] == "Reader"
    assert data["scripts"] == []


@pytest.mark.asyncio
async def test_duplicate_candidate_allocation_is_rejected(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
):
    _, assessment = await _create_assessment_for_teacher(
        db_session,
        teacher_user,
    )

    student = await _create_student(
        db_session,
        school_id=teacher_user.school_id,
        email="candidate.api.duplicate@example.com",
    )

    await _allocate_candidate_via_api(
        client,
        assessment_id=assessment.id,
        student_id=student.id,
        user=teacher_user,
        auth_headers=auth_headers,
    )

    response = await client.post(
        f"/api/v1/assessment-candidates/assessment/{assessment.id}",
        json={
            "student_id": student.id,
        },
        headers=auth_headers(teacher_user),
    )

    assert response.status_code == 409


@pytest.mark.asyncio
async def test_non_student_cannot_be_allocated(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
):
    _, assessment = await _create_assessment_for_teacher(
        db_session,
        teacher_user,
    )

    other_teacher = await create_test_user(
        db_session,
        email="candidate.api.not.student@example.com",
        roles=[UserRole.TEACHER],
        school_id=teacher_user.school_id,
    )

    response = await client.post(
        f"/api/v1/assessment-candidates/assessment/{assessment.id}",
        json={
            "student_id": other_teacher.id,
        },
        headers=auth_headers(teacher_user),
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_teacher_cannot_allocate_candidate_to_other_teachers_assessment(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
):
    other_teacher = await create_test_user(
        db_session,
        email="candidate.api.other.teacher@example.com",
        roles=[UserRole.TEACHER],
        school_id=teacher_user.school_id,
    )

    course = await _create_course(
        db_session,
        teacher_id=other_teacher.id,
        school_id=other_teacher.school_id,
        title="Other Teacher Candidate API Course",
    )

    assessment = await _create_assessment(
        db_session,
        teacher_id=other_teacher.id,
        school_id=other_teacher.school_id,
        course_id=course.id,
        title="Other Teacher Candidate API Assessment",
    )

    student = await _create_student(
        db_session,
        school_id=teacher_user.school_id,
        email="candidate.api.other.teacher.student@example.com",
    )

    response = await client.post(
        f"/api/v1/assessment-candidates/assessment/{assessment.id}",
        json={
            "student_id": student.id,
        },
        headers=auth_headers(teacher_user),
    )

    assert response.status_code == 403


# ---------------------------------------------------------------------------
# Candidate retrieval and metadata
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_teacher_can_get_candidate(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
):
    _, assessment = await _create_assessment_for_teacher(
        db_session,
        teacher_user,
    )

    student = await _create_student(
        db_session,
        school_id=teacher_user.school_id,
        email="candidate.api.get@example.com",
    )

    created = await _allocate_candidate_via_api(
        client,
        assessment_id=assessment.id,
        student_id=student.id,
        user=teacher_user,
        auth_headers=auth_headers,
    )

    response = await client.get(
        f"/api/v1/assessment-candidates/{created['id']}",
        headers=auth_headers(teacher_user),
    )

    assert response.status_code == 200, response.text

    data = response.json()

    assert data["id"] == created["id"]
    assert data["student_id"] == student.id
    assert data["assessment_id"] == assessment.id


@pytest.mark.asyncio
async def test_teacher_can_list_assessment_candidates(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
):
    _, assessment = await _create_assessment_for_teacher(
        db_session,
        teacher_user,
    )

    first_student = await _create_student(
        db_session,
        school_id=teacher_user.school_id,
        email="candidate.api.list.first@example.com",
    )

    second_student = await _create_student(
        db_session,
        school_id=teacher_user.school_id,
        email="candidate.api.list.second@example.com",
    )

    first = await _allocate_candidate_via_api(
        client,
        assessment_id=assessment.id,
        student_id=first_student.id,
        user=teacher_user,
        auth_headers=auth_headers,
        candidate_number="CAND-001",
    )

    second = await _allocate_candidate_via_api(
        client,
        assessment_id=assessment.id,
        student_id=second_student.id,
        user=teacher_user,
        auth_headers=auth_headers,
        candidate_number="CAND-002",
    )

    response = await client.get(
        f"/api/v1/assessment-candidates/assessment/{assessment.id}",
        headers=auth_headers(teacher_user),
    )

    assert response.status_code == 200, response.text

    data = response.json()

    candidate_ids = {candidate["id"] for candidate in data}

    assert first["id"] in candidate_ids
    assert second["id"] in candidate_ids


@pytest.mark.asyncio
async def test_teacher_can_update_candidate_metadata(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
):
    _, assessment = await _create_assessment_for_teacher(
        db_session,
        teacher_user,
    )

    student = await _create_student(
        db_session,
        school_id=teacher_user.school_id,
        email="candidate.api.update@example.com",
    )

    created = await _allocate_candidate_via_api(
        client,
        assessment_id=assessment.id,
        student_id=student.id,
        user=teacher_user,
        auth_headers=auth_headers,
    )

    response = await client.patch(
        f"/api/v1/assessment-candidates/{created['id']}",
        json={
            "candidate_number": "UPDATED-001",
            "access_arrangements": "Laptop",
        },
        headers=auth_headers(teacher_user),
    )

    assert response.status_code == 200, response.text

    data = response.json()

    assert data["candidate_number"] == "UPDATED-001"
    assert data["access_arrangements"] == "Laptop"


# ---------------------------------------------------------------------------
# Candidate lifecycle
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_candidate_cannot_start_draft_assessment(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
):
    _, assessment = await _create_assessment_for_teacher(
        db_session,
        teacher_user,
        assessment_status=AssessmentStatus.DRAFT,
    )

    student = await _create_student(
        db_session,
        school_id=teacher_user.school_id,
        email="candidate.api.start.draft@example.com",
    )

    created = await _allocate_candidate_via_api(
        client,
        assessment_id=assessment.id,
        student_id=student.id,
        user=teacher_user,
        auth_headers=auth_headers,
    )

    response = await client.post(
        f"/api/v1/assessment-candidates/{created['id']}/start",
        headers=auth_headers(teacher_user),
    )

    assert response.status_code == 409


@pytest.mark.asyncio
async def test_candidate_can_start_and_submit_when_assessment_is_published(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
):
    _, assessment = await _create_assessment_for_teacher(
        db_session,
        teacher_user,
        assessment_status=AssessmentStatus.PUBLISHED,
    )

    student = await _create_student(
        db_session,
        school_id=teacher_user.school_id,
        email="candidate.api.lifecycle@example.com",
    )

    created = await _allocate_candidate_via_api(
        client,
        assessment_id=assessment.id,
        student_id=student.id,
        user=teacher_user,
        auth_headers=auth_headers,
    )

    start_response = await client.post(
        f"/api/v1/assessment-candidates/{created['id']}/start",
        headers=auth_headers(teacher_user),
    )

    assert start_response.status_code == 200, start_response.text
    assert start_response.json()["status"] == AssessmentCandidateStatus.STARTED.value

    submit_response = await client.post(
        f"/api/v1/assessment-candidates/{created['id']}/submit",
        headers=auth_headers(teacher_user),
    )

    assert submit_response.status_code == 200, submit_response.text
    assert submit_response.json()["status"] == AssessmentCandidateStatus.SUBMITTED.value


@pytest.mark.asyncio
async def test_allocated_candidate_can_be_withdrawn(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
):
    _, assessment = await _create_assessment_for_teacher(
        db_session,
        teacher_user,
    )

    student = await _create_student(
        db_session,
        school_id=teacher_user.school_id,
        email="candidate.api.withdraw@example.com",
    )

    created = await _allocate_candidate_via_api(
        client,
        assessment_id=assessment.id,
        student_id=student.id,
        user=teacher_user,
        auth_headers=auth_headers,
    )

    response = await client.post(
        f"/api/v1/assessment-candidates/{created['id']}/withdraw",
        headers=auth_headers(teacher_user),
    )

    assert response.status_code == 200, response.text
    assert response.json()["status"] == AssessmentCandidateStatus.WITHDRAWN.value


@pytest.mark.asyncio
async def test_allocated_candidate_can_be_marked_absent(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
):
    _, assessment = await _create_assessment_for_teacher(
        db_session,
        teacher_user,
    )

    student = await _create_student(
        db_session,
        school_id=teacher_user.school_id,
        email="candidate.api.absent@example.com",
    )

    created = await _allocate_candidate_via_api(
        client,
        assessment_id=assessment.id,
        student_id=student.id,
        user=teacher_user,
        auth_headers=auth_headers,
    )

    response = await client.post(
        f"/api/v1/assessment-candidates/{created['id']}/absent",
        headers=auth_headers(teacher_user),
    )

    assert response.status_code == 200, response.text
    assert response.json()["status"] == AssessmentCandidateStatus.ABSENT.value


@pytest.mark.asyncio
async def test_generic_candidate_status_endpoint_rejects_invalid_transition(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
):
    _, assessment = await _create_assessment_for_teacher(
        db_session,
        teacher_user,
    )

    student = await _create_student(
        db_session,
        school_id=teacher_user.school_id,
        email="candidate.api.invalid.transition@example.com",
    )

    created = await _allocate_candidate_via_api(
        client,
        assessment_id=assessment.id,
        student_id=student.id,
        user=teacher_user,
        auth_headers=auth_headers,
    )

    response = await client.patch(
        f"/api/v1/assessment-candidates/{created['id']}/status",
        json={
            "status": AssessmentCandidateStatus.SUBMITTED.value,
        },
        headers=auth_headers(teacher_user),
    )

    assert response.status_code == 409


# ---------------------------------------------------------------------------
# Script creation and listing
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_teacher_can_upload_scanned_pdf_script(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
    assessment_script_upload_root: Path,
):
    _, assessment = await _create_assessment_for_teacher(
        db_session,
        teacher_user,
    )

    student = await _create_student(
        db_session,
        school_id=teacher_user.school_id,
        email="candidate.api.scanned.upload@example.com",
    )

    candidate = await _allocate_candidate_via_api(
        client,
        assessment_id=assessment.id,
        student_id=student.id,
        user=teacher_user,
        auth_headers=auth_headers,
    )

    response = await client.post(
        f"/api/v1/assessment-candidates/{candidate['id']}/scripts/upload",
        files={
            "file": (
                "handwritten-physics.pdf",
                SCANNED_SCRIPT_PDF,
                "application/pdf",
            ),
        },
        headers=auth_headers(teacher_user),
    )

    assert response.status_code == 201, response.text

    data = response.json()

    assert data["candidate_id"] == candidate["id"]
    assert data["version"] == 1
    assert data["status"] == AssessmentScriptStatus.SUBMITTED.value
    assert data["submitted_at"] is not None

    candidate_response = await client.get(
        f"/api/v1/assessment-candidates/{candidate['id']}",
        headers=auth_headers(teacher_user),
    )

    assert candidate_response.status_code == 200, candidate_response.text

    candidate_data = candidate_response.json()

    assert candidate_data["status"] == AssessmentCandidateStatus.SUBMITTED.value
    assert candidate_data["started_at"] is not None
    assert candidate_data["submitted_at"] is not None
    assert data["source_type"] == "scanned_pdf"
    assert data["source_filename"] == "handwritten-physics.pdf"
    assert data["mime_type"] == "application/pdf"
    assert data["checksum"] == sha256(SCANNED_SCRIPT_PDF).hexdigest()

    stored_path = Path(
        data["storage_key"],
    )

    assert stored_path.is_file()
    assert stored_path.read_bytes() == SCANNED_SCRIPT_PDF

    assert stored_path.resolve().is_relative_to(
        assessment_script_upload_root.resolve(),
    )


@pytest.mark.asyncio
async def test_scanned_pdf_upload_creates_next_script_version(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
    assessment_script_upload_root: Path,
):
    _, assessment = await _create_assessment_for_teacher(
        db_session,
        teacher_user,
    )

    student = await _create_student(
        db_session,
        school_id=teacher_user.school_id,
        email="candidate.api.scanned.version@example.com",
    )

    candidate = await _allocate_candidate_via_api(
        client,
        assessment_id=assessment.id,
        student_id=student.id,
        user=teacher_user,
        auth_headers=auth_headers,
    )

    first_response = await client.post(
        f"/api/v1/assessment-candidates/{candidate['id']}/scripts/upload",
        files={
            "file": (
                "first-scan.pdf",
                SCANNED_SCRIPT_PDF,
                "application/pdf",
            ),
        },
        headers=auth_headers(teacher_user),
    )

    second_contents = (
        b"%PDF-1.4\n"
        b"Replacement scanned assessment script\n"
        b"%%EOF\n"
    )

    second_response = await client.post(
        f"/api/v1/assessment-candidates/{candidate['id']}/scripts/upload",
        files={
            "file": (
                "second-scan.pdf",
                second_contents,
                "application/pdf",
            ),
        },
        headers=auth_headers(teacher_user),
    )

    assert first_response.status_code == 201, first_response.text
    assert second_response.status_code == 201, second_response.text

    first = first_response.json()
    second = second_response.json()

    assert first["version"] == 1
    assert second["version"] == 2
    assert first["storage_key"] != second["storage_key"]
    assert second["checksum"] == sha256(second_contents).hexdigest()

    assert first["status"] == AssessmentScriptStatus.SUBMITTED.value
    assert second["status"] == AssessmentScriptStatus.SUBMITTED.value
    assert first["submitted_at"] is not None
    assert second["submitted_at"] is not None


@pytest.mark.asyncio
async def test_scanned_script_upload_rejects_non_pdf_extension(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
    assessment_script_upload_root: Path,
):
    _, assessment = await _create_assessment_for_teacher(
        db_session,
        teacher_user,
    )

    student = await _create_student(
        db_session,
        school_id=teacher_user.school_id,
        email="candidate.api.scanned.extension@example.com",
    )

    candidate = await _allocate_candidate_via_api(
        client,
        assessment_id=assessment.id,
        student_id=student.id,
        user=teacher_user,
        auth_headers=auth_headers,
    )

    response = await client.post(
        f"/api/v1/assessment-candidates/{candidate['id']}/scripts/upload",
        files={
            "file": (
                "handwritten.txt",
                SCANNED_SCRIPT_PDF,
                "application/pdf",
            ),
        },
        headers=auth_headers(teacher_user),
    )

    assert response.status_code == 415, response.text


@pytest.mark.asyncio
async def test_scanned_script_upload_rejects_wrong_mime_type(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
    assessment_script_upload_root: Path,
):
    _, assessment = await _create_assessment_for_teacher(
        db_session,
        teacher_user,
    )

    student = await _create_student(
        db_session,
        school_id=teacher_user.school_id,
        email="candidate.api.scanned.mime@example.com",
    )

    candidate = await _allocate_candidate_via_api(
        client,
        assessment_id=assessment.id,
        student_id=student.id,
        user=teacher_user,
        auth_headers=auth_headers,
    )

    response = await client.post(
        f"/api/v1/assessment-candidates/{candidate['id']}/scripts/upload",
        files={
            "file": (
                "handwritten.pdf",
                SCANNED_SCRIPT_PDF,
                "text/plain",
            ),
        },
        headers=auth_headers(teacher_user),
    )

    assert response.status_code == 415, response.text


@pytest.mark.asyncio
async def test_scanned_script_upload_rejects_invalid_pdf_signature(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
    assessment_script_upload_root: Path,
):
    _, assessment = await _create_assessment_for_teacher(
        db_session,
        teacher_user,
    )

    student = await _create_student(
        db_session,
        school_id=teacher_user.school_id,
        email="candidate.api.scanned.signature@example.com",
    )

    candidate = await _allocate_candidate_via_api(
        client,
        assessment_id=assessment.id,
        student_id=student.id,
        user=teacher_user,
        auth_headers=auth_headers,
    )

    response = await client.post(
        f"/api/v1/assessment-candidates/{candidate['id']}/scripts/upload",
        files={
            "file": (
                "handwritten.pdf",
                b"not actually a PDF",
                "application/pdf",
            ),
        },
        headers=auth_headers(teacher_user),
    )

    assert response.status_code == 415, response.text


@pytest.mark.asyncio
async def test_scanned_script_upload_rejects_empty_pdf(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
    assessment_script_upload_root: Path,
):
    _, assessment = await _create_assessment_for_teacher(
        db_session,
        teacher_user,
    )

    student = await _create_student(
        db_session,
        school_id=teacher_user.school_id,
        email="candidate.api.scanned.empty@example.com",
    )

    candidate = await _allocate_candidate_via_api(
        client,
        assessment_id=assessment.id,
        student_id=student.id,
        user=teacher_user,
        auth_headers=auth_headers,
    )

    response = await client.post(
        f"/api/v1/assessment-candidates/{candidate['id']}/scripts/upload",
        files={
            "file": (
                "handwritten.pdf",
                b"",
                "application/pdf",
            ),
        },
        headers=auth_headers(teacher_user),
    )

    assert response.status_code == 422, response.text


@pytest.mark.asyncio
async def test_scanned_script_upload_rejects_oversized_pdf(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
    assessment_script_upload_root: Path,
    monkeypatch,
):
    from app.api.v1.endpoints import assessment_candidates
    from app.services import assessment_script_upload_service

    maximum_size = 64

    monkeypatch.setattr(
        assessment_candidates,
        "MAX_SCANNED_SCRIPT_SIZE_BYTES",
        maximum_size,
    )

    monkeypatch.setattr(
        assessment_script_upload_service,
        "MAX_SCANNED_SCRIPT_SIZE_BYTES",
        maximum_size,
    )

    _, assessment = await _create_assessment_for_teacher(
        db_session,
        teacher_user,
    )

    student = await _create_student(
        db_session,
        school_id=teacher_user.school_id,
        email="candidate.api.scanned.oversized@example.com",
    )

    candidate = await _allocate_candidate_via_api(
        client,
        assessment_id=assessment.id,
        student_id=student.id,
        user=teacher_user,
        auth_headers=auth_headers,
    )

    oversized_pdf = (
        b"%PDF-"
        + (
            b"x"
            * maximum_size
        )
    )

    response = await client.post(
        f"/api/v1/assessment-candidates/{candidate['id']}/scripts/upload",
        files={
            "file": (
                "oversized.pdf",
                oversized_pdf,
                "application/pdf",
            ),
        },
        headers=auth_headers(teacher_user),
    )

    assert response.status_code == 413, response.text

    assert not list(
        assessment_script_upload_root.rglob(
            "*.pdf",
        )
    )


@pytest.mark.asyncio
async def test_other_school_teacher_cannot_upload_scanned_script(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
    assessment_script_upload_root: Path,
):
    _, assessment = await _create_assessment_for_teacher(
        db_session,
        teacher_user,
    )

    student = await _create_student(
        db_session,
        school_id=teacher_user.school_id,
        email="candidate.api.scanned.cross.school.student@example.com",
    )

    candidate = await _allocate_candidate_via_api(
        client,
        assessment_id=assessment.id,
        student_id=student.id,
        user=teacher_user,
        auth_headers=auth_headers,
    )

    other_school_teacher = await create_test_user(
        db_session,
        email="candidate.api.scanned.cross.school.teacher@example.com",
        roles=[UserRole.TEACHER],
        school_id=2,
    )

    response = await client.post(
        f"/api/v1/assessment-candidates/{candidate['id']}/scripts/upload",
        files={
            "file": (
                "foreign-school.pdf",
                SCANNED_SCRIPT_PDF,
                "application/pdf",
            ),
        },
        headers=auth_headers(other_school_teacher),
    )

    assert response.status_code == 403, response.text

    assert not list(
        assessment_script_upload_root.rglob(
            "*.pdf",
        )
    )


@pytest.mark.asyncio
async def test_teacher_can_view_scanned_script_pdf(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
    assessment_script_upload_root: Path,
):
    _, assessment = await _create_assessment_for_teacher(
        db_session,
        teacher_user,
    )

    student = await _create_student(
        db_session,
        school_id=teacher_user.school_id,
        email="candidate.api.scanned.view@example.com",
    )

    candidate = await _allocate_candidate_via_api(
        client,
        assessment_id=assessment.id,
        student_id=student.id,
        user=teacher_user,
        auth_headers=auth_headers,
    )

    upload = await client.post(
        f"/api/v1/assessment-candidates/{candidate['id']}/scripts/upload",
        files={
            "file": (
                "view-script.pdf",
                SCANNED_SCRIPT_PDF,
                "application/pdf",
            ),
        },
        headers=auth_headers(teacher_user),
    )

    assert upload.status_code == 201, upload.text

    script = upload.json()

    response = await client.get(
        f"/api/v1/assessment-candidates/scripts/{script['id']}/file",
        headers=auth_headers(teacher_user),
    )

    assert response.status_code == 200, response.text
    assert response.headers["content-type"].startswith("application/pdf")
    assert "inline" in response.headers["content-disposition"].lower()
    assert "view-script.pdf" in response.headers["content-disposition"]
    assert response.content == SCANNED_SCRIPT_PDF


@pytest.mark.asyncio
async def test_other_school_teacher_cannot_view_scanned_script_pdf(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
    assessment_script_upload_root: Path,
):
    _, assessment = await _create_assessment_for_teacher(
        db_session,
        teacher_user,
    )

    student = await _create_student(
        db_session,
        school_id=teacher_user.school_id,
        email="candidate.api.scanned.view.cross.school@example.com",
    )

    candidate = await _allocate_candidate_via_api(
        client,
        assessment_id=assessment.id,
        student_id=student.id,
        user=teacher_user,
        auth_headers=auth_headers,
    )

    upload = await client.post(
        f"/api/v1/assessment-candidates/{candidate['id']}/scripts/upload",
        files={
            "file": (
                "protected-script.pdf",
                SCANNED_SCRIPT_PDF,
                "application/pdf",
            ),
        },
        headers=auth_headers(teacher_user),
    )

    assert upload.status_code == 201, upload.text

    script = upload.json()

    other_school_teacher = await create_test_user(
        db_session,
        email="candidate.api.scanned.viewer.other.school@example.com",
        roles=[UserRole.TEACHER],
        school_id=2,
    )

    response = await client.get(
        f"/api/v1/assessment-candidates/scripts/{script['id']}/file",
        headers=auth_headers(other_school_teacher),
    )

    assert response.status_code == 403, response.text


@pytest.mark.asyncio
async def test_generic_script_has_no_scanned_pdf_file_endpoint(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
    assessment_script_upload_root: Path,
):
    _, assessment = await _create_assessment_for_teacher(
        db_session,
        teacher_user,
    )

    student = await _create_student(
        db_session,
        school_id=teacher_user.school_id,
        email="candidate.api.generic.file@example.com",
    )

    candidate = await _allocate_candidate_via_api(
        client,
        assessment_id=assessment.id,
        student_id=student.id,
        user=teacher_user,
        auth_headers=auth_headers,
    )

    created = await client.post(
        f"/api/v1/assessment-candidates/{candidate['id']}/scripts",
        json={
            "source_type": "pdf_upload",
            "source_filename": "legacy.pdf",
            "storage_key": "somewhere/legacy.pdf",
            "mime_type": "application/pdf",
            "checksum": "legacy-checksum",
        },
        headers=auth_headers(teacher_user),
    )

    assert created.status_code == 201, created.text

    script = created.json()

    response = await client.get(
        f"/api/v1/assessment-candidates/scripts/{script['id']}/file",
        headers=auth_headers(teacher_user),
    )

    assert response.status_code == 404, response.text


@pytest.mark.asyncio
async def test_missing_scanned_script_file_returns_404(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
    assessment_script_upload_root: Path,
):
    _, assessment = await _create_assessment_for_teacher(
        db_session,
        teacher_user,
    )

    student = await _create_student(
        db_session,
        school_id=teacher_user.school_id,
        email="candidate.api.scanned.missing.file@example.com",
    )

    candidate = await _allocate_candidate_via_api(
        client,
        assessment_id=assessment.id,
        student_id=student.id,
        user=teacher_user,
        auth_headers=auth_headers,
    )

    upload = await client.post(
        f"/api/v1/assessment-candidates/{candidate['id']}/scripts/upload",
        files={
            "file": (
                "missing-script.pdf",
                SCANNED_SCRIPT_PDF,
                "application/pdf",
            ),
        },
        headers=auth_headers(teacher_user),
    )

    assert upload.status_code == 201, upload.text

    script = upload.json()

    Path(script["storage_key"]).unlink()

    response = await client.get(
        f"/api/v1/assessment-candidates/scripts/{script['id']}/file",
        headers=auth_headers(teacher_user),
    )

    assert response.status_code == 404, response.text


@pytest.mark.asyncio
async def test_scanned_script_file_rejects_other_candidate_storage_key(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
    assessment_script_upload_root: Path,
):
    _, assessment = await _create_assessment_for_teacher(
        db_session,
        teacher_user,
    )

    first_student = await _create_student(
        db_session,
        school_id=teacher_user.school_id,
        email="candidate.api.scanned.forged.first@example.com",
    )

    second_student = await _create_student(
        db_session,
        school_id=teacher_user.school_id,
        email="candidate.api.scanned.forged.second@example.com",
    )

    first_candidate = await _allocate_candidate_via_api(
        client,
        assessment_id=assessment.id,
        student_id=first_student.id,
        user=teacher_user,
        auth_headers=auth_headers,
        candidate_number="CAND-FORGE-1",
    )

    second_candidate = await _allocate_candidate_via_api(
        client,
        assessment_id=assessment.id,
        student_id=second_student.id,
        user=teacher_user,
        auth_headers=auth_headers,
        candidate_number="CAND-FORGE-2",
    )

    legitimate_upload = await client.post(
        f"/api/v1/assessment-candidates/{second_candidate['id']}/scripts/upload",
        files={
            "file": (
                "second-candidate.pdf",
                SCANNED_SCRIPT_PDF,
                "application/pdf",
            ),
        },
        headers=auth_headers(teacher_user),
    )

    assert legitimate_upload.status_code == 201, legitimate_upload.text

    legitimate_script = legitimate_upload.json()

    forged = await client.post(
        f"/api/v1/assessment-candidates/{first_candidate['id']}/scripts",
        json={
            "source_type": "scanned_pdf",
            "source_filename": "forged-reference.pdf",
            "storage_key": legitimate_script["storage_key"],
            "mime_type": "application/pdf",
            "checksum": legitimate_script["checksum"],
        },
        headers=auth_headers(teacher_user),
    )

    assert forged.status_code == 201, forged.text

    forged_script = forged.json()

    response = await client.get(
        f"/api/v1/assessment-candidates/scripts/{forged_script['id']}/file",
        headers=auth_headers(teacher_user),
    )

    assert response.status_code == 500, response.text
    assert response.content != SCANNED_SCRIPT_PDF
    assert legitimate_script["storage_key"] not in response.text


@pytest.mark.asyncio
async def test_teacher_can_create_script_version(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
):
    _, assessment = await _create_assessment_for_teacher(
        db_session,
        teacher_user,
    )

    student = await _create_student(
        db_session,
        school_id=teacher_user.school_id,
        email="candidate.api.script.create@example.com",
    )

    candidate = await _allocate_candidate_via_api(
        client,
        assessment_id=assessment.id,
        student_id=student.id,
        user=teacher_user,
        auth_headers=auth_headers,
    )

    response = await client.post(
        f"/api/v1/assessment-candidates/{candidate['id']}/scripts",
        json={
            "source_type": "pdf_upload",
            "source_filename": "paper.pdf",
            "storage_key": "assessment-scripts/paper.pdf",
            "mime_type": "application/pdf",
            "checksum": "checksum-1",
        },
        headers=auth_headers(teacher_user),
    )

    assert response.status_code == 201, response.text

    data = response.json()

    assert data["candidate_id"] == candidate["id"]
    assert data["version"] == 1
    assert data["status"] == AssessmentScriptStatus.NOT_SUBMITTED.value
    assert data["source_filename"] == "paper.pdf"


@pytest.mark.asyncio
async def test_script_versions_increment_via_api(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
):
    _, assessment = await _create_assessment_for_teacher(
        db_session,
        teacher_user,
    )

    student = await _create_student(
        db_session,
        school_id=teacher_user.school_id,
        email="candidate.api.script.version@example.com",
    )

    candidate = await _allocate_candidate_via_api(
        client,
        assessment_id=assessment.id,
        student_id=student.id,
        user=teacher_user,
        auth_headers=auth_headers,
    )

    first = await _create_script_via_api(
        client,
        candidate_id=candidate["id"],
        user=teacher_user,
        auth_headers=auth_headers,
    )

    second = await _create_script_via_api(
        client,
        candidate_id=candidate["id"],
        user=teacher_user,
        auth_headers=auth_headers,
    )

    assert first["version"] == 1
    assert second["version"] == 2


@pytest.mark.asyncio
async def test_teacher_can_list_candidate_scripts(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
):
    _, assessment = await _create_assessment_for_teacher(
        db_session,
        teacher_user,
    )

    student = await _create_student(
        db_session,
        school_id=teacher_user.school_id,
        email="candidate.api.script.list@example.com",
    )

    candidate = await _allocate_candidate_via_api(
        client,
        assessment_id=assessment.id,
        student_id=student.id,
        user=teacher_user,
        auth_headers=auth_headers,
    )

    first = await _create_script_via_api(
        client,
        candidate_id=candidate["id"],
        user=teacher_user,
        auth_headers=auth_headers,
    )

    second = await _create_script_via_api(
        client,
        candidate_id=candidate["id"],
        user=teacher_user,
        auth_headers=auth_headers,
    )

    response = await client.get(
        f"/api/v1/assessment-candidates/{candidate['id']}/scripts",
        headers=auth_headers(teacher_user),
    )

    assert response.status_code == 200, response.text

    data = response.json()

    assert [script["id"] for script in data] == [
        first["id"],
        second["id"],
    ]


@pytest.mark.asyncio
async def test_teacher_can_get_script_by_id(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
):
    _, assessment = await _create_assessment_for_teacher(
        db_session,
        teacher_user,
    )

    student = await _create_student(
        db_session,
        school_id=teacher_user.school_id,
        email="candidate.api.script.get@example.com",
    )

    candidate = await _allocate_candidate_via_api(
        client,
        assessment_id=assessment.id,
        student_id=student.id,
        user=teacher_user,
        auth_headers=auth_headers,
    )

    script = await _create_script_via_api(
        client,
        candidate_id=candidate["id"],
        user=teacher_user,
        auth_headers=auth_headers,
    )

    response = await client.get(
        f"/api/v1/assessment-candidates/scripts/{script['id']}",
        headers=auth_headers(teacher_user),
    )

    assert response.status_code == 200, response.text

    data = response.json()

    assert data["id"] == script["id"]
    assert data["candidate_id"] == candidate["id"]


# ---------------------------------------------------------------------------
# Script lifecycle
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_script_can_progress_through_full_lifecycle(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
):
    _, assessment = await _create_assessment_for_teacher(
        db_session,
        teacher_user,
        assessment_status=AssessmentStatus.PUBLISHED,
    )

    student = await _create_student(
        db_session,
        school_id=teacher_user.school_id,
        email="candidate.api.script.lifecycle@example.com",
    )

    candidate = await _allocate_candidate_via_api(
        client,
        assessment_id=assessment.id,
        student_id=student.id,
        user=teacher_user,
        auth_headers=auth_headers,
    )

    script = await _create_script_via_api(
        client,
        candidate_id=candidate["id"],
        user=teacher_user,
        auth_headers=auth_headers,
    )

    submit_response = await client.post(
        f"/api/v1/assessment-candidates/scripts/{script['id']}/submit",
        headers=auth_headers(teacher_user),
    )

    assert submit_response.status_code == 200, submit_response.text
    assert submit_response.json()["status"] == AssessmentScriptStatus.SUBMITTED.value

    marking_response = await client.post(
        f"/api/v1/assessment-candidates/scripts/{script['id']}/start-marking",
        headers=auth_headers(teacher_user),
    )

    assert marking_response.status_code == 200, marking_response.text
    assert marking_response.json()["status"] == AssessmentScriptStatus.MARKING.value

    marked_response = await client.post(
        f"/api/v1/assessment-candidates/scripts/{script['id']}/mark-complete",
        headers=auth_headers(teacher_user),
    )

    assert marked_response.status_code == 200, marked_response.text
    assert marked_response.json()["status"] == AssessmentScriptStatus.MARKED.value

    moderation_response = await client.post(
        f"/api/v1/assessment-candidates/scripts/{script['id']}/moderation",
        headers=auth_headers(teacher_user),
    )

    assert moderation_response.status_code == 200, moderation_response.text
    assert (
        moderation_response.json()["status"] == AssessmentScriptStatus.MODERATION.value
    )

    finalise_response = await client.post(
        f"/api/v1/assessment-candidates/scripts/{script['id']}/finalise",
        headers=auth_headers(teacher_user),
    )

    assert finalise_response.status_code == 200, finalise_response.text
    assert finalise_response.json()["status"] == AssessmentScriptStatus.FINALISED.value


@pytest.mark.asyncio
async def test_invalid_script_status_transition_is_rejected(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
):
    _, assessment = await _create_assessment_for_teacher(
        db_session,
        teacher_user,
    )

    student = await _create_student(
        db_session,
        school_id=teacher_user.school_id,
        email="candidate.api.script.invalid@example.com",
    )

    candidate = await _allocate_candidate_via_api(
        client,
        assessment_id=assessment.id,
        student_id=student.id,
        user=teacher_user,
        auth_headers=auth_headers,
    )

    script = await _create_script_via_api(
        client,
        candidate_id=candidate["id"],
        user=teacher_user,
        auth_headers=auth_headers,
    )

    response = await client.patch(
        f"/api/v1/assessment-candidates/scripts/{script['id']}/status",
        json={
            "status": AssessmentScriptStatus.MARKED.value,
        },
        headers=auth_headers(teacher_user),
    )

    assert response.status_code == 409


# ---------------------------------------------------------------------------
# Deletion rules
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_unsubmitted_script_can_be_deleted(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
):
    _, assessment = await _create_assessment_for_teacher(
        db_session,
        teacher_user,
    )

    student = await _create_student(
        db_session,
        school_id=teacher_user.school_id,
        email="candidate.api.script.delete@example.com",
    )

    candidate = await _allocate_candidate_via_api(
        client,
        assessment_id=assessment.id,
        student_id=student.id,
        user=teacher_user,
        auth_headers=auth_headers,
    )

    script = await _create_script_via_api(
        client,
        candidate_id=candidate["id"],
        user=teacher_user,
        auth_headers=auth_headers,
    )

    response = await client.delete(
        f"/api/v1/assessment-candidates/scripts/{script['id']}",
        headers=auth_headers(teacher_user),
    )

    assert response.status_code == 204


@pytest.mark.asyncio
async def test_submitted_script_cannot_be_deleted(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
):
    _, assessment = await _create_assessment_for_teacher(
        db_session,
        teacher_user,
        assessment_status=AssessmentStatus.PUBLISHED,
    )

    student = await _create_student(
        db_session,
        school_id=teacher_user.school_id,
        email="candidate.api.script.delete.submitted@example.com",
    )

    candidate = await _allocate_candidate_via_api(
        client,
        assessment_id=assessment.id,
        student_id=student.id,
        user=teacher_user,
        auth_headers=auth_headers,
    )

    script = await _create_script_via_api(
        client,
        candidate_id=candidate["id"],
        user=teacher_user,
        auth_headers=auth_headers,
    )

    submit_response = await client.post(
        f"/api/v1/assessment-candidates/scripts/{script['id']}/submit",
        headers=auth_headers(teacher_user),
    )

    assert submit_response.status_code == 200, submit_response.text

    response = await client.delete(
        f"/api/v1/assessment-candidates/scripts/{script['id']}",
        headers=auth_headers(teacher_user),
    )

    assert response.status_code == 409


@pytest.mark.asyncio
async def test_untouched_candidate_can_be_deleted(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
):
    _, assessment = await _create_assessment_for_teacher(
        db_session,
        teacher_user,
    )

    student = await _create_student(
        db_session,
        school_id=teacher_user.school_id,
        email="candidate.api.delete@example.com",
    )

    candidate = await _allocate_candidate_via_api(
        client,
        assessment_id=assessment.id,
        student_id=student.id,
        user=teacher_user,
        auth_headers=auth_headers,
    )

    response = await client.delete(
        f"/api/v1/assessment-candidates/{candidate['id']}",
        headers=auth_headers(teacher_user),
    )

    assert response.status_code == 204


@pytest.mark.asyncio
async def test_candidate_with_script_history_cannot_be_deleted(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
):
    _, assessment = await _create_assessment_for_teacher(
        db_session,
        teacher_user,
    )

    student = await _create_student(
        db_session,
        school_id=teacher_user.school_id,
        email="candidate.api.delete.with.script@example.com",
    )

    candidate = await _allocate_candidate_via_api(
        client,
        assessment_id=assessment.id,
        student_id=student.id,
        user=teacher_user,
        auth_headers=auth_headers,
    )

    await _create_script_via_api(
        client,
        candidate_id=candidate["id"],
        user=teacher_user,
        auth_headers=auth_headers,
    )

    response = await client.delete(
        f"/api/v1/assessment-candidates/{candidate['id']}",
        headers=auth_headers(teacher_user),
    )

    assert response.status_code == 409




