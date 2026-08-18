from __future__ import annotations

from decimal import Decimal
from io import BytesIO
from pathlib import Path

import pytest
from fastapi import HTTPException
from reportlab.pdfgen import canvas
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.assessment import (
    Assessment,
    AssessmentStatus,
)
from app.models.assessment_document import AssessmentDocument
from app.models.assessment_question import AssessmentQuestion
from app.models.assessment_question_extraction import (
    AssessmentQuestionExtraction,
    AssessmentQuestionExtractionStatus,
)
from app.models.course import Course
from app.repositories.assessment_question_extraction import (
    AssessmentQuestionExtractionRepository,
)
from app.schemas.assessment_question_extraction import (
    AssessmentQuestionExtractionReviewQuestionUpdate,
    AssessmentQuestionExtractionReviewStatus,
    AssessmentQuestionExtractionReviewUpdate,
)
from app.services import assessment_document_service
import app.services.assessment_question_extraction_service as extraction_service
from app.services.assessment_question_extraction_service import (
    _detect_question_line,
    _read_pdf,
    create_question_extraction,
    get_question_extraction,
    import_question_extraction,
    list_question_extractions_for_document,
    update_question_extraction_review,
)

# ---------------------------------------------------------------------------
# PDF helpers
# ---------------------------------------------------------------------------


