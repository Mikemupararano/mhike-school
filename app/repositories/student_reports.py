from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.student_report import StudentReport
from app.models.user import User
from app.schemas.report_memory import ReportMemoryCreate
from app.schemas.student_report import StudentReportCreate, StudentReportUpdate
from app.services.report_memory import create_report_memory

REPORT_STATUS_DRAFT = "draft"
REPORT_STATUS_SUBMITTED = "submitted"
REPORT_STATUS_APPROVED = "approved"
REPORT_STATUS_PUBLISHED = "published"


async def create_student_report(
    db: AsyncSession,
    *,
    school_id: int,
    teacher_id: int,
    payload: StudentReportCreate,
) -> StudentReport:
    existing_result = await db.execute(
        select(StudentReport).where(
            StudentReport.school_id == school_id,
            StudentReport.student_id == payload.student_id,
            StudentReport.report_session_id == payload.report_session_id,
            StudentReport.teacher_id == teacher_id,
        ),
    )

    existing_report = existing_result.scalar_one_or_none()

    if existing_report is not None:
        existing_report.title = payload.title
        existing_report.report_text = payload.report_text
        existing_report.grade = payload.grade
        existing_report.work_covered = payload.work_covered
        existing_report.teacher_notes = payload.teacher_notes
        existing_report.generated_report_text = payload.generated_report_text
        existing_report.academic_year = payload.academic_year
        existing_report.term = payload.term

        if existing_report.status == REPORT_STATUS_PUBLISHED:
            existing_report.status = REPORT_STATUS_DRAFT
            existing_report.published = False
            existing_report.published_at = None
            existing_report.published_by_id = None

        await db.commit()
        await db.refresh(existing_report)

        return existing_report

    report = StudentReport(
        school_id=school_id,
        student_id=payload.student_id,
        teacher_id=teacher_id,
        report_session_id=payload.report_session_id,
        title=payload.title,
        report_text=payload.report_text,
        grade=payload.grade,
        work_covered=payload.work_covered,
        teacher_notes=payload.teacher_notes,
        generated_report_text=payload.generated_report_text,
        academic_year=payload.academic_year,
        term=payload.term,
        status=REPORT_STATUS_DRAFT,
        published=False,
        published_at=None,
        published_by_id=None,
        reviewed_at=None,
        reviewed_by_id=None,
    )

    db.add(report)
    await db.commit()
    await db.refresh(report)

    return report


async def get_student_report(
    db: AsyncSession,
    *,
    report_id: int,
    school_id: int,
) -> StudentReport | None:
    result = await db.execute(
        select(StudentReport).where(
            StudentReport.id == report_id,
            StudentReport.school_id == school_id,
        ),
    )

    return result.scalar_one_or_none()


