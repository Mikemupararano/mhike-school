from __future__ import annotations

from io import BytesIO

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.models.user_role import UserRole
from app.repositories.parent_student import ParentStudentRepository
from app.repositories.student_reports import (
    REPORT_STATUS_APPROVED,
    REPORT_STATUS_DRAFT,
    REPORT_STATUS_PUBLISHED,
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
    update_student_report_as_reviewer,
    user_can_tutor_review_student,
)
from app.services.report_pdf import (
    ReportPdfData,
    ReportPdfField,
    ReportPdfSection,
    build_report_pdf_filename,
    generate_report_pdf_bytes,
)
from app.services.report_zip import (
    ReportZipItem,
    generate_report_zip_bytes,
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


def _user_has_role_name(user: User, *role_names: str) -> bool:
    expected = {name.strip().casefold() for name in role_names if name.strip()}

    return any(
        _normalise_role(user_role).strip().casefold() in expected
        for user_role in user.roles
    )


def _is_head_of_year(user: User) -> bool:
    return _user_has_role_name(
        user,
        "head_of_year",
        "head of year",
        "hoy",
    )


def _is_headmaster(user: User) -> bool:
    return _user_has_role_name(
        user,
        "headmaster",
        "headteacher",
        "head_teacher",
        "principal",
    )


def _is_custom_report_writer(user: User) -> bool:
    """
    Recognise common pastoral and boarding report-writer roles.

    The report type configuration and repository remain responsible for
    deciding which custom report types each role may write and which pupils
    fall within that member of staff's scope.
    """

    return _user_has_role_name(
        user,
        "housemaster",
        "housemistress",
        "house_parent",
        "boarding_staff",
        "boarding staff",
        "pastoral_staff",
        "pastoral staff",
    )


def _is_school_staff(user: User) -> bool:
    return (
        any(
            _user_has_role(user, role)
            for role in (
                UserRole.SCHOOL_ADMIN,
                UserRole.TEACHER,
                UserRole.PLATFORM_ADMIN,
            )
        )
        or _is_head_of_year(user)
        or _is_headmaster(user)
        or _is_custom_report_writer(user)
    )


def _can_review_reports(user: User) -> bool:
    """
    Final SMT review and approval.

    School Admin currently represents school-level SMT. Platform Admin may
    also complete the final review. Headmasters may read, write, edit, save,
    print and download reports, but approval remains an SMT/Platform Admin
    action unless they also hold School Admin.
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


def _can_edit_any_school_report(user: User) -> bool:
    """
    Users who may edit and save any non-published report in their school.
    """

    return _can_review_reports(user) or _is_headmaster(user)


def _can_export_whole_school_or_session(user: User) -> bool:
    """
    Whole-session and whole-school downloads are restricted to the
    Headmaster, SMT/School Admin and Platform Admin.
    """

    return _can_edit_any_school_report(user)


def _can_attempt_tutor_review(user: User) -> bool:
    """
    Teachers may be tutors. Head-of-Year access is also admitted here, but
    the repository must verify the pupil is in a tutor group or year group
    under that user's leadership.
    """

    return (
        any(
            _user_has_role(user, role)
            for role in (
                UserRole.TEACHER,
                UserRole.SCHOOL_ADMIN,
                UserRole.PLATFORM_ADMIN,
            )
        )
        or _is_head_of_year(user)
        or _is_headmaster(user)
    )


def _require_school_staff(user: User) -> None:
    if not _is_school_staff(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only authorised school staff can access student reports.",
        )


def _require_report_reviewer(user: User) -> None:
    if not _can_review_reports(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only SMT/School Admin or Platform Admin can approve reports.",
        )


def _require_report_publisher(user: User) -> None:
    if not _can_publish_reports(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only SMT/School Admin or Platform Admin can publish reports.",
        )


def _require_batch_export_role(user: User) -> None:
    if not _can_export_whole_school_or_session(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "Only the Headmaster, SMT/School Admin or Platform Admin "
                "can download a complete reporting session."
            ),
        )


def _require_tutor_review_role(user: User) -> None:
    if not _can_attempt_tutor_review(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "Only tutors, Heads of Year, the Headmaster or school "
                "administrators can review reports."
            ),
        )


def _is_report_owner(*, user: User, report_teacher_id: int | None) -> bool:
    return report_teacher_id == user.id


def _require_teacher_report_ownership(
    *,
    user: User,
    report_teacher_id: int | None,
    action: str,
) -> None:
    """
    Require ownership for author-only actions such as submitting or deleting.

    Headmaster, School Admin and Platform Admin are not restricted by author
    ownership when performing school-wide administrative work.
    """

    if _can_edit_any_school_report(user):
        return

    if report_teacher_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"You can only {action} reports that you wrote.",
        )


async def _require_tutor_access_to_student(
    *,
    db: AsyncSession,
    user: User,
    school_id: int,
    student_id: int,
) -> None:
    """
    Check pupil-level pastoral access.

    Headmaster, School Admin and Platform Admin may access any pupil in their
    school. For tutors and Heads of Year, the repository must confirm that
    the pupil belongs to an assigned tutor group or year-group scope.
    """

    if _can_edit_any_school_report(user):
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
                "You can only review or edit reports for pupils within "
                "your assigned tutor-group or year-group responsibility."
            ),
        )


async def _require_non_published_report_edit_access(
    *,
    db: AsyncSession,
    user: User,
    school_id: int,
    report,
) -> None:
    """
    Enforce role and pupil scope for editing while keeping published reports
    locked.

    Authors may edit their own draft or returned reports. Tutors and Heads of
    Year may edit reports for pupils in their assigned scope. The Headmaster,
    School Admin and Platform Admin may edit any non-published report in the
    school.
    """

    if report.status == REPORT_STATUS_PUBLISHED or report.published:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Published reports cannot be edited.",
        )

    if _can_edit_any_school_report(user):
        return

    if _is_report_owner(user=user, report_teacher_id=report.teacher_id):
        if report.status not in {
            REPORT_STATUS_DRAFT,
            REPORT_STATUS_RETURNED_BY_TUTOR,
            REPORT_STATUS_RETURNED_BY_SMT,
        }:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "A report author can edit only a draft or a report "
                    "returned for correction."
                ),
            )

        return

    await _require_tutor_access_to_student(
        db=db,
        user=user,
        school_id=school_id,
        student_id=report.student_id,
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


def _display_name(value: object | None, *, fallback: str) -> str:
    """Return a human-readable name from a school or user model."""

    if value is None:
        return fallback

    for attribute in ("full_name", "display_name", "name"):
        candidate = getattr(value, attribute, None)

        if isinstance(candidate, str) and candidate.strip():
            return " ".join(candidate.strip().split())

    first_name = getattr(value, "first_name", None)
    last_name = getattr(value, "last_name", None)

    combined = " ".join(
        part.strip()
        for part in (first_name, last_name)
        if isinstance(part, str) and part.strip()
    )

    if combined:
        return combined

    email = getattr(value, "email", None)

    if isinstance(email, str) and email.strip():
        return email.strip()

    return fallback


async def _user_can_download_published_report(
    *,
    db: AsyncSession,
    user: User,
    report,
) -> bool:
    """
    Staff may download published reports from their school.

    Non-staff users may download a published report only when they are linked
    to the report pupil through the parent-student relationship.
    """

    if _is_school_staff(user):
        return True

    parent_repository = ParentStudentRepository(db)
    children = await parent_repository.list_children_for_parent(
        parent_id=user.id,
    )

    return any(child.student_id == report.student_id for child in children)


def _build_report_pdf_data(report) -> ReportPdfData:
    """Map a StudentReport model into the model-independent PDF structure."""

    exam_result = None

    if report.exam_mark is not None:
        exam_result = str(report.exam_mark)

        if report.exam_max_mark is not None:
            exam_result = f"{report.exam_mark}/{report.exam_max_mark}"

    fields = tuple(
        field
        for field in (
            ReportPdfField("Attainment grade", report.attainment_grade),
            ReportPdfField("Effort grade", report.effort_grade),
            ReportPdfField("Target grade", report.target_grade),
            ReportPdfField("Exam grade", report.exam_grade),
            ReportPdfField("Exam mark", exam_result),
            ReportPdfField("UCAS predicted grade", report.ucas_predicted_grade),
        )
        if field.value not in (None, "")
    )

    sections = tuple(
        section
        for section in (
            ReportPdfSection("Work Covered", report.work_covered or ""),
            ReportPdfSection("Next Steps", report.next_steps or ""),
            ReportPdfSection("Tutor Comment", report.tutor_comment or ""),
            ReportPdfSection(
                "Head of Year Comment",
                report.head_of_year_comment or "",
            ),
            ReportPdfSection(
                "Headteacher Comment",
                report.headteacher_comment or "",
            ),
        )
        if section.content.strip()
    )

    return ReportPdfData(
        school_name=_display_name(
            report.school,
            fallback="School Report",
        ),
        student_name=_display_name(
            report.student,
            fallback=f"Student {report.student_id}",
        ),
        report_title=report.title,
        academic_year=report.academic_year,
        term=report.checkpoint_name or report.term,
        subject=report.subject_name,
        teacher_name=(
            _display_name(
                report.teacher,
                fallback="",
            )
            if report.teacher is not None
            else None
        ),
        grade=report.grade,
        report_text=report.report_text,
        published_at=report.published_at,
        fields=fields,
        sections=sections,
        footer_text="Confidential student report",
    )


async def _get_reports_for_session_export(
    *,
    db: AsyncSession,
    school_id: int,
    report_session_id: int,
    export_status: str,
):
    """
    Return school-scoped reports for a reporting-session export.

    ``export_status`` may be ``draft``, ``published`` or ``all``. Draft
    export means every report that has not yet been published, including
    submitted, review and approved reports.
    """

    normalised_status = export_status.strip().casefold()

    if normalised_status not in {"draft", "published", "all"}:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Export status must be draft, published or all.",
        )

    reports = await list_student_reports(
        db,
        school_id=school_id,
        report_session_id=report_session_id,
    )

    if normalised_status == "published":
        return [
            report
            for report in reports
            if report.published and report.status == REPORT_STATUS_PUBLISHED
        ]

    if normalised_status == "draft":
        return [
            report
            for report in reports
            if not report.published and report.status != REPORT_STATUS_PUBLISHED
        ]

    return reports


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
            tutor_comment=getattr(payload, "tutor_comment", None),
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

    return StudentReportReviewDashboard(
        draft=counts.get("draft", 0),
        submitted=counts.get("submitted", 0),
        tutor_review=counts.get("tutor_review", 0),
        returned_by_tutor=counts.get("returned_by_tutor", 0),
        ready_for_smt=counts.get("ready_for_smt", 0),
        returned_by_smt=counts.get("returned_by_smt", 0),
        approved=counts.get("approved", 0),
        published=counts.get("published", 0),
    )


@router.patch(
    "/{report_id}/reviewer-edit",
    response_model=StudentReportRead,
)
async def reviewer_edit_report_endpoint(
    report_id: int,
    payload: StudentReportUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> StudentReportRead:
    """
    Allow SMT reviewers to correct a report directly without returning it.

    Saving corrections does not advance or reverse the workflow status.
    Published reports remain locked.
    """

    school_id = _require_school_id(current_user)
    _require_report_reviewer(current_user)

    report = await _get_report_or_404(
        db=db,
        report_id=report_id,
        school_id=school_id,
    )

    if report.status == REPORT_STATUS_PUBLISHED or report.published:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Published reports cannot be edited.",
        )

    editable_statuses = {
        REPORT_STATUS_DRAFT,
        REPORT_STATUS_RETURNED_BY_TUTOR,
        REPORT_STATUS_RETURNED_BY_SMT,
        REPORT_STATUS_SUBMITTED,
        REPORT_STATUS_TUTOR_REVIEW,
        REPORT_STATUS_READY_FOR_SMT,
        REPORT_STATUS_APPROVED,
    }

    if report.status not in editable_statuses:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This report is not in an editable workflow state.",
        )

    try:
        return await update_student_report_as_reviewer(
            db,
            report=report,
            payload=payload,
            reviewer_id=current_user.id,
            reviewer_role=(
                "platform_admin"
                if _user_has_role(current_user, UserRole.PLATFORM_ADMIN)
                else "school_admin"
            ),
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc


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


@router.get(
    "/export-session/{report_session_id}",
    response_class=StreamingResponse,
)
async def export_report_session_zip_endpoint(
    report_session_id: int,
    export_status: str = "published",
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> StreamingResponse:
    """
    Download a complete reporting session as a ZIP of pupil PDFs.

    The Headmaster, SMT/School Admin and Platform Admin may export draft,
    published or all reports. Each PDF includes the school name, pupil name,
    report title/type and the name of the staff member who wrote it.
    """

    school_id = _require_school_id(current_user)
    _require_batch_export_role(current_user)

    if report_session_id < 1:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Report session ID must be a positive integer.",
        )

    reports = await _get_reports_for_session_export(
        db=db,
        school_id=school_id,
        report_session_id=report_session_id,
        export_status=export_status,
    )

    if not reports:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                "No reports matching the requested export status were found "
                "for this reporting session."
            ),
        )

    zip_items = [
        ReportZipItem(
            report=_build_report_pdf_data(report),
        )
        for report in reports
    ]

    try:
        zip_bytes = generate_report_zip_bytes(zip_items)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="The report ZIP archive could not be generated.",
        ) from exc

    safe_export_status = export_status.strip().casefold()
    filename = (
        f"student_reports_session_{report_session_id}_" f"{safe_export_status}.zip"
    )

    return StreamingResponse(
        BytesIO(zip_bytes),
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Length": str(len(zip_bytes)),
            "Cache-Control": "private, no-store",
        },
    )


@router.get(
    "/{report_id}/pdf",
    response_class=StreamingResponse,
)
async def download_report_pdf_endpoint(
    report_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> StreamingResponse:
    """
    Download one student report as a print-ready PDF.

    Only published reports may be downloaded. Authorised staff may download
    published reports within their permitted pupil scope. Parents may download
    published reports only for linked children.
    """

    school_id = _require_school_id(current_user)

    report = await _get_report_or_404(
        db=db,
        report_id=report_id,
        school_id=school_id,
    )

    is_published = report.status == REPORT_STATUS_PUBLISHED and bool(report.published)

    if not is_published:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only published reports can be downloaded as PDF.",
        )

    if _is_school_staff(current_user):
        if not (
            _can_edit_any_school_report(current_user)
            or _is_report_owner(
                user=current_user,
                report_teacher_id=report.teacher_id,
            )
        ):
            await _require_tutor_access_to_student(
                db=db,
                user=current_user,
                school_id=school_id,
                student_id=report.student_id,
            )
    else:
        if not await _user_can_download_published_report(
            db=db,
            user=current_user,
            report=report,
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to download this report.",
            )

    pdf_data = _build_report_pdf_data(report)

    try:
        pdf_bytes = generate_report_pdf_bytes(pdf_data)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="The report PDF could not be generated.",
        ) from exc

    filename = build_report_pdf_filename(pdf_data)

    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Length": str(len(pdf_bytes)),
            "Cache-Control": "private, no-store",
        },
    )


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

    await _require_non_published_report_edit_access(
        db=db,
        user=current_user,
        school_id=school_id,
        report=report,
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
