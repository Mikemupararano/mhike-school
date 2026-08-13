from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.assessment_target import AssessmentTarget
from app.models.course import Course
from app.models.user import User, UserRole
from app.repositories.assessment_target import (
    AssessmentTargetRepository,
    _UNSET,
)
from app.services.assessment_trends_service import (
    get_parent_student_assessment_trend,
    get_student_assessment_trend,
)

_ZERO = Decimal("0")
_DECIMAL_QUANTUM = Decimal("0.01")


# ---------------------------------------------------------------------------
# Role helpers
# ---------------------------------------------------------------------------


def _has_role(
    user: User,
    role: UserRole,
) -> bool:
    """
    Return whether a user currently holds the supplied role.
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


def _is_student(
    user: User,
) -> bool:
    return _has_role(
        user,
        UserRole.STUDENT,
    )


def _ensure_target_staff_role(
    current_user: User,
) -> None:
    """
    Ensure the caller may manage assessment targets.
    """

    if (
        _is_teacher(current_user)
        or _is_school_admin(current_user)
        or _is_platform_admin(current_user)
    ):
        return

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="You do not have permission to manage assessment targets.",
    )


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------


def _validate_positive_integer(
    value: int,
    *,
    field_name: str,
) -> int:
    """
    Require a positive integer identifier.
    """

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


def _normalise_grade_label(
    value: str,
) -> str:
    """
    Return a validated grade label.
    """

    if not isinstance(
        value,
        str,
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="grade_label must be a string.",
        )

    cleaned = value.strip()

    if not cleaned:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="grade_label cannot be blank.",
        )

    if len(cleaned) > 100:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="grade_label cannot exceed 100 characters.",
        )

    return cleaned


def _normalise_optional_text(
    value: str | None,
    *,
    field_name: str,
    max_length: int | None = None,
) -> str | None:
    """
    Trim optional text and convert blank values to None.
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

    if max_length is not None and len(cleaned) > max_length:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"{field_name} cannot exceed {max_length} characters.",
        )

    return cleaned


def _normalise_grade_points(
    value: Decimal | int | float | str | None,
) -> Decimal | None:
    """
    Validate optional target grade points.
    """

    if value is None:
        return None

    try:
        cleaned = Decimal(
            str(value),
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="grade_points must be numeric or None.",
        ) from exc

    if cleaned < _ZERO:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="grade_points cannot be negative.",
        )

    return cleaned


def _round_decimal(
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


# ---------------------------------------------------------------------------
# School scope
# ---------------------------------------------------------------------------


def _resolve_school_id(
    current_user: User,
    requested_school_id: int | None,
) -> int:
    """
    Resolve the school in which a target operation is permitted.

    School-scoped users are always restricted to their own school.

    Platform administrators must explicitly provide a school when they do
    not themselves belong to one.
    """

    if requested_school_id is not None:
        _validate_positive_integer(
            requested_school_id,
            field_name="school_id",
        )

    user_school_id = getattr(
        current_user,
        "school_id",
        None,
    )

    if _is_platform_admin(
        current_user,
    ):
        if requested_school_id is not None:
            return requested_school_id

        if user_school_id is not None:
            return int(
                user_school_id,
            )

        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="school_id is required for a platform administrator.",
        )

    if user_school_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="A school-scoped user must belong to a school.",
        )

    if requested_school_id is not None and requested_school_id != user_school_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You cannot manage assessment targets for another school.",
        )

    return int(
        user_school_id,
    )


# ---------------------------------------------------------------------------
# Entity lookup and access
# ---------------------------------------------------------------------------


async def _get_student_or_404(
    db: AsyncSession,
    *,
    student_id: int,
    school_id: int,
) -> User:
    """
    Return a student belonging to the required school.
    """

    _validate_positive_integer(
        student_id,
        field_name="student_id",
    )

    student = await db.get(
        User,
        student_id,
    )

    if student is None or student.school_id != school_id or not _is_student(student):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student not found.",
        )

    return student


