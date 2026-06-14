from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.models.user_role import UserRole
from app.repositories.parent_student import ParentStudentRepository
from app.repositories.student_reports import (
    create_student_report,
    delete_student_report,
    get_student_report,
    list_reports_for_student,
    list_student_reports,
    update_student_report,
)
from app.schemas.student_report import (
    StudentReportCreate,
    StudentReportRead,
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


@router.get("/", response_model=list[StudentReportRead])
async def list_reports_endpoint(
    teacher_id: int | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[StudentReportRead]:
    school_id = _require_school_id(current_user)
    _require_school_staff(current_user)

    return await list_student_reports(
        db,
        school_id=school_id,
        teacher_id=teacher_id,
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
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[StudentReportRead]:
    school_id = _require_school_id(current_user)

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

    if getattr(payload, "published", None) is True and not _can_publish_reports(
        current_user,
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only school admins can publish student reports.",
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

    await delete_student_report(
        db,
        report=report,
    )
