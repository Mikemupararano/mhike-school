from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Literal

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.assessment_candidate import AssessmentCandidate
from app.models.user import User
from app.repositories.assessment_candidate import AssessmentCandidateRepository
from app.services.published_assessment_results_service import (
    get_parent_published_assessment_result,
    get_student_published_assessment_result,
)

# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------


TrendAudience = Literal[
    "student",
    "parent",
]


# ---------------------------------------------------------------------------
# Numeric helpers
# ---------------------------------------------------------------------------


_ZERO = Decimal("0")
_TWO_DECIMAL_PLACES = Decimal("0.01")


def _to_decimal(
    value: Decimal | int | float | str | None,
) -> Decimal | None:
    """
    Convert a supported numeric value to Decimal.

    ``None`` remains ``None`` because missing published values must never be
    interpreted as zero.
    """

    if value is None:
        return None

    if isinstance(
        value,
        Decimal,
    ):
        return value

    return Decimal(
        str(value),
    )


def _round_decimal(
    value: Decimal,
) -> Decimal:
    """
    Round a decimal value to two decimal places.
    """

    return value.quantize(
        _TWO_DECIMAL_PLACES,
        rounding=ROUND_HALF_UP,
    )


def _mean(
    values: list[Decimal],
) -> Decimal | None:
    """
    Return the arithmetic mean of supplied decimal values.

    Missing values must be removed before calling this helper.
    """

    if not values:
        return None

    return _round_decimal(
        sum(
            values,
            _ZERO,
        )
        / Decimal(
            len(values),
        ),
    )


# ---------------------------------------------------------------------------
# Text/filter helpers
# ---------------------------------------------------------------------------


def _normalise_optional_text(
    value: str | None,
) -> str | None:
    """
    Return trimmed optional text.

    Empty strings are treated as no filter.
    """

    if value is None:
        return None

    cleaned = value.strip()

    return cleaned or None


def _text_matches(
    actual: str | None,
    expected: str | None,
) -> bool:
    """
    Return whether an optional text field matches an optional filter.

    Matching is case-insensitive while preserving original model values in
    returned trend data.
    """

    if expected is None:
        return True

    if actual is None:
        return False

    return actual.strip().casefold() == expected.strip().casefold()


# ---------------------------------------------------------------------------
# Date helpers
# ---------------------------------------------------------------------------


def _ensure_aware_datetime(
    value: datetime | None,
) -> datetime | None:
    """
    Return a timezone-aware datetime suitable for deterministic ordering.

    Database backends used during testing may return naive datetimes even
    when production columns are timezone-aware. Naive values are interpreted
    as UTC for ordering purposes.
    """

    if value is None:
        return None

    if value.tzinfo is None:
        return value.replace(
            tzinfo=timezone.utc,
        )

    return value


def _candidate_assessment_datetime(
    candidate: AssessmentCandidate,
) -> datetime:
    """
    Return the best chronological date for one assessment allocation.

    Preference order:

        1. assessment.scheduled_at
        2. candidate.submitted_at
        3. candidate.started_at
        4. candidate.allocated_at

    The final fallback ensures every candidate can be ordered.
    """

    assessment = candidate.assessment

    for value in (
        assessment.scheduled_at,
        candidate.submitted_at,
        candidate.started_at,
        candidate.allocated_at,
    ):
        normalised = _ensure_aware_datetime(
            value,
        )

        if normalised is not None:
            return normalised

    return datetime.min.replace(
        tzinfo=timezone.utc,
    )


# ---------------------------------------------------------------------------
# Relationship helpers
# ---------------------------------------------------------------------------


