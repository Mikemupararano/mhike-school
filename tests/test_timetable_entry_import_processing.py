from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import date, time
from typing import Any

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
)

import app.tasks.imports as import_tasks
from app.imports.bootstrap import register_import_handlers
from app.imports.processors.timetable_entries import (
    process_timetable_entry_row,
)
from app.imports.registry import (
    RowProcessingAction,
    get_import_handler,
)
from app.imports.validators.timetable_entries import (
    validate_timetable_entry_row,
)
from app.models.course import Course
from app.models.import_batch import (
    ImportBatch,
    ImportOperation,
    ImportRow,
    ImportRowStatus,
    ImportStatus,
)
from app.models.timetable import Timetable
from app.models.timetable_entry import (
    TimetableDay,
    TimetableEntry,
)
from app.models.timetable_period import TimetablePeriod
from app.models.user import User
from app.repositories.course import CourseRepository
from app.repositories.timetable import TimetableRepository


def create_task_session_maker(
    db_session: AsyncSession,
) -> async_sessionmaker[AsyncSession]:
    if db_session.bind is None:
        raise AssertionError(
            "The test database session is not bound to an engine.",
        )

    return async_sessionmaker(
        bind=db_session.bind,
        class_=AsyncSession,
        expire_on_commit=False,
    )


