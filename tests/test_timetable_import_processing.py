from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import date
from typing import Any

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
)

import app.tasks.imports as import_tasks
from app.imports.bootstrap import register_import_handlers
from app.imports.processors.timetables import process_timetable_row
from app.imports.registry import (
    RowProcessingAction,
    get_import_handler,
)
from app.imports.validators.timetables import validate_timetable_row
from app.models.import_batch import (
    ImportBatch,
    ImportOperation,
    ImportRow,
    ImportRowStatus,
    ImportStatus,
)
from app.models.timetable import Timetable
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
    Open a fresh session for checking committed task results.
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


async def get_timetable_by_id(
    db: AsyncSession,
    timetable_id: int,
) -> Timetable:
    result = await db.execute(
        select(Timetable).where(
            Timetable.id == timetable_id,
        ),
    )

    return result.scalar_one()


def build_timetable_batch(
    *,
    school_id: int,
    uploaded_by_id: int,
    operation: ImportOperation = ImportOperation.UPSERT,
    total_rows: int = 1,
) -> ImportBatch:
    """
    Build a ready master-timetable import batch.
    """

    return ImportBatch(
        school_id=school_id,
        uploaded_by_id=uploaded_by_id,
        import_type="timetables",
        operation=operation,
        status=ImportStatus.READY,
        original_filename="timetables.csv",
        total_rows=total_rows,
        validated_rows=total_rows,
        processed_rows=0,
        successful_rows=0,
        warning_rows=0,
        failed_rows=0,
        skipped_rows=0,
        current_stage="ready",
    )


