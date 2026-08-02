from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
)

import app.tasks.imports as import_tasks
from app.imports.bootstrap import register_import_handlers
from app.imports.processors.classes import process_class_row
from app.imports.registry import (
    RowProcessingAction,
    get_import_handler,
)
from app.imports.validators.classes import validate_class_row
from app.models.class_group import ClassGroup
from app.models.import_batch import (
    ImportBatch,
    ImportOperation,
    ImportRow,
    ImportRowStatus,
    ImportStatus,
)
from app.models.user import User
from app.repositories.class_group import ClassGroupRepository

pytestmark = pytest.mark.asyncio


def create_task_session_maker(
    db_session: AsyncSession,
) -> async_sessionmaker[AsyncSession]:
    """
    Create a task-compatible session maker bound to the test database.
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
    Open a fresh session for verifying committed background-task results.
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


async def get_class_by_id(
    db: AsyncSession,
    class_id: int,
) -> ClassGroup:
    result = await db.execute(
        select(ClassGroup).where(
            ClassGroup.id == class_id,
        ),
    )

    return result.scalar_one()


def build_class_batch(
    *,
    school_id: int,
    uploaded_by_id: int,
    operation: ImportOperation = ImportOperation.CREATE,
    total_rows: int = 1,
) -> ImportBatch:
    """
    Build a ready class-import batch with consistent counters.
    """

    return ImportBatch(
        school_id=school_id,
        uploaded_by_id=uploaded_by_id,
        import_type="classes",
        operation=operation,
        status=ImportStatus.READY,
        original_filename="classes.csv",
        total_rows=total_rows,
        validated_rows=total_rows,
        processed_rows=0,
        successful_rows=0,
        warning_rows=0,
        failed_rows=0,
        skipped_rows=0,
        current_stage="ready",
    )


def build_class_row(
    *,
    batch_id: int,
    school_id: int,
    row_number: int,
    data: dict[str, Any],
    status: ImportRowStatus = ImportRowStatus.VALID,
    validation_errors: list[dict[str, Any]] | None = None,
) -> ImportRow:
    """
    Build one staged class-import row.
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


async def test_class_import_handler_is_registered() -> None:
    register_import_handlers()

    handler = get_import_handler(
        "classes",
    )

    assert handler.validator is validate_class_row
    assert handler.processor is process_class_row


async def test_class_validator_accepts_valid_row() -> None:
    result = validate_class_row(
        {
            "name": "  Year 10 Physics  ",
            "teacher_email": " teacher@example.com ",
            "year_group": "10",
        },
    )

    assert result.is_valid is True
    assert result.errors == []
    assert result.warnings == []

    assert result.normalised_data is not None
    assert result.normalised_data["name"] == "Year 10 Physics"
    assert result.normalised_data["teacher_email"] == ("teacher@example.com")

    # Extra columns remain available for future class-import expansion.
    assert result.normalised_data["year_group"] == "10"


async def test_class_validator_accepts_missing_teacher() -> None:
    result = validate_class_row(
        {
            "name": "Year 7 Mathematics",
        },
    )

    assert result.is_valid is True
    assert result.errors == []
    assert result.normalised_data is not None
    assert result.normalised_data["name"] == "Year 7 Mathematics"
    assert result.normalised_data["teacher_email"] is None


async def test_class_validator_rejects_invalid_row() -> None:
    result = validate_class_row(
        {
            "name": "",
            "teacher_email": "not-an-email",
        },
    )

    assert result.is_valid is False
    assert result.normalised_data is None
    assert result.errors

    error_locations = {tuple(error["loc"]) for error in result.errors}

    assert ("name",) in error_locations
    assert ("teacher_email",) in error_locations


