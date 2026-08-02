from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import time
from typing import Any

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
)

import app.tasks.imports as import_tasks
from app.imports.bootstrap import register_import_handlers
from app.imports.processors.timetable_periods import (
    process_timetable_period_row,
)
from app.imports.registry import (
    RowProcessingAction,
    get_import_handler,
)
from app.imports.validators.timetable_periods import (
    validate_timetable_period_row,
)
from app.models.import_batch import (
    ImportBatch,
    ImportOperation,
    ImportRow,
    ImportRowStatus,
    ImportStatus,
)
from app.models.timetable_period import TimetablePeriod
from app.models.user import User
from app.repositories.timetable import TimetableRepository


def create_task_session_maker(
    db_session: AsyncSession,
) -> async_sessionmaker[AsyncSession]:
    """
    Create a background-task-compatible session maker bound to the test
    database.
    """

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
    """
    Configure import background tasks to use the current test database.
    """

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
    """
    Open a fresh session for checking committed background-task results.
    """

    async with session_maker() as session:
        yield session


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


async def get_period_by_id(
    db: AsyncSession,
    period_id: int,
) -> TimetablePeriod:
    result = await db.execute(
        select(TimetablePeriod).where(
            TimetablePeriod.id == period_id,
        ),
    )

    return result.scalar_one()


def build_timetable_period_batch(
    *,
    school_id: int,
    uploaded_by_id: int,
    operation: ImportOperation = ImportOperation.UPSERT,
    total_rows: int = 1,
) -> ImportBatch:
    """
    Build a ready timetable-period import batch.
    """

    return ImportBatch(
        school_id=school_id,
        uploaded_by_id=uploaded_by_id,
        import_type="timetable_periods",
        operation=operation,
        status=ImportStatus.READY,
        original_filename="timetable-periods.csv",
        total_rows=total_rows,
        validated_rows=total_rows,
        processed_rows=0,
        successful_rows=0,
        warning_rows=0,
        failed_rows=0,
        skipped_rows=0,
        current_stage="ready",
    )


def build_timetable_period_row(
    *,
    batch_id: int,
    school_id: int,
    row_number: int,
    data: dict[str, Any],
    status: ImportRowStatus = ImportRowStatus.VALID,
    validation_errors: list[dict[str, Any]] | None = None,
) -> ImportRow:
    """
    Build one staged timetable-period import row.
    """

    return ImportRow(
        batch_id=batch_id,
        school_id=school_id,
        row_number=row_number,
        status=status,
        original_data=dict(data),
        normalised_data=({} if status == ImportRowStatus.INVALID else dict(data)),
        validation_errors=validation_errors or [],
        validation_warnings=[],
        attempt_count=0,
    )


def test_timetable_period_handler_is_registered() -> None:
    register_import_handlers()

    handler = get_import_handler(
        "timetable_periods",
    )

    assert handler.validator is validate_timetable_period_row
    assert handler.processor is process_timetable_period_row


def test_timetable_period_validator_accepts_valid_row() -> None:
    result = validate_timetable_period_row(
        {
            "name": " Period 1 ",
            "short_name": " P1 ",
            "period_number": 1,
            "start_time": "09:00",
            "end_time": "09:50",
            "is_registration": False,
            "is_break": False,
            "is_lunch": False,
            "is_active": True,
            "department": "Science",
        },
    )

    assert result.is_valid is True
    assert result.errors == []
    assert result.warnings == []

    assert result.normalised_data is not None
    assert result.normalised_data["name"] == "Period 1"
    assert result.normalised_data["short_name"] == "P1"
    assert result.normalised_data["period_number"] == 1
    assert result.normalised_data["start_time"] == "09:00:00"
    assert result.normalised_data["end_time"] == "09:50:00"
    assert result.normalised_data["is_active"] is True

    # Additional fields are retained for future import expansion.
    assert result.normalised_data["department"] == "Science"


def test_timetable_period_validator_applies_default_flags() -> None:
    result = validate_timetable_period_row(
        {
            "name": "Period 2",
            "short_name": "P2",
            "period_number": 2,
            "start_time": "09:50",
            "end_time": "10:40",
        },
    )

    assert result.is_valid is True
    assert result.normalised_data is not None

    assert result.normalised_data["is_registration"] is False
    assert result.normalised_data["is_break"] is False
    assert result.normalised_data["is_lunch"] is False
    assert result.normalised_data["is_active"] is True


