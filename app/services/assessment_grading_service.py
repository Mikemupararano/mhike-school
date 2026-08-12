from __future__ import annotations

from decimal import Decimal
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.assessment_grading import (
    AssessmentGradeBoundary,
    AssessmentGradingBasis,
    AssessmentGradingScheme,
)
from app.models.user import User
from app.repositories.assessment_grading import AssessmentGradingRepository
from app.services.assessment_results_service import (
    get_assessment_results_summary,
    get_candidate_result,
    get_script_result,
)

_UNSET = object()

_ZERO = Decimal("0")
_ONE_HUNDRED = Decimal("100")


# ---------------------------------------------------------------------------
# Normalisation helpers
# ---------------------------------------------------------------------------


def _normalise_required_text(
    value: str,
    *,
    field_name: str,
) -> str:
    """
    Return a required trimmed string.
    """

    if not isinstance(value, str):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"{field_name} must be a string.",
        )

    cleaned = value.strip()

    if not cleaned:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"{field_name} cannot be blank.",
        )

    return cleaned


def _normalise_optional_text(
    value: str | None,
) -> str | None:
    """
    Return trimmed optional text or None.
    """

    if value is None:
        return None

    cleaned = value.strip()

    return cleaned or None


def _normalise_basis(
    value: AssessmentGradingBasis | str,
) -> AssessmentGradingBasis:
    """
    Return a valid grading basis.
    """

    if isinstance(
        value,
        AssessmentGradingBasis,
    ):
        return value

    if not isinstance(value, str):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Invalid assessment grading basis.",
        )

    try:
        return AssessmentGradingBasis(
            value.strip(),
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Invalid assessment grading basis.",
        ) from exc


def _normalise_decimal(
    value: Decimal | int | float | str,
    *,
    field_name: str,
) -> Decimal:
    """
    Return a Decimal value or raise HTTP 422.
    """

    try:
        decimal_value = Decimal(
            str(value),
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"{field_name} must be numeric.",
        ) from exc

    if not decimal_value.is_finite():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"{field_name} must be finite.",
        )

    return decimal_value


def _normalise_positive_order(
    value: int,
) -> int:
    """
    Return a valid positive display order.
    """

    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Boundary order must be a positive integer.",
        )

    return value


# ---------------------------------------------------------------------------
# Persistence helpers
# ---------------------------------------------------------------------------


async def _commit_grading_change(
    db: AsyncSession,
    *,
    duplicate_detail: str,
) -> None:
    """
    Commit a grading mutation and translate uniqueness failures.
    """

    try:
        await db.commit()

    except IntegrityError as exc:
        await db.rollback()

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=duplicate_detail,
        ) from exc


# ---------------------------------------------------------------------------
# Assessment scope
# ---------------------------------------------------------------------------


async def _get_assessment_context(
    db: AsyncSession,
    current_user: User,
    assessment_id: int,
) -> dict[str, Any]:
    """
    Resolve an assessment and enforce existing results access rules.

    Reusing the assessment-results service keeps teacher ownership,
    school isolation and administrator scope consistent across the
    assessment subsystem.
    """

    return await get_assessment_results_summary(
        db=db,
        current_user=current_user,
        assessment_id=assessment_id,
    )


# ---------------------------------------------------------------------------
# Scheme lookups
# ---------------------------------------------------------------------------


async def _get_scheme_or_404(
    db: AsyncSession,
    scheme_id: int,
) -> AssessmentGradingScheme:
    """
    Return one grading scheme or raise HTTP 404.
    """

    scheme = await AssessmentGradingRepository(
        db,
    ).get_scheme_by_id(
        scheme_id,
    )

    if scheme is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assessment grading scheme not found.",
        )

    return scheme


async def _get_assessment_scheme_or_404(
    db: AsyncSession,
    assessment_id: int,
) -> AssessmentGradingScheme:
    """
    Return an assessment grading scheme or raise HTTP 404.
    """

    scheme = await AssessmentGradingRepository(
        db,
    ).get_scheme_for_assessment(
        assessment_id,
    )

    if scheme is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assessment grading scheme not found.",
        )

    return scheme


