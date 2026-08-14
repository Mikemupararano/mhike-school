from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.assessment import Assessment, AssessmentStatus
from app.models.assessment_candidate import (
    AssessmentCandidate,
    AssessmentCandidateStatus,
)
from app.models.class_group import ClassGroup
from app.models.user import User, UserRole
from app.repositories.assessment_candidate_bulk import (
    AssessmentCandidateBulkRepository,
)
from app.repositories.class_group import ClassGroupRepository
from app.repositories.enrollment import EnrollmentRepository
from app.services.assessment_candidate_service import (
    _ensure_assessment_management_access,
    _get_assessment_or_404,
    has_role,
)


@dataclass(frozen=True, slots=True)
class AssessmentCandidateBulkItemResult:
    """
    Describe the result for one unique student in a bulk allocation.

    ``outcome`` is intentionally represented as a stable application string
    rather than a database enum because this object is a service result rather
    than persisted state.

    Supported outcomes:

    - ``created``;
    - ``already_allocated``;
    - ``ineligible``.
    """

    student_id: int
    outcome: str
    candidate_id: int | None = None
    detail: str | None = None


@dataclass(frozen=True, slots=True)
class AssessmentCandidateBulkResult:
    """
    Summarise one completed bulk candidate-allocation operation.
    """

    assessment_id: int
    source: str
    class_id: int | None

    requested_count: int
    unique_requested_count: int

    created_count: int
    already_allocated_count: int
    ineligible_count: int

    items: tuple[AssessmentCandidateBulkItemResult, ...]


@dataclass(frozen=True, slots=True)
class AssessmentCandidateClassPreview:
    """
    Describe the current allocation state for one class and assessment.

    Preview is read-only. It does not create candidate records.
    """

    assessment_id: int
    class_id: int
    class_name: str

    allocation_allowed: bool

    enrolled_count: int
    student_count: int

    eligible_count: int
    already_allocated_count: int
    ineligible_count: int

    eligible_student_ids: tuple[int, ...]
    already_allocated_student_ids: tuple[int, ...]
    ineligible_student_ids: tuple[int, ...]


# ----------------------------------------------------------------------
# Constants
# ----------------------------------------------------------------------


_USER_QUERY_CHUNK_SIZE = 500

_ALLOCATABLE_ASSESSMENT_STATUSES = {
    AssessmentStatus.DRAFT,
    AssessmentStatus.PUBLISHED,
}


# ----------------------------------------------------------------------
# Validation helpers
# ----------------------------------------------------------------------


def _validate_positive_integer(
    value: int,
    field_name: str,
) -> None:
    """
    Require a positive integer identifier.
    """

    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{field_name} must be a positive integer",
        )


def _normalise_student_ids(
    student_ids: Iterable[int],
) -> tuple[list[int], int]:
    """
    Validate and deduplicate student identifiers while preserving order.

    Returns:

    - the unique student IDs in first-seen order;
    - the original requested-item count.
    """

    requested_count = 0
    unique_student_ids: list[int] = []
    seen: set[int] = set()

    for student_id in student_ids:
        requested_count += 1

        _validate_positive_integer(
            student_id,
            "student_id",
        )

        if student_id in seen:
            continue

        seen.add(
            student_id,
        )
        unique_student_ids.append(
            student_id,
        )

    if requested_count == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one student ID is required",
        )

    return (
        unique_student_ids,
        requested_count,
    )


def _ensure_assessment_allows_allocation(
    assessment: Assessment,
) -> None:
    """
    Ensure the assessment may currently receive new candidates.
    """

    if assessment.status not in _ALLOCATABLE_ASSESSMENT_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Candidates cannot be allocated to a closed or " "archived assessment"
            ),
        )


