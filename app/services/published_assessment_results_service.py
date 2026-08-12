from __future__ import annotations

from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.services.assessment_grading_service import (
    grade_candidate_latest_result,
)
from app.services.assessment_result_publication_service import (
    get_published_result_visibility,
)
from app.services.assessment_results_service import (
    get_candidate_result,
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
                    int(student_id),
                )
            except (TypeError, ValueError):
                continue

    return student_ids


# ---------------------------------------------------------------------------
# Visibility helpers
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
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Published assessment result not found.",
        )

    if audience == "student":
        visible = publication.visible_to_students

    elif audience == "parent":
        visible = publication.visible_to_parents

    else:
        raise ValueError(
            f"Unsupported published-result audience: {audience!r}",
        )

    if not visible:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Published assessment result not found.",
        )

    return publication


def _apply_publication_visibility(
    *,
    publication,
    candidate_result: dict[str, Any],
    grade_result: dict[str, Any] | None,
) -> dict[str, Any]:
    """
    Build the public result representation using publication flags.

    Hidden values are returned as ``None`` rather than omitted entirely so
    API clients can render a stable result structure while respecting
    school-configured visibility.
    """

    latest_script_result = candidate_result.get(
        "latest_script_result",
    )

    mark_awarded = None
    percentage = None

    if latest_script_result is not None:
        if publication.include_mark:
            mark_awarded = latest_script_result.get(
                "finalised_mark_awarded",
            )

        if publication.include_percentage:
            percentage = latest_script_result.get(
                "finalised_percentage",
            )

    grade = None
    grade_points = None
    is_pass = None

    if publication.include_grade and grade_result is not None:
        grade = grade_result.get(
            "grade",
        )

        grade_points = grade_result.get(
            "grade_points",
        )

        is_pass = grade_result.get(
            "is_pass",
        )

    question_breakdown = None

    if publication.include_question_breakdown and latest_script_result is not None:
        question_breakdown = latest_script_result.get(
            "questions",
        )

        if question_breakdown is None:
            question_breakdown = latest_script_result.get(
                "question_results",
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
        "script_id": (
            latest_script_result.get(
                "script_id",
            )
            if latest_script_result is not None
            else None
        ),
        "script_version": (
            latest_script_result.get(
                "script_version",
            )
            if latest_script_result is not None
            else None
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
            "include_question_breakdown": (publication.include_question_breakdown),
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
    Return one published assessment result for the logged-in student.

    A student may see only their own candidate record and only when the
    assessment's active publication explicitly allows student visibility.
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
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Published assessment result not found.",
        )

    assessment_id = int(
        candidate_result["assessment_id"],
    )

    publication = await _get_publication_or_hidden(
        db,
        assessment_id=assessment_id,
        audience="student",
    )

    grade_result: dict[str, Any] | None = None

    if publication.include_grade:
        try:
            grade_result = await grade_candidate_latest_result(
                db=db,
                current_user=current_user,
                candidate_id=candidate_id,
                result_stage="finalised",
            )
        except HTTPException as exc:
            if exc.status_code not in {
                status.HTTP_404_NOT_FOUND,
                status.HTTP_409_CONFLICT,
            }:
                raise

    return _apply_publication_visibility(
        publication=publication,
        candidate_result=candidate_result,
        grade_result=grade_result,
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
    Return one published assessment result for a linked child.

    Parent-child authorization is checked before any publication data is
    returned.
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
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Published assessment result not found.",
        )

    assessment_id = int(
        candidate_result["assessment_id"],
    )

    publication = await _get_publication_or_hidden(
        db,
        assessment_id=assessment_id,
        audience="parent",
    )

    grade_result: dict[str, Any] | None = None

    if publication.include_grade:
        try:
            grade_result = await grade_candidate_latest_result(
                db=db,
                current_user=current_user,
                candidate_id=candidate_id,
                result_stage="finalised",
            )
        except HTTPException as exc:
            if exc.status_code not in {
                status.HTTP_404_NOT_FOUND,
                status.HTTP_409_CONFLICT,
            }:
                raise

    return _apply_publication_visibility(
        publication=publication,
        candidate_result=candidate_result,
        grade_result=grade_result,
    )
