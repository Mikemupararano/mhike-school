from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.report_quality import (
    ReportNotesGenerateRequest,
    ReportNotesGenerateResponse,
    ReportQualityCheckRequest,
    ReportQualityCheckResponse,
    ReportQualityIssue,
)
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
    return stripped[0].upper() + stripped[1:] if stripped else stripped


def _ensure_final_punctuation(text: str) -> str:
    stripped = text.strip()

    if not stripped:
        return stripped

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

    for incorrect, correct in replacements.items():
        if incorrect in corrected:
            corrected = corrected.replace(incorrect, correct)
            issues.append(
                ReportQualityIssue(
                    type=issue_type,
                    message=f"Changed '{incorrect}' {message_suffix}.",
                    suggestion=correct,
                ),
            )

    return corrected, issues


def _extract_student_name(notes: str, fallback: str | None) -> str:
    if fallback and fallback.strip():
        return fallback.strip()

    first_part = notes.split(",", maxsplit=1)[0].strip()

    if first_part:
        return first_part

    return "The student"


@router.post(
    "/check-comment",
    response_model=ReportQualityCheckResponse,
)
async def check_report_comment(
    payload: ReportQualityCheckRequest,
    current_user: User = Depends(get_current_user),
) -> ReportQualityCheckResponse:
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
                    "Consider adding specific evidence, progress and a clear next step."
                ),
            ),
        )

    if "needs to" not in corrected.lower() and "next step" not in corrected.lower():
        issues.append(
            ReportQualityIssue(
                type="target",
                message="No clear next step was detected.",
                suggestion="Consider adding a focused next step for improvement.",
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
    current_user: User = Depends(get_current_user),
) -> ReportNotesGenerateResponse:
    notes = payload.notes.strip()

    student_name = _extract_student_name(
        notes,
        payload.student_name,
    )

    try:
        generated_comment = generate_report_comment(
            notes=notes,
            student_name=student_name,
            subject=payload.subject,
            year_group=payload.year_group,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    return ReportNotesGenerateResponse(
        notes=notes,
        generated_comment=generated_comment,
    )