async def _get_active_assessment_scheme_or_404(
    db: AsyncSession,
    assessment_id: int,
) -> AssessmentGradingScheme:
    """
    Return the active grading scheme for an assessment.
    """

    scheme = await AssessmentGradingRepository(
        db,
    ).get_active_scheme_for_assessment(
        assessment_id,
    )

    if scheme is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active grading scheme is configured for this assessment.",
        )

    return scheme


async def _get_boundary_or_404(
    db: AsyncSession,
    boundary_id: int,
) -> AssessmentGradeBoundary:
    """
    Return one grade boundary or raise HTTP 404.
    """

    boundary = await AssessmentGradingRepository(
        db,
    ).get_boundary_by_id(
        boundary_id,
    )

    if boundary is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assessment grade boundary not found.",
        )

    return boundary


# ---------------------------------------------------------------------------
# Boundary validation
# ---------------------------------------------------------------------------


def _validate_boundary_value(
    *,
    basis: AssessmentGradingBasis,
    minimum_value: Decimal,
    assessment_maximum_mark: Decimal,
) -> None:
    """
    Validate a boundary threshold against its grading basis.
    """

    if minimum_value < _ZERO:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Grade boundary minimum value cannot be negative.",
        )

    if basis == AssessmentGradingBasis.PERCENTAGE:
        if minimum_value > _ONE_HUNDRED:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Percentage grade boundaries cannot exceed 100.",
            )

        return

    if basis == AssessmentGradingBasis.RAW_MARK:
        if assessment_maximum_mark <= _ZERO:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "Raw-mark grading cannot be configured until the "
                    "assessment has a positive maximum mark."
                ),
            )

        if minimum_value > assessment_maximum_mark:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=(
                    "Raw-mark grade boundary cannot exceed the "
                    "assessment maximum mark."
                ),
            )


async def _validate_existing_boundaries_for_basis(
    db: AsyncSession,
    *,
    scheme: AssessmentGradingScheme,
    basis: AssessmentGradingBasis,
    assessment_maximum_mark: Decimal,
) -> None:
    """
    Ensure every existing boundary remains valid under a new basis.
    """

    boundaries = await AssessmentGradingRepository(
        db,
    ).list_boundaries(
        scheme.id,
    )

    for boundary in boundaries:
        _validate_boundary_value(
            basis=basis,
            minimum_value=Decimal(
                str(boundary.minimum_value),
            ),
            assessment_maximum_mark=assessment_maximum_mark,
        )


# ---------------------------------------------------------------------------
# Scheme service
# ---------------------------------------------------------------------------


async def create_grading_scheme(
    db: AsyncSession,
    current_user: User,
    *,
    assessment_id: int,
    name: str,
    basis: AssessmentGradingBasis | str,
    description: str | None = None,
    is_active: bool = True,
) -> AssessmentGradingScheme:
    """
    Create the grading scheme for an assessment.

    The database and service both enforce one scheme per assessment.
    """

    assessment_context = await _get_assessment_context(
        db,
        current_user,
        assessment_id,
    )

    repository = AssessmentGradingRepository(
        db,
    )

    existing = await repository.get_scheme_for_assessment(
        assessment_id,
    )

    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This assessment already has a grading scheme.",
        )

    clean_name = _normalise_required_text(
        name,
        field_name="Grading scheme name",
    )

    clean_description = _normalise_optional_text(
        description,
    )

    normalised_basis = _normalise_basis(
        basis,
    )

    maximum_mark = Decimal(
        str(
            assessment_context["maximum_mark"],
        ),
    )

    if normalised_basis == AssessmentGradingBasis.RAW_MARK and maximum_mark <= _ZERO:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Raw-mark grading cannot be configured until the "
                "assessment has a positive maximum mark."
            ),
        )

    scheme = await repository.create_scheme(
        assessment_id=assessment_id,
        name=clean_name,
        description=clean_description,
        basis=normalised_basis,
        is_active=is_active,
        created_by_id=current_user.id,
    )

    await _commit_grading_change(
        db,
        duplicate_detail="This assessment already has a grading scheme.",
    )

    return await repository.get_scheme_by_id(
        scheme.id,
    )


