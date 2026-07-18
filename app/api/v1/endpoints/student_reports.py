from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.models.user_role import UserRole
from app.repositories.parent_student import ParentStudentRepository
from app.repositories.student_reports import (
    REPORT_STATUS_DRAFT,
    REPORT_STATUS_READY_FOR_SMT,
    REPORT_STATUS_RETURNED_BY_SMT,
    REPORT_STATUS_RETURNED_BY_TUTOR,
    REPORT_STATUS_SUBMITTED,
    REPORT_STATUS_TUTOR_REVIEW,
    approve_student_report,
    begin_tutor_review,
    correct_student_report_as_tutor,
    create_student_report,
    delete_student_report,
    get_student_report,
    get_student_report_completion_overview,
    get_student_report_dashboard_counts,
    list_reports_for_student,
    list_student_report_review_queue,
    list_student_reports,
    list_tutor_student_report_review_queue,
    mark_student_report_ready_for_smt,
    publish_reports_for_session,
    return_student_report,
    return_student_report_to_teacher,
    submit_student_report,
    update_student_report,
    user_can_tutor_review_student,
)
from app.schemas.student_report import (
    StudentReportCompletionOverview,
    StudentReportCreate,
    StudentReportRead,
    StudentReportReviewDashboard,
    StudentReportReviewDecision,
    StudentReportTutorCorrection,
    StudentReportTutorDecision,
    StudentReportUpdate,
)

router = APIRouter()


# ---------------------------------------------------------------------------
# Role and school helpers
# ---------------------------------------------------------------------------


def _require_school_id(user: User) -> int:
    if user.school_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not linked to a school.",
        )

    return user.school_id


def _normalise_role(value: object) -> str:
    if isinstance(value, str):
        return value

    role = getattr(value, "role", None)

    if isinstance(role, str):
        return role

    if hasattr(role, "value"):
        return str(role.value)

    if hasattr(value, "value"):
        return str(value.value)

    return str(value)


def _user_has_role(user: User, role: UserRole) -> bool:
    expected_role = _normalise_role(role)

    return any(_normalise_role(user_role) == expected_role for user_role in user.roles)


def _is_school_staff(user: User) -> bool:
    return any(
        _user_has_role(user, role)
        for role in (
            UserRole.SCHOOL_ADMIN,
            UserRole.TEACHER,
            UserRole.PLATFORM_ADMIN,
        )
    )


def _can_review_reports(user: User) -> bool:
    """
    SMT-style report review.

    At present, School Admin and Platform Admin represent the users
    permitted to perform the final review and approval stage.
    """

    return any(
        _user_has_role(user, role)
        for role in (
            UserRole.SCHOOL_ADMIN,
            UserRole.PLATFORM_ADMIN,
        )
    )


def _can_publish_reports(user: User) -> bool:
    return any(
        _user_has_role(user, role)
        for role in (
            UserRole.SCHOOL_ADMIN,
            UserRole.PLATFORM_ADMIN,
        )
    )


def _can_attempt_tutor_review(user: User) -> bool:
    """
    Teachers may be tutors, but their actual permission to review a
    particular pupil is checked against tutor-group membership.
    """

    return any(
        _user_has_role(user, role)
        for role in (
            UserRole.TEACHER,
            UserRole.SCHOOL_ADMIN,
            UserRole.PLATFORM_ADMIN,
        )
    )


def _require_school_staff(user: User) -> None:
    if not _is_school_staff(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only school staff can access student reports.",
        )


def _require_report_reviewer(user: User) -> None:
    if not _can_review_reports(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only school administrators can complete the SMT review.",
        )


def _require_report_publisher(user: User) -> None:
    if not _can_publish_reports(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only school administrators can publish student reports.",
        )


def _require_tutor_review_role(user: User) -> None:
    if not _can_attempt_tutor_review(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only tutors or school administrators can review reports.",
        )


