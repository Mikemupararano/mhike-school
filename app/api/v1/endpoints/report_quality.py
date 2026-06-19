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


def _get_first_name(student_name: str) -> str:
    cleaned = student_name.strip()

    if not cleaned or cleaned.lower() == "the student":
        return "The student"

    return cleaned.split()[0]


def _join_items(items: list[str]) -> str:
    unique_items: list[str] = []

    for item in items:
        if item and item not in unique_items:
            unique_items.append(item)

    if not unique_items:
        return ""

    if len(unique_items) == 1:
        return unique_items[0]

    return ", ".join(unique_items[:-1]) + f" and {unique_items[-1]}"


def _split_generation_notes(notes: str) -> tuple[str, str]:
    lower_notes = notes.lower()

    teacher_marker = "teacher notes:"
    work_marker = "work covered:"

    if teacher_marker in lower_notes:
        marker_index = lower_notes.index(teacher_marker)
        work_covered = notes[:marker_index]
        teacher_notes = notes[marker_index + len(teacher_marker) :]

        if work_marker in work_covered.lower():
            work_covered = work_covered.split(":", maxsplit=1)[-1]

        return work_covered.strip(), teacher_notes.strip()

    if work_marker in lower_notes:
        return notes.split(":", maxsplit=1)[-1].strip(), ""

    return notes.strip(), notes.strip()


def _detect_topics(lower_notes: str) -> list[str]:
    topic_map = {
        "rates of reaction": "rates of reaction",
        "rate of reaction": "rates of reaction",
        "reaction rate": "rates of reaction",
        "reaction rates": "rates of reaction",
        "organic chemistry": "organic chemistry",
        "alkanes": "organic chemistry",
        "alkenes": "organic chemistry",
        "alcohols": "organic chemistry",
        "carboxylic": "organic chemistry",
        "polymers": "organic chemistry",
        "crude oil": "organic chemistry",
        "chemical changes": "chemical changes",
        "energy changes": "energy changes",
        "bond energy": "energy changes",
        "exothermic": "energy changes",
        "endothermic": "energy changes",
        "equilibria": "equilibria",
        "equilibrium": "equilibria",
        "reversible reactions": "reversible reactions",
        "bonding": "bonding",
        "atomic structure": "atomic structure",
        "periodic table": "the periodic table",
        "electrolysis": "electrolysis",
        "acids": "acids and alkalis",
        "alkalis": "acids and alkalis",
        "moles": "chemical calculations",
        "calculations": "chemical calculations",
        "calculation": "chemical calculations",
        "titration": "quantitative chemistry",
        "practical": "practical work",
        "experiment": "practical work",
    }

    topics: list[str] = []

    for keyword, topic in topic_map.items():
        if keyword in lower_notes and topic not in topics:
            topics.append(topic)

    return topics


def _detect_attitude_sentence(first_name: str, lower_notes: str) -> str | None:
    qualities: list[str] = []

    if (
        "hard worker" in lower_notes
        or "hard working" in lower_notes
        or "hardworking" in lower_notes
    ):
        qualities.append("works hard")

    if "asks questions" in lower_notes or "asking questions" in lower_notes:
        qualities.append("asks thoughtful questions to deepen understanding")

    if "engaged" in lower_notes or "engagement" in lower_notes:
        qualities.append("engages well with learning")

    if "independent" in lower_notes or "independently" in lower_notes:
        qualities.append("works with increasing independence")

    if "resilient" in lower_notes or "resilience" in lower_notes:
        qualities.append("shows resilience when tackling challenging work")

    if not qualities:
        return None

    learner = "The student" if first_name == "The student" else first_name

    return f"{learner} { _join_items(qualities[:3]) }."


def _detect_achievement_sentence(first_name: str, lower_notes: str) -> str | None:
    achievements: list[str] = []

    if "confident" in lower_notes or "confidence" in lower_notes:
        achievements.append("grown in confidence")

    if "passed tests" in lower_notes or "test" in lower_notes:
        achievements.append("performed well in recent assessment work")

    if "good progress" in lower_notes or "positive progress" in lower_notes:
        achievements.append("made positive progress across the course")

    if "excellent" in lower_notes:
        achievements.append("produced work of an excellent standard")

    if "improved" in lower_notes or "improvement" in lower_notes:
        achievements.append("shown clear improvement over time")

    if "knowledge" in lower_notes or "understanding" in lower_notes:
        achievements.append("developed secure subject knowledge")

    if "answers" in lower_notes or "written" in lower_notes:
        achievements.append("improved the quality of written responses")

    if "practical" in lower_notes or "experiment" in lower_notes:
        achievements.append("developed practical and investigative skills")

    if "exam question" in lower_notes or "exam-style" in lower_notes:
        achievements.append("made progress with examination-style questions")

    if not achievements:
        return None

    return (
        f"This has helped {first_name.lower() if first_name == 'The student' else first_name} "
        f"to {_join_items(achievements[:3])}."
    )