async def _get_course_or_404(
    db: AsyncSession,
    *,
    course_id: int,
    school_id: int,
) -> Course:
    """
    Return a course belonging to the required school.
    """

    _validate_positive_integer(
        course_id,
        field_name="course_id",
    )

    course = await db.get(
        Course,
        course_id,
    )

    if course is None or course.school_id != school_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found.",
        )

    return course


def _ensure_course_management_access(
    current_user: User,
    course: Course,
) -> None:
    """
    Ensure the caller may manage targets for the supplied course.

    Ordinary teachers may manage targets only for courses they teach.
    School and platform administrators retain broader scope.
    """

    if _is_school_admin(current_user) or _is_platform_admin(current_user):
        return

    if _is_teacher(current_user) and course.teacher_id == current_user.id:
        return

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="You can only manage assessment targets for courses you teach.",
    )


async def _get_target_or_404(
    db: AsyncSession,
    current_user: User,
    *,
    target_id: int,
    school_id: int | None = None,
) -> AssessmentTarget:
    """
    Return an authorised assessment target.
    """

    _ensure_target_staff_role(
        current_user,
    )

    clean_target_id = _validate_positive_integer(
        target_id,
        field_name="target_id",
    )

    effective_school_id = _resolve_school_id(
        current_user,
        school_id,
    )

    target = await AssessmentTargetRepository(
        db,
    ).get_by_id_and_school(
        clean_target_id,
        effective_school_id,
        include_relationships=True,
    )

    if target is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assessment target not found.",
        )

    _ensure_course_management_access(
        current_user,
        target.course,
    )

    return target


# ---------------------------------------------------------------------------
# Transaction helpers
# ---------------------------------------------------------------------------


async def _commit_target_change(
    db: AsyncSession,
    *,
    duplicate_detail: str,
) -> None:
    """
    Commit an assessment-target mutation safely.
    """

    try:
        await db.commit()

    except IntegrityError as exc:
        await db.rollback()

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=duplicate_detail,
        ) from exc

    except Exception:
        await db.rollback()
        raise


# ---------------------------------------------------------------------------
# Serialisation
# ---------------------------------------------------------------------------


def _target_to_dict(
    target: AssessmentTarget,
) -> dict[str, Any]:
    """
    Convert an AssessmentTarget model to its API/service representation.
    """

    course = getattr(
        target,
        "course",
        None,
    )

    subject = (
        getattr(
            course,
            "subject",
            None,
        )
        if course is not None
        else None
    )

    student = getattr(
        target,
        "student",
        None,
    )

    setter = getattr(
        target,
        "set_by",
        None,
    )

    return {
        "id": target.id,
        "school_id": target.school_id,
        "student_id": target.student_id,
        "student_name": (student.full_name if student is not None else None),
        "course_id": target.course_id,
        "course_title": (course.title if course is not None else None),
        "subject_id": (course.subject_id if course is not None else None),
        "subject_name": (subject.name if subject is not None else None),
        "grade_label": target.grade_label,
        "grade_points": (
            Decimal(
                str(target.grade_points),
            )
            if target.grade_points is not None
            else None
        ),
        "academic_year": target.academic_year,
        "notes": target.notes,
        "set_by_id": target.set_by_id,
        "set_by_name": (setter.full_name if setter is not None else None),
        "created_at": target.created_at,
        "updated_at": target.updated_at,
    }


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------


