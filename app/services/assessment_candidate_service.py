from __future__ import annotations

from datetime import datetime, timezone
from time import perf_counter

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.assessment import Assessment, AssessmentStatus
from app.models.assessment_candidate import (
    AssessmentCandidate,
    AssessmentCandidateStatus,
    AssessmentScript,
    AssessmentScriptStatus,
)
from app.models.course import Course
from app.models.user import User, UserRole
from app.repositories.assessment import AssessmentRepository
from app.repositories.assessment_candidate import AssessmentCandidateRepository
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


# ----------------------------------------------------------------------
# General helpers
# ----------------------------------------------------------------------


def _utc_now() -> datetime:
    """
    Return the current timezone-aware UTC timestamp.
    """

    return datetime.now(
        timezone.utc,
    )


async def _get_user_or_404(
    db: AsyncSession,
    user_id: int,
) -> User:
    """
    Return a user by ID or raise a 404 response.
    """

    if not isinstance(user_id, int) or isinstance(user_id, bool) or user_id < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User ID must be a positive integer",
        )

    result = await db.execute(
        select(
            User,
        ).where(
            User.id == user_id,
        ),
    )

    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return user


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


async def _get_assessment_or_404(
    db: AsyncSession,
    assessment_id: int,
    *,
    include_relationships: bool = False,
) -> Assessment:
    """
    Return an assessment or raise a 404 response.
    """

    assessment = await AssessmentRepository(
        db,
    ).get_by_id(
        assessment_id,
        include_relationships=include_relationships,
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
    include_relationships: bool = True,
) -> AssessmentCandidate:
    """
    Return an assessment candidate or raise a 404 response.
    """

    candidate = await AssessmentCandidateRepository(
        db,
    ).get_candidate_by_id(
        candidate_id,
        include_relationships=include_relationships,
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
    include_relationships: bool = True,
) -> AssessmentScript:
    """
    Return an assessment script or raise a 404 response.
    """

    script = await AssessmentCandidateRepository(
        db,
    ).get_script_by_id(
        script_id,
        include_relationships=include_relationships,
    )

    if script is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assessment script not found",
        )

    return script


# ----------------------------------------------------------------------
# Assessment management scope
# ----------------------------------------------------------------------


def _ensure_course_management_access(
    current_user: User,
    course: Course,
) -> None:
    """
    Ensure the current user may manage assessments for the course.

    Teachers without administrator scope may manage only their own courses.
    School administrators may manage courses in their school.
    Platform administrators may manage courses across schools.
    """

    if (
        is_teacher_without_admin_scope(current_user)
        and course.teacher_id != current_user.id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only manage candidates for your own courses",
        )

    if (
        not is_platform_admin(current_user)
        and course.school_id != current_user.school_id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Course does not belong to your school",
        )


async def _ensure_assessment_management_access(
    db: AsyncSession,
    current_user: User,
    assessment: Assessment,
) -> Course:
    """
    Ensure the user may manage candidates and scripts for an assessment.
    """

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

    _ensure_course_management_access(
        current_user,
        course,
    )

    return course


async def _ensure_candidate_management_access(
    db: AsyncSession,
    current_user: User,
    candidate: AssessmentCandidate,
) -> Assessment:
    """
    Ensure the current user may manage a candidate allocation.
    """

    assessment = await _get_assessment_or_404(
        db,
        candidate.assessment_id,
        include_relationships=False,
    )

    await _ensure_assessment_management_access(
        db,
        current_user,
        assessment,
    )

    return assessment


async def _ensure_script_management_access(
    db: AsyncSession,
    current_user: User,
    script: AssessmentScript,
) -> AssessmentCandidate:
    """
    Ensure the current user may manage a script.
    """

    candidate = await _get_candidate_or_404(
        db,
        script.candidate_id,
        include_relationships=False,
    )

    await _ensure_candidate_management_access(
        db,
        current_user,
        candidate,
    )

    return candidate


# ----------------------------------------------------------------------
# Student validation
# ----------------------------------------------------------------------


async def _get_student_or_404(
    db: AsyncSession,
    student_id: int,
) -> User:
    """
    Return a user who has the student role.
    """

    student = await _get_user_or_404(
        db,
        student_id,
    )

    if not has_role(
        student,
        UserRole.STUDENT,
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="The selected user is not a student",
        )

    return student


