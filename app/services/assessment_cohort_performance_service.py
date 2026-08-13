from __future__ import annotations

from collections import Counter
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.assessment import Assessment
from app.models.user import User, UserRole
from app.repositories.assessment import AssessmentRepository
from app.services.assessment_analytics_service import (
    get_assessment_analytics,
)

_ZERO = Decimal("0")
_ONE_HUNDRED = Decimal("100")
_DECIMAL_QUANTUM = Decimal("0.01")


# ---------------------------------------------------------------------------
# Role helpers
# ---------------------------------------------------------------------------


def _has_role(
    user: User,
    role: UserRole,
) -> bool:
    """
    Return whether the user currently holds the supplied role.
    """

    return role.value in set(
        user.roles,
    )


def _is_platform_admin(
    user: User,
) -> bool:
    return _has_role(
        user,
        UserRole.PLATFORM_ADMIN,
    )


def _is_school_admin(
    user: User,
) -> bool:
    return _has_role(
        user,
        UserRole.SCHOOL_ADMIN,
    )


def _is_teacher(
    user: User,
) -> bool:
    return _has_role(
        user,
        UserRole.TEACHER,
    )


def _ensure_cohort_staff_role(
    current_user: User,
) -> None:
    """
    Ensure the caller may access staff assessment analytics.

    This intentionally mirrors the existing assessment-results/analytics
    staff scope rather than creating student- or parent-facing cohort access.
    """

    if (
        _is_teacher(current_user)
        or _is_school_admin(current_user)
        or _is_platform_admin(current_user)
    ):
        return

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="You do not have permission to view assessment cohort performance.",
    )


# ---------------------------------------------------------------------------
# Validation and normalisation
# ---------------------------------------------------------------------------


def _validate_optional_positive_integer(
    value: int | None,
    *,
    field_name: str,
) -> int | None:
    """
    Validate an optional positive integer identifier.
    """

    if value is None:
        return None

    if (
        not isinstance(
            value,
            int,
        )
        or isinstance(
            value,
            bool,
        )
        or value < 1
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"{field_name} must be a positive integer.",
        )

    return value


def _normalise_optional_text(
    value: str | None,
    *,
    field_name: str,
    max_length: int,
) -> str | None:
    """
    Trim and validate optional cohort filter text.
    """

    if value is None:
        return None

    if not isinstance(
        value,
        str,
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"{field_name} must be a string or None.",
        )

    cleaned = value.strip()

    if not cleaned:
        return None

    if len(cleaned) > max_length:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"{field_name} cannot exceed {max_length} characters.",
        )

    return cleaned


# ---------------------------------------------------------------------------
# Numeric helpers
# ---------------------------------------------------------------------------