def _require_teacher_report_ownership(
    *,
    user: User,
    report_teacher_id: int | None,
    action: str,
) -> None:
    """
    Teachers may only change reports they own.

    School Admin and Platform Admin are not restricted by teacher ownership
    because they may need to correct reports during administrative review.
    """

    if (
        _user_has_role(user, UserRole.TEACHER)
        and not _user_has_role(user, UserRole.SCHOOL_ADMIN)
        and not _user_has_role(user, UserRole.PLATFORM_ADMIN)
        and report_teacher_id != user.id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Teachers can only {action} their own reports.",
        )


async def _require_tutor_access_to_student(
    *,
    db: AsyncSession,
    user: User,
    school_id: int,
    student_id: int,
) -> None:
    """
    School and Platform Admin users may review any pupil within the school.

    A teacher must be assigned as a tutor to the pupil's tutor group.
    The repository performs the actual tutor-group membership lookup.
    """

    if _can_review_reports(user):
        return

    permitted = await user_can_tutor_review_student(
        db,
        school_id=school_id,
        tutor_id=user.id,
        student_id=student_id,
    )

    if not permitted:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "You can only review reports for pupils in your own " "tutor group."
            ),
        )


async def _get_report_or_404(
    *,
    db: AsyncSession,
    report_id: int,
    school_id: int,
):
    report = await get_student_report(
        db,
        report_id=report_id,
        school_id=school_id,
    )

    if report is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student report not found.",
        )

    return report


# ---------------------------------------------------------------------------
# General staff report access
# ---------------------------------------------------------------------------


