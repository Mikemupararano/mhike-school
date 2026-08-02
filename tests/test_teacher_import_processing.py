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
from app.imports.processors.teachers import process_teacher_row
from app.imports.registry import (
    RowProcessingAction,
    get_import_handler,
)
from app.imports.validators.teachers import validate_teacher_row
from app.models.import_batch import (
    ImportBatch,
    ImportOperation,
    ImportRow,
    ImportRowStatus,
    ImportStatus,
)
from app.models.user import (
    User,
    UserRole,
    UserStatus,
)
from app.repositories.user import UserRepository

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


async def get_user_by_email(
    db: AsyncSession,
    *,
    email: str,
    school_id: int,
) -> User | None:
    result = await db.execute(
        select(User).where(
            User.email == email,
            User.school_id == school_id,
        ),
    )

    return result.scalar_one_or_none()


def build_teacher_batch(
    *,
    school_id: int,
    uploaded_by_id: int,
    operation: ImportOperation = ImportOperation.CREATE,
    total_rows: int = 1,
) -> ImportBatch:
    """
    Build a ready teacher-import batch with consistent counters.
    """

    return ImportBatch(
        school_id=school_id,
        uploaded_by_id=uploaded_by_id,
        import_type="teachers",
        operation=operation,
        status=ImportStatus.READY,
        original_filename="teachers.csv",
        total_rows=total_rows,
        validated_rows=total_rows,
        processed_rows=0,
        successful_rows=0,
        warning_rows=0,
        failed_rows=0,
        skipped_rows=0,
        current_stage="ready",
    )


def build_teacher_row(
    *,
    batch_id: int,
    school_id: int,
    row_number: int,
    data: dict[str, Any],
    status: ImportRowStatus = ImportRowStatus.VALID,
) -> ImportRow:
    """
    Build one staged teacher-import row.
    """

    return ImportRow(
        batch_id=batch_id,
        school_id=school_id,
        row_number=row_number,
        status=status,
        original_data=dict(data),
        normalised_data=({} if status == ImportRowStatus.INVALID else dict(data)),
        validation_errors=[],
        validation_warnings=[],
        attempt_count=0,
    )


async def test_teacher_import_handler_is_registered() -> None:
    register_import_handlers()

    handler = get_import_handler(
        "teachers",
    )

    assert handler.validator is validate_teacher_row
    assert handler.processor is process_teacher_row


async def test_teacher_validator_accepts_valid_row() -> None:
    result = validate_teacher_row(
        {
            "email": " teacher@example.com ",
            "first_name": " Alice ",
            "last_name": " Johnson ",
            "department": "Science",
        },
    )

    assert result.is_valid is True
    assert result.errors == []
    assert result.warnings == []

    assert result.normalised_data is not None
    assert result.normalised_data["email"] == "teacher@example.com"
    assert result.normalised_data["first_name"] == "Alice"
    assert result.normalised_data["last_name"] == "Johnson"

    # Extra fields remain available for future teacher-import expansion.
    assert result.normalised_data["department"] == "Science"


async def test_teacher_validator_rejects_invalid_row() -> None:
    result = validate_teacher_row(
        {
            "email": "not-an-email",
            "first_name": "",
            "last_name": "Teacher",
        },
    )

    assert result.is_valid is False
    assert result.normalised_data is None
    assert result.errors

    error_locations = {tuple(error["loc"]) for error in result.errors}

    assert ("email",) in error_locations
    assert ("first_name",) in error_locations


async def test_teacher_processor_creates_new_teacher(
    db_session: AsyncSession,
    school_admin_user: User,
) -> None:
    school_id = school_admin_user.school_id

    assert school_id is not None

    result = await process_teacher_row(
        db_session,
        {
            "email": " new.teacher@example.com ",
            "first_name": " New ",
            "last_name": " Teacher ",
        },
        school_id,
    )

    await db_session.commit()

    created_teacher = await UserRepository(
        db_session,
    ).get_by_email(
        email="new.teacher@example.com",
        school_id=school_id,
    )

    assert result.action == RowProcessingAction.CREATED
    assert result.entity_id is not None
    assert result.message == "Created teacher 'New Teacher'."

    assert created_teacher is not None
    assert created_teacher.id == result.entity_id
    assert created_teacher.email == "new.teacher@example.com"
    assert created_teacher.full_name == "New Teacher"
    assert created_teacher.role == UserRole.TEACHER
    assert created_teacher.status == UserStatus.ACTIVE
    assert created_teacher.is_active is True
    assert created_teacher.is_teacher is True
    assert created_teacher.is_student is False


