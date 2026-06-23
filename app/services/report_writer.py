import random
import re

REPORT_OPENINGS = [
    "{name} has continued to make positive progress in {subject} throughout {year_group}.",
    "{name} has approached {subject} with a positive attitude and has made steady progress across the course.",
    "{name} has worked consistently well this year and developed a stronger understanding of key concepts in {subject}.",
    "{name} has shown increasing confidence in {subject} and has made good progress in developing subject knowledge and skills.",
    "{name} has engaged positively with lessons and has made encouraging progress throughout the year.",
    "{name} has demonstrated a good commitment to learning and has responded well to the challenges presented in {subject}.",
    "{name} has worked hard throughout the course and has made clear progress in {subject}.",
    "{name} has shown a mature approach to learning and continues to build knowledge and confidence in {subject}.",
    "{name} has made steady progress this year and has developed a more secure understanding of the topics studied in {subject}.",
    "{name} has embraced opportunities to develop skills and has made positive progress in {subject} over the course of the year.",
]

SUBJECT_TOPIC_MAPS = {
    "chemistry": {
        "atomic structure": "atomic structure",
        "isotopes": "isotopes",
        "separating mixtures": "separating mixtures",
        "reaction rates": "reaction rates",
        "rates of reaction": "reaction rates",
        "rate of reaction": "reaction rates",
        "reaction rate": "reaction rates",
        "reversible reactions": "reversible reactions",
        "making salts": "making salts",
        "organic": "organic chemistry",
        "alkanes": "organic chemistry",
        "alkenes": "organic chemistry",
        "alcohols": "organic chemistry",
        "acids": "acids and alkalis",
        "alkalis": "acids and alkalis",
        "moles": "chemical calculations",
        "calculations": "chemical calculations",
        "equilibrium": "equilibria",
        "equilibria": "equilibria",
        "bonding": "bonding",
        "electrolysis": "electrolysis",
        "titration": "quantitative chemistry",
    },
    "biology": {
        "cells": "cell biology",
        "microscopy": "microscopy",
        "enzymes": "enzymes",
        "photosynthesis": "photosynthesis",
        "respiration": "respiration",
        "genetics": "genetics",
        "inheritance": "inheritance",
        "ecology": "ecology",
        "evolution": "evolution",
        "homeostasis": "homeostasis",
        "infection": "infection and response",
    },
    "physics": {
        "forces": "forces",
        "motion": "motion",
        "energy": "energy",
        "waves": "waves",
        "electricity": "electricity",
        "circuits": "electricity",
        "magnetism": "magnetism",
        "radioactivity": "radioactivity",
        "moments": "moments",
        "pressure": "pressure",
        "space": "space physics",
    },
    "english": {
        "poetry": "poetry analysis",
        "shakespeare": "Shakespeare",
        "macbeth": "Macbeth",
        "essay": "essay writing",
        "creative writing": "creative writing",
        "language analysis": "language analysis",
        "reading": "reading comprehension",
        "literature": "literature study",
        "writing": "written communication",
        "grammar": "grammar and expression",
    },
    "geography": {
        "rivers": "rivers",
        "coasts": "coasts",
        "tectonics": "tectonic hazards",
        "earthquakes": "tectonic hazards",
        "volcanoes": "tectonic hazards",
        "rainforests": "rainforests",
        "urbanisation": "urbanisation",
        "fieldwork": "geographical fieldwork",
        "climate": "climate change",
        "development": "development",
        "population": "population",
    },
    "computer science": {
        "python": "Python programming",
        "programming": "programming",
        "algorithms": "algorithms",
        "databases": "databases",
        "networks": "networks",
        "cyber": "cyber security",
        "binary": "binary and data representation",
        "logic": "logic gates",
        "html": "web development",
        "css": "web development",
    },
    "art": {
        "drawing": "drawing skills",
        "painting": "painting techniques",
        "colour": "colour theory",
        "artist research": "artist research",
        "portfolio": "portfolio development",
        "composition": "composition",
        "sketchbook": "sketchbook development",
        "mixed media": "mixed media",
    },
    "religious studies": {
        "christianity": "Christianity",
        "islam": "Islam",
        "judaism": "Judaism",
        "ethics": "ethical issues",
        "morality": "morality",
        "beliefs": "religious beliefs",
        "philosophy": "philosophical ideas",
        "peace": "peace and conflict",
        "justice": "justice",
    },
    "history": {
        "medicine": "medicine through time",
        "war": "war and conflict",
        "cold war": "the Cold War",
        "tudors": "the Tudors",
        "normans": "the Normans",
        "empire": "empire",
        "source": "source analysis",
        "interpretation": "historical interpretations",
    },
    "mathematics": {
        "algebra": "algebra",
        "geometry": "geometry",
        "trigonometry": "trigonometry",
        "graphs": "graphs",
        "statistics": "statistics",
        "probability": "probability",
        "ratio": "ratio and proportion",
        "number": "number skills",
    },
}