@router.get(
    "/",
    response_model=list[StudentReportRead],
)
async def list_reports_endpoint(
    teacher_id: int | None = None,
    report_session_id: int | None = None,
    published: bool | None = None,
    status_filter: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[StudentReportRead]:
    school_id = _require_school_id(current_user)
    _require_school_staff(current_user)

    return await list_student_reports(
        db,
        school_id=school_id,
        teacher_id=teacher_id,
        report_session_id=report_session_id,
        published=published,
        status=status_filter,
    )


@router.post(
    "/",
    response_model=StudentReportRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_report_endpoint(
    payload: StudentReportCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> StudentReportRead:
    school_id = _require_school_id(current_user)
    _require_school_staff(current_user)

    return await create_student_report(
        db,
        school_id=school_id,
        teacher_id=current_user.id,
        payload=payload,
    )


@router.get(
    "/student/{student_id}",
    response_model=list[StudentReportRead],
)
async def list_student_reports_endpoint(
    student_id: int,
    report_session_id: int | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[StudentReportRead]:
    """
    Return all reports for one pupil.

    Subject teachers use this endpoint to read other subject reports for
    the same pupil. The frontend should exclude the report currently being
    edited from its 'Other Subject Reports' section.
    """

    school_id = _require_school_id(current_user)
    _require_school_staff(current_user)

    return await list_reports_for_student(
        db,
        school_id=school_id,
        student_id=student_id,
        report_session_id=report_session_id,
    )


# ---------------------------------------------------------------------------
# Parent report access
# ---------------------------------------------------------------------------


@router.get(
    "/parent",
    response_model=list[StudentReportRead],
)
async def list_parent_reports_endpoint(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[StudentReportRead]:
    school_id = _require_school_id(current_user)

    parent_repository = ParentStudentRepository(db)

    children = await parent_repository.list_children_for_parent(
        parent_id=current_user.id,
    )

    reports: list[StudentReportRead] = []

    for child in children:
        child_reports = await list_reports_for_student(
            db,
            school_id=school_id,
            student_id=child.student_id,
            published_only=True,
        )

        reports.extend(child_reports)

    return reports


# ---------------------------------------------------------------------------
# Teacher submission and resubmission
# ---------------------------------------------------------------------------


@router.post(
    "/{report_id}/submit",
    response_model=StudentReportRead,
)
async def submit_report_endpoint(
    report_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> StudentReportRead:
    school_id = _require_school_id(current_user)
    _require_school_staff(current_user)

    report = await _get_report_or_404(
        db=db,
        report_id=report_id,
        school_id=school_id,
    )

    _require_teacher_report_ownership(
        user=current_user,
        report_teacher_id=report.teacher_id,
        action="submit",
    )

    permitted_statuses = {
        REPORT_STATUS_DRAFT,
        REPORT_STATUS_RETURNED_BY_TUTOR,
        REPORT_STATUS_RETURNED_BY_SMT,
    }

    if report.status not in permitted_statuses:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Only draft reports or reports returned for correction "
                "can be submitted."
            ),
        )

    if not report.report_text or not report.report_text.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="The report text must be completed before submission.",
        )

    try:
        return await submit_student_report(
            db,
            report=report,
            submitted_by_id=current_user.id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc


# ---------------------------------------------------------------------------
# Tutor review
# ---------------------------------------------------------------------------


@router.get(
    "/tutor-review-queue",
    response_model=list[StudentReportRead],
)
async def list_tutor_review_queue_endpoint(
    report_session_id: int | None = None,
    student_id: int | None = None,
    limit: int = 100,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[StudentReportRead]:
    """
    Return reports belonging to pupils in the current tutor's tutor group.

    School Admin and Platform Admin may receive all matching reports within
    their school.
    """

    school_id = _require_school_id(current_user)
    _require_tutor_review_role(current_user)

    if limit < 1 or limit > 500:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Limit must be between 1 and 500.",
        )

    if offset < 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Offset cannot be negative.",
        )

    return await list_tutor_student_report_review_queue(
        db,
        school_id=school_id,
        tutor_id=current_user.id,
        report_session_id=report_session_id,
        student_id=student_id,
        include_all_school_reports=_can_review_reports(current_user),
        limit=limit,
        offset=offset,
    )


@router.post(
    "/{report_id}/begin-tutor-review",
    response_model=StudentReportRead,
)
async def begin_tutor_review_endpoint(
    report_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> StudentReportRead:
    school_id = _require_school_id(current_user)
    _require_tutor_review_role(current_user)

    report = await _get_report_or_404(
        db=db,
        report_id=report_id,
        school_id=school_id,
    )

    await _require_tutor_access_to_student(
        db=db,
        user=current_user,
        school_id=school_id,
        student_id=report.student_id,
    )

    if report.status != REPORT_STATUS_SUBMITTED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only submitted reports can enter tutor review.",
        )

    try:
        return await begin_tutor_review(
            db,
            report=report,
            tutor_id=current_user.id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc


@router.patch(
    "/{report_id}/tutor-correction",
    response_model=StudentReportRead,
)
async def tutor_correct_report_endpoint(
    report_id: int,
    payload: StudentReportTutorCorrection,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> StudentReportRead:
    """
    Allow a tutor to correct spelling, grammar, tone and consistency.

    Tutor changes must be recorded by the repository for audit purposes.
    """

    school_id = _require_school_id(current_user)
    _require_tutor_review_role(current_user)

    report = await _get_report_or_404(
        db=db,
        report_id=report_id,
        school_id=school_id,
    )

    await _require_tutor_access_to_student(
        db=db,
        user=current_user,
        school_id=school_id,
        student_id=report.student_id,
    )

    if report.status not in {
        REPORT_STATUS_SUBMITTED,
        REPORT_STATUS_TUTOR_REVIEW,
    }:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Tutor corrections can only be made to submitted reports "
                "or reports currently under tutor review."
            ),
        )

    try:
        return await correct_student_report_as_tutor(
            db,
            report=report,
            tutor_id=current_user.id,
            report_text=payload.report_text,
            tutor_review_comments=payload.tutor_review_comments,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc


@router.post(
    "/{report_id}/return-to-teacher",
    response_model=StudentReportRead,
)
async def tutor_return_report_endpoint(
    report_id: int,
    payload: StudentReportTutorDecision,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> StudentReportRead:
    school_id = _require_school_id(current_user)
    _require_tutor_review_role(current_user)

    report = await _get_report_or_404(
        db=db,
        report_id=report_id,
        school_id=school_id,
    )

    await _require_tutor_access_to_student(
        db=db,
        user=current_user,
        school_id=school_id,
        student_id=report.student_id,
    )

    if report.status not in {
        REPORT_STATUS_SUBMITTED,
        REPORT_STATUS_TUTOR_REVIEW,
    }:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Only submitted reports or reports under tutor review "
                "can be returned to the subject teacher."
            ),
        )

    comments = payload.tutor_review_comments

    if comments is None or not comments.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=(
                "Tutor review comments are required when returning a "
                "report to the subject teacher."
            ),
        )

    try:
        return await return_student_report_to_teacher(
            db,
            report=report,
            tutor_id=current_user.id,
            tutor_review_comments=comments.strip(),
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc


@router.post(
    "/{report_id}/ready-for-smt",
    response_model=StudentReportRead,
)
async def mark_report_ready_for_smt_endpoint(
    report_id: int,
    payload: StudentReportTutorDecision,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> StudentReportRead:
    school_id = _require_school_id(current_user)
    _require_tutor_review_role(current_user)

    report = await _get_report_or_404(
        db=db,
        report_id=report_id,
        school_id=school_id,
    )

    await _require_tutor_access_to_student(
        db=db,
        user=current_user,
        school_id=school_id,
        student_id=report.student_id,
    )

    if report.status not in {
        REPORT_STATUS_SUBMITTED,
        REPORT_STATUS_TUTOR_REVIEW,
    }:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Only submitted reports or reports under tutor review "
                "can be marked ready for SMT."
            ),
        )

    try:
        return await mark_student_report_ready_for_smt(
            db,
            report=report,
            tutor_id=current_user.id,
            tutor_review_comments=payload.tutor_review_comments,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc


# ---------------------------------------------------------------------------
# SMT / School Admin review
# ---------------------------------------------------------------------------


@router.get(
    "/review-queue",
    response_model=list[StudentReportRead],
)
async def list_review_queue_endpoint(
    teacher_id: int | None = None,
    report_session_id: int | None = None,
    student_id: int | None = None,
    limit: int = 100,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[StudentReportRead]:
    school_id = _require_school_id(current_user)
    _require_report_reviewer(current_user)

    if limit < 1 or limit > 500:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Limit must be between 1 and 500.",
        )

    if offset < 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Offset cannot be negative.",
        )

    return await list_student_report_review_queue(
        db,
        school_id=school_id,
        teacher_id=teacher_id,
        report_session_id=report_session_id,
        student_id=student_id,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/review-dashboard",
    response_model=StudentReportReviewDashboard,
    response_model_exclude_none=True,
)
async def review_dashboard_endpoint(
    teacher_id: int | None = None,
    report_session_id: int | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> StudentReportReviewDashboard:
    school_id = _require_school_id(current_user)
    _require_report_reviewer(current_user)

    counts = await get_student_report_dashboard_counts(
        db,
        school_id=school_id,
        teacher_id=teacher_id,
        report_session_id=report_session_id,
    )

    return StudentReportReviewDashboard(**counts)


@router.post(
    "/{report_id}/approve",
    response_model=StudentReportRead,
)
async def approve_report_endpoint(
    report_id: int,
    payload: StudentReportReviewDecision,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> StudentReportRead:
    school_id = _require_school_id(current_user)
    _require_report_reviewer(current_user)

    report = await _get_report_or_404(
        db=db,
        report_id=report_id,
        school_id=school_id,
    )

    if report.status not in {
        REPORT_STATUS_SUBMITTED,
        REPORT_STATUS_READY_FOR_SMT,
    }:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Only submitted reports or reports ready for SMT " "can be approved."
            ),
        )

    try:
        return await approve_student_report(
            db,
            report=report,
            reviewed_by_id=current_user.id,
            review_comments=payload.review_comments,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc


@router.post(
    "/{report_id}/return",
    response_model=StudentReportRead,
)
async def return_report_endpoint(
    report_id: int,
    payload: StudentReportReviewDecision,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> StudentReportRead:
    school_id = _require_school_id(current_user)
    _require_report_reviewer(current_user)

    report = await _get_report_or_404(
        db=db,
        report_id=report_id,
        school_id=school_id,
    )

    if report.status not in {
        REPORT_STATUS_SUBMITTED,
        REPORT_STATUS_READY_FOR_SMT,
    }:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Only submitted reports or reports awaiting SMT "
                "review can be returned."
            ),
        )

    comments = payload.review_comments

    if comments is None or not comments.strip():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Review comments are required when returning a report "
                "for correction."
            ),
        )

    try:
        return await return_student_report(
            db,
            report=report,
            reviewed_by_id=current_user.id,
            review_comments=comments.strip(),
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc


# ---------------------------------------------------------------------------
# Teacher completion overview
# ---------------------------------------------------------------------------


@router.get(
    "/completion-overview",
    response_model=StudentReportCompletionOverview,
)
async def completion_overview_endpoint(
    class_id: int,
    report_session_id: int,
    teacher_id: int | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> StudentReportCompletionOverview:
    """
    Return the complete class roster alongside the latest matching report.

    Pupils without a report are included with ``report_id=None`` and the
    synthetic status ``not_started``. This makes the endpoint authoritative
    for teacher completion tracking rather than relying only on reports that
    already exist.
    """

    school_id = _require_school_id(current_user)
    _require_school_staff(current_user)

    if class_id < 1:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Class ID must be a positive integer.",
        )

    if report_session_id < 1:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Report session ID must be a positive integer.",
        )

    resolved_teacher_id = teacher_id

    if (
        resolved_teacher_id is None
        and _user_has_role(current_user, UserRole.TEACHER)
        and not _user_has_role(current_user, UserRole.SCHOOL_ADMIN)
        and not _user_has_role(current_user, UserRole.PLATFORM_ADMIN)
    ):
        resolved_teacher_id = current_user.id

    overview = await get_student_report_completion_overview(
        db,
        school_id=school_id,
        class_id=class_id,
        report_session_id=report_session_id,
        teacher_id=resolved_teacher_id,
    )

    return StudentReportCompletionOverview(**overview)