async def create_assessment_target(
    db: AsyncSession,
    current_user: User,
    *,
    student_id: int,
    course_id: int,
    grade_label: str,
    grade_points: Decimal | int | float | str | None = None,
    academic_year: str | None = None,
    notes: str | None = None,
    school_id: int | None = None,
) -> dict[str, Any]:
    """
    Create one course-level target for a student.
    """

    _ensure_target_staff_role(
        current_user,
    )

    effective_school_id = _resolve_school_id(
        current_user,
        school_id,
    )

    clean_grade_label = _normalise_grade_label(
        grade_label,
    )

    clean_grade_points = _normalise_grade_points(
        grade_points,
    )

    clean_academic_year = _normalise_optional_text(
        academic_year,
        field_name="academic_year",
        max_length=50,
    )

    clean_notes = _normalise_optional_text(
        notes,
        field_name="notes",
    )

    await _get_student_or_404(
        db,
        student_id=student_id,
        school_id=effective_school_id,
    )

    course = await _get_course_or_404(
        db,
        course_id=course_id,
        school_id=effective_school_id,
    )

    _ensure_course_management_access(
        current_user,
        course,
    )

    repository = AssessmentTargetRepository(
        db,
    )

    existing = await repository.get_by_student_and_course(
        student_id=student_id,
        course_id=course_id,
        school_id=effective_school_id,
        include_relationships=False,
    )

    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An assessment target already exists for this student and course.",
        )

    target = await repository.create(
        school_id=effective_school_id,
        student_id=student_id,
        course_id=course_id,
        grade_label=clean_grade_label,
        grade_points=clean_grade_points,
        academic_year=clean_academic_year,
        notes=clean_notes,
        set_by_id=current_user.id,
    )

    await _commit_target_change(
        db,
        duplicate_detail=(
            "An assessment target already exists for this student and course."
        ),
    )

    await db.refresh(
        target,
    )

    refreshed = await repository.get_by_id_and_school(
        target.id,
        effective_school_id,
        include_relationships=True,
    )

    if refreshed is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Assessment target was created but could not be reloaded.",
        )

    return _target_to_dict(
        refreshed,
    )


# ---------------------------------------------------------------------------
# Staff reads
# ---------------------------------------------------------------------------


async def get_assessment_target(
    db: AsyncSession,
    current_user: User,
    *,
    target_id: int,
    school_id: int | None = None,
) -> dict[str, Any]:
    """
    Return one authorised assessment target.
    """

    target = await _get_target_or_404(
        db,
        current_user,
        target_id=target_id,
        school_id=school_id,
    )

    return _target_to_dict(
        target,
    )


async def list_assessment_targets(
    db: AsyncSession,
    current_user: User,
    *,
    school_id: int | None = None,
    student_id: int | None = None,
    course_id: int | None = None,
    academic_year: str | None = None,
) -> list[dict[str, Any]]:
    """
    Return targets visible within the caller's staff scope.
    """

    _ensure_target_staff_role(
        current_user,
    )

    effective_school_id = _resolve_school_id(
        current_user,
        school_id,
    )

    if student_id is not None:
        _validate_positive_integer(
            student_id,
            field_name="student_id",
        )

    if course_id is not None:
        _validate_positive_integer(
            course_id,
            field_name="course_id",
        )

    clean_academic_year = _normalise_optional_text(
        academic_year,
        field_name="academic_year",
        max_length=50,
    )

    targets = await AssessmentTargetRepository(
        db,
    ).list_by_school(
        effective_school_id,
        student_id=student_id,
        course_id=course_id,
        academic_year=clean_academic_year,
        include_relationships=True,
    )

    if (
        _is_teacher(current_user)
        and not _is_school_admin(current_user)
        and not _is_platform_admin(current_user)
    ):
        targets = [
            target
            for target in targets
            if (
                target.course is not None
                and target.course.teacher_id == current_user.id
            )
        ]

    return [
        _target_to_dict(
            target,
        )
        for target in targets
    ]


# ---------------------------------------------------------------------------
# Update
# ---------------------------------------------------------------------------