async def get_grading_scheme(
    db: AsyncSession,
    current_user: User,
    *,
    assessment_id: int,
) -> AssessmentGradingScheme:
    """
    Return the grading scheme configured for an assessment.
    """

    await _get_assessment_context(
        db,
        current_user,
        assessment_id,
    )

    return await _get_assessment_scheme_or_404(
        db,
        assessment_id,
    )


async def update_grading_scheme(
    db: AsyncSession,
    current_user: User,
    *,
    scheme_id: int,
    name: str | object = _UNSET,
    description: str | None | object = _UNSET,
    basis: AssessmentGradingBasis | str | object = _UNSET,
    is_active: bool | object = _UNSET,
) -> AssessmentGradingScheme:
    """
    Update an assessment grading scheme.

    Changing grading basis is allowed only when every existing threshold
    remains valid under the new basis.
    """

    scheme = await _get_scheme_or_404(
        db,
        scheme_id,
    )

    assessment_context = await _get_assessment_context(
        db,
        current_user,
        scheme.assessment_id,
    )

    if name is not _UNSET:
        scheme.name = _normalise_required_text(
            name,
            field_name="Grading scheme name",
        )

    if description is not _UNSET:
        scheme.description = _normalise_optional_text(
            description,
        )

    if basis is not _UNSET:
        normalised_basis = _normalise_basis(
            basis,
        )

        maximum_mark = Decimal(
            str(
                assessment_context["maximum_mark"],
            ),
        )

        await _validate_existing_boundaries_for_basis(
            db,
            scheme=scheme,
            basis=normalised_basis,
            assessment_maximum_mark=maximum_mark,
        )

        if (
            normalised_basis == AssessmentGradingBasis.RAW_MARK
            and maximum_mark <= _ZERO
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "Raw-mark grading cannot be configured until the "
                    "assessment has a positive maximum mark."
                ),
            )

        scheme.basis = normalised_basis

    if is_active is not _UNSET:
        if not isinstance(is_active, bool):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="is_active must be a boolean.",
            )

        scheme.is_active = is_active

    repository = AssessmentGradingRepository(
        db,
    )

    await repository.flush()

    await _commit_grading_change(
        db,
        duplicate_detail="Unable to update assessment grading scheme.",
    )

    updated = await repository.get_scheme_by_id(
        scheme.id,
    )

    if updated is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assessment grading scheme not found.",
        )

    return updated


async def delete_grading_scheme(
    db: AsyncSession,
    current_user: User,
    *,
    scheme_id: int,
) -> None:
    """
    Delete a grading scheme and all of its boundaries.
    """

    scheme = await _get_scheme_or_404(
        db,
        scheme_id,
    )

    await _get_assessment_context(
        db,
        current_user,
        scheme.assessment_id,
    )

    repository = AssessmentGradingRepository(
        db,
    )

    await repository.delete_scheme(
        scheme,
    )

    await _commit_grading_change(
        db,
        duplicate_detail="Unable to delete assessment grading scheme.",
    )


# ---------------------------------------------------------------------------
# Boundary service
# ---------------------------------------------------------------------------


async def list_grade_boundaries(
    db: AsyncSession,
    current_user: User,
    *,
    scheme_id: int,
) -> list[AssessmentGradeBoundary]:
    """
    Return all boundaries belonging to a grading scheme.
    """

    scheme = await _get_scheme_or_404(
        db,
        scheme_id,
    )

    await _get_assessment_context(
        db,
        current_user,
        scheme.assessment_id,
    )

    return await AssessmentGradingRepository(
        db,
    ).list_boundaries(
        scheme.id,
    )