def _ensure_student_school_scope(
    *,
    student: User,
    assessment: Assessment,
) -> None:
    """
    Ensure a candidate belongs to the assessment's school.
    """

    if student.school_id != assessment.school_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Student does not belong to the assessment school",
        )


# ----------------------------------------------------------------------
# Candidate allocation
# ----------------------------------------------------------------------


async def allocate_candidate(
    db: AsyncSession,
    current_user: User,
    assessment_id: int,
    student_id: int,
    *,
    candidate_number: str | None = None,
    access_arrangements: str | None = None,
) -> AssessmentCandidate:
    """
    Allocate a student to an assessment.

    Candidate allocation is permitted while an assessment is DRAFT or
    PUBLISHED. Closed and archived assessments cannot receive new
    candidates.

    The student must belong to the same school as the assessment and must
    have the student role.
    """

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

    if assessment.status not in {
        AssessmentStatus.DRAFT,
        AssessmentStatus.PUBLISHED,
    }:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Candidates cannot be allocated to a closed or " "archived assessment"
            ),
        )

    student = await _get_student_or_404(
        db,
        student_id,
    )

    _ensure_student_school_scope(
        student=student,
        assessment=assessment,
    )

    repository = AssessmentCandidateRepository(
        db,
    )

    if await repository.allocation_exists(
        assessment_id=assessment.id,
        student_id=student.id,
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Student is already allocated to this assessment",
        )

    candidate = AssessmentCandidate(
        assessment_id=assessment.id,
        student_id=student.id,
        status=AssessmentCandidateStatus.ALLOCATED,
        candidate_number=candidate_number,
        access_arrangements=access_arrangements,
    )

    try:
        candidate = await repository.create_candidate(
            candidate,
        )

        await db.commit()
        await db.refresh(
            candidate,
        )

    except IntegrityError as exc:
        await db.rollback()

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Student is already allocated to this assessment",
        ) from exc

    except Exception:
        await db.rollback()
        raise

    return candidate


async def get_candidate(
    db: AsyncSession,
    current_user: User,
    candidate_id: int,
) -> AssessmentCandidate:
    """
    Return a candidate visible to the current user.
    """

    candidate = await _get_candidate_or_404(
        db,
        candidate_id,
        include_relationships=True,
    )

    await _ensure_candidate_management_access(
        db,
        current_user,
        candidate,
    )

    return candidate


async def list_assessment_candidates(
    db: AsyncSession,
    current_user: User,
    assessment_id: int,
    *,
    candidate_status: AssessmentCandidateStatus | str | None = None,
) -> list[AssessmentCandidate]:
    """
    Return candidates allocated to an assessment.
    """

    total_started_at = perf_counter()
    stage_started_at = perf_counter()

    scope_result = await db.execute(
        select(
            Assessment.id,
            Assessment.school_id,
            Assessment.course_id,
            Course.id.label("course_record_id"),
            Course.school_id.label("course_school_id"),
            Course.teacher_id.label("course_teacher_id"),
        )
        .outerjoin(
            Course,
            Course.id == Assessment.course_id,
        )
        .where(
            Assessment.id == assessment_id,
        )
    )

    scope_row = scope_result.one_or_none()

    if scope_row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assessment not found",
        )

    (
        resolved_assessment_id,
        assessment_school_id,
        assessment_course_id,
        course_record_id,
        course_school_id,
        course_teacher_id,
    ) = scope_row

    if course_record_id is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found",
        )

    if (
        not is_platform_admin(current_user)
        and assessment_school_id != current_user.school_id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Assessment does not belong to your school",
        )

    if course_school_id != assessment_school_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Assessment and course school scope are inconsistent",
        )

    if (
        is_teacher_without_admin_scope(current_user)
        and course_teacher_id != current_user.id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only manage candidates for your own courses",
        )

    if (
        not is_platform_admin(current_user)
        and course_school_id != current_user.school_id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Course does not belong to your school",
        )

    scope_ms = (
        perf_counter() - stage_started_at
    ) * 1000

    stage_started_at = perf_counter()

    candidates = await AssessmentCandidateRepository(
        db,
    ).list_candidates_by_assessment(
        resolved_assessment_id,
        status=candidate_status,
        include_relationships=False,
        workspace_relationships=True,
    )

    candidate_query_ms = (
        perf_counter() - stage_started_at
    ) * 1000

    total_ms = (
        perf_counter() - total_started_at
    ) * 1000

    print(
        "[CANDIDATE TIMING] "
        f"assessment={assessment_id} "
        f"scope={scope_ms:.1f}ms "
        f"query={candidate_query_ms:.1f}ms "
        f"total={total_ms:.1f}ms "
        f"candidates={len(candidates)}"
    )

    return candidates

