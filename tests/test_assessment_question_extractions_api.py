from __future__ import annotations

from copy import deepcopy
from decimal import Decimal
from io import BytesIO
from pathlib import Path

import pytest
from httpx import AsyncClient
from reportlab.pdfgen import canvas
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.assessment_question import AssessmentQuestion
from app.models.assessment_question_extraction import (
    AssessmentQuestionExtraction,
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


async def _attach_test_visual_asset(
    db_session: AsyncSession,
    *,
    assessment_id: int,
    document_id: int,
    extraction_id: int,
    teacher_user,
    write_file: bool = True,
    storage_path_override: Path | None = None,
) -> tuple[AssessmentQuestionExtraction, Path, bytes]:
    """
    Attach one synthetic visual asset to the first stored extraction candidate.

    API tests should not depend on the PDF parser happening to detect a visual in
    a small fixture document. This helper therefore creates the same
    version-scoped storage layout used by the extraction service and updates a
    fresh proposal_data copy so SQLAlchemy persists the JSON change reliably.
    """

    extraction = await db_session.get(
        AssessmentQuestionExtraction,
        extraction_id,
    )

    assert extraction is not None
    assert extraction.assessment_id == assessment_id
    assert extraction.assessment_document_id == document_id
    assert isinstance(
        extraction.proposal_data,
        dict,
    )

    _, document_path = (
        await assessment_document_service.resolve_assessment_document_path(
            db=db_session,
            current_user=teacher_user,
            assessment_id=assessment_id,
            document_id=document_id,
        )
    )

    expected_root = (
        document_path.parent
        / "question-extraction-assets"
        / f"document-{document_id}"
        / f"v{extraction.version}"
    )

    expected_root.mkdir(
        parents=True,
        exist_ok=True,
    )

    asset_path = (
        storage_path_override
        if storage_path_override is not None
        else expected_root / "api-test-asset.png"
    )

    asset_bytes = b"mhike-question-extraction-asset-test"

    if write_file:
        asset_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        asset_path.write_bytes(
            asset_bytes,
        )

    proposal = deepcopy(
        extraction.proposal_data,
    )

    questions = proposal.get(
        "questions",
    )

    assert isinstance(
        questions,
        list,
    )
    assert questions
    assert isinstance(
        questions[0],
        dict,
    )

    questions[0]["assets"] = [
        {
            "asset_type": "figure",
            "storage_path": str(
                asset_path,
            ),
            "original_filename": asset_path.name,
            "mime_type": "image/png",
            "file_size_bytes": len(
                asset_bytes,
            ),
            "alt_text": "Synthetic API test visual.",
            "caption": None,
            "order": 1,
            "candidate_visible": True,
            "source_document_id": document_id,
            "source_page_number": 1,
            "source_bbox": {
                "x0": 10.0,
                "y0": 20.0,
                "x1": 110.0,
                "y1": 120.0,
            },
            "included": True,
            "reviewed": False,
        }
    ]

    extraction.proposal_data = proposal

    await db_session.commit()
    await db_session.refresh(
        extraction,
    )

    return (
        extraction,
        asset_path,
        asset_bytes,
    )


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
    assert data["parser_version"] == "8"

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
# Secure extraction asset delivery
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_full_extraction_derives_asset_content_url_without_persisting_it(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
    assessment_upload_root: Path,
):
    pdf_bytes = _build_pdf_bytes(
        [
            [
                "1 State the relative charge of an electron. [1]",
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

    extraction, _, _ = await _attach_test_visual_asset(
        db_session,
        assessment_id=assessment["id"],
        document_id=document["id"],
        extraction_id=extraction_id,
        teacher_user=teacher_user,
    )

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

    asset = data["proposal_data"]["questions"][0]["assets"][0]

    assert asset["content_url"] == (
        f"/api/v1/assessments/{assessment['id']}"
        f"/question-extractions/{extraction_id}"
        "/assets/0/0"
    )

    await db_session.refresh(
        extraction,
    )

    stored_asset = extraction.proposal_data["questions"][0]["assets"][0]

    assert "content_url" not in stored_asset


@pytest.mark.asyncio
async def test_teacher_can_read_question_extraction_asset(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
    assessment_upload_root: Path,
):
    pdf_bytes = _build_pdf_bytes(
        [
            [
                "1 State the relative charge of an electron. [1]",
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

    _, _, asset_bytes = await _attach_test_visual_asset(
        db_session,
        assessment_id=assessment["id"],
        document_id=document["id"],
        extraction_id=extraction_id,
        teacher_user=teacher_user,
    )

    response = await client.get(
        (
            f"/api/v1/assessments/{assessment['id']}"
            f"/question-extractions/{extraction_id}"
            "/assets/0/0"
        ),
        headers=auth_headers(
            teacher_user,
        ),
    )

    assert response.status_code == 200, response.text
    assert response.headers["content-type"].startswith(
        "image/png",
    )
    assert response.content == asset_bytes


@pytest.mark.asyncio
async def test_question_extraction_asset_rejects_out_of_range_indexes(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
    assessment_upload_root: Path,
):
    pdf_bytes = _build_pdf_bytes(
        [
            [
                "1 State the relative charge of an electron. [1]",
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

    await _attach_test_visual_asset(
        db_session,
        assessment_id=assessment["id"],
        document_id=document["id"],
        extraction_id=extraction_id,
        teacher_user=teacher_user,
    )

    urls = [
        (
            f"/api/v1/assessments/{assessment['id']}"
            f"/question-extractions/{extraction_id}"
            "/assets/-1/0"
        ),
        (
            f"/api/v1/assessments/{assessment['id']}"
            f"/question-extractions/{extraction_id}"
            "/assets/999/0"
        ),
        (
            f"/api/v1/assessments/{assessment['id']}"
            f"/question-extractions/{extraction_id}"
            "/assets/0/-1"
        ),
        (
            f"/api/v1/assessments/{assessment['id']}"
            f"/question-extractions/{extraction_id}"
            "/assets/0/999"
        ),
    ]

    for url in urls:
        response = await client.get(
            url,
            headers=auth_headers(
                teacher_user,
            ),
        )

        assert response.status_code == 404, response.text
        assert (
            _error_message(
                response,
            )
            == "Question extraction asset not found."
        )


@pytest.mark.asyncio
async def test_question_extraction_asset_returns_not_found_when_file_is_missing(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
    assessment_upload_root: Path,
):
    pdf_bytes = _build_pdf_bytes(
        [
            [
                "1 State the relative charge of an electron. [1]",
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

    await _attach_test_visual_asset(
        db_session,
        assessment_id=assessment["id"],
        document_id=document["id"],
        extraction_id=extraction_id,
        teacher_user=teacher_user,
        write_file=False,
    )

    response = await client.get(
        (
            f"/api/v1/assessments/{assessment['id']}"
            f"/question-extractions/{extraction_id}"
            "/assets/0/0"
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
        == "Question extraction asset file was not found."
    )


@pytest.mark.asyncio
async def test_question_extraction_asset_rejects_path_outside_version_directory(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
    assessment_upload_root: Path,
):
    pdf_bytes = _build_pdf_bytes(
        [
            [
                "1 State the relative charge of an electron. [1]",
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

    outside_path = (
        assessment_upload_root.parent / "outside-authorised-extraction-directory.png"
    )

    await _attach_test_visual_asset(
        db_session,
        assessment_id=assessment["id"],
        document_id=document["id"],
        extraction_id=extraction_id,
        teacher_user=teacher_user,
        storage_path_override=outside_path,
    )

    response = await client.get(
        (
            f"/api/v1/assessments/{assessment['id']}"
            f"/question-extractions/{extraction_id}"
            "/assets/0/0"
        ),
        headers=auth_headers(
            teacher_user,
        ),
    )

    assert response.status_code == 409
    assert _error_message(
        response,
    ) == (
        "The stored extraction asset path falls outside the "
        "authorised extraction directory."
    )


@pytest.mark.asyncio
async def test_unrelated_teacher_cannot_read_question_extraction_asset(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
    assessment_upload_root: Path,
):
    pdf_bytes = _build_pdf_bytes(
        [
            [
                "1 State the relative charge of an electron. [1]",
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

    await _attach_test_visual_asset(
        db_session,
        assessment_id=assessment["id"],
        document_id=document["id"],
        extraction_id=extraction_id,
        teacher_user=teacher_user,
    )

    other_teacher = await create_test_user(
        db_session,
        email="assessment.extraction.asset.other.teacher@example.com",
        roles=[
            UserRole.TEACHER,
        ],
        school_id=teacher_user.school_id,
    )

    response = await client.get(
        (
            f"/api/v1/assessments/{assessment['id']}"
            f"/question-extractions/{extraction_id}"
            "/assets/0/0"
        ),
        headers=auth_headers(
            other_teacher,
        ),
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_question_extraction_asset_cannot_be_read_through_another_assessment(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
    assessment_upload_root: Path,
):
    pdf_bytes = _build_pdf_bytes(
        [
            [
                "1 State the relative charge of an electron. [1]",
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

    await _attach_test_visual_asset(
        db_session,
        assessment_id=first_assessment["id"],
        document_id=document["id"],
        extraction_id=extraction_id,
        teacher_user=teacher_user,
    )

    second_course = await _create_course(
        db_session,
        teacher_id=teacher_user.id,
        school_id=teacher_user.school_id,
        title="Second Asset Delivery API Course",
    )

    second_assessment = await _create_assessment(
        client,
        course_id=second_course.id,
        user=teacher_user,
        auth_headers=auth_headers,
        title="Second Asset Delivery Assessment",
    )

    response = await client.get(
        (
            f"/api/v1/assessments/{second_assessment['id']}"
            f"/question-extractions/{extraction_id}"
            "/assets/0/0"
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


# ---------------------------------------------------------------------------
# Teacher review
# ---------------------------------------------------------------------------


def _review_payload_from_extraction(
    extraction_data: dict,
    *,
    review_status: str = "in_progress",
    review_notes: str | None = None,
) -> dict:
    """
    Build a complete public-API review payload from an extraction response.
    """

    proposal = extraction_data.get(
        "proposal_data",
    )

    assert isinstance(
        proposal,
        dict,
    )

    questions = proposal.get(
        "questions",
        [],
    )

    return {
        "review_status": review_status,
        "review_notes": review_notes,
        "questions": [
            {
                "candidate_index": index,
                "question_number": question["question_number"],
                "text": question.get(
                    "text",
                    "",
                )
                or "",
                "marks": question.get(
                    "marks",
                ),
                "parent_question_number": question.get(
                    "parent_question_number",
                ),
                "included": True,
                "reviewed": True,
            }
            for index, question in enumerate(
                questions,
            )
        ],
    }


@pytest.mark.asyncio
async def test_teacher_can_save_question_extraction_review(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
    assessment_upload_root: Path,
):
    pdf_bytes = _build_pdf_bytes(
        [
            [
                "1 State the charge of a proton. [1]",
                "(a) State the charge of an electron. [1]",
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

    created = create_response.json()

    original_page_data = created["page_data"]
    original_source = dict(
        created["proposal_data"]["questions"][0]["source"],
    )

    payload = _review_payload_from_extraction(
        created,
        review_status="reviewed",
        review_notes="  Checked against the source paper.  ",
    )

    payload["questions"][0]["question_number"] = "1 "
    payload["questions"][0]["text"] = "  State the relative charge of a proton.  "
    payload["questions"][0]["marks"] = 2

    payload["questions"][1]["included"] = False

    response = await client.patch(
        (
            f"/api/v1/assessments/{assessment['id']}"
            f"/question-extractions/{created['id']}/review"
        ),
        json=payload,
        headers=auth_headers(
            teacher_user,
        ),
    )

    assert response.status_code == 200, response.text

    data = response.json()

    assert data["id"] == created["id"]
    assert data["status"] == (AssessmentQuestionExtractionStatus.COMPLETED.value)
    assert data["page_data"] == original_page_data
    assert data["message"] == "Question extraction review saved."

    proposal = data["proposal_data"]

    assert proposal["review_status"] == "reviewed"
    assert proposal["review_required"] is False
    assert proposal["auto_import_allowed"] is False
    assert proposal["review_notes"] == "Checked against the source paper."
    assert proposal["reviewed_by_id"] == teacher_user.id
    assert proposal["reviewed_at"] is not None

    first_question = proposal["questions"][0]
    second_question = proposal["questions"][1]

    assert first_question["question_number"] == "1"
    assert first_question["text"] == ("State the relative charge of a proton.")
    assert first_question["marks"] == 2
    assert first_question["included"] is True
    assert first_question["reviewed"] is True
    assert first_question["source"] == original_source

    assert second_question["included"] is False

    assert proposal["summary"]["included_question_count"] == 1
    assert proposal["summary"]["included_mark_sum"] == 2


@pytest.mark.asyncio
async def test_review_api_rejects_incomplete_candidate_payload(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
    assessment_upload_root: Path,
):
    pdf_bytes = _build_pdf_bytes(
        [
            [
                "1 State the charge of a proton. [1]",
                "(a) State the charge of an electron. [1]",
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

    created = create_response.json()

    payload = _review_payload_from_extraction(
        created,
    )

    payload["questions"] = payload["questions"][:1]

    response = await client.patch(
        (
            f"/api/v1/assessments/{assessment['id']}"
            f"/question-extractions/{created['id']}/review"
        ),
        json=payload,
        headers=auth_headers(
            teacher_user,
        ),
    )

    assert response.status_code == 422

    assert "each stored extraction candidate" in _error_message(
        response,
    )


@pytest.mark.asyncio
async def test_review_api_rejects_duplicate_included_question_numbers(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
    assessment_upload_root: Path,
):
    pdf_bytes = _build_pdf_bytes(
        [
            [
                "1 State the charge of a proton. [1]",
                "(a) State the charge of an electron. [1]",
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

    created = create_response.json()

    payload = _review_payload_from_extraction(
        created,
    )

    assert (
        len(
            payload["questions"],
        )
        == 2
    )

    payload["questions"][0]["question_number"] = "1(a)"
    payload["questions"][1]["question_number"] = "1 (a)"

    response = await client.patch(
        (
            f"/api/v1/assessments/{assessment['id']}"
            f"/question-extractions/{created['id']}/review"
        ),
        json=payload,
        headers=auth_headers(
            teacher_user,
        ),
    )

    assert response.status_code == 422

    assert "unique question numbers" in _error_message(
        response,
    )


@pytest.mark.asyncio
async def test_review_api_rejects_superseded_extraction(
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

    first_extraction = first_response.json()

    second_response = await client.post(
        extraction_url,
        headers=auth_headers(
            teacher_user,
        ),
    )

    assert second_response.status_code == 201, second_response.text

    payload = _review_payload_from_extraction(
        first_extraction,
    )

    response = await client.patch(
        (
            f"/api/v1/assessments/{assessment['id']}"
            f"/question-extractions/{first_extraction['id']}/review"
        ),
        json=payload,
        headers=auth_headers(
            teacher_user,
        ),
    )

    assert response.status_code == 409

    assert "completed, active extraction proposal" in _error_message(
        response,
    )


@pytest.mark.asyncio
async def test_unrelated_teacher_cannot_review_question_extraction(
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

    created = create_response.json()

    other_teacher = await create_test_user(
        db_session,
        email="assessment.extraction.review.other.teacher@example.com",
        roles=[
            UserRole.TEACHER,
        ],
        school_id=teacher_user.school_id,
    )

    payload = _review_payload_from_extraction(
        created,
    )

    response = await client.patch(
        (
            f"/api/v1/assessments/{assessment['id']}"
            f"/question-extractions/{created['id']}/review"
        ),
        json=payload,
        headers=auth_headers(
            other_teacher,
        ),
    )

    assert response.status_code == 403


# ---------------------------------------------------------------------------
# Explicit import
# ---------------------------------------------------------------------------


async def _create_and_review_extraction_for_import(
    client: AsyncClient,
    db_session: AsyncSession,
    *,
    teacher_user,
    auth_headers,
    pdf_bytes: bytes,
    question_numbers: list[str] | None = None,
    marks: list[int | None] | None = None,
) -> tuple[
    dict,
    dict,
    dict,
]:
    """
    Create an assessment/document/extraction and mark its proposal reviewed.

    Optional question numbers and marks allow API import tests to exercise
    hierarchy synthesis independently from the parser's initial numbering.
    """

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

    extraction = create_response.json()

    payload = _review_payload_from_extraction(
        extraction,
        review_status="reviewed",
    )

    if question_numbers is not None:
        assert len(question_numbers) == len(
            payload["questions"],
        )

        for question, question_number in zip(
            payload["questions"],
            question_numbers,
            strict=True,
        ):
            question["question_number"] = question_number
            question["parent_question_number"] = None

    if marks is not None:
        assert len(marks) == len(
            payload["questions"],
        )

        for question, question_marks in zip(
            payload["questions"],
            marks,
            strict=True,
        ):
            question["marks"] = question_marks

    review_response = await client.patch(
        (
            f"/api/v1/assessments/{assessment['id']}"
            f"/question-extractions/{extraction['id']}/review"
        ),
        json=payload,
        headers=auth_headers(
            teacher_user,
        ),
    )

    assert review_response.status_code == 200, review_response.text

    return (
        assessment,
        document,
        review_response.json(),
    )


@pytest.mark.asyncio
async def test_teacher_can_import_reviewed_question_extraction(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
    assessment_upload_root: Path,
):
    pdf_bytes = _build_pdf_bytes(
        [
            [
                "1 State the charge of a proton. [2]",
                "(a) State the charge of an electron. [3]",
            ],
        ]
    )

    assessment, _, reviewed = await _create_and_review_extraction_for_import(
        client,
        db_session,
        teacher_user=teacher_user,
        auth_headers=auth_headers,
        pdf_bytes=pdf_bytes,
        question_numbers=[
            "1(a)",
            "1(b)",
        ],
        marks=[
            2,
            3,
        ],
    )

    response = await client.post(
        (
            f"/api/v1/assessments/{assessment['id']}"
            f"/question-extractions/{reviewed['id']}/import"
        ),
        headers=auth_headers(
            teacher_user,
        ),
    )

    assert response.status_code == 200, response.text

    data = response.json()

    assert data["id"] == reviewed["id"]
    assert data["status"] == AssessmentQuestionExtractionStatus.IMPORTED.value
    assert data["imported_by_id"] == teacher_user.id
    assert data["imported_at"] is not None

    assert data["message"] == "Reviewed question extraction imported."
    assert data["imported_question_count"] == 3
    assert data["imported_markable_question_count"] == 2
    assert data["synthesised_parent_count"] == 1
    assert Decimal(
        str(
            data["imported_total_marks"],
        )
    ) == Decimal("5")

    imported_questions = data["imported_questions"]

    assert [question["question_number"] for question in imported_questions] == [
        "1",
        "1(a)",
        "1(b)",
    ]

    by_number = {
        question["question_number"]: question for question in imported_questions
    }

    assert by_number["1"]["is_markable"] is False
    assert by_number["1"]["synthesised"] is True
    assert Decimal(
        str(
            by_number["1"]["maximum_mark"],
        )
    ) == Decimal("0")

    assert by_number["1(a)"]["is_markable"] is True
    assert by_number["1(b)"]["is_markable"] is True

    assert by_number["1(a)"]["parent_question_id"] == by_number["1"]["id"]
    assert by_number["1(b)"]["parent_question_id"] == by_number["1"]["id"]

    result = await db_session.execute(
        select(
            AssessmentQuestion,
        )
        .where(
            AssessmentQuestion.assessment_id == assessment["id"],
        )
        .order_by(
            AssessmentQuestion.order.asc(),
        )
    )

    canonical_questions = list(
        result.scalars().all(),
    )

    assert [question.question_number for question in canonical_questions] == [
        "1",
        "1(a)",
        "1(b)",
    ]


@pytest.mark.asyncio
async def test_import_api_rejects_unreviewed_extraction(
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

    extraction = create_response.json()

    response = await client.post(
        (
            f"/api/v1/assessments/{assessment['id']}"
            f"/question-extractions/{extraction['id']}/import"
        ),
        headers=auth_headers(
            teacher_user,
        ),
    )

    assert response.status_code == 409
    assert "fully reviewed before import" in _error_message(
        response,
    )

    result = await db_session.execute(
        select(
            func.count(
                AssessmentQuestion.id,
            ),
        ).where(
            AssessmentQuestion.assessment_id == assessment["id"],
        )
    )

    assert result.scalar_one() == 0


@pytest.mark.asyncio
async def test_import_api_rejects_question_number_conflict(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
    assessment_upload_root: Path,
):
    pdf_bytes = _build_pdf_bytes(
        [
            [
                "1 State the charge of a proton. [1]",
            ],
        ]
    )

    assessment, _, reviewed = await _create_and_review_extraction_for_import(
        client,
        db_session,
        teacher_user=teacher_user,
        auth_headers=auth_headers,
        pdf_bytes=pdf_bytes,
    )

    existing = AssessmentQuestion(
        assessment_id=assessment["id"],
        section_id=None,
        parent_question_id=None,
        question_number="1",
        title=None,
        prompt="Existing canonical question.",
        maximum_mark=Decimal("1"),
        order=1,
        is_markable=True,
    )

    db_session.add(
        existing,
    )
    await db_session.commit()

    response = await client.post(
        (
            f"/api/v1/assessments/{assessment['id']}"
            f"/question-extractions/{reviewed['id']}/import"
        ),
        headers=auth_headers(
            teacher_user,
        ),
    )

    assert response.status_code == 409
    assert "question numbers already exist" in _error_message(
        response,
    )

    result = await db_session.execute(
        select(
            AssessmentQuestion,
        ).where(
            AssessmentQuestion.assessment_id == assessment["id"],
        )
    )

    questions = list(
        result.scalars().all(),
    )

    assert len(questions) == 1
    assert questions[0].id == existing.id


@pytest.mark.asyncio
async def test_import_api_rejects_second_import(
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

    assessment, _, reviewed = await _create_and_review_extraction_for_import(
        client,
        db_session,
        teacher_user=teacher_user,
        auth_headers=auth_headers,
        pdf_bytes=pdf_bytes,
    )

    import_url = (
        f"/api/v1/assessments/{assessment['id']}"
        f"/question-extractions/{reviewed['id']}/import"
    )

    first_response = await client.post(
        import_url,
        headers=auth_headers(
            teacher_user,
        ),
    )

    assert first_response.status_code == 200, first_response.text

    second_response = await client.post(
        import_url,
        headers=auth_headers(
            teacher_user,
        ),
    )

    assert second_response.status_code == 409
    assert "already been imported" in _error_message(
        second_response,
    )


@pytest.mark.asyncio
async def test_import_api_rejects_superseded_extraction(
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

    first_extraction = first_response.json()

    review_payload = _review_payload_from_extraction(
        first_extraction,
        review_status="reviewed",
    )

    review_response = await client.patch(
        (
            f"/api/v1/assessments/{assessment['id']}"
            f"/question-extractions/{first_extraction['id']}/review"
        ),
        json=review_payload,
        headers=auth_headers(
            teacher_user,
        ),
    )

    assert review_response.status_code == 200, review_response.text

    second_response = await client.post(
        extraction_url,
        headers=auth_headers(
            teacher_user,
        ),
    )

    assert second_response.status_code == 201, second_response.text

    response = await client.post(
        (
            f"/api/v1/assessments/{assessment['id']}"
            f"/question-extractions/{first_extraction['id']}/import"
        ),
        headers=auth_headers(
            teacher_user,
        ),
    )

    assert response.status_code == 409
    assert "completed, active extraction proposal" in _error_message(
        response,
    )


@pytest.mark.asyncio
async def test_import_api_rejects_missing_marks(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
    assessment_upload_root: Path,
):
    pdf_bytes = _build_pdf_bytes(
        [
            [
                "1 Define isotope.",
            ],
        ]
    )

    assessment, _, reviewed = await _create_and_review_extraction_for_import(
        client,
        db_session,
        teacher_user=teacher_user,
        auth_headers=auth_headers,
        pdf_bytes=pdf_bytes,
        marks=[
            None,
        ],
    )

    response = await client.post(
        (
            f"/api/v1/assessments/{assessment['id']}"
            f"/question-extractions/{reviewed['id']}/import"
        ),
        headers=auth_headers(
            teacher_user,
        ),
    )

    assert response.status_code == 422
    assert "must have a non-negative integer mark allocation" in _error_message(
        response,
    )


@pytest.mark.asyncio
async def test_unrelated_teacher_cannot_import_question_extraction(
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

    assessment, _, reviewed = await _create_and_review_extraction_for_import(
        client,
        db_session,
        teacher_user=teacher_user,
        auth_headers=auth_headers,
        pdf_bytes=pdf_bytes,
    )

    other_teacher = await create_test_user(
        db_session,
        email="assessment.extraction.import.other.teacher@example.com",
        roles=[
            UserRole.TEACHER,
        ],
        school_id=teacher_user.school_id,
    )

    response = await client.post(
        (
            f"/api/v1/assessments/{assessment['id']}"
            f"/question-extractions/{reviewed['id']}/import"
        ),
        headers=auth_headers(
            other_teacher,
        ),
    )

    assert response.status_code == 403