SUBJECT_TOPIC_SENTENCES = {
    "chemistry": "Through the study of {topics}, {learner} has strengthened scientific knowledge and confidence.",
    "biology": "Through work on {topics}, {learner} has developed a stronger understanding of biological concepts and processes.",
    "physics": "Through the study of {topics}, {learner} has strengthened problem-solving skills and understanding of physical principles.",
    "english": "Through work on {topics}, {learner} has developed analytical, reading and written communication skills.",
    "geography": "Through the study of {topics}, {learner} has developed geographical knowledge and the ability to explain processes and places.",
    "computer science": "Through work on {topics}, {learner} has developed computational thinking and problem-solving skills.",
    "art": "Through work on {topics}, {learner} has developed creative confidence, technical control and visual communication skills.",
    "religious studies": "Through the study of {topics}, {learner} has developed understanding of beliefs, ethics and different viewpoints.",
    "history": "Through work on {topics}, {learner} has developed historical knowledge, source skills and analytical thinking.",
    "mathematics": "Through work on {topics}, {learner} has developed mathematical fluency, accuracy and problem-solving confidence.",
}

DEFAULT_TOPIC_SENTENCE = (
    "Through work on {topics}, {learner} has strengthened subject knowledge, "
    "confidence and understanding."
)

CURRICULUM_FILLER_PHRASES = [
    "in gcse chemistry",
    "in gcse biology",
    "in gcse physics",
    "in gcse english",
    "in gcse geography",
    "in gcse computer science",
    "in gcse mathematics",
    "in gcse maths",
    "in chemistry",
    "in biology",
    "in physics",
    "in english",
    "in geography",
    "the pupils have covered",
    "pupils have covered",
    "students have covered",
    "the students have covered",
    "the pupils have completed",
    "pupils have completed",
    "students have completed",
    "the students have completed",
    "the following topics:",
    "the following topics",
    "they have also sat end-of-topic tests",
    "they have sat end-of-topic tests",
    "also they have sat end-of-topic tests",
    "they have also completed end-of-topic tests",
    "they have completed end-of-topic tests",
    "they have also completed assessments",
    "they have completed assessments",
    "end-of-topic tests",
    "end of topic tests",
    "end-of-topic assessments",
    "end of topic assessments",
]

MEMORY_EXCLUSION_PHRASES = [
    "to build on this progress",
    "next step",
    "should",
    "needs to",
    "must",
    "work covered",
    "teacher notes",
]


def normalise_subject(subject: str | None) -> str:
    if not subject:
        return "default"

    subject_lower = subject.lower().strip()

    if "chemistry" in subject_lower:
        return "chemistry"
    if "biology" in subject_lower:
        return "biology"
    if "physics" in subject_lower:
        return "physics"
    if "english" in subject_lower:
        return "english"
    if "geography" in subject_lower:
        return "geography"
    if "computer" in subject_lower or "computing" in subject_lower:
        return "computer science"
    if "art" in subject_lower:
        return "art"
    if "religious" in subject_lower or subject_lower in {"rs", "re"}:
        return "religious studies"
    if "history" in subject_lower:
        return "history"
    if "math" in subject_lower:
        return "mathematics"

    return "default"


