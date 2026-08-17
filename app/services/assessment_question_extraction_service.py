from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import HTTPException, status
from pypdf import PdfReader, __version__ as pypdf_version
from pypdf.errors import PdfReadError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.assessment_document import AssessmentDocument
from app.models.assessment_question_extraction import (
    AssessmentQuestionExtraction,
    AssessmentQuestionExtractionStatus,
)
from app.models.user import User
from app.repositories.assessment_document import AssessmentDocumentRepository
from app.repositories.assessment_question_extraction import (
    AssessmentQuestionExtractionRepository,
)
from app.services.assessment_document_service import (
    QUESTION_PAPER_DOCUMENT_TYPE,
    get_assessment_document,
    resolve_assessment_document_path,
)

PARSER_VERSION = "1"

MAX_EXTRACTED_PAGE_TEXT_LENGTH = 100_000


QUESTION_NUMBER_PATTERN = re.compile(
    r"""
    ^
    \s*
    (?P<number>
        \d+
        (?:
            \s*
            \(
                [A-Za-z0-9]+
            \)
        )*
    )
    (?:
        [\.\:\)]
        |
        \s+
    )
    (?P<text>.*)
    $
    """,
    re.VERBOSE,
)


PARENTHESISED_PART_PATTERN = re.compile(
    r"""
    ^
    \s*
    (?P<number>
        (?:
            \(
                [A-Za-z]+
            \)
        )+
    )
    \s*
    (?P<text>.*)
    $
    """,
    re.VERBOSE,
)


STANDALONE_MARK_PATTERN = re.compile(
    r"""
    ^
    \s*
    \(
        \s*
        (?P<marks>\d+)
        \s*
    \)
    \s*
    $
    """,
    re.VERBOSE,
)


TOTAL_MARK_PATTERN = re.compile(
    r"""
    ^
    \s*
    \(
        \s*
        total
        \s+
        (?P<marks>\d+)
        \s+
        marks?
        \s*
    \)
    \s*
    $
    """,
    re.IGNORECASE | re.VERBOSE,
)


TRAILING_MARK_PATTERN = re.compile(
    r"""
    (?:
        \[
            \s*
            (?P<bracket_marks>\d+)
            \s*
            (?:marks?|m)?
            \s*
        \]
        |
        \(
            \s*
            (?P<paren_marks>\d+)
            \s*
            marks?
            \s*
        \)
        |
        (?P<plain_marks>\d+)
        \s*
        marks?
    )
    \s*
    $
    """,
    re.IGNORECASE | re.VERBOSE,
)


PAGE_FOOTER_PATTERN = re.compile(
    r"""
    ^
    \s*
    page
    \s+
    \d+
    \s+
    of
    \s+
    \d+
    """,
    re.IGNORECASE | re.VERBOSE,
)


ANSWER_LINE_PATTERN = re.compile(
    r"""
    ^
    \s*
    [_\-.]{5,}
    \s*
    $
    """,
    re.VERBOSE,
)


def _utc_now() -> datetime:
    """
    Return a timezone-aware UTC timestamp.
    """

    return datetime.now(
        timezone.utc,
    )


def _normalise_page_text(
    text: str | None,
) -> str:
    """
    Normalise text extracted from one PDF page.

    The original PDF remains the authoritative source document. This cleanup
    exists only to make extracted text easier to inspect and parse.
    """

    if not text:
        return ""

    normalised = text.replace(
        "\x00",
        "",
    )

    normalised = normalised.replace(
        "\r\n",
        "\n",
    ).replace(
        "\r",
        "\n",
    )

    lines = [line.rstrip() for line in normalised.splitlines()]

    normalised = "\n".join(
        lines,
    ).strip()

    if len(normalised) > MAX_EXTRACTED_PAGE_TEXT_LENGTH:
        normalised = normalised[:MAX_EXTRACTED_PAGE_TEXT_LENGTH]

    return normalised


def _serialise_pdf_metadata(
    reader: PdfReader,
) -> dict[str, Any]:
    """
    Convert pypdf document metadata into JSON-safe values.
    """

    metadata = reader.metadata

    if metadata is None:
        return {}

    serialised: dict[str, Any] = {}

    for key, value in metadata.items():
        clean_key = str(
            key,
        ).strip()

        if not clean_key:
            continue

        if value is None:
            serialised[clean_key] = None
        elif isinstance(
            value,
            (
                str,
                int,
                float,
                bool,
            ),
        ):
            serialised[clean_key] = value
        else:
            serialised[clean_key] = str(
                value,
            )

    return serialised