async def test_teacher_processor_updates_existing_teacher(
    db_session: AsyncSession,
    teacher_user: User,
) -> None:
    school_id = teacher_user.school_id
    teacher_id = teacher_user.id
    teacher_email = teacher_user.email

    assert school_id is not None

    teacher_user.status = UserStatus.DEACTIVATED
    teacher_user.is_active = False

    await db_session.commit()

    result = await process_teacher_row(
        db_session,
        {
            "email": teacher_email.upper(),
            "first_name": "Updated",
            "last_name": "Teacher",
        },
        school_id,
    )

    await db_session.commit()
    await db_session.refresh(
        teacher_user,
    )

    assert result.action == RowProcessingAction.UPDATED
    assert result.entity_id == teacher_id
    assert result.message == "Updated teacher 'Updated Teacher'."

    assert teacher_user.id == teacher_id
    assert teacher_user.email == teacher_email.lower()
    assert teacher_user.full_name == "Updated Teacher"
    assert teacher_user.role == UserRole.TEACHER
    assert teacher_user.status == UserStatus.ACTIVE
    assert teacher_user.is_active is True
    assert teacher_user.is_teacher is True


async def test_teacher_processor_rejects_existing_non_teacher(
    db_session: AsyncSession,
    student_user: User,
) -> None:
    school_id = student_user.school_id
    student_id = student_user.id
    student_email = student_user.email
    original_name = student_user.full_name

    assert school_id is not None

    with pytest.raises(
        ValueError,
        match="A non-teacher user with email",
    ):
        await process_teacher_row(
            db_session,
            {
                "email": student_email,
                "first_name": "Incorrect",
                "last_name": "Conversion",
            },
            school_id,
        )

    existing_student = await UserRepository(
        db_session,
    ).get_by_email(
        email=student_email,
        school_id=school_id,
    )

    assert existing_student is not None
    assert existing_student.id == student_id
    assert existing_student.full_name == original_name
    assert existing_student.is_student is True
    assert existing_student.is_teacher is False


