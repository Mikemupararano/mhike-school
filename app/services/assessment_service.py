from __future__ import annotations

from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.assessment import Assessment, AssessmentStatus
from app.models.course import Course
from app.models.user import User, UserRole
from app.repositories.assessment import AssessmentRepository
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
# Validation helpers
# ----------------------------------------------------------------------


def _validate_assessment_dates(
    scheduled_at: datetime | None,
    closes_at: datetime | None,
) -> None:
    """
    Validate the assessment scheduling window.

    When both timestamps are supplied, the closing time must be later than
    the scheduled/start time.
    """

    if scheduled_at is not None and closes_at is not None and closes_at <= scheduled_at:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Assessment closing time must be later than its scheduled time",
        )


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


def _ensure_course_management_access(
    current_user: User,
    course: Course,
) -> None:
    """
    Ensure the current user may manage assessments for the course.

    Teachers without administrative scope may manage assessment content only
    for courses assigned to them.

    School administrators may manage courses within their own school.

    Platform administrators may manage courses across schools.
    """

    if (
        is_teacher_without_admin_scope(current_user)
        and course.teacher_id != current_user.id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only manage assessments for your own courses",
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
    Ensure the current user may manage the supplied assessment.

    The assessment's Course is used as the authoritative teaching ownership
    boundary.
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


async def _get_assessment_or_404(
    db: AsyncSession,
    assessment_id: int,
    *,
    include_relationships: bool = True,
) -> Assessment:
    """
    Return an assessment by global identifier or raise a 404 response.

    This helper performs existence lookup only. Callers remain responsible
    for applying school and role-based access rules.
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


# ----------------------------------------------------------------------
# Assessment creation
# ----------------------------------------------------------------------


async def create_assessment(
    db: AsyncSession,
    current_user: User,
    course_id: int,
    title: str,
    description: str | None = None,
    assessment_type: str | None = None,
    academic_year: str | None = None,
    term: str | None = None,
    anonymous_marking: bool = False,
    scheduled_at: datetime | None = None,
    closes_at: datetime | None = None,
) -> Assessment:
    """
    Create a draft assessment for a course the current user may manage.

    Teachers may create assessments only for their own courses.

    School administrators may create assessments for courses in their own
    school.

    Platform administrators may create assessments across schools.

    New assessments always begin in DRAFT state. Publishing is an explicit
    lifecycle operation and must never occur implicitly during creation.
    """

    course = await _get_course_or_404(
        db,
        course_id,
    )

    _ensure_course_management_access(
        current_user,
        course,
    )

    _validate_assessment_dates(
        scheduled_at,
        closes_at,
    )

    assessment = Assessment(
        school_id=course.school_id,
        course_id=course.id,
        created_by_id=current_user.id,
        title=title,
        description=description,
        assessment_type=assessment_type,
        academic_year=academic_year,
        term=term,
        status=AssessmentStatus.DRAFT,
        anonymous_marking=anonymous_marking,
        scheduled_at=scheduled_at,
        closes_at=closes_at,
    )

    repository = AssessmentRepository(
        db,
    )

    try:
        assessment = await repository.create(
            assessment,
        )

        await db.commit()

        await db.refresh(
            assessment,
        )

    except Exception:
        await db.rollback()
        raise

    return assessment


# ----------------------------------------------------------------------
# Assessment retrieval
# ----------------------------------------------------------------------


async def get_assessment(
    db: AsyncSession,
    current_user: User,
    assessment_id: int,
    *,
    include_relationships: bool = True,
) -> Assessment:
    """
    Return an assessment visible to the current user.

    Platform administrators may retrieve assessments globally.

    Other users are restricted to their own school.

    Teachers without administrator scope are additionally restricted to
    assessments belonging to courses they teach.
    """

    assessment = await _get_assessment_or_404(
        db,
        assessment_id,
        include_relationships=include_relationships,
    )

    if is_platform_admin(current_user):
        return assessment

    if current_user.school_id is None or assessment.school_id != current_user.school_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assessment not found",
        )

    if is_teacher_without_admin_scope(current_user):
        course = await _get_course_or_404(
            db,
            assessment.course_id,
        )

        if course.teacher_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only access assessments for your own courses",
            )

    return assessment


async def list_assessments(
    db: AsyncSession,
    current_user: User,
    *,
    course_id: int | None = None,
    assessment_status: AssessmentStatus | str | None = None,
    academic_year: str | None = None,
    term: str | None = None,
    include_relationships: bool = True,
) -> list[Assessment]:
    """
    Return assessments visible to the current user.

    Teachers without administrator scope see assessments they created.

    School administrators see assessments in their own school.

    Platform administrators see assessments across schools.

    Course, status, academic-year and term filters may be applied where
    supported by the repository.
    """

    repository = AssessmentRepository(
        db,
    )

    if is_platform_admin(current_user):
        assessments = await repository.list_all(
            status=assessment_status,
            include_relationships=include_relationships,
        )

        if course_id is not None:
            assessments = [
                assessment
                for assessment in assessments
                if assessment.course_id == course_id
            ]

        if academic_year is not None:
            normalised_academic_year = academic_year.strip()
            assessments = [
                assessment
                for assessment in assessments
                if assessment.academic_year == normalised_academic_year
            ]

        if term is not None:
            normalised_term = term.strip()
            assessments = [
                assessment
                for assessment in assessments
                if assessment.term == normalised_term
            ]

        return assessments

    if current_user.school_id is None:
        return []

    if is_teacher_without_admin_scope(current_user):
        assessments = await repository.list_by_creator(
            current_user.id,
            school_id=current_user.school_id,
            status=assessment_status,
            include_relationships=include_relationships,
        )

        if course_id is not None:
            assessments = [
                assessment
                for assessment in assessments
                if assessment.course_id == course_id
            ]

        if academic_year is not None:
            normalised_academic_year = academic_year.strip()
            assessments = [
                assessment
                for assessment in assessments
                if assessment.academic_year == normalised_academic_year
            ]

        if term is not None:
            normalised_term = term.strip()
            assessments = [
                assessment
                for assessment in assessments
                if assessment.term == normalised_term
            ]

        return assessments

    return await repository.list_by_school(
        current_user.school_id,
        course_id=course_id,
        status=assessment_status,
        academic_year=academic_year,
        term=term,
        include_relationships=include_relationships,
    )


# ----------------------------------------------------------------------
# Assessment editing
# ----------------------------------------------------------------------


async def update_assessment(
    db: AsyncSession,
    current_user: User,
    assessment_id: int,
    *,
    title: str | None = None,
    description: str | None = None,
    assessment_type: str | None = None,
    academic_year: str | None = None,
    term: str | None = None,
    anonymous_marking: bool | None = None,
    scheduled_at: datetime | None = None,
    closes_at: datetime | None = None,
) -> Assessment:
    """
    Update a draft assessment.

    General assessment definition is intentionally locked once the assessment
    has been published. Published assessment lifecycle changes should occur
    through explicit status-transition operations.
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

    if assessment.status != AssessmentStatus.DRAFT:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only draft assessments can be edited",
        )

    if title is not None:
        assessment.title = title

    if description is not None:
        assessment.description = description

    if assessment_type is not None:
        assessment.assessment_type = assessment_type

    if academic_year is not None:
        assessment.academic_year = academic_year

    if term is not None:
        assessment.term = term

    if anonymous_marking is not None:
        assessment.anonymous_marking = anonymous_marking

    if scheduled_at is not None:
        assessment.scheduled_at = scheduled_at

    if closes_at is not None:
        assessment.closes_at = closes_at

    _validate_assessment_dates(
        assessment.scheduled_at,
        assessment.closes_at,
    )

    repository = AssessmentRepository(
        db,
    )

    try:
        assessment = await repository.save(
            assessment,
        )

        await db.commit()

        await db.refresh(
            assessment,
        )

    except Exception:
        await db.rollback()
        raise

    return assessment


