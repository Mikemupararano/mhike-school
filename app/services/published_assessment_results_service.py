from __future__ import annotations

from decimal import Decimal
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.services.assessment_result_outcome_service import (
    get_authoritative_assessment_result_outcome,
)
from app.services.assessment_result_publication_service import (
    get_published_result_visibility,
)
from app.services.assessment_results_service import (
    get_candidate_result,
    get_script_result,
)


# ---------------------------------------------------------------------------
# Parent/student relationship helpers
# ---------------------------------------------------------------------------


def _extract_parent_student_ids(
    parent_user: User,
) -> set[int]:
    """
    Return student IDs linked to a parent user.

    The existing parent/student relationship layer is expected to populate
    one of the standard relationship collections used by the application.

    This helper deliberately accepts the common relationship forms already
    used across MHike School rather than duplicating relationship queries in
    this service.
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
                    int(
                        student_id,
                    ),
                )

            except (TypeError, ValueError):
                continue

    return student_ids


# ---------------------------------------------------------------------------
# Numeric helpers
# ---------------------------------------------------------------------------


def _to_decimal(
    value: Decimal | int | float | str | None,
) -> Decimal | None:
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


def _decimal_values_equal(
    first: Decimal | int | float | str | None,
    second: Decimal | int | float | str | None,
) -> bool:
    """
    Compare optional numeric result values deterministically.
    """

    return _to_decimal(
        first,
    ) == _to_decimal(
        second,
    )


# ---------------------------------------------------------------------------
# Public hiding helpers
# ---------------------------------------------------------------------------


def _published_result_not_found() -> HTTPException:
    """
    Return the deliberately generic public 404 response.

    Student and parent consumers must not receive internal publication,
    grading, result-history or candidate lifecycle information.
    """

    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Published assessment result not found.",
    )


# ---------------------------------------------------------------------------
# Publication visibility helpers
# ---------------------------------------------------------------------------


async def _get_publication_or_hidden(
    db: AsyncSession,
    *,
    assessment_id: int,
    audience: str,
):
    """
    Return active publication configuration or hide the result.

    Student and parent consumers should not be told whether an unpublished
    assessment exists. Therefore unavailable or hidden publication state is
    represented as HTTP 404 rather than exposing staff-only lifecycle data.
    """

    publication = await get_published_result_visibility(
        db,
        assessment_id=assessment_id,
    )

    if publication is None:
        raise _published_result_not_found()

    if audience == "student":
        visible = publication.visible_to_students

    elif audience == "parent":
        visible = publication.visible_to_parents

    else:
        raise ValueError(
            f"Unsupported published-result audience: {audience!r}",
        )

    if not visible:
        raise _published_result_not_found()

    return publication


# ---------------------------------------------------------------------------
# Authoritative-result helpers
# ---------------------------------------------------------------------------


async def _get_authoritative_outcome_or_hidden(
    db: AsyncSession,
    current_user: User,
    *,
    candidate_id: int,
) -> dict[str, Any]:
    """
    Return the candidate's current authoritative result outcome.

    Published results must never fall back to the candidate's latest script.
    If no authoritative outcome exists, there is no official result available
    to the public audience.
    """

    try:
        return await get_authoritative_assessment_result_outcome(
            db,
            current_user,
            candidate_id=candidate_id,
        )

    except HTTPException as exc:
        if exc.status_code in {
            status.HTTP_404_NOT_FOUND,
            status.HTTP_409_CONFLICT,
        }:
            raise _published_result_not_found() from exc

        raise


async def _get_authoritative_question_breakdown(
    db: AsyncSession,
    current_user: User,
    *,
    authoritative_outcome: dict[str, Any],
) -> list[dict[str, Any]] | None:
    """
    Return question results from the authoritative outcome's script.

    Question-level marks are not currently snapshotted in
    AssessmentResultOutcome. A remark or correction may therefore alter the
    same script while the previously authoritative aggregate result remains
    official.

    To avoid leaking pending, non-authoritative question changes, the live
    script breakdown is exposed only when its finalised aggregate result still
    agrees with the authoritative snapshot.
    """

    script_id = int(
        authoritative_outcome["script_id"],
    )

    try:
        script_result = await get_script_result(
            db=db,
            current_user=current_user,
            script_id=script_id,
        )

    except HTTPException as exc:
        if exc.status_code in {
            status.HTTP_404_NOT_FOUND,
            status.HTTP_409_CONFLICT,
        }:
            return None

        raise

    if int(
        script_result["candidate_id"],
    ) != int(
        authoritative_outcome["candidate_id"],
    ):
        return None

    if int(
        script_result["assessment_id"],
    ) != int(
        authoritative_outcome["assessment_id"],
    ):
        return None

    if int(
        script_result["script_version"],
    ) != int(
        authoritative_outcome["script_version_snapshot"],
    ):
        return None

    if not _decimal_values_equal(
        script_result.get(
            "finalised_mark_awarded",
        ),
        authoritative_outcome.get(
            "mark_awarded_snapshot",
        ),
    ):
        return None

    if not _decimal_values_equal(
        script_result.get(
            "finalised_percentage",
        ),
        authoritative_outcome.get(
            "percentage_snapshot",
        ),
    ):
        return None

    question_breakdown = script_result.get(
        "questions",
    )

    if question_breakdown is None:
        question_breakdown = script_result.get(
            "question_results",
        )

    if question_breakdown is None:
        return None

    return list(
        question_breakdown,
    )


# ---------------------------------------------------------------------------
# Public representation
# ---------------------------------------------------------------------------


async def _apply_publication_visibility(
    db: AsyncSession,
    current_user: User,
    *,
    publication,
    candidate_result: dict[str, Any],
    authoritative_outcome: dict[str, Any],
) -> dict[str, Any]:
    """
    Build the public result from the authoritative historical snapshot.

    Publication settings determine which official values are exposed.

    Crucially, no result value is taken from ``latest_script_result``.
    """

    if int(
        authoritative_outcome["candidate_id"],
    ) != int(
        candidate_result["candidate_id"],
    ):
        raise _published_result_not_found()

    if int(
        authoritative_outcome["assessment_id"],
    ) != int(
        candidate_result["assessment_id"],
    ):
        raise _published_result_not_found()

    mark_awarded = None

    if publication.include_mark:
        mark_awarded = authoritative_outcome.get(
            "mark_awarded_snapshot",
        )

    percentage = None

    if publication.include_percentage:
        percentage = authoritative_outcome.get(
            "percentage_snapshot",
        )

    grade = None
    grade_points = None
    is_pass = None

    if publication.include_grade:
        grade = authoritative_outcome.get(
            "grade_label_snapshot",
        )

        grade_points = authoritative_outcome.get(
            "grade_points_snapshot",
        )

        is_pass = authoritative_outcome.get(
            "is_pass_snapshot",
        )

    question_breakdown = None

    if publication.include_question_breakdown:
        question_breakdown = await _get_authoritative_question_breakdown(
            db,
            current_user,
            authoritative_outcome=authoritative_outcome,
        )

    return {
        "assessment_id": candidate_result.get(
            "assessment_id",
        ),
        "candidate_id": candidate_result.get(
            "candidate_id",
        ),
        "student_id": candidate_result.get(
            "student_id",
        ),
        "candidate_number": candidate_result.get(
            "candidate_number",
        ),
        "script_id": authoritative_outcome.get(
            "script_id",
        ),
        "script_version": authoritative_outcome.get(
            "script_version_snapshot",
        ),
        "mark_awarded": mark_awarded,
        "percentage": percentage,
        "grade": grade,
        "grade_points": grade_points,
        "is_pass": is_pass,
        "question_breakdown": question_breakdown,
        "release_message": publication.release_message,
        "published_at": publication.published_at,
        "visibility": {
            "include_mark": publication.include_mark,
            "include_percentage": publication.include_percentage,
            "include_grade": publication.include_grade,
            "include_question_breakdown": (
                publication.include_question_breakdown
            ),
        },
    }


# ---------------------------------------------------------------------------
# Student-facing result
# ---------------------------------------------------------------------------


async def get_student_published_assessment_result(
    db: AsyncSession,
    current_user: User,
    *,
    candidate_id: int,
) -> dict[str, Any]:
    """
    Return one published authoritative result for the logged-in student.

    A student may see only their own candidate record and only when the
    assessment's active publication explicitly allows student visibility.

    The result itself comes exclusively from the candidate's current
    authoritative AssessmentResultOutcome.
    """

    candidate_result = await get_candidate_result(
        db=db,
        current_user=current_user,
        candidate_id=candidate_id,
    )

    student_id = int(
        candidate_result["student_id"],
    )

    if student_id != current_user.id:
        raise _published_result_not_found()

    assessment_id = int(
        candidate_result["assessment_id"],
    )

    publication = await _get_publication_or_hidden(
        db,
        assessment_id=assessment_id,
        audience="student",
    )

    authoritative_outcome = await _get_authoritative_outcome_or_hidden(
        db,
        current_user,
        candidate_id=candidate_id,
    )

    return await _apply_publication_visibility(
        db,
        current_user,
        publication=publication,
        candidate_result=candidate_result,
        authoritative_outcome=authoritative_outcome,
    )


# ---------------------------------------------------------------------------
# Parent-facing result
# ---------------------------------------------------------------------------


async def get_parent_published_assessment_result(
    db: AsyncSession,
    current_user: User,
    *,
    candidate_id: int,
) -> dict[str, Any]:
    """
    Return one published authoritative result for a linked child.

    Parent-child authorisation is checked before publication data is returned.

    The result itself comes exclusively from the candidate's current
    authoritative AssessmentResultOutcome.
    """

    candidate_result = await get_candidate_result(
        db=db,
        current_user=current_user,
        candidate_id=candidate_id,
    )

    student_id = int(
        candidate_result["student_id"],
    )

    linked_student_ids = _extract_parent_student_ids(
        current_user,
    )

    if student_id not in linked_student_ids:
        raise _published_result_not_found()

    assessment_id = int(
        candidate_result["assessment_id"],
    )

    publication = await _get_publication_or_hidden(
        db,
        assessment_id=assessment_id,
        audience="parent",
    )

    authoritative_outcome = await _get_authoritative_outcome_or_hidden(
        db,
        current_user,
        candidate_id=candidate_id,
    )

    return await _apply_publication_visibility(
        db,
        current_user,
        publication=publication,
        candidate_result=candidate_result,
        authoritative_outcome=authoritative_outcome,
    )