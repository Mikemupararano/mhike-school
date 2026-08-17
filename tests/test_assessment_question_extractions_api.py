from __future__ import annotations

from io import BytesIO
from pathlib import Path

import pytest
from httpx import AsyncClient
from reportlab.pdfgen import canvas
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.assessment_question_extraction import (
    AssessmentQuestionExtractionStatus,
)
from app.models.course import Course
from app.models.user import UserRole
from app.services import assessment_document_service
from tests.conftest import create_test_user

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build_pdf_bytes(
    pages: list[list[str]],
) -> bytes:
    """
    Build a small digital PDF suitable for extraction API tests.
    """

    buffer = BytesIO()

    pdf = canvas.Canvas(
        buffer,
    )

    for page_lines in pages:
        y = 800

        for line in page_lines:
            pdf.drawString(
                72,
                y,
                line,
            )
            y -= 24

        pdf.showPage()

    pdf.save()

    return buffer.getvalue()


def _error_message(
    response,
) -> str:
    """
    Extract the application's error message from either the standard MHike
    error envelope or FastAPI's default detail response.
    """

    body = response.json()

    detail = body.get(
        "detail",
    )

    if isinstance(
        detail,
        str,
    ):
        return detail

    message = body.get(
        "message",
    )

    if isinstance(
        message,
        str,
    ):
        return message

    error = body.get(
        "error",
    )

    if isinstance(
        error,
        str,
    ):
        return error

    if isinstance(
        error,
        dict,
    ):
        nested_message = error.get(
            "message",
        )

        if isinstance(
            nested_message,
            str,
        ):
            return nested_message

        nested_detail = error.get(
            "detail",
        )

        if isinstance(
            nested_detail,
            str,
        ):
            return nested_detail

    raise AssertionError(
        f"Could not extract an error message from response body: {body!r}",
    )


async def _create_course(
    db_session: AsyncSession,
    *,
    teacher_id: int,
    school_id: int,
    title: str = "Question Extraction API Test Course",
) -> Course:
    """
    Create a teacher-owned course for extraction API tests.
    """

    course = Course(
        title=title,
        description="Course used by question extraction API tests.",
        teacher_id=teacher_id,
        school_id=school_id,
        published=True,
    )

    db_session.add(
        course,
    )

    await db_session.commit()
    await db_session.refresh(
        course,
    )

    return course


async def _create_assessment(
    client: AsyncClient,
    *,
    course_id: int,
    user,
    auth_headers,
    title: str = "Atomic Structure Extraction Test",
) -> dict:
    """
    Create a draft assessment through the public API.
    """

    response = await client.post(
        "/api/v1/assessments",
        json={
            "course_id": course_id,
            "title": title,
            "description": "Question extraction API test.",
            "assessment_type": "class_test",
            "academic_year": "2026/27",
            "term": "Autumn",
            "anonymous_marking": False,
        },
        headers=auth_headers(
            user,
        ),
    )

    assert response.status_code == 201, response.text

    return response.json()


async def _create_teacher_assessment(
    client: AsyncClient,
    db_session: AsyncSession,
    *,
    teacher_user,
    auth_headers,
    title: str = "Atomic Structure Extraction Test",
) -> dict:
    """
    Create a course and assessment owned by the supplied teacher.
    """

    course = await _create_course(
        db_session,
        teacher_id=teacher_user.id,
        school_id=teacher_user.school_id,
    )

    return await _create_assessment(
        client,
        course_id=course.id,
        user=teacher_user,
        auth_headers=auth_headers,
        title=title,
    )


async def _upload_question_paper(
    client: AsyncClient,
    *,
    assessment_id: int,
    user,
    auth_headers,
    pdf_bytes: bytes,
    filename: str = "atomic-structure.pdf",
) -> dict:
    """
    Upload a question paper through the existing assessment document API.
    """

    response = await client.post(
        (f"/api/v1/assessments/{assessment_id}" "/documents/question-paper"),
        files={
            "file": (
                filename,
                pdf_bytes,
                "application/pdf",
            ),
        },
        headers=auth_headers(
            user,
        ),
    )

    assert response.status_code == 201, response.text

    return response.json()


async def _create_assessment_with_question_paper(
    client: AsyncClient,
    db_session: AsyncSession,
    *,
    teacher_user,
    auth_headers,
    pdf_bytes: bytes,
) -> tuple[
    dict,
    dict,
]:
    """
    Create an assessment and upload its current question paper.
    """

    assessment = await _create_teacher_assessment(
        client,
        db_session,
        teacher_user=teacher_user,
        auth_headers=auth_headers,
    )

    document = await _upload_question_paper(
        client,
        assessment_id=assessment["id"],
        user=teacher_user,
        auth_headers=auth_headers,
        pdf_bytes=pdf_bytes,
    )

    return (
        assessment,
        document,
    )