def test_timetable_period_validator_accepts_break_period() -> None:
    result = validate_timetable_period_row(
        {
            "name": "Morning Break",
            "short_name": "BRK",
            "period_number": 3,
            "start_time": "10:40",
            "end_time": "11:00",
            "is_break": True,
        },
    )

    assert result.is_valid is True
    assert result.normalised_data is not None
    assert result.normalised_data["is_break"] is True


def test_timetable_period_validator_rejects_invalid_time_range() -> None:
    result = validate_timetable_period_row(
        {
            "name": "Invalid Period",
            "short_name": "INV",
            "period_number": 1,
            "start_time": "10:00",
            "end_time": "09:00",
        },
    )

    assert result.is_valid is False
    assert result.normalised_data is None
    assert result.errors


def test_timetable_period_validator_rejects_equal_times() -> None:
    result = validate_timetable_period_row(
        {
            "name": "Zero-Length Period",
            "short_name": "ZERO",
            "period_number": 1,
            "start_time": "10:00",
            "end_time": "10:00",
        },
    )

    assert result.is_valid is False
    assert result.normalised_data is None
    assert result.errors


def test_timetable_period_validator_rejects_invalid_fields() -> None:
    result = validate_timetable_period_row(
        {
            "name": "",
            "short_name": "",
            "period_number": 0,
            "start_time": "not-a-time",
            "end_time": "also-not-a-time",
        },
    )

    assert result.is_valid is False
    assert result.normalised_data is None

    error_locations = {tuple(error["loc"]) for error in result.errors}

    assert ("name",) in error_locations
    assert ("short_name",) in error_locations
    assert ("period_number",) in error_locations
    assert ("start_time",) in error_locations
    assert ("end_time",) in error_locations


def test_timetable_period_validator_rejects_long_names() -> None:
    result = validate_timetable_period_row(
        {
            "name": "A" * 101,
            "short_name": "B" * 21,
            "period_number": 1,
            "start_time": "09:00",
            "end_time": "09:50",
        },
    )

    assert result.is_valid is False
    assert result.normalised_data is None

    error_locations = {tuple(error["loc"]) for error in result.errors}

    assert ("name",) in error_locations
    assert ("short_name",) in error_locations


@pytest.mark.asyncio
async def test_processor_creates_timetable_period(
    db_session: AsyncSession,
    school_admin_user: User,
) -> None:
    school_id = school_admin_user.school_id

    assert school_id is not None

    result = await process_timetable_period_row(
        db_session,
        {
            "name": " Period 1 ",
            "short_name": " P1 ",
            "period_number": 1,
            "start_time": time(9, 0),
            "end_time": time(9, 50),
            "is_registration": False,
            "is_break": False,
            "is_lunch": False,
            "is_active": True,
        },
        school_id,
    )

    await db_session.commit()

    period = await TimetableRepository(
        db_session,
    ).get_period_by_number(
        school_id=school_id,
        period_number=1,
    )

    assert result.action == RowProcessingAction.CREATED
    assert result.entity_id is not None
    assert result.message == "Created timetable period 'Period 1' (P1)."

    assert period is not None
    assert period.id == result.entity_id
    assert period.school_id == school_id
    assert period.name == "Period 1"
    assert period.short_name == "P1"
    assert period.period_number == 1
    assert period.start_time == time(9, 0)
    assert period.end_time == time(9, 50)
    assert period.is_registration is False
    assert period.is_break is False
    assert period.is_lunch is False
    assert period.is_active is True


@pytest.mark.asyncio
async def test_processor_updates_existing_period_by_number(
    db_session: AsyncSession,
    school_admin_user: User,
) -> None:
    school_id = school_admin_user.school_id

    assert school_id is not None

    period = TimetablePeriod(
        school_id=school_id,
        name="Old Period",
        short_name="OLD",
        period_number=2,
        start_time=time(9, 50),
        end_time=time(10, 40),
        is_registration=False,
        is_break=False,
        is_lunch=False,
        is_active=True,
    )

    db_session.add(period)
    await db_session.commit()
    await db_session.refresh(period)

    period_id = period.id

    result = await process_timetable_period_row(
        db_session,
        {
            "name": "Updated Period 2",
            "short_name": "P2",
            "period_number": 2,
            "start_time": time(9, 55),
            "end_time": time(10, 45),
            "is_registration": False,
            "is_break": False,
            "is_lunch": False,
            "is_active": False,
        },
        school_id,
    )

    await db_session.commit()
    await db_session.refresh(period)

    assert result.action == RowProcessingAction.UPDATED
    assert result.entity_id == period_id
    assert result.message == ("Updated timetable period 'Updated Period 2' (P2).")

    assert period.id == period_id
    assert period.name == "Updated Period 2"
    assert period.short_name == "P2"
    assert period.start_time == time(9, 55)
    assert period.end_time == time(10, 45)
    assert period.is_active is False


