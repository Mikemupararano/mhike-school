from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.assessment import Assessment
from app.models.assessment_candidate import (
    AssessmentCandidate,
    AssessmentScript,
)
from app.models.assessment_question import AssessmentQuestion
from app.models.assessment_response import (
    AssessmentResponse,
    MarkingDecision,
    MarkingDecisionStatus,
)
from app.models.course import Course
from app.models.user import User, UserRole
from app.repositories.assessment_results import AssessmentResultsRepository
from app.repositories.course import CourseRepository

# ----------------------------------------------------------------------
# Role helpers
# ----------------------------------------------------------------------


def has_role(
    user: User,
    role: UserRole,
) -> bool:
    """
    Return whether the user currently has the supplied role.
    """

    return role.value in set(user.roles)


def is_platform_admin(
    user: User,
) -> bool:
    """
    Return whether the user has platform-administrator scope.
    """

    return has_role(
        user,
        UserRole.PLATFORM_ADMIN,
    )


def is_school_admin(
    user: User,
) -> bool:
    """
    Return whether the user has school-administrator scope.
    """

    return has_role(
        user,
        UserRole.SCHOOL_ADMIN,
    )


def is_teacher_without_admin_scope(
    user: User,
) -> bool:
    """
    Return whether the user is a teacher without administrator scope.
    """

    return (
        has_role(
            user,
            UserRole.TEACHER,
        )
        and not is_school_admin(user)
        and not is_platform_admin(user)
    )


def _ensure_results_staff_role(
    current_user: User,
) -> None:
    """
    Ensure the user has a role capable of viewing assessment results.
    """

    if (
        has_role(
            current_user,
            UserRole.TEACHER,
        )
        or is_school_admin(current_user)
        or is_platform_admin(current_user)
    ):
        return

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="You do not have permission to view assessment results",
    )


# ----------------------------------------------------------------------
# Numeric helpers
# ----------------------------------------------------------------------


_ZERO = Decimal("0")
_ONE_HUNDRED = Decimal("100")
_PERCENTAGE_QUANTUM = Decimal("0.01")


def _to_decimal(
    value: Decimal | int | float | str | None,
) -> Decimal:
    """
    Convert a supported numeric value to Decimal.

    None is treated as zero for derived-result calculations.
    """

    if value is None:
        return _ZERO

    if isinstance(value, Decimal):
        return value

    return Decimal(
        str(value),
    )


def _percentage(
    numerator: Decimal | int | float | str | None,
    denominator: Decimal | int | float | str | None,
) -> Decimal | None:
    """
    Return a percentage rounded to two decimal places.

    None is returned when the denominator is zero.
    """

    numerator_value = _to_decimal(
        numerator,
    )

    denominator_value = _to_decimal(
        denominator,
    )

    if denominator_value <= _ZERO:
        return None

    return ((numerator_value / denominator_value) * _ONE_HUNDRED).quantize(
        _PERCENTAGE_QUANTUM,
        rounding=ROUND_HALF_UP,
    )


def _completion_percentage(
    completed_count: int,
    total_count: int,
) -> Decimal | None:
    """
    Return a two-decimal completion percentage.
    """

    if total_count <= 0:
        return None

    return _percentage(
        Decimal(completed_count),
        Decimal(total_count),
    )


# ----------------------------------------------------------------------
# Lookup helpers
# ----------------------------------------------------------------------


async def _get_assessment_or_404(
    db: AsyncSession,
    assessment_id: int,
    *,
    include_results: bool = True,
) -> Assessment:
    """
    Return an assessment or raise a 404 response.
    """

    assessment = await AssessmentResultsRepository(
        db,
    ).get_assessment_by_id(
        assessment_id,
        include_results=include_results,
    )

    if assessment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assessment not found",
        )

    return assessment


async def _get_candidate_or_404(
    db: AsyncSession,
    candidate_id: int,
    *,
    include_results: bool = True,
) -> AssessmentCandidate:
    """
    Return an assessment candidate or raise a 404 response.
    """

    candidate = await AssessmentResultsRepository(
        db,
    ).get_candidate_by_id(
        candidate_id,
        include_results=include_results,
    )

    if candidate is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assessment candidate not found",
        )

    return candidate