def _to_decimal(
    value: Decimal | int | float | str | None,
) -> Decimal | None:
    """
    Convert a supported numeric value to Decimal.

    Missing formal results remain None and are never interpreted as zero.
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


def _quantize(
    value: Decimal | None,
) -> Decimal | None:
    """
    Round a Decimal analytics value to two decimal places.
    """

    if value is None:
        return None

    return value.quantize(
        _DECIMAL_QUANTUM,
        rounding=ROUND_HALF_UP,
    )


def _percentage(
    numerator: int | Decimal,
    denominator: int | Decimal,
) -> Decimal | None:
    """
    Return a percentage rounded to two decimal places.
    """

    numerator_value = Decimal(
        str(numerator),
    )

    denominator_value = Decimal(
        str(denominator),
    )

    if denominator_value <= _ZERO:
        return None

    return _quantize(
        (numerator_value / denominator_value) * _ONE_HUNDRED,
    )


def _mean(
    values: list[Decimal],
) -> Decimal | None:
    """
    Return the arithmetic mean of individual candidate results.
    """

    if not values:
        return None

    return _quantize(
        sum(
            values,
            _ZERO,
        )
        / Decimal(
            len(values),
        ),
    )


def _median(
    values: list[Decimal],
) -> Decimal | None:
    """
    Return the median of individual candidate results.
    """

    if not values:
        return None

    ordered = sorted(
        values,
    )

    count = len(
        ordered,
    )

    midpoint = count // 2

    if count % 2:
        return _quantize(
            ordered[midpoint],
        )

    return _quantize(
        (ordered[midpoint - 1] + ordered[midpoint]) / Decimal("2"),
    )


# ---------------------------------------------------------------------------
# Assessment-scope helpers
# ---------------------------------------------------------------------------


def _assessment_subject_id(
    assessment: Assessment,
) -> int | None:
    """
    Return the canonical subject identifier for an assessment's course.
    """

    course = assessment.course

    if course is None:
        return None

    return course.subject_id


def _assessment_subject_name(
    assessment: Assessment,
) -> str | None:
    """
    Return the canonical subject name when available.
    """

    course = assessment.course

    if course is None:
        return None

    subject = getattr(
        course,
        "subject",
        None,
    )

    if subject is None:
        return None

    return subject.name


def _assessment_matches_scope(
    assessment: Assessment,
    current_user: User,
    *,
    subject_id: int | None,
    teacher_id: int | None,
) -> bool:
    """
    Apply service-level filters that are not handled directly by the
    AssessmentRepository.

    Teacher-only callers are restricted to courses they teach.

    School Admin and Platform Admin retain their broader existing assessment
    scope.
    """

    course = assessment.course

    if course is None:
        return False

    if (
        _is_teacher(current_user)
        and not _is_school_admin(current_user)
        and not _is_platform_admin(current_user)
        and course.teacher_id != current_user.id
    ):
        return False

    if subject_id is not None and course.subject_id != subject_id:
        return False

    if teacher_id is not None and course.teacher_id != teacher_id:
        return False

    return True


async def _list_accessible_assessments(
    db: AsyncSession,
    current_user: User,
    *,
    school_id: int | None,
    course_id: int | None,
    subject_id: int | None,
    teacher_id: int | None,
    academic_year: str | None,
    term: str | None,
) -> tuple[
    int | None,
    list[Assessment],
]:
    """
    Return candidate assessments for cohort aggregation.

    The underlying single-assessment analytics service remains authoritative
    for final access control. This function narrows the query up front so
    ordinary teachers do not enumerate unrelated courses unnecessarily.
    """

    _ensure_cohort_staff_role(
        current_user,
    )

    repository = AssessmentRepository(
        db,
    )

    effective_school_id = school_id

    if not _is_platform_admin(
        current_user,
    ):
        user_school_id = getattr(
            current_user,
            "school_id",
            None,
        )

        if user_school_id is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="A school-scoped user must belong to a school.",
            )

        if effective_school_id is not None and effective_school_id != user_school_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You cannot view assessment cohort performance for another school.",
            )

        effective_school_id = int(
            user_school_id,
        )

    if effective_school_id is None:
        # Platform-wide query.
        assessments = await repository.list_all(
            include_relationships=True,
        )

        # list_all does not expose the school/course/year/term filters used by
        # list_by_school, so apply those safely below.
        assessments = [
            assessment
            for assessment in assessments
            if (
                (course_id is None or assessment.course_id == course_id)
                and (academic_year is None or assessment.academic_year == academic_year)
                and (term is None or assessment.term == term)
            )
        ]

    else:
        assessments = await repository.list_by_school(
            effective_school_id,
            course_id=course_id,
            academic_year=academic_year,
            term=term,
            include_relationships=True,
        )

    accessible = [
        assessment
        for assessment in assessments
        if _assessment_matches_scope(
            assessment,
            current_user,
            subject_id=subject_id,
            teacher_id=teacher_id,
        )
    ]

    return (
        effective_school_id,
        accessible,
    )


# ---------------------------------------------------------------------------
# Grade aggregation
# ---------------------------------------------------------------------------


def _build_cohort_grade_distribution(
    candidate_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Aggregate grade labels across candidate-result instances.

    Minimum boundaries are deliberately not combined across assessments
    because different assessments may use different grading schemes.

    The cohort distribution therefore reports label frequency only.
    """

    counts: Counter[str] = Counter()

    for row in candidate_rows:
        grade = row.get(
            "grade",
        )

        if grade is None:
            continue

        counts[
            str(
                grade,
            )
        ] += 1

    graded_count = sum(
        counts.values(),
    )

    return [
        {
            "grade": grade,
            "count": count,
            "percentage": _percentage(
                count,
                graded_count,
            ),
        }
        for grade, count in counts.items()
    ]


# ---------------------------------------------------------------------------
# Assessment-level comparison rows
# ---------------------------------------------------------------------------


