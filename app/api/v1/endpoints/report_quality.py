import re

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.report_quality import (
    ReportNotesGenerateRequest,
    ReportNotesGenerateResponse,
    ReportQualityCheckRequest,
    ReportQualityCheckResponse,
    ReportQualityIssue,
)
from app.services.report_memory import find_similar_report_memory
from app.services.report_writer import generate_report_comment

router = APIRouter()


UK_SPELLING_REPLACEMENTS = {
    "color": "colour",
    "behavior": "behaviour",
    "organization": "organisation",
    "organize": "organise",
    "organized": "organised",
    "organizing": "organising",
    "analyze": "analyse",
    "analyzed": "analysed",
    "analyzing": "analysing",
    "center": "centre",
    "favorite": "favourite",
    "honor": "honour",
    "labor": "labour",
    "program": "programme",
}


COMMON_TYPO_REPLACEMENTS = {
    "lessansi": "lessons",
    "lessonsi": "lessons",
    "teh": "the",
    "recieve": "receive",
    "acheive": "achieve",
    "seperate": "separate",
    "definately": "definitely",
    "occured": "occurred",
    "goverment": "government",
    "enviroment": "environment",
    "sucess": "success",
    "sucessful": "successful",
    "independant": "independent",
    "independance": "independence",
}


COMMON_PHRASE_FIXES = {
    "has her studies in": "has made a positive start to her studies in",
    "has his studies in": "has made a positive start to his studies in",
    "good knowledge of": "a good knowledge of",
}


def _capitalise_first_letter(text: str) -> str:
    stripped = text.strip()

    if not stripped:
        return ""

    return stripped[0].upper() + stripped[1:]


def _ensure_final_punctuation(text: str) -> str:
    stripped = text.strip()

    if not stripped:
        return ""

    if stripped[-1] in ".!?":
        return stripped

    return f"{stripped}."


def _apply_replacements(
    text: str,
    replacements: dict[str, str],
    issue_type: str,
    message_suffix: str,
) -> tuple[str, list[ReportQualityIssue]]:
    corrected = text
    issues: list[ReportQualityIssue] = []

    for incorrect, replacement in replacements.items():
        pattern = re.compile(
            rf"\b{re.escape(incorrect)}\b",
            flags=re.IGNORECASE,
        )

        if not pattern.search(corrected):
            continue

        corrected = pattern.sub(replacement, corrected)

        issues.append(
            ReportQualityIssue(
                type=issue_type,
                message=f"Changed '{incorrect}' {message_suffix}.",
                suggestion=replacement,
            ),
        )

    return corrected, issues


def _extract_first_name(student_name: str | None) -> str:
    """
    Return only the pupil's first name.

    The name must come from the explicit student_name field. Teacher notes
    must never be interpreted as a pupil name.
    """
    if not student_name:
        return "The student"

    cleaned = " ".join(student_name.strip().split())

    if not cleaned:
        return "The student"

    first_name = cleaned.split(" ", maxsplit=1)[0]
    first_name = first_name.strip(" ,.;:!?()[]{}")

    return first_name or "The student"


def _normalise_optional_text(value: str | None) -> str | None:
    if value is None:
        return None

    cleaned = " ".join(value.strip().split())

    return cleaned or None


@router.post(
    "/check-comment",
    response_model=ReportQualityCheckResponse,
)
async def check_report_comment(
    payload: ReportQualityCheckRequest,
    current_user: User = Depends(get_current_user),
) -> ReportQualityCheckResponse:
    # Authentication is intentionally required, even though the user record
    # is not otherwise needed by this endpoint.
    _ = current_user

    original = payload.comment.strip()
    corrected = original
    issues: list[ReportQualityIssue] = []

    corrected, spelling_issues = _apply_replacements(
        corrected,
        UK_SPELLING_REPLACEMENTS,
        "uk_spelling",
        "to UK spelling",
    )
    issues.extend(spelling_issues)

    corrected, typo_issues = _apply_replacements(
        corrected,
        COMMON_TYPO_REPLACEMENTS,
        "spelling",
        "to the correct spelling",
    )
    issues.extend(typo_issues)

    corrected, phrase_issues = _apply_replacements(
        corrected,
        COMMON_PHRASE_FIXES,
        "phrasing",
        "to improve phrasing",
    )
    issues.extend(phrase_issues)

    capitalised = _capitalise_first_letter(corrected)

    if capitalised != corrected:
        issues.append(
            ReportQualityIssue(
                type="capitalisation",
                message="Capitalised the first letter of the comment.",
                suggestion=capitalised,
            ),
        )
        corrected = capitalised

    punctuated = _ensure_final_punctuation(corrected)

    if punctuated != corrected:
        issues.append(
            ReportQualityIssue(
                type="punctuation",
                message="Added final punctuation.",
                suggestion=punctuated,
            ),
        )
        corrected = punctuated

    if len(corrected.split()) < 15:
        issues.append(
            ReportQualityIssue(
                type="length",
                message="The report comment may be too short.",
                suggestion=(
                    "Consider adding specific evidence, progress and "
                    "a clear next step."
                ),
            ),
        )

    corrected_lower = corrected.lower()

    has_next_step = any(
        phrase in corrected_lower
        for phrase in (
            "needs to",
            "next step",
            "should",
            "could improve",
            "to make further progress",
        )
    )

    if not has_next_step:
        issues.append(
            ReportQualityIssue(
                type="target",
                message="No clear next step was detected.",
                suggestion=("Consider adding a focused next step for improvement."),
            ),
        )

    return ReportQualityCheckResponse(
        original_comment=original,
        corrected_comment=corrected,
        issues=issues,
    )


@router.post(
    "/generate-from-notes",
    response_model=ReportNotesGenerateResponse,
)
async def generate_report_from_notes(
    payload: ReportNotesGenerateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ReportNotesGenerateResponse:
    notes = payload.notes.strip()

    if not notes:
        raise HTTPException(
            status_code=400,
            detail="Teacher notes are required to generate a report.",
        )

    student_first_name = _extract_first_name(payload.student_name)
    subject = _normalise_optional_text(payload.subject)
    year_group = _normalise_optional_text(payload.year_group)

    similar_reports: list[str] = []

    if current_user.school_id is not None:
        memories = await find_similar_report_memory(
            db,
            school_id=current_user.school_id,
            teacher_id=current_user.id,
            subject=subject or "",
            year_group=year_group,
            teacher_notes=notes,
            limit=5,
        )

        similar_reports = [
            memory.final_report.strip()
            for memory in memories
            if memory.final_report and memory.final_report.strip()
        ]

    try:
        generated_comment = generate_report_comment(
            notes=notes,
            student_name=student_first_name,
            subject=subject,
            year_group=year_group,
            similar_reports=similar_reports,
        ).strip()
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    if not generated_comment:
        raise HTTPException(
            status_code=500,
            detail="The report writer returned an empty report.",
        )

    return ReportNotesGenerateResponse(
        notes=notes,
        generated_comment=generated_comment,
    )
