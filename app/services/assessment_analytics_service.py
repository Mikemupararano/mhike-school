from __future__ import annotations

from collections import Counter
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.assessment_candidate import AssessmentCandidate
from app.models.assessment_result_outcome import AssessmentResultOutcome
from app.models.user import User
from app.repositories.assessment_result_outcome import (
    AssessmentResultOutcomeRepository,
)
from app.repositories.assessment_results import AssessmentResultsRepository
from app.services.assessment_results_service import (
    get_assessment_question_analysis,
    get_assessment_results_summary,
    get_candidate_result,
)

_ZERO = Decimal("0")
_ONE_HUNDRED = Decimal("100")
_DECIMAL_QUANTUM = Decimal("0.01")


# ---------------------------------------------------------------------------
# Numeric helpers
# ---------------------------------------------------------------------------


def _to_decimal(
    value: Decimal | int | float | str | None,
) -> Decimal | None:
    """
    Convert a supported numeric value to Decimal.

    ``None`` remains ``None`` because absence of a formal result must not
    silently become a zero mark in analytics.
    """

    if value is None:
        return None

    if isinstance(
        value,
        Decimal,
    ):
        return value

    return Decimal(
        str(
            value,
        ),
    )


def _quantize(
    value: Decimal | None,
) -> Decimal | None:
    """
    Round an analytics value to two decimal places.
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
        str(
            numerator,
        ),
    )

    denominator_value = Decimal(
        str(
            denominator,
        ),
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
    Return the arithmetic mean of Decimal values.
    """

    if not values:
        return None

    return _quantize(
        sum(
            values,
            _ZERO,
        )
        / Decimal(
            len(
                values,
            ),
        ),
    )


def _median(
    values: list[Decimal],
) -> Decimal | None:
    """
    Return the median of Decimal values.
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
        (ordered[midpoint - 1] + ordered[midpoint])
        / Decimal(
            "2",
        ),
    )


# ---------------------------------------------------------------------------
# Candidate helpers
# ---------------------------------------------------------------------------


def _latest_script_sort_key(
    script,
) -> tuple[int, int]:
    """
    Return the deterministic ordering used for current script state.

    Script version is primary and database ID is the tiebreaker.

    This helper remains useful for operational marking-state metrics. It is
    deliberately not used to decide a candidate's official result.
    """

    return (
        int(
            script.version,
        ),
        int(
            script.id,
        ),
    )


def _latest_candidate_script(
    candidate: AssessmentCandidate,
):
    """
    Return a candidate's latest script version, or None.

    Latest-script selection describes current marking activity only. Formal
    analytics are sourced from AssessmentResultOutcome.
    """

    scripts = list(
        candidate.scripts or [],
    )

    if not scripts:
        return None

    return max(
        scripts,
        key=_latest_script_sort_key,
    )


# ---------------------------------------------------------------------------
# Ranking helpers
# ---------------------------------------------------------------------------


def _apply_competition_ranks(
    rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Apply standard competition ranking to authoritative results.

    Example:

        90 -> rank 1
        90 -> rank 1
        80 -> rank 3
        70 -> rank 4

    Candidate ID is used only as a deterministic ordering tiebreaker. It does
    not break equal-score ranks.
    """

    ordered = sorted(
        rows,
        key=lambda row: (
            -row["percentage"],
            -row["mark_awarded"],
            row["candidate_id"],
        ),
    )

    previous_percentage: Decimal | None = None
    previous_mark: Decimal | None = None
    current_rank = 0

    for position, row in enumerate(
        ordered,
        start=1,
    ):
        percentage = row["percentage"]
        mark_awarded = row["mark_awarded"]

        if (
            previous_percentage is None
            or percentage != previous_percentage
            or mark_awarded != previous_mark
        ):
            current_rank = position

        row["rank"] = current_rank

        previous_percentage = percentage
        previous_mark = mark_awarded

    return ordered


# ---------------------------------------------------------------------------
# Grade-distribution helpers
# ---------------------------------------------------------------------------