def _extract_mark_from_text(
    text: str,
) -> tuple[str, int | None]:
    """
    Extract an inline trailing mark allocation where one is obvious.

    Examples supported include:

    - ``[2]``
    - ``[2 marks]``
    - ``(2 marks)``
    - ``2 marks``

    A bare standalone ``(2)`` is deliberately handled separately. In many
    school and examination-board PDFs that notation appears on its own line
    after the question rather than on the question line itself.
    """

    match = TRAILING_MARK_PATTERN.search(
        text,
    )

    if match is None:
        return (
            text.strip(),
            None,
        )

    raw_marks = (
        match.group(
            "bracket_marks",
        )
        or match.group(
            "paren_marks",
        )
        or match.group(
            "plain_marks",
        )
    )

    if raw_marks is None:
        return (
            text.strip(),
            None,
        )

    try:
        marks = int(
            raw_marks,
        )
    except ValueError:
        return (
            text.strip(),
            None,
        )

    if marks < 0:
        return (
            text.strip(),
            None,
        )

    question_text = text[: match.start()].rstrip()

    return (
        question_text,
        marks,
    )


def _extract_standalone_mark(
    line: str,
) -> int | None:
    """
    Return a standalone mark allocation such as ``(2)``.

    Numeric parenthesised lines are treated as mark allocations rather than
    question identifiers. This distinction is important for papers where
    marks are printed on a separate line after the answer space.
    """

    match = STANDALONE_MARK_PATTERN.match(
        line.strip(),
    )

    if match is None:
        return None

    try:
        marks = int(
            match.group(
                "marks",
            )
        )
    except ValueError:
        return None

    if marks < 0:
        return None

    return marks


def _extract_declared_total(
    line: str,
) -> int | None:
    """
    Return a declared section/question total such as ``(Total 8 marks)``.
    """

    match = TOTAL_MARK_PATTERN.match(
        line.strip(),
    )

    if match is None:
        return None

    try:
        marks = int(
            match.group(
                "marks",
            )
        )
    except ValueError:
        return None

    if marks < 0:
        return None

    return marks


def _normalise_question_number(
    value: str,
) -> str:
    """
    Remove whitespace from a detected question identifier.

    ``1 (a) (i)`` therefore becomes ``1(a)(i)``.
    """

    return re.sub(
        r"\s+",
        "",
        value,
    )


def _is_main_question_number(
    question_number: str,
) -> bool:
    """
    Return True when the identifier is a plain top-level number.
    """

    return question_number.isdigit()


def _main_number_from_question_number(
    question_number: str,
) -> str | None:
    """
    Return the leading numeric main-question identifier when present.
    """

    match = re.match(
        r"^(?P<number>\d+)",
        question_number,
    )

    if match is None:
        return None

    return match.group(
        "number",
    )


def _detect_question_line(
    line: str,
) -> dict[str, Any] | None:
    """
    Detect a possible numbered question or sub-question line.

    Numeric-only parenthesised values such as ``(2)`` are deliberately not
    treated as question identifiers because those are commonly standalone
    mark allocations.

    The result remains only a proposal for teacher review and never creates
    canonical assessment questions directly.
    """

    stripped = line.strip()

    if not stripped:
        return None

    if (
        _extract_declared_total(
            stripped,
        )
        is not None
    ):
        return None

    if (
        _extract_standalone_mark(
            stripped,
        )
        is not None
    ):
        return None

    match = QUESTION_NUMBER_PATTERN.match(
        stripped,
    )

    if match is None:
        match = PARENTHESISED_PART_PATTERN.match(
            stripped,
        )

    if match is None:
        return None

    question_number = _normalise_question_number(
        match.group(
            "number",
        ),
    )

    raw_text = (
        match.group(
            "text",
        )
        or ""
    ).strip()

    question_text, marks = _extract_mark_from_text(
        raw_text,
    )

    return {
        "question_number": question_number,
        "text": question_text,
        "marks": marks,
    }