async def update_candidate_details(
    db: AsyncSession,
    current_user: User,
    candidate_id: int,
    *,
    candidate_number: str | None = None,
    access_arrangements: str | None = None,
) -> AssessmentCandidate:
    """
    Update candidate metadata.

    Candidate metadata is locked after submission, withdrawal, or absence.
    """

    candidate = await _get_candidate_or_404(
        db,
        candidate_id,
        include_relationships=False,
    )

    await _ensure_candidate_management_access(
        db,
        current_user,
        candidate,
    )

    if candidate.status in {
        AssessmentCandidateStatus.SUBMITTED,
        AssessmentCandidateStatus.WITHDRAWN,
        AssessmentCandidateStatus.ABSENT,
    }:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Candidate details can no longer be changed",
        )

    candidate.candidate_number = candidate_number
    candidate.access_arrangements = access_arrangements

    repository = AssessmentCandidateRepository(
        db,
    )

    try:
        candidate = await repository.save_candidate(
            candidate,
        )

        await db.commit()
        await db.refresh(
            candidate,
        )

    except Exception:
        await db.rollback()
        raise

    return candidate


# ----------------------------------------------------------------------
# Candidate lifecycle
# ----------------------------------------------------------------------


_ALLOWED_CANDIDATE_TRANSITIONS: dict[
    AssessmentCandidateStatus,
    set[AssessmentCandidateStatus],
] = {
    AssessmentCandidateStatus.ALLOCATED: {
        AssessmentCandidateStatus.STARTED,
        AssessmentCandidateStatus.WITHDRAWN,
        AssessmentCandidateStatus.ABSENT,
    },
    AssessmentCandidateStatus.STARTED: {
        AssessmentCandidateStatus.SUBMITTED,
        AssessmentCandidateStatus.WITHDRAWN,
    },
    AssessmentCandidateStatus.SUBMITTED: set(),
    AssessmentCandidateStatus.WITHDRAWN: set(),
    AssessmentCandidateStatus.ABSENT: set(),
}


def _normalise_candidate_status(
    value: AssessmentCandidateStatus | str,
) -> AssessmentCandidateStatus:
    """
    Convert input into an AssessmentCandidateStatus.
    """

    if isinstance(
        value,
        AssessmentCandidateStatus,
    ):
        return value

    try:
        return AssessmentCandidateStatus(
            value,
        )
    except (TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid assessment candidate status: {value!r}",
        ) from exc


async def transition_candidate_status(
    db: AsyncSession,
    current_user: User,
    candidate_id: int,
    new_status: AssessmentCandidateStatus | str,
) -> AssessmentCandidate:
    """
    Move a candidate through an allowed participation transition.
    """

    candidate = await _get_candidate_or_404(
        db,
        candidate_id,
        include_relationships=False,
    )

    assessment = await _ensure_candidate_management_access(
        db,
        current_user,
        candidate,
    )

    requested_status = _normalise_candidate_status(
        new_status,
    )

    if requested_status == candidate.status:
        return candidate

    if (
        requested_status == AssessmentCandidateStatus.STARTED
        and assessment.status != AssessmentStatus.PUBLISHED
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Candidate cannot start until the assessment is published",
        )

    allowed_targets = _ALLOWED_CANDIDATE_TRANSITIONS.get(
        candidate.status,
        set(),
    )

    if requested_status not in allowed_targets:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Invalid assessment candidate status transition: "
                f"{candidate.status.value} -> {requested_status.value}"
            ),
        )

    now = _utc_now()

    candidate.status = requested_status

    if requested_status == AssessmentCandidateStatus.STARTED:
        candidate.started_at = candidate.started_at or now

    elif requested_status == AssessmentCandidateStatus.SUBMITTED:
        candidate.submitted_at = candidate.submitted_at or now

    repository = AssessmentCandidateRepository(
        db,
    )

    try:
        candidate = await repository.save_candidate(
            candidate,
        )

        await db.commit()
        await db.refresh(
            candidate,
        )

    except Exception:
        await db.rollback()
        raise

    return candidate