async def update_assessment_target(
    db: AsyncSession,
    current_user: User,
    *,
    target_id: int,
    grade_label: str | object = _UNSET,
    grade_points: Decimal | int | float | str | None | object = _UNSET,
    academic_year: str | None | object = _UNSET,
    notes: str | None | object = _UNSET,
    school_id: int | None = None,
) -> dict[str, Any]:
    """
    Update an assessment target.

    Nullable fields may be explicitly cleared by supplying None.
    """

    target = await _get_target_or_404(
        db,
        current_user,
        target_id=target_id,
        school_id=school_id,
    )

    clean_grade_label: str | object = _UNSET
    clean_grade_points: Decimal | None | object = _UNSET
    clean_academic_year: str | None | object = _UNSET
    clean_notes: str | None | object = _UNSET

    if grade_label is not _UNSET:
        clean_grade_label = _normalise_grade_label(
            grade_label,
        )

    if grade_points is not _UNSET:
        clean_grade_points = _normalise_grade_points(
            grade_points,
        )

    if academic_year is not _UNSET:
        clean_academic_year = _normalise_optional_text(
            academic_year,
            field_name="academic_year",
            max_length=50,
        )

    if notes is not _UNSET:
        clean_notes = _normalise_optional_text(
            notes,
            field_name="notes",
        )

    repository = AssessmentTargetRepository(
        db,
    )

    await repository.update(
        target,
        grade_label=clean_grade_label,
        grade_points=clean_grade_points,
        academic_year=clean_academic_year,
        notes=clean_notes,
        set_by_id=current_user.id,
    )

    await _commit_target_change(
        db,
        duplicate_detail="Unable to update assessment target.",
    )

    await db.refresh(
        target,
    )

    refreshed = await repository.get_by_id_and_school(
        target.id,
        target.school_id,
        include_relationships=True,
    )

    if refreshed is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Assessment target was updated but could not be reloaded.",
        )

    return _target_to_dict(
        refreshed,
    )


# ---------------------------------------------------------------------------
# Delete
# ---------------------------------------------------------------------------


async def delete_assessment_target(
    db: AsyncSession,
    current_user: User,
    *,
    target_id: int,
    school_id: int | None = None,
) -> None:
    """
    Delete an authorised assessment target.
    """

    target = await _get_target_or_404(
        db,
        current_user,
        target_id=target_id,
        school_id=school_id,
    )

    await AssessmentTargetRepository(
        db,
    ).delete(
        target,
    )

    await _commit_target_change(
        db,
        duplicate_detail="Unable to delete assessment target.",
    )


# ---------------------------------------------------------------------------
# Progress comparison
# ---------------------------------------------------------------------------


def _calculate_progress_comparison(
    *,
    target_grade_label: str,
    target_grade_points: Decimal | None,
    current_grade: str | None,
    current_grade_points: Decimal | None,
) -> dict[str, Any]:
    """
    Compare the latest formal grade with the stored target.

    Grade labels alone are not ordered because MHike School supports arbitrary
    grading systems. Numeric comparison is therefore performed only when both
    the target and current result provide grade points.
    """

    if target_grade_points is None or current_grade_points is None:
        return {
            "status": "not_comparable",
            "grade_points_difference": None,
            "target_grade_label": target_grade_label,
            "target_grade_points": target_grade_points,
            "current_grade": current_grade,
            "current_grade_points": current_grade_points,
        }

    difference = _round_decimal(
        current_grade_points - target_grade_points,
    )

    if difference is None:
        progress_status = "not_comparable"

    elif difference > _ZERO:
        progress_status = "above_target"

    elif difference < _ZERO:
        progress_status = "below_target"

    else:
        progress_status = "on_target"

    return {
        "status": progress_status,
        "grade_points_difference": difference,
        "target_grade_label": target_grade_label,
        "target_grade_points": target_grade_points,
        "current_grade": current_grade,
        "current_grade_points": current_grade_points,
    }


def _latest_trend_point(
    trend: dict[str, Any],
) -> dict[str, Any] | None:
    """
    Return the latest chronological trend point.
    """

    points = trend.get(
        "points",
        [],
    )

    if not points:
        return None

    return points[-1]