@pytest.mark.parametrize(
    "school_id",
    [
        0,
        -1,
        -999,
    ],
)
async def test_teacher_processor_rejects_invalid_school_id(
    db_session: AsyncSession,
    school_id: int,
) -> None:
    with pytest.raises(
        ValueError,
        match="school_id must be a positive integer",
    ):
        await process_teacher_row(
            db_session,
            {
                "email": "teacher@example.com",
                "first_name": "Test",
                "last_name": "Teacher",
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
                "email": None,
                "first_name": "Test",
                "last_name": "Teacher",
            },
            "Teacher import field 'email' is required.",
        ),
        (
            {
                "email": "teacher@example.com",
                "first_name": "   ",
                "last_name": "Teacher",
            },
            "Teacher import field 'first_name' cannot be blank.",
        ),
        (
            {
                "email": "teacher@example.com",
                "first_name": "Test",
                "last_name": None,
            },
            "Teacher import field 'last_name' is required.",
        ),
    ],
)
async def test_teacher_processor_defensively_rejects_malformed_rows(
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
        await process_teacher_row(
            db_session,
            row,
            1,
        )


async def test_processing_task_imports_valid_teacher_row(
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

    batch = build_teacher_batch(
        school_id=school_id,
        uploaded_by_id=school_admin_user.id,
    )

    db_session.add(batch)
    await db_session.flush()

    row_data = {
        "email": "batch.teacher@example.com",
        "first_name": "Batch",
        "last_name": "Teacher",
    }

    row = build_teacher_row(
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

        created_teacher = await get_user_by_email(
            verification_db,
            email="batch.teacher@example.com",
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
        assert processed_row.entity_type == "teachers"
        assert processed_row.created_entity_id is not None
        assert processed_row.processed_at is not None
        assert processed_row.error_message is not None
        assert "Created teacher" in processed_row.error_message

        assert created_teacher is not None
        assert created_teacher.id == processed_row.created_entity_id
        assert created_teacher.full_name == "Batch Teacher"
        assert created_teacher.role == UserRole.TEACHER
        assert created_teacher.status == UserStatus.ACTIVE
        assert created_teacher.is_active is True


async def test_processing_task_updates_existing_teacher(
    db_session: AsyncSession,
    teacher_user: User,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    register_import_handlers()

    school_id = teacher_user.school_id
    teacher_id = teacher_user.id
    teacher_email = teacher_user.email

    assert school_id is not None

    task_session_maker = configure_task_session_maker(
        db_session,
        monkeypatch,
    )

    batch = build_teacher_batch(
        school_id=school_id,
        uploaded_by_id=teacher_id,
        operation=ImportOperation.UPSERT,
    )

    db_session.add(batch)
    await db_session.flush()

    row_data = {
        "email": teacher_email,
        "first_name": "Batch",
        "last_name": "Updated",
    }

    row = build_teacher_row(
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

        updated_teacher = (
            await verification_db.execute(
                select(User).where(
                    User.id == teacher_id,
                ),
            )
        ).scalar_one()

        matching_teachers = (
            (
                await verification_db.execute(
                    select(User).where(
                        User.email == teacher_email,
                        User.school_id == school_id,
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
        assert processed_batch.processed_rows == 1
        assert processed_batch.successful_rows == 1
        assert processed_batch.failed_rows == 0

        assert processed_row.status == ImportRowStatus.UPDATED
        assert processed_row.attempt_count == 1
        assert processed_row.entity_type == "teachers"
        assert processed_row.created_entity_id == teacher_id
        assert processed_row.processed_at is not None
        assert processed_row.error_message is not None
        assert "Updated teacher" in processed_row.error_message

        assert updated_teacher.full_name == "Batch Updated"
        assert updated_teacher.role == UserRole.TEACHER
        assert updated_teacher.status == UserStatus.ACTIVE
        assert updated_teacher.is_active is True

        assert len(matching_teachers) == 1
        assert matching_teachers[0].id == teacher_id


async def test_processing_task_records_teacher_role_conflict(
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

    batch = build_teacher_batch(
        school_id=school_id,
        uploaded_by_id=school_admin_user.id,
        operation=ImportOperation.UPSERT,
    )

    db_session.add(batch)
    await db_session.flush()

    row_data = {
        "email": student_user.email,
        "first_name": "Role",
        "last_name": "Conflict",
    }

    row = build_teacher_row(
        batch_id=batch.id,
        school_id=school_id,
        row_number=2,
        data=row_data,
    )

    db_session.add(row)
    await db_session.commit()

    batch_id = batch.id
    row_id = row.id
    student_id = student_user.id

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

        unchanged_student = (
            await verification_db.execute(
                select(User).where(
                    User.id == student_id,
                ),
            )
        ).scalar_one()

        assert summary["status"] == (ImportStatus.COMPLETED_WITH_ERRORS.value)
        assert summary["processed_rows"] == 1
        assert summary["successful_rows"] == 0
        assert summary["failed_rows"] == 1

        assert processed_batch.status == (ImportStatus.COMPLETED_WITH_ERRORS)
        assert processed_batch.processed_rows == 1
        assert processed_batch.successful_rows == 0
        assert processed_batch.failed_rows == 1

        assert failed_row.status == ImportRowStatus.FAILED
        assert failed_row.attempt_count == 1
        assert failed_row.created_entity_id is None
        assert failed_row.processed_at is not None
        assert failed_row.error_message is not None
        assert "non-teacher user" in failed_row.error_message

        assert unchanged_student.id == student_id
        assert unchanged_student.is_student is True
        assert unchanged_student.is_teacher is False


async def test_teacher_processing_enforces_school_isolation(
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

    batch = build_teacher_batch(
        school_id=school_id,
        uploaded_by_id=school_admin_user.id,
    )

    db_session.add(batch)
    await db_session.flush()

    row = build_teacher_row(
        batch_id=batch.id,
        school_id=school_id,
        row_number=2,
        data={
            "email": "isolated.teacher@example.com",
            "first_name": "Isolated",
            "last_name": "Teacher",
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
