import random
import re
from collections.abc import Iterable

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
    "chemistry": "Through the study of {topics}, they have strengthened their scientific knowledge and confidence.",
    "biology": "Through work on {topics}, they have developed a stronger understanding of biological concepts and processes.",
    "physics": "Through the study of {topics}, they have strengthened their problem-solving skills and understanding of physical principles.",
    "english": "Through work on {topics}, they have developed their analytical, reading and written communication skills.",
    "geography": "Through the study of {topics}, they have developed their geographical knowledge and ability to explain processes and places.",
    "computer science": "Through work on {topics}, they have developed their computational thinking and problem-solving skills.",
    "art": "Through work on {topics}, they have developed their creative confidence, technical control and visual communication skills.",
    "religious studies": "Through the study of {topics}, they have developed their understanding of beliefs, ethics and different viewpoints.",
    "history": "Through work on {topics}, they have developed their historical knowledge, source skills and analytical thinking.",
    "mathematics": "Through work on {topics}, they have developed their mathematical fluency, accuracy and problem-solving confidence.",
}

DEFAULT_TOPIC_SENTENCE = (
    "Through work on {topics}, they have strengthened their subject knowledge, "
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

PROMPT_LEAKAGE_PATTERNS = [
    r"use these teacher notes as the main evidence.*",
    r"use the teacher notes as the main evidence.*",
    r"write a professional school report.*",
    r"generate a professional school report.*",
    r"do not invent information.*",
    r"use the pupil'?s first name only.*",
    r"use the student'?s first name only.*",
    r"avoid repeating the work covered.*",
    r"include a clear next step.*",
    r"return only the report.*",
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

BULLET_PREFIX_PATTERN = re.compile(r"^\s*(?:[-*•▪◦‣]+|\d+[.)])\s*")


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
    cleaned = " ".join(student_name.strip().split())

    if not cleaned or cleaned.lower() == "the student":
        return "The student"

    first_name = cleaned.split(" ", maxsplit=1)[0]
    first_name = first_name.strip(" ,.;:!?()[]{}")

    return first_name or "The student"


def join_items(items: Iterable[str]) -> str:
    unique_items: list[str] = []

    for raw_item in items:
        item = raw_item.strip()

        if item and item not in unique_items:
            unique_items.append(item)

    if not unique_items:
        return ""

    if len(unique_items) == 1:
        return unique_items[0]

    if len(unique_items) == 2:
        return f"{unique_items[0]} and {unique_items[1]}"

    return ", ".join(unique_items[:-1]) + f" and {unique_items[-1]}"


def _remove_prompt_leakage(text: str) -> str:
    cleaned_lines: list[str] = []

    for raw_line in text.splitlines():
        line = raw_line.strip()

        if not line:
            continue

        lower_line = line.lower()

        if any(
            re.fullmatch(pattern, lower_line) for pattern in PROMPT_LEAKAGE_PATTERNS
        ):
            continue

        cleaned_lines.append(line)

    return "\n".join(cleaned_lines).strip()


def _normalise_bullets(text: str) -> list[str]:
    items: list[str] = []

    for raw_line in re.split(r"[\r\n]+", text):
        line = BULLET_PREFIX_PATTERN.sub("", raw_line).strip(" \t,;")

        if not line:
            continue

        if ";" in line:
            items.extend(part.strip() for part in line.split(";") if part.strip())
        else:
            items.append(line)

    return items


def split_generation_notes(notes: str) -> tuple[str, str]:
    cleaned_notes = _remove_prompt_leakage(notes)

    markers = list(
        re.finditer(
            r"(?im)^\s*(work covered|teacher notes|student comment|teacher comment)\s*:\s*",
            cleaned_notes,
        ),
    )

    if not markers:
        return "", cleaned_notes.strip()

    sections: dict[str, list[str]] = {}

    for index, marker in enumerate(markers):
        label = marker.group(1).lower()
        start = marker.end()
        end = (
            markers[index + 1].start()
            if index + 1 < len(markers)
            else len(cleaned_notes)
        )
        sections.setdefault(label, []).append(cleaned_notes[start:end].strip())

    work_covered = "\n".join(sections.get("work covered", [])).strip()
    teacher_notes = "\n".join(
        sections.get("teacher notes", [])
        + sections.get("student comment", [])
        + sections.get("teacher comment", [])
    ).strip()

    return work_covered, teacher_notes


def clean_work_covered_text(text: str) -> str:
    cleaned = _remove_prompt_leakage(text).lower()

    for pattern in (
        r"\bin\s+(aqa|ocr|edexcel)\s+gcse\s+[a-z ]+?,",
        r"\b(aqa|ocr|edexcel)\s+gcse\s+[a-z ]+?,",
        r"\bin\s+(aqa|ocr|edexcel)\s+[a-z ]+?,",
        r"\b(aqa|ocr|edexcel)\s+[a-z ]+?,",
    ):
        cleaned = re.sub(pattern, "", cleaned)

    for phrase in CURRICULUM_FILLER_PHRASES:
        cleaned = cleaned.replace(phrase, "")

    cleaned = re.sub(r"[\r\n;]+", ",", cleaned)
    cleaned = cleaned.replace(".", ",")
    cleaned = re.sub(r"\s+and\s+", ",", cleaned)
    cleaned = re.sub(r",+", ",", cleaned)

    return cleaned.strip(" ,..:")


def detect_topics(text: str, subject_key: str) -> list[str]:
    topic_map = SUBJECT_TOPIC_MAPS.get(subject_key, {})
    cleaned_text = clean_work_covered_text(text)
    topics: list[str] = []

    for keyword, topic in topic_map.items():
        if keyword in cleaned_text and topic not in topics:
            topics.append(topic)

    if topics:
        return topics[:5]

    fallback_parts = [
        part.strip() for part in cleaned_text.split(",") if len(part.strip()) > 2
    ]

    return list(dict.fromkeys(fallback_parts))[:5]


def build_topic_sentence(*, topics: list[str], subject_key: str) -> str:
    if not topics:
        return ""

    template = SUBJECT_TOPIC_SENTENCES.get(subject_key, DEFAULT_TOPIC_SENTENCE)
    return template.format(topics=join_items(topics[:5]))


def clean_teacher_notes_text(text: str, first_name: str) -> str:
    cleaned = _remove_prompt_leakage(text).strip()

    if not cleaned:
        return ""

    if first_name != "The student":
        cleaned = re.sub(
            rf"^\s*{re.escape(first_name)}\s*[:.,-]*\s*",
            "",
            cleaned,
            flags=re.IGNORECASE,
        )

    cleaned = re.sub(r"[ \t]+", " ", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)

    return cleaned.strip(" .")


def _extract_percentage_evidence(text: str) -> str | None:
    percentage_match = re.search(
        r"\b(\d{1,3})\s*%\s*(?:in|on)?\s*([^.,;\n]*)",
        text,
        flags=re.IGNORECASE,
    )

    if not percentage_match:
        return None

    percentage = percentage_match.group(1)
    context = percentage_match.group(2).strip() or "recent assessment work"
    return f"They achieved {percentage}% in {context}."


def build_teacher_evidence_sentence(*, first_name: str, teacher_notes: str) -> str:
    cleaned = clean_teacher_notes_text(teacher_notes, first_name)

    if not cleaned:
        return ""

    items = _normalise_bullets(cleaned)
    lower_notes = cleaned.lower()
    strengths: list[str] = []

    if "hardworking" in lower_notes or "hard working" in lower_notes:
        strengths.append("work hard")
    if "positive attitude" in lower_notes:
        strengths.append("show a positive attitude to learning")
    if "well behaved" in lower_notes or "well-behaved" in lower_notes:
        strengths.append("behave well in lessons")
    if "punctual" in lower_notes:
        strengths.append("are punctual and prepared for learning")
    if "homework" in lower_notes and any(
        phrase in lower_notes
        for phrase in ("on time", "completed", "completes", "always done")
    ):
        strengths.append("complete homework reliably")
    if "engaged" in lower_notes or "class discussion" in lower_notes:
        strengths.append("engage positively in class")
    if "practical" in lower_notes:
        strengths.append("contribute well to practical work")
    if "independent" in lower_notes or "independently" in lower_notes:
        strengths.append("work with increasing independence")

    evidence_parts: list[str] = []

    if strengths:
        evidence_parts.append(f"They {join_items(strengths[:4])}.")

    percentage_sentence = _extract_percentage_evidence(cleaned)
    if percentage_sentence:
        evidence_parts.append(percentage_sentence)

    if evidence_parts:
        return " ".join(evidence_parts)

    cleaned_items = [item.rstrip(".") for item in items if len(item.split()) >= 2]
    if cleaned_items:
        return f"They have shown {join_items(cleaned_items[:3])}."

    return ""


def detect_attitude_sentence(lower_notes: str) -> str | None:
    qualities: list[str] = []

    if any(
        phrase in lower_notes
        for phrase in ("hard worker", "hard working", "hardworking")
    ):
        qualities.append("work hard")
    if "asks questions" in lower_notes or "asking questions" in lower_notes:
        qualities.append("ask thoughtful questions to deepen their understanding")
    if "engaged" in lower_notes or "engagement" in lower_notes:
        qualities.append("engage well with learning")
    if "independent" in lower_notes or "independently" in lower_notes:
        qualities.append("work with increasing independence")
    if "resilient" in lower_notes or "resilience" in lower_notes:
        qualities.append("show resilience when tackling challenging work")
    if "creative" in lower_notes or "creativity" in lower_notes:
        qualities.append("show creativity and originality")
    if "organised" in lower_notes or "organized" in lower_notes:
        qualities.append("are organised and prepared for learning")

    return f"They {join_items(qualities[:3])}." if qualities else None


def detect_achievement_sentence(lower_notes: str) -> str | None:
    achievements: list[str] = []

    if "confident" in lower_notes or "confidence" in lower_notes:
        achievements.append("grown in confidence")
    if any(
        phrase in lower_notes
        for phrase in (
            "passed tests",
            "excellent assessment",
            "strong assessment",
            "good assessment",
            "high test score",
            "strong test score",
        )
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
        achievements.append("improved the quality of their written responses")
    if "practical" in lower_notes or "experiment" in lower_notes:
        achievements.append("developed their practical and investigative skills")
    if "exam question" in lower_notes or "exam-style" in lower_notes:
        achievements.append("made progress with examination-style questions")
    if "analysis" in lower_notes or "analytical" in lower_notes:
        achievements.append("developed their analytical skills")
    if "evaluation" in lower_notes or "evaluate" in lower_notes:
        achievements.append("improved their evaluative skills")
    if "coding" in lower_notes or "programming" in lower_notes:
        achievements.append("developed their programming skills")
    if "composition" in lower_notes or "portfolio" in lower_notes:
        achievements.append("developed their creative and technical skills")

    return (
        f"This has helped them to {join_items(achievements[:3])}."
        if achievements
        else None
    )


def detect_next_steps(lower_notes: str, subject_key: str) -> list[str]:
    next_steps: list[str] = []

    if "revision guide" in lower_notes:
        next_steps.append(
            "use the revision guide regularly to consolidate key knowledge"
        )
    if "exam question" in lower_notes or "exam-style" in lower_notes:
        next_steps.append("continue practising examination-style questions")
    if "application" in lower_notes or "apply" in lower_notes:
        next_steps.append(
            "focus on applying knowledge accurately to unfamiliar questions"
        )
    if any(word in lower_notes for word in ("calculation", "calculations", "maths")):
        next_steps.append(
            "show clear working in calculations and check units carefully"
        )
    if "detail" in lower_notes or "explain" in lower_notes:
        next_steps.append("include more precise detail in written explanations")
    if "recall" in lower_notes or "remember" in lower_notes:
        next_steps.append("strengthen recall of key facts and definitions")
    if "revise" in lower_notes or "revision" in lower_notes:
        next_steps.append("maintain a regular revision routine")
    if "six-mark" in lower_notes or "6-mark" in lower_notes:
        next_steps.append(
            "structure extended responses carefully and include sufficient detail"
        )

    if next_steps:
        return list(dict.fromkeys(next_steps))

    defaults = {
        "english": "continue developing clear paragraph structure and support ideas with precise textual evidence",
        "geography": "continue using accurate geographical terminology and evidence when explaining processes",
        "computer science": "continue practising programming problems and explaining algorithms clearly",
        "art": "continue refining observational detail and recording development clearly in the sketchbook",
        "religious studies": "continue using evidence and examples to explain different beliefs and viewpoints",
        "history": "continue supporting judgements with precise evidence and clear explanation",
        "mathematics": "continue practising multi-step problems and checking their working carefully",
        "biology": "continue using key terminology accurately when explaining biological processes",
        "physics": "continue applying equations carefully and explaining physical principles clearly",
        "chemistry": "continue applying chemical ideas accurately to unfamiliar questions",
    }

    return [
        defaults.get(
            subject_key,
            "continue to review class notes and practise applying their knowledge",
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

    defaults = {
        "english": "continue developing clear paragraph structure and support ideas with precise textual evidence",
        "geography": "continue using accurate geographical terminology and evidence when explaining processes",
        "computer science": "continue practising programming problems and explaining algorithms clearly",
        "art": "continue refining observational detail and recording development clearly in the sketchbook",
        "religious studies": "continue using evidence and examples to explain different beliefs and viewpoints",
        "history": "continue supporting judgements with precise evidence and clear explanation",
        "mathematics": "continue practising multi-step problems and checking their working carefully",
        "biology": "continue using key terminology accurately when explaining biological processes",
        "physics": "continue applying equations carefully and explaining physical principles clearly",
    }

    return defaults.get(
        subject_key,
        "continue to review class notes and practise applying their knowledge",
    )


def extract_memory_phrases(similar_reports: list[str] | None) -> list[str]:
    if not similar_reports:
        return []

    phrases: list[str] = []

    for report in similar_reports:
        for raw_sentence in re.split(r"(?<=[.!?])\s+", report):
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

    scored.sort(key=lambda item: item[0], reverse=True)
    top_candidates = [phrase for score, phrase in scored[:5] if score > -100]

    if not top_candidates:
        return None

    selected = random.choice(top_candidates).strip()
    selected = re.sub(
        rf"\b{re.escape(student_name)}\b", learner, selected, flags=re.IGNORECASE
    )
    selected = re.sub(
        rf"\b{re.escape(first_name)}\b", learner, selected, flags=re.IGNORECASE
    )

    if selected[-1] not in ".!?":
        selected += "."

    return selected


def select_opening_sentence(
    *, first_name: str, subject_name: str, year_group_name: str
) -> str:
    if first_name == "The student":
        return f"The student has made positive progress in {subject_name} during {year_group_name}."

    template = random.choice(REPORT_OPENINGS)
    return template.format(
        name=first_name, subject=subject_name, year_group=year_group_name
    )


def _deduplicate_sentences(parts: list[str | None]) -> list[str]:
    output: list[str] = []
    seen: set[str] = set()

    for part in parts:
        if not part:
            continue

        sentence = re.sub(r"\s+", " ", part.strip())

        if not sentence:
            continue

        key = re.sub(r"[^a-z0-9]+", " ", sentence.lower()).strip()

        if key in seen:
            continue

        seen.add(key)
        output.append(sentence)

    return output


def generate_report_comment(
    *,
    notes: str,
    student_name: str,
    subject: str | None,
    year_group: str | None,
    similar_reports: list[str] | None = None,
    used_phrases: set[str] | None = None,
) -> str:
    del similar_reports, used_phrases

    cleaned_notes = _remove_prompt_leakage(notes)

    if len(cleaned_notes.split()) < 4:
        raise ValueError(
            "Please enter more detailed teacher notes before generating a report.",
        )

    work_covered_text, teacher_notes_text = split_generation_notes(cleaned_notes)

    first_name = get_first_name(student_name)
    subject_name = subject.strip() if subject and subject.strip() else "the subject"
    year_group_name = (
        year_group.strip() if year_group and year_group.strip() else "this year"
    )
    subject_key = normalise_subject(subject_name)

    work_lower = work_covered_text.lower()
    teacher_lower = teacher_notes_text.lower()
    combined_lower = cleaned_notes.lower()

    topics = detect_topics(work_lower, subject_key)

    if not topics and not work_covered_text:
        topics = detect_topics(combined_lower, subject_key)

    next_steps = detect_next_steps(teacher_lower, subject_key)

    if not next_steps:
        next_steps = detect_next_steps(combined_lower, subject_key)

    if not next_steps:
        next_steps = [infer_next_step_from_topics(topics, subject_key)]

    opening_sentence = select_opening_sentence(
        first_name=first_name,
        subject_name=subject_name,
        year_group_name=year_group_name,
    )

    teacher_evidence_sentence = build_teacher_evidence_sentence(
        first_name=first_name,
        teacher_notes=teacher_notes_text,
    )

    topic_sentence = build_topic_sentence(topics=topics, subject_key=subject_key)
    attitude_sentence = detect_attitude_sentence(teacher_lower)
    achievement_sentence = detect_achievement_sentence(teacher_lower)

    if teacher_evidence_sentence and attitude_sentence:
        attitude_sentence = None

    if (
        not teacher_evidence_sentence
        and not topic_sentence
        and not achievement_sentence
    ):
        achievement_sentence = "They have made positive progress in lessons."

    next_step_sentence = f"To build on this progress, they should {next_steps[0]}."

    parts = _deduplicate_sentences(
        [
            opening_sentence,
            teacher_evidence_sentence,
            attitude_sentence,
            topic_sentence,
            achievement_sentence,
            next_step_sentence,
        ],
    )

    return re.sub(r"\s+", " ", " ".join(parts).strip())