async def create_grade_boundary(
    db: AsyncSession,
    current_user: User,
    *,
    scheme_id: int,
    grade_label: str,
    minimum_value: Decimal | int | float | str,
    order: int,
    description: str | None = None,
    grade_points: Decimal | int | float | str | None = None,
    is_pass: bool | None = None,
) -> AssessmentGradeBoundary:
    """
    Create one inclusive grade boundary.
    """

    scheme = await _get_scheme_or_404(
        db,
        scheme_id,
    )

    assessment_context = await _get_assessment_context(
        db,
        current_user,
        scheme.assessment_id,
    )

    clean_label = _normalise_required_text(
        grade_label,
        field_name="Grade label",
    )

    clean_description = _normalise_optional_text(
        description,
    )

    clean_minimum = _normalise_decimal(
        minimum_value,
        field_name="minimum_value",
    )

    clean_order = _normalise_positive_order(
        order,
    )

    clean_grade_points: Decimal | None = None

    if grade_points is not None:
        clean_grade_points = _normalise_decimal(
            grade_points,
            field_name="grade_points",
        )

        if clean_grade_points < _ZERO:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="grade_points cannot be negative.",
            )

    if is_pass is not None and not isinstance(is_pass, bool):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="is_pass must be a boolean or null.",
        )

    maximum_mark = Decimal(
        str(
            assessment_context["maximum_mark"],
        ),
    )

    _validate_boundary_value(
        basis=scheme.basis,
        minimum_value=clean_minimum,
        assessment_maximum_mark=maximum_mark,
    )

    repository = AssessmentGradingRepository(
        db,
    )

    if await repository.get_boundary_by_label(
        grading_scheme_id=scheme.id,
        grade_label=clean_label,
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A grade boundary with this label already exists.",
        )

    if await repository.get_boundary_by_minimum_value(
        grading_scheme_id=scheme.id,
        minimum_value=clean_minimum,
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A grade boundary with this minimum value already exists.",
        )

    if await repository.get_boundary_by_order(
        grading_scheme_id=scheme.id,
        order=clean_order,
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A grade boundary with this order already exists.",
        )

    boundary = await repository.create_boundary(
        grading_scheme_id=scheme.id,
        grade_label=clean_label,
        minimum_value=clean_minimum,
        order=clean_order,
        description=clean_description,
        grade_points=clean_grade_points,
        is_pass=is_pass,
    )

    await _commit_grading_change(
        db,
        duplicate_detail=(
            "A conflicting grade boundary already exists in this grading scheme."
        ),
    )

    refreshed = await repository.get_boundary_by_id(
        boundary.id,
    )

    if refreshed is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assessment grade boundary not found.",
        )

    return refreshed


