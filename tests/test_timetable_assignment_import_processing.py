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
from app.imports.processors.timetable_assignments import (
    process_timetable_assignment_row,
)
from app.imports.registry import (
    RowProcessingAction,
    get_import_handler,
)
from app.imports.validators.timetable_assignments import (
    validate_timetable_assignment_row,
)
from app.models.import_batch import (
    ImportBatch,
    ImportOperation,
    ImportRow,
    ImportRowStatus,
    ImportStatus,
)
from app.models.timetable import Timetable
from app.models.timetable_assignment import (
    TimetableAssignment,
    TimetableAssignmentType,
)
from app.models.user import User
from app.repositories.timetable import TimetableRepository


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
    Open a fresh session for checking committed task results.
    """

    async with session_maker() as session:
        yield session


async def create_timetable(
    db_session: AsyncSession,
    *,
    school_id: int,
    name: str = "Main Timetable",
    academic_year: str = "2026/2027",
) -> Timetable:
    """
    Create a timetable used by assignment processor tests.
    """

    timetable = Timetable(
        school_id=school_id,
        name=name,
        academic_year=academic_year,
        effective_from=date(2026, 9, 1),
        effective_to=date(2027, 7, 20),
        is_active=True,
    )

    db_session.add(
        timetable,
    )
    await db_session.commit()
    await db_session.refresh(
        timetable,
    )

    return timetable


async def get_assignment_by_id(
    db: AsyncSession,
    assignment_id: int,
) -> TimetableAssignment:
    result = await db.execute(
        select(TimetableAssignment).where(
            TimetableAssignment.id == assignment_id,
        ),
    )

    return result.scalar_one()


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


def build_assignment_batch(
    *,
    school_id: int,
    uploaded_by_id: int,
    operation: ImportOperation = ImportOperation.UPSERT,
) -> ImportBatch:
    """
    Build a ready timetable-assignment import batch.
    """

    return ImportBatch(
        school_id=school_id,
        uploaded_by_id=uploaded_by_id,
        import_type="timetable_assignments",
        operation=operation,
        status=ImportStatus.READY,
        original_filename="timetable-assignments.csv",
        total_rows=1,
        validated_rows=1,
        processed_rows=0,
        successful_rows=0,
        warning_rows=0,
        failed_rows=0,
        skipped_rows=0,
        current_stage="ready",
    )


def build_assignment_row(
    *,
    batch_id: int,
    school_id: int,
    data: dict[str, Any],
) -> ImportRow:
    """
    Build one JSON-safe staged timetable-assignment row.
    """

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


def test_timetable_assignment_handler_is_registered() -> None:
    register_import_handlers()

    handler = get_import_handler(
        "timetable_assignments",
    )

    assert handler.validator is validate_timetable_assignment_row
    assert handler.processor is process_timetable_assignment_row


@pytest.mark.parametrize(
    (
        "assignment_type",
        "target_data",
    ),
    [
        (
            "teacher",
            {
                "user_email": "teacher@example.com",
            },
        ),
        (
            "student",
            {
                "user_email": "student@example.com",
            },
        ),
        (
            "class_group",
            {
                "class_name": "Year 10 Physics",
            },
        ),
    ],
)
def test_validator_accepts_supported_assignment_types(
    assignment_type: str,
    target_data: dict[str, str],
) -> None:
    result = validate_timetable_assignment_row(
        {
            "timetable_name": " Main Timetable ",
            "academic_year": " 2026/2027 ",
            "assignment_type": assignment_type,
            **target_data,
            "source_system": "MIS",
        },
    )

    assert result.is_valid is True
    assert result.errors == []
    assert result.warnings == []

    assert result.normalised_data is not None
    assert result.normalised_data["timetable_name"] == "Main Timetable"
    assert result.normalised_data["academic_year"] == "2026/2027"
    assert result.normalised_data["assignment_type"] == assignment_type
    assert result.normalised_data["source_system"] == "MIS"


@pytest.mark.parametrize(
    "missing_field",
    [
        "timetable_name",
        "academic_year",
        "assignment_type",
    ],
)
def test_validator_requires_core_fields(
    missing_field: str,
) -> None:
    row = {
        "timetable_name": "Main Timetable",
        "academic_year": "2026/2027",
        "assignment_type": "teacher",
        "user_email": "teacher@example.com",
    }

    row.pop(
        missing_field,
    )

    result = validate_timetable_assignment_row(
        row,
    )

    assert result.is_valid is False
    assert result.normalised_data is None


@pytest.mark.parametrize(
    "assignment_type",
    [
        "teacher",
        "student",
    ],
)
def test_validator_requires_user_email_for_user_assignments(
    assignment_type: str,
) -> None:
    result = validate_timetable_assignment_row(
        {
            "timetable_name": "Main Timetable",
            "academic_year": "2026/2027",
            "assignment_type": assignment_type,
        },
    )

    assert result.is_valid is False
    assert result.normalised_data is None
    assert result.errors


@pytest.mark.parametrize(
    "assignment_type",
    [
        "teacher",
        "student",
    ],
)
def test_validator_rejects_class_name_for_user_assignments(
    assignment_type: str,
) -> None:
    result = validate_timetable_assignment_row(
        {
            "timetable_name": "Main Timetable",
            "academic_year": "2026/2027",
            "assignment_type": assignment_type,
            "user_email": "user@example.com",
            "class_name": "Year 10 Physics",
        },
    )

    assert result.is_valid is False
    assert result.normalised_data is None


def test_validator_requires_class_name_for_class_assignment() -> None:
    result = validate_timetable_assignment_row(
        {
            "timetable_name": "Main Timetable",
            "academic_year": "2026/2027",
            "assignment_type": "class_group",
        },
    )

    assert result.is_valid is False
    assert result.normalised_data is None


def test_validator_rejects_user_email_for_class_assignment() -> None:
    result = validate_timetable_assignment_row(
        {
            "timetable_name": "Main Timetable",
            "academic_year": "2026/2027",
            "assignment_type": "class_group",
            "class_name": "Year 10 Physics",
            "user_email": "teacher@example.com",
        },
    )

    assert result.is_valid is False
    assert result.normalised_data is None


def test_validator_rejects_unknown_assignment_type() -> None:
    result = validate_timetable_assignment_row(
        {
            "timetable_name": "Main Timetable",
            "academic_year": "2026/2027",
            "assignment_type": "department",
            "user_email": "teacher@example.com",
        },
    )

    assert result.is_valid is False
    assert result.normalised_data is None


def test_validator_rejects_invalid_email() -> None:
    result = validate_timetable_assignment_row(
        {
            "timetable_name": "Main Timetable",
            "academic_year": "2026/2027",
            "assignment_type": "teacher",
            "user_email": "not-an-email",
        },
    )

    assert result.is_valid is False
    assert result.normalised_data is None


@pytest.mark.asyncio
async def test_processor_creates_teacher_assignment(
    db_session: AsyncSession,
    school_admin_user: User,
    teacher_user: User,
) -> None:
    school_id = school_admin_user.school_id

    assert school_id is not None
    assert teacher_user.school_id == school_id

    timetable = await create_timetable(
        db_session,
        school_id=school_id,
    )

    result = await process_timetable_assignment_row(
        db_session,
        {
            "timetable_name": timetable.name,
            "academic_year": timetable.academic_year,
            "assignment_type": "teacher",
            "user_email": teacher_user.email.upper(),
        },
        school_id,
    )

    await db_session.commit()

    assignment = await get_assignment_by_id(
        db_session,
        result.entity_id,
    )

    assert result.action == RowProcessingAction.CREATED
    assert result.message == (
        "Created teacher timetable assignment " f"for '{teacher_user.email}'."
    )

    assert assignment.school_id == school_id
    assert assignment.timetable_id == timetable.id
    assert assignment.assignment_type == TimetableAssignmentType.TEACHER
    assert assignment.user_id == teacher_user.id
    assert assignment.class_group_id is None


@pytest.mark.asyncio
async def test_processor_creates_student_assignment(
    db_session: AsyncSession,
    school_admin_user: User,
    student_user: User,
) -> None:
    school_id = school_admin_user.school_id

    assert school_id is not None
    assert student_user.school_id == school_id

    timetable = await create_timetable(
        db_session,
        school_id=school_id,
    )

    result = await process_timetable_assignment_row(
        db_session,
        {
            "timetable_name": timetable.name,
            "academic_year": timetable.academic_year,
            "assignment_type": "student",
            "user_email": student_user.email,
        },
        school_id,
    )

    await db_session.commit()

    assignment = await get_assignment_by_id(
        db_session,
        result.entity_id,
    )

    assert result.action == RowProcessingAction.CREATED
    assert assignment.assignment_type == TimetableAssignmentType.STUDENT
    assert assignment.user_id == student_user.id
    assert assignment.class_group_id is None


@pytest.mark.asyncio
async def test_processor_skips_existing_assignment(
    db_session: AsyncSession,
    school_admin_user: User,
    teacher_user: User,
) -> None:
    school_id = school_admin_user.school_id

    assert school_id is not None

    timetable = await create_timetable(
        db_session,
        school_id=school_id,
    )

    existing_assignment = TimetableAssignment(
        timetable_id=timetable.id,
        school_id=school_id,
        assignment_type=TimetableAssignmentType.TEACHER,
        user_id=teacher_user.id,
        class_group_id=None,
    )

    db_session.add(
        existing_assignment,
    )
    await db_session.commit()
    await db_session.refresh(
        existing_assignment,
    )

    result = await process_timetable_assignment_row(
        db_session,
        {
            "timetable_name": timetable.name,
            "academic_year": timetable.academic_year,
            "assignment_type": "teacher",
            "user_email": teacher_user.email,
        },
        school_id,
    )

    assert result.action == RowProcessingAction.SKIPPED
    assert result.entity_id == existing_assignment.id
    assert result.message == ("Timetable assignment already exists for 'teacher'.")


@pytest.mark.asyncio
async def test_processor_rejects_invalid_school_id(
    db_session: AsyncSession,
) -> None:
    with pytest.raises(
        ValueError,
        match="school_id must be a positive integer",
    ):
        await process_timetable_assignment_row(
            db_session,
            {
                "timetable_name": "Main Timetable",
                "academic_year": "2026/2027",
                "assignment_type": "teacher",
                "user_email": "teacher@example.com",
            },
            0,
        )


@pytest.mark.asyncio
async def test_processor_rejects_missing_timetable(
    db_session: AsyncSession,
    school_admin_user: User,
    teacher_user: User,
) -> None:
    school_id = school_admin_user.school_id

    assert school_id is not None

    with pytest.raises(
        ValueError,
        match="No timetable named",
    ):
        await process_timetable_assignment_row(
            db_session,
            {
                "timetable_name": "Missing Timetable",
                "academic_year": "2026/2027",
                "assignment_type": "teacher",
                "user_email": teacher_user.email,
            },
            school_id,
        )


@pytest.mark.asyncio
async def test_processor_rejects_missing_user(
    db_session: AsyncSession,
    school_admin_user: User,
) -> None:
    school_id = school_admin_user.school_id

    assert school_id is not None

    timetable = await create_timetable(
        db_session,
        school_id=school_id,
    )

    with pytest.raises(
        ValueError,
        match="No user with email",
    ):
        await process_timetable_assignment_row(
            db_session,
            {
                "timetable_name": timetable.name,
                "academic_year": timetable.academic_year,
                "assignment_type": "teacher",
                "user_email": "missing@example.com",
            },
            school_id,
        )


@pytest.mark.asyncio
async def test_processor_rejects_student_used_as_teacher(
    db_session: AsyncSession,
    school_admin_user: User,
    student_user: User,
) -> None:
    school_id = school_admin_user.school_id

    assert school_id is not None

    timetable = await create_timetable(
        db_session,
        school_id=school_id,
    )

    with pytest.raises(
        ValueError,
        match="is not registered as a teacher",
    ):
        await process_timetable_assignment_row(
            db_session,
            {
                "timetable_name": timetable.name,
                "academic_year": timetable.academic_year,
                "assignment_type": "teacher",
                "user_email": student_user.email,
            },
            school_id,
        )


@pytest.mark.asyncio
async def test_processor_rejects_teacher_used_as_student(
    db_session: AsyncSession,
    school_admin_user: User,
    teacher_user: User,
) -> None:
    school_id = school_admin_user.school_id

    assert school_id is not None

    timetable = await create_timetable(
        db_session,
        school_id=school_id,
    )

    with pytest.raises(
        ValueError,
        match="is not registered as a student",
    ):
        await process_timetable_assignment_row(
            db_session,
            {
                "timetable_name": timetable.name,
                "academic_year": timetable.academic_year,
                "assignment_type": "student",
                "user_email": teacher_user.email,
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

    timetable = await create_timetable(
        db_session,
        school_id=school_id,
    )

    with pytest.raises(
        ValueError,
        match="No class named",
    ):
        await process_timetable_assignment_row(
            db_session,
            {
                "timetable_name": timetable.name,
                "academic_year": timetable.academic_year,
                "assignment_type": "class_group",
                "class_name": "Missing Class",
            },
            school_id,
        )


@pytest.mark.asyncio
async def test_repository_finds_matching_assignment(
    db_session: AsyncSession,
    school_admin_user: User,
    teacher_user: User,
) -> None:
    school_id = school_admin_user.school_id

    assert school_id is not None

    timetable = await create_timetable(
        db_session,
        school_id=school_id,
    )

    assignment = TimetableAssignment(
        timetable_id=timetable.id,
        school_id=school_id,
        assignment_type=TimetableAssignmentType.TEACHER,
        user_id=teacher_user.id,
        class_group_id=None,
    )

    db_session.add(
        assignment,
    )
    await db_session.commit()
    await db_session.refresh(
        assignment,
    )

    matching_assignment = await TimetableRepository(
        db_session,
    ).find_matching_assignment(
        school_id=school_id,
        timetable_id=timetable.id,
        assignment_type=TimetableAssignmentType.TEACHER,
        user_id=teacher_user.id,
        class_group_id=None,
    )

    assert matching_assignment is not None
    assert matching_assignment.id == assignment.id


@pytest.mark.asyncio
async def test_processing_task_creates_teacher_assignment(
    db_session: AsyncSession,
    school_admin_user: User,
    teacher_user: User,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    register_import_handlers()

    school_id = school_admin_user.school_id

    assert school_id is not None

    timetable = await create_timetable(
        db_session,
        school_id=school_id,
    )

    task_session_maker = configure_task_session_maker(
        db_session,
        monkeypatch,
    )

    batch = build_assignment_batch(
        school_id=school_id,
        uploaded_by_id=school_admin_user.id,
        operation=ImportOperation.CREATE,
    )

    db_session.add(
        batch,
    )
    await db_session.flush()

    row = build_assignment_row(
        batch_id=batch.id,
        school_id=school_id,
        data={
            "timetable_name": timetable.name,
            "academic_year": timetable.academic_year,
            "assignment_type": "teacher",
            "user_email": teacher_user.email,
            "class_name": None,
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
        assert summary["failed_rows"] == 0

        assert processed_batch.status == ImportStatus.COMPLETED
        assert processed_batch.successful_rows == 1
        assert processed_batch.failed_rows == 0

        assert processed_row.status == ImportRowStatus.IMPORTED
        assert processed_row.attempt_count == 1
        assert processed_row.entity_type == "timetable_assignments"
        assert processed_row.created_entity_id is not None
        assert processed_row.processed_at is not None
        assert processed_row.error_message is not None
        assert "Created teacher timetable assignment" in (processed_row.error_message)

        assignment = await get_assignment_by_id(
            verification_db,
            processed_row.created_entity_id,
        )

        assert assignment.timetable_id == timetable.id
        assert assignment.user_id == teacher_user.id
        assert assignment.assignment_type == TimetableAssignmentType.TEACHER


@pytest.mark.asyncio
async def test_timetable_assignment_processing_enforces_school_isolation(
    db_session: AsyncSession,
    school_admin_user: User,
    teacher_user: User,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    school_id = school_admin_user.school_id

    assert school_id is not None

    timetable = await create_timetable(
        db_session,
        school_id=school_id,
    )

    configure_task_session_maker(
        db_session,
        monkeypatch,
    )

    batch = build_assignment_batch(
        school_id=school_id,
        uploaded_by_id=school_admin_user.id,
    )

    db_session.add(
        batch,
    )
    await db_session.flush()

    row = build_assignment_row(
        batch_id=batch.id,
        school_id=school_id,
        data={
            "timetable_name": timetable.name,
            "academic_year": timetable.academic_year,
            "assignment_type": "teacher",
            "user_email": teacher_user.email,
            "class_name": None,
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

    matching_assignment = await TimetableRepository(
        db_session,
    ).find_matching_assignment(
        school_id=school_id,
        timetable_id=timetable.id,
        assignment_type=TimetableAssignmentType.TEACHER,
        user_id=teacher_user.id,
        class_group_id=None,
    )

    assert matching_assignment is None
