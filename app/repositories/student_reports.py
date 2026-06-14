from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.student_report import StudentReport
from app.models.user import User
from app.schemas.student_report import StudentReportCreate, StudentReportUpdate


async def create_student_report(
    db: AsyncSession,
    *,
    school_id: int,
    teacher_id: int,
    payload: StudentReportCreate,
) -> StudentReport:
    report = StudentReport(
        school_id=school_id,
        student_id=payload.student_id,
        teacher_id=teacher_id,
        title=payload.title,
        report_text=payload.report_text,
        grade=payload.grade,
        academic_year=payload.academic_year,
        term=payload.term,
        published=False,
        published_at=None,
        published_by_id=None,
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

    statement = (
        statement.order_by(StudentReport.created_at.desc()).offset(offset).limit(limit)
    )

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

    if publishing_requested is True:
        report.published = True
        report.published_at = datetime.now(timezone.utc)

        if current_user is not None:
            report.published_by_id = current_user.id

    elif publishing_requested is False:
        report.published = False
        report.published_at = None
        report.published_by_id = None

    for key, value in update_data.items():
        setattr(report, key, value)

    await db.commit()
    await db.refresh(report)

    return report


async def delete_student_report(
    db: AsyncSession,
    *,
    report: StudentReport,
) -> None:
    await db.delete(report)
    await db.commit()