def _extract_parent_student_ids(
    parent_user: User,
) -> set[int]:
    """
    Return student identifiers linked to a parent.

    This mirrors the relationship forms supported by the published assessment
    result service. The actual published-result service remains authoritative
    for final parent authorization when individual results are retrieved.
    """

    student_ids: set[int] = set()

    for attribute_name in (
        "students",
        "parent_students",
        "linked_students",
    ):
        relationship_value = getattr(
            parent_user,
            attribute_name,
            None,
        )

        if relationship_value is None:
            continue

        for item in relationship_value:
            if hasattr(
                item,
                "student_id",
            ):
                student_id = getattr(
                    item,
                    "student_id",
                )

            elif hasattr(
                item,
                "id",
            ):
                student_id = getattr(
                    item,
                    "id",
                )

            else:
                continue

            try:
                student_ids.add(
                    int(student_id),
                )
            except (TypeError, ValueError):
                continue

    return student_ids


# ---------------------------------------------------------------------------
# Candidate filtering
# ---------------------------------------------------------------------------


def _candidate_matches_filters(
    candidate: AssessmentCandidate,
    *,
    course_id: int | None,
    subject_id: int | None,
    academic_year: str | None,
    term: str | None,
) -> bool:
    """
    Return whether a candidate's assessment matches trend filters.
    """

    assessment = candidate.assessment
    course = assessment.course

    if course_id is not None and assessment.course_id != course_id:
        return False

    if subject_id is not None:
        if course is None:
            return False

        if course.subject_id != subject_id:
            return False

    if not _text_matches(
        assessment.academic_year,
        academic_year,
    ):
        return False

    if not _text_matches(
        assessment.term,
        term,
    ):
        return False

    return True


# ---------------------------------------------------------------------------
# Published result retrieval
# ---------------------------------------------------------------------------


async def _get_visible_published_result(
    db: AsyncSession,
    current_user: User,
    *,
    candidate_id: int,
    audience: TrendAudience,
) -> dict[str, Any] | None:
    """
    Return one audience-visible published result.

    Hidden or unpublished results are deliberately skipped rather than
    exposed in trend output.

    The existing published-result services remain authoritative for:

        - student ownership,
        - parent-child authorization,
        - active publication state,
        - audience visibility,
        - result-field visibility,
        - finalised result selection,
        - grading.

    A 404 therefore means that the assessment must not contribute to the
    audience's trend.

    Other failures are propagated because they represent genuine application
    or authorization problems rather than normal publication filtering.
    """

    try:
        if audience == "student":
            return await get_student_published_assessment_result(
                db=db,
                current_user=current_user,
                candidate_id=candidate_id,
            )

        if audience == "parent":
            return await get_parent_published_assessment_result(
                db=db,
                current_user=current_user,
                candidate_id=candidate_id,
            )

        raise ValueError(
            f"Unsupported assessment trend audience: {audience!r}",
        )

    except HTTPException as exc:
        if exc.status_code == status.HTTP_404_NOT_FOUND:
            return None

        raise


# ---------------------------------------------------------------------------
# Trend-point construction
# ---------------------------------------------------------------------------


def _build_trend_point(
    *,
    candidate: AssessmentCandidate,
    published_result: dict[str, Any],
) -> dict[str, Any]:
    """
    Build one chronological published assessment trend point.
    """

    assessment = candidate.assessment
    course = assessment.course
    subject = course.subject if course is not None else None

    percentage = _to_decimal(
        published_result.get(
            "percentage",
        ),
    )

    mark_awarded = _to_decimal(
        published_result.get(
            "mark_awarded",
        ),
    )

    grade_points = _to_decimal(
        published_result.get(
            "grade_points",
        ),
    )

    return {
        "assessment_id": assessment.id,
        "candidate_id": candidate.id,
        "student_id": candidate.student_id,
        "assessment_title": assessment.title,
        "assessment_type": assessment.assessment_type,
        "academic_year": assessment.academic_year,
        "term": assessment.term,
        "scheduled_at": assessment.scheduled_at,
        "assessment_date": _candidate_assessment_datetime(
            candidate,
        ),
        "course_id": assessment.course_id,
        "course_title": (course.title if course is not None else None),
        "subject_id": (course.subject_id if course is not None else None),
        "subject_name": (subject.name if subject is not None else None),
        "subject_code": (subject.code if subject is not None else None),
        "exam_board": (course.exam_board if course is not None else None),
        "qualification": (course.qualification if course is not None else None),
        "specification_code": (
            course.specification_code if course is not None else None
        ),
        "script_id": published_result.get(
            "script_id",
        ),
        "script_version": published_result.get(
            "script_version",
        ),
        "mark_awarded": mark_awarded,
        "percentage": percentage,
        "grade": published_result.get(
            "grade",
        ),
        "grade_points": grade_points,
        "is_pass": published_result.get(
            "is_pass",
        ),
        "published_at": published_result.get(
            "published_at",
        ),
        "visibility": published_result.get(
            "visibility",
        ),
    }


