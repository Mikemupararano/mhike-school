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
from app.imports.processors.enrollments import process_enrollment_row
from app.imports.processors.parents import process_parent_row
from app.imports.processors.students import process_student_row
from app.imports.processors.teachers import process_teacher_row
from app.imports.registry import (
    RowProcessingAction,
    get_import_handler,
)
from app.models.class_group import ClassGroup
from app.models.enrollment import Enrollment
from app.models.import_batch import (
    ImportBatch,
    ImportOperation,
    ImportRow,
    ImportRowStatus,
    ImportStatus,
)
from app.models.user import User, UserRole, UserStatus
from app.models.user_role import UserRoleAssignment
from app.repositories.class_group import ClassGroupRepository
from app.repositories.enrollment import EnrollmentRepository
from app.repositories.parent_student import ParentStudentRepository
from app.repositories.user import UserRepository
from app.services.import_service import (
    ImportBatchStateError,
    retry_import_batch,
)

pytestmark = pytest.mark.asyncio


def create_task_session_maker(
    db_session: AsyncSession,
) -> async_sessionmaker[AsyncSession]:
    """Create a task-compatible session maker using the test database."""

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
    """Configure import tasks to use the current test database."""

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
    """Open a clean verification session after a background task runs."""

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


def build_import_batch(
    *,
    school_id: int,
    uploaded_by_id: int,
    import_type: str = "students",
    operation: ImportOperation = ImportOperation.CREATE,
    status: ImportStatus = ImportStatus.READY,
    original_filename: str = "students.csv",
    total_rows: int = 1,
    validated_rows: int | None = None,
    processed_rows: int = 0,
    successful_rows: int = 0,
    warning_rows: int = 0,
    failed_rows: int = 0,
    skipped_rows: int = 0,
    current_stage: str | None = "ready",
) -> ImportBatch:
    """Build a consistent import batch for processing tests."""

    resolved_validated_rows = total_rows if validated_rows is None else validated_rows

    return ImportBatch(
        school_id=school_id,
        uploaded_by_id=uploaded_by_id,
        import_type=import_type,
        operation=operation,
        status=status,
        original_filename=original_filename,
        total_rows=total_rows,
        validated_rows=resolved_validated_rows,
        processed_rows=processed_rows,
        successful_rows=successful_rows,
        warning_rows=warning_rows,
        failed_rows=failed_rows,
        skipped_rows=skipped_rows,
        current_stage=current_stage,
    )


def build_import_row(
    *,
    batch_id: int,
    school_id: int,
    row_number: int,
    data: dict[str, Any],
    status: ImportRowStatus = ImportRowStatus.VALID,
    attempt_count: int = 0,
    validation_errors: list[dict[str, Any]] | None = None,
    validation_warnings: list[dict[str, Any]] | None = None,
    error_message: str | None = None,
    created_entity_id: int | None = None,
) -> ImportRow:
    """Build a consistent import row for processing tests."""

    normalised_data = {} if status == ImportRowStatus.INVALID else dict(data)

    return ImportRow(
        batch_id=batch_id,
        school_id=school_id,
        row_number=row_number,
        status=status,
        original_data=dict(data),
        normalised_data=normalised_data,
        validation_errors=validation_errors or [],
        validation_warnings=validation_warnings or [],
        error_message=error_message,
        created_entity_id=created_entity_id,
        attempt_count=attempt_count,
    )


async def test_student_import_handler_is_registered() -> None:
    register_import_handlers()

    handler = get_import_handler(
        "students",
    )

    assert handler.validator is not None
    assert handler.processor is process_student_row


async def test_student_processor_creates_new_student(
    db_session: AsyncSession,
    school_admin_user: User,
) -> None:
    school_id = school_admin_user.school_id

    assert school_id is not None

    result = await process_student_row(
        db_session,
        {
            "email": "new.student@example.com",
            "first_name": "New",
            "last_name": "Student",
        },
        school_id,
    )

    await db_session.commit()

    repository = UserRepository(
        db_session,
    )

    created_student = await repository.get_by_email(
        email="new.student@example.com",
        school_id=school_id,
    )

    assert result.action == RowProcessingAction.CREATED
    assert result.entity_id is not None

    assert created_student is not None
    assert created_student.id == result.entity_id
    assert created_student.email == "new.student@example.com"
    assert created_student.full_name == "New Student"
    assert created_student.role == UserRole.STUDENT
    assert created_student.is_active is True


async def test_student_processor_updates_existing_student(
    db_session: AsyncSession,
    student_user: User,
) -> None:
    school_id = student_user.school_id

    assert school_id is not None

    result = await process_student_row(
        db_session,
        {
            "email": student_user.email,
            "first_name": "Updated",
            "last_name": "Student",
        },
        school_id,
    )

    await db_session.commit()
    await db_session.refresh(
        student_user,
    )

    assert result.action == RowProcessingAction.UPDATED
    assert result.entity_id == student_user.id

    assert student_user.full_name == "Updated Student"
    assert student_user.is_active is True


async def test_student_processor_rejects_existing_non_student(
    db_session: AsyncSession,
    teacher_user: User,
) -> None:
    school_id = teacher_user.school_id
    teacher_email = teacher_user.email
    teacher_id = teacher_user.id

    assert school_id is not None

    with pytest.raises(
        ValueError,
        match="A non-student user with email",
    ):
        await process_student_row(
            db_session,
            {
                "email": teacher_email,
                "first_name": "Incorrect",
                "last_name": "Conversion",
            },
            school_id,
        )

    existing_teacher = await UserRepository(
        db_session,
    ).get_by_email(
        email=teacher_email,
        school_id=school_id,
    )

    assert existing_teacher is not None
    assert existing_teacher.id == teacher_id
    assert existing_teacher.is_teacher is True
    assert existing_teacher.is_student is False


async def test_student_processor_creates_student_role_assignment(
    db_session: AsyncSession,
    school_admin_user: User,
) -> None:
    school_id = school_admin_user.school_id

    assert school_id is not None

    result = await process_student_row(
        db_session,
        {
            "email": "role.assignment@example.com",
            "first_name": "Role",
            "last_name": "Assignment",
        },
        school_id,
    )

    await db_session.commit()

    assignments = (
        (
            await db_session.execute(
                select(UserRoleAssignment).where(
                    UserRoleAssignment.user_id == result.entity_id,
                    UserRoleAssignment.role == UserRole.STUDENT,
                ),
            )
        )
        .scalars()
        .all()
    )

    assert result.action == RowProcessingAction.CREATED
    assert result.entity_id is not None
    assert len(assignments) == 1


async def test_student_processor_repairs_legacy_student_role_assignment(
    db_session: AsyncSession,
    school_admin_user: User,
) -> None:
    school_id = school_admin_user.school_id

    assert school_id is not None

    legacy_student = User(
        email="legacy.student@example.com",
        hashed_password=None,
        full_name="Legacy Student",
        role=UserRole.STUDENT,
        status=UserStatus.ACTIVE,
        is_active=True,
        school_id=school_id,
    )

    db_session.add(
        legacy_student,
    )

    await db_session.commit()

    result = await process_student_row(
        db_session,
        {
            "email": legacy_student.email,
            "first_name": "Repaired",
            "last_name": "Student",
        },
        school_id,
    )

    await db_session.commit()

    assignments = (
        (
            await db_session.execute(
                select(UserRoleAssignment).where(
                    UserRoleAssignment.user_id == legacy_student.id,
                    UserRoleAssignment.role == UserRole.STUDENT,
                ),
            )
        )
        .scalars()
        .all()
    )

    assert result.action == RowProcessingAction.UPDATED
    assert result.entity_id == legacy_student.id
    assert len(assignments) == 1
    assert result.message is not None
    assert "restored the student role assignment" in result.message


async def test_student_processor_does_not_duplicate_student_role_assignment(
    db_session: AsyncSession,
    student_user: User,
) -> None:
    school_id = student_user.school_id

    assert school_id is not None

    before_assignments = (
        (
            await db_session.execute(
                select(UserRoleAssignment).where(
                    UserRoleAssignment.user_id == student_user.id,
                    UserRoleAssignment.role == UserRole.STUDENT,
                ),
            )
        )
        .scalars()
        .all()
    )

    assert len(before_assignments) == 1

    result = await process_student_row(
        db_session,
        {
            "email": student_user.email,
            "first_name": "No",
            "last_name": "Duplicate",
        },
        school_id,
    )

    await db_session.commit()

    after_assignments = (
        (
            await db_session.execute(
                select(UserRoleAssignment).where(
                    UserRoleAssignment.user_id == student_user.id,
                    UserRoleAssignment.role == UserRole.STUDENT,
                ),
            )
        )
        .scalars()
        .all()
    )

    assert result.action == RowProcessingAction.UPDATED
    assert result.entity_id == student_user.id
    assert len(after_assignments) == 1


