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
from app.imports.processors.enrollments import process_enrollment_row
from app.imports.registry import (
    RowProcessingAction,
    get_import_handler,
)
from app.imports.validators.enrollments import validate_enrollment_row
from app.models.class_group import ClassGroup
from app.models.enrollment import Enrollment
from app.models.import_batch import (
    ImportBatch,
    ImportOperation,
    ImportRow,
    ImportRowStatus,
    ImportStatus,
)
from app.models.user import User
from app.repositories.enrollment import EnrollmentRepository

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


async def get_enrollment_by_id(
    db: AsyncSession,
    enrollment_id: int,
) -> Enrollment:
    result = await db.execute(
        select(Enrollment).where(
            Enrollment.id == enrollment_id,
        ),
    )

    return result.scalar_one()


def build_enrollment_batch(
    *,
    school_id: int,
    uploaded_by_id: int,
    operation: ImportOperation = ImportOperation.CREATE,
    total_rows: int = 1,
) -> ImportBatch:
    """
    Build a ready enrolment-import batch with consistent counters.
    """

    return ImportBatch(
        school_id=school_id,
        uploaded_by_id=uploaded_by_id,
        import_type="enrollments",
        operation=operation,
        status=ImportStatus.READY,
        original_filename="enrollments.csv",
        total_rows=total_rows,
        validated_rows=total_rows,
        processed_rows=0,
        successful_rows=0,
        warning_rows=0,
        failed_rows=0,
        skipped_rows=0,
        current_stage="ready",
    )