async def _get_manageable_assessment(
    db: AsyncSession,
    current_user: User,
    assessment_id: int,
    *,
    require_allocation_allowed: bool,
) -> Assessment:
    """
    Resolve an assessment and enforce the existing management-access rules.
    """

    _validate_positive_integer(
        assessment_id,
        "assessment_id",
    )

    assessment = await _get_assessment_or_404(
        db,
        assessment_id,
        include_relationships=False,
    )

    await _ensure_assessment_management_access(
        db,
        current_user,
        assessment,
    )

    if require_allocation_allowed:
        _ensure_assessment_allows_allocation(
            assessment,
        )

    return assessment


async def _get_class_in_assessment_school(
    db: AsyncSession,
    *,
    assessment: Assessment,
    class_id: int,
) -> ClassGroup:
    """
    Resolve a class only within the assessment's school.
    """

    _validate_positive_integer(
        class_id,
        "class_id",
    )

    class_group = await ClassGroupRepository(
        db,
    ).get_by_id_and_school(
        class_id=class_id,
        school_id=assessment.school_id,
        include_relationships=False,
    )

    if class_group is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Class not found",
        )

    return class_group


async def _load_users_by_ids(
    db: AsyncSession,
    student_ids: list[int],
) -> dict[int, User]:
    """
    Load users in bounded set-based queries.

    Users are intentionally loaded without a school predicate here so the
    service can distinguish:

    - a nonexistent user;
    - a real user from another school;
    - a same-school user without the student role.

    The service then applies the same security and role semantics as the
    existing single-candidate allocation workflow.
    """

    if not student_ids:
        return {}

    users_by_id: dict[int, User] = {}

    for start in range(
        0,
        len(student_ids),
        _USER_QUERY_CHUNK_SIZE,
    ):
        student_id_chunk = student_ids[start : start + _USER_QUERY_CHUNK_SIZE]

        result = await db.execute(
            select(
                User,
            ).where(
                User.id.in_(
                    student_id_chunk,
                ),
            ),
        )

        for user in result.scalars().all():
            users_by_id[user.id] = user

    return users_by_id


def _validate_explicit_students(
    *,
    assessment: Assessment,
    student_ids: list[int],
    users_by_id: dict[int, User],
) -> None:
    """
    Validate explicit bulk-allocation users atomically.

    Explicit bulk requests preserve the behaviour of single allocation:

    - missing users fail the request;
    - non-students fail with 422;
    - cross-school students fail with 403.

    No candidate records are created until every requested student has passed
    validation.
    """

    for student_id in student_ids:
        user = users_by_id.get(
            student_id,
        )

        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User {student_id} not found",
            )

        if not has_role(
            user,
            UserRole.STUDENT,
        ):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="The selected user is not a student",
            )

        if user.school_id != assessment.school_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Student does not belong to the assessment school",
            )


# ----------------------------------------------------------------------
# Shared allocation engine
# ----------------------------------------------------------------------