def _build_pdf_bytes(
    pages: list[list[str]],
) -> bytes:
    """
    Build a small digital PDF suitable for deterministic extraction tests.

    Each inner list represents one page. An empty list deliberately creates
    a page with no digital text.
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


# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------


async def _create_course(
    db_session: AsyncSession,
    *,
    teacher_id: int,
    school_id: int,
    title: str = "Extraction Test Course",
) -> Course:
    """
    Create a teacher-owned course for extraction tests.
    """

    course = Course(
        title=title,
        description="Course used by question extraction tests.",
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
    db_session: AsyncSession,
    *,
    teacher_id: int,
    school_id: int,
    course_id: int,
    title: str = "Question Extraction Test",
) -> Assessment:
    """
    Create a draft assessment owned by the supplied teacher.
    """

    assessment = Assessment(
        school_id=school_id,
        course_id=course_id,
        created_by_id=teacher_id,
        title=title,
        description="Assessment used by question extraction tests.",
        assessment_type="class_test",
        academic_year="2026/27",
        term="Autumn",
        status=AssessmentStatus.DRAFT,
        anonymous_marking=False,
    )

    db_session.add(
        assessment,
    )

    await db_session.commit()
    await db_session.refresh(
        assessment,
    )

    return assessment


async def _create_question_paper(
    db_session: AsyncSession,
    *,
    assessment: Assessment,
    teacher_user,
    upload_root: Path,
    pdf_bytes: bytes,
    filename: str = "question-paper.pdf",
) -> AssessmentDocument:
    """
    Persist a current question-paper document and its physical PDF.
    """

    assessment_directory = (
        upload_root
        / str(
            assessment.school_id,
        )
        / str(
            assessment.id,
        )
    )

    assessment_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    stored_filename = "test-question-paper.pdf"

    storage_path = assessment_directory / stored_filename

    storage_path.write_bytes(
        pdf_bytes,
    )

    document = AssessmentDocument(
        assessment_id=assessment.id,
        uploaded_by_id=teacher_user.id,
        document_type="question_paper",
        original_filename=filename,
        stored_filename=stored_filename,
        storage_path=str(
            storage_path,
        ),
        mime_type="application/pdf",
        file_size_bytes=len(
            pdf_bytes,
        ),
        is_current=True,
        extraction_requested=False,
        extraction_completed=False,
        extraction_error=None,
    )

    db_session.add(
        document,
    )

    await db_session.commit()
    await db_session.refresh(
        document,
    )

    return document


async def _create_assessment_with_document(
    db_session: AsyncSession,
    *,
    teacher_user,
    upload_root: Path,
    pdf_bytes: bytes,
) -> tuple[
    Assessment,
    AssessmentDocument,
]:
    """
    Create the standard assessment/document pair used by service tests.
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

    document = await _create_question_paper(
        db_session,
        assessment=assessment,
        teacher_user=teacher_user,
        upload_root=upload_root,
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
    Keep extraction test documents outside the real project uploads folder.
    """

    upload_root = tmp_path / "assessment_extraction_uploads"

    monkeypatch.setattr(
        assessment_document_service,
        "ASSESSMENT_UPLOAD_ROOT",
        upload_root,
    )

    return upload_root


# ---------------------------------------------------------------------------
# Parser tests
# ---------------------------------------------------------------------------


def test_detect_question_line_parses_number_and_marks():
    detected = _detect_question_line(
        "1(a)(i) State the relative charge of a proton. [2]",
    )

    assert detected is not None

    assert detected["question_number"] == "1(a)(i)"
    assert detected["text"] == ("State the relative charge of a proton.")
    assert detected["marks"] == 2


def test_detect_question_line_accepts_parenthesised_subquestion():
    detected = _detect_question_line(
        "(b) Explain why isotopes have the same chemical properties. 4 marks",
    )

    assert detected is not None

    assert detected["question_number"] == "(b)"
    assert detected["text"] == (
        "Explain why isotopes have the same chemical properties."
    )
    assert detected["marks"] == 4


def test_non_question_text_is_not_detected():
    assert _detect_question_line("Turn over for the next question.") is None


# ---------------------------------------------------------------------------
# PDF-reading tests
# ---------------------------------------------------------------------------


def test_read_pdf_retains_page_evidence_and_candidates(
    tmp_path: Path,
):
    pdf_bytes = _build_pdf_bytes(
        [
            [
                "Atomic Structure",
                "1 State two features of the nuclear model. [2]",
                "(a) Give the relative charge of an electron. [1]",
            ],
            [
                "2 Complete the particle diagram. [4]",
                "(b) State the number of protons. [1]",
            ],
        ]
    )

    pdf_path = tmp_path / "digital-question-paper.pdf"

    pdf_path.write_bytes(
        pdf_bytes,
    )

    source_metadata, pages, proposal = _read_pdf(
        pdf_path,
    )

    assert source_metadata["extractor"] == "pypdf"
    assert source_metadata["page_count"] == 2
    assert source_metadata["text_page_count"] == 2

    assert len(pages) == 2

    assert pages[0]["page_number"] == 1
    assert pages[0]["has_extractable_text"] is True
    assert "Atomic Structure" in pages[0]["text"]

    first_page_numbers = [
        candidate["question_number"] for candidate in pages[0]["question_candidates"]
    ]

    assert "1" in first_page_numbers
    assert "(a)" in first_page_numbers

    second_page_numbers = [
        candidate["question_number"] for candidate in pages[1]["question_candidates"]
    ]

    assert "2" in second_page_numbers
    assert "(b)" in second_page_numbers

    assert proposal["review_required"] is True
    assert proposal["auto_import_allowed"] is False

    proposal_numbers = [
        question["question_number"] for question in proposal["questions"]
    ]

    assert "1" in proposal_numbers
    assert "1(a)" in proposal_numbers
    assert "2" in proposal_numbers
    assert "2(b)" in proposal_numbers


def test_read_pdf_flags_pages_without_extractable_text(
    tmp_path: Path,
):
    pdf_bytes = _build_pdf_bytes(
        [
            [
                "1 State the charge of an electron. [1]",
            ],
            [],
        ]
    )

    pdf_path = tmp_path / "paper-with-blank-page.pdf"

    pdf_path.write_bytes(
        pdf_bytes,
    )

    source_metadata, pages, proposal = _read_pdf(
        pdf_path,
    )

    assert source_metadata["page_count"] == 2
    assert source_metadata["text_page_count"] == 1

    assert pages[0]["has_extractable_text"] is True
    assert pages[1]["has_extractable_text"] is False
    assert pages[1]["text"] == ""

    warnings = proposal["warnings"]

    assert len(warnings) == 1

    assert warnings[0]["code"] == ("pages_without_extractable_text")

    assert warnings[0]["page_numbers"] == [
        2,
    ]


# ---------------------------------------------------------------------------
# Persistence/service tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_question_extraction_persists_review_proposal(
    db_session: AsyncSession,
    teacher_user,
    assessment_upload_root: Path,
):
    pdf_bytes = _build_pdf_bytes(
        [
            [
                "Atomic Structure",
                "1 State two differences between the models. [2]",
                "(a) Explain one difference. [2]",
            ],
            [
                "2 State the relative mass of a neutron. [1]",
                "(a) Complete the diagram. [4]",
            ],
        ]
    )

    assessment, document = await _create_assessment_with_document(
        db_session,
        teacher_user=teacher_user,
        upload_root=assessment_upload_root,
        pdf_bytes=pdf_bytes,
    )

    extraction = await create_question_extraction(
        db=db_session,
        current_user=teacher_user,
        assessment_id=assessment.id,
        document_id=document.id,
    )

    assert extraction.id is not None
    assert extraction.assessment_id == assessment.id
    assert extraction.assessment_document_id == document.id
    assert extraction.requested_by_id == teacher_user.id
    assert extraction.version == 1

    assert extraction.status == (AssessmentQuestionExtractionStatus.COMPLETED.value)

    assert extraction.extractor_name == "pypdf"
    assert extraction.extractor_version is not None

    assert extraction.page_count == 2
    assert extraction.text_page_count == 2

    assert extraction.detected_question_count is not None
    assert extraction.detected_question_count >= 4

    assert extraction.detected_markable_question_count is not None
    assert extraction.detected_markable_question_count >= 4

    assert extraction.detected_total_marks is not None
    assert extraction.detected_total_marks >= 9

    assert extraction.page_data is not None
    assert (
        len(
            extraction.page_data,
        )
        == 2
    )

    assert extraction.proposal_data is not None
    assert extraction.proposal_data["review_required"] is True
    assert extraction.proposal_data["auto_import_allowed"] is False

    refreshed_document = await db_session.get(
        AssessmentDocument,
        document.id,
    )

    assert refreshed_document is not None
    assert refreshed_document.extraction_requested is True
    assert refreshed_document.extraction_completed is True
    assert refreshed_document.extraction_error is None


@pytest.mark.asyncio
async def test_extraction_does_not_create_live_assessment_questions(
    db_session: AsyncSession,
    teacher_user,
    assessment_upload_root: Path,
):
    pdf_bytes = _build_pdf_bytes(
        [
            [
                "1 State the charge of a proton. [1]",
                "(a) State the charge of an electron. [1]",
                "(b) State the relative mass of a neutron. [1]",
            ],
        ]
    )

    assessment, document = await _create_assessment_with_document(
        db_session,
        teacher_user=teacher_user,
        upload_root=assessment_upload_root,
        pdf_bytes=pdf_bytes,
    )

    before_result = await db_session.execute(
        select(
            func.count(
                AssessmentQuestion.id,
            ),
        ).where(
            AssessmentQuestion.assessment_id == assessment.id,
        )
    )

    assert before_result.scalar_one() == 0

    extraction = await create_question_extraction(
        db=db_session,
        current_user=teacher_user,
        assessment_id=assessment.id,
        document_id=document.id,
    )

    assert extraction.status == (AssessmentQuestionExtractionStatus.COMPLETED.value)

    after_result = await db_session.execute(
        select(
            func.count(
                AssessmentQuestion.id,
            ),
        ).where(
            AssessmentQuestion.assessment_id == assessment.id,
        )
    )

    assert after_result.scalar_one() == 0


@pytest.mark.asyncio
async def test_reextracting_document_creates_new_version_and_supersedes_old_proposal(
    db_session: AsyncSession,
    teacher_user,
    assessment_upload_root: Path,
):
    pdf_bytes = _build_pdf_bytes(
        [
            [
                "1 State the relative mass of a proton. [1]",
                "(a) State the relative mass of a neutron. [1]",
            ],
        ]
    )

    assessment, document = await _create_assessment_with_document(
        db_session,
        teacher_user=teacher_user,
        upload_root=assessment_upload_root,
        pdf_bytes=pdf_bytes,
    )

    first_extraction = await create_question_extraction(
        db=db_session,
        current_user=teacher_user,
        assessment_id=assessment.id,
        document_id=document.id,
    )

    assert first_extraction.version == 1

    second_extraction = await create_question_extraction(
        db=db_session,
        current_user=teacher_user,
        assessment_id=assessment.id,
        document_id=document.id,
    )

    assert second_extraction.version == 2

    await db_session.refresh(
        first_extraction,
    )

    assert first_extraction.status == (
        AssessmentQuestionExtractionStatus.SUPERSEDED.value
    )

    assert second_extraction.status == (
        AssessmentQuestionExtractionStatus.COMPLETED.value
    )

    history = await list_question_extractions_for_document(
        db=db_session,
        current_user=teacher_user,
        assessment_id=assessment.id,
        document_id=document.id,
    )

    assert len(history) == 2

    assert [extraction.version for extraction in history] == [
        2,
        1,
    ]


@pytest.mark.asyncio
async def test_get_question_extraction_returns_assessment_scoped_proposal(
    db_session: AsyncSession,
    teacher_user,
    assessment_upload_root: Path,
):
    pdf_bytes = _build_pdf_bytes(
        [
            [
                "1 Define isotope. [2]",
            ],
        ]
    )

    assessment, document = await _create_assessment_with_document(
        db_session,
        teacher_user=teacher_user,
        upload_root=assessment_upload_root,
        pdf_bytes=pdf_bytes,
    )

    created = await create_question_extraction(
        db=db_session,
        current_user=teacher_user,
        assessment_id=assessment.id,
        document_id=document.id,
    )

    loaded = await get_question_extraction(
        db=db_session,
        current_user=teacher_user,
        assessment_id=assessment.id,
        extraction_id=created.id,
    )

    assert loaded.id == created.id
    assert loaded.assessment_id == assessment.id
    assert loaded.assessment_document_id == document.id
    assert loaded.version == 1


@pytest.mark.asyncio
async def test_corrupt_pdf_creates_failed_extraction_history(
    db_session: AsyncSession,
    teacher_user,
    assessment_upload_root: Path,
):
    corrupt_pdf = (
        b"%PDF-1.4\n"
        b"This payload has a PDF header but is not "
        b"a readable PDF structure.\n"
    )

    assessment, document = await _create_assessment_with_document(
        db_session,
        teacher_user=teacher_user,
        upload_root=assessment_upload_root,
        pdf_bytes=corrupt_pdf,
    )

    # Preserve scalar identifiers before the failure path.
    # create_question_extraction() rolls back the session if extraction fails,
    # which can expire ORM instances such as assessment and document.
    assessment_id = assessment.id
    document_id = document.id

    with pytest.raises(
        HTTPException,
    ) as exc_info:
        await create_question_extraction(
            db=db_session,
            current_user=teacher_user,
            assessment_id=assessment_id,
            document_id=document_id,
        )

    assert exc_info.value.status_code == 422

    repository = AssessmentQuestionExtractionRepository(
        db_session,
    )

    history = await repository.list_for_document(
        assessment_document_id=document_id,
        include_relationships=False,
    )

    assert len(history) == 1

    failed_extraction = history[0]

    assert failed_extraction.version == 1
    assert failed_extraction.status == (AssessmentQuestionExtractionStatus.FAILED.value)
    assert failed_extraction.error_message

    refreshed_document = await db_session.get(
        AssessmentDocument,
        document_id,
    )

    assert refreshed_document is not None
    assert refreshed_document.extraction_requested is True
    assert refreshed_document.extraction_completed is False
    assert refreshed_document.extraction_error


@pytest.mark.asyncio
async def test_document_version_unique_constraint_is_reflected_in_repository_sequence(
    db_session: AsyncSession,
    teacher_user,
    assessment_upload_root: Path,
):
    pdf_bytes = _build_pdf_bytes(
        [
            [
                "1 State the number of electrons in a neutral atom. [1]",
            ],
        ]
    )

    assessment, document = await _create_assessment_with_document(
        db_session,
        teacher_user=teacher_user,
        upload_root=assessment_upload_root,
        pdf_bytes=pdf_bytes,
    )

    repository = AssessmentQuestionExtractionRepository(
        db_session,
    )

    assert (
        await repository.get_next_version(
            assessment_document_id=document.id,
        )
        == 1
    )

    await create_question_extraction(
        db=db_session,
        current_user=teacher_user,
        assessment_id=assessment.id,
        document_id=document.id,
    )

    assert (
        await repository.get_next_version(
            assessment_document_id=document.id,
        )
        == 2
    )


# ---------------------------------------------------------------------------
# Teacher review tests
# ---------------------------------------------------------------------------


def _review_update_from_extraction(
    extraction: AssessmentQuestionExtraction,
    *,
    review_status: AssessmentQuestionExtractionReviewStatus = (
        AssessmentQuestionExtractionReviewStatus.IN_PROGRESS
    ),
    review_notes: str | None = None,
) -> AssessmentQuestionExtractionReviewUpdate:
    """
    Build a complete review payload from the stored proposal.

    Individual tests may mutate the returned Pydantic model before saving.
    """

    assert extraction.proposal_data is not None

    stored_questions = extraction.proposal_data.get(
        "questions",
        [],
    )

    return AssessmentQuestionExtractionReviewUpdate(
        review_status=review_status,
        review_notes=review_notes,
        questions=[
            AssessmentQuestionExtractionReviewQuestionUpdate(
                candidate_index=index,
                question_number=str(
                    question["question_number"],
                ),
                text=str(
                    question.get(
                        "text",
                        "",
                    )
                    or ""
                ),
                marks=question.get(
                    "marks",
                ),
                parent_question_number=question.get(
                    "parent_question_number",
                ),
                included=True,
                reviewed=True,
            )
            for index, question in enumerate(
                stored_questions,
            )
        ],
    )


@pytest.mark.asyncio
async def test_update_question_extraction_review_saves_edits_and_preserves_evidence(
    db_session: AsyncSession,
    teacher_user,
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

    assessment, document = await _create_assessment_with_document(
        db_session,
        teacher_user=teacher_user,
        upload_root=assessment_upload_root,
        pdf_bytes=pdf_bytes,
    )

    extraction = await create_question_extraction(
        db=db_session,
        current_user=teacher_user,
        assessment_id=assessment.id,
        document_id=document.id,
    )

    original_page_data = extraction.page_data

    assert extraction.proposal_data is not None

    original_source = dict(
        extraction.proposal_data["questions"][0]["source"],
    )

    review_update = _review_update_from_extraction(
        extraction,
        review_status=AssessmentQuestionExtractionReviewStatus.REVIEWED,
        review_notes="  Checked against the source paper.  ",
    )

    review_update.questions[0].question_number = "1 "
    review_update.questions[0].text = "  State the relative charge of a proton.  "
    review_update.questions[0].marks = 2

    # Excluding a row keeps it in the proposal/history but removes it from
    # review totals and future import eligibility.
    review_update.questions[1].included = False

    updated = await update_question_extraction_review(
        db=db_session,
        current_user=teacher_user,
        assessment_id=assessment.id,
        extraction_id=extraction.id,
        review_update=review_update,
    )

    assert updated.status == AssessmentQuestionExtractionStatus.COMPLETED.value
    assert updated.page_data == original_page_data

    assert updated.proposal_data is not None

    proposal = updated.proposal_data

    assert proposal["review_status"] == (
        AssessmentQuestionExtractionReviewStatus.REVIEWED.value
    )
    assert proposal["review_required"] is False
    assert proposal["auto_import_allowed"] is False
    assert proposal["review_notes"] == "Checked against the source paper."
    assert proposal["reviewed_by_id"] == teacher_user.id
    assert proposal["reviewed_at"]

    first_question = proposal["questions"][0]
    second_question = proposal["questions"][1]

    assert first_question["question_number"] == "1"
    assert first_question["text"] == "State the relative charge of a proton."
    assert first_question["marks"] == 2
    assert first_question["included"] is True
    assert first_question["reviewed"] is True
    assert first_question["source"] == original_source

    assert second_question["included"] is False

    assert proposal["summary"]["included_question_count"] == 1
    assert proposal["summary"]["included_mark_sum"] == 2

    live_question_count_result = await db_session.execute(
        select(
            func.count(
                AssessmentQuestion.id,
            ),
        ).where(
            AssessmentQuestion.assessment_id == assessment.id,
        )
    )

    assert live_question_count_result.scalar_one() == 0


@pytest.mark.asyncio
async def test_update_question_extraction_review_requires_every_candidate_once(
    db_session: AsyncSession,
    teacher_user,
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

    assessment, document = await _create_assessment_with_document(
        db_session,
        teacher_user=teacher_user,
        upload_root=assessment_upload_root,
        pdf_bytes=pdf_bytes,
    )

    extraction = await create_question_extraction(
        db=db_session,
        current_user=teacher_user,
        assessment_id=assessment.id,
        document_id=document.id,
    )

    review_update = _review_update_from_extraction(
        extraction,
    )

    review_update.questions = review_update.questions[:1]

    with pytest.raises(
        HTTPException,
    ) as exc_info:
        await update_question_extraction_review(
            db=db_session,
            current_user=teacher_user,
            assessment_id=assessment.id,
            extraction_id=extraction.id,
            review_update=review_update,
        )

    assert exc_info.value.status_code == 422
    assert "each stored extraction candidate" in str(
        exc_info.value.detail,
    )


@pytest.mark.asyncio
async def test_update_question_extraction_review_rejects_duplicate_included_numbers(
    db_session: AsyncSession,
    teacher_user,
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

    assessment, document = await _create_assessment_with_document(
        db_session,
        teacher_user=teacher_user,
        upload_root=assessment_upload_root,
        pdf_bytes=pdf_bytes,
    )

    extraction = await create_question_extraction(
        db=db_session,
        current_user=teacher_user,
        assessment_id=assessment.id,
        document_id=document.id,
    )

    review_update = _review_update_from_extraction(
        extraction,
    )

    assert (
        len(
            review_update.questions,
        )
        == 2
    )

    review_update.questions[0].question_number = "1(a)"
    review_update.questions[1].question_number = "1 (a)"

    with pytest.raises(
        HTTPException,
    ) as exc_info:
        await update_question_extraction_review(
            db=db_session,
            current_user=teacher_user,
            assessment_id=assessment.id,
            extraction_id=extraction.id,
            review_update=review_update,
        )

    assert exc_info.value.status_code == 422
    assert "unique question numbers" in str(
        exc_info.value.detail,
    )


@pytest.mark.asyncio
async def test_update_question_extraction_review_requires_included_rows_reviewed_before_completion(
    db_session: AsyncSession,
    teacher_user,
    assessment_upload_root: Path,
):
    pdf_bytes = _build_pdf_bytes(
        [
            [
                "1 Define isotope. [2]",
            ],
        ]
    )

    assessment, document = await _create_assessment_with_document(
        db_session,
        teacher_user=teacher_user,
        upload_root=assessment_upload_root,
        pdf_bytes=pdf_bytes,
    )

    extraction = await create_question_extraction(
        db=db_session,
        current_user=teacher_user,
        assessment_id=assessment.id,
        document_id=document.id,
    )

    review_update = _review_update_from_extraction(
        extraction,
        review_status=AssessmentQuestionExtractionReviewStatus.REVIEWED,
    )

    review_update.questions[0].reviewed = False

    with pytest.raises(
        HTTPException,
    ) as exc_info:
        await update_question_extraction_review(
            db=db_session,
            current_user=teacher_user,
            assessment_id=assessment.id,
            extraction_id=extraction.id,
            review_update=review_update,
        )

    assert exc_info.value.status_code == 422
    assert "must be reviewed" in str(
        exc_info.value.detail,
    )


@pytest.mark.asyncio
async def test_update_question_extraction_review_rejects_superseded_extraction(
    db_session: AsyncSession,
    teacher_user,
    assessment_upload_root: Path,
):
    pdf_bytes = _build_pdf_bytes(
        [
            [
                "1 Define isotope. [2]",
            ],
        ]
    )

    assessment, document = await _create_assessment_with_document(
        db_session,
        teacher_user=teacher_user,
        upload_root=assessment_upload_root,
        pdf_bytes=pdf_bytes,
    )

    first_extraction = await create_question_extraction(
        db=db_session,
        current_user=teacher_user,
        assessment_id=assessment.id,
        document_id=document.id,
    )

    review_update = _review_update_from_extraction(
        first_extraction,
    )

    await create_question_extraction(
        db=db_session,
        current_user=teacher_user,
        assessment_id=assessment.id,
        document_id=document.id,
    )

    await db_session.refresh(
        first_extraction,
    )

    assert first_extraction.status == (
        AssessmentQuestionExtractionStatus.SUPERSEDED.value
    )

    with pytest.raises(
        HTTPException,
    ) as exc_info:
        await update_question_extraction_review(
            db=db_session,
            current_user=teacher_user,
            assessment_id=assessment.id,
            extraction_id=first_extraction.id,
            review_update=review_update,
        )

    assert exc_info.value.status_code == 409
    assert "completed, active extraction proposal" in str(
        exc_info.value.detail,
    )


# ---------------------------------------------------------------------------
# Explicit import tests
# ---------------------------------------------------------------------------


async def _review_extraction_for_import(
    db_session: AsyncSession,
    *,
    teacher_user,
    assessment: Assessment,
    extraction: AssessmentQuestionExtraction,
    question_numbers: list[str] | None = None,
    marks: list[int | None] | None = None,
) -> AssessmentQuestionExtraction:
    """
    Mark an extraction proposal fully reviewed and ready for explicit import.

    Optional question numbers/marks allow import tests to exercise hierarchy
    synthesis independently from the PDF parser's initial numbering.
    """

    review_update = _review_update_from_extraction(
        extraction,
        review_status=AssessmentQuestionExtractionReviewStatus.REVIEWED,
    )

    if question_numbers is not None:
        assert len(question_numbers) == len(
            review_update.questions,
        )

        for question, question_number in zip(
            review_update.questions,
            question_numbers,
            strict=True,
        ):
            question.question_number = question_number
            question.parent_question_number = None

    if marks is not None:
        assert len(marks) == len(
            review_update.questions,
        )

        for question, question_marks in zip(
            review_update.questions,
            marks,
            strict=True,
        ):
            question.marks = question_marks

    return await update_question_extraction_review(
        db=db_session,
        current_user=teacher_user,
        assessment_id=assessment.id,
        extraction_id=extraction.id,
        review_update=review_update,
    )


@pytest.mark.asyncio
async def test_import_question_extraction_creates_hierarchy_and_marks_atomically(
    db_session: AsyncSession,
    teacher_user,
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

    assessment, document = await _create_assessment_with_document(
        db_session,
        teacher_user=teacher_user,
        upload_root=assessment_upload_root,
        pdf_bytes=pdf_bytes,
    )

    extraction = await create_question_extraction(
        db=db_session,
        current_user=teacher_user,
        assessment_id=assessment.id,
        document_id=document.id,
    )

    reviewed = await _review_extraction_for_import(
        db_session,
        teacher_user=teacher_user,
        assessment=assessment,
        extraction=extraction,
        question_numbers=[
            "1(a)",
            "1(b)",
        ],
        marks=[
            2,
            3,
        ],
    )

    imported_extraction, imported_questions = await import_question_extraction(
        db=db_session,
        current_user=teacher_user,
        assessment_id=assessment.id,
        extraction_id=reviewed.id,
    )

    assert imported_extraction.status == (
        AssessmentQuestionExtractionStatus.IMPORTED.value
    )
    assert imported_extraction.imported_by_id == teacher_user.id
    assert imported_extraction.imported_at is not None

    assert len(imported_questions) == 3

    by_number = {question.question_number: question for question in imported_questions}

    assert set(by_number) == {
        "1",
        "1(a)",
        "1(b)",
    }

    structural_parent = by_number["1"]

    assert structural_parent.is_markable is False
    assert structural_parent.synthesised is True
    assert structural_parent.maximum_mark == Decimal("0")
    assert structural_parent.parent_question_id is None
    assert structural_parent.source_candidate_index is None

    first_child = by_number["1(a)"]
    second_child = by_number["1(b)"]

    assert first_child.is_markable is True
    assert second_child.is_markable is True
    assert first_child.synthesised is False
    assert second_child.synthesised is False

    assert first_child.parent_question_id == structural_parent.id
    assert second_child.parent_question_id == structural_parent.id

    assert first_child.maximum_mark == Decimal("2")
    assert second_child.maximum_mark == Decimal("3")

    assert sum(
        question.maximum_mark for question in imported_questions if question.is_markable
    ) == Decimal("5")

    result = await db_session.execute(
        select(
            AssessmentQuestion,
        )
        .where(
            AssessmentQuestion.assessment_id == assessment.id,
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

    canonical_by_number = {
        question.question_number: question for question in canonical_questions
    }

    assert canonical_by_number["1"].is_markable is False
    assert canonical_by_number["1"].maximum_mark == Decimal("0.00")

    assert canonical_by_number["1(a)"].parent_question_id == (
        canonical_by_number["1"].id
    )
    assert canonical_by_number["1(b)"].parent_question_id == (
        canonical_by_number["1"].id
    )


@pytest.mark.asyncio
async def test_import_question_extraction_synthesises_nested_parents(
    db_session: AsyncSession,
    teacher_user,
    assessment_upload_root: Path,
):
    pdf_bytes = _build_pdf_bytes(
        [
            [
                "1 State the charge of a proton. [2]",
            ],
        ]
    )

    assessment, document = await _create_assessment_with_document(
        db_session,
        teacher_user=teacher_user,
        upload_root=assessment_upload_root,
        pdf_bytes=pdf_bytes,
    )

    extraction = await create_question_extraction(
        db=db_session,
        current_user=teacher_user,
        assessment_id=assessment.id,
        document_id=document.id,
    )

    reviewed = await _review_extraction_for_import(
        db_session,
        teacher_user=teacher_user,
        assessment=assessment,
        extraction=extraction,
        question_numbers=[
            "1(a)(i)",
        ],
        marks=[
            2,
        ],
    )

    _, imported_questions = await import_question_extraction(
        db=db_session,
        current_user=teacher_user,
        assessment_id=assessment.id,
        extraction_id=reviewed.id,
    )

    assert [question.question_number for question in imported_questions] == [
        "1",
        "1(a)",
        "1(a)(i)",
    ]

    by_number = {question.question_number: question for question in imported_questions}

    assert by_number["1"].synthesised is True
    assert by_number["1(a)"].synthesised is True
    assert by_number["1(a)(i)"].synthesised is False

    assert by_number["1(a)"].parent_question_id == by_number["1"].id
    assert by_number["1(a)(i)"].parent_question_id == by_number["1(a)"].id


@pytest.mark.asyncio
async def test_import_question_extraction_requires_completed_teacher_review(
    db_session: AsyncSession,
    teacher_user,
    assessment_upload_root: Path,
):
    pdf_bytes = _build_pdf_bytes(
        [
            [
                "1 Define isotope. [2]",
            ],
        ]
    )

    assessment, document = await _create_assessment_with_document(
        db_session,
        teacher_user=teacher_user,
        upload_root=assessment_upload_root,
        pdf_bytes=pdf_bytes,
    )

    extraction = await create_question_extraction(
        db=db_session,
        current_user=teacher_user,
        assessment_id=assessment.id,
        document_id=document.id,
    )

    with pytest.raises(
        HTTPException,
    ) as exc_info:
        await import_question_extraction(
            db=db_session,
            current_user=teacher_user,
            assessment_id=assessment.id,
            extraction_id=extraction.id,
        )

    assert exc_info.value.status_code == 409
    assert "fully reviewed before import" in str(
        exc_info.value.detail,
    )

    result = await db_session.execute(
        select(
            func.count(
                AssessmentQuestion.id,
            ),
        ).where(
            AssessmentQuestion.assessment_id == assessment.id,
        )
    )

    assert result.scalar_one() == 0


@pytest.mark.asyncio
async def test_import_question_extraction_requires_marks_on_included_questions(
    db_session: AsyncSession,
    teacher_user,
    assessment_upload_root: Path,
):
    pdf_bytes = _build_pdf_bytes(
        [
            [
                "1 Define isotope.",
            ],
        ]
    )

    assessment, document = await _create_assessment_with_document(
        db_session,
        teacher_user=teacher_user,
        upload_root=assessment_upload_root,
        pdf_bytes=pdf_bytes,
    )

    extraction = await create_question_extraction(
        db=db_session,
        current_user=teacher_user,
        assessment_id=assessment.id,
        document_id=document.id,
    )

    reviewed = await _review_extraction_for_import(
        db_session,
        teacher_user=teacher_user,
        assessment=assessment,
        extraction=extraction,
        marks=[
            None,
        ],
    )

    with pytest.raises(
        HTTPException,
    ) as exc_info:
        await import_question_extraction(
            db=db_session,
            current_user=teacher_user,
            assessment_id=assessment.id,
            extraction_id=reviewed.id,
        )

    assert exc_info.value.status_code == 422
    assert "must have a non-negative integer mark allocation" in str(
        exc_info.value.detail,
    )

    await db_session.refresh(
        reviewed,
    )

    assert reviewed.status == AssessmentQuestionExtractionStatus.COMPLETED.value

    result = await db_session.execute(
        select(
            func.count(
                AssessmentQuestion.id,
            ),
        ).where(
            AssessmentQuestion.assessment_id == assessment.id,
        )
    )

    assert result.scalar_one() == 0


@pytest.mark.asyncio
async def test_import_question_extraction_rejects_existing_question_number_conflict(
    db_session: AsyncSession,
    teacher_user,
    assessment_upload_root: Path,
):
    pdf_bytes = _build_pdf_bytes(
        [
            [
                "1 State the charge of a proton. [1]",
            ],
        ]
    )

    assessment, document = await _create_assessment_with_document(
        db_session,
        teacher_user=teacher_user,
        upload_root=assessment_upload_root,
        pdf_bytes=pdf_bytes,
    )

    existing = AssessmentQuestion(
        assessment_id=assessment.id,
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

    extraction = await create_question_extraction(
        db=db_session,
        current_user=teacher_user,
        assessment_id=assessment.id,
        document_id=document.id,
    )

    reviewed = await _review_extraction_for_import(
        db_session,
        teacher_user=teacher_user,
        assessment=assessment,
        extraction=extraction,
    )

    with pytest.raises(
        HTTPException,
    ) as exc_info:
        await import_question_extraction(
            db=db_session,
            current_user=teacher_user,
            assessment_id=assessment.id,
            extraction_id=reviewed.id,
        )

    assert exc_info.value.status_code == 409
    assert "question numbers already exist" in str(
        exc_info.value.detail,
    )

    result = await db_session.execute(
        select(
            AssessmentQuestion,
        ).where(
            AssessmentQuestion.assessment_id == assessment.id,
        )
    )

    questions = list(
        result.scalars().all(),
    )

    assert len(questions) == 1
    assert questions[0].id == existing.id

    await db_session.refresh(
        reviewed,
    )

    assert reviewed.status == AssessmentQuestionExtractionStatus.COMPLETED.value


@pytest.mark.asyncio
async def test_import_question_extraction_cannot_be_imported_twice(
    db_session: AsyncSession,
    teacher_user,
    assessment_upload_root: Path,
):
    pdf_bytes = _build_pdf_bytes(
        [
            [
                "1 State the relative mass of a proton. [1]",
            ],
        ]
    )

    assessment, document = await _create_assessment_with_document(
        db_session,
        teacher_user=teacher_user,
        upload_root=assessment_upload_root,
        pdf_bytes=pdf_bytes,
    )

    extraction = await create_question_extraction(
        db=db_session,
        current_user=teacher_user,
        assessment_id=assessment.id,
        document_id=document.id,
    )

    reviewed = await _review_extraction_for_import(
        db_session,
        teacher_user=teacher_user,
        assessment=assessment,
        extraction=extraction,
    )

    imported, _ = await import_question_extraction(
        db=db_session,
        current_user=teacher_user,
        assessment_id=assessment.id,
        extraction_id=reviewed.id,
    )

    with pytest.raises(
        HTTPException,
    ) as exc_info:
        await import_question_extraction(
            db=db_session,
            current_user=teacher_user,
            assessment_id=assessment.id,
            extraction_id=imported.id,
        )

    assert exc_info.value.status_code == 409
    assert "already been imported" in str(
        exc_info.value.detail,
    )

    result = await db_session.execute(
        select(
            func.count(
                AssessmentQuestion.id,
            ),
        ).where(
            AssessmentQuestion.assessment_id == assessment.id,
        )
    )

    assert result.scalar_one() == 1


@pytest.mark.asyncio
async def test_import_question_extraction_rejects_superseded_extraction(
    db_session: AsyncSession,
    teacher_user,
    assessment_upload_root: Path,
):
    pdf_bytes = _build_pdf_bytes(
        [
            [
                "1 Define isotope. [2]",
            ],
        ]
    )

    assessment, document = await _create_assessment_with_document(
        db_session,
        teacher_user=teacher_user,
        upload_root=assessment_upload_root,
        pdf_bytes=pdf_bytes,
    )

    first_extraction = await create_question_extraction(
        db=db_session,
        current_user=teacher_user,
        assessment_id=assessment.id,
        document_id=document.id,
    )

    reviewed_first = await _review_extraction_for_import(
        db_session,
        teacher_user=teacher_user,
        assessment=assessment,
        extraction=first_extraction,
    )

    await create_question_extraction(
        db=db_session,
        current_user=teacher_user,
        assessment_id=assessment.id,
        document_id=document.id,
    )

    await db_session.refresh(
        reviewed_first,
    )

    assert reviewed_first.status == (
        AssessmentQuestionExtractionStatus.SUPERSEDED.value
    )

    with pytest.raises(
        HTTPException,
    ) as exc_info:
        await import_question_extraction(
            db=db_session,
            current_user=teacher_user,
            assessment_id=assessment.id,
            extraction_id=reviewed_first.id,
        )

    assert exc_info.value.status_code == 409
    assert "completed, active extraction proposal" in str(
        exc_info.value.detail,
    )


@pytest.mark.asyncio
async def test_import_question_extraction_rolls_back_partial_question_creation(
    db_session: AsyncSession,
    teacher_user,
    assessment_upload_root: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    pdf_bytes = _build_pdf_bytes(
        [
            [
                "1 State the charge of a proton. [2]",
                "(a) State the charge of an electron. [3]",
            ],
        ]
    )

    assessment, document = await _create_assessment_with_document(
        db_session,
        teacher_user=teacher_user,
        upload_root=assessment_upload_root,
        pdf_bytes=pdf_bytes,
    )

    assessment_id = assessment.id

    extraction = await create_question_extraction(
        db=db_session,
        current_user=teacher_user,
        assessment_id=assessment_id,
        document_id=document.id,
    )

    reviewed = await _review_extraction_for_import(
        db_session,
        teacher_user=teacher_user,
        assessment=assessment,
        extraction=extraction,
        question_numbers=[
            "1(a)",
            "1(b)",
        ],
        marks=[
            2,
            3,
        ],
    )

    extraction_id = reviewed.id

    original_create_question = (
        extraction_service.AssessmentQuestionRepository.create_question
    )

    call_count = 0

    async def fail_on_second_question(
        self,
        question,
    ):
        nonlocal call_count

        call_count += 1

        if call_count == 2:
            raise RuntimeError(
                "Synthetic import failure.",
            )

        return await original_create_question(
            self,
            question,
        )

    monkeypatch.setattr(
        extraction_service.AssessmentQuestionRepository,
        "create_question",
        fail_on_second_question,
    )

    with pytest.raises(
        RuntimeError,
        match="Synthetic import failure",
    ):
        await import_question_extraction(
            db=db_session,
            current_user=teacher_user,
            assessment_id=assessment_id,
            extraction_id=extraction_id,
        )

    result = await db_session.execute(
        select(
            func.count(
                AssessmentQuestion.id,
            ),
        ).where(
            AssessmentQuestion.assessment_id == assessment_id,
        )
    )

    assert result.scalar_one() == 0

    refreshed_extraction = await db_session.get(
        AssessmentQuestionExtraction,
        extraction_id,
    )

    assert refreshed_extraction is not None
    assert refreshed_extraction.status == (
        AssessmentQuestionExtractionStatus.COMPLETED.value
    )
    assert refreshed_extraction.imported_by_id is None
    assert refreshed_extraction.imported_at is None