@pytest.mark.asyncio
async def test_processor_creates_registration_period(
    db_session: AsyncSession,
    school_admin_user: User,
) -> None:
    school_id = school_admin_user.school_id

    assert school_id is not None

    result = await process_timetable_period_row(
        db_session,
        {
            "name": "Registration",
            "short_name": "REG",
            "period_number": 1,
            "start_time": time(8, 30),
            "end_time": time(8, 50),
            "is_registration": True,
        },
        school_id,
    )

    await db_session.commit()

    period = await TimetableRepository(
        db_session,
    ).get_period_by_number(
        school_id=school_id,
        period_number=1,
    )

    assert result.action == RowProcessingAction.CREATED
    assert period is not None
    assert period.is_registration is True
    assert period.is_break is False
    assert period.is_lunch is False


@pytest.mark.asyncio
async def test_processor_rejects_duplicate_short_name(
    db_session: AsyncSession,
    school_admin_user: User,
) -> None:
    school_id = school_admin_user.school_id

    assert school_id is not None

    existing_period = TimetablePeriod(
        school_id=school_id,
        name="Existing Period",
        short_name="P1",
        period_number=1,
        start_time=time(9, 0),
        end_time=time(9, 50),
        is_registration=False,
        is_break=False,
        is_lunch=False,
        is_active=True,
    )

    db_session.add(existing_period)
    await db_session.commit()

    with pytest.raises(
        ValueError,
        match="Another timetable period with short name",
    ):
        await process_timetable_period_row(
            db_session,
            {
                "name": "Different Period",
                "short_name": "P1",
                "period_number": 2,
                "start_time": time(9, 50),
                "end_time": time(10, 40),
            },
            school_id,
        )


@pytest.mark.parametrize(
    "school_id",
    [
        0,
        -1,
        -999,
    ],
)
@pytest.mark.asyncio
async def test_processor_rejects_invalid_school_id(
    db_session: AsyncSession,
    school_id: int,
) -> None:
    with pytest.raises(
        ValueError,
        match="school_id must be a positive integer",
    ):
        await process_timetable_period_row(
            db_session,
            {
                "name": "Period 1",
                "short_name": "P1",
                "period_number": 1,
                "start_time": time(9, 0),
                "end_time": time(9, 50),
            },
            school_id,
        )


@pytest.mark.parametrize(
    (
        "row",
        "expected_message",
    ),
    [
        (
            {
                "short_name": "P1",
                "period_number": 1,
                "start_time": time(9, 0),
                "end_time": time(9, 50),
            },
            "Timetable period import field 'name' is required.",
        ),
        (
            {
                "name": "   ",
                "short_name": "P1",
                "period_number": 1,
                "start_time": time(9, 0),
                "end_time": time(9, 50),
            },
            "Timetable period import field 'name' cannot be blank.",
        ),
        (
            {
                "name": "Period 1",
                "period_number": 1,
                "start_time": time(9, 0),
                "end_time": time(9, 50),
            },
            "Timetable period import field 'short_name' is required.",
        ),
        (
            {
                "name": "Period 1",
                "short_name": "P1",
                "period_number": 0,
                "start_time": time(9, 0),
                "end_time": time(9, 50),
            },
            (
                "Timetable period import field 'period_number' "
                "must be a positive integer."
            ),
        ),
        (
            {
                "name": "Period 1",
                "short_name": "P1",
                "period_number": 1,
                "start_time": "not-a-time",
                "end_time": time(9, 50),
            },
            ("Timetable period import field 'start_time' " "must be a valid time."),
        ),
        (
            {
                "name": "Period 1",
                "short_name": "P1",
                "period_number": 1,
                "start_time": time(9, 0),
                "end_time": time(9, 0),
            },
            (
                "Timetable period import field 'end_time' "
                "must be later than start_time."
            ),
        ),
        (
            {
                "name": "A" * 101,
                "short_name": "P1",
                "period_number": 1,
                "start_time": time(9, 0),
                "end_time": time(9, 50),
            },
            ("Timetable period import field 'name' " "cannot exceed 100 characters."),
        ),
        (
            {
                "name": "Period 1",
                "short_name": "P" * 21,
                "period_number": 1,
                "start_time": time(9, 0),
                "end_time": time(9, 50),
            },
            (
                "Timetable period import field 'short_name' "
                "cannot exceed 20 characters."
            ),
        ),
        (
            {
                "name": "Period 1",
                "short_name": "P1",
                "period_number": 1,
                "start_time": time(9, 0),
                "end_time": time(9, 50),
                "is_break": "yes",
            },
            ("Timetable period import field 'is_break' " "must be a boolean."),
        ),
    ],
)
@pytest.mark.asyncio
async def test_processor_defensively_rejects_malformed_rows(
    db_session: AsyncSession,
    row: dict[str, Any],
    expected_message: str,
) -> None:
    with pytest.raises(
        ValueError,
        match=expected_message.replace(
            "'",
            r"\'",
        ),
    ):
        await process_timetable_period_row(
            db_session,
            row,
            1,
        )