async def update_grade_boundary(
    db: AsyncSession,
    current_user: User,
    *,
    boundary_id: int,
    grade_label: str | object = _UNSET,
    minimum_value: Decimal | int | float | str | object = _UNSET,
    order: int | object = _UNSET,
    description: str | None | object = _UNSET,
    grade_points: Decimal | int | float | str | None | object = _UNSET,
    is_pass: bool | None | object = _UNSET,
) -> AssessmentGradeBoundary:
    """
    Update one grade boundary.
    """

    boundary = await _get_boundary_or_404(
        db,
        boundary_id,
    )

    scheme = await _get_scheme_or_404(
        db,
        boundary.grading_scheme_id,
    )

    assessment_context = await _get_assessment_context(
        db,
        current_user,
        scheme.assessment_id,
    )

    repository = AssessmentGradingRepository(
        db,
    )

    if grade_label is not _UNSET:
        clean_label = _normalise_required_text(
            grade_label,
            field_name="Grade label",
        )

        existing = await repository.get_boundary_by_label(
            grading_scheme_id=scheme.id,
            grade_label=clean_label,
        )

        if existing is not None and existing.id != boundary.id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A grade boundary with this label already exists.",
            )

        boundary.grade_label = clean_label

    if minimum_value is not _UNSET:
        clean_minimum = _normalise_decimal(
            minimum_value,
            field_name="minimum_value",
        )

        maximum_mark = Decimal(
            str(
                assessment_context["maximum_mark"],
            ),
        )

        _validate_boundary_value(
            basis=scheme.basis,
            minimum_value=clean_minimum,
            assessment_maximum_mark=maximum_mark,
        )

        existing = await repository.get_boundary_by_minimum_value(
            grading_scheme_id=scheme.id,
            minimum_value=clean_minimum,
        )

        if existing is not None and existing.id != boundary.id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=("A grade boundary with this minimum value already exists."),
            )

        boundary.minimum_value = clean_minimum

    if order is not _UNSET:
        clean_order = _normalise_positive_order(
            order,
        )

        existing = await repository.get_boundary_by_order(
            grading_scheme_id=scheme.id,
            order=clean_order,
        )

        if existing is not None and existing.id != boundary.id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A grade boundary with this order already exists.",
            )

        boundary.order = clean_order

    if description is not _UNSET:
        boundary.description = _normalise_optional_text(
            description,
        )

    if grade_points is not _UNSET:
        if grade_points is None:
            boundary.grade_points = None

        else:
            clean_grade_points = _normalise_decimal(
                grade_points,
                field_name="grade_points",
            )

            if clean_grade_points < _ZERO:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                    detail="grade_points cannot be negative.",
                )

            boundary.grade_points = clean_grade_points

    if is_pass is not _UNSET:
        if is_pass is not None and not isinstance(is_pass, bool):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="is_pass must be a boolean or null.",
            )

        boundary.is_pass = is_pass

    await repository.flush()

    await _commit_grading_change(
        db,
        duplicate_detail=(
            "A conflicting grade boundary already exists in this grading scheme."
        ),
    )

    refreshed = await repository.get_boundary_by_id(
        boundary.id,
    )

    if refreshed is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assessment grade boundary not found.",
        )

    return refreshed


async def delete_grade_boundary(
    db: AsyncSession,
    current_user: User,
    *,
    boundary_id: int,
) -> None:
    """
    Delete one grade boundary.
    """

    boundary = await _get_boundary_or_404(
        db,
        boundary_id,
    )

    scheme = await _get_scheme_or_404(
        db,
        boundary.grading_scheme_id,
    )

    await _get_assessment_context(
        db,
        current_user,
        scheme.assessment_id,
    )

    repository = AssessmentGradingRepository(
        db,
    )

    await repository.delete_boundary(
        boundary,
    )

    await _commit_grading_change(
        db,
        duplicate_detail="Unable to delete assessment grade boundary.",
    )


# ---------------------------------------------------------------------------
# Grade resolution
# ---------------------------------------------------------------------------


async def resolve_grade(
    db: AsyncSession,
    current_user: User,
    *,
    assessment_id: int,
    value: Decimal | int | float | str,
) -> dict[str, Any]:
    """
    Resolve an explicit raw mark or percentage against the active scheme.

    The caller must supply a value expressed in the scheme's configured
    basis.
    """

    assessment_context = await _get_assessment_context(
        db,
        current_user,
        assessment_id,
    )

    scheme = await _get_active_assessment_scheme_or_404(
        db,
        assessment_id,
    )

    clean_value = _normalise_decimal(
        value,
        field_name="value",
    )

    maximum_mark = Decimal(
        str(
            assessment_context["maximum_mark"],
        ),
    )

    if clean_value < _ZERO:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Grading value cannot be negative.",
        )

    if scheme.basis == AssessmentGradingBasis.PERCENTAGE and clean_value > _ONE_HUNDRED:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Percentage grading value cannot exceed 100.",
        )

    if scheme.basis == AssessmentGradingBasis.RAW_MARK and clean_value > maximum_mark:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Raw grading value cannot exceed the assessment maximum mark.",
        )

    boundary = await AssessmentGradingRepository(
        db,
    ).resolve_boundary(
        grading_scheme_id=scheme.id,
        value=clean_value,
    )

    return {
        "assessment_id": assessment_id,
        "grading_scheme_id": scheme.id,
        "grading_scheme_name": scheme.name,
        "basis": scheme.basis,
        "value": clean_value,
        "grade": (boundary.grade_label if boundary is not None else None),
        "boundary_id": (boundary.id if boundary is not None else None),
        "minimum_value": (
            Decimal(
                str(boundary.minimum_value),
            )
            if boundary is not None
            else None
        ),
        "grade_points": (
            Decimal(
                str(boundary.grade_points),
            )
            if (boundary is not None and boundary.grade_points is not None)
            else None
        ),
        "is_pass": (boundary.is_pass if boundary is not None else None),
    }