async def _get_script_or_404(
    db: AsyncSession,
    script_id: int,
    *,
    include_results: bool = True,
) -> AssessmentScript:
    """
    Return an assessment script or raise a 404 response.
    """

    script = await AssessmentResultsRepository(
        db,
    ).get_script_by_id(
        script_id,
        include_results=include_results,
    )

    if script is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assessment script not found",
        )

    return script


async def _get_course_or_404(
    db: AsyncSession,
    course_id: int,
) -> Course:
    """
    Return a course or raise a 404 response.
    """

    course = await CourseRepository(
        db,
    ).get_by_id(
        course_id,
        include_relationships=False,
    )

    if course is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found",
        )

    return course


# ----------------------------------------------------------------------
# Access control
# ----------------------------------------------------------------------


async def _ensure_assessment_results_access(
    db: AsyncSession,
    current_user: User,
    assessment: Assessment,
) -> Course:
    """
    Ensure the current user may view results for an assessment.

    Teachers without administrative scope may view results only for courses
    they teach. School administrators may view results within their school.
    Platform administrators may view results across schools.
    """

    _ensure_results_staff_role(
        current_user,
    )

    if (
        not is_platform_admin(current_user)
        and assessment.school_id != current_user.school_id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Assessment does not belong to your school",
        )

    course = await _get_course_or_404(
        db,
        assessment.course_id,
    )

    if course.school_id != assessment.school_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Assessment and course school scope are inconsistent",
        )

    if (
        is_teacher_without_admin_scope(current_user)
        and course.teacher_id != current_user.id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only view results for your own courses",
        )

    return course


async def _ensure_candidate_results_access(
    db: AsyncSession,
    current_user: User,
    candidate: AssessmentCandidate,
) -> Assessment:
    """
    Ensure the user may view results for a candidate.
    """

    assessment = await _get_assessment_or_404(
        db,
        candidate.assessment_id,
        include_results=False,
    )

    await _ensure_assessment_results_access(
        db,
        current_user,
        assessment,
    )

    return assessment


async def _ensure_script_results_access(
    db: AsyncSession,
    current_user: User,
    script: AssessmentScript,
) -> tuple[AssessmentCandidate, Assessment]:
    """
    Ensure the user may view results for a script.
    """

    candidate = await _get_candidate_or_404(
        db,
        script.candidate_id,
        include_results=False,
    )

    assessment = await _ensure_candidate_results_access(
        db,
        current_user,
        candidate,
    )

    return candidate, assessment


# ----------------------------------------------------------------------
# Question-result helpers
# ----------------------------------------------------------------------


def _build_question_result(
    question: AssessmentQuestion,
    response: AssessmentResponse | None,
    decision: MarkingDecision | None,
) -> dict[str, Any]:
    """
    Build one question-level result representation.
    """

    maximum_mark = _to_decimal(
        question.maximum_mark,
    )

    mark_awarded = (
        _to_decimal(
            decision.mark_awarded,
        )
        if (decision is not None and decision.mark_awarded is not None)
        else None
    )

    return {
        "question_id": question.id,
        "question_number": question.question_number,
        "title": question.title,
        "maximum_mark": maximum_mark,
        "response_id": (response.id if response is not None else None),
        "response_status": (response.status if response is not None else None),
        "decision_id": (decision.id if decision is not None else None),
        "decision_status": (decision.status if decision is not None else None),
        "mark_awarded": mark_awarded,
        "percentage": (
            _percentage(
                mark_awarded,
                maximum_mark,
            )
            if mark_awarded is not None
            else None
        ),
        "is_marked": (
            decision is not None
            and decision.status
            in AssessmentResultsRepository.COMPLETED_MARKING_STATUSES
        ),
        "is_finalised": (
            decision is not None and decision.status == MarkingDecisionStatus.FINALISED
        ),
    }


# ----------------------------------------------------------------------
# Script result
# ----------------------------------------------------------------------


