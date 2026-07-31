from __future__ import annotations

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
)

import app.tasks.imports as import_tasks
from app.imports.bootstrap import register_import_handlers
from app.imports.processors.students import process_student_row
from app.imports.registry import (
    RowProcessingAction,
    get_import_handler,
)
from app.models.import_batch import (
    ImportBatch,
    ImportOperation,
    ImportRow,
    ImportRowStatus,
    ImportStatus,
)
from app.models.user import User, UserRole
from app.repositories.user import UserRepository

pytestmark = pytest.mark.asyncio


async def test_student_import_handler_is_registered() -> None:
    register_import_handlers()

    handler = get_import_handler("students")

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

    repository = UserRepository(db_session)

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
    await db_session.refresh(student_user)

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


async def test_processing_task_imports_valid_student_row(
    db_session: AsyncSession,
    school_admin_user: User,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    register_import_handlers()

    school_id = school_admin_user.school_id

    assert school_id is not None
    assert db_session.bind is not None

    task_session_maker = async_sessionmaker(
        bind=db_session.bind,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    monkeypatch.setattr(
        import_tasks,
        "AsyncSessionLocal",
        task_session_maker,
    )

    batch = ImportBatch(
        school_id=school_id,
        uploaded_by_id=school_admin_user.id,
        import_type="students",
        operation=ImportOperation.CREATE,
        status=ImportStatus.READY,
        original_filename="students.csv",
        total_rows=1,
        validated_rows=1,
        processed_rows=0,
        successful_rows=0,
        warning_rows=0,
        failed_rows=0,
        skipped_rows=0,
        current_stage="ready",
    )

    db_session.add(batch)
    await db_session.flush()

    row_data = {
        "email": "batch.student@example.com",
        "first_name": "Batch",
        "last_name": "Student",
    }

    row = ImportRow(
        batch_id=batch.id,
        school_id=school_id,
        row_number=2,
        status=ImportRowStatus.VALID,
        original_data=dict(row_data),
        normalised_data=dict(row_data),
        validation_errors=[],
        validation_warnings=[],
        attempt_count=0,
    )

    db_session.add(row)
    await db_session.commit()

    batch_id = batch.id
    row_id = row.id

    summary = await import_tasks._process_import_batch_task(
        batch_id=batch_id,
        school_id=school_id,
    )

    async with task_session_maker() as verification_db:
        processed_batch = (
            await verification_db.execute(
                select(ImportBatch).where(
                    ImportBatch.id == batch_id,
                )
            )
        ).scalar_one()

        processed_row = (
            await verification_db.execute(
                select(ImportRow).where(
                    ImportRow.id == row_id,
                )
            )
        ).scalar_one()

        created_student = (
            await verification_db.execute(
                select(User).where(
                    User.email == "batch.student@example.com",
                    User.school_id == school_id,
                )
            )
        ).scalar_one_or_none()

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
    assert db_session.bind is not None

    task_session_maker = async_sessionmaker(
        bind=db_session.bind,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    monkeypatch.setattr(
        import_tasks,
        "AsyncSessionLocal",
        task_session_maker,
    )

    batch = ImportBatch(
        school_id=school_id,
        uploaded_by_id=student_id,
        import_type="students",
        operation=ImportOperation.UPSERT,
        status=ImportStatus.READY,
        original_filename="student-updates.csv",
        total_rows=1,
        validated_rows=1,
        processed_rows=0,
        successful_rows=0,
        warning_rows=0,
        failed_rows=0,
        skipped_rows=0,
        current_stage="ready",
    )

    db_session.add(batch)
    await db_session.flush()

    row_data = {
        "email": student_email,
        "first_name": "Batch",
        "last_name": "Updated",
    }

    row = ImportRow(
        batch_id=batch.id,
        school_id=school_id,
        row_number=2,
        status=ImportRowStatus.VALID,
        original_data=dict(row_data),
        normalised_data=dict(row_data),
        validation_errors=[],
        validation_warnings=[],
        attempt_count=0,
    )

    db_session.add(row)
    await db_session.commit()

    batch_id = batch.id
    row_id = row.id

    summary = await import_tasks._process_import_batch_task(
        batch_id=batch_id,
        school_id=school_id,
    )

    async with task_session_maker() as verification_db:
        processed_batch = (
            await verification_db.execute(
                select(ImportBatch).where(
                    ImportBatch.id == batch_id,
                )
            )
        ).scalar_one()

        processed_row = (
            await verification_db.execute(
                select(ImportRow).where(
                    ImportRow.id == row_id,
                )
            )
        ).scalar_one()

        updated_student = (
            await verification_db.execute(
                select(User).where(
                    User.id == student_id,
                )
            )
        ).scalar_one()

        matching_students = (
            (
                await verification_db.execute(
                    select(User).where(
                        User.email == student_email,
                        User.school_id == school_id,
                    )
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
    assert db_session.bind is not None

    task_session_maker = async_sessionmaker(
        bind=db_session.bind,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    monkeypatch.setattr(
        import_tasks,
        "AsyncSessionLocal",
        task_session_maker,
    )

    batch = ImportBatch(
        school_id=school_id,
        uploaded_by_id=school_admin_user.id,
        import_type="students",
        operation=ImportOperation.UPSERT,
        status=ImportStatus.READY,
        original_filename="mixed-students.csv",
        total_rows=2,
        validated_rows=2,
        processed_rows=0,
        successful_rows=0,
        warning_rows=0,
        failed_rows=0,
        skipped_rows=0,
        current_stage="ready",
    )

    db_session.add(batch)
    await db_session.flush()

    successful_data = {
        "email": "successful.student@example.com",
        "first_name": "Successful",
        "last_name": "Student",
    }

    successful_row = ImportRow(
        batch_id=batch.id,
        school_id=school_id,
        row_number=2,
        status=ImportRowStatus.VALID,
        original_data=dict(successful_data),
        normalised_data=dict(successful_data),
        validation_errors=[],
        validation_warnings=[],
        attempt_count=0,
    )

    failed_data = {
        "email": teacher_email,
        "first_name": "Teacher",
        "last_name": "Conflict",
    }

    failed_row = ImportRow(
        batch_id=batch.id,
        school_id=school_id,
        row_number=3,
        status=ImportRowStatus.VALID,
        original_data=dict(failed_data),
        normalised_data=dict(failed_data),
        validation_errors=[],
        validation_warnings=[],
        attempt_count=0,
    )

    db_session.add_all(
        [
            successful_row,
            failed_row,
        ]
    )
    await db_session.commit()

    batch_id = batch.id
    successful_row_id = successful_row.id
    failed_row_id = failed_row.id

    summary = await import_tasks._process_import_batch_task(
        batch_id=batch_id,
        school_id=school_id,
    )

    async with task_session_maker() as verification_db:
        processed_batch = (
            await verification_db.execute(
                select(ImportBatch).where(
                    ImportBatch.id == batch_id,
                )
            )
        ).scalar_one()

        processed_successful_row = (
            await verification_db.execute(
                select(ImportRow).where(
                    ImportRow.id == successful_row_id,
                )
            )
        ).scalar_one()

        processed_failed_row = (
            await verification_db.execute(
                select(ImportRow).where(
                    ImportRow.id == failed_row_id,
                )
            )
        ).scalar_one()

        created_student = (
            await verification_db.execute(
                select(User).where(
                    User.email == "successful.student@example.com",
                    User.school_id == school_id,
                )
            )
        ).scalar_one_or_none()

        existing_teacher = (
            await verification_db.execute(
                select(User).where(
                    User.email == teacher_email,
                    User.school_id == school_id,
                )
            )
        ).scalar_one()

        assert summary["status"] == (ImportStatus.COMPLETED_WITH_ERRORS.value)
        assert summary["processed_rows"] == 2
        assert summary["successful_rows"] == 1
        assert summary["imported_rows"] == 1
        assert summary["updated_rows"] == 0
        assert summary["failed_rows"] == 1

        assert processed_batch.status == (ImportStatus.COMPLETED_WITH_ERRORS)
        assert processed_batch.processed_rows == 2
        assert processed_batch.successful_rows == 1
        assert processed_batch.failed_rows == 1

        assert processed_successful_row.status == (ImportRowStatus.IMPORTED)
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
    assert db_session.bind is not None

    task_session_maker = async_sessionmaker(
        bind=db_session.bind,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    monkeypatch.setattr(
        import_tasks,
        "AsyncSessionLocal",
        task_session_maker,
    )

    batch = ImportBatch(
        school_id=school_id,
        uploaded_by_id=school_admin_user.id,
        import_type="students",
        operation=ImportOperation.CREATE,
        status=ImportStatus.READY,
        original_filename="students-with-invalid-row.csv",
        total_rows=2,
        validated_rows=2,
        processed_rows=0,
        successful_rows=0,
        warning_rows=0,
        failed_rows=1,
        skipped_rows=0,
        current_stage="ready",
    )

    db_session.add(batch)
    await db_session.flush()

    valid_data = {
        "email": "valid.student@example.com",
        "first_name": "Valid",
        "last_name": "Student",
    }

    valid_row = ImportRow(
        batch_id=batch.id,
        school_id=school_id,
        row_number=2,
        status=ImportRowStatus.VALID,
        original_data=dict(valid_data),
        normalised_data=dict(valid_data),
        validation_errors=[],
        validation_warnings=[],
        attempt_count=0,
    )

    invalid_data = {
        "email": "not-an-email",
        "first_name": "",
        "last_name": "Invalid",
    }

    invalid_row = ImportRow(
        batch_id=batch.id,
        school_id=school_id,
        row_number=3,
        status=ImportRowStatus.INVALID,
        original_data=dict(invalid_data),
        normalised_data={},
        validation_errors=[
            {
                "type": "validation_error",
                "message": "Invalid student row.",
            }
        ],
        validation_warnings=[],
        error_message="Row validation failed.",
        attempt_count=0,
    )

    db_session.add_all(
        [
            valid_row,
            invalid_row,
        ]
    )
    await db_session.commit()

    batch_id = batch.id
    valid_row_id = valid_row.id
    invalid_row_id = invalid_row.id

    summary = await import_tasks._process_import_batch_task(
        batch_id=batch_id,
        school_id=school_id,
    )

    async with task_session_maker() as verification_db:
        processed_batch = (
            await verification_db.execute(
                select(ImportBatch).where(
                    ImportBatch.id == batch_id,
                )
            )
        ).scalar_one()

        processed_valid_row = (
            await verification_db.execute(
                select(ImportRow).where(
                    ImportRow.id == valid_row_id,
                )
            )
        ).scalar_one()

        preserved_invalid_row = (
            await verification_db.execute(
                select(ImportRow).where(
                    ImportRow.id == invalid_row_id,
                )
            )
        ).scalar_one()

        created_student = (
            await verification_db.execute(
                select(User).where(
                    User.email == "valid.student@example.com",
                    User.school_id == school_id,
                )
            )
        ).scalar_one_or_none()

        assert summary["status"] == (ImportStatus.COMPLETED_WITH_ERRORS.value)
        assert summary["processed_rows"] == 2
        assert summary["successful_rows"] == 1
        assert summary["imported_rows"] == 1
        assert summary["updated_rows"] == 0
        assert summary["invalid_rows"] == 1
        assert summary["failed_rows"] == 1

        assert processed_batch.status == (ImportStatus.COMPLETED_WITH_ERRORS)
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


async def test_processing_task_skips_cancelled_batch(
    db_session: AsyncSession,
    school_admin_user: User,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    register_import_handlers()

    school_id = school_admin_user.school_id

    assert school_id is not None
    assert db_session.bind is not None

    task_session_maker = async_sessionmaker(
        bind=db_session.bind,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    monkeypatch.setattr(
        import_tasks,
        "AsyncSessionLocal",
        task_session_maker,
    )

    batch = ImportBatch(
        school_id=school_id,
        uploaded_by_id=school_admin_user.id,
        import_type="students",
        operation=ImportOperation.CREATE,
        status=ImportStatus.CANCELLED,
        original_filename="cancelled-students.csv",
        total_rows=1,
        validated_rows=1,
        processed_rows=0,
        successful_rows=0,
        warning_rows=0,
        failed_rows=0,
        skipped_rows=0,
        current_stage="cancelled",
    )

    db_session.add(batch)
    await db_session.flush()

    row_data = {
        "email": "cancelled.student@example.com",
        "first_name": "Cancelled",
        "last_name": "Student",
    }

    row = ImportRow(
        batch_id=batch.id,
        school_id=school_id,
        row_number=2,
        status=ImportRowStatus.VALID,
        original_data=dict(row_data),
        normalised_data=dict(row_data),
        validation_errors=[],
        validation_warnings=[],
        attempt_count=0,
    )

    db_session.add(row)
    await db_session.commit()

    batch_id = batch.id
    row_id = row.id

    summary = await import_tasks._process_import_batch_task(
        batch_id=batch_id,
        school_id=school_id,
    )

    async with task_session_maker() as verification_db:
        unchanged_batch = (
            await verification_db.execute(
                select(ImportBatch).where(
                    ImportBatch.id == batch_id,
                )
            )
        ).scalar_one()

        unchanged_row = (
            await verification_db.execute(
                select(ImportRow).where(
                    ImportRow.id == row_id,
                )
            )
        ).scalar_one()

        created_student = (
            await verification_db.execute(
                select(User).where(
                    User.email == "cancelled.student@example.com",
                    User.school_id == school_id,
                )
            )
        ).scalar_one_or_none()

        assert summary == {
            "batch_id": batch_id,
            "school_id": school_id,
            "status": ImportStatus.CANCELLED.value,
            "skipped": True,
            "reason": "Batch has been cancelled.",
        }

        assert unchanged_batch.status == ImportStatus.CANCELLED
        assert unchanged_batch.processed_rows == 0
        assert unchanged_batch.successful_rows == 0
        assert unchanged_batch.failed_rows == 0

        assert unchanged_row.status == ImportRowStatus.VALID
        assert unchanged_row.attempt_count == 0
        assert unchanged_row.created_entity_id is None
        assert unchanged_row.processed_at is None

        assert created_student is None


async def test_processing_task_skips_completed_batch(
    db_session: AsyncSession,
    school_admin_user: User,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    register_import_handlers()

    school_id = school_admin_user.school_id

    assert school_id is not None
    assert db_session.bind is not None

    task_session_maker = async_sessionmaker(
        bind=db_session.bind,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    monkeypatch.setattr(
        import_tasks,
        "AsyncSessionLocal",
        task_session_maker,
    )

    batch = ImportBatch(
        school_id=school_id,
        uploaded_by_id=school_admin_user.id,
        import_type="students",
        operation=ImportOperation.CREATE,
        status=ImportStatus.COMPLETED,
        original_filename="completed-students.csv",
        total_rows=1,
        validated_rows=1,
        processed_rows=1,
        successful_rows=1,
        warning_rows=0,
        failed_rows=0,
        skipped_rows=0,
        current_stage="completed",
    )

    db_session.add(batch)
    await db_session.flush()

    row_data = {
        "email": "already.completed@example.com",
        "first_name": "Already",
        "last_name": "Completed",
    }

    row = ImportRow(
        batch_id=batch.id,
        school_id=school_id,
        row_number=2,
        status=ImportRowStatus.VALID,
        original_data=dict(row_data),
        normalised_data=dict(row_data),
        validation_errors=[],
        validation_warnings=[],
        attempt_count=0,
    )

    db_session.add(row)
    await db_session.commit()

    batch_id = batch.id
    row_id = row.id

    summary = await import_tasks._process_import_batch_task(
        batch_id=batch_id,
        school_id=school_id,
    )

    async with task_session_maker() as verification_db:
        unchanged_batch = (
            await verification_db.execute(
                select(ImportBatch).where(
                    ImportBatch.id == batch_id,
                )
            )
        ).scalar_one()

        unchanged_row = (
            await verification_db.execute(
                select(ImportRow).where(
                    ImportRow.id == row_id,
                )
            )
        ).scalar_one()

        created_student = (
            await verification_db.execute(
                select(User).where(
                    User.email == "already.completed@example.com",
                    User.school_id == school_id,
                )
            )
        ).scalar_one_or_none()

        assert summary == {
            "batch_id": batch_id,
            "school_id": school_id,
            "status": ImportStatus.COMPLETED.value,
            "skipped": True,
            "reason": "Batch has already finished.",
        }

        assert unchanged_batch.status == ImportStatus.COMPLETED
        assert unchanged_batch.processed_rows == 1
        assert unchanged_batch.successful_rows == 1
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
    assert db_session.bind is not None

    task_session_maker = async_sessionmaker(
        bind=db_session.bind,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    monkeypatch.setattr(
        import_tasks,
        "AsyncSessionLocal",
        task_session_maker,
    )

    batch = ImportBatch(
        school_id=school_id,
        uploaded_by_id=school_admin_user.id,
        import_type="unknown_import_type",
        operation=ImportOperation.CREATE,
        status=ImportStatus.READY,
        original_filename="unknown-import.csv",
        total_rows=1,
        validated_rows=1,
        processed_rows=0,
        successful_rows=0,
        warning_rows=0,
        failed_rows=0,
        skipped_rows=0,
        current_stage="ready",
    )

    db_session.add(batch)
    await db_session.flush()

    row_data = {
        "external_id": "12345",
    }

    row = ImportRow(
        batch_id=batch.id,
        school_id=school_id,
        row_number=2,
        status=ImportRowStatus.VALID,
        original_data=dict(row_data),
        normalised_data=dict(row_data),
        validation_errors=[],
        validation_warnings=[],
        attempt_count=0,
    )

    db_session.add(row)
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

    async with task_session_maker() as verification_db:
        failed_batch = (
            await verification_db.execute(
                select(ImportBatch).where(
                    ImportBatch.id == batch_id,
                )
            )
        ).scalar_one()

        unchanged_row = (
            await verification_db.execute(
                select(ImportRow).where(
                    ImportRow.id == row_id,
                )
            )
        ).scalar_one()

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
    assert db_session.bind is not None

    task_session_maker = async_sessionmaker(
        bind=db_session.bind,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    monkeypatch.setattr(
        import_tasks,
        "AsyncSessionLocal",
        task_session_maker,
    )

    with pytest.raises(
        import_tasks.ImportBatchNotFoundError,
        match="Import batch 999999 was not found for school 1",
    ):
        await import_tasks._process_import_batch_task(
            batch_id=999999,
            school_id=1,
        )