def get_first_name(student_name: str) -> str:
    cleaned = student_name.strip()

    if not cleaned or cleaned.lower() == "the student":
        return "The student"

    return cleaned.split()[0]


def join_items(items: list[str]) -> str:
    unique_items: list[str] = []

    for item in items:
        if item and item not in unique_items:
            unique_items.append(item)

    if not unique_items:
        return ""

    if len(unique_items) == 1:
        return unique_items[0]

    return ", ".join(unique_items[:-1]) + f" and {unique_items[-1]}"


def split_generation_notes(notes: str) -> tuple[str, str]:
    """Split combined frontend notes into work-covered and teacher-note sections.

    The frontend may send either order, for example:
    - Teacher notes: ...\n\nWork covered: ...
    - Work covered: ...\n\nTeacher notes: ...

    This parser keeps the two sections separate so curriculum context is not
    mistaken for pupil-specific evidence.
    """

    markers = list(
        re.finditer(
            r"(?im)^(work covered|teacher notes):\s*",
            notes,
        ),
    )

    if not markers:
        cleaned = notes.strip()
        return "", cleaned

    sections: dict[str, str] = {}

    for index, marker in enumerate(markers):
        label = marker.group(1).lower()
        start = marker.end()
        end = markers[index + 1].start() if index + 1 < len(markers) else len(notes)
        sections[label] = notes[start:end].strip()

    return (
        sections.get("work covered", "").strip(),
        sections.get("teacher notes", "").strip(),
    )


def clean_work_covered_text(text: str) -> str:
    cleaned = text.lower()

    cleaned = re.sub(
        r"\bin\s+(aqa|ocr|edexcel)\s+gcse\s+[a-z ]+?,",
        "",
        cleaned,
    )
    cleaned = re.sub(
        r"\b(aqa|ocr|edexcel)\s+gcse\s+[a-z ]+?,",
        "",
        cleaned,
    )
    cleaned = re.sub(
        r"\bin\s+(aqa|ocr|edexcel)\s+[a-z ]+?,",
        "",
        cleaned,
    )
    cleaned = re.sub(
        r"\b(aqa|ocr|edexcel)\s+[a-z ]+?,",
        "",
        cleaned,
    )

    for phrase in CURRICULUM_FILLER_PHRASES:
        cleaned = cleaned.replace(phrase, "")

    cleaned = cleaned.replace(".", ",")
    cleaned = cleaned.replace(";", ",")
    cleaned = cleaned.replace(" and ", ",")

    while ",," in cleaned:
        cleaned = cleaned.replace(",,", ",")

    return cleaned.strip(" ,.:")


def detect_topics(text: str, subject_key: str) -> list[str]:
    topic_map = SUBJECT_TOPIC_MAPS.get(subject_key, {})
    topics: list[str] = []

    cleaned_text = clean_work_covered_text(text)

    for keyword, topic in topic_map.items():
        if keyword in cleaned_text and topic not in topics:
            topics.append(topic)

    if topics:
        return topics

    parts = [part.strip() for part in cleaned_text.split(",") if len(part.strip()) > 2]

    unique_parts: list[str] = []

    for part in parts:
        if part not in unique_parts:
            unique_parts.append(part)

    return unique_parts[:5]


def build_topic_sentence(
    *,
    topics: list[str],
    learner: str,
    subject_key: str,
) -> str:
    if not topics:
        return ""

    template = SUBJECT_TOPIC_SENTENCES.get(subject_key, DEFAULT_TOPIC_SENTENCE)

    return template.format(
        topics=join_items(topics[:5]),
        learner=learner,
    )


