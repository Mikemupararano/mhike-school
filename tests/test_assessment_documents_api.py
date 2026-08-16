from __future__ import annotations

from pathlib import Path

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.assessment import (
    Assessment,
    AssessmentStatus,
)
from app.models.assessment_document import AssessmentDocument
from app.models.course import Course
from app.models.user import UserRole
from app.services import assessment_document_service
from tests.conftest import create_test_user

PDF_CONTENT = (
    b"%PDF-1.4\n"
    b"% MHike School assessment document test\n"
    b"1 0 obj\n"
    b"<< /Type /Catalog >>\n"
    b"endobj\n"
    b"trailer\n"
    b"<<>>\n"
    b"%%EOF\n"
)


def _error_message(
    response,
) -> str:
    """
    Extract the API error message from the project's standard error envelope.

    The application normally returns errors in this form:

        {
            "success": False,
            "error": {
                "code": "...",
                "message": "..."
            }
        }

    FastAPI's default ``detail`` shape is also supported so these tests remain
    resilient if the application's exception-response format changes.
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
        "Could not extract an error message " f"from response body: {body!r}",
    )


async def _create_course(
    db_session: AsyncSession,
    *,
    teacher_id: int,
    school_id: int,
    title: str = "Assessment Document Test Course",
) -> Course:
    """
    Create a course suitable for assessment-document API tests.
    """

    course = Course(
        title=title,
        description="Course used by assessment-document API tests.",
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
    title: str = "Atomic Structure Test",
) -> dict:
    """
    Create a draft assessment through the public API.
    """

    response = await client.post(
        "/api/v1/assessments",
        json={
            "course_id": course_id,
            "title": title,
            "description": "Assessment document API test.",
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
    title: str = "Atomic Structure Test",
) -> dict:
    """
    Create a course and draft assessment owned by ``teacher_user``.
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


