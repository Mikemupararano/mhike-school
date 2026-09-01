from __future__ import annotations

import re
import shutil
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any

from fastapi import HTTPException, status
import pymupdf
from pypdf import PdfReader, __version__ as pypdf_version
from pypdf.errors import PdfReadError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.assessment_document import AssessmentDocument
from app.models.assessment_question import (
    AssessmentQuestion,
    AssessmentQuestionAsset,
    AssessmentQuestionAssetType,
    AssessmentQuestionOption,
    AssessmentQuestionType,
)
from app.models.assessment_question_extraction import (
    AssessmentQuestionExtraction,
    AssessmentQuestionExtractionStatus,
)
from app.models.user import User
from app.repositories.assessment_document import AssessmentDocumentRepository
from app.repositories.assessment_question import AssessmentQuestionRepository
from app.repositories.assessment_question_extraction import (
    AssessmentQuestionExtractionRepository,
)
from app.schemas.assessment import AssessmentQuestionInteractionConfig
from app.schemas.assessment_question_extraction import (
    AssessmentQuestionExtractionImportedQuestionResponse,
    AssessmentQuestionExtractionReviewStatus,
    AssessmentQuestionExtractionReviewUpdate,
)
from app.services.assessment_document_service import (
    QUESTION_PAPER_DOCUMENT_TYPE,
    get_assessment_document,
    resolve_assessment_document_path,
)
from app.services.assessment_interaction_palette_service import (
    infer_interaction_config,
    interaction_config_as_dict,
)
from app.services.assessment_question_service import (
    _get_manageable_draft_assessment,
)

PARSER_VERSION = "8"

MAX_EXTRACTED_PAGE_TEXT_LENGTH = 100_000


MCQ_SINGLE_INSTRUCTION_PATTERN = re.compile(
    r"""
    (?P<instruction>
        \b
        (?:tick|select|choose|mark|circle)
        \b
        .{0,100}?
        \b(?:one|1)\b
        (?:\s+(?:box|answer|option|response))?
        [\.\:\;]?
    )
    \s*$
    """,
    re.IGNORECASE | re.VERBOSE,
)


MCQ_MULTIPLE_INSTRUCTION_PATTERN = re.compile(
    r"""
    (?P<instruction>
        \b
        (?:
            select\s+all
            |
            choose\s+all
            |
            tick\s+all
            |
            tick\s+(?:two|three|four|2|3|4)
            |
            select\s+(?:two|three|four|2|3|4)
            |
            choose\s+(?:two|three|four|2|3|4)
        )
        \b
        .{0,100}?
        (?:
            boxes?
            |
            answers?
            |
            options?
            |
            responses?
            |
            that\s+apply
        )?
        [\.\:\;]?
    )
    \s*$
    """,
    re.IGNORECASE | re.VERBOSE,
)


VISUAL_REFERENCE_PATTERN = re.compile(
    r"""
    \b
    (?:
        figure
        |
        diagram
        |
        graph
        |
        chart
        |
        image
        |
        illustration
        |
        drawing
        |
        model
    )
    \b
    """,
    re.IGNORECASE | re.VERBOSE,
)


VISUAL_ABOVE_PATTERN = re.compile(
    r"\b(?:above|shown\s+above|figure\s+above|diagram\s+above)\b",
    re.IGNORECASE,
)


VISUAL_BELOW_PATTERN = re.compile(
    r"\b(?:below|shown\s+below|figure\s+below|diagram\s+below)\b",
    re.IGNORECASE,
)


DIAGRAM_ANNOTATION_INSTRUCTION_PATTERN = re.compile(
    r"""
    \b
    (?:
        complete
        |
        annotate
        |
        label
        |
        mark
        |
        add
        |
        place
        |
        plot
        |
        draw
    )
    \b
    .{0,120}?
    \b
    (?:
        figure
        |
        diagram
        |
        graph
        |
        chart
        |
        image
        |
        drawing
        |
        model
    )
    \b
    """,
    re.IGNORECASE | re.VERBOSE,
)


VISUAL_RENDER_SCALE = 2.0
VISUAL_REGION_MARGIN = 18.0
VISUAL_EMBEDDED_IMAGE_MARGIN = 2.0
VISUAL_EMBEDDED_IMAGE_COVERAGE_THRESHOLD = 0.50
VISUAL_COMPONENT_MERGE_GAP = 36.0
VISUAL_SAME_BAND_GAP = 120.0


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


def _split_mcq_instruction(
    text: str,
) -> tuple[
    str,
    AssessmentQuestionType | None,
    str | None,
]:
    """
    Split a trailing multiple-choice instruction from question stem text.

    Detection is deliberately conservative. Only explicit authoring phrases
    such as ``Tick one box`` or ``Select all that apply`` cause automatic
    classification. The parser never infers a correct answer.
    """

    stripped = text.strip()

    if not stripped:
        return (
            "",
            None,
            None,
        )

    multiple_match = MCQ_MULTIPLE_INSTRUCTION_PATTERN.search(
        stripped,
    )

    if multiple_match is not None:
        stem = stripped[: multiple_match.start()].strip()
        instruction = stripped[multiple_match.start() : multiple_match.end()].strip()

        return (
            stem,
            AssessmentQuestionType.MULTIPLE_CHOICE_MULTIPLE,
            instruction,
        )

    single_match = MCQ_SINGLE_INSTRUCTION_PATTERN.search(
        stripped,
    )

    if single_match is not None:
        stem = stripped[: single_match.start()].strip()
        instruction = stripped[single_match.start() : single_match.end()].strip()

        return (
            stem,
            AssessmentQuestionType.MULTIPLE_CHOICE_SINGLE,
            instruction,
        )

    return (
        stripped,
        None,
        None,
    )