async def get_script_result(
    db: AsyncSession,
    current_user: User,
    script_id: int,
) -> dict[str, Any]:
    """
    Return a complete derived result for one assessment script.

    Both provisional and final result values are exposed:

    - mark_awarded:
        sum of every non-null question-level mark, including provisional
        in-progress marking;

    - completed_mark_awarded:
        sum of MARKED, REVIEWED, and FINALISED decisions;

    - finalised_mark_awarded:
        sum of FINALISED decisions only.

    Assessment maximum mark is always derived from all questions where
    is_markable=True.
    """

    script = await _get_script_or_404(
        db,
        script_id,
        include_results=False,
    )

    candidate, assessment = await _ensure_script_results_access(
        db,
        current_user,
        script,
    )

    repository = AssessmentResultsRepository(
        db,
    )

    maximum_mark = await repository.get_assessment_maximum_mark(
        assessment.id,
    )

    markable_question_count = await repository.count_markable_questions(
        assessment.id,
    )

    response_count = await repository.count_script_responses(
        script.id,
        exclude_void=True,
    )

    submitted_response_count = await repository.count_script_submitted_responses(
        script.id,
    )

    decision_count = await repository.count_script_decisions(
        script.id,
    )

    marked_question_count = await repository.count_script_completed_decisions(
        script.id,
    )

    finalised_question_count = await repository.count_script_finalised_decisions(
        script.id,
    )

    mark_awarded = await repository.get_script_mark_awarded(
        script.id,
    )

    completed_mark_awarded = await repository.get_script_mark_awarded(
        script.id,
        completed_only=True,
    )

    finalised_mark_awarded = await repository.get_script_mark_awarded(
        script.id,
        finalised_only=True,
    )

    question_rows = await repository.list_script_question_results(
        script.id,
    )

    question_results = [
        _build_question_result(
            question,
            response,
            decision,
        )
        for (
            question,
            response,
            decision,
        ) in question_rows
    ]

    return {
        "assessment_id": assessment.id,
        "candidate_id": candidate.id,
        "student_id": candidate.student_id,
        "script_id": script.id,
        "script_version": script.version,
        "script_status": script.status,
        "maximum_mark": maximum_mark,
        "mark_awarded": mark_awarded,
        "completed_mark_awarded": completed_mark_awarded,
        "finalised_mark_awarded": finalised_mark_awarded,
        "percentage": _percentage(
            mark_awarded,
            maximum_mark,
        ),
        "completed_percentage": _percentage(
            completed_mark_awarded,
            maximum_mark,
        ),
        "finalised_percentage": _percentage(
            finalised_mark_awarded,
            maximum_mark,
        ),
        "markable_question_count": markable_question_count,
        "response_count": response_count,
        "submitted_response_count": submitted_response_count,
        "decision_count": decision_count,
        "marked_question_count": marked_question_count,
        "finalised_question_count": finalised_question_count,
        "response_completion_percentage": _completion_percentage(
            response_count,
            markable_question_count,
        ),
        "marking_completion_percentage": _completion_percentage(
            marked_question_count,
            markable_question_count,
        ),
        "finalisation_completion_percentage": _completion_percentage(
            finalised_question_count,
            markable_question_count,
        ),
        "is_fully_responded": (
            markable_question_count > 0 and response_count >= markable_question_count
        ),
        "is_fully_marked": (
            markable_question_count > 0
            and marked_question_count >= markable_question_count
        ),
        "is_fully_finalised": (
            markable_question_count > 0
            and finalised_question_count >= markable_question_count
        ),
        "questions": question_results,
    }


# ----------------------------------------------------------------------
# Candidate result
# ----------------------------------------------------------------------