def _build_assessment_comparison_row(
    assessment: Assessment,
    analytics: dict[str, Any],
) -> dict[str, Any]:
    """
    Build the compact comparison representation for one assessment.
    """

    course = assessment.course

    return {
        "assessment_id": assessment.id,
        "assessment_title": assessment.title,
        "assessment_type": assessment.assessment_type,
        "academic_year": assessment.academic_year,
        "term": assessment.term,
        "scheduled_at": assessment.scheduled_at,
        "course_id": assessment.course_id,
        "course_title": (course.title if course is not None else None),
        "teacher_id": (course.teacher_id if course is not None else None),
        "subject_id": _assessment_subject_id(
            assessment,
        ),
        "subject_name": _assessment_subject_name(
            assessment,
        ),
        "candidate_count": analytics["candidate_count"],
        "included_candidate_count": analytics["included_candidate_count"],
        "excluded_incomplete_candidate_count": analytics[
            "excluded_incomplete_candidate_count"
        ],
        "mean_percentage": analytics["mean_percentage"],
        "median_percentage": analytics["median_percentage"],
        "lowest_percentage": analytics["lowest_percentage"],
        "highest_percentage": analytics["highest_percentage"],
        "graded_candidate_count": analytics["graded_candidate_count"],
        "ungraded_candidate_count": analytics["ungraded_candidate_count"],
        "pass_count": analytics["pass_count"],
        "fail_count": analytics["fail_count"],
        "pass_percentage": analytics["pass_percentage"],
    }


# ---------------------------------------------------------------------------
# Main cohort aggregation
# ---------------------------------------------------------------------------


async def get_assessment_cohort_performance(
    db: AsyncSession,
    current_user: User,
    *,
    school_id: int | None = None,
    course_id: int | None = None,
    subject_id: int | None = None,
    teacher_id: int | None = None,
    academic_year: str | None = None,
    term: str | None = None,
) -> dict[str, Any]:
    """
    Return comparative formal performance across multiple assessments.

    Formal candidate statistics are delegated to
    ``get_assessment_analytics`` so this layer inherits the established rules:

        - latest script only;
        - fully finalised results only;
        - one candidate = one result per assessment;
        - existing teacher ownership and school isolation;
        - existing grading semantics.

    Cohort-level means and medians are calculated from the individual
    candidate percentages in each assessment ranking. Assessment averages are
    never averaged together because that would give differently-sized
    assessments equal statistical weight.
    """

    clean_school_id = _validate_optional_positive_integer(
        school_id,
        field_name="school_id",
    )

    clean_course_id = _validate_optional_positive_integer(
        course_id,
        field_name="course_id",
    )

    clean_subject_id = _validate_optional_positive_integer(
        subject_id,
        field_name="subject_id",
    )

    clean_teacher_id = _validate_optional_positive_integer(
        teacher_id,
        field_name="teacher_id",
    )

    clean_academic_year = _normalise_optional_text(
        academic_year,
        field_name="academic_year",
        max_length=50,
    )

    clean_term = _normalise_optional_text(
        term,
        field_name="term",
        max_length=100,
    )

    (
        effective_school_id,
        assessments,
    ) = await _list_accessible_assessments(
        db,
        current_user,
        school_id=clean_school_id,
        course_id=clean_course_id,
        subject_id=clean_subject_id,
        teacher_id=clean_teacher_id,
        academic_year=clean_academic_year,
        term=clean_term,
    )

    assessment_rows: list[dict[str, Any]] = []

    candidate_rows: list[dict[str, Any]] = []

    selected_assessment_count = len(
        assessments,
    )

    assessments_with_results = 0
    assessments_without_results = 0

    total_candidate_count = 0
    total_included_candidate_count = 0
    total_excluded_incomplete_candidate_count = 0

    total_graded_candidate_count = 0
    total_ungraded_candidate_count = 0

    total_pass_count = 0
    total_fail_count = 0

    unique_student_ids: set[int] = set()

    for assessment in assessments:
        analytics = await get_assessment_analytics(
            db=db,
            current_user=current_user,
            assessment_id=assessment.id,
        )

        assessment_rows.append(
            _build_assessment_comparison_row(
                assessment,
                analytics,
            )
        )

        included_count = int(analytics["included_candidate_count"])

        if included_count > 0:
            assessments_with_results += 1
        else:
            assessments_without_results += 1

        total_candidate_count += int(analytics["candidate_count"])

        total_included_candidate_count += included_count

        total_excluded_incomplete_candidate_count += int(
            analytics["excluded_incomplete_candidate_count"]
        )

        total_graded_candidate_count += int(analytics["graded_candidate_count"])

        total_ungraded_candidate_count += int(analytics["ungraded_candidate_count"])

        total_pass_count += int(analytics["pass_count"])

        total_fail_count += int(analytics["fail_count"])

        for candidate_row in analytics["ranking"]:
            row = {
                **candidate_row,
                "assessment_id": assessment.id,
                "assessment_title": assessment.title,
                "course_id": assessment.course_id,
                "subject_id": _assessment_subject_id(
                    assessment,
                ),
            }

            candidate_rows.append(
                row,
            )

            student_id = row.get(
                "student_id",
            )

            if student_id is not None:
                unique_student_ids.add(
                    int(
                        student_id,
                    )
                )

    percentages = [
        value
        for row in candidate_rows
        if (
            value := _to_decimal(
                row.get(
                    "percentage",
                )
            )
        )
        is not None
    ]

    classified_pass_fail_count = total_pass_count + total_fail_count

    grade_distribution = _build_cohort_grade_distribution(
        candidate_rows,
    )

    # Present assessments chronologically where possible. ID provides a
    # deterministic fallback for undated assessments.
    assessment_rows.sort(
        key=lambda row: (
            row["scheduled_at"] is None,
            row["scheduled_at"],
            row["assessment_id"],
        ),
    )

    return {
        "scope": {
            "school_id": effective_school_id,
            "course_id": clean_course_id,
            "subject_id": clean_subject_id,
            "teacher_id": clean_teacher_id,
            "academic_year": clean_academic_year,
            "term": clean_term,
        },
        "result_stage": "finalised",
        "script_selection": "latest",
        "selected_assessment_count": selected_assessment_count,
        "assessments_with_results": assessments_with_results,
        "assessments_without_results": assessments_without_results,
        "candidate_allocation_count": total_candidate_count,
        "included_result_count": total_included_candidate_count,
        "excluded_incomplete_result_count": (total_excluded_incomplete_candidate_count),
        "unique_student_count": len(
            unique_student_ids,
        ),
        "candidate_inclusion_percentage": _percentage(
            total_included_candidate_count,
            total_candidate_count,
        ),
        "mean_percentage": _mean(
            percentages,
        ),
        "median_percentage": _median(
            percentages,
        ),
        "lowest_percentage": (
            _quantize(
                min(
                    percentages,
                )
            )
            if percentages
            else None
        ),
        "highest_percentage": (
            _quantize(
                max(
                    percentages,
                )
            )
            if percentages
            else None
        ),
        "graded_result_count": total_graded_candidate_count,
        "ungraded_result_count": total_ungraded_candidate_count,
        "pass_count": total_pass_count,
        "fail_count": total_fail_count,
        "pass_percentage": _percentage(
            total_pass_count,
            classified_pass_fail_count,
        ),
        "grade_distribution": grade_distribution,
        "assessments": assessment_rows,
    }