def _is_plausible_mcq_option_line(
    line: str,
) -> bool:
    """
    Return whether a continuation line is plausible as one answer option.

    This helper is used only after an explicit MCQ instruction has already been
    detected. That prerequisite is what keeps ordinary continuation prose from
    being reclassified as answer choices.
    """

    candidate = line.strip()

    if not candidate:
        return False

    if len(candidate) > 500:
        return False

    if _is_page_footer(
        candidate,
    ):
        return False

    if _is_answer_line(
        candidate,
    ):
        return False

    if (
        _extract_declared_total(
            candidate,
        )
        is not None
    ):
        return False

    if (
        _extract_standalone_mark(
            candidate,
        )
        is not None
    ):
        return False

    if (
        _detect_question_line(
            candidate,
        )
        is not None
    ):
        return False

    return True


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

    Explicit multiple-choice instructions are separated from the stem at this
    stage so following continuation lines can become structured options rather
    than being flattened into question text.
    """

    (
        stem_text,
        detected_question_type,
        mcq_instruction,
    ) = _split_mcq_instruction(
        text,
    )

    question = {
        "question_number": question_number,
        "text": stem_text,
        "marks": marks,
        "depth": _infer_question_depth(
            question_number,
        ),
        "question_type": (
            detected_question_type.value
            if detected_question_type is not None
            else AssessmentQuestionType.WRITTEN.value
        ),
        "options": [],
        "assets": [],
        "source": {
            "page_number": page_number,
            "line_number": line_number,
            "source_line": source_line,
        },
        "confidence": "candidate",
        "requires_review": True,
    }

    if detected_question_type is not None:
        question["_mcq_collecting_options"] = True
        question["_mcq_instruction"] = mcq_instruction

    return question


def _append_question_text(
    question: dict[str, Any],
    line: str,
) -> None:
    """
    Append useful continuation content to a detected question.

    Once an explicit multiple-choice instruction is encountered, later
    continuation lines are captured as structured answer options. Correctness
    is always left false for teacher review; the parser never guesses answers.
    """

    continuation = _clean_continuation_line(
        line,
    )

    if continuation is None:
        return

    if bool(
        question.get(
            "_mcq_collecting_options",
            False,
        )
    ):
        if _is_plausible_mcq_option_line(
            continuation,
        ):
            options = question.setdefault(
                "options",
                [],
            )

            options.append(
                {
                    "text": continuation,
                    "order": len(options) + 1,
                    "is_correct": False,
                    "feedback": None,
                }
            )

            return

        question["_mcq_collecting_options"] = False

    (
        continuation_stem,
        detected_question_type,
        mcq_instruction,
    ) = _split_mcq_instruction(
        continuation,
    )

    existing_text = str(
        question.get(
            "text",
            "",
        )
        or ""
    ).strip()

    if detected_question_type is not None:
        if continuation_stem:
            if existing_text:
                question["text"] = f"{existing_text} {continuation_stem}"
            else:
                question["text"] = continuation_stem

        question["question_type"] = detected_question_type.value
        question["_mcq_collecting_options"] = True
        question["_mcq_instruction"] = mcq_instruction
        question["options"] = []
        return

    if existing_text:
        question["text"] = f"{existing_text} {continuation}"
    else:
        question["text"] = continuation


def _restore_unstructured_mcq_candidate(
    question: dict[str, Any],
    *,
    instruction: str | None,
    options: list[dict[str, Any]],
) -> None:
    """
    Restore uncertain MCQ material to ordinary written question text.
    """

    fallback_parts: list[str] = []

    existing_text = str(
        question.get(
            "text",
            "",
        )
        or ""
    ).strip()

    if existing_text:
        fallback_parts.append(
            existing_text,
        )

    if (
        isinstance(
            instruction,
            str,
        )
        and instruction.strip()
    ):
        fallback_parts.append(
            instruction.strip(),
        )

    for option in options:
        if not isinstance(
            option,
            dict,
        ):
            continue

        option_text = option.get(
            "text",
        )

        if (
            isinstance(
                option_text,
                str,
            )
            and option_text.strip()
        ):
            fallback_parts.append(
                option_text.strip(),
            )

    question["text"] = " ".join(
        fallback_parts,
    )
    question["question_type"] = AssessmentQuestionType.WRITTEN.value
    question["options"] = []


def _finalise_structured_question_candidate(
    question: dict[str, Any],
) -> None:
    """
    Finalise temporary parser-only MCQ state before proposal persistence.

    An MCQ classification is retained only when at least two answer options
    were captured. Otherwise all captured material is restored to ordinary
    written question text so uncertain extraction never destroys source text.
    """

    question.pop(
        "_mcq_collecting_options",
        None,
    )

    instruction = question.pop(
        "_mcq_instruction",
        None,
    )

    question_type_value = question.get(
        "question_type",
        AssessmentQuestionType.WRITTEN.value,
    )

    is_mcq = question_type_value in {
        AssessmentQuestionType.MULTIPLE_CHOICE_SINGLE.value,
        AssessmentQuestionType.MULTIPLE_CHOICE_MULTIPLE.value,
    }

    if not is_mcq:
        return

    raw_options = question.get(
        "options",
        [],
    )

    if not isinstance(
        raw_options,
        list,
    ):
        raw_options = []

    normalised_options: list[dict[str, Any]] = []

    for option in raw_options:
        if not isinstance(
            option,
            dict,
        ):
            continue

        option_text = option.get(
            "text",
        )

        if (
            not isinstance(
                option_text,
                str,
            )
            or not option_text.strip()
        ):
            continue

        normalised_options.append(
            {
                "text": option_text.strip(),
                "order": len(normalised_options) + 1,
                "is_correct": False,
                "feedback": None,
            }
        )

    if len(normalised_options) < 2:
        _restore_unstructured_mcq_candidate(
            question,
            instruction=instruction,
            options=normalised_options,
        )
        return

    question["options"] = normalised_options
    question["requires_review"] = True


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

    for question in questions:
        _finalise_structured_question_candidate(
            question,
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


def _normalise_visual_match_text(
    value: str,
) -> str:
    """
    Return a compact lower-case representation for locating source text blocks.
    """

    return (
        re.sub(
            r"\s+",
            " ",
            value,
        )
        .strip()
        .lower()
    )


def _question_visual_direction(
    question_text: str,
) -> str:
    """
    Return the preferred visual direction for a question reference.
    """

    if VISUAL_ABOVE_PATTERN.search(
        question_text,
    ):
        return "above"

    if VISUAL_BELOW_PATTERN.search(
        question_text,
    ):
        return "below"

    return "nearest"


def _infer_visual_asset_type(
    question_text: str,
) -> AssessmentQuestionAssetType:
    """
    Infer a conservative canonical asset type from the question wording.
    """

    lowered = question_text.lower()

    if "graph" in lowered or "chart" in lowered:
        return AssessmentQuestionAssetType.GRAPH

    if "diagram" in lowered or "drawing" in lowered:
        return AssessmentQuestionAssetType.DIAGRAM

    if "image" in lowered or "illustration" in lowered:
        return AssessmentQuestionAssetType.IMAGE

    return AssessmentQuestionAssetType.FIGURE


def _is_diagram_annotation_instruction(
    question_text: str,
) -> bool:
    """
    Return whether the wording explicitly requires the learner to modify a visual.

    Classification is intentionally conservative. A mere reference such as
    ``Use the figure above`` remains a written response. Only an action directed
    at a figure/diagram/graph/image/model is eligible for automatic
    ``diagram_annotation`` classification, and the caller additionally requires
    that a real visual asset was successfully materialised.
    """

    return bool(
        DIAGRAM_ANNOTATION_INSTRUCTION_PATTERN.search(
            question_text,
        )
    )


def _rect_distance(
    left: pymupdf.Rect,
    right: pymupdf.Rect,
) -> float:
    """
    Return the shortest axis-aligned gap between two rectangles.
    """

    horizontal_gap = max(
        0.0,
        max(
            left.x0,
            right.x0,
        )
        - min(
            left.x1,
            right.x1,
        ),
    )

    vertical_gap = max(
        0.0,
        max(
            left.y0,
            right.y0,
        )
        - min(
            left.y1,
            right.y1,
        ),
    )

    return max(
        horizontal_gap,
        vertical_gap,
    )


def _merge_visual_rectangles(
    rects: list[pymupdf.Rect],
    *,
    gap: float,
) -> list[pymupdf.Rect]:
    """
    Merge nearby visual primitives into candidate figure regions.
    """

    pending = [
        pymupdf.Rect(
            rect,
        )
        for rect in rects
    ]

    merged: list[pymupdf.Rect] = []

    while pending:
        current = pending.pop(
            0,
        )

        changed = True

        while changed:
            changed = False
            remaining: list[pymupdf.Rect] = []

            for candidate in pending:
                if (
                    _rect_distance(
                        current,
                        candidate,
                    )
                    <= gap
                ):
                    current |= candidate
                    changed = True
                else:
                    remaining.append(
                        candidate,
                    )

            pending = remaining

        merged.append(
            current,
        )

    return merged


def _extract_page_visual_regions(
    page: pymupdf.Page,
) -> list[pymupdf.Rect]:
    """
    Detect raster and vector visual regions on one PDF page.

    The result intentionally excludes page-sized backgrounds, tiny glyph-like
    shapes and long answer-space rules. Nearby vector primitives are merged so
    an atom model, graph or multi-part diagram becomes one crop candidate.
    """

    page_rect = page.rect
    page_area = max(
        page_rect.width * page_rect.height,
        1.0,
    )

    raw_rects: list[pymupdf.Rect] = []

    # PyMuPDF's ``get_text("blocks")`` does not reliably surface image blocks
    # for every PDF producer. The Atomic Structure paper is one concrete
    # example: its atom-model and atom-shell figures are genuine embedded
    # images, but they are absent from the text-block stream. Therefore inspect
    # image XRefs directly and ask the page for every placed rectangle.
    try:
        page_images = page.get_images(
            full=True,
        )
    except Exception:
        page_images = []

    seen_image_rects: set[
        tuple[
            float,
            float,
            float,
            float,
        ]
    ] = set()

    for image_info in page_images:
        if not image_info:
            continue

        xref = image_info[0]

        try:
            image_rects = page.get_image_rects(
                xref,
            )
        except Exception:
            image_rects = []

        for image_rect in image_rects:
            rect = pymupdf.Rect(
                image_rect,
            )

            if rect.is_empty:
                continue

            key = (
                round(
                    rect.x0,
                    3,
                ),
                round(
                    rect.y0,
                    3,
                ),
                round(
                    rect.x1,
                    3,
                ),
                round(
                    rect.y1,
                    3,
                ),
            )

            if key in seen_image_rects:
                continue

            seen_image_rects.add(
                key,
            )

            # Keep even small embedded images at this stage. Small symbols can
            # be semantically essential and will be merged with a nearby
            # principal figure before the final size filter is applied.
            raw_rects.append(
                rect,
            )

    # Retain the block-based path as a secondary source for PDFs that do expose
    # raster images through the text-block stream.
    try:
        blocks = page.get_text(
            "blocks",
        )
    except Exception:
        blocks = []

    for block in blocks:
        if len(block) < 7:
            continue

        block_type = block[6]

        if block_type != 1:
            continue

        rect = pymupdf.Rect(
            block[:4],
        )

        if rect.is_empty:
            continue

        raw_rects.append(
            rect,
        )

    try:
        drawings = page.get_drawings()
    except Exception:
        drawings = []

    for drawing in drawings:
        drawing_rect = drawing.get(
            "rect",
        )

        if drawing_rect is None:
            continue

        rect = pymupdf.Rect(
            drawing_rect,
        )

        if rect.is_empty:
            continue

        area = rect.width * rect.height

        if area >= page_area * 0.70:
            continue

        # Ignore long single answer rules and near-zero drawing artefacts.
        if rect.height < 3.0 and rect.width > 120.0:
            continue

        if rect.width < 2.0 and rect.height < 2.0:
            continue

        raw_rects.append(
            rect,
        )

    if not raw_rects:
        return []

    merged = _merge_visual_rectangles(
        raw_rects,
        gap=VISUAL_COMPONENT_MERGE_GAP,
    )

    filtered: list[pymupdf.Rect] = []

    for rect in merged:
        area = rect.width * rect.height

        if area < 250.0:
            continue

        if rect.width < 16.0 or rect.height < 10.0:
            continue

        if area >= page_area * 0.70:
            continue

        filtered.append(
            rect,
        )

    return filtered


def _page_text_blocks(
    page: pymupdf.Page,
) -> list[tuple[pymupdf.Rect, str]]:
    """
    Return text block rectangles and text for source-line anchoring.
    """

    result: list[tuple[pymupdf.Rect, str]] = []

    try:
        blocks = page.get_text(
            "blocks",
        )
    except Exception:
        return result

    for block in blocks:
        if len(block) < 7:
            continue

        block_type = block[6]

        if block_type != 0:
            continue

        text = str(
            block[4],
        ).strip()

        if not text:
            continue

        result.append(
            (
                pymupdf.Rect(
                    block[:4],
                ),
                text,
            )
        )

    return result


def _find_question_anchor_rect(
    *,
    page: pymupdf.Page,
    question: dict[str, Any],
) -> pymupdf.Rect | None:
    """
    Locate the question's source text block on the rendered PDF page.
    """

    source = question.get(
        "source",
        {},
    )

    source_line = source.get(
        "source_line",
    )

    question_text = question.get(
        "text",
        "",
    )

    needles: list[str] = []

    for raw_value in (
        source_line,
        question_text,
    ):
        if not isinstance(
            raw_value,
            str,
        ):
            continue

        normalised = _normalise_visual_match_text(
            raw_value,
        )

        if normalised:
            needles.append(
                normalised,
            )

    if not needles:
        return None

    candidates: list[
        tuple[
            int,
            pymupdf.Rect,
        ]
    ] = []

    for rect, block_text in _page_text_blocks(
        page,
    ):
        normalised_block = _normalise_visual_match_text(
            block_text,
        )

        score = 0

        for needle in needles:
            if needle in normalised_block:
                score = max(
                    score,
                    len(
                        needle,
                    ),
                )
                continue

            shortened = needle[:80]

            if len(shortened) >= 20 and shortened in normalised_block:
                score = max(
                    score,
                    len(
                        shortened,
                    ),
                )

        if score > 0:
            candidates.append(
                (
                    score,
                    rect,
                )
            )

    if not candidates:
        return None

    candidates.sort(
        key=lambda item: (
            -item[0],
            item[1].y0,
        ),
    )

    return candidates[0][1]


def _choose_visual_region_for_question(
    *,
    page: pymupdf.Page,
    question: dict[str, Any],
    visual_regions: list[pymupdf.Rect],
) -> pymupdf.Rect | None:
    """
    Choose the most plausible visual region referenced by one question.
    """

    question_text = str(
        question.get(
            "text",
            "",
        )
        or ""
    )

    source = question.get(
        "source",
        {},
    )

    source_line = source.get(
        "source_line",
        "",
    )

    combined_text = " ".join(
        part
        for part in (
            question_text,
            source_line if isinstance(source_line, str) else "",
        )
        if part
    )

    if (
        VISUAL_REFERENCE_PATTERN.search(
            combined_text,
        )
        is None
    ):
        return None

    anchor = _find_question_anchor_rect(
        page=page,
        question=question,
    )

    if anchor is None:
        return None

    direction = _question_visual_direction(
        combined_text,
    )

    ranked: list[
        tuple[
            float,
            pymupdf.Rect,
        ]
    ] = []

    for rect in visual_regions:
        horizontal_overlap = max(
            0.0,
            min(
                anchor.x1,
                rect.x1,
            )
            - max(
                anchor.x0,
                rect.x0,
            ),
        )

        horizontal_bonus = horizontal_overlap / max(
            min(
                anchor.width,
                rect.width,
            ),
            1.0,
        )

        if direction == "above":
            if rect.y1 > anchor.y0 + 12.0:
                continue

            distance = max(
                0.0,
                anchor.y0 - rect.y1,
            )

        elif direction == "below":
            if rect.y0 < anchor.y1 - 12.0:
                continue

            distance = max(
                0.0,
                rect.y0 - anchor.y1,
            )

        else:
            vertical_gap = max(
                0.0,
                max(
                    anchor.y0,
                    rect.y0,
                )
                - min(
                    anchor.y1,
                    rect.y1,
                ),
            )

            distance = vertical_gap

        score = distance - (horizontal_bonus * 40.0)

        ranked.append(
            (
                score,
                rect,
            )
        )

    if not ranked:
        return None

    ranked.sort(
        key=lambda item: item[0],
    )

    best_score, best_rect = ranked[0]

    # Do not associate a remote figure with a question merely because the page
    # contains graphics elsewhere.
    if best_score > 260.0:
        return None

    selected = pymupdf.Rect(
        best_rect,
    )

    # Multi-model figures are often represented as separate vector groups on
    # the same horizontal band. Fold nearby peer groups into one candidate crop.
    best_center_y = (best_rect.y0 + best_rect.y1) / 2.0

    for _, candidate in ranked[1:]:
        candidate_center_y = (candidate.y0 + candidate.y1) / 2.0

        if abs(candidate_center_y - best_center_y) > 45.0:
            continue

        horizontal_gap = max(
            0.0,
            max(
                selected.x0,
                candidate.x0,
            )
            - min(
                selected.x1,
                candidate.x1,
            ),
        )

        if horizontal_gap <= VISUAL_SAME_BAND_GAP:
            selected |= candidate

    return selected


def _question_asset_output_directory(
    *,
    document_path: Path,
    source_document_id: int,
    extraction_version: int,
) -> Path:
    """
    Return the version-scoped directory for generated question visual crops.
    """

    return (
        document_path.parent
        / "question-extraction-assets"
        / f"document-{source_document_id}"
        / f"v{extraction_version}"
    )


def _safe_question_asset_filename_part(
    question_number: str,
) -> str:
    """
    Return a filesystem-safe question-number fragment.
    """

    cleaned = re.sub(
        r"[^A-Za-z0-9_-]+",
        "-",
        question_number.strip(),
    ).strip(
        "-",
    )

    return cleaned or "question"


def _rect_intersection_area(
    left: pymupdf.Rect,
    right: pymupdf.Rect,
) -> float:
    """
    Return the area shared by two rectangles.
    """

    intersection = pymupdf.Rect(
        max(
            left.x0,
            right.x0,
        ),
        max(
            left.y0,
            right.y0,
        ),
        min(
            left.x1,
            right.x1,
        ),
        min(
            left.y1,
            right.y1,
        ),
    )

    if intersection.is_empty:
        return 0.0

    return max(
        intersection.width,
        0.0,
    ) * max(
        intersection.height,
        0.0,
    )


def _embedded_image_rectangles(
    page: pymupdf.Page,
) -> list[pymupdf.Rect]:
    """
    Return unique placed-image rectangles from one PDF page.

    This helper is intentionally defensive because malformed or unusual PDFs can
    expose image XRefs that PyMuPDF cannot resolve back to placement rectangles.
    """

    try:
        page_images = page.get_images(
            full=True,
        )
    except Exception:
        return []

    result: list[pymupdf.Rect] = []
    seen: set[
        tuple[
            float,
            float,
            float,
            float,
        ]
    ] = set()

    for image_info in page_images:
        if not image_info:
            continue

        xref = image_info[0]

        try:
            image_rects = page.get_image_rects(
                xref,
            )
        except Exception:
            image_rects = []

        for image_rect in image_rects:
            rect = pymupdf.Rect(
                image_rect,
            )

            if rect.is_empty:
                continue

            key = (
                round(
                    rect.x0,
                    3,
                ),
                round(
                    rect.y0,
                    3,
                ),
                round(
                    rect.x1,
                    3,
                ),
                round(
                    rect.y1,
                    3,
                ),
            )

            if key in seen:
                continue

            seen.add(
                key,
            )
            result.append(
                rect,
            )

    return result


def _question_visual_render_margin(
    *,
    page: pymupdf.Page,
    crop_rect: pymupdf.Rect,
) -> tuple[
    float,
    str,
]:
    """
    Choose a rendering margin without pulling nearby question prose into crops.

    Raster figures already have a precise placed-image rectangle in the source
    PDF, so a very small safety margin is sufficient. Vector-built figures still
    use the wider historical margin because separate strokes, arrowheads and
    labels may sit just outside the merged primitive region.

    The coverage test also supports figures assembled from more than one placed
    raster image: intersections are accumulated up to the crop area.
    """

    crop_area = max(
        crop_rect.width * crop_rect.height,
        1.0,
    )

    covered_area = 0.0

    for image_rect in _embedded_image_rectangles(
        page,
    ):
        covered_area += _rect_intersection_area(
            crop_rect,
            image_rect,
        )

        if covered_area >= crop_area:
            covered_area = crop_area
            break

    coverage = min(
        covered_area / crop_area,
        1.0,
    )

    if coverage >= VISUAL_EMBEDDED_IMAGE_COVERAGE_THRESHOLD:
        return (
            VISUAL_EMBEDDED_IMAGE_MARGIN,
            "embedded_image_tight",
        )

    return (
        VISUAL_REGION_MARGIN,
        "visual_region_margin",
    )


def _render_question_visual_asset(
    *,
    page: pymupdf.Page,
    crop_rect: pymupdf.Rect,
    output_directory: Path,
    question_number: str,
    page_number: int,
    asset_index: int,
    source_document_id: int,
    asset_type: AssessmentQuestionAssetType,
) -> dict[str, Any]:
    """
    Render one candidate-visible PNG crop and return proposal asset metadata.
    """

    page_rect = page.rect

    (
        render_margin,
        crop_strategy,
    ) = _question_visual_render_margin(
        page=page,
        crop_rect=crop_rect,
    )

    expanded = pymupdf.Rect(
        max(
            page_rect.x0,
            crop_rect.x0 - render_margin,
        ),
        max(
            page_rect.y0,
            crop_rect.y0 - render_margin,
        ),
        min(
            page_rect.x1,
            crop_rect.x1 + render_margin,
        ),
        min(
            page_rect.y1,
            crop_rect.y1 + render_margin,
        ),
    )

    output_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    safe_question_number = _safe_question_asset_filename_part(
        question_number,
    )

    filename = (
        f"question-{safe_question_number}"
        f"-page-{page_number}"
        f"-asset-{asset_index + 1}.png"
    )

    output_path = output_directory / filename

    pixmap = page.get_pixmap(
        matrix=pymupdf.Matrix(
            VISUAL_RENDER_SCALE,
            VISUAL_RENDER_SCALE,
        ),
        clip=expanded,
        alpha=False,
    )

    pixmap.save(
        str(
            output_path,
        )
    )

    return {
        "asset_type": asset_type.value,
        "storage_path": str(
            output_path,
        ),
        "original_filename": filename,
        "mime_type": "image/png",
        "file_size_bytes": output_path.stat().st_size,
        "alt_text": None,
        "caption": None,
        "order": asset_index + 1,
        "candidate_visible": True,
        "source_document_id": source_document_id,
        "source_page_number": page_number,
        "source_bbox": {
            "x0": round(
                expanded.x0,
                3,
            ),
            "y0": round(
                expanded.y0,
                3,
            ),
            "x1": round(
                expanded.x1,
                3,
            ),
            "y1": round(
                expanded.y1,
                3,
            ),
            "page_width": round(
                page_rect.width,
                3,
            ),
            "page_height": round(
                page_rect.height,
                3,
            ),
            "render_margin": round(
                render_margin,
                3,
            ),
            "crop_strategy": crop_strategy,
        },
        "included": True,
        "reviewed": False,
    }


def _attach_visual_assets_to_proposal(
    *,
    document_path: Path,
    proposal: dict[str, Any],
    source_document_id: int,
    extraction_version: int,
) -> int:
    """
    Detect, crop and attach visually referenced PDF regions to proposal rows.

    Text extraction remains owned by pypdf. PyMuPDF is used only for
    coordinate-aware visual detection and clipped rendering.
    """

    questions = proposal.get(
        "questions",
        [],
    )

    if not isinstance(
        questions,
        list,
    ):
        return 0

    output_directory = _question_asset_output_directory(
        document_path=document_path,
        source_document_id=source_document_id,
        extraction_version=extraction_version,
    )

    generated_count = 0
    warning_pages: set[int] = set()

    try:
        visual_document = pymupdf.open(
            str(
                document_path,
            )
        )
    except Exception as exc:
        proposal.setdefault(
            "warnings",
            [],
        ).append(
            {
                "code": "visual_extraction_unavailable",
                "message": (
                    "The PDF text was extracted, but visual regions could not "
                    f"be inspected: {type(exc).__name__}."
                ),
                "page_numbers": [],
            }
        )

        return 0

    try:
        regions_by_page: dict[
            int,
            list[pymupdf.Rect],
        ] = {}

        for question in questions:
            if not isinstance(
                question,
                dict,
            ):
                continue

            source = question.get(
                "source",
                {},
            )

            page_number = source.get(
                "page_number",
            )

            if (
                not isinstance(
                    page_number,
                    int,
                )
                or page_number < 1
                or page_number
                > len(
                    visual_document,
                )
            ):
                continue

            question_text = str(
                question.get(
                    "text",
                    "",
                )
                or ""
            )

            source_line = source.get(
                "source_line",
                "",
            )

            combined_text = " ".join(
                part
                for part in (
                    question_text,
                    source_line if isinstance(source_line, str) else "",
                )
                if part
            )

            if (
                VISUAL_REFERENCE_PATTERN.search(
                    combined_text,
                )
                is None
            ):
                continue

            page = visual_document[page_number - 1]

            if page_number not in regions_by_page:
                regions_by_page[page_number] = _extract_page_visual_regions(
                    page,
                )

            crop_rect = _choose_visual_region_for_question(
                page=page,
                question=question,
                visual_regions=regions_by_page[page_number],
            )

            if crop_rect is None:
                warning_pages.add(
                    page_number,
                )
                continue

            existing_assets = question.get(
                "assets",
                [],
            )

            if not isinstance(
                existing_assets,
                list,
            ):
                existing_assets = []

            asset_type = _infer_visual_asset_type(
                combined_text,
            )

            asset = _render_question_visual_asset(
                page=page,
                crop_rect=crop_rect,
                output_directory=output_directory,
                question_number=str(
                    question.get(
                        "question_number",
                        "",
                    )
                ),
                page_number=page_number,
                asset_index=len(
                    existing_assets,
                ),
                source_document_id=source_document_id,
                asset_type=asset_type,
            )

            existing_assets.append(
                asset,
            )

            question["assets"] = existing_assets

            current_question_type = str(
                question.get(
                    "question_type",
                    AssessmentQuestionType.WRITTEN.value,
                )
                or AssessmentQuestionType.WRITTEN.value
            )

            if (
                current_question_type == AssessmentQuestionType.WRITTEN.value
                and _is_diagram_annotation_instruction(
                    combined_text,
                )
            ):
                question["question_type"] = (
                    AssessmentQuestionType.DIAGRAM_ANNOTATION.value
                )
                question["requires_review"] = True

            generated_count += 1

        if warning_pages:
            proposal.setdefault(
                "warnings",
                [],
            ).append(
                {
                    "code": "visual_reference_without_asset",
                    "message": (
                        "One or more questions refer to a figure, diagram, "
                        "graph or model, but no reliable visual crop could be "
                        "created automatically. Review the original paper."
                    ),
                    "page_numbers": sorted(
                        warning_pages,
                    ),
                }
            )

    finally:
        visual_document.close()

    return generated_count


def _read_pdf(
    document_path: Path,
    *,
    source_document_id: int | None = None,
    extraction_version: int | None = None,
) -> tuple[
    dict[str, Any],
    list[dict[str, Any]],
    dict[str, Any],
]:
    """
    Read a digital PDF and return metadata, page evidence and proposal data.

    OCR is deliberately not attempted here. Pages with no extractable text are
    recorded so a future OCR fallback can identify them explicitly.

    After visual extraction/classification is complete, high-confidence learner
    interaction palettes are proposed from the final question wording/type.
    These proposals remain teacher-reviewable and are never treated as answers.
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
        "visual_extractor": "pymupdf",
        "visual_extractor_version": pymupdf.__version__,
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

    generated_visual_asset_count = 0

    if source_document_id is not None and extraction_version is not None:
        generated_visual_asset_count = _attach_visual_assets_to_proposal(
            document_path=document_path,
            proposal=proposal,
            source_document_id=source_document_id,
            extraction_version=extraction_version,
        )

    source_metadata["generated_visual_asset_count"] = generated_visual_asset_count

    proposed_interaction_config_count = 0

    raw_questions = proposal.get(
        "questions",
        [],
    )

    if isinstance(
        raw_questions,
        list,
    ):
        for question in raw_questions:
            if not isinstance(
                question,
                dict,
            ):
                continue

            # Preserve any explicit extractor/teacher configuration already
            # present. Inference is proposal assistance, never an overwrite.
            if question.get(
                "interaction_config",
            ) is not None:
                continue

            inferred_config = infer_interaction_config(
                question_text=(
                    question.get(
                        "text",
                    )
                    if isinstance(
                        question.get(
                            "text",
                        ),
                        str,
                    )
                    else None
                ),
                question_type=question.get(
                    "question_type",
                    AssessmentQuestionType.WRITTEN.value,
                ),
            )

            if inferred_config is None:
                continue

            question["interaction_config"] = interaction_config_as_dict(
                inferred_config,
            )
            question["requires_review"] = True
            proposed_interaction_config_count += 1

    source_metadata["proposed_interaction_config_count"] = (
        proposed_interaction_config_count
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
            source_document_id=source_document_id,
            extraction_version=next_version,
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
        asset_output_directory = _question_asset_output_directory(
            document_path=document_path,
            source_document_id=source_document_id,
            extraction_version=next_version,
        )

        shutil.rmtree(
            asset_output_directory,
            ignore_errors=True,
        )

        await db.rollback()
        raise

    except Exception as exc:
        asset_output_directory = _question_asset_output_directory(
            document_path=document_path,
            source_document_id=source_document_id,
            extraction_version=next_version,
        )

        shutil.rmtree(
            asset_output_directory,
            ignore_errors=True,
        )

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


def _normalise_review_text(
    value: str | None,
) -> str | None:
    """
    Trim optional teacher-authored review text.

    Empty strings are persisted as None so proposal metadata remains compact
    and semantically clear.
    """

    if value is None:
        return None

    cleaned = value.strip()

    if not cleaned:
        return None

    return cleaned


def _review_parent_question_number(
    value: str | None,
) -> str | None:
    """
    Normalise an optional teacher-supplied parent question identifier.
    """

    cleaned = _normalise_review_text(
        value,
    )

    if cleaned is None:
        return None

    return _normalise_question_number(
        cleaned,
    )


def _validate_review_candidate_indexes(
    *,
    stored_questions: list[dict[str, Any]],
    review_update: AssessmentQuestionExtractionReviewUpdate,
) -> None:
    """
    Require a complete, one-to-one review payload for the stored proposal.

    A review save deliberately replaces only editable proposal state. Requiring
    every stored candidate prevents an omitted browser row from being silently
    lost or left with stale review state.
    """

    expected_indexes = set(
        range(
            len(
                stored_questions,
            )
        )
    )

    supplied_indexes = {
        question.candidate_index for question in review_update.questions
    }

    if supplied_indexes != expected_indexes:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=(
                "Review questions must contain each stored extraction "
                "candidate exactly once."
            ),
        )