async def start_candidate(
    db: AsyncSession,
    current_user: User,
    candidate_id: int,
) -> AssessmentCandidate:
    """
    Mark an allocated candidate as having started the assessment.
    """

    return await transition_candidate_status(
        db,
        current_user,
        candidate_id,
        AssessmentCandidateStatus.STARTED,
    )


async def submit_candidate(
    db: AsyncSession,
    current_user: User,
    candidate_id: int,
) -> AssessmentCandidate:
    """
    Mark a started candidate as submitted.
    """

    return await transition_candidate_status(
        db,
        current_user,
        candidate_id,
        AssessmentCandidateStatus.SUBMITTED,
    )


async def withdraw_candidate(
    db: AsyncSession,
    current_user: User,
    candidate_id: int,
) -> AssessmentCandidate:
    """
    Withdraw an allocated or started candidate.
    """

    return await transition_candidate_status(
        db,
        current_user,
        candidate_id,
        AssessmentCandidateStatus.WITHDRAWN,
    )


async def mark_candidate_absent(
    db: AsyncSession,
    current_user: User,
    candidate_id: int,
) -> AssessmentCandidate:
    """
    Mark an allocated candidate absent.
    """

    return await transition_candidate_status(
        db,
        current_user,
        candidate_id,
        AssessmentCandidateStatus.ABSENT,
    )


async def delete_candidate(
    db: AsyncSession,
    current_user: User,
    candidate_id: int,
) -> None:
    """
    Delete an untouched candidate allocation.

    Once a candidate has started, submitted, been withdrawn, been marked
    absent, or acquired script history, the allocation is retained.
    """

    candidate = await _get_candidate_or_404(
        db,
        candidate_id,
        include_relationships=True,
    )

    await _ensure_candidate_management_access(
        db,
        current_user,
        candidate,
    )

    if candidate.status != AssessmentCandidateStatus.ALLOCATED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only untouched allocated candidates can be deleted",
        )

    if candidate.scripts:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Candidate cannot be deleted after script creation",
        )

    repository = AssessmentCandidateRepository(
        db,
    )

    try:
        await repository.delete_candidate(
            candidate,
        )

        await db.commit()

    except Exception:
        await db.rollback()
        raise


# ----------------------------------------------------------------------
# Script creation and retrieval
# ----------------------------------------------------------------------