def configure_task_session_maker(
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> async_sessionmaker[AsyncSession]:
    session_maker = create_task_session_maker(
        db_session,
    )

    monkeypatch.setattr(
        import_tasks,
        "AsyncSessionLocal",
        session_maker,
    )

    return session_maker


@asynccontextmanager
async def verification_session(
    session_maker: async_sessionmaker[AsyncSession],
) -> AsyncIterator[AsyncSession]:
    async with session_maker() as session:
        yield session


async def create_timetable_context(
    db_session: AsyncSession,
    *,
    school_id: int,
    timetable_name: str = "Main Timetable",
    academic_year: str = "2026/2027",
    period_number: int = 1,
) -> tuple[Timetable, TimetablePeriod]:
    timetable = Timetable(
        school_id=school_id,
        name=timetable_name,
        academic_year=academic_year,
        effective_from=date(2026, 9, 1),
        effective_to=date(2027, 7, 20),
        is_active=True,
    )

    period = TimetablePeriod(
        school_id=school_id,
        name=f"Period {period_number}",
        short_name=f"P{period_number}",
        period_number=period_number,
        start_time=time(9, 0),
        end_time=time(9, 50),
        is_registration=False,
        is_break=False,
        is_lunch=False,
        is_active=True,
    )

    db_session.add_all(
        [
            timetable,
            period,
        ],
    )

    await db_session.commit()
    await db_session.refresh(timetable)
    await db_session.refresh(period)

    return timetable, period


async def create_teacher_course(
    db_session: AsyncSession,
    *,
    school_id: int,
    teacher: User,
    title: str = "Physics",
) -> Course:
    course = Course(
        title=title,
        description="Imported timetable test course",
        teacher_id=teacher.id,
        school_id=school_id,
        published=True,
    )

    await CourseRepository(
        db_session,
    ).create(
        course,
    )

    await db_session.commit()
    await db_session.refresh(course)

    return course


async def get_batch_by_id(
    db: AsyncSession,
    batch_id: int,
) -> ImportBatch:
    result = await db.execute(
        select(ImportBatch).where(
            ImportBatch.id == batch_id,
        ),
    )

    return result.scalar_one()


async def get_row_by_id(
    db: AsyncSession,
    row_id: int,
) -> ImportRow:
    result = await db.execute(
        select(ImportRow).where(
            ImportRow.id == row_id,
        ),
    )

    return result.scalar_one()


async def get_entry_by_id(
    db: AsyncSession,
    entry_id: int,
) -> TimetableEntry:
    result = await db.execute(
        select(TimetableEntry).where(
            TimetableEntry.id == entry_id,
        ),
    )

    return result.scalar_one()


def build_timetable_entry_batch(
    *,
    school_id: int,
    uploaded_by_id: int,
    operation: ImportOperation = ImportOperation.UPSERT,
) -> ImportBatch:
    return ImportBatch(
        school_id=school_id,
        uploaded_by_id=uploaded_by_id,
        import_type="timetable_entries",
        operation=operation,
        status=ImportStatus.READY,
        original_filename="timetable-entries.csv",
        total_rows=1,
        validated_rows=1,
        processed_rows=0,
        successful_rows=0,
        warning_rows=0,
        failed_rows=0,
        skipped_rows=0,
        current_stage="ready",
    )


def build_timetable_entry_row(
    *,
    batch_id: int,
    school_id: int,
    data: dict[str, Any],
) -> ImportRow:
    return ImportRow(
        batch_id=batch_id,
        school_id=school_id,
        row_number=2,
        status=ImportRowStatus.VALID,
        original_data=dict(data),
        normalised_data=dict(data),
        validation_errors=[],
        validation_warnings=[],
        attempt_count=0,
    )


def test_timetable_entry_handler_is_registered() -> None:
    register_import_handlers()

    handler = get_import_handler(
        "timetable_entries",
    )

    assert handler.validator is validate_timetable_entry_row
    assert handler.processor is process_timetable_entry_row


def test_validate_timetable_entry_row_success() -> None:
    result = validate_timetable_entry_row(
        {
            "timetable_name": " Main Timetable ",
            "academic_year": " 2026/2027 ",
            "day_of_week": "monday",
            "period_number": 1,
            "teacher_email": "teacher@example.com",
            "room": " Lab 1 ",
            "title": " Physics ",
            "notes": " Bring goggles ",
            "source_system": "MIS",
        },
    )

    assert result.is_valid is True
    assert result.errors == []
    assert result.warnings == []

    assert result.normalised_data is not None
    assert result.normalised_data["timetable_name"] == "Main Timetable"
    assert result.normalised_data["academic_year"] == "2026/2027"
    assert result.normalised_data["day_of_week"] == "monday"
    assert result.normalised_data["period_number"] == 1
    assert result.normalised_data["room"] == "Lab 1"
    assert result.normalised_data["source_system"] == "MIS"


@pytest.mark.parametrize(
    "missing_field",
    [
        "timetable_name",
        "academic_year",
        "day_of_week",
        "period_number",
    ],
)
def test_validate_timetable_entry_requires_core_fields(
    missing_field: str,
) -> None:
    row = {
        "timetable_name": "Main Timetable",
        "academic_year": "2026/2027",
        "day_of_week": "monday",
        "period_number": 1,
        "teacher_email": "teacher@example.com",
    }

    row.pop(
        missing_field,
    )

    result = validate_timetable_entry_row(
        row,
    )

    assert result.is_valid is False
    assert result.normalised_data is None


def test_validate_timetable_entry_requires_teaching_context() -> None:
    result = validate_timetable_entry_row(
        {
            "timetable_name": "Main Timetable",
            "academic_year": "2026/2027",
            "day_of_week": "monday",
            "period_number": 1,
        },
    )

    assert result.is_valid is False
    assert result.normalised_data is None
    assert result.errors


def test_validate_timetable_entry_rejects_invalid_day() -> None:
    result = validate_timetable_entry_row(
        {
            "timetable_name": "Main Timetable",
            "academic_year": "2026/2027",
            "day_of_week": "holiday",
            "period_number": 1,
            "teacher_email": "teacher@example.com",
        },
    )

    assert result.is_valid is False
    assert result.normalised_data is None


def test_validate_timetable_entry_rejects_invalid_email() -> None:
    result = validate_timetable_entry_row(
        {
            "timetable_name": "Main Timetable",
            "academic_year": "2026/2027",
            "day_of_week": "monday",
            "period_number": 1,
            "teacher_email": "not-an-email",
        },
    )

    assert result.is_valid is False
    assert result.normalised_data is None


def test_validate_timetable_entry_rejects_long_fields() -> None:
    result = validate_timetable_entry_row(
        {
            "timetable_name": "A" * 151,
            "academic_year": "B" * 21,
            "day_of_week": "monday",
            "period_number": 1,
            "teacher_email": "teacher@example.com",
            "room": "C" * 101,
            "title": "D" * 201,
        },
    )

    assert result.is_valid is False
    assert result.normalised_data is None


@pytest.mark.asyncio
async def test_processor_creates_teacher_entry(
    db_session: AsyncSession,
    school_admin_user: User,
    teacher_user: User,
) -> None:
    school_id = school_admin_user.school_id

    assert school_id is not None
    assert teacher_user.school_id == school_id

    timetable, period = await create_timetable_context(
        db_session,
        school_id=school_id,
    )

    result = await process_timetable_entry_row(
        db_session,
        {
            "timetable_name": timetable.name,
            "academic_year": timetable.academic_year,
            "day_of_week": "monday",
            "period_number": period.period_number,
            "teacher_email": teacher_user.email.upper(),
            "room": " Lab 1 ",
            "title": " Physics ",
            "notes": " Bring goggles ",
        },
        school_id,
    )

    await db_session.commit()

    entry = await get_entry_by_id(
        db_session,
        result.entity_id,
    )

    assert result.action == RowProcessingAction.CREATED
    assert result.message == ("Created timetable entry for monday, period 1.")

    assert entry.school_id == school_id
    assert entry.timetable_id == timetable.id
    assert entry.timetable_period_id == period.id
    assert entry.teacher_id == teacher_user.id
    assert entry.class_group_id is None
    assert entry.course_id is None
    assert entry.day_of_week == TimetableDay.MONDAY
    assert entry.room == "Lab 1"
    assert entry.title == "Physics"
    assert entry.notes == "Bring goggles"


@pytest.mark.asyncio
async def test_processor_creates_teacher_course_entry(
    db_session: AsyncSession,
    school_admin_user: User,
    teacher_user: User,
) -> None:
    school_id = school_admin_user.school_id

    assert school_id is not None

    timetable, period = await create_timetable_context(
        db_session,
        school_id=school_id,
    )

    course = await create_teacher_course(
        db_session,
        school_id=school_id,
        teacher=teacher_user,
    )

    result = await process_timetable_entry_row(
        db_session,
        {
            "timetable_name": timetable.name,
            "academic_year": timetable.academic_year,
            "day_of_week": "tuesday",
            "period_number": period.period_number,
            "teacher_email": teacher_user.email,
            "course_title": course.title,
            "room": "Lab 2",
        },
        school_id,
    )

    await db_session.commit()

    entry = await get_entry_by_id(
        db_session,
        result.entity_id,
    )

    assert result.action == RowProcessingAction.CREATED
    assert entry.teacher_id == teacher_user.id
    assert entry.course_id == course.id
    assert entry.day_of_week == TimetableDay.TUESDAY
    assert entry.room == "Lab 2"


@pytest.mark.asyncio
async def test_processor_updates_matching_entry_details(
    db_session: AsyncSession,
    school_admin_user: User,
    teacher_user: User,
) -> None:
    school_id = school_admin_user.school_id

    assert school_id is not None

    timetable, period = await create_timetable_context(
        db_session,
        school_id=school_id,
    )

    existing_entry = TimetableEntry(
        timetable_id=timetable.id,
        school_id=school_id,
        class_group_id=None,
        course_id=None,
        teacher_id=teacher_user.id,
        timetable_period_id=period.id,
        day_of_week=TimetableDay.WEDNESDAY,
        room="Old Room",
        title="Old Title",
        notes="Old Notes",
    )

    db_session.add(
        existing_entry,
    )
    await db_session.commit()
    await db_session.refresh(
        existing_entry,
    )

    result = await process_timetable_entry_row(
        db_session,
        {
            "timetable_name": timetable.name,
            "academic_year": timetable.academic_year,
            "day_of_week": "wednesday",
            "period_number": period.period_number,
            "teacher_email": teacher_user.email,
            "room": "New Room",
            "title": "New Title",
            "notes": "New Notes",
        },
        school_id,
    )

    await db_session.commit()
    await db_session.refresh(
        existing_entry,
    )

    assert result.action == RowProcessingAction.UPDATED
    assert result.entity_id == existing_entry.id
    assert result.message == ("Updated timetable entry for wednesday, period 1.")

    assert existing_entry.room == "New Room"
    assert existing_entry.title == "New Title"
    assert existing_entry.notes == "New Notes"


@pytest.mark.asyncio
async def test_processor_rejects_invalid_school_id(
    db_session: AsyncSession,
) -> None:
    with pytest.raises(
        ValueError,
        match="school_id must be a positive integer",
    ):
        await process_timetable_entry_row(
            db_session,
            {
                "timetable_name": "Main Timetable",
                "academic_year": "2026/2027",
                "day_of_week": "monday",
                "period_number": 1,
                "teacher_email": "teacher@example.com",
            },
            0,
        )


@pytest.mark.asyncio
async def test_processor_rejects_missing_timetable(
    db_session: AsyncSession,
    school_admin_user: User,
) -> None:
    school_id = school_admin_user.school_id

    assert school_id is not None

    with pytest.raises(
        ValueError,
        match="No timetable named",
    ):
        await process_timetable_entry_row(
            db_session,
            {
                "timetable_name": "Missing",
                "academic_year": "2026/2027",
                "day_of_week": "monday",
                "period_number": 1,
                "teacher_email": "teacher@example.com",
            },
            school_id,
        )


@pytest.mark.asyncio
async def test_processor_rejects_missing_period(
    db_session: AsyncSession,
    school_admin_user: User,
    teacher_user: User,
) -> None:
    school_id = school_admin_user.school_id

    assert school_id is not None

    timetable, _ = await create_timetable_context(
        db_session,
        school_id=school_id,
    )

    with pytest.raises(
        ValueError,
        match="No timetable period numbered 999",
    ):
        await process_timetable_entry_row(
            db_session,
            {
                "timetable_name": timetable.name,
                "academic_year": timetable.academic_year,
                "day_of_week": "monday",
                "period_number": 999,
                "teacher_email": teacher_user.email,
            },
            school_id,
        )


@pytest.mark.asyncio
async def test_processor_rejects_missing_teacher(
    db_session: AsyncSession,
    school_admin_user: User,
) -> None:
    school_id = school_admin_user.school_id

    assert school_id is not None

    timetable, period = await create_timetable_context(
        db_session,
        school_id=school_id,
    )

    with pytest.raises(
        ValueError,
        match="No teacher with email",
    ):
        await process_timetable_entry_row(
            db_session,
            {
                "timetable_name": timetable.name,
                "academic_year": timetable.academic_year,
                "day_of_week": "monday",
                "period_number": period.period_number,
                "teacher_email": "missing@example.com",
            },
            school_id,
        )


@pytest.mark.asyncio
async def test_processor_rejects_non_teacher_user(
    db_session: AsyncSession,
    school_admin_user: User,
    student_user: User,
) -> None:
    school_id = school_admin_user.school_id

    assert school_id is not None

    timetable, period = await create_timetable_context(
        db_session,
        school_id=school_id,
    )

    with pytest.raises(
        ValueError,
        match="is not registered as a teacher",
    ):
        await process_timetable_entry_row(
            db_session,
            {
                "timetable_name": timetable.name,
                "academic_year": timetable.academic_year,
                "day_of_week": "monday",
                "period_number": period.period_number,
                "teacher_email": student_user.email,
            },
            school_id,
        )


@pytest.mark.asyncio
async def test_processor_rejects_missing_course(
    db_session: AsyncSession,
    school_admin_user: User,
) -> None:
    school_id = school_admin_user.school_id

    assert school_id is not None

    timetable, period = await create_timetable_context(
        db_session,
        school_id=school_id,
    )

    with pytest.raises(
        ValueError,
        match="No course titled",
    ):
        await process_timetable_entry_row(
            db_session,
            {
                "timetable_name": timetable.name,
                "academic_year": timetable.academic_year,
                "day_of_week": "monday",
                "period_number": period.period_number,
                "course_title": "Unknown Course",
            },
            school_id,
        )


@pytest.mark.asyncio
async def test_processor_rejects_missing_class(
    db_session: AsyncSession,
    school_admin_user: User,
) -> None:
    school_id = school_admin_user.school_id

    assert school_id is not None

    timetable, period = await create_timetable_context(
        db_session,
        school_id=school_id,
    )

    with pytest.raises(
        ValueError,
        match="No class named",
    ):
        await process_timetable_entry_row(
            db_session,
            {
                "timetable_name": timetable.name,
                "academic_year": timetable.academic_year,
                "day_of_week": "monday",
                "period_number": period.period_number,
                "class_name": "Unknown Class",
            },
            school_id,
        )


@pytest.mark.asyncio
async def test_repository_finds_matching_entry(
    db_session: AsyncSession,
    school_admin_user: User,
    teacher_user: User,
) -> None:
    school_id = school_admin_user.school_id

    assert school_id is not None

    timetable, period = await create_timetable_context(
        db_session,
        school_id=school_id,
    )

    entry = TimetableEntry(
        timetable_id=timetable.id,
        school_id=school_id,
        class_group_id=None,
        course_id=None,
        teacher_id=teacher_user.id,
        timetable_period_id=period.id,
        day_of_week=TimetableDay.THURSDAY,
        room="Lab 3",
        title="Physics",
        notes=None,
    )

    db_session.add(
        entry,
    )
    await db_session.commit()
    await db_session.refresh(
        entry,
    )

    matching_entry = await TimetableRepository(
        db_session,
    ).find_matching_entry(
        school_id=school_id,
        timetable_id=timetable.id,
        timetable_period_id=period.id,
        day_of_week=TimetableDay.THURSDAY,
        class_group_id=None,
        course_id=None,
        teacher_id=teacher_user.id,
    )

    assert matching_entry is not None
    assert matching_entry.id == entry.id


@pytest.mark.asyncio
async def test_processing_task_creates_timetable_entry(
    db_session: AsyncSession,
    school_admin_user: User,
    teacher_user: User,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    register_import_handlers()

    school_id = school_admin_user.school_id

    assert school_id is not None

    timetable, period = await create_timetable_context(
        db_session,
        school_id=school_id,
    )

    task_session_maker = configure_task_session_maker(
        db_session,
        monkeypatch,
    )

    batch = build_timetable_entry_batch(
        school_id=school_id,
        uploaded_by_id=school_admin_user.id,
        operation=ImportOperation.CREATE,
    )

    db_session.add(
        batch,
    )
    await db_session.flush()

    row = build_timetable_entry_row(
        batch_id=batch.id,
        school_id=school_id,
        data={
            "timetable_name": timetable.name,
            "academic_year": timetable.academic_year,
            "day_of_week": "friday",
            "period_number": period.period_number,
            "teacher_email": teacher_user.email,
            "room": "Lab 4",
            "title": "Friday Physics",
            "notes": "Imported",
        },
    )

    db_session.add(
        row,
    )
    await db_session.commit()

    batch_id = batch.id
    row_id = row.id

    summary = await import_tasks._process_import_batch_task(
        batch_id=batch_id,
        school_id=school_id,
    )

    async with verification_session(
        task_session_maker,
    ) as verification_db:
        processed_batch = await get_batch_by_id(
            verification_db,
            batch_id,
        )

        processed_row = await get_row_by_id(
            verification_db,
            row_id,
        )

        assert summary["status"] == ImportStatus.COMPLETED.value
        assert summary["processed_rows"] == 1
        assert summary["successful_rows"] == 1
        assert summary["imported_rows"] == 1
        assert summary["updated_rows"] == 0
        assert summary["failed_rows"] == 0

        assert processed_batch.status == ImportStatus.COMPLETED
        assert processed_batch.successful_rows == 1
        assert processed_batch.failed_rows == 0

        assert processed_row.status == ImportRowStatus.IMPORTED
        assert processed_row.attempt_count == 1
        assert processed_row.entity_type == "timetable_entries"
        assert processed_row.created_entity_id is not None
        assert processed_row.processed_at is not None
        assert processed_row.error_message is not None
        assert "Created timetable entry" in processed_row.error_message

        created_entry = await get_entry_by_id(
            verification_db,
            processed_row.created_entity_id,
        )

        assert created_entry.teacher_id == teacher_user.id
        assert created_entry.day_of_week == TimetableDay.FRIDAY
        assert created_entry.room == "Lab 4"


@pytest.mark.asyncio
async def test_processing_task_updates_existing_timetable_entry(
    db_session: AsyncSession,
    school_admin_user: User,
    teacher_user: User,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    register_import_handlers()

    school_id = school_admin_user.school_id

    assert school_id is not None

    timetable, period = await create_timetable_context(
        db_session,
        school_id=school_id,
    )

    entry = TimetableEntry(
        timetable_id=timetable.id,
        school_id=school_id,
        class_group_id=None,
        course_id=None,
        teacher_id=teacher_user.id,
        timetable_period_id=period.id,
        day_of_week=TimetableDay.SATURDAY,
        room="Old Room",
        title="Old Title",
        notes="Old Notes",
    )

    db_session.add(
        entry,
    )
    await db_session.commit()
    await db_session.refresh(
        entry,
    )

    entry_id = entry.id

    task_session_maker = configure_task_session_maker(
        db_session,
        monkeypatch,
    )

    batch = build_timetable_entry_batch(
        school_id=school_id,
        uploaded_by_id=school_admin_user.id,
        operation=ImportOperation.UPSERT,
    )

    db_session.add(
        batch,
    )
    await db_session.flush()

    row = build_timetable_entry_row(
        batch_id=batch.id,
        school_id=school_id,
        data={
            "timetable_name": timetable.name,
            "academic_year": timetable.academic_year,
            "day_of_week": "saturday",
            "period_number": period.period_number,
            "teacher_email": teacher_user.email,
            "room": "Updated Room",
            "title": "Updated Title",
            "notes": "Updated Notes",
        },
    )

    db_session.add(
        row,
    )
    await db_session.commit()

    batch_id = batch.id
    row_id = row.id

    summary = await import_tasks._process_import_batch_task(
        batch_id=batch_id,
        school_id=school_id,
    )

    async with verification_session(
        task_session_maker,
    ) as verification_db:
        processed_row = await get_row_by_id(
            verification_db,
            row_id,
        )

        updated_entry = await get_entry_by_id(
            verification_db,
            entry_id,
        )

        assert summary["status"] == ImportStatus.COMPLETED.value
        assert summary["successful_rows"] == 1
        assert summary["imported_rows"] == 0
        assert summary["updated_rows"] == 1
        assert summary["failed_rows"] == 0

        assert processed_row.status == ImportRowStatus.UPDATED
        assert processed_row.created_entity_id == entry_id
        assert processed_row.error_message is not None
        assert "Updated timetable entry" in processed_row.error_message

        assert updated_entry.room == "Updated Room"
        assert updated_entry.title == "Updated Title"
        assert updated_entry.notes == "Updated Notes"


@pytest.mark.asyncio
async def test_timetable_entry_processing_enforces_school_isolation(
    db_session: AsyncSession,
    school_admin_user: User,
    teacher_user: User,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    school_id = school_admin_user.school_id

    assert school_id is not None

    timetable, period = await create_timetable_context(
        db_session,
        school_id=school_id,
    )

    configure_task_session_maker(
        db_session,
        monkeypatch,
    )

    batch = build_timetable_entry_batch(
        school_id=school_id,
        uploaded_by_id=school_admin_user.id,
    )

    db_session.add(
        batch,
    )
    await db_session.flush()

    row = build_timetable_entry_row(
        batch_id=batch.id,
        school_id=school_id,
        data={
            "timetable_name": timetable.name,
            "academic_year": timetable.academic_year,
            "day_of_week": "sunday",
            "period_number": period.period_number,
            "teacher_email": teacher_user.email,
        },
    )

    db_session.add(
        row,
    )
    await db_session.commit()

    wrong_school_id = school_id + 999

    with pytest.raises(
        import_tasks.ImportBatchNotFoundError,
        match=(
            rf"Import batch {batch.id} was not found " rf"for school {wrong_school_id}"
        ),
    ):
        await import_tasks._process_import_batch_task(
            batch_id=batch.id,
            school_id=wrong_school_id,
        )

    await db_session.refresh(
        batch,
    )
    await db_session.refresh(
        row,
    )

    assert batch.status == ImportStatus.READY
    assert batch.processed_rows == 0
    assert batch.successful_rows == 0
    assert batch.failed_rows == 0

    assert row.status == ImportRowStatus.VALID
    assert row.attempt_count == 0
    assert row.created_entity_id is None
    assert row.processed_at is None

    matching_entry = await TimetableRepository(
        db_session,
    ).find_matching_entry(
        school_id=school_id,
        timetable_id=timetable.id,
        timetable_period_id=period.id,
        day_of_week=TimetableDay.SUNDAY,
        class_group_id=None,
        course_id=None,
        teacher_id=teacher_user.id,
    )

    assert matching_entry is None