def _validate_review_question_numbers(
    review_update: AssessmentQuestionExtractionReviewUpdate,
) -> None:
    """
    Ensure included proposal questions have unique normalised identifiers.
    """

    seen_numbers: set[str] = set()

    for question in review_update.questions:
        if not question.included:
            continue

        question_number = _normalise_question_number(
            question.question_number.strip(),
        )

        if question_number in seen_numbers:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=(
                    "Included extraction questions must have unique "
                    "question numbers."
                ),
            )

        seen_numbers.add(
            question_number,
        )


def _validate_review_completion(
    review_update: AssessmentQuestionExtractionReviewUpdate,
) -> None:
    """
    A proposal cannot be marked reviewed while included rows remain unreviewed.
    """

    if review_update.review_status != AssessmentQuestionExtractionReviewStatus.REVIEWED:
        return

    unreviewed_indexes = [
        question.candidate_index
        for question in review_update.questions
        if question.included and not question.reviewed
    ]

    if unreviewed_indexes:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=(
                "All included extraction questions must be reviewed before "
                "the proposal can be marked reviewed."
            ),
        )


def _normalise_review_question_type(
    value: AssessmentQuestionType | str | None,
    *,
    fallback: Any,
) -> str:
    """
    Return a validated canonical question-type value for proposal storage.
    """

    candidate = value if value is not None else fallback

    if candidate is None:
        candidate = AssessmentQuestionType.WRITTEN.value

    try:
        return AssessmentQuestionType(
            candidate,
        ).value
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Unsupported assessment question type: {candidate!r}.",
        ) from exc