def clean_teacher_notes_text(text: str, first_name: str) -> str:
    cleaned = text.strip()

    if not cleaned:
        return ""

    if first_name != "The student":
        cleaned = re.sub(
            rf"^\s*{re.escape(first_name)}\s*[:.,-]*\s*",
            "",
            cleaned,
            flags=re.IGNORECASE,
        )

    cleaned = cleaned.strip(" .")
    cleaned = re.sub(r"\s+", " ", cleaned)

    return cleaned


def build_teacher_evidence_sentence(
    *,
    first_name: str,
    teacher_notes: str,
) -> str:
    """Create a pupil-specific evidence sentence from the teacher's notes.

    This deliberately uses the teacher notes directly, because these are the
    most reliable evidence for the individual pupil. It avoids copying frontend
    labels such as "Teacher notes:" into the report.
    """

    cleaned = clean_teacher_notes_text(
        teacher_notes,
        first_name,
    )

    if not cleaned:
        return ""

    learner = "The student" if first_name == "The student" else first_name
    lower_cleaned = cleaned.lower()

    strengths: list[str] = []

    if "hardworking" in lower_cleaned or "hard working" in lower_cleaned:
        strengths.append("is hardworking")

    if "well behaved" in lower_cleaned or "well-behaved" in lower_cleaned:
        strengths.append("is well behaved")

    if "punctual" in lower_cleaned:
        strengths.append("is punctual")

    if "homework" in lower_cleaned and (
        "on time" in lower_cleaned
        or "completed" in lower_cleaned
        or "completes" in lower_cleaned
    ):
        strengths.append("completes homework on time")

    if "engaged" in lower_cleaned or "class discussion" in lower_cleaned:
        strengths.append("engages positively in class")

    if "practical" in lower_cleaned:
        strengths.append("contributes well to practical work")

    assessment_sentence = ""
    percentage_match = re.search(
        r"(\d{1,3})\s*%\s*(?:in|on)?\s*([^.,;]*)",
        cleaned,
        flags=re.IGNORECASE,
    )

    if percentage_match:
        percentage = percentage_match.group(1)
        assessment_context = percentage_match.group(2).strip()
        assessment_context = assessment_context or "recent assessment work"
        assessment_sentence = (
            f" {learner} achieved {percentage}% in {assessment_context}."
        )

    if strengths:
        return f"{learner} {join_items(strengths)}.{assessment_sentence}".strip()

    if cleaned.endswith((".", "!", "?")):
        return f"{learner} has shown that {cleaned}"

    return f"{learner} has shown that {cleaned}."


def detect_attitude_sentence(first_name: str, lower_notes: str) -> str | None:
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

    if "creative" in lower_notes or "creativity" in lower_notes:
        qualities.append("shows creativity and originality")

    if "organised" in lower_notes or "organized" in lower_notes:
        qualities.append("is organised and prepared for learning")

    if not qualities:
        return None

    learner = "The student" if first_name == "The student" else first_name

    return f"{learner} {join_items(qualities[:3])}."


def detect_achievement_sentence(first_name: str, lower_notes: str) -> str | None:
    achievements: list[str] = []

    if "confident" in lower_notes or "confidence" in lower_notes:
        achievements.append("grown in confidence")

    if (
        "passed tests" in lower_notes
        or "excellent assessment" in lower_notes
        or "strong assessment" in lower_notes
        or "good assessment" in lower_notes
        or "high test score" in lower_notes
        or "strong test score" in lower_notes
    ):
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

    if "analysis" in lower_notes or "analytical" in lower_notes:
        achievements.append("developed analytical skills")

    if "evaluation" in lower_notes or "evaluate" in lower_notes:
        achievements.append("improved evaluative skills")

    if "coding" in lower_notes or "programming" in lower_notes:
        achievements.append("developed programming skills")

    if "composition" in lower_notes or "portfolio" in lower_notes:
        achievements.append("developed creative and technical skills")

    if not achievements:
        return None

    learner = "the student" if first_name == "The student" else first_name

    return f"This has helped {learner} to {join_items(achievements[:3])}."


