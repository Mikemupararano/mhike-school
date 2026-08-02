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
from app.imports.processors.courses import process_course_row
from app.imports.registry import (
    RowProcessingAction,
    get_import_handler,
)
from app.imports.validators.courses import validate_course_row
from app.models.course import Course
from app.models.import_batch import (
    ImportBatch,
    ImportOperation,
    ImportRow,
    ImportRowStatus,
    ImportStatus,
)
from app.models.user import User
from app.repositories.course import CourseRepository

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


async def get_course_by_id(
    db: AsyncSession,
    course_id: int,
) -> Course:
    result = await db.execute(
        select(Course).where(
            Course.id == course_id,
        ),
    )

    return result.scalar_one()


def build_course_batch(
    *,
    school_id: int,
    uploaded_by_id: int,
    operation: ImportOperation = ImportOperation.CREATE,
    total_rows: int = 1,
) -> ImportBatch:
    """
    Build a ready course-import batch with consistent counters.
    """

    return ImportBatch(
        school_id=school_id,
        uploaded_by_id=uploaded_by_id,
        import_type="courses",
        operation=operation,
        status=ImportStatus.READY,
        original_filename="courses.csv",
        total_rows=total_rows,
        validated_rows=total_rows,
        processed_rows=0,
        successful_rows=0,
        warning_rows=0,
        failed_rows=0,
        skipped_rows=0,
        current_stage="ready",
    )