@pytest.mark.asyncio
async def test_repository_period_lookup_and_exists_checks(
    db_session: AsyncSession,
    school_admin_user: User,
) -> None:
    school_id = school_admin_user.school_id

    assert school_id is not None

    period = TimetablePeriod(
        school_id=school_id,
        name="Repository Period",
        short_name="RP",
        period_number=4,
        start_time=time(11, 0),
        end_time=time(11, 50),
        is_registration=False,
        is_break=False,
        is_lunch=False,
        is_active=True,
    )

    db_session.add(period)
    await db_session.commit()
    await db_session.refresh(period)

    repository = TimetableRepository(
        db_session,
    )

    found_by_id = await repository.get_period_by_id_and_school(
        period.id,
        school_id,
    )

    found_by_number = await repository.get_period_by_number(
        school_id=school_id,
        period_number=4,
    )

    found_by_short_name = await repository.get_period_by_short_name(
        school_id=school_id,
        short_name=" RP ",
    )

    assert found_by_id is not None
    assert found_by_id.id == period.id

    assert found_by_number is not None
    assert found_by_number.id == period.id

    assert found_by_short_name is not None
    assert found_by_short_name.id == period.id

    assert (
        await repository.period_exists_in_school(
            school_id=school_id,
            period_id=period.id,
        )
        is True
    )

    assert (
        await repository.period_exists_in_school(
            school_id=school_id,
            period_number=4,
        )
        is True
    )

    assert (
        await repository.period_exists_in_school(
            school_id=school_id,
            short_name="RP",
        )
        is True
    )

    assert (
        await repository.period_exists_in_school(
            school_id=school_id + 999,
            period_id=period.id,
        )
        is False
    )


@pytest.mark.asyncio
async def test_repository_lists_periods_in_period_number_order(
    db_session: AsyncSession,
    school_admin_user: User,
) -> None:
    school_id = school_admin_user.school_id

    assert school_id is not None

    period_three = TimetablePeriod(
        school_id=school_id,
        name="Period 3",
        short_name="P3",
        period_number=3,
        start_time=time(10, 40),
        end_time=time(11, 30),
        is_registration=False,
        is_break=False,
        is_lunch=False,
        is_active=True,
    )

    period_one = TimetablePeriod(
        school_id=school_id,
        name="Period 1",
        short_name="P1",
        period_number=1,
        start_time=time(9, 0),
        end_time=time(9, 50),
        is_registration=False,
        is_break=False,
        is_lunch=False,
        is_active=True,
    )

    period_two = TimetablePeriod(
        school_id=school_id,
        name="Period 2",
        short_name="P2",
        period_number=2,
        start_time=time(9, 50),
        end_time=time(10, 40),
        is_registration=False,
        is_break=False,
        is_lunch=False,
        is_active=False,
    )

    db_session.add_all(
        [
            period_three,
            period_one,
            period_two,
        ],
    )

    await db_session.commit()

    repository = TimetableRepository(
        db_session,
    )

    all_periods = await repository.list_periods(
        school_id,
    )

    active_periods = await repository.list_periods(
        school_id,
        active_only=True,
    )

    relevant_all = [
        period
        for period in all_periods
        if period.id
        in {
            period_one.id,
            period_two.id,
            period_three.id,
        }
    ]

    relevant_active = [
        period
        for period in active_periods
        if period.id
        in {
            period_one.id,
            period_two.id,
            period_three.id,
        }
    ]

    assert [period.id for period in relevant_all] == [
        period_one.id,
        period_two.id,
        period_three.id,
    ]

    assert [period.id for period in relevant_active] == [
        period_one.id,
        period_three.id,
    ]