def _extract_question_candidates_from_page(
    *,
    page_number: int,
    text: str,
) -> list[dict[str, Any]]:
    """
    Return locally detectable question-like lines from one page.

    Parent relationships and standalone mark allocations are resolved later
    across the entire document because the main question number, sub-question
    and mark allocation can appear on different lines or even different pages.
    """

    candidates: list[dict[str, Any]] = []

    for line_number, line in enumerate(
        text.splitlines(),
        start=1,
    ):
        detected = _detect_question_line(
            line,
        )

        if detected is None:
            continue

        candidates.append(
            {
                **detected,
                "page_number": page_number,
                "line_number": line_number,
                "source_line": line.strip(),
            }
        )

    return candidates


def _infer_question_depth(
    question_number: str,
) -> int:
    """
    Infer structural depth from a question identifier.

    Examples:

    - ``1`` -> 0
    - ``1(a)`` -> 1
    - ``1(a)(i)`` -> 2
    - ``(a)`` -> 1
    """

    return question_number.count(
        "(",
    )


def _is_page_footer(
    line: str,
) -> bool:
    """
    Return True for a conventional ``Page X of Y`` footer.
    """

    return bool(
        PAGE_FOOTER_PATTERN.match(
            line.strip(),
        )
    )


def _is_answer_line(
    line: str,
) -> bool:
    """
    Return True for a line made almost entirely from answer-space characters.
    """

    return bool(
        ANSWER_LINE_PATTERN.match(
            line.strip(),
        )
    )


def _clean_continuation_line(
    line: str,
) -> str | None:
    """
    Return useful continuation text or None for obvious layout-only material.

    We retain instructions, choices and scientific context because those may
    be essential to the meaning of the question. Only blank lines, page
    footers and pure answer-space lines are discarded.
    """

    stripped = line.strip()

    if not stripped:
        return None

    if _is_page_footer(
        stripped,
    ):
        return None

    if _is_answer_line(
        stripped,
    ):
        return None

    return stripped


def _new_proposal_question(
    *,
    question_number: str,
    text: str,
    marks: int | None,
    page_number: int,
    line_number: int,
    source_line: str,
) -> dict[str, Any]:
    """
    Create one reviewable proposal question.
    """

    return {
        "question_number": question_number,
        "text": text.strip(),
        "marks": marks,
        "depth": _infer_question_depth(
            question_number,
        ),
        "source": {
            "page_number": page_number,
            "line_number": line_number,
            "source_line": source_line,
        },
        "confidence": "candidate",
        "requires_review": True,
    }


def _append_question_text(
    question: dict[str, Any],
    line: str,
) -> None:
    """
    Append useful continuation text to a detected question.
    """

    continuation = _clean_continuation_line(
        line,
    )

    if continuation is None:
        return

    existing_text = str(
        question.get(
            "text",
            "",
        )
        or ""
    ).strip()

    if existing_text:
        question["text"] = f"{existing_text} {continuation}"
    else:
        question["text"] = continuation


def _prefix_pending_questions_with_main_number(
    *,
    questions: list[dict[str, Any]],
    pending_question_indexes: list[int],
    main_question_number: str,
) -> None:
    """
    Resolve sub-questions encountered before their main question number.

    Some PDFs extract visually positioned numbers out of reading order. In the
    real Bethany paper, Q2(a) and its mark allocation are extracted before the
    standalone ``2.`` main-question label. We retain the earlier candidate and
    retroactively resolve ``(a)`` to ``2(a)`` when the main number appears.
    """

    for question_index in pending_question_indexes:
        question = questions[question_index]

        current_number = str(
            question.get(
                "question_number",
                "",
            )
        )

        if not current_number.startswith(
            "(",
        ):
            continue

        resolved_number = f"{main_question_number}{current_number}"

        question["question_number"] = resolved_number
        question["depth"] = _infer_question_depth(
            resolved_number,
        )