@pytest.fixture
def assessment_upload_root(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> Path:
    """
    Keep extraction API test PDFs outside the real uploads directory.
    """

    upload_root = tmp_path / "assessment_question_extraction_api_uploads"

    monkeypatch.setattr(
        assessment_document_service,
        "ASSESSMENT_UPLOAD_ROOT",
        upload_root,
    )

    return upload_root


# ---------------------------------------------------------------------------
# Creation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_teacher_can_create_question_extraction(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
    assessment_upload_root: Path,
):
    pdf_bytes = _build_pdf_bytes(
        [
            [
                "Atomic Structure",
                "1 State two features of the nuclear model. [2]",
                "(a) State the relative charge of an electron. [1]",
            ],
            [
                "2 Complete the particle diagram. [4]",
                "(a) State the number of protons. [1]",
            ],
        ]
    )

    assessment, document = await _create_assessment_with_question_paper(
        client,
        db_session,
        teacher_user=teacher_user,
        auth_headers=auth_headers,
        pdf_bytes=pdf_bytes,
    )

    response = await client.post(
        (
            f"/api/v1/assessments/{assessment['id']}"
            f"/documents/{document['id']}"
            "/question-extractions"
        ),
        headers=auth_headers(
            teacher_user,
        ),
    )

    assert response.status_code == 201, response.text

    data = response.json()

    assert data["assessment_id"] == assessment["id"]
    assert data["assessment_document_id"] == document["id"]
    assert data["requested_by_id"] == teacher_user.id
    assert data["version"] == 1

    assert data["status"] == (AssessmentQuestionExtractionStatus.COMPLETED.value)

    assert data["extractor_name"] == "pypdf"
    assert data["parser_version"] == "1"

    assert data["page_count"] == 2
    assert data["text_page_count"] == 2

    assert data["detected_question_count"] >= 4
    assert data["detected_markable_question_count"] >= 4
    assert data["detected_total_marks"] >= 8

    assert data["proposal_data"] is not None
    assert data["proposal_data"]["review_required"] is True
    assert data["proposal_data"]["auto_import_allowed"] is False

    assert data["page_data"] is not None
    assert len(data["page_data"]) == 2

    assert data["message"] == ("Question-paper extraction completed.")

    # Internal source-file storage details must not leak through extraction.
    assert "storage_path" not in data
    assert "stored_filename" not in data


@pytest.mark.asyncio
async def test_extraction_api_retains_review_only_proposal(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
    assessment_upload_root: Path,
):
    pdf_bytes = _build_pdf_bytes(
        [
            [
                "1 Define isotope. [2]",
                "(a) State the charge of a proton. [1]",
            ],
        ]
    )

    assessment, document = await _create_assessment_with_question_paper(
        client,
        db_session,
        teacher_user=teacher_user,
        auth_headers=auth_headers,
        pdf_bytes=pdf_bytes,
    )

    response = await client.post(
        (
            f"/api/v1/assessments/{assessment['id']}"
            f"/documents/{document['id']}"
            "/question-extractions"
        ),
        headers=auth_headers(
            teacher_user,
        ),
    )

    assert response.status_code == 201, response.text

    proposal = response.json()["proposal_data"]

    assert proposal["review_required"] is True
    assert proposal["auto_import_allowed"] is False

    questions = proposal["questions"]

    assert len(questions) >= 2

    assert all(question["requires_review"] is True for question in questions)

    assert all(question["source"]["page_number"] == 1 for question in questions)


# ---------------------------------------------------------------------------
# Retrieval
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_teacher_can_get_full_question_extraction(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
    assessment_upload_root: Path,
):
    pdf_bytes = _build_pdf_bytes(
        [
            [
                "1 State the relative mass of a proton. [1]",
            ],
        ]
    )

    assessment, document = await _create_assessment_with_question_paper(
        client,
        db_session,
        teacher_user=teacher_user,
        auth_headers=auth_headers,
        pdf_bytes=pdf_bytes,
    )

    create_response = await client.post(
        (
            f"/api/v1/assessments/{assessment['id']}"
            f"/documents/{document['id']}"
            "/question-extractions"
        ),
        headers=auth_headers(
            teacher_user,
        ),
    )

    assert create_response.status_code == 201, create_response.text

    extraction_id = create_response.json()["id"]

    response = await client.get(
        (
            f"/api/v1/assessments/{assessment['id']}"
            f"/question-extractions/{extraction_id}"
        ),
        headers=auth_headers(
            teacher_user,
        ),
    )

    assert response.status_code == 200, response.text

    data = response.json()

    assert data["id"] == extraction_id
    assert data["assessment_id"] == assessment["id"]
    assert data["assessment_document_id"] == document["id"]
    assert data["version"] == 1

    assert data["proposal_data"] is not None
    assert data["page_data"] is not None
    assert len(data["page_data"]) == 1


