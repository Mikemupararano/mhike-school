from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.student_report import StudentReport
from app.schemas.student_report import StudentReportCreate, StudentReportUpdate


async def create_student_report(
    db: AsyncSession,
    *,
    school_id: int,
    payload: StudentReportCreate,
) -> StudentReport:
    report = StudentReport(
        school_id=school_id,
        student_id=payload.student_id,
        teacher_id=payload.teacher_id,
        title=payload.title,
        report_text=payload.report_text,
        grade=payload.grade,
        academic_year=payload.academic_year,
        term=payload.term,
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
    limit: int = 100,
    offset: int = 0,
) -> list[StudentReport]:
    result = await db.execute(
        select(StudentReport)
        .where(StudentReport.school_id == school_id)
        .order_by(StudentReport.created_at.desc())
        .offset(offset)
        .limit(limit),
    )

    return list(result.scalars().all())


async def list_reports_for_student(
    db: AsyncSession,
    *,
    school_id: int,
    student_id: int,
) -> list[StudentReport]:
    result = await db.execute(
        select(StudentReport)
        .where(
            StudentReport.school_id == school_id,
            StudentReport.student_id == student_id,
        )
        .order_by(StudentReport.created_at.desc()),
    )

    return list(result.scalars().all())


async def update_student_report(
    db: AsyncSession,
    *,
    report: StudentReport,
    payload: StudentReportUpdate,
) -> StudentReport:
    update_data = payload.model_dump(exclude_unset=True)

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