def _get_result_value_for_scheme(
    *,
    scheme: AssessmentGradingScheme,
    result: dict[str, Any],
    result_stage: str,
) -> Decimal | None:
    """
    Select the correct result value for a grading scheme and result stage.

    Supported result stages:

        current
            Includes provisional marks.

        completed
            Uses MARKED, REVIEWED and FINALISED marks.

        finalised
            Uses FINALISED marks only.
    """

    normalised_stage = result_stage.strip().lower()

    stage_fields = {
        "current": (
            "mark_awarded",
            "percentage",
        ),
        "completed": (
            "completed_mark_awarded",
            "completed_percentage",
        ),
        "finalised": (
            "finalised_mark_awarded",
            "finalised_percentage",
        ),
    }

    fields = stage_fields.get(
        normalised_stage,
    )

    if fields is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=("result_stage must be one of: " "current, completed, finalised."),
        )

    raw_field, percentage_field = fields

    if scheme.basis == AssessmentGradingBasis.RAW_MARK:
        value = result.get(
            raw_field,
        )

    else:
        value = result.get(
            percentage_field,
        )

    if value is None:
        return None

    return Decimal(
        str(value),
    )


async def grade_script_result(
    db: AsyncSession,
    current_user: User,
    *,
    script_id: int,
    result_stage: str = "finalised",
) -> dict[str, Any]:
    """
    Grade one script using its assessment's active grading scheme.

    By default the grade is derived from finalised marks only.
    """

    result = await get_script_result(
        db=db,
        current_user=current_user,
        script_id=script_id,
    )

    assessment_id = int(
        result["assessment_id"],
    )

    scheme = await _get_active_assessment_scheme_or_404(
        db,
        assessment_id,
    )

    value = _get_result_value_for_scheme(
        scheme=scheme,
        result=result,
        result_stage=result_stage,
    )

    if value is None:
        return {
            "assessment_id": assessment_id,
            "candidate_id": result["candidate_id"],
            "student_id": result["student_id"],
            "script_id": result["script_id"],
            "script_version": result["script_version"],
            "result_stage": result_stage.strip().lower(),
            "grading_scheme_id": scheme.id,
            "grading_scheme_name": scheme.name,
            "basis": scheme.basis,
            "value": None,
            "grade": None,
            "boundary_id": None,
            "minimum_value": None,
            "grade_points": None,
            "is_pass": None,
        }

    resolved = await resolve_grade(
        db,
        current_user,
        assessment_id=assessment_id,
        value=value,
    )

    return {
        "assessment_id": assessment_id,
        "candidate_id": result["candidate_id"],
        "student_id": result["student_id"],
        "script_id": result["script_id"],
        "script_version": result["script_version"],
        "result_stage": result_stage.strip().lower(),
        **resolved,
    }


async def grade_candidate_latest_result(
    db: AsyncSession,
    current_user: User,
    *,
    candidate_id: int,
    result_stage: str = "finalised",
) -> dict[str, Any]:
    """
    Grade the candidate's latest script version.

    Earlier versions remain available through the assessment results layer.
    """

    candidate_result = await get_candidate_result(
        db=db,
        current_user=current_user,
        candidate_id=candidate_id,
    )

    latest = candidate_result.get(
        "latest_script_result",
    )

    if latest is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Assessment candidate does not yet have a script to grade.",
        )

    return await grade_script_result(
        db,
        current_user,
        script_id=int(
            latest["script_id"],
        ),
        result_stage=result_stage,
    )