async def test_student_processor_preserves_other_existing_roles(
    db_session: AsyncSession,
    student_user: User,
) -> None:
    school_id = student_user.school_id

    assert school_id is not None

    db_session.add(
        UserRoleAssignment(
            user_id=student_user.id,
            role=UserRole.TEACHER,
        ),
    )

    await db_session.commit()

    result = await process_student_row(
        db_session,
        {
            "email": student_user.email,
            "first_name": "Multi",
            "last_name": "Role",
        },
        school_id,
    )

    await db_session.commit()

    assignments = (
        (
            await db_session.execute(
                select(UserRoleAssignment).where(
                    UserRoleAssignment.user_id == student_user.id,
                ),
            )
        )
        .scalars()
        .all()
    )

    roles = {assignment.role for assignment in assignments}

    assert result.action == RowProcessingAction.UPDATED
    assert result.entity_id == student_user.id
    assert roles == {
        UserRole.STUDENT,
        UserRole.TEACHER,
    }


async def test_processing_task_imports_valid_student_row(
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

    batch = build_import_batch(
        school_id=school_id,
        uploaded_by_id=school_admin_user.id,
        original_filename="students.csv",
    )

    db_session.add(
        batch,
    )
    await db_session.flush()

    row_data = {
        "email": "batch.student@example.com",
        "first_name": "Batch",
        "last_name": "Student",
    }

    row = build_import_row(
        batch_id=batch.id,
        school_id=school_id,
        row_number=2,
        data=row_data,
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

        created_student = await get_user_by_email(
            verification_db,
            email="batch.student@example.com",
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
        assert processed_row.entity_type == "students"
        assert processed_row.created_entity_id is not None
        assert processed_row.processed_at is not None

        assert created_student is not None
        assert created_student.id == processed_row.created_entity_id
        assert created_student.full_name == "Batch Student"
        assert created_student.role == UserRole.STUDENT


async def test_processing_task_updates_existing_student(
    db_session: AsyncSession,
    student_user: User,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    register_import_handlers()

    school_id = student_user.school_id
    student_id = student_user.id
    student_email = student_user.email

    assert school_id is not None

    task_session_maker = configure_task_session_maker(
        db_session,
        monkeypatch,
    )

    batch = build_import_batch(
        school_id=school_id,
        uploaded_by_id=student_id,
        operation=ImportOperation.UPSERT,
        original_filename="student-updates.csv",
    )

    db_session.add(
        batch,
    )
    await db_session.flush()

    row_data = {
        "email": student_email,
        "first_name": "Batch",
        "last_name": "Updated",
    }

    row = build_import_row(
        batch_id=batch.id,
        school_id=school_id,
        row_number=2,
        data=row_data,
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

        updated_student = (
            await verification_db.execute(
                select(User).where(
                    User.id == student_id,
                ),
            )
        ).scalar_one()

        matching_students = (
            (
                await verification_db.execute(
                    select(User).where(
                        User.email == student_email,
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
        assert processed_row.entity_type == "students"
        assert processed_row.created_entity_id == student_id
        assert processed_row.processed_at is not None

        assert updated_student.full_name == "Batch Updated"
        assert updated_student.role == UserRole.STUDENT
        assert updated_student.is_active is True

        assert len(matching_students) == 1
        assert matching_students[0].id == student_id


async def test_processing_task_records_failure_and_continues(
    db_session: AsyncSession,
    school_admin_user: User,
    teacher_user: User,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    register_import_handlers()

    school_id = school_admin_user.school_id
    teacher_email = teacher_user.email

    assert school_id is not None
    assert teacher_user.school_id == school_id

    task_session_maker = configure_task_session_maker(
        db_session,
        monkeypatch,
    )

    batch = build_import_batch(
        school_id=school_id,
        uploaded_by_id=school_admin_user.id,
        operation=ImportOperation.UPSERT,
        original_filename="mixed-students.csv",
        total_rows=2,
        validated_rows=2,
    )

    db_session.add(
        batch,
    )
    await db_session.flush()

    successful_data = {
        "email": "successful.student@example.com",
        "first_name": "Successful",
        "last_name": "Student",
    }

    successful_row = build_import_row(
        batch_id=batch.id,
        school_id=school_id,
        row_number=2,
        data=successful_data,
    )

    failed_data = {
        "email": teacher_email,
        "first_name": "Teacher",
        "last_name": "Conflict",
    }

    failed_row = build_import_row(
        batch_id=batch.id,
        school_id=school_id,
        row_number=3,
        data=failed_data,
    )

    db_session.add_all(
        [
            successful_row,
            failed_row,
        ],
    )

    await db_session.commit()

    batch_id = batch.id
    successful_row_id = successful_row.id
    failed_row_id = failed_row.id

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

        processed_successful_row = await get_row_by_id(
            verification_db,
            successful_row_id,
        )

        processed_failed_row = await get_row_by_id(
            verification_db,
            failed_row_id,
        )

        created_student = await get_user_by_email(
            verification_db,
            email="successful.student@example.com",
            school_id=school_id,
        )

        existing_teacher = await get_user_by_email(
            verification_db,
            email=teacher_email,
            school_id=school_id,
        )

        assert summary["status"] == ImportStatus.COMPLETED_WITH_ERRORS.value
        assert summary["processed_rows"] == 2
        assert summary["successful_rows"] == 1
        assert summary["imported_rows"] == 1
        assert summary["updated_rows"] == 0
        assert summary["failed_rows"] == 1

        assert processed_batch.status == ImportStatus.COMPLETED_WITH_ERRORS
        assert processed_batch.processed_rows == 2
        assert processed_batch.successful_rows == 1
        assert processed_batch.failed_rows == 1

        assert processed_successful_row.status == ImportRowStatus.IMPORTED
        assert processed_successful_row.attempt_count == 1
        assert processed_successful_row.created_entity_id is not None
        assert processed_successful_row.processed_at is not None

        assert processed_failed_row.status == ImportRowStatus.FAILED
        assert processed_failed_row.attempt_count == 1
        assert processed_failed_row.created_entity_id is None
        assert processed_failed_row.processed_at is not None
        assert processed_failed_row.error_message is not None
        assert "non-student user" in processed_failed_row.error_message

        assert created_student is not None
        assert created_student.full_name == "Successful Student"
        assert created_student.role == UserRole.STUDENT

        assert existing_teacher is not None
        assert existing_teacher.id == teacher_user.id
        assert existing_teacher.is_teacher is True
        assert existing_teacher.is_student is False


async def test_processing_task_preserves_preexisting_invalid_row(
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

    batch = build_import_batch(
        school_id=school_id,
        uploaded_by_id=school_admin_user.id,
        original_filename="students-with-invalid-row.csv",
        total_rows=2,
        validated_rows=2,
        failed_rows=1,
    )

    db_session.add(
        batch,
    )
    await db_session.flush()

    valid_data = {
        "email": "valid.student@example.com",
        "first_name": "Valid",
        "last_name": "Student",
    }

    valid_row = build_import_row(
        batch_id=batch.id,
        school_id=school_id,
        row_number=2,
        data=valid_data,
    )

    invalid_data = {
        "email": "not-an-email",
        "first_name": "",
        "last_name": "Invalid",
    }

    invalid_row = build_import_row(
        batch_id=batch.id,
        school_id=school_id,
        row_number=3,
        data=invalid_data,
        status=ImportRowStatus.INVALID,
        validation_errors=[
            {
                "type": "validation_error",
                "message": "Invalid student row.",
            },
        ],
        error_message="Row validation failed.",
    )

    db_session.add_all(
        [
            valid_row,
            invalid_row,
        ],
    )

    await db_session.commit()

    batch_id = batch.id
    valid_row_id = valid_row.id
    invalid_row_id = invalid_row.id

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

        processed_valid_row = await get_row_by_id(
            verification_db,
            valid_row_id,
        )

        preserved_invalid_row = await get_row_by_id(
            verification_db,
            invalid_row_id,
        )

        created_student = await get_user_by_email(
            verification_db,
            email="valid.student@example.com",
            school_id=school_id,
        )

        assert summary["status"] == ImportStatus.COMPLETED_WITH_ERRORS.value
        assert summary["processed_rows"] == 2
        assert summary["successful_rows"] == 1
        assert summary["imported_rows"] == 1
        assert summary["updated_rows"] == 0
        assert summary["invalid_rows"] == 1
        assert summary["failed_rows"] == 1

        assert processed_batch.status == ImportStatus.COMPLETED_WITH_ERRORS
        assert processed_batch.processed_rows == 2
        assert processed_batch.successful_rows == 1
        assert processed_batch.failed_rows == 1

        assert processed_valid_row.status == ImportRowStatus.IMPORTED
        assert processed_valid_row.attempt_count == 1
        assert processed_valid_row.created_entity_id is not None
        assert processed_valid_row.processed_at is not None

        assert preserved_invalid_row.status == ImportRowStatus.INVALID
        assert preserved_invalid_row.attempt_count == 0
        assert preserved_invalid_row.created_entity_id is None
        assert preserved_invalid_row.processed_at is None
        assert preserved_invalid_row.error_message == ("Row validation failed.")
        assert preserved_invalid_row.validation_errors

        assert created_student is not None
        assert created_student.full_name == "Valid Student"
        assert created_student.role == UserRole.STUDENT


@pytest.mark.parametrize(
    (
        "batch_status",
        "expected_reason",
    ),
    [
        (
            ImportStatus.CANCELLED,
            "Batch has been cancelled.",
        ),
        (
            ImportStatus.COMPLETED,
            "Batch has already finished.",
        ),
    ],
)
async def test_processing_task_skips_terminal_batch(
    db_session: AsyncSession,
    school_admin_user: User,
    monkeypatch: pytest.MonkeyPatch,
    batch_status: ImportStatus,
    expected_reason: str,
) -> None:
    register_import_handlers()

    school_id = school_admin_user.school_id

    assert school_id is not None

    task_session_maker = configure_task_session_maker(
        db_session,
        monkeypatch,
    )

    is_completed = batch_status == ImportStatus.COMPLETED

    batch = build_import_batch(
        school_id=school_id,
        uploaded_by_id=school_admin_user.id,
        status=batch_status,
        original_filename=(
            "completed-students.csv" if is_completed else "cancelled-students.csv"
        ),
        processed_rows=1 if is_completed else 0,
        successful_rows=1 if is_completed else 0,
        current_stage=batch_status.value,
    )

    db_session.add(
        batch,
    )
    await db_session.flush()

    row_data = {
        "email": (
            "already.completed@example.com"
            if is_completed
            else "cancelled.student@example.com"
        ),
        "first_name": ("Already" if is_completed else "Cancelled"),
        "last_name": ("Completed" if is_completed else "Student"),
    }

    row = build_import_row(
        batch_id=batch.id,
        school_id=school_id,
        row_number=2,
        data=row_data,
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
        unchanged_batch = await get_batch_by_id(
            verification_db,
            batch_id,
        )

        unchanged_row = await get_row_by_id(
            verification_db,
            row_id,
        )

        created_student = await get_user_by_email(
            verification_db,
            email=row_data["email"],
            school_id=school_id,
        )

        assert summary == {
            "batch_id": batch_id,
            "school_id": school_id,
            "status": batch_status.value,
            "skipped": True,
            "reason": expected_reason,
        }

        assert unchanged_batch.status == batch_status
        assert unchanged_batch.processed_rows == (1 if is_completed else 0)
        assert unchanged_batch.successful_rows == (1 if is_completed else 0)
        assert unchanged_batch.failed_rows == 0

        assert unchanged_row.status == ImportRowStatus.VALID
        assert unchanged_row.attempt_count == 0
        assert unchanged_row.created_entity_id is None
        assert unchanged_row.processed_at is None

        assert created_student is None


async def test_processing_task_marks_batch_failed_for_unknown_handler(
    db_session: AsyncSession,
    school_admin_user: User,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    school_id = school_admin_user.school_id

    assert school_id is not None

    task_session_maker = configure_task_session_maker(
        db_session,
        monkeypatch,
    )

    batch = build_import_batch(
        school_id=school_id,
        uploaded_by_id=school_admin_user.id,
        import_type="unknown_import_type",
        original_filename="unknown-import.csv",
    )

    db_session.add(
        batch,
    )
    await db_session.flush()

    row = build_import_row(
        batch_id=batch.id,
        school_id=school_id,
        row_number=2,
        data={
            "external_id": "12345",
        },
    )

    db_session.add(
        row,
    )
    await db_session.commit()

    batch_id = batch.id
    row_id = row.id

    with pytest.raises(
        KeyError,
        match="No import handler registered",
    ):
        await import_tasks._process_import_batch_task(
            batch_id=batch_id,
            school_id=school_id,
        )

    async with verification_session(
        task_session_maker,
    ) as verification_db:
        failed_batch = await get_batch_by_id(
            verification_db,
            batch_id,
        )

        unchanged_row = await get_row_by_id(
            verification_db,
            row_id,
        )

        assert failed_batch.status == ImportStatus.FAILED
        assert failed_batch.current_stage == "handler_resolution_failed"
        assert failed_batch.error_message is not None
        assert "No import handler registered" in failed_batch.error_message
        assert failed_batch.completed_at is not None

        assert unchanged_row.status == ImportRowStatus.VALID
        assert unchanged_row.attempt_count == 0
        assert unchanged_row.created_entity_id is None
        assert unchanged_row.processed_at is None


async def test_processing_task_raises_when_batch_not_found(
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    configure_task_session_maker(
        db_session,
        monkeypatch,
    )

    with pytest.raises(
        import_tasks.ImportBatchNotFoundError,
        match="Import batch 999999 was not found for school 1",
    ):
        await import_tasks._process_import_batch_task(
            batch_id=999999,
            school_id=1,
        )


async def test_retry_import_batch_resets_only_failed_rows(
    db_session: AsyncSession,
    school_admin_user: User,
) -> None:
    school_id = school_admin_user.school_id

    assert school_id is not None

    batch = build_import_batch(
        school_id=school_id,
        uploaded_by_id=school_admin_user.id,
        operation=ImportOperation.UPSERT,
        status=ImportStatus.COMPLETED_WITH_ERRORS,
        original_filename="retry-students.csv",
        total_rows=3,
        validated_rows=3,
        processed_rows=3,
        successful_rows=1,
        failed_rows=1,
        skipped_rows=1,
        current_stage="completed_with_errors",
    )

    db_session.add(
        batch,
    )
    await db_session.flush()

    successful_row = build_import_row(
        batch_id=batch.id,
        school_id=school_id,
        row_number=2,
        data={
            "email": "successful.retry@example.com",
            "first_name": "Successful",
            "last_name": "Retry",
        },
        status=ImportRowStatus.IMPORTED,
        attempt_count=1,
        created_entity_id=123,
    )

    successful_row.entity_type = "students"
    successful_row.processed_at = batch.created_at

    failed_row = build_import_row(
        batch_id=batch.id,
        school_id=school_id,
        row_number=3,
        data={
            "email": "failed.retry@example.com",
            "first_name": "Failed",
            "last_name": "Retry",
        },
        status=ImportRowStatus.FAILED,
        attempt_count=2,
        error_message="Temporary processing failure.",
    )

    failed_row.entity_type = "students"
    failed_row.processed_at = batch.created_at

    skipped_row = build_import_row(
        batch_id=batch.id,
        school_id=school_id,
        row_number=4,
        data={
            "email": "skipped.retry@example.com",
            "first_name": "Skipped",
            "last_name": "Retry",
        },
        status=ImportRowStatus.SKIPPED,
        attempt_count=1,
    )

    skipped_row.entity_type = "students"
    skipped_row.processed_at = batch.created_at

    db_session.add_all(
        [
            successful_row,
            failed_row,
            skipped_row,
        ],
    )

    await db_session.commit()

    batch_id = batch.id
    successful_row_id = successful_row.id
    failed_row_id = failed_row.id
    skipped_row_id = skipped_row.id

    retry_summary = await retry_import_batch(
        db_session,
        batch=batch,
    )

    assert retry_summary.batch_id == batch_id
    assert retry_summary.school_id == school_id
    assert retry_summary.retryable_rows == 1
    assert retry_summary.status == ImportStatus.READY

    db_session.expire_all()

    retried_batch = await get_batch_by_id(
        db_session,
        batch_id,
    )

    preserved_successful_row = await get_row_by_id(
        db_session,
        successful_row_id,
    )

    reset_failed_row = await get_row_by_id(
        db_session,
        failed_row_id,
    )

    preserved_skipped_row = await get_row_by_id(
        db_session,
        skipped_row_id,
    )

    assert retried_batch.status == ImportStatus.READY
    assert retried_batch.current_stage == "ready_for_retry"
    assert retried_batch.error_message is None
    assert retried_batch.completed_at is None
    assert retried_batch.cancelled_at is None
    assert retried_batch.queued_at is None
    assert retried_batch.started_at is None

    assert preserved_successful_row.status == ImportRowStatus.IMPORTED
    assert preserved_successful_row.attempt_count == 1
    assert preserved_successful_row.created_entity_id == 123
    assert preserved_successful_row.processed_at is not None

    assert reset_failed_row.status == ImportRowStatus.VALID
    assert reset_failed_row.attempt_count == 2
    assert reset_failed_row.created_entity_id is None
    assert reset_failed_row.error_message is None
    assert reset_failed_row.processed_at is None

    assert preserved_skipped_row.status == ImportRowStatus.SKIPPED
    assert preserved_skipped_row.attempt_count == 1
    assert preserved_skipped_row.processed_at is not None


async def test_retry_processing_reprocesses_failed_row_only(
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

    batch = build_import_batch(
        school_id=school_id,
        uploaded_by_id=school_admin_user.id,
        operation=ImportOperation.UPSERT,
        status=ImportStatus.COMPLETED_WITH_ERRORS,
        original_filename="retry-processing.csv",
        total_rows=2,
        validated_rows=2,
        processed_rows=2,
        successful_rows=1,
        failed_rows=1,
        current_stage="completed_with_errors",
    )

    db_session.add(
        batch,
    )
    await db_session.flush()

    successful_data = {
        "email": "already.imported@example.com",
        "first_name": "Already",
        "last_name": "Imported",
    }

    successful_row = build_import_row(
        batch_id=batch.id,
        school_id=school_id,
        row_number=2,
        data=successful_data,
        status=ImportRowStatus.IMPORTED,
        attempt_count=1,
        created_entity_id=987,
    )

    successful_row.entity_type = "students"
    successful_row.processed_at = batch.created_at

    retry_data = {
        "email": "retry.success@example.com",
        "first_name": "Retry",
        "last_name": "Success",
    }

    failed_row = build_import_row(
        batch_id=batch.id,
        school_id=school_id,
        row_number=3,
        data=retry_data,
        status=ImportRowStatus.FAILED,
        attempt_count=1,
        error_message="Temporary failure.",
    )

    failed_row.entity_type = "students"
    failed_row.processed_at = batch.created_at

    db_session.add_all(
        [
            successful_row,
            failed_row,
        ],
    )

    await db_session.commit()

    batch_id = batch.id
    successful_row_id = successful_row.id
    failed_row_id = failed_row.id

    await retry_import_batch(
        db_session,
        batch=batch,
    )

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

        preserved_successful_row = await get_row_by_id(
            verification_db,
            successful_row_id,
        )

        retried_row = await get_row_by_id(
            verification_db,
            failed_row_id,
        )

        created_student = await get_user_by_email(
            verification_db,
            email="retry.success@example.com",
            school_id=school_id,
        )

        duplicate_existing_student = await get_user_by_email(
            verification_db,
            email="already.imported@example.com",
            school_id=school_id,
        )

        assert summary["status"] == ImportStatus.COMPLETED.value
        assert summary["successful_rows"] == 2
        assert summary["failed_rows"] == 0

        assert processed_batch.status == ImportStatus.COMPLETED
        assert processed_batch.successful_rows == 2
        assert processed_batch.failed_rows == 0
        assert processed_batch.processed_rows == 2

        assert preserved_successful_row.status == ImportRowStatus.IMPORTED
        assert preserved_successful_row.attempt_count == 1
        assert preserved_successful_row.created_entity_id == 987

        assert retried_row.status == ImportRowStatus.IMPORTED
        assert retried_row.attempt_count == 2
        assert retried_row.created_entity_id is not None
        assert retried_row.error_message is not None
        assert "Created student" in retried_row.error_message
        assert retried_row.processed_at is not None

        assert created_student is not None
        assert created_student.full_name == "Retry Success"

        assert duplicate_existing_student is None


async def test_retry_import_batch_rejects_batch_without_failed_rows(
    db_session: AsyncSession,
    school_admin_user: User,
) -> None:
    school_id = school_admin_user.school_id

    assert school_id is not None

    batch = build_import_batch(
        school_id=school_id,
        uploaded_by_id=school_admin_user.id,
        status=ImportStatus.COMPLETED,
        original_filename="completed-without-failures.csv",
        processed_rows=1,
        successful_rows=1,
        failed_rows=0,
        current_stage="completed",
    )

    db_session.add(
        batch,
    )
    await db_session.commit()

    with pytest.raises(
        ImportBatchStateError,
        match="does not allow retry",
    ):
        await retry_import_batch(
            db_session,
            batch=batch,
        )


async def test_retry_import_batch_rejects_archived_batch(
    db_session: AsyncSession,
    school_admin_user: User,
) -> None:
    school_id = school_admin_user.school_id

    assert school_id is not None

    batch = build_import_batch(
        school_id=school_id,
        uploaded_by_id=school_admin_user.id,
        status=ImportStatus.COMPLETED_WITH_ERRORS,
        original_filename="archived-retry.csv",
        processed_rows=1,
        failed_rows=1,
        current_stage="completed_with_errors",
    )

    batch.is_archived = True

    db_session.add(
        batch,
    )
    await db_session.commit()

    with pytest.raises(
        ImportBatchStateError,
        match="Archived import batches cannot be retried",
    ):
        await retry_import_batch(
            db_session,
            batch=batch,
        )


async def test_processing_task_enforces_school_isolation(
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

    batch = build_import_batch(
        school_id=school_id,
        uploaded_by_id=school_admin_user.id,
        original_filename="school-isolation.csv",
    )

    db_session.add(
        batch,
    )
    await db_session.flush()

    row = build_import_row(
        batch_id=batch.id,
        school_id=school_id,
        row_number=2,
        data={
            "email": "isolated.student@example.com",
            "first_name": "Isolated",
            "last_name": "Student",
        },
    )

    db_session.add(
        row,
    )
    await db_session.commit()

    with pytest.raises(
        import_tasks.ImportBatchNotFoundError,
        match=(
            rf"Import batch {batch.id} was not found " rf"for school {school_id + 999}"
        ),
    ):
        await import_tasks._process_import_batch_task(
            batch_id=batch.id,
            school_id=school_id + 999,
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


async def test_teacher_import_handler_is_registered() -> None:
    register_import_handlers()

    handler = get_import_handler(
        "teachers",
    )

    assert handler.validator is not None
    assert handler.processor is process_teacher_row


async def test_teacher_processor_creates_new_teacher(
    db_session: AsyncSession,
    school_admin_user: User,
) -> None:
    school_id = school_admin_user.school_id

    assert school_id is not None

    result = await process_teacher_row(
        db_session,
        {
            "email": "new.teacher@example.com",
            "first_name": "New",
            "last_name": "Teacher",
        },
        school_id,
    )

    await db_session.commit()

    teacher = await UserRepository(
        db_session,
    ).get_by_email(
        email="new.teacher@example.com",
        school_id=school_id,
    )

    assert result.action == RowProcessingAction.CREATED
    assert result.entity_id is not None

    assert teacher is not None
    assert teacher.id == result.entity_id
    assert teacher.full_name == "New Teacher"
    assert teacher.role == UserRole.TEACHER
    assert teacher.status == UserStatus.ACTIVE
    assert teacher.is_active is True
    assert teacher.is_teacher is True

    assignments = (
        (
            await db_session.execute(
                select(UserRoleAssignment).where(
                    UserRoleAssignment.user_id == teacher.id,
                    UserRoleAssignment.role == UserRole.TEACHER,
                ),
            )
        )
        .scalars()
        .all()
    )

    assert len(assignments) == 1


async def test_teacher_processor_updates_existing_teacher_without_duplicate_role(
    db_session: AsyncSession,
    teacher_user: User,
) -> None:
    school_id = teacher_user.school_id

    assert school_id is not None

    result = await process_teacher_row(
        db_session,
        {
            "email": teacher_user.email,
            "first_name": "Updated",
            "last_name": "Teacher",
        },
        school_id,
    )

    await db_session.commit()
    await db_session.refresh(
        teacher_user,
    )

    assignments = (
        (
            await db_session.execute(
                select(UserRoleAssignment).where(
                    UserRoleAssignment.user_id == teacher_user.id,
                    UserRoleAssignment.role == UserRole.TEACHER,
                ),
            )
        )
        .scalars()
        .all()
    )

    assert result.action == RowProcessingAction.UPDATED
    assert result.entity_id == teacher_user.id

    assert teacher_user.full_name == "Updated Teacher"
    assert teacher_user.status == UserStatus.ACTIVE
    assert teacher_user.is_active is True
    assert teacher_user.is_teacher is True

    assert len(assignments) == 1


async def test_teacher_processor_rejects_existing_non_teacher(
    db_session: AsyncSession,
    student_user: User,
) -> None:
    school_id = student_user.school_id

    assert school_id is not None

    with pytest.raises(
        ValueError,
        match="A non-teacher user with email",
    ):
        await process_teacher_row(
            db_session,
            {
                "email": student_user.email,
                "first_name": "Incorrect",
                "last_name": "Conversion",
            },
            school_id,
        )

    preserved_student = await UserRepository(
        db_session,
    ).get_by_email(
        email=student_user.email,
        school_id=school_id,
    )

    assert preserved_student is not None
    assert preserved_student.id == student_user.id
    assert preserved_student.is_student is True
    assert preserved_student.is_teacher is False


async def test_teacher_processor_repairs_legacy_role_and_preserves_other_roles(
    db_session: AsyncSession,
    school_admin_user: User,
) -> None:
    school_id = school_admin_user.school_id

    assert school_id is not None

    legacy_teacher = User(
        email="legacy.teacher@example.com",
        hashed_password=None,
        full_name="Legacy Teacher",
        role=UserRole.TEACHER,
        status=UserStatus.ACTIVE,
        is_active=True,
        school_id=school_id,
    )

    db_session.add(
        legacy_teacher,
    )
    await db_session.flush()

    db_session.add(
        UserRoleAssignment(
            user_id=legacy_teacher.id,
            role=UserRole.STUDENT,
        ),
    )

    await db_session.commit()

    result = await process_teacher_row(
        db_session,
        {
            "email": legacy_teacher.email,
            "first_name": "Repaired",
            "last_name": "Teacher",
        },
        school_id,
    )

    await db_session.commit()

    assignments = (
        (
            await db_session.execute(
                select(UserRoleAssignment).where(
                    UserRoleAssignment.user_id == legacy_teacher.id,
                ),
            )
        )
        .scalars()
        .all()
    )

    roles = {assignment.role for assignment in assignments}

    assert result.action == RowProcessingAction.UPDATED
    assert result.entity_id == legacy_teacher.id
    assert result.message is not None
    assert "restored the teacher role assignment" in result.message

    assert roles == {
        UserRole.STUDENT,
        UserRole.TEACHER,
    }


@pytest.mark.parametrize(
    "invalid_school_id",
    [
        0,
        -1,
        True,
    ],
)
async def test_teacher_processor_rejects_invalid_school_id(
    db_session: AsyncSession,
    invalid_school_id: int,
) -> None:
    with pytest.raises(
        ValueError,
        match="school_id must be a positive integer",
    ):
        await process_teacher_row(
            db_session,
            {
                "email": "invalid.school@example.com",
                "first_name": "Invalid",
                "last_name": "School",
            },
            invalid_school_id,
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

    batch = build_import_batch(
        school_id=school_id,
        uploaded_by_id=school_admin_user.id,
        import_type="teachers",
        original_filename="teachers.csv",
    )

    db_session.add(
        batch,
    )
    await db_session.flush()

    row = build_import_row(
        batch_id=batch.id,
        school_id=school_id,
        row_number=2,
        data={
            "email": "batch.teacher@example.com",
            "first_name": "Batch",
            "last_name": "Teacher",
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

        teacher = await get_user_by_email(
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

        assert teacher is not None
        assert teacher.id == processed_row.created_entity_id
        assert teacher.full_name == "Batch Teacher"
        assert teacher.role == UserRole.TEACHER
        assert teacher.is_teacher is True


async def test_parent_import_handler_is_registered() -> None:
    register_import_handlers()

    handler = get_import_handler(
        "parents",
    )

    assert handler.validator is not None
    assert handler.processor is process_parent_row


async def test_parent_processor_creates_parent_and_student_link(
    db_session: AsyncSession,
    school_admin_user: User,
    student_user: User,
) -> None:
    school_id = school_admin_user.school_id

    assert school_id is not None
    assert student_user.school_id == school_id

    result = await process_parent_row(
        db_session,
        {
            "email": "new.parent@example.com",
            "first_name": "New",
            "last_name": "Parent",
            "student_email": student_user.email,
            "phone": "+44 7700 900123",
        },
        school_id,
    )

    await db_session.commit()

    parent = await UserRepository(
        db_session,
    ).get_by_email(
        email="new.parent@example.com",
        school_id=school_id,
    )

    assert result.action == RowProcessingAction.CREATED
    assert result.entity_id is not None
    assert result.message is not None
    assert "Created parent" in result.message

    assert parent is not None
    assert parent.full_name == "New Parent"
    assert parent.role == UserRole.PARENT
    assert parent.status == UserStatus.ACTIVE
    assert parent.is_active is True
    assert parent.has_role(
        UserRole.PARENT,
    )

    link = await ParentStudentRepository(
        db_session,
    ).get_link_in_school(
        parent_id=parent.id,
        student_id=student_user.id,
        school_id=school_id,
        include_relationships=False,
    )

    assert link is not None
    assert link.id == result.entity_id


async def test_parent_processor_updates_existing_parent_and_creates_link(
    db_session: AsyncSession,
    parent_user: User,
    student_user: User,
) -> None:
    school_id = parent_user.school_id

    assert school_id is not None
    assert student_user.school_id == school_id

    result = await process_parent_row(
        db_session,
        {
            "email": parent_user.email,
            "first_name": "Updated",
            "last_name": "Parent",
            "student_email": student_user.email,
        },
        school_id,
    )

    await db_session.commit()
    await db_session.refresh(
        parent_user,
    )

    assert result.action == RowProcessingAction.UPDATED
    assert result.entity_id is not None
    assert parent_user.full_name == "Updated Parent"
    assert parent_user.status == UserStatus.ACTIVE
    assert parent_user.is_active is True
    assert parent_user.has_role(
        UserRole.PARENT,
    )

    link = await ParentStudentRepository(
        db_session,
    ).get_link_in_school(
        parent_id=parent_user.id,
        student_id=student_user.id,
        school_id=school_id,
        include_relationships=False,
    )

    assert link is not None
    assert link.id == result.entity_id


async def test_parent_processor_skips_duplicate_parent_student_link(
    db_session: AsyncSession,
    parent_user: User,
    student_user: User,
) -> None:
    school_id = parent_user.school_id

    assert school_id is not None
    assert student_user.school_id == school_id

    first_result = await process_parent_row(
        db_session,
        {
            "email": parent_user.email,
            "first_name": "Existing",
            "last_name": "Parent",
            "student_email": student_user.email,
        },
        school_id,
    )

    await db_session.commit()

    second_result = await process_parent_row(
        db_session,
        {
            "email": parent_user.email,
            "first_name": "Existing",
            "last_name": "Parent",
            "student_email": student_user.email,
        },
        school_id,
    )

    await db_session.commit()

    assert first_result.action == RowProcessingAction.UPDATED
    assert second_result.action == RowProcessingAction.SKIPPED
    assert second_result.entity_id == first_result.entity_id
    assert second_result.message is not None
    assert "already linked" in second_result.message


async def test_parent_processor_rejects_existing_non_parent(
    db_session: AsyncSession,
    teacher_user: User,
    student_user: User,
) -> None:
    school_id = teacher_user.school_id

    assert school_id is not None
    assert student_user.school_id == school_id

    with pytest.raises(
        ValueError,
        match="A non-parent user with email",
    ):
        await process_parent_row(
            db_session,
            {
                "email": teacher_user.email,
                "first_name": "Incorrect",
                "last_name": "Conversion",
                "student_email": student_user.email,
            },
            school_id,
        )

    preserved_teacher = await UserRepository(
        db_session,
    ).get_by_email(
        email=teacher_user.email,
        school_id=school_id,
    )

    assert preserved_teacher is not None
    assert preserved_teacher.id == teacher_user.id
    assert preserved_teacher.has_role(
        UserRole.TEACHER,
    )
    assert not preserved_teacher.has_role(
        UserRole.PARENT,
    )


async def test_parent_processor_rejects_missing_student(
    db_session: AsyncSession,
    school_admin_user: User,
) -> None:
    school_id = school_admin_user.school_id

    assert school_id is not None

    with pytest.raises(
        ValueError,
        match="No student with email",
    ):
        await process_parent_row(
            db_session,
            {
                "email": "missing.student.parent@example.com",
                "first_name": "Missing",
                "last_name": "Student",
                "student_email": "not.found.student@example.com",
            },
            school_id,
        )


async def test_parent_processor_repairs_legacy_roles_and_preserves_other_roles(
    db_session: AsyncSession,
    school_admin_user: User,
) -> None:
    school_id = school_admin_user.school_id

    assert school_id is not None

    legacy_student = User(
        email="legacy.linked.student@example.com",
        hashed_password=None,
        full_name="Legacy Linked Student",
        role=UserRole.STUDENT,
        status=UserStatus.ACTIVE,
        is_active=True,
        school_id=school_id,
    )

    legacy_parent = User(
        email="legacy.parent@example.com",
        hashed_password=None,
        full_name="Legacy Parent",
        role=UserRole.PARENT,
        status=UserStatus.ACTIVE,
        is_active=True,
        school_id=school_id,
    )

    db_session.add_all(
        [
            legacy_student,
            legacy_parent,
        ],
    )
    await db_session.flush()

    db_session.add(
        UserRoleAssignment(
            user_id=legacy_parent.id,
            role=UserRole.TEACHER,
        ),
    )

    await db_session.commit()

    result = await process_parent_row(
        db_session,
        {
            "email": legacy_parent.email,
            "first_name": "Repaired",
            "last_name": "Parent",
            "student_email": legacy_student.email,
        },
        school_id,
    )

    await db_session.commit()

    parent_assignments = (
        (
            await db_session.execute(
                select(UserRoleAssignment).where(
                    UserRoleAssignment.user_id == legacy_parent.id,
                ),
            )
        )
        .scalars()
        .all()
    )

    student_assignments = (
        (
            await db_session.execute(
                select(UserRoleAssignment).where(
                    UserRoleAssignment.user_id == legacy_student.id,
                ),
            )
        )
        .scalars()
        .all()
    )

    parent_roles = {assignment.role for assignment in parent_assignments}

    student_roles = {assignment.role for assignment in student_assignments}

    assert result.action == RowProcessingAction.UPDATED
    assert result.message is not None
    assert "restored the parent role assignment" in result.message

    assert parent_roles == {
        UserRole.PARENT,
        UserRole.TEACHER,
    }

    assert student_roles == {
        UserRole.STUDENT,
    }


@pytest.mark.parametrize(
    "invalid_school_id",
    [
        0,
        -1,
        True,
    ],
)
async def test_parent_processor_rejects_invalid_school_id(
    db_session: AsyncSession,
    invalid_school_id: int,
) -> None:
    with pytest.raises(
        ValueError,
        match="school_id must be a positive integer",
    ):
        await process_parent_row(
            db_session,
            {
                "email": "invalid.school.parent@example.com",
                "first_name": "Invalid",
                "last_name": "School",
                "student_email": "student@example.com",
            },
            invalid_school_id,
        )


async def test_parent_processor_rejects_phone_over_maximum_length(
    db_session: AsyncSession,
    school_admin_user: User,
    student_user: User,
) -> None:
    school_id = school_admin_user.school_id

    assert school_id is not None
    assert student_user.school_id == school_id

    with pytest.raises(
        ValueError,
        match="phone.*cannot exceed 50 characters",
    ):
        await process_parent_row(
            db_session,
            {
                "email": "long.phone.parent@example.com",
                "first_name": "Long",
                "last_name": "Phone",
                "student_email": student_user.email,
                "phone": "1" * 51,
            },
            school_id,
        )


async def test_processing_task_imports_valid_parent_row(
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

    batch = build_import_batch(
        school_id=school_id,
        uploaded_by_id=school_admin_user.id,
        import_type="parents",
        original_filename="parents.csv",
    )

    db_session.add(
        batch,
    )
    await db_session.flush()

    row = build_import_row(
        batch_id=batch.id,
        school_id=school_id,
        row_number=2,
        data={
            "email": "batch.parent@example.com",
            "first_name": "Batch",
            "last_name": "Parent",
            "student_email": student_user.email,
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

        parent = await get_user_by_email(
            verification_db,
            email="batch.parent@example.com",
            school_id=school_id,
        )

        assert parent is not None

        link = await ParentStudentRepository(
            verification_db,
        ).get_link_in_school(
            parent_id=parent.id,
            student_id=student_user.id,
            school_id=school_id,
            include_relationships=False,
        )

        assert summary["status"] == ImportStatus.COMPLETED.value
        assert summary["processed_rows"] == 1
        assert summary["successful_rows"] == 1
        assert summary["imported_rows"] == 1
        assert summary["updated_rows"] == 0
        assert summary["skipped_rows"] == 0
        assert summary["failed_rows"] == 0

        assert processed_batch.status == ImportStatus.COMPLETED
        assert processed_batch.processed_rows == 1
        assert processed_batch.successful_rows == 1
        assert processed_batch.failed_rows == 0
        assert processed_batch.skipped_rows == 0

        assert processed_row.status == ImportRowStatus.IMPORTED
        assert processed_row.attempt_count == 1
        assert processed_row.entity_type == "parents"
        assert processed_row.created_entity_id is not None
        assert processed_row.processed_at is not None

        assert parent.full_name == "Batch Parent"
        assert parent.role == UserRole.PARENT
        assert parent.has_role(
            UserRole.PARENT,
        )

        assert link is not None
        assert link.id == processed_row.created_entity_id


async def test_class_import_handler_is_registered() -> None:
    register_import_handlers()

    handler = get_import_handler(
        "classes",
    )

    assert handler.validator is not None
    assert handler.processor is process_class_row


async def test_class_processor_creates_class_without_teacher(
    db_session: AsyncSession,
    school_admin_user: User,
) -> None:
    school_id = school_admin_user.school_id

    assert school_id is not None

    result = await process_class_row(
        db_session,
        {
            "name": "Year 7 Science",
        },
        school_id,
    )

    await db_session.commit()

    class_group = await ClassGroupRepository(
        db_session,
    ).get_by_name_and_school(
        name="Year 7 Science",
        school_id=school_id,
        include_relationships=False,
    )

    assert result.action == RowProcessingAction.CREATED
    assert result.entity_id is not None
    assert result.message == "Created class 'Year 7 Science'."

    assert class_group is not None
    assert class_group.id == result.entity_id
    assert class_group.name == "Year 7 Science"
    assert class_group.school_id == school_id
    assert class_group.teacher_id is None


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
            "name": "Year 8 Physics",
            "teacher_email": teacher_user.email,
        },
        school_id,
    )

    await db_session.commit()

    class_group = await ClassGroupRepository(
        db_session,
    ).get_by_name_and_school(
        name="Year 8 Physics",
        school_id=school_id,
        include_relationships=False,
    )

    assert result.action == RowProcessingAction.CREATED
    assert result.entity_id is not None

    assert class_group is not None
    assert class_group.id == result.entity_id
    assert class_group.name == "Year 8 Physics"
    assert class_group.school_id == school_id
    assert class_group.teacher_id == teacher_user.id


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

    class_group = await ClassGroupRepository(
        db_session,
    ).create(
        class_group,
    )

    await db_session.commit()

    result = await process_class_row(
        db_session,
        {
            "name": "Year 9 Chemistry",
            "teacher_email": teacher_user.email,
        },
        school_id,
    )

    await db_session.commit()
    await db_session.refresh(
        class_group,
    )

    assert result.action == RowProcessingAction.UPDATED
    assert result.entity_id == class_group.id
    assert result.message == "Updated class 'Year 9 Chemistry'."

    assert class_group.name == "Year 9 Chemistry"
    assert class_group.school_id == school_id
    assert class_group.teacher_id == teacher_user.id


async def test_class_processor_removes_existing_teacher_assignment(
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

    class_group = await ClassGroupRepository(
        db_session,
    ).create(
        class_group,
    )

    await db_session.commit()

    result = await process_class_row(
        db_session,
        {
            "name": "Year 10 Biology",
        },
        school_id,
    )

    await db_session.commit()
    await db_session.refresh(
        class_group,
    )

    assert result.action == RowProcessingAction.UPDATED
    assert result.entity_id == class_group.id
    assert class_group.teacher_id is None


async def test_class_processor_rejects_missing_teacher(
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
                "name": "Year 11 Physics",
                "teacher_email": "missing.teacher@example.com",
            },
            school_id,
        )

    class_group = await ClassGroupRepository(
        db_session,
    ).get_by_name_and_school(
        name="Year 11 Physics",
        school_id=school_id,
        include_relationships=False,
    )

    assert class_group is None


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
                "name": "Year 12 Mathematics",
                "teacher_email": student_user.email,
            },
            school_id,
        )

    class_group = await ClassGroupRepository(
        db_session,
    ).get_by_name_and_school(
        name="Year 12 Mathematics",
        school_id=school_id,
        include_relationships=False,
    )

    assert class_group is None


@pytest.mark.parametrize(
    "invalid_school_id",
    [
        0,
        -1,
        True,
    ],
)
async def test_class_processor_rejects_invalid_school_id(
    db_session: AsyncSession,
    invalid_school_id: int,
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
            invalid_school_id,
        )


async def test_class_processor_rejects_overlong_name(
    db_session: AsyncSession,
    school_admin_user: User,
) -> None:
    school_id = school_admin_user.school_id

    assert school_id is not None

    with pytest.raises(
        ValueError,
        match="name.*cannot exceed 255 characters",
    ):
        await process_class_row(
            db_session,
            {
                "name": "C" * 256,
            },
            school_id,
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

    batch = build_import_batch(
        school_id=school_id,
        uploaded_by_id=school_admin_user.id,
        import_type="classes",
        original_filename="classes.csv",
    )

    db_session.add(
        batch,
    )
    await db_session.flush()

    row = build_import_row(
        batch_id=batch.id,
        school_id=school_id,
        row_number=2,
        data={
            "name": "Browser Science Class",
            "teacher_email": teacher_user.email,
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

        class_group = await ClassGroupRepository(
            verification_db,
        ).get_by_name_and_school(
            name="Browser Science Class",
            school_id=school_id,
            include_relationships=False,
        )

        assert summary["status"] == ImportStatus.COMPLETED.value
        assert summary["processed_rows"] == 1
        assert summary["successful_rows"] == 1
        assert summary["imported_rows"] == 1
        assert summary["updated_rows"] == 0
        assert summary["skipped_rows"] == 0
        assert summary["failed_rows"] == 0

        assert processed_batch.status == ImportStatus.COMPLETED
        assert processed_batch.processed_rows == 1
        assert processed_batch.successful_rows == 1
        assert processed_batch.failed_rows == 0
        assert processed_batch.skipped_rows == 0

        assert processed_row.status == ImportRowStatus.IMPORTED
        assert processed_row.attempt_count == 1
        assert processed_row.entity_type == "classes"
        assert processed_row.created_entity_id is not None
        assert processed_row.processed_at is not None
        assert processed_row.error_message is not None
        assert "Created class" in processed_row.error_message

        assert class_group is not None
        assert class_group.id == processed_row.created_entity_id
        assert class_group.name == "Browser Science Class"
        assert class_group.school_id == school_id
        assert class_group.teacher_id == teacher_user.id


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
        name="Existing Import Class",
        school_id=school_id,
        teacher_id=None,
    )

    class_group = await ClassGroupRepository(
        db_session,
    ).create(
        class_group,
    )

    batch = build_import_batch(
        school_id=school_id,
        uploaded_by_id=school_admin_user.id,
        import_type="classes",
        operation=ImportOperation.UPSERT,
        original_filename="class-updates.csv",
    )

    db_session.add(
        batch,
    )
    await db_session.flush()

    row = build_import_row(
        batch_id=batch.id,
        school_id=school_id,
        row_number=2,
        data={
            "name": class_group.name,
            "teacher_email": teacher_user.email,
        },
    )

    db_session.add(
        row,
    )
    await db_session.commit()

    batch_id = batch.id
    row_id = row.id
    class_id = class_group.id

    task_session_maker = configure_task_session_maker(
        db_session,
        monkeypatch,
    )

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

        updated_class = await ClassGroupRepository(
            verification_db,
        ).get_by_id_and_school(
            class_id=class_id,
            school_id=school_id,
            include_relationships=False,
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
        assert processed_row.entity_type == "classes"
        assert processed_row.created_entity_id == class_id
        assert processed_row.processed_at is not None
        assert processed_row.error_message is not None
        assert "Updated class" in processed_row.error_message

        assert updated_class is not None
        assert updated_class.id == class_id
        assert updated_class.teacher_id == teacher_user.id


async def test_processing_task_records_class_teacher_failure(
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

    batch = build_import_batch(
        school_id=school_id,
        uploaded_by_id=school_admin_user.id,
        import_type="classes",
        original_filename="invalid-class-teachers.csv",
    )

    db_session.add(
        batch,
    )
    await db_session.flush()

    row = build_import_row(
        batch_id=batch.id,
        school_id=school_id,
        row_number=2,
        data={
            "name": "Invalid Teacher Class",
            "teacher_email": student_user.email,
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

        class_group = await ClassGroupRepository(
            verification_db,
        ).get_by_name_and_school(
            name="Invalid Teacher Class",
            school_id=school_id,
            include_relationships=False,
        )

        assert summary["status"] == ImportStatus.COMPLETED_WITH_ERRORS.value
        assert summary["processed_rows"] == 1
        assert summary["successful_rows"] == 0
        assert summary["imported_rows"] == 0
        assert summary["updated_rows"] == 0
        assert summary["failed_rows"] == 1

        assert processed_batch.status == ImportStatus.COMPLETED_WITH_ERRORS
        assert processed_batch.processed_rows == 1
        assert processed_batch.successful_rows == 0
        assert processed_batch.failed_rows == 1

        assert processed_row.status == ImportRowStatus.FAILED
        assert processed_row.attempt_count == 1
        assert processed_row.created_entity_id is None
        assert processed_row.processed_at is not None
        assert processed_row.error_message is not None
        assert "not registered as a teacher" in (processed_row.error_message)

        assert class_group is None


async def test_enrollment_import_handler_is_registered() -> None:
    register_import_handlers()

    handler = get_import_handler(
        "enrollments",
    )

    assert handler.validator is not None
    assert handler.processor is process_enrollment_row


async def test_enrollment_processor_creates_enrollment(
    db_session: AsyncSession,
    school_admin_user: User,
    student_user: User,
) -> None:
    school_id = school_admin_user.school_id

    assert school_id is not None
    assert student_user.school_id == school_id

    class_group = ClassGroup(
        name="Enrollment Processor Class",
        school_id=school_id,
        teacher_id=None,
    )

    class_group = await ClassGroupRepository(
        db_session,
    ).create(
        class_group,
    )

    result = await process_enrollment_row(
        db_session,
        {
            "student_email": student_user.email,
            "class_name": class_group.name,
        },
        school_id,
    )

    await db_session.commit()

    enrollment = await EnrollmentRepository(
        db_session,
    ).get_by_student_and_class_in_school(
        student_id=student_user.id,
        class_id=class_group.id,
        school_id=school_id,
        include_relationships=False,
    )

    assert result.action == RowProcessingAction.CREATED
    assert result.entity_id is not None
    assert result.message == (
        f"Enrolled student '{student_user.email}' " f"in class '{class_group.name}'."
    )

    assert enrollment is not None
    assert enrollment.id == result.entity_id
    assert enrollment.user_id == student_user.id
    assert enrollment.class_id == class_group.id


async def test_enrollment_processor_skips_duplicate_enrollment(
    db_session: AsyncSession,
    school_admin_user: User,
    student_user: User,
) -> None:
    school_id = school_admin_user.school_id

    assert school_id is not None
    assert student_user.school_id == school_id

    class_group = ClassGroup(
        name="Duplicate Enrollment Class",
        school_id=school_id,
        teacher_id=None,
    )

    class_group = await ClassGroupRepository(
        db_session,
    ).create(
        class_group,
    )

    existing_enrollment = Enrollment(
        user_id=student_user.id,
        class_id=class_group.id,
    )

    existing_enrollment = await EnrollmentRepository(
        db_session,
    ).create(
        existing_enrollment,
    )

    await db_session.commit()

    result = await process_enrollment_row(
        db_session,
        {
            "student_email": student_user.email,
            "class_name": class_group.name,
        },
        school_id,
    )

    assert result.action == RowProcessingAction.SKIPPED
    assert result.entity_id == existing_enrollment.id
    assert result.message == (
        f"Student '{student_user.email}' is already enrolled "
        f"in class '{class_group.name}'."
    )

    matching_enrollments = await EnrollmentRepository(
        db_session,
    ).list_by_student(
        student_user.id,
        school_id=school_id,
    )

    matching_ids = {
        enrollment.id
        for enrollment in matching_enrollments
        if enrollment.class_id == class_group.id
    }

    assert matching_ids == {
        existing_enrollment.id,
    }


async def test_enrollment_processor_rejects_missing_student(
    db_session: AsyncSession,
    school_admin_user: User,
) -> None:
    school_id = school_admin_user.school_id

    assert school_id is not None

    class_group = ClassGroup(
        name="Missing Student Enrollment Class",
        school_id=school_id,
        teacher_id=None,
    )

    class_group = await ClassGroupRepository(
        db_session,
    ).create(
        class_group,
    )

    with pytest.raises(
        ValueError,
        match="No student with email",
    ):
        await process_enrollment_row(
            db_session,
            {
                "student_email": "missing.student@example.com",
                "class_name": class_group.name,
            },
            school_id,
        )


async def test_enrollment_processor_rejects_missing_class(
    db_session: AsyncSession,
    school_admin_user: User,
    student_user: User,
) -> None:
    school_id = school_admin_user.school_id

    assert school_id is not None
    assert student_user.school_id == school_id

    with pytest.raises(
        ValueError,
        match="No class named",
    ):
        await process_enrollment_row(
            db_session,
            {
                "student_email": student_user.email,
                "class_name": "Missing Enrollment Class",
            },
            school_id,
        )


async def test_enrollment_processor_rejects_non_student_user(
    db_session: AsyncSession,
    school_admin_user: User,
    teacher_user: User,
) -> None:
    school_id = school_admin_user.school_id

    assert school_id is not None
    assert teacher_user.school_id == school_id

    class_group = ClassGroup(
        name="Non Student Enrollment Class",
        school_id=school_id,
        teacher_id=None,
    )

    class_group = await ClassGroupRepository(
        db_session,
    ).create(
        class_group,
    )

    with pytest.raises(
        ValueError,
        match="is not registered as a student",
    ):
        await process_enrollment_row(
            db_session,
            {
                "student_email": teacher_user.email,
                "class_name": class_group.name,
            },
            school_id,
        )

    enrollment = await EnrollmentRepository(
        db_session,
    ).get_by_student_and_class_in_school(
        student_id=teacher_user.id,
        class_id=class_group.id,
        school_id=school_id,
        include_relationships=False,
    )

    assert enrollment is None


@pytest.mark.parametrize(
    "invalid_school_id",
    [
        0,
        -1,
        True,
    ],
)
async def test_enrollment_processor_rejects_invalid_school_id(
    db_session: AsyncSession,
    invalid_school_id: int,
) -> None:
    with pytest.raises(
        ValueError,
        match="school_id must be a positive integer",
    ):
        await process_enrollment_row(
            db_session,
            {
                "student_email": "student@example.com",
                "class_name": "Invalid School Enrollment",
            },
            invalid_school_id,
        )


async def test_enrollment_processor_rejects_overlong_class_name(
    db_session: AsyncSession,
    school_admin_user: User,
) -> None:
    school_id = school_admin_user.school_id

    assert school_id is not None

    with pytest.raises(
        ValueError,
        match="class_name.*cannot exceed 255 characters",
    ):
        await process_enrollment_row(
            db_session,
            {
                "student_email": "student@example.com",
                "class_name": "C" * 256,
            },
            school_id,
        )


async def test_processing_task_imports_valid_enrollment_row(
    db_session: AsyncSession,
    school_admin_user: User,
    student_user: User,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    register_import_handlers()

    school_id = school_admin_user.school_id

    assert school_id is not None
    assert student_user.school_id == school_id

    class_group = ClassGroup(
        name="Background Enrollment Class",
        school_id=school_id,
        teacher_id=None,
    )

    class_group = await ClassGroupRepository(
        db_session,
    ).create(
        class_group,
    )

    task_session_maker = configure_task_session_maker(
        db_session,
        monkeypatch,
    )

    batch = build_import_batch(
        school_id=school_id,
        uploaded_by_id=school_admin_user.id,
        import_type="enrollments",
        original_filename="enrollments.csv",
    )

    db_session.add(
        batch,
    )
    await db_session.flush()

    row = build_import_row(
        batch_id=batch.id,
        school_id=school_id,
        row_number=2,
        data={
            "student_email": student_user.email,
            "class_name": class_group.name,
        },
    )

    db_session.add(
        row,
    )
    await db_session.commit()

    batch_id = batch.id
    row_id = row.id
    class_id = class_group.id
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

        processed_row = await get_row_by_id(
            verification_db,
            row_id,
        )

        enrollment = await EnrollmentRepository(
            verification_db,
        ).get_by_student_and_class_in_school(
            student_id=student_id,
            class_id=class_id,
            school_id=school_id,
            include_relationships=False,
        )

        assert summary["status"] == ImportStatus.COMPLETED.value
        assert summary["processed_rows"] == 1
        assert summary["successful_rows"] == 1
        assert summary["imported_rows"] == 1
        assert summary["updated_rows"] == 0
        assert summary["skipped_rows"] == 0
        assert summary["failed_rows"] == 0

        assert processed_batch.status == ImportStatus.COMPLETED
        assert processed_batch.processed_rows == 1
        assert processed_batch.successful_rows == 1
        assert processed_batch.skipped_rows == 0
        assert processed_batch.failed_rows == 0

        assert processed_row.status == ImportRowStatus.IMPORTED
        assert processed_row.attempt_count == 1
        assert processed_row.entity_type == "enrollments"
        assert processed_row.created_entity_id is not None
        assert processed_row.processed_at is not None
        assert processed_row.error_message is not None
        assert "Enrolled student" in processed_row.error_message

        assert enrollment is not None
        assert enrollment.id == processed_row.created_entity_id
        assert enrollment.user_id == student_id
        assert enrollment.class_id == class_id


async def test_processing_task_skips_duplicate_enrollment_row(
    db_session: AsyncSession,
    school_admin_user: User,
    student_user: User,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    register_import_handlers()

    school_id = school_admin_user.school_id

    assert school_id is not None
    assert student_user.school_id == school_id

    class_group = ClassGroup(
        name="Background Duplicate Enrollment Class",
        school_id=school_id,
        teacher_id=None,
    )

    class_group = await ClassGroupRepository(
        db_session,
    ).create(
        class_group,
    )

    existing_enrollment = Enrollment(
        user_id=student_user.id,
        class_id=class_group.id,
    )

    existing_enrollment = await EnrollmentRepository(
        db_session,
    ).create(
        existing_enrollment,
    )

    task_session_maker = configure_task_session_maker(
        db_session,
        monkeypatch,
    )

    batch = build_import_batch(
        school_id=school_id,
        uploaded_by_id=school_admin_user.id,
        import_type="enrollments",
        operation=ImportOperation.UPSERT,
        original_filename="duplicate-enrollments.csv",
    )

    db_session.add(
        batch,
    )
    await db_session.flush()

    row = build_import_row(
        batch_id=batch.id,
        school_id=school_id,
        row_number=2,
        data={
            "student_email": student_user.email,
            "class_name": class_group.name,
        },
    )

    db_session.add(
        row,
    )
    await db_session.commit()

    batch_id = batch.id
    row_id = row.id
    existing_enrollment_id = existing_enrollment.id

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
        assert summary["successful_rows"] == 0
        assert summary["imported_rows"] == 0
        assert summary["updated_rows"] == 0
        assert summary["skipped_rows"] == 1
        assert summary["failed_rows"] == 0

        assert processed_batch.status == ImportStatus.COMPLETED
        assert processed_batch.processed_rows == 1
        assert processed_batch.successful_rows == 0
        assert processed_batch.skipped_rows == 1
        assert processed_batch.failed_rows == 0

        assert processed_row.status == ImportRowStatus.SKIPPED
        assert processed_row.attempt_count == 1
        assert processed_row.entity_type == "enrollments"
        assert processed_row.created_entity_id == existing_enrollment_id
        assert processed_row.processed_at is not None
        assert processed_row.error_message is not None
        assert "already enrolled" in processed_row.error_message


async def test_processing_task_records_enrollment_failure(
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
        name="Invalid Background Enrollment Class",
        school_id=school_id,
        teacher_id=None,
    )

    class_group = await ClassGroupRepository(
        db_session,
    ).create(
        class_group,
    )

    task_session_maker = configure_task_session_maker(
        db_session,
        monkeypatch,
    )

    batch = build_import_batch(
        school_id=school_id,
        uploaded_by_id=school_admin_user.id,
        import_type="enrollments",
        original_filename="invalid-enrollments.csv",
    )

    db_session.add(
        batch,
    )
    await db_session.flush()

    row = build_import_row(
        batch_id=batch.id,
        school_id=school_id,
        row_number=2,
        data={
            "student_email": teacher_user.email,
            "class_name": class_group.name,
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

        enrollment = await EnrollmentRepository(
            verification_db,
        ).get_by_student_and_class_in_school(
            student_id=teacher_user.id,
            class_id=class_group.id,
            school_id=school_id,
            include_relationships=False,
        )

        assert summary["status"] == ImportStatus.COMPLETED_WITH_ERRORS.value
        assert summary["processed_rows"] == 1
        assert summary["successful_rows"] == 0
        assert summary["imported_rows"] == 0
        assert summary["updated_rows"] == 0
        assert summary["skipped_rows"] == 0
        assert summary["failed_rows"] == 1

        assert processed_batch.status == ImportStatus.COMPLETED_WITH_ERRORS
        assert processed_batch.processed_rows == 1
        assert processed_batch.successful_rows == 0
        assert processed_batch.skipped_rows == 0
        assert processed_batch.failed_rows == 1

        assert processed_row.status == ImportRowStatus.FAILED
        assert processed_row.attempt_count == 1
        assert processed_row.created_entity_id is None
        assert processed_row.processed_at is not None
        assert processed_row.error_message is not None
        assert "not registered as a student" in processed_row.error_message

        assert enrollment is None