@pytest.mark.asyncio
async def test_processing_task_creates_period(
    db_session: AsyncSession,
    school_admin_user: User,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    register_import_handlers()

    school_id = school_admin_user.school_id

    assert school_id is not None

    task_session_maker = configure_task_session_maker(
        db_session,
        monkeypatch,
    )

    batch = build_timetable_period_batch(
        school_id=school_id,
        uploaded_by_id=school_admin_user.id,
        operation=ImportOperation.CREATE,
    )

    db_session.add(batch)
    await db_session.flush()

    row = build_timetable_period_row(
        batch_id=batch.id,
        school_id=school_id,
        row_number=2,
        data={
            "name": "Batch Period 1",
            "short_name": "BP1",
            "period_number": 10,
            "start_time": "13:00:00",
            "end_time": "13:50:00",
            "is_registration": False,
            "is_break": False,
            "is_lunch": False,
            "is_active": True,
        },
    )

    db_session.add(row)
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

        created_period = await TimetableRepository(
            verification_db,
        ).get_period_by_number(
            school_id=school_id,
            period_number=10,
        )

        assert summary["status"] == ImportStatus.COMPLETED.value
        assert summary["processed_rows"] == 1
        assert summary["successful_rows"] == 1
        assert summary["imported_rows"] == 1
        assert summary["updated_rows"] == 0
        assert summary["failed_rows"] == 0

        assert processed_batch.status == ImportStatus.COMPLETED
        assert processed_batch.processed_rows == 1
        assert processed_batch.successful_rows == 1
        assert processed_batch.failed_rows == 0

        assert processed_row.status == ImportRowStatus.IMPORTED
        assert processed_row.attempt_count == 1
        assert processed_row.entity_type == "timetable_periods"
        assert processed_row.created_entity_id is not None
        assert processed_row.processed_at is not None
        assert processed_row.error_message is not None
        assert "Created timetable period" in processed_row.error_message

        assert created_period is not None
        assert created_period.id == processed_row.created_entity_id
        assert created_period.short_name == "BP1"


@pytest.mark.asyncio
async def test_processing_task_updates_existing_period(
    db_session: AsyncSession,
    school_admin_user: User,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    register_import_handlers()

    school_id = school_admin_user.school_id

    assert school_id is not None

    period = TimetablePeriod(
        school_id=school_id,
        name="Old Batch Period",
        short_name="OLD",
        period_number=11,
        start_time=time(13, 50),
        end_time=time(14, 40),
        is_registration=False,
        is_break=False,
        is_lunch=False,
        is_active=True,
    )

    db_session.add(period)
    await db_session.commit()
    await db_session.refresh(period)

    period_id = period.id

    task_session_maker = configure_task_session_maker(
        db_session,
        monkeypatch,
    )

    batch = build_timetable_period_batch(
        school_id=school_id,
        uploaded_by_id=school_admin_user.id,
        operation=ImportOperation.UPSERT,
    )

    db_session.add(batch)
    await db_session.flush()

    row = build_timetable_period_row(
        batch_id=batch.id,
        school_id=school_id,
        row_number=2,
        data={
            "name": "Updated Batch Period",
            "short_name": "UBP",
            "period_number": 11,
            "start_time": "13:55:00",
            "end_time": "14:45:00",
            "is_registration": False,
            "is_break": False,
            "is_lunch": False,
            "is_active": False,
        },
    )

    db_session.add(row)
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

        updated_period = await get_period_by_id(
            verification_db,
            period_id,
        )

        assert summary["status"] == ImportStatus.COMPLETED.value
        assert summary["processed_rows"] == 1
        assert summary["successful_rows"] == 1
        assert summary["imported_rows"] == 0
        assert summary["updated_rows"] == 1
        assert summary["failed_rows"] == 0

        assert processed_batch.status == ImportStatus.COMPLETED
        assert processed_batch.successful_rows == 1
        assert processed_batch.failed_rows == 0

        assert processed_row.status == ImportRowStatus.UPDATED
        assert processed_row.attempt_count == 1
        assert processed_row.entity_type == "timetable_periods"
        assert processed_row.created_entity_id == period_id
        assert processed_row.error_message is not None
        assert "Updated timetable period" in processed_row.error_message

        assert updated_period.name == "Updated Batch Period"
        assert updated_period.short_name == "UBP"
        assert updated_period.start_time == time(13, 55)
        assert updated_period.end_time == time(14, 45)
        assert updated_period.is_active is False


@pytest.mark.asyncio
async def test_processing_task_records_duplicate_short_name_failure(
    db_session: AsyncSession,
    school_admin_user: User,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    register_import_handlers()

    school_id = school_admin_user.school_id

    assert school_id is not None

    existing_period = TimetablePeriod(
        school_id=school_id,
        name="Existing Period",
        short_name="DUP",
        period_number=12,
        start_time=time(14, 45),
        end_time=time(15, 35),
        is_registration=False,
        is_break=False,
        is_lunch=False,
        is_active=True,
    )

    db_session.add(existing_period)
    await db_session.commit()

    task_session_maker = configure_task_session_maker(
        db_session,
        monkeypatch,
    )

    batch = build_timetable_period_batch(
        school_id=school_id,
        uploaded_by_id=school_admin_user.id,
    )

    db_session.add(batch)
    await db_session.flush()

    row = build_timetable_period_row(
        batch_id=batch.id,
        school_id=school_id,
        row_number=2,
        data={
            "name": "Conflicting Period",
            "short_name": "DUP",
            "period_number": 13,
            "start_time": "15:35:00",
            "end_time": "16:25:00",
            "is_registration": False,
            "is_break": False,
            "is_lunch": False,
            "is_active": True,
        },
    )

    db_session.add(row)
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

        failed_row = await get_row_by_id(
            verification_db,
            row_id,
        )

        conflicting_period = await TimetableRepository(
            verification_db,
        ).get_period_by_number(
            school_id=school_id,
            period_number=13,
        )

        assert summary["status"] == (ImportStatus.COMPLETED_WITH_ERRORS.value)
        assert summary["processed_rows"] == 1
        assert summary["successful_rows"] == 0
        assert summary["failed_rows"] == 1

        assert processed_batch.status == (ImportStatus.COMPLETED_WITH_ERRORS)
        assert processed_batch.successful_rows == 0
        assert processed_batch.failed_rows == 1

        assert failed_row.status == ImportRowStatus.FAILED
        assert failed_row.attempt_count == 1
        assert failed_row.created_entity_id is None
        assert failed_row.processed_at is not None
        assert failed_row.error_message is not None
        assert "short name" in failed_row.error_message

        assert conflicting_period is None


@pytest.mark.asyncio
async def test_timetable_period_processing_enforces_school_isolation(
    db_session: AsyncSession,
    school_admin_user: User,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    school_id = school_admin_user.school_id

    assert school_id is not None

    configure_task_session_maker(
        db_session,
        monkeypatch,
    )

    batch = build_timetable_period_batch(
        school_id=school_id,
        uploaded_by_id=school_admin_user.id,
    )

    db_session.add(batch)
    await db_session.flush()

    row = build_timetable_period_row(
        batch_id=batch.id,
        school_id=school_id,
        row_number=2,
        data={
            "name": "Isolated Period",
            "short_name": "ISO",
            "period_number": 20,
            "start_time": "16:00:00",
            "end_time": "16:50:00",
            "is_registration": False,
            "is_break": False,
            "is_lunch": False,
            "is_active": True,
        },
    )

    db_session.add(row)
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

    await db_session.refresh(batch)
    await db_session.refresh(row)

    assert batch.status == ImportStatus.READY
    assert batch.processed_rows == 0
    assert batch.successful_rows == 0
    assert batch.failed_rows == 0

    assert row.status == ImportRowStatus.VALID
    assert row.attempt_count == 0
    assert row.created_entity_id is None
    assert row.processed_at is None

    period = await TimetableRepository(
        db_session,
    ).get_period_by_number(
        school_id=school_id,
        period_number=20,
    )

    assert period is None