def build_course_row(
    *,
    batch_id: int,
    school_id: int,
    row_number: int,
    data: dict[str, Any],
    status: ImportRowStatus = ImportRowStatus.VALID,
    validation_errors: list[dict[str, Any]] | None = None,
) -> ImportRow:
    """
    Build one staged course-import row.
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


async def test_course_import_handler_is_registered() -> None:
    register_import_handlers()

    handler = get_import_handler(
        "courses",
    )

    assert handler.validator is validate_course_row
    assert handler.processor is process_course_row


async def test_course_validator_accepts_valid_row() -> None:
    result = validate_course_row(
        {
            "title": "  A Level Physics  ",
            "description": "  Mechanics and electricity  ",
            "teacher_email": " teacher@example.com ",
            "exam_board": "OCR",
        },
    )

    assert result.is_valid is True
    assert result.errors == []
    assert result.warnings == []

    assert result.normalised_data is not None
    assert result.normalised_data["title"] == "A Level Physics"
    assert result.normalised_data["description"] == ("Mechanics and electricity")
    assert result.normalised_data["teacher_email"] == ("teacher@example.com")

    # Extra columns remain available for future import expansion.
    assert result.normalised_data["exam_board"] == "OCR"


async def test_course_validator_accepts_missing_description() -> None:
    result = validate_course_row(
        {
            "title": "GCSE Chemistry",
            "teacher_email": "teacher@example.com",
        },
    )

    assert result.is_valid is True
    assert result.errors == []
    assert result.normalised_data is not None
    assert result.normalised_data["title"] == "GCSE Chemistry"
    assert result.normalised_data["description"] is None


async def test_course_validator_rejects_invalid_row() -> None:
    result = validate_course_row(
        {
            "title": "",
            "teacher_email": "not-an-email",
        },
    )

    assert result.is_valid is False
    assert result.normalised_data is None
    assert result.errors

    error_locations = {tuple(error["loc"]) for error in result.errors}

    assert ("title",) in error_locations
    assert ("teacher_email",) in error_locations


async def test_course_validator_rejects_long_description() -> None:
    result = validate_course_row(
        {
            "title": "Physics",
            "description": "A" * 2001,
            "teacher_email": "teacher@example.com",
        },
    )

    assert result.is_valid is False
    assert result.normalised_data is None

    error_locations = {tuple(error["loc"]) for error in result.errors}

    assert ("description",) in error_locations


async def test_course_processor_creates_unpublished_course(
    db_session: AsyncSession,
    school_admin_user: User,
    teacher_user: User,
) -> None:
    school_id = school_admin_user.school_id

    assert school_id is not None
    assert teacher_user.school_id == school_id

    result = await process_course_row(
        db_session,
        {
            "title": "  A Level Physics  ",
            "description": "  Advanced physics course  ",
            "teacher_email": teacher_user.email.upper(),
        },
        school_id,
    )

    await db_session.commit()

    created_course = await CourseRepository(
        db_session,
    ).get_by_title_and_teacher(
        title="A Level Physics",
        teacher_id=teacher_user.id,
        school_id=school_id,
    )

    assert result.action == RowProcessingAction.CREATED
    assert result.entity_id is not None
    assert result.message == "Created course 'A Level Physics'."

    assert created_course is not None
    assert created_course.id == result.entity_id
    assert created_course.title == "A Level Physics"
    assert created_course.description == "Advanced physics course"
    assert created_course.teacher_id == teacher_user.id
    assert created_course.school_id == school_id
    assert created_course.published is False


async def test_course_processor_updates_existing_course(
    db_session: AsyncSession,
    school_admin_user: User,
    teacher_user: User,
) -> None:
    school_id = school_admin_user.school_id

    assert school_id is not None
    assert teacher_user.school_id == school_id

    course = Course(
        title="GCSE Biology",
        description="Old description",
        teacher_id=teacher_user.id,
        school_id=school_id,
        published=False,
    )

    db_session.add(course)
    await db_session.commit()
    await db_session.refresh(course)

    course_id = course.id

    result = await process_course_row(
        db_session,
        {
            "title": "GCSE Biology",
            "description": "Updated biology description",
            "teacher_email": teacher_user.email,
        },
        school_id,
    )

    await db_session.commit()
    await db_session.refresh(course)

    assert result.action == RowProcessingAction.UPDATED
    assert result.entity_id == course_id
    assert result.message == "Updated course 'GCSE Biology'."

    assert course.id == course_id
    assert course.description == "Updated biology description"
    assert course.teacher_id == teacher_user.id
    assert course.published is False


async def test_course_processor_preserves_published_state_on_update(
    db_session: AsyncSession,
    school_admin_user: User,
    teacher_user: User,
) -> None:
    school_id = school_admin_user.school_id

    assert school_id is not None
    assert teacher_user.school_id == school_id

    course = Course(
        title="Published Chemistry",
        description="Original description",
        teacher_id=teacher_user.id,
        school_id=school_id,
        published=True,
    )

    db_session.add(course)
    await db_session.commit()
    await db_session.refresh(course)

    result = await process_course_row(
        db_session,
        {
            "title": "Published Chemistry",
            "description": "Updated description",
            "teacher_email": teacher_user.email,
        },
        school_id,
    )

    await db_session.commit()
    await db_session.refresh(course)

    assert result.action == RowProcessingAction.UPDATED
    assert result.entity_id == course.id
    assert course.description == "Updated description"
    assert course.published is True


async def test_course_processor_converts_blank_description_to_none(
    db_session: AsyncSession,
    school_admin_user: User,
    teacher_user: User,
) -> None:
    school_id = school_admin_user.school_id

    assert school_id is not None
    assert teacher_user.school_id == school_id

    result = await process_course_row(
        db_session,
        {
            "title": "Course Without Description",
            "description": "   ",
            "teacher_email": teacher_user.email,
        },
        school_id,
    )

    await db_session.commit()

    created_course = await CourseRepository(
        db_session,
    ).get_by_title_and_teacher(
        title="Course Without Description",
        teacher_id=teacher_user.id,
        school_id=school_id,
    )

    assert result.action == RowProcessingAction.CREATED
    assert created_course is not None
    assert created_course.description is None


async def test_course_processor_rejects_unknown_teacher(
    db_session: AsyncSession,
    school_admin_user: User,
) -> None:
    school_id = school_admin_user.school_id

    assert school_id is not None

    with pytest.raises(
        ValueError,
        match="No teacher with email",
    ):
        await process_course_row(
            db_session,
            {
                "title": "Invalid Teacher Course",
                "teacher_email": "missing.teacher@example.com",
            },
            school_id,
        )

    courses = await CourseRepository(
        db_session,
    ).list_by_school(
        school_id,
    )

    assert all(course.title != "Invalid Teacher Course" for course in courses)


async def test_course_processor_rejects_non_teacher_user(
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
        await process_course_row(
            db_session,
            {
                "title": "Student Owned Course",
                "teacher_email": student_user.email,
            },
            school_id,
        )

    courses = await CourseRepository(
        db_session,
    ).list_by_school(
        school_id,
    )

    assert all(course.title != "Student Owned Course" for course in courses)


@pytest.mark.parametrize(
    "school_id",
    [
        0,
        -1,
        -999,
    ],
)
async def test_course_processor_rejects_invalid_school_id(
    db_session: AsyncSession,
    school_id: int,
) -> None:
    with pytest.raises(
        ValueError,
        match="school_id must be a positive integer",
    ):
        await process_course_row(
            db_session,
            {
                "title": "Invalid School Course",
                "teacher_email": "teacher@example.com",
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
                "teacher_email": "teacher@example.com",
            },
            "Course import field 'title' is required.",
        ),
        (
            {
                "title": "   ",
                "teacher_email": "teacher@example.com",
            },
            "Course import field 'title' cannot be blank.",
        ),
        (
            {
                "title": "A" * 256,
                "teacher_email": "teacher@example.com",
            },
            "Course import field 'title' cannot exceed 255 characters.",
        ),
        (
            {
                "title": "Physics",
            },
            "Course import field 'teacher_email' is required.",
        ),
        (
            {
                "title": "Physics",
                "teacher_email": "   ",
            },
            "Course import field 'teacher_email' cannot be blank.",
        ),
        (
            {
                "title": "Physics",
                "teacher_email": "teacher@example.com",
                "description": "A" * 2001,
            },
            ("Course import field 'description' cannot exceed " "2000 characters."),
        ),
    ],
)
async def test_course_processor_defensively_rejects_malformed_rows(
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
        await process_course_row(
            db_session,
            row,
            1,
        )


async def test_course_repository_school_scoped_lookup(
    db_session: AsyncSession,
    school_admin_user: User,
    teacher_user: User,
) -> None:
    school_id = school_admin_user.school_id

    assert school_id is not None
    assert teacher_user.school_id == school_id

    course = Course(
        title="Repository Lookup Course",
        description=None,
        teacher_id=teacher_user.id,
        school_id=school_id,
        published=False,
    )

    db_session.add(course)
    await db_session.commit()
    await db_session.refresh(course)

    repository = CourseRepository(
        db_session,
    )

    found = await repository.get_by_title_and_teacher(
        title=" Repository Lookup Course ",
        teacher_id=teacher_user.id,
        school_id=school_id,
    )

    missing = await repository.get_by_title_and_teacher(
        title="Repository Lookup Course",
        teacher_id=teacher_user.id,
        school_id=school_id + 999,
    )

    assert found is not None
    assert found.id == course.id
    assert missing is None


async def test_course_repository_exists_checks(
    db_session: AsyncSession,
    school_admin_user: User,
    teacher_user: User,
) -> None:
    school_id = school_admin_user.school_id

    assert school_id is not None
    assert teacher_user.school_id == school_id

    course = Course(
        title="Repository Exists Course",
        description=None,
        teacher_id=teacher_user.id,
        school_id=school_id,
        published=False,
    )

    db_session.add(course)
    await db_session.commit()
    await db_session.refresh(course)

    repository = CourseRepository(
        db_session,
    )

    assert (
        await repository.exists(
            course.id,
        )
        is True
    )

    assert (
        await repository.exists_in_school(
            school_id=school_id,
            course_id=course.id,
        )
        is True
    )

    assert (
        await repository.exists_in_school(
            school_id=school_id,
            title="Repository Exists Course",
            teacher_id=teacher_user.id,
        )
        is True
    )

    assert (
        await repository.exists_in_school(
            school_id=school_id + 999,
            course_id=course.id,
        )
        is False
    )

    assert (
        await repository.exists_in_school(
            school_id=school_id,
            title="Repository Exists Course",
            teacher_id=teacher_user.id,
            exclude_course_id=course.id,
        )
        is False
    )


async def test_course_repository_lists_by_school_and_teacher(
    db_session: AsyncSession,
    school_admin_user: User,
    teacher_user: User,
) -> None:
    school_id = school_admin_user.school_id

    assert school_id is not None
    assert teacher_user.school_id == school_id

    unpublished_course = Course(
        title="Unpublished Repository Course",
        teacher_id=teacher_user.id,
        school_id=school_id,
        published=False,
    )

    published_course = Course(
        title="Published Repository Course",
        teacher_id=teacher_user.id,
        school_id=school_id,
        published=True,
    )

    db_session.add_all(
        [
            unpublished_course,
            published_course,
        ],
    )
    await db_session.commit()

    repository = CourseRepository(
        db_session,
    )

    school_courses = await repository.list_by_school(
        school_id,
    )

    published_courses = await repository.list_by_school(
        school_id,
        published=True,
    )

    teacher_courses = await repository.list_by_teacher(
        teacher_user.id,
        school_id=school_id,
    )

    school_course_ids = {course.id for course in school_courses}

    published_course_ids = {course.id for course in published_courses}

    teacher_course_ids = {course.id for course in teacher_courses}

    assert unpublished_course.id in school_course_ids
    assert published_course.id in school_course_ids

    assert published_course.id in published_course_ids
    assert unpublished_course.id not in published_course_ids

    assert unpublished_course.id in teacher_course_ids
    assert published_course.id in teacher_course_ids


async def test_processing_task_imports_valid_course_row(
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

    batch = build_course_batch(
        school_id=school_id,
        uploaded_by_id=school_admin_user.id,
    )

    db_session.add(batch)
    await db_session.flush()

    row = build_course_row(
        batch_id=batch.id,
        school_id=school_id,
        row_number=2,
        data={
            "title": "Batch Imported Course",
            "description": "Imported course description",
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

        created_course = await CourseRepository(
            verification_db,
        ).get_by_title_and_teacher(
            title="Batch Imported Course",
            teacher_id=teacher_user.id,
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
        assert processed_row.entity_type == "courses"
        assert processed_row.created_entity_id is not None
        assert processed_row.processed_at is not None
        assert processed_row.error_message is not None
        assert "Created course" in processed_row.error_message

        assert created_course is not None
        assert created_course.id == processed_row.created_entity_id
        assert created_course.description == "Imported course description"
        assert created_course.teacher_id == teacher_user.id
        assert created_course.published is False


async def test_processing_task_updates_existing_course(
    db_session: AsyncSession,
    school_admin_user: User,
    teacher_user: User,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    register_import_handlers()

    school_id = school_admin_user.school_id

    assert school_id is not None
    assert teacher_user.school_id == school_id

    course = Course(
        title="Existing Batch Course",
        description="Original description",
        teacher_id=teacher_user.id,
        school_id=school_id,
        published=True,
    )

    db_session.add(course)
    await db_session.commit()
    await db_session.refresh(course)

    course_id = course.id

    task_session_maker = configure_task_session_maker(
        db_session,
        monkeypatch,
    )

    batch = build_course_batch(
        school_id=school_id,
        uploaded_by_id=school_admin_user.id,
        operation=ImportOperation.UPSERT,
    )

    db_session.add(batch)
    await db_session.flush()

    row = build_course_row(
        batch_id=batch.id,
        school_id=school_id,
        row_number=2,
        data={
            "title": "Existing Batch Course",
            "description": "Updated batch description",
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

        updated_course = await get_course_by_id(
            verification_db,
            course_id,
        )

        matching_courses = (
            (
                await verification_db.execute(
                    select(Course).where(
                        Course.title == "Existing Batch Course",
                        Course.teacher_id == teacher_user.id,
                        Course.school_id == school_id,
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
        assert processed_row.entity_type == "courses"
        assert processed_row.created_entity_id == course_id
        assert processed_row.processed_at is not None
        assert processed_row.error_message is not None
        assert "Updated course" in processed_row.error_message

        assert updated_course.description == "Updated batch description"
        assert updated_course.published is True

        assert len(matching_courses) == 1
        assert matching_courses[0].id == course_id


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

    batch = build_course_batch(
        school_id=school_id,
        uploaded_by_id=school_admin_user.id,
    )

    db_session.add(batch)
    await db_session.flush()

    row = build_course_row(
        batch_id=batch.id,
        school_id=school_id,
        row_number=2,
        data={
            "title": "Failed Teacher Course",
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

        courses = await CourseRepository(
            verification_db,
        ).list_by_school(
            school_id,
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

        assert all(course.title != "Failed Teacher Course" for course in courses)


async def test_course_processing_enforces_school_isolation(
    db_session: AsyncSession,
    school_admin_user: User,
    teacher_user: User,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    school_id = school_admin_user.school_id

    assert school_id is not None
    assert teacher_user.school_id == school_id

    configure_task_session_maker(
        db_session,
        monkeypatch,
    )

    batch = build_course_batch(
        school_id=school_id,
        uploaded_by_id=school_admin_user.id,
    )

    db_session.add(batch)
    await db_session.flush()

    row = build_course_row(
        batch_id=batch.id,
        school_id=school_id,
        row_number=2,
        data={
            "title": "Isolated Course",
            "teacher_email": teacher_user.email,
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

    courses = await CourseRepository(
        db_session,
    ).list_by_school(
        school_id,
    )

    assert all(course.title != "Isolated Course" for course in courses)