async def get_candidate_result(
    db: AsyncSession,
    current_user: User,
    candidate_id: int,
) -> dict[str, Any]:
    """
    Return results for every script version belonging to one candidate.

    No implicit "latest result wins" rule is applied. Every script version
    is retained and reported because version history is part of the current
    AssessmentScript design.

    ``latest_script_result`` is provided as a convenience view using the
    highest script version, with ID as a deterministic tiebreaker.
    """

    candidate = await _get_candidate_or_404(
        db,
        candidate_id,
        include_results=True,
    )

    assessment = await _ensure_candidate_results_access(
        db,
        current_user,
        candidate,
    )

    scripts = sorted(
        candidate.scripts,
        key=lambda script: (
            script.version,
            script.id,
        ),
    )

    script_results: list[dict[str, Any]] = []

    for script in scripts:
        script_results.append(
            await get_script_result(
                db,
                current_user,
                script.id,
            )
        )

    latest_script_result = script_results[-1] if script_results else None

    return {
        "assessment_id": assessment.id,
        "candidate_id": candidate.id,
        "student_id": candidate.student_id,
        "candidate_number": candidate.candidate_number,
        "candidate_status": candidate.status,
        "script_count": len(script_results),
        "scripts": script_results,
        "latest_script_result": latest_script_result,
    }


# ----------------------------------------------------------------------
# Assessment question analysis
# ----------------------------------------------------------------------


async def get_assessment_question_analysis(
    db: AsyncSession,
    current_user: User,
    assessment_id: int,
    *,
    completed_only: bool = True,
) -> list[dict[str, Any]]:
    """
    Return question-level analysis for every markable assessment question.
    """

    assessment = await _get_assessment_or_404(
        db,
        assessment_id,
        include_results=False,
    )

    await _ensure_assessment_results_access(
        db,
        current_user,
        assessment,
    )

    rows = await AssessmentResultsRepository(
        db,
    ).list_assessment_question_statistics(
        assessment.id,
        completed_only=completed_only,
    )

    output: list[dict[str, Any]] = []

    for row in rows:
        question = row["question"]

        if not isinstance(
            question,
            AssessmentQuestion,
        ):
            continue

        maximum_mark = _to_decimal(
            question.maximum_mark,
        )

        response_count = int(
            row["response_count"],
        )

        marked_count = int(
            row["marked_count"],
        )

        mark_sum = _to_decimal(
            row["mark_sum"],
        )

        mark_average = row["mark_average"]
        mark_minimum = row["mark_minimum"]
        mark_maximum = row["mark_maximum"]

        output.append(
            {
                "question_id": question.id,
                "question_number": question.question_number,
                "title": question.title,
                "maximum_mark": maximum_mark,
                "response_count": response_count,
                "marked_count": marked_count,
                "mark_sum": mark_sum,
                "mark_average": (
                    _to_decimal(mark_average) if mark_average is not None else None
                ),
                "mark_minimum": (
                    _to_decimal(mark_minimum) if mark_minimum is not None else None
                ),
                "mark_maximum": (
                    _to_decimal(mark_maximum) if mark_maximum is not None else None
                ),
                "average_percentage": (
                    _percentage(
                        mark_average,
                        maximum_mark,
                    )
                    if mark_average is not None
                    else None
                ),
                "marking_completion_percentage": (
                    _completion_percentage(
                        marked_count,
                        response_count,
                    )
                ),
            }
        )

    return output


# ----------------------------------------------------------------------
# Assessment result grid
# ----------------------------------------------------------------------


