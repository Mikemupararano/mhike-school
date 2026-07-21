from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.report_group_content import ReportGroupContent


async def get_report_group_content(
    db: AsyncSession,
    *,
    school_id: int,
    report_session_id: int,
    class_group_id: int,
    subject_name: str,
) -> ReportGroupContent | None:
    """
    Return the shared report content for one exact reporting scope.

    The scope is uniquely identified by:

    - school
    - report session
    - class group
    - subject
    """

    normalized_subject_name = subject_name.strip()

    result = await db.execute(
        select(ReportGroupContent).where(
            ReportGroupContent.school_id == school_id,
            ReportGroupContent.report_session_id == report_session_id,
            ReportGroupContent.class_group_id == class_group_id,
            ReportGroupContent.subject_name == normalized_subject_name,
        )
    )

    return result.scalar_one_or_none()


async def get_report_group_content_by_id(
    db: AsyncSession,
    *,
    school_id: int,
    content_id: int,
) -> ReportGroupContent | None:
    """
    Return one shared report content record by ID within the given school.

    The school filter prevents records from another school being accessed by
    guessing or supplying their database IDs.
    """

    result = await db.execute(
        select(ReportGroupContent).where(
            ReportGroupContent.id == content_id,
            ReportGroupContent.school_id == school_id,
        )
    )

    return result.scalar_one_or_none()


async def list_report_group_contents(
    db: AsyncSession,
    *,
    school_id: int,
    report_session_id: int | None = None,
    class_group_id: int | None = None,
    subject_name: str | None = None,
) -> list[ReportGroupContent]:
    """
    List shared report content records belonging to one school.

    Optional filters may narrow the results by reporting session, class group,
    or subject.
    """

    statement = select(ReportGroupContent).where(
        ReportGroupContent.school_id == school_id,
    )

    if report_session_id is not None:
        statement = statement.where(
            ReportGroupContent.report_session_id == report_session_id,
        )

    if class_group_id is not None:
        statement = statement.where(
            ReportGroupContent.class_group_id == class_group_id,
        )

    if subject_name is not None:
        statement = statement.where(
            ReportGroupContent.subject_name == subject_name.strip(),
        )

    statement = statement.order_by(
        ReportGroupContent.report_session_id,
        ReportGroupContent.class_group_id,
        ReportGroupContent.subject_name,
    )

    result = await db.execute(statement)

    return list(result.scalars().all())


async def upsert_report_group_content(
    db: AsyncSession,
    *,
    school_id: int,
    report_session_id: int,
    class_group_id: int,
    subject_name: str,
    work_covered: str,
    updated_by_id: int | None,
) -> ReportGroupContent:
    """
    Create or update shared content for one reporting scope.

    The database uniqueness constraint protects the combination of:

    - school_id
    - report_session_id
    - class_group_id
    - subject_name

    This function performs the application-level lookup first so repeated PUT
    requests update the existing record rather than creating duplicates.
    """

    normalized_subject_name = subject_name.strip()
    normalized_work_covered = work_covered.strip()

    record = await get_report_group_content(
        db,
        school_id=school_id,
        report_session_id=report_session_id,
        class_group_id=class_group_id,
        subject_name=normalized_subject_name,
    )

    if record is None:
        record = ReportGroupContent(
            school_id=school_id,
            report_session_id=report_session_id,
            class_group_id=class_group_id,
            subject_name=normalized_subject_name,
            work_covered=normalized_work_covered,
            updated_by_id=updated_by_id,
        )

        db.add(record)
    else:
        record.work_covered = normalized_work_covered
        record.updated_by_id = updated_by_id

    await db.flush()
    await db.refresh(record)

    return record


async def update_report_group_content(
    db: AsyncSession,
    *,
    record: ReportGroupContent,
    work_covered: str,
    updated_by_id: int | None,
) -> ReportGroupContent:
    """
    Update the editable shared-content fields on an existing record.

    The reporting scope itself is intentionally unchanged. A different subject,
    class group, or reporting session should use the upsert operation for that
    separate scope.
    """

    record.work_covered = work_covered.strip()
    record.updated_by_id = updated_by_id

    await db.flush()
    await db.refresh(record)

    return record


async def delete_report_group_content(
    db: AsyncSession,
    *,
    record: ReportGroupContent,
) -> None:
    """Delete an existing shared report content record."""

    await db.delete(record)
    await db.flush()