def _serialise_review_options(
    value: Any,
) -> list[dict[str, Any]]:
    """
    Convert teacher-reviewed option models into JSON-safe proposal rows.
    """

    if value is None:
        return []

    return [
        {
            "text": option.text.strip(),
            "order": option.order,
            "is_correct": option.is_correct,
            "feedback": _normalise_review_text(
                option.feedback,
            ),
        }
        for option in value
    ]


def _merge_review_assets(
    *,
    stored_question: dict[str, Any],
    update_assets: Any,
) -> list[dict[str, Any]]:
    """
    Merge teacher-editable asset fields with extractor-owned provenance.

    The client identifies stored assets only by ``asset_index``. Storage paths,
    source document ids, source pages and bounding boxes remain copied from the
    persisted proposal and cannot be supplied by the browser.
    """

    stored_assets = stored_question.get(
        "assets",
        [],
    )

    if stored_assets is None:
        stored_assets = []

    if not isinstance(
        stored_assets,
        list,
    ) or not all(
        isinstance(
            asset,
            dict,
        )
        for asset in stored_assets
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The stored extraction proposal contains malformed assets.",
        )

    if update_assets is None:
        return [
            dict(
                asset,
            )
            for asset in stored_assets
        ]

    expected_indexes = set(
        range(
            len(
                stored_assets,
            )
        )
    )

    supplied_indexes = {asset.asset_index for asset in update_assets}

    if supplied_indexes != expected_indexes:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=(
                "Reviewed question assets must contain each stored visual "
                "candidate exactly once."
            ),
        )

    updates_by_index = {asset.asset_index: asset for asset in update_assets}

    merged_assets: list[dict[str, Any]] = []

    for asset_index, stored_asset in enumerate(
        stored_assets,
    ):
        update = updates_by_index[asset_index]

        merged_asset = dict(
            stored_asset,
        )

        merged_asset["asset_type"] = update.asset_type.value
        merged_asset["alt_text"] = _normalise_review_text(
            update.alt_text,
        )
        merged_asset["caption"] = _normalise_review_text(
            update.caption,
        )
        merged_asset["order"] = update.order
        merged_asset["candidate_visible"] = update.candidate_visible
        merged_asset["included"] = update.included
        merged_asset["reviewed"] = update.reviewed

        merged_assets.append(
            merged_asset,
        )

    return merged_assets


