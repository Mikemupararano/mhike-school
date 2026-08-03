from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
)

import app.tasks.imports as import_tasks
from app.imports.bootstrap import register_import_handlers
from app.imports.processors.assignments import (
    process_assignment_row,
)
from app.imports.registry import (
    RowProcessingAction,
    get_import_handler,
)
from app.imports.validators.assignments import (
    validate_assignment_row,
)
from app.models.assignment import Assignment
from app.models.course import Course
from app.models.import_batch import (
    ImportBatch,
    ImportOperation,
    ImportRow,
    ImportRowStatus,
    ImportStatus,
)
from app.models.user import User
from app.repositories.assignment import AssignmentRepository
from app.repositories.course import CourseRepository


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


async def create_course(
    db_session: AsyncSession,
    *,
    school_id: int,
    teacher: User,
    title: str = "Physics",
) -> Course:
    """
    Create a course for assignment import tests.
    """

    course = Course(
        title=title,
        description=f"{title} course for assignment import testing.",
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
    await db_session.refresh(
        course,
    )

    return course


async def get_assignment_by_id(
    db: AsyncSession,
    assignment_id: int,
) -> Assignment:
    result = await db.execute(
        select(Assignment).where(
            Assignment.id == assignment_id,
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
    Build a ready assignment import batch.
    """

    return ImportBatch(
        school_id=school_id,
        uploaded_by_id=uploaded_by_id,
        import_type="assignments",
        operation=operation,
        status=ImportStatus.READY,
        original_filename="assignments.csv",
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
    Build one JSON-safe staged assignment import row.
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


def test_assignment_handler_is_registered() -> None:
    register_import_handlers()

    handler = get_import_handler(
        "assignments",
    )

    assert handler.validator is validate_assignment_row
    assert handler.processor is process_assignment_row


def test_validate_assignment_row_success() -> None:
    result = validate_assignment_row(
        {
            "title": " Forces Homework ",
            "course_title": " Physics ",
            "teacher_email": "teacher@example.com",
            "created_by_email": "teacher@example.com",
            "description": " Complete questions 1-10. ",
            "due_date": "2026-09-01T09:00:00",
            "max_score": 100,
            "is_published": False,
            "source_system": "MIS",
        },
    )

    assert result.is_valid is True
    assert result.errors == []
    assert result.warnings == []

    assert result.normalised_data is not None
    assert result.normalised_data["title"] == "Forces Homework"
    assert result.normalised_data["course_title"] == "Physics"
    assert result.normalised_data["description"] == ("Complete questions 1-10.")
    assert result.normalised_data["due_date"] == "2026-09-01T09:00:00"
    assert result.normalised_data["max_score"] == 100
    assert result.normalised_data["is_published"] is False
    assert result.normalised_data["source_system"] == "MIS"


@pytest.mark.parametrize(
    "missing_field",
    [
        "title",
        "course_title",
        "teacher_email",
    ],
)
def test_validate_assignment_requires_core_fields(
    missing_field: str,
) -> None:
    row = {
        "title": "Homework",
        "course_title": "Physics",
        "teacher_email": "teacher@example.com",
    }

    row.pop(
        missing_field,
    )

    result = validate_assignment_row(
        row,
    )

    assert result.is_valid is False
    assert result.normalised_data is None


def test_validate_assignment_rejects_invalid_email() -> None:
    result = validate_assignment_row(
        {
            "title": "Homework",
            "course_title": "Physics",
            "teacher_email": "not-an-email",
        },
    )

    assert result.is_valid is False
    assert result.normalised_data is None


def test_validate_assignment_rejects_invalid_creator_email() -> None:
    result = validate_assignment_row(
        {
            "title": "Homework",
            "course_title": "Physics",
            "teacher_email": "teacher@example.com",
            "created_by_email": "not-an-email",
        },
    )

    assert result.is_valid is False
    assert result.normalised_data is None


def test_validate_assignment_rejects_invalid_due_date() -> None:
    result = validate_assignment_row(
        {
            "title": "Homework",
            "course_title": "Physics",
            "teacher_email": "teacher@example.com",
            "due_date": "tomorrow morning",
        },
    )

    assert result.is_valid is False
    assert result.normalised_data is None


def test_validate_assignment_rejects_invalid_max_score() -> None:
    result = validate_assignment_row(
        {
            "title": "Homework",
            "course_title": "Physics",
            "teacher_email": "teacher@example.com",
            "max_score": 0,
        },
    )

    assert result.is_valid is False
    assert result.normalised_data is None


def test_validate_assignment_rejects_long_fields() -> None:
    result = validate_assignment_row(
        {
            "title": "A" * 256,
            "course_title": "B" * 256,
            "teacher_email": "teacher@example.com",
        },
    )

    assert result.is_valid is False
    assert result.normalised_data is None


def test_validate_assignment_accepts_iso_datetime() -> None:
    result = validate_assignment_row(
        {
            "title": "Homework",
            "course_title": "Physics",
            "teacher_email": "teacher@example.com",
            "due_date": "2026-09-01T09:00:00",
        },
    )

    assert result.is_valid is True


def test_validate_assignment_accepts_zulu_datetime() -> None:
    result = validate_assignment_row(
        {
            "title": "Homework",
            "course_title": "Physics",
            "teacher_email": "teacher@example.com",
            "due_date": "2026-09-01T09:00:00Z",
        },
    )

    assert result.is_valid is True


def test_validate_assignment_defaults() -> None:
    result = validate_assignment_row(
        {
            "title": "Homework",
            "course_title": "Physics",
            "teacher_email": "teacher@example.com",
        },
    )

    assert result.is_valid is True
    assert result.normalised_data is not None

    data = result.normalised_data

    assert data["max_score"] == 100
    assert data["is_published"] is False
    assert data["description"] is None
    assert data["created_by_email"] is None
    assert data["due_date"] is None


@pytest.mark.asyncio
async def test_processor_creates_assignment_with_teacher_as_creator(
    db_session: AsyncSession,
    school_admin_user: User,
    teacher_user: User,
) -> None:
    school_id = school_admin_user.school_id

    assert school_id is not None
    assert teacher_user.school_id == school_id

    course = await create_course(
        db_session,
        school_id=school_id,
        teacher=teacher_user,
    )

    result = await process_assignment_row(
        db_session,
        {
            "title": " Forces Homework ",
            "course_title": course.title,
            "teacher_email": teacher_user.email.upper(),
            "description": " Complete questions 1-10. ",
            "due_date": "2026-09-01T09:00:00",
            "max_score": 80,
            "is_published": True,
        },
        school_id,
    )

    await db_session.commit()

    assignment = await get_assignment_by_id(
        db_session,
        result.entity_id,
    )

    assert result.action == RowProcessingAction.CREATED
    assert result.message == "Created assignment 'Forces Homework'."

    assert assignment.school_id == school_id
    assert assignment.course_id == course.id
    assert assignment.created_by == teacher_user.id
    assert assignment.title == "Forces Homework"
    assert assignment.description == "Complete questions 1-10."
    assert assignment.due_date == datetime(2026, 9, 1, 9, 0)
    assert assignment.max_score == 80
    assert assignment.is_published is True


@pytest.mark.asyncio
async def test_processor_creates_assignment_with_explicit_staff_creator(
    db_session: AsyncSession,
    school_admin_user: User,
    teacher_user: User,
) -> None:
    school_id = school_admin_user.school_id

    assert school_id is not None

    course = await create_course(
        db_session,
        school_id=school_id,
        teacher=teacher_user,
    )

    result = await process_assignment_row(
        db_session,
        {
            "title": "Admin-Created Homework",
            "course_title": course.title,
            "teacher_email": teacher_user.email,
            "created_by_email": school_admin_user.email,
            "max_score": 50,
        },
        school_id,
    )

    await db_session.commit()

    assignment = await get_assignment_by_id(
        db_session,
        result.entity_id,
    )

    assert result.action == RowProcessingAction.CREATED
    assert assignment.created_by == school_admin_user.id
    assert assignment.course_id == course.id
    assert assignment.max_score == 50
    assert assignment.is_published is False


@pytest.mark.asyncio
async def test_processor_updates_existing_assignment(
    db_session: AsyncSession,
    school_admin_user: User,
    teacher_user: User,
) -> None:
    school_id = school_admin_user.school_id

    assert school_id is not None

    course = await create_course(
        db_session,
        school_id=school_id,
        teacher=teacher_user,
    )

    assignment = Assignment(
        title="Forces Homework",
        description="Old description",
        due_date=datetime(2026, 9, 1, 9, 0),
        max_score=50,
        is_published=False,
        course_id=course.id,
        school_id=school_id,
        created_by=teacher_user.id,
    )

    await AssignmentRepository(
        db_session,
    ).create(
        assignment,
    )

    await db_session.commit()
    await db_session.refresh(
        assignment,
    )

    assignment_id = assignment.id

    result = await process_assignment_row(
        db_session,
        {
            "title": assignment.title,
            "course_title": course.title,
            "teacher_email": teacher_user.email,
            "created_by_email": school_admin_user.email,
            "description": "Updated description",
            "due_date": "2026-09-05T15:30:00",
            "max_score": 120,
            "is_published": True,
        },
        school_id,
    )

    await db_session.commit()
    await db_session.refresh(
        assignment,
    )

    assert result.action == RowProcessingAction.UPDATED
    assert result.entity_id == assignment_id
    assert result.message == "Updated assignment 'Forces Homework'."

    assert assignment.id == assignment_id
    assert assignment.description == "Updated description"
    assert assignment.due_date == datetime(2026, 9, 5, 15, 30)
    assert assignment.max_score == 120
    assert assignment.is_published is True
    assert assignment.created_by == school_admin_user.id


@pytest.mark.asyncio
async def test_processor_accepts_zulu_due_date(
    db_session: AsyncSession,
    school_admin_user: User,
    teacher_user: User,
) -> None:
    school_id = school_admin_user.school_id

    assert school_id is not None

    course = await create_course(
        db_session,
        school_id=school_id,
        teacher=teacher_user,
    )

    result = await process_assignment_row(
        db_session,
        {
            "title": "Zulu Deadline Homework",
            "course_title": course.title,
            "teacher_email": teacher_user.email,
            "due_date": "2026-09-01T09:00:00Z",
        },
        school_id,
    )

    await db_session.commit()

    assignment = await get_assignment_by_id(
        db_session,
        result.entity_id,
    )

    assert result.action == RowProcessingAction.CREATED
    assert assignment.due_date is not None
    assert assignment.due_date.year == 2026
    assert assignment.due_date.month == 9
    assert assignment.due_date.day == 1
    assert assignment.due_date.hour == 9


@pytest.mark.asyncio
async def test_processor_rejects_invalid_school_id(
    db_session: AsyncSession,
) -> None:
    with pytest.raises(
        ValueError,
        match="school_id must be a positive integer",
    ):
        await process_assignment_row(
            db_session,
            {
                "title": "Homework",
                "course_title": "Physics",
                "teacher_email": "teacher@example.com",
            },
            0,
        )


@pytest.mark.asyncio
async def test_processor_rejects_missing_teacher(
    db_session: AsyncSession,
    school_admin_user: User,
) -> None:
    school_id = school_admin_user.school_id

    assert school_id is not None

    with pytest.raises(
        ValueError,
        match="No teacher with email",
    ):
        await process_assignment_row(
            db_session,
            {
                "title": "Homework",
                "course_title": "Physics",
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

    with pytest.raises(
        ValueError,
        match="is not registered as a teacher",
    ):
        await process_assignment_row(
            db_session,
            {
                "title": "Homework",
                "course_title": "Physics",
                "teacher_email": student_user.email,
            },
            school_id,
        )


@pytest.mark.asyncio
async def test_processor_rejects_missing_course(
    db_session: AsyncSession,
    school_admin_user: User,
    teacher_user: User,
) -> None:
    school_id = school_admin_user.school_id

    assert school_id is not None

    with pytest.raises(
        ValueError,
        match="No course titled",
    ):
        await process_assignment_row(
            db_session,
            {
                "title": "Homework",
                "course_title": "Unknown Course",
                "teacher_email": teacher_user.email,
            },
            school_id,
        )


@pytest.mark.asyncio
async def test_processor_rejects_missing_creator(
    db_session: AsyncSession,
    school_admin_user: User,
    teacher_user: User,
) -> None:
    school_id = school_admin_user.school_id

    assert school_id is not None

    course = await create_course(
        db_session,
        school_id=school_id,
        teacher=teacher_user,
    )

    with pytest.raises(
        ValueError,
        match="No assignment creator with email",
    ):
        await process_assignment_row(
            db_session,
            {
                "title": "Homework",
                "course_title": course.title,
                "teacher_email": teacher_user.email,
                "created_by_email": "missing@example.com",
            },
            school_id,
        )


@pytest.mark.asyncio
async def test_processor_rejects_non_staff_creator(
    db_session: AsyncSession,
    school_admin_user: User,
    teacher_user: User,
    student_user: User,
) -> None:
    school_id = school_admin_user.school_id

    assert school_id is not None

    course = await create_course(
        db_session,
        school_id=school_id,
        teacher=teacher_user,
    )

    with pytest.raises(
        ValueError,
        match="is not registered as an authorised staff member",
    ):
        await process_assignment_row(
            db_session,
            {
                "title": "Homework",
                "course_title": course.title,
                "teacher_email": teacher_user.email,
                "created_by_email": student_user.email,
            },
            school_id,
        )


@pytest.mark.asyncio
async def test_processor_rejects_invalid_due_date(
    db_session: AsyncSession,
) -> None:
    with pytest.raises(
        ValueError,
        match="must be a valid ISO datetime",
    ):
        await process_assignment_row(
            db_session,
            {
                "title": "Homework",
                "course_title": "Physics",
                "teacher_email": "teacher@example.com",
                "due_date": "tomorrow morning",
            },
            1,
        )


@pytest.mark.asyncio
async def test_processor_rejects_invalid_max_score(
    db_session: AsyncSession,
) -> None:
    with pytest.raises(
        ValueError,
        match="must be a positive integer",
    ):
        await process_assignment_row(
            db_session,
            {
                "title": "Homework",
                "course_title": "Physics",
                "teacher_email": "teacher@example.com",
                "max_score": 0,
            },
            1,
        )


@pytest.mark.asyncio
async def test_repository_assignment_lookup_and_lists(
    db_session: AsyncSession,
    school_admin_user: User,
    teacher_user: User,
) -> None:
    school_id = school_admin_user.school_id

    assert school_id is not None

    course = await create_course(
        db_session,
        school_id=school_id,
        teacher=teacher_user,
    )

    published_assignment = Assignment(
        title="Published Homework",
        description=None,
        due_date=None,
        max_score=100,
        is_published=True,
        course_id=course.id,
        school_id=school_id,
        created_by=teacher_user.id,
    )

    draft_assignment = Assignment(
        title="Draft Homework",
        description=None,
        due_date=None,
        max_score=50,
        is_published=False,
        course_id=course.id,
        school_id=school_id,
        created_by=teacher_user.id,
    )

    repository = AssignmentRepository(
        db_session,
    )

    await repository.create(
        published_assignment,
    )
    await repository.create(
        draft_assignment,
    )

    await db_session.commit()

    found = await repository.get_by_title_and_course(
        title=" Published Homework ",
        course_id=course.id,
        school_id=school_id,
    )

    school_assignments = await repository.list_by_school(
        school_id,
    )

    creator_assignments = await repository.list_by_creator(
        teacher_user.id,
        school_id=school_id,
    )

    published_assignments = await repository.list_published_for_school(
        school_id,
    )

    assert found is not None
    assert found.id == published_assignment.id

    relevant_school_ids = {
        assignment.id
        for assignment in school_assignments
        if assignment.id
        in {
            published_assignment.id,
            draft_assignment.id,
        }
    }

    relevant_creator_ids = {
        assignment.id
        for assignment in creator_assignments
        if assignment.id
        in {
            published_assignment.id,
            draft_assignment.id,
        }
    }

    relevant_published_ids = {
        assignment.id
        for assignment in published_assignments
        if assignment.id
        in {
            published_assignment.id,
            draft_assignment.id,
        }
    }

    assert relevant_school_ids == {
        published_assignment.id,
        draft_assignment.id,
    }

    assert relevant_creator_ids == {
        published_assignment.id,
        draft_assignment.id,
    }

    assert relevant_published_ids == {
        published_assignment.id,
    }


@pytest.mark.asyncio
async def test_processing_task_creates_assignment(
    db_session: AsyncSession,
    school_admin_user: User,
    teacher_user: User,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    register_import_handlers()

    school_id = school_admin_user.school_id

    assert school_id is not None

    course = await create_course(
        db_session,
        school_id=school_id,
        teacher=teacher_user,
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
            "title": "Batch Homework",
            "course_title": course.title,
            "teacher_email": teacher_user.email,
            "created_by_email": None,
            "description": "Created by the background import task.",
            "due_date": "2026-10-01T09:00:00",
            "max_score": 75,
            "is_published": False,
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
        assert processed_row.entity_type == "assignments"
        assert processed_row.created_entity_id is not None
        assert processed_row.processed_at is not None
        assert processed_row.error_message is not None
        assert "Created assignment" in processed_row.error_message

        assignment = await get_assignment_by_id(
            verification_db,
            processed_row.created_entity_id,
        )

        assert assignment.course_id == course.id
        assert assignment.created_by == teacher_user.id
        assert assignment.title == "Batch Homework"
        assert assignment.max_score == 75


@pytest.mark.asyncio
async def test_processing_task_updates_existing_assignment(
    db_session: AsyncSession,
    school_admin_user: User,
    teacher_user: User,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    register_import_handlers()

    school_id = school_admin_user.school_id

    assert school_id is not None

    course = await create_course(
        db_session,
        school_id=school_id,
        teacher=teacher_user,
    )

    assignment = Assignment(
        title="Existing Batch Homework",
        description="Old description",
        due_date=None,
        max_score=50,
        is_published=False,
        course_id=course.id,
        school_id=school_id,
        created_by=teacher_user.id,
    )

    await AssignmentRepository(
        db_session,
    ).create(
        assignment,
    )

    await db_session.commit()
    await db_session.refresh(
        assignment,
    )

    assignment_id = assignment.id

    task_session_maker = configure_task_session_maker(
        db_session,
        monkeypatch,
    )

    batch = build_assignment_batch(
        school_id=school_id,
        uploaded_by_id=school_admin_user.id,
        operation=ImportOperation.UPSERT,
    )

    db_session.add(
        batch,
    )
    await db_session.flush()

    row = build_assignment_row(
        batch_id=batch.id,
        school_id=school_id,
        data={
            "title": assignment.title,
            "course_title": course.title,
            "teacher_email": teacher_user.email,
            "created_by_email": school_admin_user.email,
            "description": "Updated by background processing.",
            "due_date": "2026-11-01T12:00:00",
            "max_score": 150,
            "is_published": True,
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

        updated_assignment = await get_assignment_by_id(
            verification_db,
            assignment_id,
        )

        assert summary["status"] == ImportStatus.COMPLETED.value
        assert summary["successful_rows"] == 1
        assert summary["imported_rows"] == 0
        assert summary["updated_rows"] == 1
        assert summary["failed_rows"] == 0

        assert processed_row.status == ImportRowStatus.UPDATED
        assert processed_row.created_entity_id == assignment_id
        assert processed_row.error_message is not None
        assert "Updated assignment" in processed_row.error_message

        assert updated_assignment.description == ("Updated by background processing.")
        assert updated_assignment.max_score == 150
        assert updated_assignment.is_published is True
        assert updated_assignment.created_by == school_admin_user.id


@pytest.mark.asyncio
async def test_assignment_processing_enforces_school_isolation(
    db_session: AsyncSession,
    school_admin_user: User,
    teacher_user: User,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    school_id = school_admin_user.school_id

    assert school_id is not None

    course = await create_course(
        db_session,
        school_id=school_id,
        teacher=teacher_user,
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
            "title": "Isolated Homework",
            "course_title": course.title,
            "teacher_email": teacher_user.email,
            "created_by_email": None,
            "description": None,
            "due_date": None,
            "max_score": 100,
            "is_published": False,
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

    assignment = await AssignmentRepository(
        db_session,
    ).get_by_title_and_course(
        title="Isolated Homework",
        course_id=course.id,
        school_id=school_id,
    )

    assert assignment is None