def build_enrollment_row(
    *,
    batch_id: int,
    school_id: int,
    row_number: int,
    data: dict[str, Any],
    status: ImportRowStatus = ImportRowStatus.VALID,
    validation_errors: list[dict[str, Any]] | None = None,
) -> ImportRow:
    """
    Build one staged enrolment-import row.
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


async def create_class_group(
    db_session: AsyncSession,
    *,
    school_id: int,
    name: str,
    teacher_id: int | None = None,
) -> ClassGroup:
    class_group = ClassGroup(
        name=name,
        school_id=school_id,
        teacher_id=teacher_id,
    )

    db_session.add(class_group)
    await db_session.flush()

    return class_group


async def test_enrollment_import_handler_is_registered() -> None:
    register_import_handlers()

    handler = get_import_handler(
        "enrollments",
    )

    assert handler.validator is validate_enrollment_row
    assert handler.processor is process_enrollment_row


async def test_enrollment_validator_accepts_valid_row() -> None:
    result = validate_enrollment_row(
        {
            "student_email": " student@example.com ",
            "class_name": " Year 9 Physics ",
            "academic_year": "2026/2027",
        },
    )

    assert result.is_valid is True
    assert result.errors == []
    assert result.warnings == []

    assert result.normalised_data is not None
    assert result.normalised_data["student_email"] == ("student@example.com")
    assert result.normalised_data["class_name"] == "Year 9 Physics"

    # Extra fields remain available for future enrolment-import expansion.
    assert result.normalised_data["academic_year"] == "2026/2027"


async def test_enrollment_validator_rejects_invalid_row() -> None:
    result = validate_enrollment_row(
        {
            "student_email": "not-an-email",
            "class_name": "",
        },
    )

    assert result.is_valid is False
    assert result.normalised_data is None
    assert result.errors

    error_locations = {tuple(error["loc"]) for error in result.errors}

    assert ("student_email",) in error_locations
    assert ("class_name",) in error_locations


async def test_enrollment_validator_rejects_long_class_name() -> None:
    result = validate_enrollment_row(
        {
            "student_email": "student@example.com",
            "class_name": "A" * 256,
        },
    )

    assert result.is_valid is False
    assert result.normalised_data is None

    error_locations = {tuple(error["loc"]) for error in result.errors}

    assert ("class_name",) in error_locations


async def test_enrollment_processor_creates_new_enrollment(
    db_session: AsyncSession,
    school_admin_user: User,
    student_user: User,
    teacher_user: User,
) -> None:
    school_id = school_admin_user.school_id

    assert school_id is not None
    assert student_user.school_id == school_id
    assert teacher_user.school_id == school_id

    class_group = await create_class_group(
        db_session,
        school_id=school_id,
        name="Year 10 Physics",
        teacher_id=teacher_user.id,
    )

    await db_session.commit()

    result = await process_enrollment_row(
        db_session,
        {
            "student_email": student_user.email.upper(),
            "class_name": " Year 10 Physics ",
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
    )

    assert result.action == RowProcessingAction.CREATED
    assert result.entity_id is not None
    assert result.message == (
        f"Enrolled student '{student_user.email.lower()}' "
        "in class 'Year 10 Physics'."
    )

    assert enrollment is not None
    assert enrollment.id == result.entity_id
    assert enrollment.user_id == student_user.id
    assert enrollment.class_id == class_group.id


async def test_enrollment_processor_skips_existing_enrollment(
    db_session: AsyncSession,
    school_admin_user: User,
    student_user: User,
    teacher_user: User,
) -> None:
    school_id = school_admin_user.school_id

    assert school_id is not None
    assert student_user.school_id == school_id
    assert teacher_user.school_id == school_id

    class_group = await create_class_group(
        db_session,
        school_id=school_id,
        name="Year 11 Chemistry",
        teacher_id=teacher_user.id,
    )

    await db_session.flush()

    existing_enrollment = Enrollment(
        user_id=student_user.id,
        class_id=class_group.id,
    )

    db_session.add(existing_enrollment)
    await db_session.commit()
    await db_session.refresh(existing_enrollment)

    result = await process_enrollment_row(
        db_session,
        {
            "student_email": student_user.email,
            "class_name": "Year 11 Chemistry",
        },
        school_id,
    )

    await db_session.commit()

    matching_enrollments = (
        (
            await db_session.execute(
                select(Enrollment).where(
                    Enrollment.user_id == student_user.id,
                    Enrollment.class_id == class_group.id,
                ),
            )
        )
        .scalars()
        .all()
    )

    assert result.action == RowProcessingAction.SKIPPED
    assert result.entity_id == existing_enrollment.id
    assert result.message == (
        f"Student '{student_user.email.lower()}' is already enrolled "
        "in class 'Year 11 Chemistry'."
    )

    assert len(matching_enrollments) == 1
    assert matching_enrollments[0].id == existing_enrollment.id


async def test_enrollment_processor_rejects_missing_student(
    db_session: AsyncSession,
    school_admin_user: User,
    teacher_user: User,
) -> None:
    school_id = school_admin_user.school_id

    assert school_id is not None
    assert teacher_user.school_id == school_id

    class_group = await create_class_group(
        db_session,
        school_id=school_id,
        name="Missing Student Class",
        teacher_id=teacher_user.id,
    )

    await db_session.commit()

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

    enrollments = await EnrollmentRepository(
        db_session,
    ).list_by_class(
        class_group.id,
        school_id=school_id,
    )

    assert enrollments == []


async def test_enrollment_processor_rejects_non_student_user(
    db_session: AsyncSession,
    school_admin_user: User,
    teacher_user: User,
) -> None:
    school_id = school_admin_user.school_id

    assert school_id is not None
    assert teacher_user.school_id == school_id

    class_group = await create_class_group(
        db_session,
        school_id=school_id,
        name="Non Student Class",
        teacher_id=teacher_user.id,
    )

    await db_session.commit()

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

    enrollments = await EnrollmentRepository(
        db_session,
    ).list_by_class(
        class_group.id,
        school_id=school_id,
    )

    assert enrollments == []


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
                "class_name": "Missing Class",
            },
            school_id,
        )

    enrollments = await EnrollmentRepository(
        db_session,
    ).list_by_student(
        student_user.id,
        school_id=school_id,
    )

    assert all(
        enrollment.class_group.name != "Missing Class" for enrollment in enrollments
    )


@pytest.mark.parametrize(
    "school_id",
    [
        0,
        -1,
        -999,
    ],
)
async def test_enrollment_processor_rejects_invalid_school_id(
    db_session: AsyncSession,
    school_id: int,
) -> None:
    with pytest.raises(
        ValueError,
        match="school_id must be a positive integer",
    ):
        await process_enrollment_row(
            db_session,
            {
                "student_email": "student@example.com",
                "class_name": "Physics",
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
                "class_name": "Physics",
            },
            "Enrollment import field 'student_email' is required.",
        ),
        (
            {
                "student_email": "   ",
                "class_name": "Physics",
            },
            "Enrollment import field 'student_email' cannot be blank.",
        ),
        (
            {
                "student_email": "student@example.com",
            },
            "Enrollment import field 'class_name' is required.",
        ),
        (
            {
                "student_email": "student@example.com",
                "class_name": "   ",
            },
            "Enrollment import field 'class_name' cannot be blank.",
        ),
        (
            {
                "student_email": "student@example.com",
                "class_name": "A" * 256,
            },
            ("Enrollment import field 'class_name' " "cannot exceed 255 characters."),
        ),
    ],
)
async def test_enrollment_processor_defensively_rejects_malformed_rows(
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
        await process_enrollment_row(
            db_session,
            row,
            1,
        )


async def test_enrollment_repository_school_scoped_lookup(
    db_session: AsyncSession,
    school_admin_user: User,
    student_user: User,
    teacher_user: User,
) -> None:
    school_id = school_admin_user.school_id

    assert school_id is not None
    assert student_user.school_id == school_id
    assert teacher_user.school_id == school_id

    class_group = await create_class_group(
        db_session,
        school_id=school_id,
        name="Repository Lookup Class",
        teacher_id=teacher_user.id,
    )

    await db_session.flush()

    enrollment = Enrollment(
        user_id=student_user.id,
        class_id=class_group.id,
    )

    db_session.add(enrollment)
    await db_session.commit()
    await db_session.refresh(enrollment)

    repository = EnrollmentRepository(
        db_session,
    )

    found = await repository.get_by_student_and_class_in_school(
        student_id=student_user.id,
        class_id=class_group.id,
        school_id=school_id,
    )

    missing = await repository.get_by_student_and_class_in_school(
        student_id=student_user.id,
        class_id=class_group.id,
        school_id=school_id + 999,
    )

    assert found is not None
    assert found.id == enrollment.id
    assert missing is None


async def test_enrollment_repository_exists_checks(
    db_session: AsyncSession,
    school_admin_user: User,
    student_user: User,
    teacher_user: User,
) -> None:
    school_id = school_admin_user.school_id

    assert school_id is not None
    assert student_user.school_id == school_id
    assert teacher_user.school_id == school_id

    class_group = await create_class_group(
        db_session,
        school_id=school_id,
        name="Repository Exists Class",
        teacher_id=teacher_user.id,
    )

    await db_session.flush()

    enrollment = Enrollment(
        user_id=student_user.id,
        class_id=class_group.id,
    )

    db_session.add(enrollment)
    await db_session.commit()
    await db_session.refresh(enrollment)

    repository = EnrollmentRepository(
        db_session,
    )

    assert (
        await repository.exists(
            enrollment.id,
        )
        is True
    )

    assert (
        await repository.exists_for_student_and_class(
            student_id=student_user.id,
            class_id=class_group.id,
        )
        is True
    )

    assert (
        await repository.exists_in_school(
            school_id=school_id,
            enrollment_id=enrollment.id,
        )
        is True
    )

    assert (
        await repository.exists_in_school(
            school_id=school_id,
            student_id=student_user.id,
            class_id=class_group.id,
        )
        is True
    )

    assert (
        await repository.exists_in_school(
            school_id=school_id + 999,
            enrollment_id=enrollment.id,
        )
        is False
    )


async def test_enrollment_repository_lists_by_student_and_class(
    db_session: AsyncSession,
    school_admin_user: User,
    student_user: User,
    teacher_user: User,
) -> None:
    school_id = school_admin_user.school_id

    assert school_id is not None
    assert student_user.school_id == school_id
    assert teacher_user.school_id == school_id

    first_class = await create_class_group(
        db_session,
        school_id=school_id,
        name="First Enrolment Class",
        teacher_id=teacher_user.id,
    )

    second_class = await create_class_group(
        db_session,
        school_id=school_id,
        name="Second Enrolment Class",
        teacher_id=teacher_user.id,
    )

    await db_session.flush()

    first_enrollment = Enrollment(
        user_id=student_user.id,
        class_id=first_class.id,
    )

    second_enrollment = Enrollment(
        user_id=student_user.id,
        class_id=second_class.id,
    )

    db_session.add_all(
        [
            first_enrollment,
            second_enrollment,
        ],
    )

    await db_session.commit()

    repository = EnrollmentRepository(
        db_session,
    )

    student_enrollments = await repository.list_by_student(
        student_user.id,
        school_id=school_id,
    )

    first_class_enrollments = await repository.list_by_class(
        first_class.id,
        school_id=school_id,
    )

    student_enrollment_ids = {enrollment.id for enrollment in student_enrollments}

    first_class_enrollment_ids = {
        enrollment.id for enrollment in first_class_enrollments
    }

    assert first_enrollment.id in student_enrollment_ids
    assert second_enrollment.id in student_enrollment_ids

    assert first_enrollment.id in first_class_enrollment_ids
    assert second_enrollment.id not in first_class_enrollment_ids


async def test_processing_task_imports_valid_enrollment_row(
    db_session: AsyncSession,
    school_admin_user: User,
    student_user: User,
    teacher_user: User,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    register_import_handlers()

    school_id = school_admin_user.school_id

    assert school_id is not None
    assert student_user.school_id == school_id
    assert teacher_user.school_id == school_id

    class_group = await create_class_group(
        db_session,
        school_id=school_id,
        name="Batch Enrolment Class",
        teacher_id=teacher_user.id,
    )

    task_session_maker = configure_task_session_maker(
        db_session,
        monkeypatch,
    )

    batch = build_enrollment_batch(
        school_id=school_id,
        uploaded_by_id=school_admin_user.id,
    )

    db_session.add(batch)
    await db_session.flush()

    row = build_enrollment_row(
        batch_id=batch.id,
        school_id=school_id,
        row_number=2,
        data={
            "student_email": student_user.email,
            "class_name": class_group.name,
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

        created_enrollment = await EnrollmentRepository(
            verification_db,
        ).get_by_student_and_class_in_school(
            student_id=student_user.id,
            class_id=class_group.id,
            school_id=school_id,
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

        assert created_enrollment is not None
        assert created_enrollment.id == processed_row.created_entity_id
        assert created_enrollment.user_id == student_user.id
        assert created_enrollment.class_id == class_group.id


async def test_processing_task_skips_existing_enrollment(
    db_session: AsyncSession,
    school_admin_user: User,
    student_user: User,
    teacher_user: User,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    register_import_handlers()

    school_id = school_admin_user.school_id

    assert school_id is not None
    assert student_user.school_id == school_id
    assert teacher_user.school_id == school_id

    class_group = await create_class_group(
        db_session,
        school_id=school_id,
        name="Existing Batch Enrolment Class",
        teacher_id=teacher_user.id,
    )

    await db_session.flush()

    existing_enrollment = Enrollment(
        user_id=student_user.id,
        class_id=class_group.id,
    )

    db_session.add(existing_enrollment)
    await db_session.flush()

    task_session_maker = configure_task_session_maker(
        db_session,
        monkeypatch,
    )

    batch = build_enrollment_batch(
        school_id=school_id,
        uploaded_by_id=school_admin_user.id,
        operation=ImportOperation.UPSERT,
    )

    db_session.add(batch)
    await db_session.flush()

    row = build_enrollment_row(
        batch_id=batch.id,
        school_id=school_id,
        row_number=2,
        data={
            "student_email": student_user.email,
            "class_name": class_group.name,
        },
    )

    db_session.add(row)
    await db_session.commit()

    batch_id = batch.id
    row_id = row.id
    enrollment_id = existing_enrollment.id

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

        preserved_enrollment = await get_enrollment_by_id(
            verification_db,
            enrollment_id,
        )

        matching_enrollments = (
            (
                await verification_db.execute(
                    select(Enrollment).where(
                        Enrollment.user_id == student_user.id,
                        Enrollment.class_id == class_group.id,
                    ),
                )
            )
            .scalars()
            .all()
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
        assert processed_row.created_entity_id == enrollment_id
        assert processed_row.processed_at is not None
        assert processed_row.error_message is not None
        assert "already enrolled" in processed_row.error_message

        assert preserved_enrollment.id == enrollment_id
        assert len(matching_enrollments) == 1


async def test_processing_task_records_missing_class_failure(
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

    batch = build_enrollment_batch(
        school_id=school_id,
        uploaded_by_id=school_admin_user.id,
    )

    db_session.add(batch)
    await db_session.flush()

    row = build_enrollment_row(
        batch_id=batch.id,
        school_id=school_id,
        row_number=2,
        data={
            "student_email": student_user.email,
            "class_name": "Missing Batch Class",
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

        assert summary["status"] == (ImportStatus.COMPLETED_WITH_ERRORS.value)
        assert summary["processed_rows"] == 1
        assert summary["successful_rows"] == 0
        assert summary["skipped_rows"] == 0
        assert summary["failed_rows"] == 1

        assert processed_batch.status == (ImportStatus.COMPLETED_WITH_ERRORS)
        assert processed_batch.successful_rows == 0
        assert processed_batch.skipped_rows == 0
        assert processed_batch.failed_rows == 1

        assert failed_row.status == ImportRowStatus.FAILED
        assert failed_row.attempt_count == 1
        assert failed_row.created_entity_id is None
        assert failed_row.processed_at is not None
        assert failed_row.error_message is not None
        assert "No class named" in failed_row.error_message


async def test_enrollment_processing_enforces_school_isolation(
    db_session: AsyncSession,
    school_admin_user: User,
    student_user: User,
    teacher_user: User,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    school_id = school_admin_user.school_id

    assert school_id is not None
    assert student_user.school_id == school_id
    assert teacher_user.school_id == school_id

    class_group = await create_class_group(
        db_session,
        school_id=school_id,
        name="Isolated Enrolment Class",
        teacher_id=teacher_user.id,
    )

    configure_task_session_maker(
        db_session,
        monkeypatch,
    )

    batch = build_enrollment_batch(
        school_id=school_id,
        uploaded_by_id=school_admin_user.id,
    )

    db_session.add(batch)
    await db_session.flush()

    row = build_enrollment_row(
        batch_id=batch.id,
        school_id=school_id,
        row_number=2,
        data={
            "student_email": student_user.email,
            "class_name": class_group.name,
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
    assert batch.skipped_rows == 0
    assert batch.failed_rows == 0

    assert row.status == ImportRowStatus.VALID
    assert row.attempt_count == 0
    assert row.created_entity_id is None
    assert row.processed_at is None

    enrollment = await EnrollmentRepository(
        db_session,
    ).get_by_student_and_class_in_school(
        student_id=student_user.id,
        class_id=class_group.id,
        school_id=school_id,
    )

    assert enrollment is None