async def create_script_version(
    db: AsyncSession,
    current_user: User,
    candidate_id: int,
    *,
    source_type: str | None = None,
    source_filename: str | None = None,
    storage_key: str | None = None,
    mime_type: str | None = None,
    checksum: str | None = None,
    initial_status: AssessmentScriptStatus = AssessmentScriptStatus.NOT_SUBMITTED,
    commit_transaction: bool = True,
) -> AssessmentScript:
    """
    Create the next script version for a candidate.

    Withdrawn and absent candidates cannot receive scripts.

    Database uniqueness on ``(candidate_id, version)`` remains the final
    concurrency safeguard if two version-creation requests race.
    """

    candidate = await _get_candidate_or_404(
        db,
        candidate_id,
        include_relationships=False,
    )

    assessment = await _ensure_candidate_management_access(
        db,
        current_user,
        candidate,
    )

    if assessment.status == AssessmentStatus.ARCHIVED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Scripts cannot be created for archived assessments",
        )

    if candidate.status in {
        AssessmentCandidateStatus.WITHDRAWN,
        AssessmentCandidateStatus.ABSENT,
    }:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Scripts cannot be created for this candidate",
        )

    if initial_status not in {
        AssessmentScriptStatus.NOT_SUBMITTED,
        AssessmentScriptStatus.SUBMITTED,
    }:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="A newly created script must be unsubmitted or submitted",
        )

    now = _utc_now()

    repository = AssessmentCandidateRepository(
        db,
    )

    version = await repository.get_next_script_version(
        candidate.id,
    )

    script = AssessmentScript(
        candidate_id=candidate.id,
        version=version,
        status=initial_status,
        source_type=source_type,
        source_filename=source_filename,
        storage_key=storage_key,
        mime_type=mime_type,
        checksum=checksum,
        submitted_at=(
            now
            if initial_status == AssessmentScriptStatus.SUBMITTED
            else None
        ),
    )

    if initial_status == AssessmentScriptStatus.SUBMITTED:
        if candidate.status == AssessmentCandidateStatus.ALLOCATED:
            candidate.started_at = candidate.started_at or now

        if candidate.status in {
            AssessmentCandidateStatus.ALLOCATED,
            AssessmentCandidateStatus.STARTED,
        }:
            candidate.status = AssessmentCandidateStatus.SUBMITTED
            candidate.submitted_at = candidate.submitted_at or now

    try:
        script = await repository.create_script(
            script,
        )

        if initial_status == AssessmentScriptStatus.SUBMITTED:
            await repository.save_candidate(
                candidate,
            )

        if commit_transaction:
            await db.commit()
            await db.refresh(
                script,
            )
        else:
            await db.flush()

    except IntegrityError as exc:
        await db.rollback()

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "A conflicting script version was created concurrently; "
                "retry the operation"
            ),
        ) from exc

    except Exception:
        await db.rollback()
        raise

    return script


async def get_script(
    db: AsyncSession,
    current_user: User,
    script_id: int,
) -> AssessmentScript:
    """
    Return a script visible to the current user.
    """

    script = await _get_script_or_404(
        db,
        script_id,
        include_relationships=True,
    )

    await _ensure_script_management_access(
        db,
        current_user,
        script,
    )

    return script


async def list_candidate_scripts(
    db: AsyncSession,
    current_user: User,
    candidate_id: int,
    *,
    script_status: AssessmentScriptStatus | str | None = None,
) -> list[AssessmentScript]:
    """
    Return all script versions for a candidate.
    """

    candidate = await _get_candidate_or_404(
        db,
        candidate_id,
        include_relationships=False,
    )

    await _ensure_candidate_management_access(
        db,
        current_user,
        candidate,
    )

    return await AssessmentCandidateRepository(
        db,
    ).list_scripts_by_candidate(
        candidate.id,
        status=script_status,
        include_relationships=True,
    )


# ----------------------------------------------------------------------
# Script lifecycle
# ----------------------------------------------------------------------


_ALLOWED_SCRIPT_TRANSITIONS: dict[
    AssessmentScriptStatus,
    set[AssessmentScriptStatus],
] = {
    AssessmentScriptStatus.NOT_SUBMITTED: {
        AssessmentScriptStatus.SUBMITTED,
    },
    AssessmentScriptStatus.SUBMITTED: {
        AssessmentScriptStatus.MARKING,
    },
    AssessmentScriptStatus.MARKING: {
        AssessmentScriptStatus.MARKED,
    },
    AssessmentScriptStatus.MARKED: {
        AssessmentScriptStatus.MODERATION,
        AssessmentScriptStatus.FINALISED,
    },
    AssessmentScriptStatus.MODERATION: {
        AssessmentScriptStatus.FINALISED,
    },
    AssessmentScriptStatus.FINALISED: set(),
}


def _normalise_script_status(
    value: AssessmentScriptStatus | str,
) -> AssessmentScriptStatus:
    """
    Convert input into an AssessmentScriptStatus.
    """

    if isinstance(
        value,
        AssessmentScriptStatus,
    ):
        return value

    try:
        return AssessmentScriptStatus(
            value,
        )
    except (TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid assessment script status: {value!r}",
        ) from exc