def build_timetable_row(
    *,
    batch_id: int,
    school_id: int,
    row_number: int,
    data: dict[str, Any],
    status: ImportRowStatus = ImportRowStatus.VALID,
    validation_errors: list[dict[str, Any]] | None = None,
) -> ImportRow:
    """
    Build one staged master-timetable import row.

    Dates must be represented using JSON-safe ISO strings.
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


def test_timetable_handler_is_registered() -> None:
    register_import_handlers()

    handler = get_import_handler(
        "timetables",
    )

    assert handler.validator is validate_timetable_row
    assert handler.processor is process_timetable_row


def test_timetable_validator_accepts_valid_row() -> None:
    result = validate_timetable_row(
        {
            "name": " Main Timetable ",
            "academic_year": " 2026/2027 ",
            "effective_from": "2026-09-01",
            "effective_to": "2027-07-20",
            "is_active": True,
            "source_system": "MIS",
        },
    )

    assert result.is_valid is True
    assert result.errors == []
    assert result.warnings == []

    assert result.normalised_data is not None
    assert result.normalised_data["name"] == "Main Timetable"
    assert result.normalised_data["academic_year"] == "2026/2027"

    # Validated rows are serialised for JSON persistence.
    assert result.normalised_data["effective_from"] == "2026-09-01"
    assert result.normalised_data["effective_to"] == "2027-07-20"
    assert result.normalised_data["is_active"] is True

    # Extra columns remain available for future import expansion.
    assert result.normalised_data["source_system"] == "MIS"


def test_timetable_validator_applies_defaults() -> None:
    result = validate_timetable_row(
        {
            "name": "Main Timetable",
            "academic_year": "2026/2027",
            "effective_from": "2026-09-01",
        },
    )

    assert result.is_valid is True
    assert result.normalised_data is not None
    assert result.normalised_data["effective_to"] is None
    assert result.normalised_data["is_active"] is True


def test_timetable_validator_accepts_equal_effective_dates() -> None:
    result = validate_timetable_row(
        {
            "name": "One Day Timetable",
            "academic_year": "2026/2027",
            "effective_from": "2026-09-01",
            "effective_to": "2026-09-01",
        },
    )

    assert result.is_valid is True
    assert result.normalised_data is not None


def test_timetable_validator_rejects_invalid_date_range() -> None:
    result = validate_timetable_row(
        {
            "name": "Invalid Timetable",
            "academic_year": "2026/2027",
            "effective_from": "2026-09-01",
            "effective_to": "2026-08-31",
        },
    )

    assert result.is_valid is False
    assert result.normalised_data is None
    assert result.errors


def test_timetable_validator_rejects_invalid_dates() -> None:
    result = validate_timetable_row(
        {
            "name": "Invalid Timetable",
            "academic_year": "2026/2027",
            "effective_from": "not-a-date",
            "effective_to": "also-not-a-date",
        },
    )

    assert result.is_valid is False
    assert result.normalised_data is None

    error_locations = {tuple(error["loc"]) for error in result.errors}

    assert ("effective_from",) in error_locations
    assert ("effective_to",) in error_locations


def test_timetable_validator_rejects_missing_required_fields() -> None:
    result = validate_timetable_row(
        {},
    )

    assert result.is_valid is False
    assert result.normalised_data is None

    error_locations = {tuple(error["loc"]) for error in result.errors}

    assert ("name",) in error_locations
    assert ("academic_year",) in error_locations
    assert ("effective_from",) in error_locations


def test_timetable_validator_rejects_long_strings() -> None:
    result = validate_timetable_row(
        {
            "name": "A" * 151,
            "academic_year": "B" * 21,
            "effective_from": "2026-09-01",
        },
    )

    assert result.is_valid is False
    assert result.normalised_data is None

    error_locations = {tuple(error["loc"]) for error in result.errors}

    assert ("name",) in error_locations
    assert ("academic_year",) in error_locations


@pytest.mark.asyncio
async def test_processor_creates_timetable(
    db_session: AsyncSession,
    school_admin_user: User,
) -> None:
    school_id = school_admin_user.school_id

    assert school_id is not None

    result = await process_timetable_row(
        db_session,
        {
            "name": " Main Timetable ",
            "academic_year": " 2026/2027 ",
            "effective_from": date(2026, 9, 1),
            "effective_to": date(2027, 7, 20),
            "is_active": True,
        },
        school_id,
    )

    await db_session.commit()

    timetable = await TimetableRepository(
        db_session,
    ).get_timetable_by_name_and_year(
        school_id=school_id,
        name="Main Timetable",
        academic_year="2026/2027",
    )

    assert result.action == RowProcessingAction.CREATED
    assert result.entity_id is not None
    assert result.message == (
        "Created timetable 'Main Timetable' " "for academic year '2026/2027'."
    )

    assert timetable is not None
    assert timetable.id == result.entity_id
    assert timetable.school_id == school_id
    assert timetable.name == "Main Timetable"
    assert timetable.academic_year == "2026/2027"
    assert timetable.effective_from == date(2026, 9, 1)
    assert timetable.effective_to == date(2027, 7, 20)
    assert timetable.is_active is True


@pytest.mark.asyncio
async def test_processor_accepts_iso_date_strings(
    db_session: AsyncSession,
    school_admin_user: User,
) -> None:
    school_id = school_admin_user.school_id

    assert school_id is not None

    result = await process_timetable_row(
        db_session,
        {
            "name": "String Date Timetable",
            "academic_year": "2027/2028",
            "effective_from": "2027-09-01",
            "effective_to": "2028-07-20",
        },
        school_id,
    )

    await db_session.commit()

    timetable = await TimetableRepository(
        db_session,
    ).get_timetable_by_name_and_year(
        school_id=school_id,
        name="String Date Timetable",
        academic_year="2027/2028",
    )

    assert result.action == RowProcessingAction.CREATED
    assert timetable is not None
    assert timetable.effective_from == date(2027, 9, 1)
    assert timetable.effective_to == date(2028, 7, 20)
    assert timetable.is_active is True


@pytest.mark.asyncio
async def test_processor_creates_timetable_without_end_date(
    db_session: AsyncSession,
    school_admin_user: User,
) -> None:
    school_id = school_admin_user.school_id

    assert school_id is not None

    result = await process_timetable_row(
        db_session,
        {
            "name": "Open Ended Timetable",
            "academic_year": "2026/2027",
            "effective_from": "2026-09-01",
            "effective_to": "",
            "is_active": True,
        },
        school_id,
    )

    await db_session.commit()

    timetable = await TimetableRepository(
        db_session,
    ).get_timetable_by_name_and_year(
        school_id=school_id,
        name="Open Ended Timetable",
        academic_year="2026/2027",
    )

    assert result.action == RowProcessingAction.CREATED
    assert timetable is not None
    assert timetable.effective_to is None


@pytest.mark.asyncio
async def test_processor_updates_existing_timetable(
    db_session: AsyncSession,
    school_admin_user: User,
) -> None:
    school_id = school_admin_user.school_id

    assert school_id is not None

    timetable = Timetable(
        school_id=school_id,
        name="Main Timetable",
        academic_year="2026/2027",
        effective_from=date(2026, 9, 1),
        effective_to=date(2027, 7, 20),
        is_active=True,
    )

    db_session.add(timetable)
    await db_session.commit()
    await db_session.refresh(timetable)

    timetable_id = timetable.id

    result = await process_timetable_row(
        db_session,
        {
            "name": "Main Timetable",
            "academic_year": "2026/2027",
            "effective_from": "2026-09-05",
            "effective_to": "2027-07-25",
            "is_active": False,
        },
        school_id,
    )

    await db_session.commit()
    await db_session.refresh(timetable)

    assert result.action == RowProcessingAction.UPDATED
    assert result.entity_id == timetable_id
    assert result.message == (
        "Updated timetable 'Main Timetable' " "for academic year '2026/2027'."
    )

    assert timetable.id == timetable_id
    assert timetable.effective_from == date(2026, 9, 5)
    assert timetable.effective_to == date(2027, 7, 25)
    assert timetable.is_active is False


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
        await process_timetable_row(
            db_session,
            {
                "name": "Main Timetable",
                "academic_year": "2026/2027",
                "effective_from": "2026-09-01",
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
                "academic_year": "2026/2027",
                "effective_from": "2026-09-01",
            },
            "Timetable import field 'name' is required.",
        ),
        (
            {
                "name": "   ",
                "academic_year": "2026/2027",
                "effective_from": "2026-09-01",
            },
            "Timetable import field 'name' cannot be blank.",
        ),
        (
            {
                "name": "Main Timetable",
                "effective_from": "2026-09-01",
            },
            "Timetable import field 'academic_year' is required.",
        ),
        (
            {
                "name": "Main Timetable",
                "academic_year": "   ",
                "effective_from": "2026-09-01",
            },
            "Timetable import field 'academic_year' cannot be blank.",
        ),
        (
            {
                "name": "Main Timetable",
                "academic_year": "2026/2027",
            },
            "Timetable import field 'effective_from' must be a valid date.",
        ),
        (
            {
                "name": "Main Timetable",
                "academic_year": "2026/2027",
                "effective_from": "not-a-date",
            },
            "Timetable import field 'effective_from' must be a valid date.",
        ),
        (
            {
                "name": "Main Timetable",
                "academic_year": "2026/2027",
                "effective_from": "2026-09-01",
                "effective_to": "not-a-date",
            },
            "Timetable import field 'effective_to' must be a valid date.",
        ),
        (
            {
                "name": "Main Timetable",
                "academic_year": "2026/2027",
                "effective_from": "2026-09-01",
                "effective_to": "2026-08-31",
            },
            (
                "Timetable import field 'effective_to' "
                "cannot be earlier than effective_from."
            ),
        ),
        (
            {
                "name": "A" * 151,
                "academic_year": "2026/2027",
                "effective_from": "2026-09-01",
            },
            ("Timetable import field 'name' " "cannot exceed 150 characters."),
        ),
        (
            {
                "name": "Main Timetable",
                "academic_year": "A" * 21,
                "effective_from": "2026-09-01",
            },
            ("Timetable import field 'academic_year' " "cannot exceed 20 characters."),
        ),
        (
            {
                "name": "Main Timetable",
                "academic_year": "2026/2027",
                "effective_from": "2026-09-01",
                "is_active": "yes",
            },
            "Timetable import field 'is_active' must be a boolean.",
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
        await process_timetable_row(
            db_session,
            row,
            1,
        )


@pytest.mark.asyncio
async def test_repository_timetable_lookup_and_exists_checks(
    db_session: AsyncSession,
    school_admin_user: User,
) -> None:
    school_id = school_admin_user.school_id

    assert school_id is not None

    timetable = Timetable(
        school_id=school_id,
        name="Repository Timetable",
        academic_year="2026/2027",
        effective_from=date(2026, 9, 1),
        effective_to=date(2027, 7, 20),
        is_active=True,
    )

    db_session.add(timetable)
    await db_session.commit()
    await db_session.refresh(timetable)

    repository = TimetableRepository(
        db_session,
    )

    found_by_id = await repository.get_timetable_by_id_and_school(
        timetable.id,
        school_id,
    )

    found_by_identity = await repository.get_timetable_by_name_and_year(
        school_id=school_id,
        name=" Repository Timetable ",
        academic_year=" 2026/2027 ",
    )

    assert found_by_id is not None
    assert found_by_id.id == timetable.id

    assert found_by_identity is not None
    assert found_by_identity.id == timetable.id

    assert (
        await repository.timetable_exists_in_school(
            school_id=school_id,
            timetable_id=timetable.id,
        )
        is True
    )

    assert (
        await repository.timetable_exists_in_school(
            school_id=school_id,
            name="Repository Timetable",
            academic_year="2026/2027",
        )
        is True
    )

    assert (
        await repository.timetable_exists_in_school(
            school_id=school_id + 999,
            timetable_id=timetable.id,
        )
        is False
    )


@pytest.mark.asyncio
async def test_repository_saves_existing_timetable(
    db_session: AsyncSession,
    school_admin_user: User,
) -> None:
    school_id = school_admin_user.school_id

    assert school_id is not None

    timetable = Timetable(
        school_id=school_id,
        name="Original Timetable",
        academic_year="2026/2027",
        effective_from=date(2026, 9, 1),
        effective_to=None,
        is_active=True,
    )

    db_session.add(timetable)
    await db_session.commit()
    await db_session.refresh(timetable)

    timetable.name = "Updated Repository Timetable"
    timetable.effective_to = date(2027, 7, 20)
    timetable.is_active = False

    saved = await TimetableRepository(
        db_session,
    ).save_timetable(
        timetable,
    )

    await db_session.commit()

    assert saved.id == timetable.id
    assert saved.name == "Updated Repository Timetable"
    assert saved.effective_to == date(2027, 7, 20)
    assert saved.is_active is False


@pytest.mark.asyncio
async def test_processing_task_creates_timetable(
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

    batch = build_timetable_batch(
        school_id=school_id,
        uploaded_by_id=school_admin_user.id,
        operation=ImportOperation.CREATE,
    )

    db_session.add(batch)
    await db_session.flush()

    row = build_timetable_row(
        batch_id=batch.id,
        school_id=school_id,
        row_number=2,
        data={
            "name": "Batch Timetable",
            "academic_year": "2028/2029",
            "effective_from": "2028-09-01",
            "effective_to": "2029-07-20",
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

        created_timetable = await TimetableRepository(
            verification_db,
        ).get_timetable_by_name_and_year(
            school_id=school_id,
            name="Batch Timetable",
            academic_year="2028/2029",
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
        assert processed_row.entity_type == "timetables"
        assert processed_row.created_entity_id is not None
        assert processed_row.processed_at is not None
        assert processed_row.error_message is not None
        assert "Created timetable" in processed_row.error_message

        assert created_timetable is not None
        assert created_timetable.id == processed_row.created_entity_id
        assert created_timetable.effective_from == date(2028, 9, 1)
        assert created_timetable.effective_to == date(2029, 7, 20)


@pytest.mark.asyncio
async def test_processing_task_updates_existing_timetable(
    db_session: AsyncSession,
    school_admin_user: User,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    register_import_handlers()

    school_id = school_admin_user.school_id

    assert school_id is not None

    timetable = Timetable(
        school_id=school_id,
        name="Batch Existing Timetable",
        academic_year="2029/2030",
        effective_from=date(2029, 9, 1),
        effective_to=date(2030, 7, 20),
        is_active=True,
    )

    db_session.add(timetable)
    await db_session.commit()
    await db_session.refresh(timetable)

    timetable_id = timetable.id

    task_session_maker = configure_task_session_maker(
        db_session,
        monkeypatch,
    )

    batch = build_timetable_batch(
        school_id=school_id,
        uploaded_by_id=school_admin_user.id,
        operation=ImportOperation.UPSERT,
    )

    db_session.add(batch)
    await db_session.flush()

    row = build_timetable_row(
        batch_id=batch.id,
        school_id=school_id,
        row_number=2,
        data={
            "name": "Batch Existing Timetable",
            "academic_year": "2029/2030",
            "effective_from": "2029-09-05",
            "effective_to": "2030-07-25",
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

        updated_timetable = await get_timetable_by_id(
            verification_db,
            timetable_id,
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
        assert processed_row.entity_type == "timetables"
        assert processed_row.created_entity_id == timetable_id
        assert processed_row.processed_at is not None
        assert processed_row.error_message is not None
        assert "Updated timetable" in processed_row.error_message

        assert updated_timetable.effective_from == date(2029, 9, 5)
        assert updated_timetable.effective_to == date(2030, 7, 25)
        assert updated_timetable.is_active is False


@pytest.mark.asyncio
async def test_processing_task_records_invalid_date_failure(
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

    batch = build_timetable_batch(
        school_id=school_id,
        uploaded_by_id=school_admin_user.id,
    )

    db_session.add(batch)
    await db_session.flush()

    row = build_timetable_row(
        batch_id=batch.id,
        school_id=school_id,
        row_number=2,
        data={
            "name": "Invalid Batch Timetable",
            "academic_year": "2030/2031",
            "effective_from": "not-a-date",
            "effective_to": "2031-07-20",
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

        created_timetable = await TimetableRepository(
            verification_db,
        ).get_timetable_by_name_and_year(
            school_id=school_id,
            name="Invalid Batch Timetable",
            academic_year="2030/2031",
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
        assert "must be a valid date" in failed_row.error_message

        assert created_timetable is None


@pytest.mark.asyncio
async def test_timetable_processing_enforces_school_isolation(
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

    batch = build_timetable_batch(
        school_id=school_id,
        uploaded_by_id=school_admin_user.id,
    )

    db_session.add(batch)
    await db_session.flush()

    row = build_timetable_row(
        batch_id=batch.id,
        school_id=school_id,
        row_number=2,
        data={
            "name": "Isolated Timetable",
            "academic_year": "2031/2032",
            "effective_from": "2031-09-01",
            "effective_to": "2032-07-20",
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

    timetable = await TimetableRepository(
        db_session,
    ).get_timetable_by_name_and_year(
        school_id=school_id,
        name="Isolated Timetable",
        academic_year="2031/2032",
    )

    assert timetable is None