def detect_next_steps(lower_notes: str, subject_key: str) -> list[str]:
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
        next_steps.append("include more precise detail in written explanations")

    if "recall" in lower_notes or "remember" in lower_notes:
        next_steps.append("strengthen recall of key facts and definitions")

    if "revise" in lower_notes or "revision" in lower_notes:
        next_steps.append("maintain a regular revision routine")

    if "six-mark" in lower_notes or "6-mark" in lower_notes:
        next_steps.append(
            "structure extended responses carefully and include sufficient detail",
        )

    if next_steps:
        return next_steps

    subject_defaults = {
        "english": "continue developing clear paragraph structure and support ideas with precise textual evidence",
        "geography": "continue using accurate geographical terminology and evidence when explaining processes",
        "computer science": "continue practising programming problems and explaining algorithms clearly",
        "art": "continue refining observational detail and recording development clearly in the sketchbook",
        "religious studies": "continue using evidence and examples to explain different beliefs and viewpoints",
        "history": "continue supporting judgements with precise evidence and clear explanation",
        "mathematics": "continue practising multi-step problems and checking working carefully",
        "biology": "continue using key terminology accurately when explaining biological processes",
        "physics": "continue applying equations carefully and explaining physical principles clearly",
        "chemistry": "continue applying chemical ideas accurately to unfamiliar questions",
    }

    return [
        subject_defaults.get(
            subject_key,
            "continue to review class notes and practise applying knowledge",
        ),
    ]


def infer_next_step_from_topics(topics: list[str], subject_key: str) -> str:
    if subject_key == "chemistry":
        if "chemical calculations" in topics:
            return "show clear working in calculations and check units carefully"

        if "reaction rates" in topics:
            return (
                "practise explaining how changes in conditions affect reaction "
                "rate using precise scientific language"
            )

    if subject_key == "english":
        return (
            "continue developing clear paragraph structure and support ideas "
            "with precise textual evidence"
        )

    if subject_key == "geography":
        return (
            "continue using accurate geographical terminology and evidence "
            "when explaining processes"
        )

    if subject_key == "computer science":
        return (
            "continue practising programming problems and explaining algorithms clearly"
        )

    if subject_key == "art":
        return (
            "continue refining observational detail and recording development "
            "clearly in the sketchbook"
        )

    if subject_key == "religious studies":
        return (
            "continue using evidence and examples to explain different beliefs "
            "and viewpoints"
        )

    if subject_key == "history":
        return (
            "continue supporting judgements with precise evidence and clear explanation"
        )

    if subject_key == "mathematics":
        return "continue practising multi-step problems and checking working carefully"

    if subject_key == "biology":
        return "continue using key terminology accurately when explaining biological processes"

    if subject_key == "physics":
        return "continue applying equations carefully and explaining physical principles clearly"

    return "continue to review class notes and practise applying knowledge"


def extract_memory_phrases(
    similar_reports: list[str] | None,
) -> list[str]:
    if not similar_reports:
        return []

    phrases: list[str] = []

    for report in similar_reports:
        for raw_sentence in report.split("."):
            sentence = raw_sentence.strip()

            if len(sentence) < 35:
                continue

            lower_sentence = sentence.lower()

            if any(excluded in lower_sentence for excluded in MEMORY_EXCLUSION_PHRASES):
                continue

            if sentence not in phrases:
                phrases.append(sentence)

            if len(phrases) >= 20:
                return phrases

    return phrases


