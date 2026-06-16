from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.report_quality import (
    ReportQualityCheckRequest,
    ReportQualityCheckResponse,
    ReportQualityIssue,
)

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


def _capitalise_first_letter(text: str) -> str:
    stripped = text.strip()

    if not stripped:
        return stripped

    return stripped[0].upper() + stripped[1:]


def _ensure_final_punctuation(text: str) -> str:
    stripped = text.strip()

    if not stripped:
        return stripped

    if stripped[-1] in ".!?":
        return stripped

    return f"{stripped}."


def _apply_uk_spelling(text: str) -> tuple[str, list[ReportQualityIssue]]:
    corrected = text
    issues: list[ReportQualityIssue] = []

    for incorrect, correct in UK_SPELLING_REPLACEMENTS.items():
        if incorrect in corrected:
            corrected = corrected.replace(incorrect, correct)

            issues.append(
                ReportQualityIssue(
                    type="uk_spelling",
                    message=f"Changed '{incorrect}' to UK spelling.",
                    suggestion=correct,
                ),
            )

    return corrected, issues


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

    corrected, spelling_issues = _apply_uk_spelling(corrected)
    issues.extend(spelling_issues)

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
                suggestion="Consider adding specific evidence, progress and a clear next step.",
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