def _detect_next_steps(lower_notes: str) -> list[str]:
    next_steps: list[str] = []

    if "revision guide" in lower_notes:
        next_steps.append(
            "use the revision guide regularly to consolidate key knowledge",
        )

    if "exam question" in lower_notes or "exam-style" in lower_notes:
        next_steps.append("continue practising examination-style questions")

    if "application" in lower_notes or "apply" in lower_notes:
        next_steps.append(
            "focus on applying knowledge accurately to unfamiliar questions",
        )

    if (
        "calculation" in lower_notes
        or "calculations" in lower_notes
        or "maths" in lower_notes
    ):
        next_steps.append(
            "show clear working in calculations and check units carefully",
        )

    if "detail" in lower_notes or "explain" in lower_notes:
        next_steps.append(
            "include more precise scientific detail in written explanations",
        )

    if "recall" in lower_notes or "remember" in lower_notes:
        next_steps.append("strengthen recall of key facts and definitions")

    if "revise" in lower_notes or "revision" in lower_notes:
        next_steps.append("maintain a regular revision routine")

    if "six-mark" in lower_notes or "6-mark" in lower_notes:
        next_steps.append(
            "structure extended responses carefully and include sufficient detail",
        )

    return next_steps


def _infer_next_step_from_topics(topics: list[str]) -> str:
    if "chemical calculations" in topics:
        return "show clear working in calculations and check units carefully"

    if "rates of reaction" in topics:
        return (
            "practise explaining how changes in conditions affect reaction rate "
            "using precise scientific language"
        )

    if "organic chemistry" in topics:
        return "secure the key reactions and terminology used in organic chemistry"

    if "acids and alkalis" in topics:
        return "practise applying key ideas about acids and alkalis to unfamiliar questions"

    if "practical work" in topics:
        return (
            "continue linking practical observations to accurate scientific conclusions"
        )

    return "continue to review class notes and practise applying knowledge"


def _generate_report_from_notes_text(
    *,
    notes: str,
    student_name: str,
    subject: str | None,
    year_group: str | None,
) -> str:
    if len(notes.split()) < 4:
        raise HTTPException(
            status_code=400,
            detail="Please enter more detailed teacher notes before generating a report.",
        )

    work_covered_text, teacher_notes_text = _split_generation_notes(notes)

    first_name = _get_first_name(student_name)
    subject_name = subject.strip() if subject and subject.strip() else "the subject"
    year_group_name = (
        year_group.strip() if year_group and year_group.strip() else "this year"
    )

    work_lower = work_covered_text.lower()
    teacher_lower = teacher_notes_text.lower()
    combined_lower = notes.lower()

    topics = _detect_topics(work_lower) or _detect_topics(combined_lower)

    next_steps = _detect_next_steps(teacher_lower) or _detect_next_steps(
        combined_lower,
    )

    if not next_steps:
        next_steps.append(_infer_next_step_from_topics(topics))

    learner = "the student" if first_name == "The student" else first_name

    opening_sentence = (
        f"The student has made good progress in {subject_name} during {year_group_name}."
        if first_name == "The student"
        else f"{first_name} has made good progress in {subject_name} during {year_group_name}."
    )

    topic_sentence = ""
    if topics:
        topic_sentence = (
            f" Through the study of {_join_items(topics[:4])}, "
            f"{learner} has strengthened subject knowledge and confidence."
        )

    attitude_sentence = _detect_attitude_sentence(first_name, teacher_lower)

    if attitude_sentence is None:
        attitude_sentence = _detect_attitude_sentence(first_name, combined_lower)

    achievement_sentence = _detect_achievement_sentence(first_name, teacher_lower)

    if achievement_sentence is None:
        achievement_sentence = _detect_achievement_sentence(
            first_name,
            combined_lower,
        )

    if achievement_sentence is None and not topic_sentence:
        achievement_sentence = (
            f"{first_name if first_name != 'The student' else 'The student'} "
            "has made positive progress in lessons."
        )

    next_step_sentence = (
        f" To build on this progress, {learner} should {next_steps[0]}."
    )

    parts = [
        opening_sentence,
        topic_sentence,
        attitude_sentence,
        achievement_sentence,
        next_step_sentence,
    ]

    return " ".join(part.strip() for part in parts if part).strip()


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

    generated_comment = _generate_report_from_notes_text(
        notes=notes,
        student_name=student_name,
        subject=payload.subject,
        year_group=payload.year_group,
    )

    return ReportNotesGenerateResponse(
        notes=notes,
        generated_comment=generated_comment,
    )