# ----------------------------------------------------------------------
# Lifecycle transitions
# ----------------------------------------------------------------------


_ALLOWED_STATUS_TRANSITIONS: dict[
    AssessmentStatus,
    set[AssessmentStatus],
] = {
    AssessmentStatus.DRAFT: {
        AssessmentStatus.PUBLISHED,
        AssessmentStatus.ARCHIVED,
    },
    AssessmentStatus.PUBLISHED: {
        AssessmentStatus.CLOSED,
    },
    AssessmentStatus.CLOSED: {
        AssessmentStatus.ARCHIVED,
    },
    AssessmentStatus.ARCHIVED: set(),
}


def _normalise_requested_status(
    requested_status: AssessmentStatus | str,
) -> AssessmentStatus:
    """
    Convert an assessment-status input into AssessmentStatus.
    """

    if isinstance(
        requested_status,
        AssessmentStatus,
    ):
        return requested_status

    try:
        return AssessmentStatus(
            requested_status,
        )
    except (TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid assessment status: {requested_status!r}",
        ) from exc


def _validate_publishable_assessment(
    assessment: Assessment,
) -> None:
    """
    Ensure an assessment has sufficient question structure to publish.

    At least one markable question with a positive maximum mark is required.
    """

    markable_questions = [
        question for question in assessment.questions if question.is_markable
    ]

    if not markable_questions:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Assessment must contain at least one markable question before publishing",
        )

    if not any(question.maximum_mark > 0 for question in markable_questions):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Assessment must contain a positive available mark before publishing",
        )