async def transition_script_status(
    db: AsyncSession,
    current_user: User,
    script_id: int,
    new_status: AssessmentScriptStatus | str,
) -> AssessmentScript:
    """
    Move a script through its controlled lifecycle.

    Supported transitions:

        NOT_SUBMITTED -> SUBMITTED
        SUBMITTED -> MARKING
        MARKING -> MARKED
        MARKED -> MODERATION
        MARKED -> FINALISED
        MODERATION -> FINALISED
    """

    script = await _get_script_or_404(
        db,
        script_id,
        include_relationships=False,
    )

    candidate = await _ensure_script_management_access(
        db,
        current_user,
        script,
    )

    requested_status = _normalise_script_status(
        new_status,
    )

    if requested_status == script.status:
        return script

    allowed_targets = _ALLOWED_SCRIPT_TRANSITIONS.get(
        script.status,
        set(),
    )

    if requested_status not in allowed_targets:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Invalid assessment script status transition: "
                f"{script.status.value} -> {requested_status.value}"
            ),
        )

    now = _utc_now()

    script.status = requested_status

    if requested_status == AssessmentScriptStatus.SUBMITTED:
        script.submitted_at = script.submitted_at or now

        if candidate.status == AssessmentCandidateStatus.ALLOCATED:
            candidate.started_at = candidate.started_at or now

        if candidate.status in {
            AssessmentCandidateStatus.ALLOCATED,
            AssessmentCandidateStatus.STARTED,
        }:
            candidate.status = AssessmentCandidateStatus.SUBMITTED
            candidate.submitted_at = candidate.submitted_at or now

    elif requested_status == AssessmentScriptStatus.MARKING:
        script.marking_started_at = script.marking_started_at or now

    elif requested_status == AssessmentScriptStatus.MARKED:
        script.marked_at = script.marked_at or now

    elif requested_status == AssessmentScriptStatus.FINALISED:
        script.finalised_at = script.finalised_at or now

    repository = AssessmentCandidateRepository(
        db,
    )

    try:
        script = await repository.save_script(
            script,
        )

        if requested_status == AssessmentScriptStatus.SUBMITTED:
            await repository.save_candidate(
                candidate,
            )

        await db.commit()
        await db.refresh(
            script,
        )

    except Exception:
        await db.rollback()
        raise

    return script


async def submit_script(
    db: AsyncSession,
    current_user: User,
    script_id: int,
) -> AssessmentScript:
    """
    Submit a script for marking.
    """

    return await transition_script_status(
        db,
        current_user,
        script_id,
        AssessmentScriptStatus.SUBMITTED,
    )


async def start_script_marking(
    db: AsyncSession,
    current_user: User,
    script_id: int,
) -> AssessmentScript:
    """
    Move a submitted script into marking.
    """

    return await transition_script_status(
        db,
        current_user,
        script_id,
        AssessmentScriptStatus.MARKING,
    )


async def mark_script_complete(
    db: AsyncSession,
    current_user: User,
    script_id: int,
) -> AssessmentScript:
    """
    Mark primary marking as complete.
    """

    return await transition_script_status(
        db,
        current_user,
        script_id,
        AssessmentScriptStatus.MARKED,
    )


async def send_script_to_moderation(
    db: AsyncSession,
    current_user: User,
    script_id: int,
) -> AssessmentScript:
    """
    Move a marked script into moderation.
    """

    return await transition_script_status(
        db,
        current_user,
        script_id,
        AssessmentScriptStatus.MODERATION,
    )


async def finalise_script(
    db: AsyncSession,
    current_user: User,
    script_id: int,
) -> AssessmentScript:
    """
    Finalise a marked or moderated script.
    """

    return await transition_script_status(
        db,
        current_user,
        script_id,
        AssessmentScriptStatus.FINALISED,
    )


async def delete_script(
    db: AsyncSession,
    current_user: User,
    script_id: int,
) -> None:
    """
    Delete an unsubmitted script version.

    Once submitted, scripts are retained for marking, moderation, analysis,
    and audit history.
    """

    script = await _get_script_or_404(
        db,
        script_id,
        include_relationships=False,
    )

    await _ensure_script_management_access(
        db,
        current_user,
        script,
    )

    if script.status != AssessmentScriptStatus.NOT_SUBMITTED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only unsubmitted scripts can be deleted",
        )

    repository = AssessmentCandidateRepository(
        db,
    )

    try:
        await repository.delete_script(
            script,
        )

        await db.commit()

    except Exception:
        await db.rollback()
        raise





