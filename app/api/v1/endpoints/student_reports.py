from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.models.user_role import UserRole
from app.repositories.parent_student import ParentStudentRepository
from app.repositories.student_reports import (
    REPORT_STATUS_DRAFT,
    REPORT_STATUS_SUBMITTED,
    approve_student_report,
    create_student_report,
    delete_student_report,
    get_student_report,
    get_student_report_dashboard_counts,
    list_reports_for_student,
    list_student_report_review_queue,
    list_student_reports,
    publish_reports_for_session,
    return_student_report,
    submit_student_report,
    update_student_report,
)
from app.schemas.student_report import (
    StudentReportCreate,
    StudentReportRead,
    StudentReportReviewDashboard,
    StudentReportReviewDecision,
    StudentReportUpdate,
)

router = APIRouter()


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
            detail="Only school admins can review student reports.",
        )


def _require_report_publisher(user: User) -> None:
    if not _can_publish_reports(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only school admins can publish student reports.",
        )


def _require_teacher_report_ownership(
    *,
    user: User,
    report_teacher_id: int | None,
    action: str,
) -> None:
    if _user_has_role(user, UserRole.TEACHER) and report_teacher_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Teachers can only {action} their own reports.",
        )


@router.get(
    "/",
    response_model=list[StudentReportRead],
)
async def list_reports_endpoint(
    teacher_id: int | None = None,
    report_session_id: int | None = None,
    published: bool | None = None,
    status: str | None = None,
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
        status=status,
    )


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
    "/student/{student_id}",
    response_model=list[StudentReportRead],
)
async def list_student_reports_endpoint(
    student_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[StudentReportRead]:
    school_id = _require_school_id(current_user)
    _require_school_staff(current_user)

    return await list_reports_for_student(
        db,
        school_id=school_id,
        student_id=student_id,
    )


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

    _require_teacher_report_ownership(
        user=current_user,
        report_teacher_id=report.teacher_id,
        action="submit",
    )

    if report.status != REPORT_STATUS_DRAFT:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only draft reports can be submitted for review.",
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

    if report.status != REPORT_STATUS_SUBMITTED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only submitted reports can be approved.",
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

    if report.status != REPORT_STATUS_SUBMITTED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only submitted reports can be returned for correction.",
        )

    try:
        return await return_student_report(
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

    _require_teacher_report_ownership(
        user=current_user,
        report_teacher_id=report.teacher_id,
        action="edit",
    )

    if report.status != REPORT_STATUS_DRAFT:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only draft reports can be edited.",
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