async def test_class_processor_creates_class_without_teacher(
    db_session: AsyncSession,
    school_admin_user: User,
) -> None:
    school_id = school_admin_user.school_id

    assert school_id is not None

    result = await process_class_row(
        db_session,
        {
            "name": " Year 8 Science ",
        },
        school_id,
    )

    await db_session.commit()

    repository = ClassGroupRepository(
        db_session,
    )

    created_class = await repository.get_by_name_and_school(
        name="Year 8 Science",
        school_id=school_id,
    )

    assert result.action == RowProcessingAction.CREATED
    assert result.entity_id is not None
    assert result.message == "Created class 'Year 8 Science'."

    assert created_class is not None
    assert created_class.id == result.entity_id
    assert created_class.name == "Year 8 Science"
    assert created_class.school_id == school_id
    assert created_class.teacher_id is None


async def test_class_processor_creates_class_with_teacher(
    db_session: AsyncSession,
    school_admin_user: User,
    teacher_user: User,
) -> None:
    school_id = school_admin_user.school_id

    assert school_id is not None
    assert teacher_user.school_id == school_id

    result = await process_class_row(
        db_session,
        {
            "name": "Year 11 Physics",
            "teacher_email": teacher_user.email.upper(),
        },
        school_id,
    )

    await db_session.commit()

    created_class = await ClassGroupRepository(
        db_session,
    ).get_by_name_and_school(
        name="Year 11 Physics",
        school_id=school_id,
    )

    assert result.action == RowProcessingAction.CREATED
    assert result.entity_id is not None

    assert created_class is not None
    assert created_class.id == result.entity_id
    assert created_class.teacher_id == teacher_user.id


async def test_class_processor_updates_existing_class_teacher(
    db_session: AsyncSession,
    school_admin_user: User,
    teacher_user: User,
) -> None:
    school_id = school_admin_user.school_id

    assert school_id is not None
    assert teacher_user.school_id == school_id

    class_group = ClassGroup(
        name="Year 9 Chemistry",
        school_id=school_id,
        teacher_id=None,
    )

    db_session.add(class_group)
    await db_session.commit()
    await db_session.refresh(class_group)

    class_id = class_group.id

    result = await process_class_row(
        db_session,
        {
            "name": "Year 9 Chemistry",
            "teacher_email": teacher_user.email,
        },
        school_id,
    )

    await db_session.commit()
    await db_session.refresh(class_group)

    assert result.action == RowProcessingAction.UPDATED
    assert result.entity_id == class_id
    assert result.message == "Updated class 'Year 9 Chemistry'."

    assert class_group.id == class_id
    assert class_group.teacher_id == teacher_user.id


async def test_class_processor_clears_existing_teacher_when_omitted(
    db_session: AsyncSession,
    school_admin_user: User,
    teacher_user: User,
) -> None:
    school_id = school_admin_user.school_id

    assert school_id is not None
    assert teacher_user.school_id == school_id

    class_group = ClassGroup(
        name="Year 10 Biology",
        school_id=school_id,
        teacher_id=teacher_user.id,
    )

    db_session.add(class_group)
    await db_session.commit()
    await db_session.refresh(class_group)

    result = await process_class_row(
        db_session,
        {
            "name": "Year 10 Biology",
        },
        school_id,
    )

    await db_session.commit()
    await db_session.refresh(class_group)

    assert result.action == RowProcessingAction.UPDATED
    assert result.entity_id == class_group.id
    assert class_group.teacher_id is None


async def test_class_processor_rejects_unknown_teacher(
    db_session: AsyncSession,
    school_admin_user: User,
) -> None:
    school_id = school_admin_user.school_id

    assert school_id is not None

    with pytest.raises(
        ValueError,
        match="No teacher with email",
    ):
        await process_class_row(
            db_session,
            {
                "name": "Unknown Teacher Class",
                "teacher_email": "missing.teacher@example.com",
            },
            school_id,
        )

    existing_class = await ClassGroupRepository(
        db_session,
    ).get_by_name_and_school(
        name="Unknown Teacher Class",
        school_id=school_id,
    )

    assert existing_class is None