async def _allocate_validated_students(
    db: AsyncSession,
    *,
    assessment: Assessment,
    student_ids: list[int],
    requested_count: int,
    source: str,
    class_id: int | None = None,
    ineligible_student_ids: set[int] | None = None,
) -> AssessmentCandidateBulkResult:
    """
    Allocate a validated set of students in one service transaction.

    Existing allocations are intentionally skipped rather than treated as
    errors. Database uniqueness remains the final concurrency safeguard.
    """

    ineligible_student_ids = ineligible_student_ids or set()

    allocation_student_ids = [
        student_id
        for student_id in student_ids
        if student_id not in ineligible_student_ids
    ]

    repository = AssessmentCandidateBulkRepository(
        db,
    )

    existing_student_ids = await repository.get_existing_student_ids(
        assessment_id=assessment.id,
        student_ids=allocation_student_ids,
    )

    new_student_ids = [
        student_id
        for student_id in allocation_student_ids
        if student_id not in existing_student_ids
    ]

    candidates = [
        AssessmentCandidate(
            assessment_id=assessment.id,
            student_id=student_id,
            status=AssessmentCandidateStatus.ALLOCATED,
        )
        for student_id in new_student_ids
    ]

    try:
        created_candidates = await repository.create_candidates(
            candidates,
        )

        created_candidate_ids = {
            candidate.student_id: candidate.id for candidate in created_candidates
        }

        await db.commit()

    except IntegrityError as exc:
        await db.rollback()

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "One or more students were allocated concurrently; "
                "retry the bulk allocation"
            ),
        ) from exc

    except Exception:
        await db.rollback()
        raise

    items: list[AssessmentCandidateBulkItemResult] = []

    for student_id in student_ids:
        if student_id in ineligible_student_ids:
            items.append(
                AssessmentCandidateBulkItemResult(
                    student_id=student_id,
                    outcome="ineligible",
                    detail=(
                        "Class membership does not resolve to an eligible "
                        "student in the assessment school"
                    ),
                ),
            )
            continue

        if student_id in existing_student_ids:
            items.append(
                AssessmentCandidateBulkItemResult(
                    student_id=student_id,
                    outcome="already_allocated",
                ),
            )
            continue

        items.append(
            AssessmentCandidateBulkItemResult(
                student_id=student_id,
                outcome="created",
                candidate_id=created_candidate_ids.get(
                    student_id,
                ),
            ),
        )

    return AssessmentCandidateBulkResult(
        assessment_id=assessment.id,
        source=source,
        class_id=class_id,
        requested_count=requested_count,
        unique_requested_count=len(student_ids),
        created_count=len(created_candidate_ids),
        already_allocated_count=len(existing_student_ids),
        ineligible_count=len(ineligible_student_ids),
        items=tuple(
            items,
        ),
    )


# ----------------------------------------------------------------------
# Explicit bulk allocation
# ----------------------------------------------------------------------


async def bulk_allocate_candidates(
    db: AsyncSession,
    current_user: User,
    assessment_id: int,
    student_ids: Iterable[int],
) -> AssessmentCandidateBulkResult:
    """
    Allocate an explicit collection of students to an assessment.

    Behaviour:

    - duplicates in the request are collapsed;
    - all students are validated before any write occurs;
    - existing allocations are skipped idempotently;
    - all new allocations are committed in one transaction;
    - concurrent duplicate creation is surfaced as a retryable conflict.
    """

    assessment = await _get_manageable_assessment(
        db,
        current_user,
        assessment_id,
        require_allocation_allowed=True,
    )

    (
        unique_student_ids,
        requested_count,
    ) = _normalise_student_ids(
        student_ids,
    )

    users_by_id = await _load_users_by_ids(
        db,
        unique_student_ids,
    )

    _validate_explicit_students(
        assessment=assessment,
        student_ids=unique_student_ids,
        users_by_id=users_by_id,
    )

    return await _allocate_validated_students(
        db,
        assessment=assessment,
        student_ids=unique_student_ids,
        requested_count=requested_count,
        source="explicit",
    )


# ----------------------------------------------------------------------
# Class allocation
# ----------------------------------------------------------------------


async def allocate_class_candidates(
    db: AsyncSession,
    current_user: User,
    assessment_id: int,
    class_id: int,
) -> AssessmentCandidateBulkResult:
    """
    Allocate the current eligible membership of one class.

    Class membership is resolved from ``Enrollment`` at the time this
    operation runs.

    The class ID is not copied onto ``AssessmentCandidate``. This deliberately
    preserves candidate history independently of later class membership
    changes.

    Defensive handling:

    - valid student enrolments become candidates;
    - already allocated students are skipped;
    - malformed/non-student enrolments are reported as ineligible rather than
      creating invalid candidate records.
    """

    assessment = await _get_manageable_assessment(
        db,
        current_user,
        assessment_id,
        require_allocation_allowed=True,
    )

    class_group = await _get_class_in_assessment_school(
        db,
        assessment=assessment,
        class_id=class_id,
    )

    enrollments = await EnrollmentRepository(
        db,
    ).list_by_class(
        class_group.id,
        school_id=assessment.school_id,
    )

    ordered_student_ids: list[int] = []
    seen_student_ids: set[int] = set()
    ineligible_student_ids: set[int] = set()

    for enrollment in enrollments:
        student_id = enrollment.user_id

        if student_id in seen_student_ids:
            continue

        seen_student_ids.add(
            student_id,
        )
        ordered_student_ids.append(
            student_id,
        )

        user = enrollment.user

        if (
            user is None
            or user.school_id != assessment.school_id
            or not has_role(
                user,
                UserRole.STUDENT,
            )
        ):
            ineligible_student_ids.add(
                student_id,
            )

    if not ordered_student_ids:
        return AssessmentCandidateBulkResult(
            assessment_id=assessment.id,
            source="class",
            class_id=class_group.id,
            requested_count=0,
            unique_requested_count=0,
            created_count=0,
            already_allocated_count=0,
            ineligible_count=0,
            items=(),
        )

    return await _allocate_validated_students(
        db,
        assessment=assessment,
        student_ids=ordered_student_ids,
        requested_count=len(enrollments),
        source="class",
        class_id=class_group.id,
        ineligible_student_ids=ineligible_student_ids,
    )