def _build_reviewed_proposal_questions(
    *,
    stored_questions: list[dict[str, Any]],
    review_update: AssessmentQuestionExtractionReviewUpdate,
) -> list[dict[str, Any]]:
    """
    Merge teacher-editable fields into proposal copies.

    Extractor-owned evidence such as source metadata and confidence is copied
    from the stored proposal, never accepted from the client.
    """

    updates_by_index = {
        question.candidate_index: question for question in review_update.questions
    }

    reviewed_questions: list[dict[str, Any]] = []

    for candidate_index, stored_question in enumerate(
        stored_questions,
    ):
        update = updates_by_index[candidate_index]

        reviewed_question = dict(
            stored_question,
        )

        question_number = _normalise_question_number(
            update.question_number.strip(),
        )

        reviewed_question["question_number"] = question_number
        reviewed_question["text"] = update.text.strip()
        reviewed_question["marks"] = update.marks
        reviewed_question["depth"] = _infer_question_depth(
            question_number,
        )
        reviewed_question["parent_question_number"] = _review_parent_question_number(
            update.parent_question_number,
        )
        reviewed_question["question_type"] = _normalise_review_question_type(
            update.question_type,
            fallback=stored_question.get(
                "question_type",
                AssessmentQuestionType.WRITTEN.value,
            ),
        )

        if "interaction_config" in update.model_fields_set:
            reviewed_question["interaction_config"] = (
                interaction_config_as_dict(
                    update.interaction_config,
                )
                if update.interaction_config is not None
                else None
            )
        else:
            stored_interaction_config = stored_question.get(
                "interaction_config",
            )

            if stored_interaction_config is None:
                reviewed_question["interaction_config"] = None
            elif isinstance(
                stored_interaction_config,
                dict,
            ):
                reviewed_question["interaction_config"] = dict(
                    stored_interaction_config,
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=(
                        "The stored extraction proposal contains malformed "
                        "interaction configuration."
                    ),
                )

        if update.options is None:
            stored_options = stored_question.get(
                "options",
                [],
            )

            if not isinstance(
                stored_options,
                list,
            ):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=(
                        "The stored extraction proposal contains malformed "
                        "question options."
                    ),
                )

            reviewed_question["options"] = [
                dict(
                    option,
                )
                for option in stored_options
                if isinstance(
                    option,
                    dict,
                )
            ]
        else:
            reviewed_question["options"] = _serialise_review_options(
                update.options,
            )

        reviewed_question["assets"] = _merge_review_assets(
            stored_question=stored_question,
            update_assets=update.assets,
        )
        reviewed_question["included"] = update.included
        reviewed_question["reviewed"] = update.reviewed

        if "source" in stored_question:
            reviewed_question["source"] = stored_question["source"]

        if "confidence" in stored_question:
            reviewed_question["confidence"] = stored_question["confidence"]

        if "requires_review" in stored_question:
            reviewed_question["requires_review"] = stored_question["requires_review"]

        reviewed_questions.append(
            reviewed_question,
        )

    return reviewed_questions


def _validate_reviewed_interaction_requirements(
    reviewed_questions: list[dict[str, Any]],
) -> None:
    """
    Enforce interaction-specific requirements on the fully merged review state.

    Diagram-annotation questions require at least one included,
    candidate-visible, reviewed visual asset. This validation operates on the
    merged proposal rather than the raw request so omitted asset updates still
    preserve and validate extractor-owned assets correctly.
    """

    for question in reviewed_questions:
        if not bool(
            question.get(
                "included",
                True,
            )
        ):
            continue

        question_number = str(
            question.get(
                "question_number",
                "",
            )
            or ""
        )

        try:
            question_type = AssessmentQuestionType(
                question.get(
                    "question_type",
                    AssessmentQuestionType.WRITTEN.value,
                )
            )
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=(
                    f"Question {question_number!r} contains an unsupported "
                    "question type."
                ),
            ) from exc

        if question_type != AssessmentQuestionType.DIAGRAM_ANNOTATION:
            continue

        raw_assets = question.get(
            "assets",
            [],
        )

        if not isinstance(
            raw_assets,
            list,
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"Question {question_number!r} has malformed visual assets."
                ),
            )

        usable_assets = [
            asset
            for asset in raw_assets
            if isinstance(
                asset,
                dict,
            )
            and bool(
                asset.get(
                    "included",
                    True,
                )
            )
            and bool(
                asset.get(
                    "candidate_visible",
                    True,
                )
            )
            and bool(
                asset.get(
                    "reviewed",
                    False,
                )
            )
        ]

        if not usable_assets:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=(
                    f"Question {question_number!r}: a diagram-annotation "
                    "question must have at least one included, candidate-visible "
                    "and reviewed visual asset."
                ),
            )