async def list_student_reports(
    db: AsyncSession,
    *,
    school_id: int,
    teacher_id: int | None = None,
    report_session_id: int | None = None,
    published: bool | None = None,
    status: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[StudentReport]:
    statement = select(StudentReport).where(
        StudentReport.school_id == school_id,
    )

    if teacher_id is not None:
        statement = statement.where(
            StudentReport.teacher_id == teacher_id,
        )

    if report_session_id is not None:
        statement = statement.where(
            StudentReport.report_session_id == report_session_id,
        )

    if published is not None:
        statement = statement.where(
            StudentReport.published.is_(published),
        )

    if status is not None:
        statement = statement.where(
            StudentReport.status == status,
        )

    statement = statement.order_by(StudentReport.created_at.desc())
    statement = statement.offset(offset).limit(limit)

    result = await db.execute(statement)

    return list(result.scalars().all())


async def list_reports_for_student(
    db: AsyncSession,
    *,
    school_id: int,
    student_id: int,
    published_only: bool = False,
) -> list[StudentReport]:
    statement = select(StudentReport).where(
        StudentReport.school_id == school_id,
        StudentReport.student_id == student_id,
    )

    if published_only:
        statement = statement.where(
            StudentReport.published.is_(True),
        )

    statement = statement.order_by(
        StudentReport.created_at.desc(),
    )

    result = await db.execute(statement)

    return list(result.scalars().all())


def _get_user_display_name(user: User | None) -> str | None:
    if user is None:
        return None

    full_name = getattr(user, "full_name", None)

    if isinstance(full_name, str) and full_name.strip():
        return full_name.strip()

    email = getattr(user, "email", None)

    if isinstance(email, str) and email.strip():
        return email.strip()

    return None


def _apply_status_change(
    report: StudentReport,
    *,
    status: str,
    current_user: User | None,
) -> None:
    now = datetime.now(timezone.utc)

    report.status = status

    if status == REPORT_STATUS_DRAFT:
        report.reviewed_at = None
        report.reviewed_by_id = None
        report.published = False
        report.published_at = None
        report.published_by_id = None

    elif status == REPORT_STATUS_SUBMITTED:
        report.reviewed_at = None
        report.reviewed_by_id = None
        report.published = False
        report.published_at = None
        report.published_by_id = None

    elif status == REPORT_STATUS_APPROVED:
        report.reviewed_at = now

        if current_user is not None:
            report.reviewed_by_id = current_user.id

        report.published = False
        report.published_at = None
        report.published_by_id = None

    elif status == REPORT_STATUS_PUBLISHED:
        report.published = True
        report.published_at = now

        if current_user is not None:
            report.published_by_id = current_user.id


async def _get_teacher_for_report(
    db: AsyncSession,
    report: StudentReport,
) -> User | None:
    if report.teacher_id is None:
        return None

    result = await db.execute(
        select(User).where(
            User.id == report.teacher_id,
            User.school_id == report.school_id,
        ),
    )

    return result.scalar_one_or_none()


async def _store_report_memory_for_published_report(
    db: AsyncSession,
    *,
    report: StudentReport,
) -> None:
    if not report.published:
        return

    if not report.report_text or not report.report_text.strip():
        return

    teacher = await _get_teacher_for_report(
        db,
        report,
    )

    await create_report_memory(
        db,
        ReportMemoryCreate(
            school_id=report.school_id,
            teacher_id=report.teacher_id,
            teacher_name=_get_user_display_name(teacher),
            subject=report.title or "General",
            year_group=report.academic_year,
            topics_studied=report.work_covered,
            teacher_notes=report.teacher_notes,
            generated_report=report.generated_report_text,
            final_report=report.report_text.strip(),
            source_report_id=report.id,
        ),
    )


async def update_student_report(
    db: AsyncSession,
    *,
    report: StudentReport,
    payload: StudentReportUpdate,
    current_user: User | None = None,
) -> StudentReport:
    update_data = payload.model_dump(exclude_unset=True)

    publishing_requested = update_data.pop(
        "published",
        None,
    )

    requested_status = update_data.pop(
        "status",
        None,
    )

    if publishing_requested is True:
        _apply_status_change(
            report,
            status=REPORT_STATUS_PUBLISHED,
            current_user=current_user,
        )

    elif publishing_requested is False:
        _apply_status_change(
            report,
            status=REPORT_STATUS_DRAFT,
            current_user=current_user,
        )

    if requested_status is not None:
        _apply_status_change(
            report,
            status=requested_status,
            current_user=current_user,
        )

    for key, value in update_data.items():
        setattr(report, key, value)

    await db.commit()
    await db.refresh(report)

    if report.published:
        await _store_report_memory_for_published_report(
            db,
            report=report,
        )

    return report


async def publish_reports_for_session(
    db: AsyncSession,
    *,
    school_id: int,
    report_session_id: int,
    published_by_id: int,
) -> int:
    result = await db.execute(
        select(StudentReport).where(
            StudentReport.school_id == school_id,
            StudentReport.report_session_id == report_session_id,
            StudentReport.published.is_(False),
            StudentReport.status == REPORT_STATUS_APPROVED,
        ),
    )

    reports = list(result.scalars().all())
    published_at = datetime.now(timezone.utc)

    for report in reports:
        report.status = REPORT_STATUS_PUBLISHED
        report.published = True
        report.published_at = published_at
        report.published_by_id = published_by_id

    await db.commit()

    for report in reports:
        await _store_report_memory_for_published_report(
            db,
            report=report,
        )

    return len(reports)


async def delete_student_report(
    db: AsyncSession,
    *,
    report: StudentReport,
) -> None:
    await db.delete(report)
    await db.commit()