# ----------------------------------------------------------------------
# Class allocation preview
# ----------------------------------------------------------------------


async def preview_class_candidate_allocation(
    db: AsyncSession,
    current_user: User,
    assessment_id: int,
    class_id: int,
) -> AssessmentCandidateClassPreview:
    """
    Preview class-to-assessment allocation without mutating database state.

    Preview is available for closed/archived assessments so callers can inspect
    historical/current population state, but ``allocation_allowed`` explicitly
    reports whether a subsequent allocation operation would be accepted.
    """

    assessment = await _get_manageable_assessment(
        db,
        current_user,
        assessment_id,
        require_allocation_allowed=False,
    )

    class_group = await _get_class_in_assessment_school(
        db,
        assessment=assessment,
        class_id=class_id,
    )

    enrollments = await EnrollmentRepository(
        db,
    ).list_by_class(
        class_group.id,
        school_id=assessment.school_id,
    )

    ordered_student_ids: list[int] = []
    seen_student_ids: set[int] = set()
    ineligible_student_ids: set[int] = set()

    for enrollment in enrollments:
        student_id = enrollment.user_id

        if student_id in seen_student_ids:
            continue

        seen_student_ids.add(
            student_id,
        )
        ordered_student_ids.append(
            student_id,
        )

        user = enrollment.user

        if (
            user is None
            or user.school_id != assessment.school_id
            or not has_role(
                user,
                UserRole.STUDENT,
            )
        ):
            ineligible_student_ids.add(
                student_id,
            )

    eligible_population_ids = [
        student_id
        for student_id in ordered_student_ids
        if student_id not in ineligible_student_ids
    ]

    existing_student_ids = await AssessmentCandidateBulkRepository(
        db,
    ).get_existing_student_ids(
        assessment_id=assessment.id,
        student_ids=eligible_population_ids,
    )

    eligible_student_ids = tuple(
        student_id
        for student_id in eligible_population_ids
        if student_id not in existing_student_ids
    )

    already_allocated_student_ids = tuple(
        student_id
        for student_id in eligible_population_ids
        if student_id in existing_student_ids
    )

    ordered_ineligible_student_ids = tuple(
        student_id
        for student_id in ordered_student_ids
        if student_id in ineligible_student_ids
    )

    return AssessmentCandidateClassPreview(
        assessment_id=assessment.id,
        class_id=class_group.id,
        class_name=class_group.name,
        allocation_allowed=(assessment.status in _ALLOCATABLE_ASSESSMENT_STATUSES),
        enrolled_count=len(enrollments),
        student_count=len(
            eligible_population_ids,
        ),
        eligible_count=len(
            eligible_student_ids,
        ),
        already_allocated_count=len(
            already_allocated_student_ids,
        ),
        ineligible_count=len(
            ordered_ineligible_student_ids,
        ),
        eligible_student_ids=eligible_student_ids,
        already_allocated_student_ids=(already_allocated_student_ids),
        ineligible_student_ids=ordered_ineligible_student_ids,
    )