def _review_summary(
    *,
    proposal: dict[str, Any],
    reviewed_questions: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Preserve extraction statistics and add teacher-review totals.
    """

    existing_summary = proposal.get(
        "summary",
        {},
    )

    if not isinstance(
        existing_summary,
        dict,
    ):
        existing_summary = {}

    summary = dict(
        existing_summary,
    )

    included_questions = [
        question
        for question in reviewed_questions
        if bool(
            question.get(
                "included",
                True,
            )
        )
    ]

    included_marks = [
        question["marks"]
        for question in included_questions
        if isinstance(
            question.get(
                "marks",
            ),
            int,
        )
    ]

    summary["included_question_count"] = len(
        included_questions,
    )
    summary["included_mark_sum"] = sum(
        included_marks,
    )

    return summary


async def update_question_extraction_review(
    *,
    db: AsyncSession,
    current_user: User,
    assessment_id: int,
    extraction_id: int,
    review_update: AssessmentQuestionExtractionReviewUpdate,
) -> AssessmentQuestionExtraction:
    """
    Save teacher review edits to a completed extraction proposal.

    Only proposal_data is changed. Raw page_data/source evidence remains
    immutable and no AssessmentQuestion records are created by this operation.
    """

    extraction = await _load_question_paper_document_for_extraction_access(
        db=db,
        current_user=current_user,
        assessment_id=assessment_id,
        extraction_id=extraction_id,
    )

    if extraction.status != AssessmentQuestionExtractionStatus.COMPLETED.value:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=("Only a completed, active extraction proposal can be " "reviewed."),
        )

    proposal = extraction.proposal_data

    if not isinstance(
        proposal,
        dict,
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The extraction does not contain a reviewable proposal.",
        )

    stored_questions = proposal.get(
        "questions",
    )

    if (
        not isinstance(
            stored_questions,
            list,
        )
        or not stored_questions
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The extraction proposal does not contain any questions.",
        )

    if not all(
        isinstance(
            question,
            dict,
        )
        for question in stored_questions
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The stored extraction proposal is malformed.",
        )

    _validate_review_candidate_indexes(
        stored_questions=stored_questions,
        review_update=review_update,
    )

    _validate_review_question_numbers(
        review_update,
    )

    _validate_review_completion(
        review_update,
    )

    reviewed_questions = _build_reviewed_proposal_questions(
        stored_questions=stored_questions,
        review_update=review_update,
    )

    if review_update.review_status == AssessmentQuestionExtractionReviewStatus.REVIEWED:
        _validate_reviewed_interaction_requirements(
            reviewed_questions,
        )

    reviewed_proposal = dict(
        proposal,
    )

    reviewed_proposal["questions"] = reviewed_questions
    reviewed_proposal["summary"] = _review_summary(
        proposal=proposal,
        reviewed_questions=reviewed_questions,
    )
    reviewed_proposal["review_status"] = review_update.review_status.value
    reviewed_proposal["review_notes"] = _normalise_review_text(
        review_update.review_notes,
    )
    reviewed_proposal["auto_import_allowed"] = False

    if review_update.review_status == AssessmentQuestionExtractionReviewStatus.REVIEWED:
        reviewed_proposal["review_required"] = False
        reviewed_proposal["reviewed_by_id"] = current_user.id
        reviewed_proposal["reviewed_at"] = _utc_now().isoformat()
    else:
        reviewed_proposal["review_required"] = True
        reviewed_proposal["reviewed_by_id"] = None
        reviewed_proposal["reviewed_at"] = None

    extraction.proposal_data = reviewed_proposal

    repository = AssessmentQuestionExtractionRepository(
        db,
    )

    try:
        extraction = await repository.save(
            extraction,
        )

        await db.commit()

        await db.refresh(
            extraction,
        )

        return extraction

    except HTTPException:
        await db.rollback()
        raise

    except Exception:
        await db.rollback()
        raise


def _infer_import_parent_question_number(
    question_number: str,
) -> str | None:
    """
    Infer the immediate structural parent of a canonical question number.

    Examples:

    - ``1`` -> None
    - ``1(a)`` -> ``1``
    - ``1(a)(i)`` -> ``1(a)``

    Teacher-supplied ``parent_question_number`` remains authoritative when
    present. This helper is used only when review did not explicitly set one.
    """

    cleaned = _normalise_question_number(
        question_number.strip(),
    )

    if not cleaned:
        return None

    match = re.match(
        r"^(?P<parent>.+)\([^()]+\)$",
        cleaned,
    )

    if match is None:
        return None

    parent = match.group(
        "parent",
    ).strip()

    if not parent:
        return None

    return parent


def _normalise_import_question_number(
    value: Any,
    *,
    field_name: str,
) -> str:
    """
    Return one validated canonical question identifier for import.
    """

    if not isinstance(
        value,
        str,
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"{field_name} must be a string.",
        )

    cleaned = _normalise_question_number(
        value.strip(),
    )

    if not cleaned:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"{field_name} cannot be blank.",
        )

    if (
        len(
            cleaned,
        )
        > 50
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"{field_name} cannot exceed 50 characters.",
        )

    return cleaned


def _normalise_import_question_type(
    value: Any,
    *,
    question_number: str,
) -> AssessmentQuestionType:
    """
    Validate the reviewed proposal's canonical question type.
    """

    if value is None:
        value = AssessmentQuestionType.WRITTEN.value

    try:
        return AssessmentQuestionType(
            value,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=(
                f"Question {question_number!r} contains an unsupported "
                f"question type {value!r}."
            ),
        ) from exc


def _normalise_import_options(
    value: Any,
    *,
    question_number: str,
    question_type: AssessmentQuestionType,
) -> list[dict[str, Any]]:
    """
    Validate and normalise structured options before canonical import.
    """

    if value is None:
        value = []

    if not isinstance(
        value,
        list,
    ) or not all(
        isinstance(
            option,
            dict,
        )
        for option in value
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Question {question_number!r} options are malformed.",
        )

    options: list[dict[str, Any]] = []

    for index, option in enumerate(
        value,
        start=1,
    ):
        raw_text = option.get(
            "text",
        )

        if (
            not isinstance(
                raw_text,
                str,
            )
            or not raw_text.strip()
        ):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=(
                    f"Question {question_number!r} option {index} must contain "
                    "non-blank text."
                ),
            )

        raw_order = option.get(
            "order",
            index,
        )

        if (
            not isinstance(
                raw_order,
                int,
            )
            or isinstance(
                raw_order,
                bool,
            )
            or raw_order < 1
        ):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=(
                    f"Question {question_number!r} option {index} has an "
                    "invalid order."
                ),
            )

        raw_is_correct = option.get(
            "is_correct",
            False,
        )

        if not isinstance(
            raw_is_correct,
            bool,
        ):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=(
                    f"Question {question_number!r} option {index} has an "
                    "invalid correctness flag."
                ),
            )

        feedback = option.get(
            "feedback",
        )

        if feedback is not None and not isinstance(
            feedback,
            str,
        ):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=(
                    f"Question {question_number!r} option {index} feedback "
                    "must be text or null."
                ),
            )

        options.append(
            {
                "text": raw_text.strip(),
                "order": raw_order,
                "is_correct": raw_is_correct,
                "feedback": (
                    feedback.strip()
                    if isinstance(
                        feedback,
                        str,
                    )
                    and feedback.strip()
                    else None
                ),
            }
        )

    option_orders = [option["order"] for option in options]

    if len(option_orders) != len(set(option_orders)):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=(
                f"Question {question_number!r} option order values must be " "unique."
            ),
        )

    option_count = len(
        options,
    )

    correct_count = sum(1 for option in options if option["is_correct"])

    if (
        question_type
        in {
            AssessmentQuestionType.WRITTEN,
            AssessmentQuestionType.NUMERIC,
            AssessmentQuestionType.DIAGRAM_ANNOTATION,
            AssessmentQuestionType.STRUCTURAL,
        }
        and option_count > 0
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=(
                f"Question {question_number!r} cannot have multiple-choice "
                "options for its selected question type."
            ),
        )

    if question_type == AssessmentQuestionType.MULTIPLE_CHOICE_SINGLE:
        if option_count < 2 or correct_count != 1:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=(
                    f"Question {question_number!r} must contain at least two "
                    "options and exactly one correct option."
                ),
            )

    if question_type == AssessmentQuestionType.MULTIPLE_CHOICE_MULTIPLE:
        if option_count < 2 or correct_count < 1:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=(
                    f"Question {question_number!r} must contain at least two "
                    "options and at least one correct option."
                ),
            )

    if question_type == AssessmentQuestionType.TRUE_FALSE:
        if option_count != 2 or correct_count != 1:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=(
                    f"Question {question_number!r} must contain exactly two "
                    "true/false options and exactly one correct option."
                ),
            )

    return options


def _normalise_import_assets(
    value: Any,
    *,
    question_number: str,
    source_document_id: int,
) -> list[dict[str, Any]]:
    """
    Validate reviewed visual assets before canonical import.

    Only included assets are imported. A visual without a real ``storage_path``
    and ``mime_type`` cannot yet be delivered to a candidate, so import blocks
    rather than silently dropping the figure.
    """

    if value is None:
        value = []

    if not isinstance(
        value,
        list,
    ) or not all(
        isinstance(
            asset,
            dict,
        )
        for asset in value
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Question {question_number!r} assets are malformed.",
        )

    assets: list[dict[str, Any]] = []

    for index, asset in enumerate(
        value,
        start=1,
    ):
        if not bool(
            asset.get(
                "included",
                True,
            )
        ):
            continue

        if not bool(
            asset.get(
                "reviewed",
                False,
            )
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"Question {question_number!r} contains a visual asset "
                    "that has not been reviewed."
                ),
            )

        try:
            asset_type = AssessmentQuestionAssetType(
                asset.get(
                    "asset_type",
                    AssessmentQuestionAssetType.FIGURE.value,
                )
            )
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=(
                    f"Question {question_number!r} asset {index} has an "
                    "unsupported asset type."
                ),
            ) from exc

        storage_path = asset.get(
            "storage_path",
        )

        mime_type = asset.get(
            "mime_type",
        )

        if (
            not isinstance(
                storage_path,
                str,
            )
            or not storage_path.strip()
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"Question {question_number!r} contains a reviewed visual "
                    "that has not yet been materialised for candidate delivery."
                ),
            )

        if (
            not isinstance(
                mime_type,
                str,
            )
            or not mime_type.strip()
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"Question {question_number!r} contains a visual asset "
                    "without a MIME type."
                ),
            )

        raw_order = asset.get(
            "order",
            index,
        )

        if (
            not isinstance(
                raw_order,
                int,
            )
            or isinstance(
                raw_order,
                bool,
            )
            or raw_order < 1
        ):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=(
                    f"Question {question_number!r} asset {index} has an "
                    "invalid order."
                ),
            )

        source_page_number = asset.get(
            "source_page_number",
        )

        if source_page_number is not None and (
            not isinstance(
                source_page_number,
                int,
            )
            or isinstance(
                source_page_number,
                bool,
            )
            or source_page_number < 1
        ):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=(
                    f"Question {question_number!r} asset {index} has an "
                    "invalid source page number."
                ),
            )

        source_bbox = asset.get(
            "source_bbox",
        )

        if source_bbox is not None and not isinstance(
            source_bbox,
            dict,
        ):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=(
                    f"Question {question_number!r} asset {index} has malformed "
                    "source coordinates."
                ),
            )

        original_filename = asset.get(
            "original_filename",
        )

        if original_filename is not None and not isinstance(
            original_filename,
            str,
        ):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=(
                    f"Question {question_number!r} asset {index} filename "
                    "must be text or null."
                ),
            )

        file_size_bytes = asset.get(
            "file_size_bytes",
        )

        if file_size_bytes is not None and (
            not isinstance(
                file_size_bytes,
                int,
            )
            or isinstance(
                file_size_bytes,
                bool,
            )
            or file_size_bytes < 0
        ):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=(
                    f"Question {question_number!r} asset {index} has an "
                    "invalid file size."
                ),
            )

        alt_text = asset.get(
            "alt_text",
        )

        caption = asset.get(
            "caption",
        )

        if alt_text is not None and not isinstance(
            alt_text,
            str,
        ):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=(
                    f"Question {question_number!r} asset {index} alt text "
                    "must be text or null."
                ),
            )

        if caption is not None and not isinstance(
            caption,
            str,
        ):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=(
                    f"Question {question_number!r} asset {index} caption "
                    "must be text or null."
                ),
            )

        assets.append(
            {
                "asset_type": asset_type.value,
                "storage_path": storage_path.strip(),
                "original_filename": (
                    original_filename.strip()
                    if isinstance(
                        original_filename,
                        str,
                    )
                    and original_filename.strip()
                    else None
                ),
                "mime_type": mime_type.strip(),
                "file_size_bytes": file_size_bytes,
                "alt_text": (
                    alt_text.strip()
                    if isinstance(
                        alt_text,
                        str,
                    )
                    and alt_text.strip()
                    else None
                ),
                "caption": (
                    caption.strip()
                    if isinstance(
                        caption,
                        str,
                    )
                    and caption.strip()
                    else None
                ),
                "order": raw_order,
                "candidate_visible": bool(
                    asset.get(
                        "candidate_visible",
                        True,
                    )
                ),
                "source_document_id": source_document_id,
                "source_page_number": source_page_number,
                "source_bbox": source_bbox,
            }
        )

    asset_orders = [asset["order"] for asset in assets]

    if len(asset_orders) != len(set(asset_orders)):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=(
                f"Question {question_number!r} asset order values must be " "unique."
            ),
        )

    return assets


def _normalise_import_interaction_config(
    raw_config: Any,
    *,
    question_number: str,
) -> dict[str, object] | None:
    """
    Validate candidate-visible interaction configuration before canonical import.

    Extraction proposals are JSON documents and may originate from older parser
    versions. A missing/null configuration therefore remains valid for backwards
    compatibility, while any supplied configuration must satisfy the shared
    strict schema before it can reach AssessmentQuestion.interaction_config.
    """

    if raw_config is None:
        return None

    if not isinstance(
        raw_config,
        dict,
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=(
                f"Question {question_number!r} contains malformed interaction "
                "configuration."
            ),
        )

    try:
        validated = AssessmentQuestionInteractionConfig.model_validate(
            raw_config,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=(
                f"Question {question_number!r} contains invalid interaction "
                f"configuration: {exc}"
            ),
        ) from exc

    return interaction_config_as_dict(
        validated,
    )


def _build_import_question_specs(
    *,
    proposal: dict[str, Any],
    source_document_id: int,
) -> list[dict[str, Any]]:
    """
    Convert a reviewed proposal into ordered canonical-question specifications.

    Included proposal rows become markable questions. Missing structural parents
    are synthesised recursively with zero marks and ``is_markable=False``.

    The returned list is topologically ordered: every parent appears before its
    children, while first appearance in the reviewed proposal remains the
    controlling display order.
    """

    questions = proposal.get(
        "questions",
    )

    if (
        not isinstance(
            questions,
            list,
        )
        or not questions
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The extraction proposal does not contain any questions.",
        )

    if not all(
        isinstance(
            question,
            dict,
        )
        for question in questions
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The stored extraction proposal is malformed.",
        )

    included_candidates: list[dict[str, Any]] = []

    for candidate_index, question in enumerate(
        questions,
    ):
        if not bool(
            question.get(
                "included",
                True,
            )
        ):
            continue

        if not bool(
            question.get(
                "reviewed",
                False,
            )
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "Every included extraction question must be reviewed "
                    "before import."
                ),
            )

        question_number = _normalise_import_question_number(
            question.get(
                "question_number",
            ),
            field_name="question_number",
        )

        source = question.get(
            "source",
        )

        source_page_number: int | None = None

        if isinstance(
            source,
            dict,
        ):
            raw_source_page_number = source.get(
                "page_number",
            )

            if (
                isinstance(
                    raw_source_page_number,
                    int,
                )
                and not isinstance(
                    raw_source_page_number,
                    bool,
                )
                and raw_source_page_number > 0
            ):
                source_page_number = raw_source_page_number

        marks = question.get(
            "marks",
        )

        if (
            not isinstance(
                marks,
                int,
            )
            or isinstance(
                marks,
                bool,
            )
            or marks < 0
        ):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=(
                    f"Included question {question_number!r} must have a "
                    "non-negative integer mark allocation before import."
                ),
            )

        raw_parent = question.get(
            "parent_question_number",
        )

        if raw_parent is None:
            parent_question_number = _infer_import_parent_question_number(
                question_number,
            )
        else:
            parent_question_number = _normalise_import_question_number(
                raw_parent,
                field_name="parent_question_number",
            )

        if parent_question_number == question_number:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=(f"Question {question_number!r} cannot be its own parent."),
            )

        text = question.get(
            "text",
            "",
        )

        if text is None:
            text = ""

        if not isinstance(
            text,
            str,
        ):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=(f"Question {question_number!r} text must be a string."),
            )

        question_type = _normalise_import_question_type(
            question.get(
                "question_type",
                AssessmentQuestionType.WRITTEN.value,
            ),
            question_number=question_number,
        )

        options = _normalise_import_options(
            question.get(
                "options",
                [],
            ),
            question_number=question_number,
            question_type=question_type,
        )

        assets = _normalise_import_assets(
            question.get(
                "assets",
                [],
            ),
            question_number=question_number,
            source_document_id=source_document_id,
        )

        interaction_config = _normalise_import_interaction_config(
            question.get(
                "interaction_config",
            ),
            question_number=question_number,
        )

        if question_type == AssessmentQuestionType.DIAGRAM_ANNOTATION:
            candidate_visible_assets = [
                asset
                for asset in assets
                if bool(
                    asset.get(
                        "candidate_visible",
                        True,
                    )
                )
            ]

            if not candidate_visible_assets:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                    detail=(
                        f"Question {question_number!r}: a diagram-annotation "
                        "question must import at least one candidate-visible "
                        "visual asset."
                    ),
                )

        included_candidates.append(
            {
                "question_number": question_number,
                "parent_question_number": parent_question_number,
                "prompt": text.strip() or None,
                "question_type": question_type.value,
                "interaction_config": interaction_config,
                "maximum_mark": Decimal(
                    marks,
                ),
                "is_markable": True,
                "source_page_number": source_page_number,
                "options": options,
                "assets": assets,
                "synthesised": False,
                "source_candidate_index": candidate_index,
            }
        )

    if not included_candidates:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The reviewed extraction proposal contains no included questions.",
        )

    specs_by_number: dict[str, dict[str, Any]] = {}

    for spec in included_candidates:
        question_number = spec["question_number"]

        if question_number in specs_by_number:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=(
                    "Included extraction questions must have unique "
                    "question numbers."
                ),
            )

        specs_by_number[question_number] = spec

    def ensure_parent_spec(
        parent_number: str | None,
        *,
        ancestry: tuple[str, ...],
    ) -> None:
        if parent_number is None:
            return

        if parent_number in ancestry:
            cycle = " -> ".join(
                (
                    *ancestry,
                    parent_number,
                )
            )
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=f"Question parent hierarchy contains a cycle: {cycle}.",
            )

        existing = specs_by_number.get(
            parent_number,
        )

        if existing is not None:
            next_parent = existing.get(
                "parent_question_number",
            )

            if next_parent is None and existing["synthesised"]:
                next_parent = _infer_import_parent_question_number(
                    parent_number,
                )
                existing["parent_question_number"] = next_parent

            ensure_parent_spec(
                next_parent,
                ancestry=(
                    *ancestry,
                    parent_number,
                ),
            )
            return

        inferred_parent = _infer_import_parent_question_number(
            parent_number,
        )

        specs_by_number[parent_number] = {
            "question_number": parent_number,
            "parent_question_number": inferred_parent,
            "prompt": None,
            "question_type": AssessmentQuestionType.STRUCTURAL.value,
            "interaction_config": None,
            "maximum_mark": Decimal("0"),
            "is_markable": False,
            "options": [],
            "assets": [],
            "synthesised": True,
            "source_candidate_index": None,
        }

        ensure_parent_spec(
            inferred_parent,
            ancestry=(
                *ancestry,
                parent_number,
            ),
        )

    for spec in list(
        included_candidates,
    ):
        ensure_parent_spec(
            spec["parent_question_number"],
            ancestry=(spec["question_number"],),
        )

    ordered_specs: list[dict[str, Any]] = []
    emitted: set[str] = set()
    visiting: set[str] = set()

    def emit(
        question_number: str,
    ) -> None:
        if question_number in emitted:
            return

        if question_number in visiting:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Question parent hierarchy contains a cycle.",
            )

        visiting.add(
            question_number,
        )

        spec = specs_by_number[question_number]
        parent_number = spec.get(
            "parent_question_number",
        )

        if parent_number is not None:
            if parent_number not in specs_by_number:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                    detail=(
                        f"Question {question_number!r} references an invalid "
                        f"parent {parent_number!r}."
                    ),
                )

            emit(
                parent_number,
            )

        visiting.remove(
            question_number,
        )
        emitted.add(
            question_number,
        )
        ordered_specs.append(
            spec,
        )

    for candidate in included_candidates:
        emit(
            candidate["question_number"],
        )

    return ordered_specs


async def import_question_extraction(
    *,
    db: AsyncSession,
    current_user: User,
    assessment_id: int,
    extraction_id: int,
) -> tuple[
    AssessmentQuestionExtraction,
    list[AssessmentQuestionExtractionImportedQuestionResponse],
]:
    """
    Explicitly import a fully reviewed extraction into canonical questions.

    Import is intentionally separate from extraction and review. The operation
    is atomic: all question rows, hierarchy links and the extraction's IMPORTED
    state are committed together, or all are rolled back together.
    """

    await _get_manageable_draft_assessment(
        db,
        current_user,
        assessment_id,
        include_relationships=False,
    )

    extraction = await _load_question_paper_document_for_extraction_access(
        db=db,
        current_user=current_user,
        assessment_id=assessment_id,
        extraction_id=extraction_id,
    )

    if extraction.status == AssessmentQuestionExtractionStatus.IMPORTED.value:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This extraction proposal has already been imported.",
        )

    if extraction.status != AssessmentQuestionExtractionStatus.COMPLETED.value:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=("Only a completed, active extraction proposal can be imported."),
        )

    proposal = extraction.proposal_data

    if not isinstance(
        proposal,
        dict,
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The extraction does not contain a reviewable proposal.",
        )

    if (
        proposal.get(
            "review_status",
        )
        != AssessmentQuestionExtractionReviewStatus.REVIEWED.value
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=("The extraction proposal must be fully reviewed before import."),
        )

    if bool(
        proposal.get(
            "review_required",
            True,
        )
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "The extraction proposal still requires review and cannot "
                "be imported."
            ),
        )

    specs = _build_import_question_specs(
        proposal=proposal,
        source_document_id=extraction.assessment_document_id,
    )

    question_repository = AssessmentQuestionRepository(
        db,
    )

    extraction_repository = AssessmentQuestionExtractionRepository(
        db,
    )

    existing_questions = await question_repository.list_questions_by_assessment(
        assessment_id,
        include_relationships=False,
    )

    existing_numbers = {question.question_number for question in existing_questions}

    import_numbers = {spec["question_number"] for spec in specs}

    conflicts = sorted(
        existing_numbers.intersection(
            import_numbers,
        )
    )

    if conflicts:
        conflict_text = ", ".join(
            repr(
                question_number,
            )
            for question_number in conflicts
        )

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Cannot import the reviewed extraction because these question "
                f"numbers already exist in the assessment: {conflict_text}."
            ),
        )

    next_order = (
        max(
            (question.order for question in existing_questions),
            default=0,
        )
        + 1
    )

    created_by_number: dict[str, AssessmentQuestion] = {}

    imported_question_responses: list[
        AssessmentQuestionExtractionImportedQuestionResponse
    ] = []

    try:
        for offset, spec in enumerate(
            specs,
        ):
            parent_number = spec.get(
                "parent_question_number",
            )

            parent_question_id: int | None = None

            if parent_number is not None:
                parent = created_by_number.get(
                    parent_number,
                )

                if parent is None or parent.id is None:
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                        detail=(
                            f"Question {spec['question_number']!r} could not "
                            f"resolve parent {parent_number!r} during import."
                        ),
                    )

                parent_question_id = parent.id

            question = AssessmentQuestion(
                assessment_id=assessment_id,
                section_id=None,
                parent_question_id=parent_question_id,
                question_number=spec["question_number"],
                title=None,
                prompt=spec["prompt"],
                question_type=spec["question_type"],
                interaction_config=spec["interaction_config"],
                maximum_mark=spec["maximum_mark"],
                order=next_order + offset,
                is_markable=spec["is_markable"],
                source_page_number=spec.get("source_page_number"),
                options=[
                    AssessmentQuestionOption(
                        text=option["text"],
                        order=option["order"],
                        is_correct=option["is_correct"],
                        feedback=option["feedback"],
                    )
                    for option in spec["options"]
                ],
                assets=[
                    AssessmentQuestionAsset(
                        asset_type=asset["asset_type"],
                        storage_path=asset["storage_path"],
                        original_filename=asset["original_filename"],
                        mime_type=asset["mime_type"],
                        file_size_bytes=asset["file_size_bytes"],
                        alt_text=asset["alt_text"],
                        caption=asset["caption"],
                        order=asset["order"],
                        candidate_visible=asset["candidate_visible"],
                        source_document_id=asset["source_document_id"],
                        source_page_number=asset["source_page_number"],
                        source_bbox=asset["source_bbox"],
                    )
                    for asset in spec["assets"]
                ],
            )

            question = await question_repository.create_question(
                question,
            )

            created_by_number[question.question_number] = question

            imported_question_responses.append(
                AssessmentQuestionExtractionImportedQuestionResponse(
                    id=question.id,
                    question_number=question.question_number,
                    parent_question_id=question.parent_question_id,
                    parent_question_number=parent_number,
                    maximum_mark=question.maximum_mark,
                    order=question.order,
                    is_markable=question.is_markable,
                    question_type=AssessmentQuestionType(
                        question.question_type,
                    ),
                    option_count=len(
                        spec["options"],
                    ),
                    asset_count=len(
                        spec["assets"],
                    ),
                    synthesised=spec["synthesised"],
                    source_candidate_index=spec["source_candidate_index"],
                )
            )

        extraction.status = AssessmentQuestionExtractionStatus.IMPORTED.value
        extraction.imported_by_id = current_user.id
        extraction.imported_at = _utc_now()

        extraction = await extraction_repository.save(
            extraction,
        )

        await db.commit()

        await db.refresh(
            extraction,
        )

        return (
            extraction,
            imported_question_responses,
        )

    except HTTPException:
        await db.rollback()
        raise

    except IntegrityError as exc:
        await db.rollback()

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "The reviewed extraction could not be imported because the "
                "assessment structure changed concurrently."
            ),
        ) from exc

    except ValueError as exc:
        await db.rollback()

        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(
                exc,
            ),
        ) from exc

    except Exception:
        await db.rollback()
        raise


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


async def resolve_question_extraction_asset_path(
    *,
    db: AsyncSession,
    current_user: User,
    assessment_id: int,
    extraction_id: int,
    candidate_index: int,
    asset_index: int,
) -> tuple[dict[str, Any], Path]:
    """
    Resolve one extraction visual asset to an authorised local filesystem path.

    The browser identifies an asset only by its extraction-scoped candidate and
    asset indexes. A client-supplied filesystem path is never accepted.

    Normal extraction access is enforced first, then the source document path
    is resolved through the assessment-document policy. The stored asset path
    must remain inside the version-scoped extraction asset directory before the
    file can be served.
    """

    if candidate_index < 0 or asset_index < 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Question extraction asset not found.",
        )

    extraction = await get_question_extraction(
        db=db,
        current_user=current_user,
        assessment_id=assessment_id,
        extraction_id=extraction_id,
    )

    proposal = extraction.proposal_data

    if not isinstance(
        proposal,
        dict,
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Question extraction asset not found.",
        )

    questions = proposal.get(
        "questions",
        [],
    )

    if not isinstance(
        questions,
        list,
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The stored extraction proposal contains malformed questions.",
        )

    if candidate_index >= len(
        questions,
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Question extraction asset not found.",
        )

    question = questions[candidate_index]

    if not isinstance(
        question,
        dict,
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The stored extraction proposal contains a malformed question.",
        )

    assets = question.get(
        "assets",
        [],
    )

    if not isinstance(
        assets,
        list,
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The stored extraction proposal contains malformed assets.",
        )

    if asset_index >= len(
        assets,
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Question extraction asset not found.",
        )

    asset = assets[asset_index]

    if not isinstance(
        asset,
        dict,
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The stored extraction proposal contains a malformed asset.",
        )

    storage_path = asset.get(
        "storage_path",
    )

    if (
        not isinstance(
            storage_path,
            str,
        )
        or not storage_path.strip()
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Question extraction asset file is not available.",
        )

    source_document_id = asset.get(
        "source_document_id",
    )

    if (
        source_document_id is not None
        and source_document_id != extraction.assessment_document_id
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "The stored extraction asset does not belong to the "
                "extraction source document."
            ),
        )

    _, document_path = await resolve_assessment_document_path(
        db=db,
        current_user=current_user,
        assessment_id=assessment_id,
        document_id=extraction.assessment_document_id,
    )

    expected_root = _question_asset_output_directory(
        document_path=document_path,
        source_document_id=extraction.assessment_document_id,
        extraction_version=extraction.version,
    ).resolve()

    asset_path = Path(
        storage_path,
    ).resolve()

    try:
        asset_path.relative_to(
            expected_root,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "The stored extraction asset path falls outside the "
                "authorised extraction directory."
            ),
        ) from exc

    if not asset_path.exists() or not asset_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Question extraction asset file was not found.",
        )

    return (
        dict(
            asset,
        ),
        asset_path,
    )


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