def _build_target_progress(
    *,
    target: AssessmentTarget,
    trend: dict[str, Any],
    audience: str,
) -> dict[str, Any]:
    """
    Build the target-versus-current-performance representation.
    """

    target_payload = _target_to_dict(
        target,
    )

    latest = _latest_trend_point(
        trend,
    )

    target_grade_points = (
        Decimal(
            str(target.grade_points),
        )
        if target.grade_points is not None
        else None
    )

    if latest is None:
        comparison = _calculate_progress_comparison(
            target_grade_label=target.grade_label,
            target_grade_points=target_grade_points,
            current_grade=None,
            current_grade_points=None,
        )

        return {
            "audience": audience,
            "target": target_payload,
            "latest_result": None,
            **comparison,
        }

    current_grade_points = (
        Decimal(str(latest["grade_points"]))
        if latest.get(
            "grade_points",
        )
        is not None
        else None
    )

    comparison = _calculate_progress_comparison(
        target_grade_label=target.grade_label,
        target_grade_points=target_grade_points,
        current_grade=latest.get(
            "grade",
        ),
        current_grade_points=current_grade_points,
    )

    return {
        "audience": audience,
        "target": target_payload,
        "latest_result": latest,
        **comparison,
    }


# ---------------------------------------------------------------------------
# Student-facing target progress
# ---------------------------------------------------------------------------


async def get_student_target_progress(
    db: AsyncSession,
    current_user: User,
    *,
    course_id: int,
) -> dict[str, Any]:
    """
    Return the logged-in student's course target and latest formal progress.
    """

    if not _is_student(
        current_user,
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only students can access the student target-progress view.",
        )

    clean_course_id = _validate_positive_integer(
        course_id,
        field_name="course_id",
    )

    school_id = getattr(
        current_user,
        "school_id",
        None,
    )

    if school_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Student must belong to a school.",
        )

    target = await AssessmentTargetRepository(
        db,
    ).get_by_student_and_course(
        student_id=current_user.id,
        course_id=clean_course_id,
        school_id=int(
            school_id,
        ),
        include_relationships=True,
    )

    if target is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assessment target not found.",
        )

    trend = await get_student_assessment_trend(
        db=db,
        current_user=current_user,
        school_id=int(
            school_id,
        ),
        course_id=clean_course_id,
        subject_id=None,
        academic_year=target.academic_year,
        term=None,
    )

    return _build_target_progress(
        target=target,
        trend=trend,
        audience="student",
    )


# ---------------------------------------------------------------------------
# Parent-facing target progress
# ---------------------------------------------------------------------------


async def get_parent_student_target_progress(
    db: AsyncSession,
    current_user: User,
    *,
    student_id: int,
    course_id: int,
) -> dict[str, Any]:
    """
    Return target progress for an authorised linked child.

    Parent-child authorisation is delegated to the existing parent assessment
    trend service, keeping that relationship rule in one place.
    """

    clean_student_id = _validate_positive_integer(
        student_id,
        field_name="student_id",
    )

    clean_course_id = _validate_positive_integer(
        course_id,
        field_name="course_id",
    )

    school_id = getattr(
        current_user,
        "school_id",
        None,
    )

    target = await AssessmentTargetRepository(
        db,
    ).get_by_student_and_course(
        student_id=clean_student_id,
        course_id=clean_course_id,
        school_id=(
            int(
                school_id,
            )
            if school_id is not None
            else None
        ),
        include_relationships=True,
    )

    if target is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assessment target not found.",
        )

    # This call is deliberately made even when there are no assessment
    # results. It is the existing authority for parent-child access.
    trend = await get_parent_student_assessment_trend(
        db=db,
        current_user=current_user,
        student_id=clean_student_id,
        school_id=target.school_id,
        course_id=clean_course_id,
        subject_id=None,
        academic_year=target.academic_year,
        term=None,
    )

    return _build_target_progress(
        target=target,
        trend=trend,
        audience="parent",
    )