async def transition_assessment_status(
    db: AsyncSession,
    current_user: User,
    assessment_id: int,
    new_status: AssessmentStatus | str,
) -> Assessment:
    """
    Move an assessment through its controlled lifecycle.

    Supported transitions:

        DRAFT -> PUBLISHED
        DRAFT -> ARCHIVED
        PUBLISHED -> CLOSED
        CLOSED -> ARCHIVED

    ARCHIVED is terminal.

    Publishing also validates that the assessment contains at least one
    markable question carrying positive available marks.
    """

    assessment = await _get_assessment_or_404(
        db,
        assessment_id,
        include_relationships=True,
    )

    await _ensure_assessment_management_access(
        db,
        current_user,
        assessment,
    )

    requested_status = _normalise_requested_status(
        new_status,
    )

    if requested_status == assessment.status:
        return assessment

    allowed_targets = _ALLOWED_STATUS_TRANSITIONS.get(
        assessment.status,
        set(),
    )

    if requested_status not in allowed_targets:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Invalid assessment status transition: "
                f"{assessment.status.value} -> {requested_status.value}"
            ),
        )

    if requested_status == AssessmentStatus.PUBLISHED:
        _validate_publishable_assessment(
            assessment,
        )

    assessment.status = requested_status

    repository = AssessmentRepository(
        db,
    )

    try:
        assessment = await repository.save(
            assessment,
        )

        await db.commit()

        await db.refresh(
            assessment,
        )

    except Exception:
        await db.rollback()
        raise

    return assessment


async def publish_assessment(
    db: AsyncSession,
    current_user: User,
    assessment_id: int,
) -> Assessment:
    """
    Publish a draft assessment.
    """

    return await transition_assessment_status(
        db,
        current_user,
        assessment_id,
        AssessmentStatus.PUBLISHED,
    )


async def close_assessment(
    db: AsyncSession,
    current_user: User,
    assessment_id: int,
) -> Assessment:
    """
    Close a published assessment.
    """

    return await transition_assessment_status(
        db,
        current_user,
        assessment_id,
        AssessmentStatus.CLOSED,
    )


async def archive_assessment(
    db: AsyncSession,
    current_user: User,
    assessment_id: int,
) -> Assessment:
    """
    Archive an eligible assessment.
    """

    return await transition_assessment_status(
        db,
        current_user,
        assessment_id,
        AssessmentStatus.ARCHIVED,
    )


# ----------------------------------------------------------------------
# Deletion
# ----------------------------------------------------------------------


async def delete_assessment(
    db: AsyncSession,
    current_user: User,
    assessment_id: int,
) -> None:
    """
    Delete a draft assessment.

    Assessments that have entered the published lifecycle are retained rather
    than physically deleted because they may have candidate, script, response,
    marking or moderation history.
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

    if assessment.status != AssessmentStatus.DRAFT:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only draft assessments can be deleted",
        )

    repository = AssessmentRepository(
        db,
    )

    try:
        await repository.delete(
            assessment,
        )

        await db.commit()

    except Exception:
        await db.rollback()
        raise