# ---------------------------------------------------------------------------
# Movement helpers
# ---------------------------------------------------------------------------


def _add_percentage_movements(
    points: list[dict[str, Any]],
) -> None:
    """
    Add percentage movement from the previous visible percentage.

    Movement is calculated only where both the current and previous
    assessments expose a percentage to the audience.

    A hidden percentage therefore never contributes indirectly to a trend.
    """

    previous_percentage: Decimal | None = None

    for point in points:
        percentage = _to_decimal(
            point.get(
                "percentage",
            ),
        )

        if percentage is None:
            point["percentage_change"] = None
            continue

        if previous_percentage is None:
            point["percentage_change"] = None

        else:
            point["percentage_change"] = _round_decimal(
                percentage - previous_percentage,
            )

        previous_percentage = percentage


def _calculate_percentage_summary(
    points: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Calculate aggregate statistics from audience-visible percentages only.
    """

    percentages = [
        value
        for point in points
        if (
            value := _to_decimal(
                point.get(
                    "percentage",
                ),
            )
        )
        is not None
    ]

    if not percentages:
        return {
            "percentage_result_count": 0,
            "average_percentage": None,
            "first_percentage": None,
            "latest_percentage": None,
            "overall_percentage_change": None,
            "highest_percentage": None,
            "lowest_percentage": None,
        }

    first_percentage = percentages[0]
    latest_percentage = percentages[-1]

    return {
        "percentage_result_count": len(
            percentages,
        ),
        "average_percentage": _mean(
            percentages,
        ),
        "first_percentage": first_percentage,
        "latest_percentage": latest_percentage,
        "overall_percentage_change": (
            _round_decimal(
                latest_percentage - first_percentage,
            )
            if len(percentages) > 1
            else None
        ),
        "highest_percentage": max(
            percentages,
        ),
        "lowest_percentage": min(
            percentages,
        ),
    }


def _calculate_grade_points_summary(
    points: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Calculate aggregate statistics from audience-visible grade points only.
    """

    grade_points = [
        value
        for point in points
        if (
            value := _to_decimal(
                point.get(
                    "grade_points",
                ),
            )
        )
        is not None
    ]

    if not grade_points:
        return {
            "grade_points_result_count": 0,
            "average_grade_points": None,
            "first_grade_points": None,
            "latest_grade_points": None,
            "overall_grade_points_change": None,
        }

    first_grade_points = grade_points[0]
    latest_grade_points = grade_points[-1]

    return {
        "grade_points_result_count": len(
            grade_points,
        ),
        "average_grade_points": _mean(
            grade_points,
        ),
        "first_grade_points": first_grade_points,
        "latest_grade_points": latest_grade_points,
        "overall_grade_points_change": (
            _round_decimal(
                latest_grade_points - first_grade_points,
            )
            if len(grade_points) > 1
            else None
        ),
    }


# ---------------------------------------------------------------------------
# Core trend builder
# ---------------------------------------------------------------------------


async def _build_published_student_trend(
    db: AsyncSession,
    current_user: User,
    *,
    student_id: int,
    audience: TrendAudience,
    school_id: int | None = None,
    course_id: int | None = None,
    subject_id: int | None = None,
    academic_year: str | None = None,
    term: str | None = None,
) -> dict[str, Any]:
    """
    Build longitudinal published assessment performance for one student.

    Only audience-visible published results contribute to the returned trend.

    No result marks, percentages or grades are persisted by this service.
    Everything is derived from the existing assessment result, grading and
    publication layers.
    """

    if student_id <= 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="student_id must be a positive integer.",
        )

    if school_id is not None and school_id <= 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="school_id must be a positive integer.",
        )

    if course_id is not None and course_id <= 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="course_id must be a positive integer.",
        )

    if subject_id is not None and subject_id <= 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="subject_id must be a positive integer.",
        )

    clean_academic_year = _normalise_optional_text(
        academic_year,
    )

    clean_term = _normalise_optional_text(
        term,
    )

    repository = AssessmentCandidateRepository(
        db,
    )

    candidates = await repository.list_candidates_by_student(
        student_id,
        school_id=school_id,
        include_relationships=True,
    )

    filtered_candidates = [
        candidate
        for candidate in candidates
        if _candidate_matches_filters(
            candidate,
            course_id=course_id,
            subject_id=subject_id,
            academic_year=clean_academic_year,
            term=clean_term,
        )
    ]

    # The repository returns newest allocations first. Trend output is
    # deliberately chronological from earliest to latest.
    filtered_candidates.sort(
        key=_candidate_assessment_datetime,
    )

    points: list[dict[str, Any]] = []

    for candidate in filtered_candidates:
        published_result = await _get_visible_published_result(
            db,
            current_user,
            candidate_id=candidate.id,
            audience=audience,
        )

        if published_result is None:
            continue

        points.append(
            _build_trend_point(
                candidate=candidate,
                published_result=published_result,
            )
        )

    _add_percentage_movements(
        points,
    )

    percentage_summary = _calculate_percentage_summary(
        points,
    )

    grade_points_summary = _calculate_grade_points_summary(
        points,
    )

    return {
        "student_id": student_id,
        "audience": audience,
        "filters": {
            "school_id": school_id,
            "course_id": course_id,
            "subject_id": subject_id,
            "academic_year": clean_academic_year,
            "term": clean_term,
        },
        "assessment_count": len(
            points,
        ),
        **percentage_summary,
        **grade_points_summary,
        "points": points,
    }