def _build_initial_proposal(
    *,
    pages: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Build the first review proposal across the whole question paper.

    The parser is deliberately review-first rather than import-first. It:

    - resolves standalone mark lines such as ``(2)``
    - ignores ``(Total N marks)`` as a question
    - carries a main question number across page boundaries
    - resolves sub-questions such as ``(a)`` into ``1(a)``
    - handles a main number appearing after its first sub-question because of
      PDF visual-reading-order extraction
    - retains page and line evidence for every proposed question
    - never creates AssessmentQuestion records automatically
    """

    questions: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    declared_totals: list[dict[str, Any]] = []

    active_main_question: str | None = None

    current_question_index: int | None = None

    pending_unparented_question_indexes: list[int] = []

    for page in pages:
        page_number = int(page["page_number"])

        text = str(
            page.get(
                "text",
                "",
            )
            or ""
        )

        for line_number, line in enumerate(
            text.splitlines(),
            start=1,
        ):
            stripped = line.strip()

            if not stripped:
                continue

            if _is_page_footer(
                stripped,
            ):
                current_question_index = None
                continue

            declared_total = _extract_declared_total(
                stripped,
            )

            if declared_total is not None:
                declared_totals.append(
                    {
                        "marks": declared_total,
                        "page_number": page_number,
                        "line_number": line_number,
                        "source_line": stripped,
                    }
                )

                # A declared total conventionally closes the current main
                # question. The following unnumbered/part-labelled material
                # therefore belongs to the next main question.
                active_main_question = None
                current_question_index = None
                continue

            standalone_mark = _extract_standalone_mark(
                stripped,
            )

            if standalone_mark is not None:
                if current_question_index is None:
                    warnings.append(
                        {
                            "code": "orphan_standalone_mark",
                            "message": (
                                "A standalone mark allocation could not be "
                                "linked confidently to a detected question."
                            ),
                            "page_numbers": [
                                page_number,
                            ],
                        }
                    )
                    continue

                current_question = questions[current_question_index]

                if (
                    current_question.get(
                        "marks",
                    )
                    is None
                ):
                    current_question["marks"] = standalone_mark
                elif (
                    current_question.get(
                        "marks",
                    )
                    != standalone_mark
                ):
                    warnings.append(
                        {
                            "code": "conflicting_mark_allocation",
                            "message": (
                                "A question contained conflicting detected "
                                "mark allocations and requires review."
                            ),
                            "page_numbers": [
                                page_number,
                            ],
                        }
                    )

                # A standalone mark line terminates that question's extracted
                # response block. Subsequent prose belongs to later context.
                current_question_index = None
                continue

            detected = _detect_question_line(
                stripped,
            )

            if detected is not None:
                raw_question_number = str(detected["question_number"])

                question_text = str(
                    detected.get(
                        "text",
                        "",
                    )
                    or ""
                )

                marks = detected.get(
                    "marks",
                )

                if _is_main_question_number(
                    raw_question_number,
                ):
                    active_main_question = raw_question_number

                    if pending_unparented_question_indexes:
                        _prefix_pending_questions_with_main_number(
                            questions=questions,
                            pending_question_indexes=(
                                pending_unparented_question_indexes
                            ),
                            main_question_number=active_main_question,
                        )

                        pending_unparented_question_indexes = []

                    # A bare ``1.`` or ``2.`` acts as structural context only.
                    # It is not a markable proposal question by itself.
                    if not question_text and marks is None:
                        current_question_index = None
                        continue

                    question = _new_proposal_question(
                        question_number=raw_question_number,
                        text=question_text,
                        marks=marks,
                        page_number=page_number,
                        line_number=line_number,
                        source_line=stripped,
                    )

                    questions.append(
                        question,
                    )

                    current_question_index = (
                        len(
                            questions,
                        )
                        - 1
                    )

                    continue

                main_number = _main_number_from_question_number(
                    raw_question_number,
                )

                if main_number is not None:
                    active_main_question = main_number
                    resolved_question_number = raw_question_number
                elif raw_question_number.startswith(
                    "(",
                ):
                    if active_main_question is not None:
                        resolved_question_number = (
                            f"{active_main_question}" f"{raw_question_number}"
                        )
                    else:
                        resolved_question_number = raw_question_number
                else:
                    resolved_question_number = raw_question_number

                question = _new_proposal_question(
                    question_number=resolved_question_number,
                    text=question_text,
                    marks=marks,
                    page_number=page_number,
                    line_number=line_number,
                    source_line=stripped,
                )

                questions.append(
                    question,
                )

                current_question_index = (
                    len(
                        questions,
                    )
                    - 1
                )

                if (
                    active_main_question is None
                    and resolved_question_number.startswith(
                        "(",
                    )
                ):
                    pending_unparented_question_indexes.append(
                        current_question_index,
                    )

                continue

            if current_question_index is not None:
                _append_question_text(
                    questions[current_question_index],
                    stripped,
                )

    if pending_unparented_question_indexes:
        page_numbers = sorted(
            {
                int(questions[index]["source"]["page_number"])
                for index in pending_unparented_question_indexes
            }
        )

        warnings.append(
            {
                "code": "unresolved_question_parent",
                "message": (
                    "One or more sub-questions could not be linked "
                    "confidently to a main question number."
                ),
                "page_numbers": page_numbers,
            }
        )

    detected_marks = [
        question["marks"]
        for question in questions
        if isinstance(
            question.get(
                "marks",
            ),
            int,
        )
    ]

    detected_mark_sum = sum(
        detected_marks,
    )

    declared_total_mark_sum = sum(total["marks"] for total in declared_totals)

    if (
        declared_totals
        and detected_marks
        and declared_total_mark_sum != detected_mark_sum
    ):
        warnings.append(
            {
                "code": "declared_total_mismatch",
                "message": (
                    "The sum of detected question marks does not match "
                    "the total marks declared in the source paper."
                ),
                "page_numbers": sorted(
                    {int(total["page_number"]) for total in declared_totals}
                ),
            }
        )

    return {
        "parser_version": PARSER_VERSION,
        "review_required": True,
        "auto_import_allowed": False,
        "questions": questions,
        "summary": {
            "detected_question_count": len(
                questions,
            ),
            "questions_with_detected_marks": len(
                detected_marks,
            ),
            "detected_mark_sum": detected_mark_sum,
        },
        "declared_totals": declared_totals,
        "warnings": warnings,
    }


def _read_pdf(
    document_path: Path,
) -> tuple[
    dict[str, Any],
    list[dict[str, Any]],
    dict[str, Any],
]:
    """
    Read a digital PDF and return metadata, page evidence and proposal data.

    OCR is deliberately not attempted here. Pages with no extractable text are
    recorded so a future OCR fallback can identify them explicitly.
    """

    try:
        reader = PdfReader(
            str(
                document_path,
            ),
        )
    except (
        PdfReadError,
        OSError,
        ValueError,
    ) as exc:
        raise ValueError(
            "The question paper could not be opened as a readable PDF.",
        ) from exc

    if reader.is_encrypted:
        try:
            decrypt_result = reader.decrypt(
                "",
            )
        except Exception as exc:
            raise ValueError(
                "Encrypted question papers are not currently supported.",
            ) from exc

        if not decrypt_result:
            raise ValueError(
                "Encrypted question papers are not currently supported.",
            )

    source_metadata = {
        "extractor": "pypdf",
        "extractor_version": pypdf_version,
        "pdf_metadata": _serialise_pdf_metadata(
            reader,
        ),
    }

    pages: list[dict[str, Any]] = []

    for page_index, page in enumerate(
        reader.pages,
        start=1,
    ):
        extraction_error: str | None = None

        try:
            raw_text = page.extract_text()
        except Exception as exc:
            raw_text = ""
            extraction_error = (f"{type(exc).__name__}: {exc}")[:1000]

        text = _normalise_page_text(
            raw_text,
        )

        # Retain page-local detection as immutable extraction evidence.
        # Parent resolution and standalone mark allocation are applied only
        # to proposal_data so page_data continues to reflect what pypdf saw.
        question_candidates = _extract_question_candidates_from_page(
            page_number=page_index,
            text=text,
        )

        page_record: dict[str, Any] = {
            "page_number": page_index,
            "has_extractable_text": bool(
                text.strip(),
            ),
            "text_length": len(
                text,
            ),
            "text": text,
            "question_candidates": question_candidates,
        }

        if extraction_error is not None:
            page_record["extraction_error"] = extraction_error

        pages.append(
            page_record,
        )

    proposal = _build_initial_proposal(
        pages=pages,
    )

    text_page_count = sum(1 for page in pages if page["has_extractable_text"])

    pages_without_text = [
        page["page_number"] for page in pages if not page["has_extractable_text"]
    ]

    if pages_without_text:
        proposal["warnings"].append(
            {
                "code": "pages_without_extractable_text",
                "message": (
                    "Some pages contain no extractable digital text and may "
                    "require OCR or visual review."
                ),
                "page_numbers": pages_without_text,
            }
        )

    source_metadata["page_count"] = len(
        pages,
    )

    source_metadata["text_page_count"] = text_page_count

    return (
        source_metadata,
        pages,
        proposal,
    )


async def _load_question_paper_document(
    *,
    db: AsyncSession,
    current_user: User,
    assessment_id: int,
    document_id: int,
) -> AssessmentDocument:
    """
    Load an assessment-scoped document and verify it is a question paper.
    """

    document = await get_assessment_document(
        db=db,
        current_user=current_user,
        assessment_id=assessment_id,
        document_id=document_id,
    )

    if document.document_type != QUESTION_PAPER_DOCUMENT_TYPE:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Only assessment question-paper documents can be "
                "processed for question extraction."
            ),
        )

    return document


async def create_question_extraction(
    *,
    db: AsyncSession,
    current_user: User,
    assessment_id: int,
    document_id: int,
) -> AssessmentQuestionExtraction:
    """
    Extract question-paper text into a reviewable proposal.

    The extraction is persisted as a versioned attempt. No
    AssessmentSection or AssessmentQuestion records are created here.
    """

    document = await _load_question_paper_document(
        db=db,
        current_user=current_user,
        assessment_id=assessment_id,
        document_id=document_id,
    )

    document, document_path = await resolve_assessment_document_path(
        db=db,
        current_user=current_user,
        assessment_id=assessment_id,
        document_id=document_id,
    )

    # Preserve scalar identifiers before any rollback can expire ORM objects.
    source_document_id = document.id
    requested_by_id = current_user.id

    extraction_repository = AssessmentQuestionExtractionRepository(
        db,
    )

    document_repository = AssessmentDocumentRepository(
        db,
    )

    next_version = await extraction_repository.get_next_version(
        assessment_document_id=source_document_id,
    )

    extraction = AssessmentQuestionExtraction(
        assessment_id=assessment_id,
        assessment_document_id=source_document_id,
        requested_by_id=requested_by_id,
        imported_by_id=None,
        version=next_version,
        status=AssessmentQuestionExtractionStatus.PROCESSING.value,
        extractor_name="pypdf",
        extractor_version=pypdf_version,
        parser_version=PARSER_VERSION,
        page_count=None,
        text_page_count=None,
        detected_question_count=None,
        detected_markable_question_count=None,
        detected_total_marks=None,
        source_metadata=None,
        page_data=None,
        proposal_data=None,
        error_message=None,
        started_at=_utc_now(),
        completed_at=None,
        imported_at=None,
    )

    try:
        document.extraction_requested = True
        document.extraction_completed = False
        document.extraction_error = None

        await document_repository.save(
            document,
        )

        extraction = await extraction_repository.create(
            extraction,
        )

        source_metadata, page_data, proposal_data = _read_pdf(
            document_path,
        )

        questions = proposal_data.get(
            "questions",
            [],
        )

        marked_questions = [
            question
            for question in questions
            if isinstance(
                question.get(
                    "marks",
                ),
                int,
            )
        ]

        extraction.status = AssessmentQuestionExtractionStatus.COMPLETED.value

        extraction.page_count = len(
            page_data,
        )

        extraction.text_page_count = sum(
            1
            for page in page_data
            if page.get(
                "has_extractable_text",
            )
        )

        extraction.detected_question_count = len(
            questions,
        )

        extraction.detected_markable_question_count = len(
            marked_questions,
        )

        extraction.detected_total_marks = sum(
            question["marks"] for question in marked_questions
        )

        extraction.source_metadata = source_metadata
        extraction.page_data = page_data
        extraction.proposal_data = proposal_data
        extraction.error_message = None
        extraction.completed_at = _utc_now()

        extraction = await extraction_repository.save(
            extraction,
        )

        await extraction_repository.mark_previous_completed_as_superseded(
            assessment_document_id=source_document_id,
            except_extraction_id=extraction.id,
        )

        document.extraction_completed = True
        document.extraction_error = None

        await document_repository.save(
            document,
        )

        await db.commit()

        await db.refresh(
            extraction,
        )

        return extraction

    except HTTPException:
        await db.rollback()
        raise

    except Exception as exc:
        await db.rollback()

        failure_message = str(
            exc,
        ).strip()

        if not failure_message:
            failure_message = "Question-paper extraction failed."

        failure_message = failure_message[:4000]

        try:
            failure_repository = AssessmentQuestionExtractionRepository(
                db,
            )

            failure_document_repository = AssessmentDocumentRepository(
                db,
            )

            # The original PROCESSING row belonged to the transaction that
            # was rolled back, so it will normally no longer exist. Querying
            # first also keeps this recovery path safe if future transaction
            # boundaries change.
            failed_extraction = await failure_repository.get_by_document_and_version(
                assessment_document_id=source_document_id,
                version=next_version,
                include_relationships=False,
            )

            if failed_extraction is None:
                failed_extraction = AssessmentQuestionExtraction(
                    assessment_id=assessment_id,
                    assessment_document_id=source_document_id,
                    requested_by_id=requested_by_id,
                    imported_by_id=None,
                    version=next_version,
                    status=(AssessmentQuestionExtractionStatus.FAILED.value),
                    extractor_name="pypdf",
                    extractor_version=pypdf_version,
                    parser_version=PARSER_VERSION,
                    page_count=None,
                    text_page_count=None,
                    detected_question_count=None,
                    detected_markable_question_count=None,
                    detected_total_marks=None,
                    source_metadata=None,
                    page_data=None,
                    proposal_data=None,
                    error_message=failure_message,
                    started_at=_utc_now(),
                    completed_at=_utc_now(),
                    imported_at=None,
                )

                failed_extraction = await failure_repository.create(
                    failed_extraction,
                )
            else:
                failed_extraction.status = (
                    AssessmentQuestionExtractionStatus.FAILED.value
                )
                failed_extraction.error_message = failure_message
                failed_extraction.completed_at = _utc_now()

                failed_extraction = await failure_repository.save(
                    failed_extraction,
                )

            # Access was already authorised before extraction began. After
            # rollback, reload the document asynchronously by its preserved
            # primary key rather than touching the expired ORM instance or
            # expired current_user object.
            failed_document = await db.get(
                AssessmentDocument,
                source_document_id,
            )

            if failed_document is None:
                raise RuntimeError(
                    "Question-paper document disappeared during "
                    "extraction failure recovery."
                )

            if failed_document.assessment_id != assessment_id:
                raise RuntimeError(
                    "Question-paper document assessment changed during "
                    "extraction failure recovery."
                )

            failed_document.extraction_requested = True
            failed_document.extraction_completed = False
            failed_document.extraction_error = failure_message

            await failure_document_repository.save(
                failed_document,
            )

            await db.commit()

        except Exception:
            await db.rollback()

        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=failure_message,
        ) from exc


async def get_question_extraction(
    *,
    db: AsyncSession,
    current_user: User,
    assessment_id: int,
    extraction_id: int,
) -> AssessmentQuestionExtraction:
    """
    Return one assessment-scoped extraction proposal.
    """

    await _load_question_paper_document_for_extraction_access(
        db=db,
        current_user=current_user,
        assessment_id=assessment_id,
        extraction_id=extraction_id,
    )

    repository = AssessmentQuestionExtractionRepository(
        db,
    )

    extraction = await repository.get_by_id_and_assessment(
        extraction_id=extraction_id,
        assessment_id=assessment_id,
        include_relationships=False,
    )

    if extraction is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assessment question extraction not found.",
        )

    return extraction


async def _load_question_paper_document_for_extraction_access(
    *,
    db: AsyncSession,
    current_user: User,
    assessment_id: int,
    extraction_id: int,
) -> AssessmentQuestionExtraction:
    """
    Ensure extraction access passes through the assessment document policy.
    """

    repository = AssessmentQuestionExtractionRepository(
        db,
    )

    extraction = await repository.get_by_id_and_assessment(
        extraction_id=extraction_id,
        assessment_id=assessment_id,
        include_relationships=False,
    )

    if extraction is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assessment question extraction not found.",
        )

    await _load_question_paper_document(
        db=db,
        current_user=current_user,
        assessment_id=assessment_id,
        document_id=extraction.assessment_document_id,
    )

    return extraction


async def list_question_extractions_for_document(
    *,
    db: AsyncSession,
    current_user: User,
    assessment_id: int,
    document_id: int,
) -> list[AssessmentQuestionExtraction]:
    """
    Return the extraction history for one question-paper document.
    """

    document = await _load_question_paper_document(
        db=db,
        current_user=current_user,
        assessment_id=assessment_id,
        document_id=document_id,
    )

    repository = AssessmentQuestionExtractionRepository(
        db,
    )

    return await repository.list_for_document(
        assessment_document_id=document.id,
        include_relationships=False,
    )