def _build_grade_distribution(
    grades: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Build a deterministic grade distribution.

    Grade data is supplied from immutable authoritative result snapshots.

    ``minimum_value`` remains optional because AssessmentResultOutcome
    snapshots the resolved grade and boundary identity but does not currently
    snapshot the historic boundary minimum. Analytics must therefore never
    reconstruct that value from today's grading configuration.
    """

    grade_counts: Counter[str] = Counter()

    grade_metadata: dict[
        str,
        dict[str, Any],
    ] = {}

    grade_order: list[str] = []

    for result in grades:
        grade = result.get(
            "grade",
        )

        if grade is None:
            continue

        grade_label = str(
            grade,
        )

        if grade_label not in grade_metadata:
            grade_order.append(
                grade_label,
            )

            grade_metadata[grade_label] = {
                "grade": grade_label,
                "minimum_value": result.get(
                    "minimum_value",
                ),
                "grade_points": result.get(
                    "grade_points",
                ),
                "is_pass": result.get(
                    "is_pass",
                ),
            }

        grade_counts[grade_label] += 1

    graded_count = sum(
        grade_counts.values(),
    )

    output: list[dict[str, Any]] = []

    for grade_label in grade_order:
        count = grade_counts[grade_label]

        output.append(
            {
                **grade_metadata[grade_label],
                "count": count,
                "percentage": _percentage(
                    count,
                    graded_count,
                ),
            },
        )

    return output


# ---------------------------------------------------------------------------
# Assessment context
# ---------------------------------------------------------------------------


async def _get_assessment_candidates(
    db: AsyncSession,
    current_user: User,
    assessment_id: int,
) -> tuple[
    dict[str, Any],
    list[AssessmentCandidate],
]:
    """
    Resolve assessment scope and return its candidates.

    ``get_assessment_results_summary`` is deliberately called first because
    it is the existing authority for:

    - staff-role validation;
    - teacher course ownership;
    - school isolation;
    - platform-administrator scope.

    Analytics therefore does not implement a second access-control policy.
    """

    summary = await get_assessment_results_summary(
        db=db,
        current_user=current_user,
        assessment_id=assessment_id,
    )

    assessment = await AssessmentResultsRepository(
        db,
    ).get_assessment_by_id(
        assessment_id,
        include_results=True,
    )

    if assessment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assessment not found",
        )

    candidates = sorted(
        list(
            assessment.candidates or [],
        ),
        key=lambda candidate: candidate.id,
    )

    return (
        summary,
        candidates,
    )


# ---------------------------------------------------------------------------
# Authoritative-outcome helpers
# ---------------------------------------------------------------------------


def _authoritative_outcome_map(
    outcomes: list[AssessmentResultOutcome],
    *,
    assessment_id: int,
) -> dict[int, AssessmentResultOutcome]:
    """
    Build a candidate-ID lookup for authoritative assessment outcomes.

    The database already enforces at most one authoritative outcome per
    candidate. These defensive checks also protect analytics from inconsistent
    repository data or cross-assessment records.
    """

    output: dict[int, AssessmentResultOutcome] = {}

    for outcome in outcomes:
        if int(
            outcome.assessment_id,
        ) != int(
            assessment_id,
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "Authoritative assessment result history is "
                    "inconsistent with the requested assessment."
                ),
            )

        if not bool(
            outcome.is_authoritative,
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "A non-authoritative result was returned while "
                    "building authoritative assessment analytics."
                ),
            )

        candidate_id = int(
            outcome.candidate_id,
        )

        if candidate_id in output:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "More than one authoritative result was returned "
                    "for an assessment candidate."
                ),
            )

        output[candidate_id] = outcome

    return output


def _build_authoritative_grade_result(
    outcome: AssessmentResultOutcome,
) -> dict[str, Any]:
    """
    Build the grade-distribution representation from an outcome snapshot.

    Historical grades are never recalculated from the currently active
    grading scheme.
    """

    grade_points = _to_decimal(
        outcome.grade_points_snapshot,
    )

    return {
        "grade": outcome.grade_label_snapshot,
        "minimum_value": None,
        "grade_points": (
            _quantize(
                grade_points,
            )
            if grade_points is not None
            else None
        ),
        "is_pass": outcome.is_pass_snapshot,
    }


def _authoritative_candidate_row(
    *,
    candidate: AssessmentCandidate,
    outcome: AssessmentResultOutcome,
) -> dict[str, Any]:
    """
    Build one formal candidate analytics row from an immutable outcome.
    """

    if int(
        outcome.candidate_id,
    ) != int(
        candidate.id,
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Authoritative result outcome and assessment candidate "
                "are inconsistent."
            ),
        )

    mark_awarded = _to_decimal(
        outcome.mark_awarded_snapshot,
    )

    maximum_mark = _to_decimal(
        outcome.maximum_mark_snapshot,
    )

    percentage = _to_decimal(
        outcome.percentage_snapshot,
    )

    if mark_awarded is None or maximum_mark is None or percentage is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "An authoritative assessment result outcome does not "
                "contain a complete formal mark snapshot."
            ),
        )

    grade_points = _to_decimal(
        outcome.grade_points_snapshot,
    )

    return {
        "candidate_id": candidate.id,
        "student_id": candidate.student_id,
        "candidate_number": candidate.candidate_number,
        "candidate_status": candidate.status,
        "script_id": outcome.script_id,
        "script_version": outcome.script_version_snapshot,
        "mark_awarded": _quantize(
            mark_awarded,
        ),
        "maximum_mark": _quantize(
            maximum_mark,
        ),
        "percentage": _quantize(
            percentage,
        ),
        "grade": outcome.grade_label_snapshot,
        "grade_points": (
            _quantize(
                grade_points,
            )
            if grade_points is not None
            else None
        ),
        "is_pass": outcome.is_pass_snapshot,
        "rank": None,
    }


# ---------------------------------------------------------------------------
# Candidate analytics
# ---------------------------------------------------------------------------


async def _build_candidate_analytics(
    db: AsyncSession,
    current_user: User,
    candidates: list[AssessmentCandidate],
    *,
    assessment_id: int,
) -> tuple[
    list[dict[str, Any]],
    list[dict[str, Any]],
    dict[str, int],
]:
    """
    Build formal candidate analytics from authoritative result outcomes.

    Latest-script data remains useful for operational marking metrics:

    - candidates with or without scripts;
    - fully marked candidates;
    - fully finalised candidates;
    - candidates whose latest work is incomplete.

    Formal statistics are different. Marks, percentages, grades, rankings,
    pass/fail classifications and official script identity come exclusively
    from the current authoritative AssessmentResultOutcome.

    Consequently:

    - a newer retake does not alter formal analytics until authorised;
    - a pending remark does not alter formal analytics;
    - a grading-scheme change does not rewrite historic formal grades;
    - one candidate contributes at most one official result.
    """

    candidate_rows: list[dict[str, Any]] = []
    grade_results: list[dict[str, Any]] = []

    counts = {
        "with_script": 0,
        "without_script": 0,
        "fully_marked": 0,
        "fully_finalised": 0,
        "included_in_statistics": 0,
        "excluded_incomplete": 0,
        "without_authoritative_result": 0,
        "graded": 0,
        "ungraded": 0,
    }

    authoritative_outcomes = await AssessmentResultOutcomeRepository(
        db,
    ).list_for_assessment(
        assessment_id,
        authoritative_only=True,
    )

    outcome_by_candidate_id = _authoritative_outcome_map(
        authoritative_outcomes,
        assessment_id=assessment_id,
    )

    candidate_ids = {
        int(
            candidate.id,
        )
        for candidate in candidates
    }

    orphaned_outcome_candidate_ids = (
        set(
            outcome_by_candidate_id,
        )
        - candidate_ids
    )

    if orphaned_outcome_candidate_ids:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Authoritative result history contains a candidate "
                "outside the requested assessment candidate set."
            ),
        )

    for candidate in candidates:
        candidate_id = int(
            candidate.id,
        )

        latest_script = _latest_candidate_script(
            candidate,
        )

        outcome = outcome_by_candidate_id.get(
            candidate_id,
        )

        if latest_script is None:
            counts["without_script"] += 1

            if outcome is None:
                counts["without_authoritative_result"] += 1
                continue

            # An authoritative result should always reference a retained
            # assessment script. Reaching this state indicates inconsistent
            # loaded assessment relationships.
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "An authoritative assessment result exists for a "
                    "candidate with no assessment script."
                ),
            )

        counts["with_script"] += 1

        candidate_result = await get_candidate_result(
            db=db,
            current_user=current_user,
            candidate_id=candidate_id,
        )

        if (
            int(
                candidate_result["candidate_id"],
            )
            != candidate_id
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "Assessment candidate analytics resolved an "
                    "inconsistent candidate result."
                ),
            )

        if int(
            candidate_result["assessment_id"],
        ) != int(
            assessment_id,
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "Assessment candidate analytics resolved a result "
                    "for a different assessment."
                ),
            )

        latest = candidate_result.get(
            "latest_script_result",
        )

        if latest is None:
            counts["without_script"] += 1
            counts["with_script"] -= 1

            if outcome is None:
                counts["without_authoritative_result"] += 1
                continue

            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "An authoritative assessment result exists but the "
                    "candidate result contains no assessment script."
                ),
            )

        is_fully_marked = bool(
            latest.get(
                "is_fully_marked",
            ),
        )

        is_fully_finalised = bool(
            latest.get(
                "is_fully_finalised",
            ),
        )

        if is_fully_marked:
            counts["fully_marked"] += 1

        if is_fully_finalised:
            counts["fully_finalised"] += 1

        latest_finalised_mark = _to_decimal(
            latest.get(
                "finalised_mark_awarded",
            ),
        )

        latest_finalised_percentage = _to_decimal(
            latest.get(
                "finalised_percentage",
            ),
        )

        latest_is_complete = (
            is_fully_finalised
            and latest_finalised_mark is not None
            and latest_finalised_percentage is not None
        )

        if not latest_is_complete:
            counts["excluded_incomplete"] += 1

        if outcome is None:
            counts["without_authoritative_result"] += 1
            continue

        if int(
            outcome.assessment_id,
        ) != int(
            assessment_id,
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "Authoritative assessment result and assessment "
                    "analytics scope are inconsistent."
                ),
            )

        candidate_rows.append(
            _authoritative_candidate_row(
                candidate=candidate,
                outcome=outcome,
            ),
        )

        counts["included_in_statistics"] += 1

        grade_result = _build_authoritative_grade_result(
            outcome,
        )

        grade = grade_result.get(
            "grade",
        )

        if grade is None:
            counts["ungraded"] += 1

        else:
            counts["graded"] += 1

            grade_results.append(
                grade_result,
            )

    return (
        candidate_rows,
        grade_results,
        counts,
    )


# ---------------------------------------------------------------------------
# Main assessment analytics
# ---------------------------------------------------------------------------


async def get_assessment_analytics(
    db: AsyncSession,
    current_user: User,
    assessment_id: int,
) -> dict[str, Any]:
    """
    Return formal analytics for one assessment.

    Candidate-level formal statistics use each candidate's current
    authoritative AssessmentResultOutcome.

    Latest scripts remain relevant to operational marking-completion metrics,
    but they do not automatically replace an official result.

    This preserves one candidate = one formal analytics result while allowing
    retakes, remarks and corrections to exist safely before authorisation.
    """

    (
        results_summary,
        candidates,
    ) = await _get_assessment_candidates(
        db,
        current_user,
        assessment_id,
    )

    (
        candidate_rows,
        grade_results,
        counts,
    ) = await _build_candidate_analytics(
        db,
        current_user,
        candidates,
        assessment_id=assessment_id,
    )

    ranked_candidates = _apply_competition_ranks(
        candidate_rows,
    )

    marks = [
        row["mark_awarded"]
        for row in ranked_candidates
        if row.get(
            "mark_awarded",
        )
        is not None
    ]

    percentages = [
        row["percentage"]
        for row in ranked_candidates
        if row.get(
            "percentage",
        )
        is not None
    ]

    # Question-level analytics currently describe live/current marking data.
    #
    # AssessmentResultOutcome snapshots aggregate official outcomes rather
    # than immutable question-level decisions. Formal candidate statistics
    # therefore use authoritative outcome snapshots while this question
    # section retains its existing operational meaning until question-level
    # marking history is introduced.
    question_analysis = await get_assessment_question_analysis(
        db=db,
        current_user=current_user,
        assessment_id=assessment_id,
        completed_only=True,
    )

    grade_distribution = _build_grade_distribution(
        grade_results,
    )

    pass_count = sum(
        1
        for row in ranked_candidates
        if row.get(
            "is_pass",
        )
        is True
    )

    fail_count = sum(
        1
        for row in ranked_candidates
        if row.get(
            "is_pass",
        )
        is False
    )

    classified_pass_fail_count = pass_count + fail_count

    candidate_count = int(
        results_summary["candidate_count"],
    )

    included_count = counts["included_in_statistics"]

    return {
        "assessment_id": results_summary["assessment_id"],
        "title": results_summary["title"],
        "status": results_summary["status"],
        "result_stage": "authoritative",
        "script_selection": "authoritative",
        "maximum_mark": _quantize(
            _to_decimal(
                results_summary["maximum_mark"],
            ),
        ),
        "markable_question_count": results_summary["markable_question_count"],
        "candidate_count": candidate_count,
        "script_count": results_summary["script_count"],
        "candidates_with_script": counts["with_script"],
        "candidates_without_script": counts["without_script"],
        "fully_marked_candidate_count": counts["fully_marked"],
        "fully_finalised_candidate_count": counts["fully_finalised"],
        "included_candidate_count": included_count,
        "excluded_incomplete_candidate_count": counts["excluded_incomplete"],
        "candidates_without_authoritative_result": counts[
            "without_authoritative_result"
        ],
        "candidate_inclusion_percentage": _percentage(
            included_count,
            candidate_count,
        ),
        "marking_completion_percentage": results_summary[
            "marking_completion_percentage"
        ],
        "finalisation_completion_percentage": results_summary[
            "finalisation_completion_percentage"
        ],
        "mean_mark": _mean(
            marks,
        ),
        "median_mark": _median(
            marks,
        ),
        "lowest_mark": (
            _quantize(
                min(
                    marks,
                ),
            )
            if marks
            else None
        ),
        "highest_mark": (
            _quantize(
                max(
                    marks,
                ),
            )
            if marks
            else None
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
                ),
            )
            if percentages
            else None
        ),
        "highest_percentage": (
            _quantize(
                max(
                    percentages,
                ),
            )
            if percentages
            else None
        ),
        "graded_candidate_count": counts["graded"],
        "ungraded_candidate_count": counts["ungraded"],
        "pass_count": pass_count,
        "fail_count": fail_count,
        "pass_percentage": _percentage(
            pass_count,
            classified_pass_fail_count,
        ),
        "grade_distribution": grade_distribution,
        "ranking": ranked_candidates,
        "questions": question_analysis,
    }


# ---------------------------------------------------------------------------
# Compact cohort summary
# ---------------------------------------------------------------------------


async def get_assessment_analytics_summary(
    db: AsyncSession,
    current_user: User,
    assessment_id: int,
) -> dict[str, Any]:
    """
    Return formal assessment analytics without ranking or question rows.

    This is intended for dashboards and list views where the full analytics
    payload would be unnecessarily large.
    """

    analytics = await get_assessment_analytics(
        db=db,
        current_user=current_user,
        assessment_id=assessment_id,
    )

    return {
        key: value
        for key, value in analytics.items()
        if key
        not in {
            "ranking",
            "questions",
        }
    }


# ---------------------------------------------------------------------------
# Ranking view
# ---------------------------------------------------------------------------


async def get_assessment_candidate_ranking(
    db: AsyncSession,
    current_user: User,
    assessment_id: int,
) -> list[dict[str, Any]]:
    """
    Return candidate ranking based on authoritative result outcomes.

    Ties use standard competition ranking.
    """

    analytics = await get_assessment_analytics(
        db=db,
        current_user=current_user,
        assessment_id=assessment_id,
    )

    return list(
        analytics["ranking"],
    )


# ---------------------------------------------------------------------------
# Grade-distribution view
# ---------------------------------------------------------------------------


async def get_assessment_grade_distribution(
    db: AsyncSession,
    current_user: User,
    assessment_id: int,
) -> dict[str, Any]:
    """
    Return the formal authoritative grade distribution for an assessment.

    Grades come from historical outcome snapshots rather than the currently
    active grading scheme. Authoritative outcomes without a resolved grade
    remain valid mark results and are counted as ungraded.
    """

    analytics = await get_assessment_analytics(
        db=db,
        current_user=current_user,
        assessment_id=assessment_id,
    )

    return {
        "assessment_id": analytics["assessment_id"],
        "graded_candidate_count": analytics["graded_candidate_count"],
        "ungraded_candidate_count": analytics["ungraded_candidate_count"],
        "pass_count": analytics["pass_count"],
        "fail_count": analytics["fail_count"],
        "pass_percentage": analytics["pass_percentage"],
        "grades": analytics["grade_distribution"],
    }