# ---------------------------------------------------------------------------
# Student-facing trends
# ---------------------------------------------------------------------------


async def get_student_assessment_trend(
    db: AsyncSession,
    current_user: User,
    *,
    school_id: int | None = None,
    course_id: int | None = None,
    subject_id: int | None = None,
    academic_year: str | None = None,
    term: str | None = None,
) -> dict[str, Any]:
    """
    Return published longitudinal assessment performance for the logged-in
    student.

    The student identifier is always derived from ``current_user`` and cannot
    be supplied by the caller.
    """

    return await _build_published_student_trend(
        db,
        current_user,
        student_id=current_user.id,
        audience="student",
        school_id=school_id,
        course_id=course_id,
        subject_id=subject_id,
        academic_year=academic_year,
        term=term,
    )


# ---------------------------------------------------------------------------
# Parent-facing trends
# ---------------------------------------------------------------------------


async def get_parent_student_assessment_trend(
    db: AsyncSession,
    current_user: User,
    *,
    student_id: int,
    school_id: int | None = None,
    course_id: int | None = None,
    subject_id: int | None = None,
    academic_year: str | None = None,
    term: str | None = None,
) -> dict[str, Any]:
    """
    Return published longitudinal assessment performance for a parent's
    linked child.

    Parent-child authorization is performed before candidate history is
    queried. Individual published results are then independently authorized
    again by the existing published-result service.
    """

    if student_id <= 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="student_id must be a positive integer.",
        )

    linked_student_ids = _extract_parent_student_ids(
        current_user,
    )

    if student_id not in linked_student_ids:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Published assessment trend not found.",
        )

    return await _build_published_student_trend(
        db,
        current_user,
        student_id=student_id,
        audience="parent",
        school_id=school_id,
        course_id=course_id,
        subject_id=subject_id,
        academic_year=academic_year,
        term=term,
    )