async def get_assessment_result_grid(
    db: AsyncSession,
    current_user: User,
    assessment_id: int,
) -> dict[str, Any]:
    """
    Return a compact script-level result grid for an assessment.

    This is intended for teacher/admin result screens where loading every
    question response for every script would be unnecessarily expensive.
    """

    assessment = await _get_assessment_or_404(
        db,
        assessment_id,
        include_results=False,
    )

    await _ensure_assessment_results_access(
        db,
        current_user,
        assessment,
    )

    repository = AssessmentResultsRepository(
        db,
    )

    maximum_mark = await repository.get_assessment_maximum_mark(
        assessment.id,
    )

    markable_question_count = await repository.count_markable_questions(
        assessment.id,
    )

    rows = await repository.list_assessment_script_mark_summaries(
        assessment.id,
    )

    scripts: list[dict[str, Any]] = []

    for row in rows:
        mark_awarded = _to_decimal(
            row["mark_awarded"],
        )

        completed_decision_count = int(
            row["completed_decision_count"],
        )

        finalised_decision_count = int(
            row["finalised_decision_count"],
        )

        scripts.append(
            {
                "script_id": row["script_id"],
                "candidate_id": row["candidate_id"],
                "version": row["version"],
                "script_status": row["script_status"],
                "response_count": row["response_count"],
                "decision_count": row["decision_count"],
                "mark_awarded": mark_awarded,
                "maximum_mark": maximum_mark,
                "percentage": _percentage(
                    mark_awarded,
                    maximum_mark,
                ),
                "completed_decision_count": completed_decision_count,
                "finalised_decision_count": finalised_decision_count,
                "marking_completion_percentage": (
                    _completion_percentage(
                        completed_decision_count,
                        markable_question_count,
                    )
                ),
                "finalisation_completion_percentage": (
                    _completion_percentage(
                        finalised_decision_count,
                        markable_question_count,
                    )
                ),
                "is_fully_marked": (
                    markable_question_count > 0
                    and completed_decision_count >= markable_question_count
                ),
                "is_fully_finalised": (
                    markable_question_count > 0
                    and finalised_decision_count >= markable_question_count
                ),
            }
        )

    return {
        "assessment_id": assessment.id,
        "title": assessment.title,
        "status": assessment.status,
        "maximum_mark": maximum_mark,
        "markable_question_count": markable_question_count,
        "script_count": len(scripts),
        "scripts": scripts,
    }


# ----------------------------------------------------------------------
# Assessment-wide summary
# ----------------------------------------------------------------------


async def get_assessment_results_summary(
    db: AsyncSession,
    current_user: User,
    assessment_id: int,
) -> dict[str, Any]:
    """
    Return assessment-wide marking and results summary data.

    Aggregate mark totals are deliberately reported as totals, not averages.
    Candidate-level means and distributions can be added later once the
    project defines how multiple script versions should contribute to formal
    assessment outcomes.
    """

    assessment = await _get_assessment_or_404(
        db,
        assessment_id,
        include_results=False,
    )

    await _ensure_assessment_results_access(
        db,
        current_user,
        assessment,
    )

    repository = AssessmentResultsRepository(
        db,
    )

    maximum_mark = await repository.get_assessment_maximum_mark(
        assessment.id,
    )

    markable_question_count = await repository.count_markable_questions(
        assessment.id,
    )

    candidate_count = await repository.count_assessment_candidates(
        assessment.id,
    )

    script_count = await repository.count_assessment_scripts(
        assessment.id,
    )

    completed_decision_count = await repository.count_assessment_decisions_by_status(
        assessment.id,
        repository.COMPLETED_MARKING_STATUSES,
    )

    finalised_decision_count = await repository.count_assessment_decisions_by_status(
        assessment.id,
        repository.FINAL_MARKING_STATUSES,
    )

    total_awarded_marks = await repository.get_assessment_total_awarded_marks(
        assessment.id,
    )

    completed_awarded_marks = await repository.get_assessment_total_awarded_marks(
        assessment.id,
        completed_only=True,
    )

    finalised_awarded_marks = await repository.get_assessment_total_awarded_marks(
        assessment.id,
        finalised_only=True,
    )

    expected_question_decisions = markable_question_count * script_count

    return {
        "assessment_id": assessment.id,
        "title": assessment.title,
        "status": assessment.status,
        "maximum_mark": maximum_mark,
        "markable_question_count": markable_question_count,
        "candidate_count": candidate_count,
        "script_count": script_count,
        "expected_question_decisions": expected_question_decisions,
        "completed_decision_count": completed_decision_count,
        "finalised_decision_count": finalised_decision_count,
        "marking_completion_percentage": (
            _completion_percentage(
                completed_decision_count,
                expected_question_decisions,
            )
        ),
        "finalisation_completion_percentage": (
            _completion_percentage(
                finalised_decision_count,
                expected_question_decisions,
            )
        ),
        "total_awarded_marks": total_awarded_marks,
        "completed_awarded_marks": completed_awarded_marks,
        "finalised_awarded_marks": finalised_awarded_marks,
    }