async def test_class_processor_rejects_non_teacher_user(
    db_session: AsyncSession,
    school_admin_user: User,
    student_user: User,
) -> None:
    school_id = school_admin_user.school_id

    assert school_id is not None
    assert student_user.school_id == school_id

    with pytest.raises(
        ValueError,
        match="is not registered as a teacher",
    ):
        await process_class_row(
            db_session,
            {
                "name": "Invalid Teacher Assignment",
                "teacher_email": student_user.email,
            },
            school_id,
        )

    existing_class = await ClassGroupRepository(
        db_session,
    ).get_by_name_and_school(
        name="Invalid Teacher Assignment",
        school_id=school_id,
    )

    assert existing_class is None


@pytest.mark.parametrize(
    "school_id",
    [
        0,
        -1,
        -999,
    ],
)
async def test_class_processor_rejects_invalid_school_id(
    db_session: AsyncSession,
    school_id: int,
) -> None:
    with pytest.raises(
        ValueError,
        match="school_id must be a positive integer",
    ):
        await process_class_row(
            db_session,
            {
                "name": "Invalid School Class",
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
            {},
            "Class import field 'name' is required.",
        ),
        (
            {
                "name": None,
            },
            "Class import field 'name' is required.",
        ),
        (
            {
                "name": "   ",
            },
            "Class import field 'name' cannot be blank.",
        ),
        (
            {
                "name": "A" * 256,
            },
            "Class import field 'name' cannot exceed 255 characters.",
        ),
    ],
)
async def test_class_processor_defensively_rejects_malformed_rows(
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
        await process_class_row(
            db_session,
            row,
            1,
        )


async def test_class_repository_school_scoped_name_lookup(
    db_session: AsyncSession,
    school_admin_user: User,
) -> None:
    school_id = school_admin_user.school_id

    assert school_id is not None

    class_group = ClassGroup(
        name="Repository Lookup Class",
        school_id=school_id,
    )

    db_session.add(class_group)
    await db_session.commit()
    await db_session.refresh(class_group)

    repository = ClassGroupRepository(
        db_session,
    )

    found = await repository.get_by_name_and_school(
        name=" Repository Lookup Class ",
        school_id=school_id,
    )

    missing = await repository.get_by_name_and_school(
        name="Repository Lookup Class",
        school_id=school_id + 999,
    )

    assert found is not None
    assert found.id == class_group.id
    assert missing is None


async def test_class_repository_exists_in_school_by_name_and_id(
    db_session: AsyncSession,
    school_admin_user: User,
) -> None:
    school_id = school_admin_user.school_id

    assert school_id is not None

    class_group = ClassGroup(
        name="Repository Exists Class",
        school_id=school_id,
    )

    db_session.add(class_group)
    await db_session.commit()
    await db_session.refresh(class_group)

    repository = ClassGroupRepository(
        db_session,
    )

    assert (
        await repository.exists(
            class_group.id,
        )
        is True
    )

    assert (
        await repository.exists_in_school(
            school_id=school_id,
            class_id=class_group.id,
        )
        is True
    )

    assert (
        await repository.exists_in_school(
            school_id=school_id,
            name="Repository Exists Class",
        )
        is True
    )

    assert (
        await repository.exists_in_school(
            school_id=school_id + 999,
            class_id=class_group.id,
        )
        is False
    )

    assert (
        await repository.exists_in_school(
            school_id=school_id,
            name="Repository Exists Class",
            exclude_class_id=class_group.id,
        )
        is False
    )


async def test_processing_task_imports_valid_class_row(
    db_session: AsyncSession,
    school_admin_user: User,
    teacher_user: User,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    register_import_handlers()

    school_id = school_admin_user.school_id

    assert school_id is not None
    assert teacher_user.school_id == school_id

    task_session_maker = configure_task_session_maker(
        db_session,
        monkeypatch,
    )

    batch = build_class_batch(
        school_id=school_id,
        uploaded_by_id=school_admin_user.id,
    )

    db_session.add(batch)
    await db_session.flush()

    row_data = {
        "name": "Batch Imported Class",
        "teacher_email": teacher_user.email,
    }

    row = build_class_row(
        batch_id=batch.id,
        school_id=school_id,
        row_number=2,
        data=row_data,
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

        created_class = await ClassGroupRepository(
            verification_db,
        ).get_by_name_and_school(
            name="Batch Imported Class",
            school_id=school_id,
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
        assert processed_row.entity_type == "classes"
        assert processed_row.created_entity_id is not None
        assert processed_row.processed_at is not None
        assert processed_row.error_message is not None
        assert "Created class" in processed_row.error_message

        assert created_class is not None
        assert created_class.id == processed_row.created_entity_id
        assert created_class.teacher_id == teacher_user.id


async def test_processing_task_updates_existing_class(
    db_session: AsyncSession,
    school_admin_user: User,
    teacher_user: User,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    register_import_handlers()

    school_id = school_admin_user.school_id

    assert school_id is not None
    assert teacher_user.school_id == school_id

    class_group = ClassGroup(
        name="Existing Batch Class",
        school_id=school_id,
        teacher_id=None,
    )

    db_session.add(class_group)
    await db_session.commit()
    await db_session.refresh(class_group)

    class_id = class_group.id

    task_session_maker = configure_task_session_maker(
        db_session,
        monkeypatch,
    )

    batch = build_class_batch(
        school_id=school_id,
        uploaded_by_id=school_admin_user.id,
        operation=ImportOperation.UPSERT,
    )

    db_session.add(batch)
    await db_session.flush()

    row = build_class_row(
        batch_id=batch.id,
        school_id=school_id,
        row_number=2,
        data={
            "name": "Existing Batch Class",
            "teacher_email": teacher_user.email,
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

        updated_class = await get_class_by_id(
            verification_db,
            class_id,
        )

        matching_classes = (
            (
                await verification_db.execute(
                    select(ClassGroup).where(
                        ClassGroup.name == "Existing Batch Class",
                        ClassGroup.school_id == school_id,
                    ),
                )
            )
            .scalars()
            .all()
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
        assert processed_row.entity_type == "classes"
        assert processed_row.created_entity_id == class_id
        assert processed_row.error_message is not None
        assert "Updated class" in processed_row.error_message

        assert updated_class.teacher_id == teacher_user.id
        assert len(matching_classes) == 1
        assert matching_classes[0].id == class_id


async def test_processing_task_records_invalid_teacher_failure(
    db_session: AsyncSession,
    school_admin_user: User,
    student_user: User,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    register_import_handlers()

    school_id = school_admin_user.school_id

    assert school_id is not None
    assert student_user.school_id == school_id

    task_session_maker = configure_task_session_maker(
        db_session,
        monkeypatch,
    )

    batch = build_class_batch(
        school_id=school_id,
        uploaded_by_id=school_admin_user.id,
    )

    db_session.add(batch)
    await db_session.flush()

    row = build_class_row(
        batch_id=batch.id,
        school_id=school_id,
        row_number=2,
        data={
            "name": "Failed Teacher Class",
            "teacher_email": student_user.email,
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

        created_class = await ClassGroupRepository(
            verification_db,
        ).get_by_name_and_school(
            name="Failed Teacher Class",
            school_id=school_id,
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
        assert "not registered as a teacher" in (failed_row.error_message)

        assert created_class is None


async def test_class_processing_enforces_school_isolation(
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

    batch = build_class_batch(
        school_id=school_id,
        uploaded_by_id=school_admin_user.id,
    )

    db_session.add(batch)
    await db_session.flush()

    row = build_class_row(
        batch_id=batch.id,
        school_id=school_id,
        row_number=2,
        data={
            "name": "Isolated Class",
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

    created_class = await ClassGroupRepository(
        db_session,
    ).get_by_name_and_school(
        name="Isolated Class",
        school_id=school_id,
    )

    assert created_class is None