@pytest.mark.asyncio
async def test_teacher_can_list_question_extraction_history(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
    assessment_upload_root: Path,
):
    pdf_bytes = _build_pdf_bytes(
        [
            [
                "1 State the relative charge of a proton. [1]",
            ],
        ]
    )

    assessment, document = await _create_assessment_with_question_paper(
        client,
        db_session,
        teacher_user=teacher_user,
        auth_headers=auth_headers,
        pdf_bytes=pdf_bytes,
    )

    extraction_url = (
        f"/api/v1/assessments/{assessment['id']}"
        f"/documents/{document['id']}"
        "/question-extractions"
    )

    first_response = await client.post(
        extraction_url,
        headers=auth_headers(
            teacher_user,
        ),
    )

    assert first_response.status_code == 201, first_response.text

    second_response = await client.post(
        extraction_url,
        headers=auth_headers(
            teacher_user,
        ),
    )

    assert second_response.status_code == 201, second_response.text

    response = await client.get(
        extraction_url,
        headers=auth_headers(
            teacher_user,
        ),
    )

    assert response.status_code == 200, response.text

    data = response.json()

    assert data["assessment_id"] == assessment["id"]
    assert data["assessment_document_id"] == document["id"]

    extractions = data["extractions"]

    assert len(extractions) == 2

    assert [extraction["version"] for extraction in extractions] == [
        2,
        1,
    ]

    assert extractions[0]["status"] == (
        AssessmentQuestionExtractionStatus.COMPLETED.value
    )

    assert extractions[1]["status"] == (
        AssessmentQuestionExtractionStatus.SUPERSEDED.value
    )

    # History is intentionally lightweight.
    for extraction in extractions:
        assert "page_data" not in extraction
        assert "proposal_data" not in extraction
        assert "source_metadata" not in extraction


# ---------------------------------------------------------------------------
# Access isolation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_unrelated_teacher_cannot_create_question_extraction(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
    assessment_upload_root: Path,
):
    pdf_bytes = _build_pdf_bytes(
        [
            [
                "1 State the charge of an electron. [1]",
            ],
        ]
    )

    assessment, document = await _create_assessment_with_question_paper(
        client,
        db_session,
        teacher_user=teacher_user,
        auth_headers=auth_headers,
        pdf_bytes=pdf_bytes,
    )

    other_teacher = await create_test_user(
        db_session,
        email="assessment.extraction.other.teacher@example.com",
        roles=[
            UserRole.TEACHER,
        ],
        school_id=teacher_user.school_id,
    )

    response = await client.post(
        (
            f"/api/v1/assessments/{assessment['id']}"
            f"/documents/{document['id']}"
            "/question-extractions"
        ),
        headers=auth_headers(
            other_teacher,
        ),
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_extraction_cannot_be_read_through_another_assessment(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
    assessment_upload_root: Path,
):
    pdf_bytes = _build_pdf_bytes(
        [
            [
                "1 State the mass of an electron. [1]",
            ],
        ]
    )

    first_assessment, document = await _create_assessment_with_question_paper(
        client,
        db_session,
        teacher_user=teacher_user,
        auth_headers=auth_headers,
        pdf_bytes=pdf_bytes,
    )

    second_course = await _create_course(
        db_session,
        teacher_id=teacher_user.id,
        school_id=teacher_user.school_id,
        title="Second Extraction API Course",
    )

    second_assessment = await _create_assessment(
        client,
        course_id=second_course.id,
        user=teacher_user,
        auth_headers=auth_headers,
        title="Second Extraction Assessment",
    )

    create_response = await client.post(
        (
            f"/api/v1/assessments/{first_assessment['id']}"
            f"/documents/{document['id']}"
            "/question-extractions"
        ),
        headers=auth_headers(
            teacher_user,
        ),
    )

    assert create_response.status_code == 201, create_response.text

    extraction_id = create_response.json()["id"]

    response = await client.get(
        (
            f"/api/v1/assessments/{second_assessment['id']}"
            f"/question-extractions/{extraction_id}"
        ),
        headers=auth_headers(
            teacher_user,
        ),
    )

    assert response.status_code == 404

    assert (
        _error_message(
            response,
        )
        == "Assessment question extraction not found."
    )


# ---------------------------------------------------------------------------
# Invalid documents
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_missing_question_paper_document_returns_not_found(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
    assessment_upload_root: Path,
):
    assessment = await _create_teacher_assessment(
        client,
        db_session,
        teacher_user=teacher_user,
        auth_headers=auth_headers,
    )

    response = await client.post(
        (
            f"/api/v1/assessments/{assessment['id']}"
            "/documents/999999/question-extractions"
        ),
        headers=auth_headers(
            teacher_user,
        ),
    )

    assert response.status_code == 404

    assert (
        _error_message(
            response,
        )
        == "Assessment document not found."
    )