@pytest.fixture
def assessment_upload_root(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> Path:
    """
    Store test uploads outside the real project upload directory.
    """

    upload_root = tmp_path / "assessment_uploads"

    monkeypatch.setattr(
        assessment_document_service,
        "ASSESSMENT_UPLOAD_ROOT",
        upload_root,
    )

    return upload_root


@pytest.mark.asyncio
async def test_teacher_can_upload_pdf_question_paper(
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
        (f"/api/v1/assessments/{assessment['id']}" "/documents/question-paper"),
        files={
            "file": (
                "atomic-structure.pdf",
                PDF_CONTENT,
                "application/pdf",
            ),
        },
        headers=auth_headers(
            teacher_user,
        ),
    )

    assert response.status_code == 201, response.text

    data = response.json()

    assert data["assessment_id"] == assessment["id"]
    assert data["uploaded_by_id"] == teacher_user.id
    assert data["document_type"] == "question_paper"
    assert data["original_filename"] == "atomic-structure.pdf"
    assert data["mime_type"] == "application/pdf"
    assert data["file_size_bytes"] == len(PDF_CONTENT)
    assert data["is_current"] is True
    assert data["extraction_requested"] is False
    assert data["extraction_completed"] is False
    assert data["extraction_error"] is None
    assert data["message"] == "Question paper uploaded successfully."

    # Internal filesystem details must never leak through the API.
    assert "storage_path" not in data
    assert "stored_filename" not in data

    result = await db_session.execute(
        select(
            AssessmentDocument,
        ).where(
            AssessmentDocument.assessment_id == assessment["id"],
        ),
    )

    documents = list(
        result.scalars().all(),
    )

    assert len(documents) == 1

    document = documents[0]

    assert document.is_current is True

    stored_path = Path(
        document.storage_path,
    )

    assert stored_path.is_file()
    assert stored_path.read_bytes() == PDF_CONTENT

    resolved_root = assessment_upload_root.resolve()
    resolved_path = stored_path.resolve()

    assert resolved_path.is_relative_to(
        resolved_root,
    )


@pytest.mark.asyncio
async def test_current_question_paper_returns_null_before_upload(
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

    response = await client.get(
        (f"/api/v1/assessments/{assessment['id']}" "/documents/question-paper"),
        headers=auth_headers(
            teacher_user,
        ),
    )

    assert response.status_code == 200, response.text
    assert response.json() is None


@pytest.mark.asyncio
async def test_teacher_can_get_current_question_paper_metadata(
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

    upload_response = await client.post(
        (f"/api/v1/assessments/{assessment['id']}" "/documents/question-paper"),
        files={
            "file": (
                "physics-paper.pdf",
                PDF_CONTENT,
                "application/pdf",
            ),
        },
        headers=auth_headers(
            teacher_user,
        ),
    )

    assert upload_response.status_code == 201, upload_response.text

    response = await client.get(
        (f"/api/v1/assessments/{assessment['id']}" "/documents/question-paper"),
        headers=auth_headers(
            teacher_user,
        ),
    )

    assert response.status_code == 200, response.text

    data = response.json()

    assert data["id"] == upload_response.json()["id"]
    assert data["assessment_id"] == assessment["id"]
    assert data["original_filename"] == "physics-paper.pdf"
    assert data["is_current"] is True

    assert "storage_path" not in data
    assert "stored_filename" not in data


@pytest.mark.asyncio
async def test_replacing_question_paper_preserves_old_version(
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

    first_content = b"%PDF-1.4\n" b"first paper\n" b"%%EOF\n"

    second_content = b"%PDF-1.4\n" b"replacement paper\n" b"%%EOF\n"

    first_response = await client.post(
        (f"/api/v1/assessments/{assessment['id']}" "/documents/question-paper"),
        files={
            "file": (
                "original-paper.pdf",
                first_content,
                "application/pdf",
            ),
        },
        headers=auth_headers(
            teacher_user,
        ),
    )

    assert first_response.status_code == 201, first_response.text

    first_document_id = first_response.json()["id"]

    first_document = await db_session.get(
        AssessmentDocument,
        first_document_id,
    )

    assert first_document is not None

    first_storage_path = Path(
        first_document.storage_path,
    )

    assert first_storage_path.is_file()

    second_response = await client.post(
        (f"/api/v1/assessments/{assessment['id']}" "/documents/question-paper"),
        files={
            "file": (
                "replacement-paper.pdf",
                second_content,
                "application/pdf",
            ),
        },
        headers=auth_headers(
            teacher_user,
        ),
    )

    assert second_response.status_code == 201, second_response.text

    await db_session.refresh(
        first_document,
    )

    assert first_document.is_current is False

    # Replacement must preserve the original physical source document.
    assert first_storage_path.is_file()
    assert first_storage_path.read_bytes() == first_content

    second_document = await db_session.get(
        AssessmentDocument,
        second_response.json()["id"],
    )

    assert second_document is not None
    assert second_document.is_current is True
    assert second_document.id != first_document.id

    second_storage_path = Path(
        second_document.storage_path,
    )

    assert second_storage_path.is_file()
    assert second_storage_path.read_bytes() == second_content

    history_response = await client.get(
        f"/api/v1/assessments/{assessment['id']}/documents",
        headers=auth_headers(
            teacher_user,
        ),
    )

    assert history_response.status_code == 200, history_response.text

    documents = history_response.json()["documents"]

    assert len(documents) == 2

    by_id = {document["id"]: document for document in documents}

    assert by_id[first_document.id]["is_current"] is False
    assert by_id[second_document.id]["is_current"] is True


@pytest.mark.asyncio
async def test_teacher_can_download_question_paper(
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

    upload_response = await client.post(
        (f"/api/v1/assessments/{assessment['id']}" "/documents/question-paper"),
        files={
            "file": (
                "download-test.pdf",
                PDF_CONTENT,
                "application/pdf",
            ),
        },
        headers=auth_headers(
            teacher_user,
        ),
    )

    assert upload_response.status_code == 201, upload_response.text

    document_id = upload_response.json()["id"]

    response = await client.get(
        (
            f"/api/v1/assessments/{assessment['id']}"
            f"/documents/{document_id}/download"
        ),
        headers=auth_headers(
            teacher_user,
        ),
    )

    assert response.status_code == 200, response.text
    assert response.content == PDF_CONTENT

    assert response.headers["content-type"].startswith(
        "application/pdf",
    )

    content_disposition = response.headers.get(
        "content-disposition",
        "",
    )

    assert "download-test.pdf" in content_disposition


@pytest.mark.asyncio
async def test_non_pdf_extension_is_rejected(
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
        (f"/api/v1/assessments/{assessment['id']}" "/documents/question-paper"),
        files={
            "file": (
                "question-paper.txt",
                PDF_CONTENT,
                "application/pdf",
            ),
        },
        headers=auth_headers(
            teacher_user,
        ),
    )

    assert response.status_code == 415

    assert _error_message(
        response,
    ) == ("Question papers must be uploaded as PDF files.")


@pytest.mark.asyncio
async def test_wrong_pdf_mime_type_is_rejected(
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
        (f"/api/v1/assessments/{assessment['id']}" "/documents/question-paper"),
        files={
            "file": (
                "question-paper.pdf",
                PDF_CONTENT,
                "text/plain",
            ),
        },
        headers=auth_headers(
            teacher_user,
        ),
    )

    assert response.status_code == 415

    assert _error_message(
        response,
    ) == ("Question papers must use the application/pdf MIME type.")


@pytest.mark.asyncio
async def test_fake_pdf_content_is_rejected(
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
        (f"/api/v1/assessments/{assessment['id']}" "/documents/question-paper"),
        files={
            "file": (
                "fake.pdf",
                b"This is not actually a PDF.",
                "application/pdf",
            ),
        },
        headers=auth_headers(
            teacher_user,
        ),
    )

    assert response.status_code == 415

    assert _error_message(
        response,
    ) == ("The uploaded file does not appear to be a valid PDF.")


@pytest.mark.asyncio
async def test_empty_pdf_is_rejected(
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
        (f"/api/v1/assessments/{assessment['id']}" "/documents/question-paper"),
        files={
            "file": (
                "empty.pdf",
                b"",
                "application/pdf",
            ),
        },
        headers=auth_headers(
            teacher_user,
        ),
    )

    assert response.status_code == 422

    assert _error_message(
        response,
    ) == ("The uploaded question paper is empty.")


@pytest.mark.asyncio
async def test_question_paper_cannot_be_uploaded_after_publication(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
    assessment_upload_root: Path,
):
    assessment_data = await _create_teacher_assessment(
        client,
        db_session,
        teacher_user=teacher_user,
        auth_headers=auth_headers,
    )

    assessment = await db_session.get(
        Assessment,
        assessment_data["id"],
    )

    assert assessment is not None

    assessment.status = AssessmentStatus.PUBLISHED

    await db_session.commit()

    response = await client.post(
        (f"/api/v1/assessments/{assessment.id}" "/documents/question-paper"),
        files={
            "file": (
                "published-paper.pdf",
                PDF_CONTENT,
                "application/pdf",
            ),
        },
        headers=auth_headers(
            teacher_user,
        ),
    )

    assert response.status_code == 409

    assert _error_message(
        response,
    ) == (
        "Question papers can only be uploaded or replaced "
        "while the assessment is in draft."
    )


@pytest.mark.asyncio
async def test_unrelated_teacher_cannot_access_question_paper(
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

    upload_response = await client.post(
        (f"/api/v1/assessments/{assessment['id']}" "/documents/question-paper"),
        files={
            "file": (
                "private-paper.pdf",
                PDF_CONTENT,
                "application/pdf",
            ),
        },
        headers=auth_headers(
            teacher_user,
        ),
    )

    assert upload_response.status_code == 201, upload_response.text

    other_teacher = await create_test_user(
        db_session,
        email="assessment.documents.other.teacher@example.com",
        roles=[
            UserRole.TEACHER,
        ],
        school_id=teacher_user.school_id,
    )

    response = await client.get(
        (f"/api/v1/assessments/{assessment['id']}" "/documents/question-paper"),
        headers=auth_headers(
            other_teacher,
        ),
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_document_cannot_be_downloaded_through_another_assessment(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
    assessment_upload_root: Path,
):
    first_course = await _create_course(
        db_session,
        teacher_id=teacher_user.id,
        school_id=teacher_user.school_id,
        title="First Document Test Course",
    )

    second_course = await _create_course(
        db_session,
        teacher_id=teacher_user.id,
        school_id=teacher_user.school_id,
        title="Second Document Test Course",
    )

    first_assessment = await _create_assessment(
        client,
        course_id=first_course.id,
        user=teacher_user,
        auth_headers=auth_headers,
        title="First Assessment",
    )

    second_assessment = await _create_assessment(
        client,
        course_id=second_course.id,
        user=teacher_user,
        auth_headers=auth_headers,
        title="Second Assessment",
    )

    upload_response = await client.post(
        (f"/api/v1/assessments/{first_assessment['id']}" "/documents/question-paper"),
        files={
            "file": (
                "first-assessment.pdf",
                PDF_CONTENT,
                "application/pdf",
            ),
        },
        headers=auth_headers(
            teacher_user,
        ),
    )

    assert upload_response.status_code == 201, upload_response.text

    document_id = upload_response.json()["id"]

    response = await client.get(
        (
            f"/api/v1/assessments/{second_assessment['id']}"
            f"/documents/{document_id}/download"
        ),
        headers=auth_headers(
            teacher_user,
        ),
    )

    assert response.status_code == 404

    assert _error_message(
        response,
    ) == ("Assessment document not found.")