# ---------------------------------------------------------------------------
# Publication
# ---------------------------------------------------------------------------


@router.post(
    "/publish-session/{report_session_id}",
)
async def publish_report_session_endpoint(
    report_session_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, int]:
    school_id = _require_school_id(current_user)
    _require_report_publisher(current_user)

    published_count = await publish_reports_for_session(
        db,
        school_id=school_id,
        report_session_id=report_session_id,
        published_by_id=current_user.id,
    )

    return {
        "published_count": published_count,
    }


# ---------------------------------------------------------------------------
# Individual report retrieval and editing
# ---------------------------------------------------------------------------


@router.get(
    "/{report_id}",
    response_model=StudentReportRead,
)
async def get_report_endpoint(
    report_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> StudentReportRead:
    school_id = _require_school_id(current_user)
    _require_school_staff(current_user)

    report = await _get_report_or_404(
        db=db,
        report_id=report_id,
        school_id=school_id,
    )

    return report


@router.patch(
    "/{report_id}",
    response_model=StudentReportRead,
)
async def update_report_endpoint(
    report_id: int,
    payload: StudentReportUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> StudentReportRead:
    school_id = _require_school_id(current_user)
    _require_school_staff(current_user)

    report = await _get_report_or_404(
        db=db,
        report_id=report_id,
        school_id=school_id,
    )

    _require_teacher_report_ownership(
        user=current_user,
        report_teacher_id=report.teacher_id,
        action="edit",
    )

    editable_statuses = {
        REPORT_STATUS_DRAFT,
        REPORT_STATUS_RETURNED_BY_TUTOR,
        REPORT_STATUS_RETURNED_BY_SMT,
    }

    if report.status not in editable_statuses:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Only draft reports or reports returned for correction "
                "can be edited by the subject teacher."
            ),
        )

    return await update_student_report(
        db,
        report=report,
        payload=payload,
        current_user=current_user,
    )


@router.delete(
    "/{report_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_report_endpoint(
    report_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    school_id = _require_school_id(current_user)
    _require_school_staff(current_user)

    report = await _get_report_or_404(
        db=db,
        report_id=report_id,
        school_id=school_id,
    )

    _require_teacher_report_ownership(
        user=current_user,
        report_teacher_id=report.teacher_id,
        action="delete",
    )

    if report.status != REPORT_STATUS_DRAFT:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only draft reports can be deleted.",
        )

    await delete_student_report(
        db,
        report=report,
    )