# ---------------------------------------------------------------------------
# Course view
# ---------------------------------------------------------------------------


async def get_course_assessment_performance(
    db: AsyncSession,
    current_user: User,
    *,
    course_id: int,
    school_id: int | None = None,
    academic_year: str | None = None,
    term: str | None = None,
) -> dict[str, Any]:
    """
    Return comparative assessment performance for one course.
    """

    return await get_assessment_cohort_performance(
        db,
        current_user,
        school_id=school_id,
        course_id=course_id,
        academic_year=academic_year,
        term=term,
    )


# ---------------------------------------------------------------------------
# Subject view
# ---------------------------------------------------------------------------


async def get_subject_assessment_performance(
    db: AsyncSession,
    current_user: User,
    *,
    subject_id: int,
    school_id: int | None = None,
    academic_year: str | None = None,
    term: str | None = None,
) -> dict[str, Any]:
    """
    Return comparative assessment performance across courses belonging to one
    canonical subject.
    """

    return await get_assessment_cohort_performance(
        db,
        current_user,
        school_id=school_id,
        subject_id=subject_id,
        academic_year=academic_year,
        term=term,
    )


# ---------------------------------------------------------------------------
# Teacher view
# ---------------------------------------------------------------------------


async def get_teacher_assessment_performance(
    db: AsyncSession,
    current_user: User,
    *,
    teacher_id: int,
    school_id: int | None = None,
    academic_year: str | None = None,
    term: str | None = None,
) -> dict[str, Any]:
    """
    Return comparative assessment performance for courses taught by one
    teacher.

    Existing access restrictions still apply. A non-admin teacher therefore
    cannot use this endpoint to inspect another teacher's assessments.
    """

    if (
        _is_teacher(current_user)
        and not _is_school_admin(current_user)
        and not _is_platform_admin(current_user)
        and teacher_id != current_user.id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only view cohort performance for your own courses.",
        )

    return await get_assessment_cohort_performance(
        db,
        current_user,
        school_id=school_id,
        teacher_id=teacher_id,
        academic_year=academic_year,
        term=term,
    )