def choose_memory_sentence(
    similar_reports: list[str] | None,
    *,
    teacher_notes: str,
    first_name: str,
    student_name: str,
    learner: str,
    used_phrases: set[str] | None = None,
) -> str | None:
    phrases = extract_memory_phrases(similar_reports)

    if not phrases:
        return None

    used_phrases = used_phrases or set()

    keywords = {
        word.strip(".,!?").lower()
        for word in teacher_notes.split()
        if len(word.strip(".,!?")) >= 5
    }

    scored: list[tuple[int, str]] = []

    for phrase in phrases:
        phrase_lower = phrase.lower()

        score = sum(1 for keyword in keywords if keyword in phrase_lower)

        if phrase_lower in used_phrases:
            score -= 100

        scored.append((score, phrase))

    scored.sort(
        key=lambda item: item[0],
        reverse=True,
    )

    top_candidates = [phrase for score, phrase in scored[:5] if score > -100]

    if not top_candidates:
        return None

    selected = random.choice(top_candidates).strip()

    selected = selected.replace(student_name, learner)
    selected = selected.replace(first_name, learner)

    if not selected.endswith("."):
        selected += "."

    return selected


def select_opening_sentence(
    *,
    first_name: str,
    subject_name: str,
    year_group_name: str,
) -> str:
    if first_name == "The student":
        return (
            f"The student has made good progress in {subject_name} during "
            f"{year_group_name}."
        )

    template = random.choice(REPORT_OPENINGS)

    return template.format(
        name=first_name,
        subject=subject_name,
        year_group=year_group_name,
    )


def generate_report_comment(
    *,
    notes: str,
    student_name: str,
    subject: str | None,
    year_group: str | None,
    similar_reports: list[str] | None = None,
    used_phrases: set[str] | None = None,
) -> str:
    if len(notes.split()) < 4:
        raise ValueError(
            "Please enter more detailed teacher notes before generating a report.",
        )

    work_covered_text, teacher_notes_text = split_generation_notes(notes)

    first_name = get_first_name(student_name)
    subject_name = subject.strip() if subject and subject.strip() else "the subject"
    year_group_name = (
        year_group.strip() if year_group and year_group.strip() else "this year"
    )

    subject_key = normalise_subject(subject_name)

    work_lower = work_covered_text.lower()
    teacher_lower = teacher_notes_text.lower()
    combined_lower = notes.lower()

    topics = detect_topics(
        work_lower,
        subject_key,
    ) or detect_topics(
        combined_lower,
        subject_key,
    )

    next_steps = detect_next_steps(
        teacher_lower,
        subject_key,
    ) or detect_next_steps(
        combined_lower,
        subject_key,
    )

    if not next_steps:
        next_steps.append(
            infer_next_step_from_topics(
                topics,
                subject_key,
            ),
        )

    learner = "the student" if first_name == "The student" else first_name

    opening_sentence = select_opening_sentence(
        first_name=first_name,
        subject_name=subject_name,
        year_group_name=year_group_name,
    )

    topic_sentence = build_topic_sentence(
        topics=topics,
        learner=learner,
        subject_key=subject_key,
    )

    attitude_sentence = detect_attitude_sentence(
        first_name,
        teacher_lower,
    )

    if attitude_sentence is None:
        attitude_sentence = detect_attitude_sentence(
            first_name,
            combined_lower,
        )

    achievement_sentence = detect_achievement_sentence(
        first_name,
        teacher_lower,
    )

    if achievement_sentence is None:
        achievement_sentence = detect_achievement_sentence(
            first_name,
            combined_lower,
        )

    teacher_evidence_sentence = build_teacher_evidence_sentence(
        first_name=first_name,
        teacher_notes=teacher_notes_text,
    )

    # Keep report-memory phrasing disabled for now. It can make reports sound
    # generic or repetitive before the core teacher-note workflow is stable.
    memory_sentence = None

    if (
        achievement_sentence is None
        and not topic_sentence
        and not teacher_evidence_sentence
        and memory_sentence is None
    ):
        achievement_sentence = (
            f"{first_name if first_name != 'The student' else 'The student'} "
            "has made positive progress in lessons."
        )

    next_step_sentence = f"To build on this progress, {learner} should {next_steps[0]}."

    parts = [
        opening_sentence,
        teacher_evidence_sentence,
        topic_sentence,
        achievement_sentence,
        memory_sentence,
        next_step_sentence,
    ]

    return " ".join(part.strip() for part in parts if part).strip()
