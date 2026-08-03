from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.imports.processors.assignment_submissions import (
    process_assignment_submission_row,
)
from app.imports.registry import RowProcessingAction
from app.imports.validators.assignment_submissions import (
    validate_assignment_submission_row,
)
from app.models.assignment import Assignment
from app.models.assignment_submission import AssignmentSubmission
from app.models.course import Course
from app.models.user import User


def test_validate_assignment_submission_success() -> None:
    result = validate_assignment_submission_row(
        {
            "assignment_title": "Homework 1",
            "course_title": "Physics",
            "teacher_email": "teacher@example.com",
            "student_email": "student@example.com",
            "submission_text": "My work",
        },
    )

    assert result.is_valid is True
    assert result.errors == []


def test_validate_assignment_submission_requires_assignment() -> None:
    result = validate_assignment_submission_row(
        {
            "course_title": "Physics",
            "teacher_email": "teacher@example.com",
            "student_email": "student@example.com",
        },
    )

    assert result.is_valid is False


def test_validate_assignment_submission_requires_course() -> None:
    result = validate_assignment_submission_row(
        {
            "assignment_title": "Homework",
            "teacher_email": "teacher@example.com",
            "student_email": "student@example.com",
        },
    )

    assert result.is_valid is False


def test_validate_assignment_submission_requires_teacher() -> None:
    result = validate_assignment_submission_row(
        {
            "assignment_title": "Homework",
            "course_title": "Physics",
            "student_email": "student@example.com",
        },
    )

    assert result.is_valid is False


def test_validate_assignment_submission_requires_student() -> None:
    result = validate_assignment_submission_row(
        {
            "assignment_title": "Homework",
            "course_title": "Physics",
            "teacher_email": "teacher@example.com",
        },
    )

    assert result.is_valid is False


def test_validate_assignment_submission_invalid_teacher_email() -> None:
    result = validate_assignment_submission_row(
        {
            "assignment_title": "Homework",
            "course_title": "Physics",
            "teacher_email": "bad-email",
            "student_email": "student@example.com",
        },
    )

    assert result.is_valid is False


def test_validate_assignment_submission_invalid_student_email() -> None:
    result = validate_assignment_submission_row(
        {
            "assignment_title": "Homework",
            "course_title": "Physics",
            "teacher_email": "teacher@example.com",
            "student_email": "bad-email",
        },
    )

    assert result.is_valid is False


def test_validate_assignment_submission_rejects_invalid_status() -> None:
    result = validate_assignment_submission_row(
        {
            "assignment_title": "Homework",
            "course_title": "Physics",
            "teacher_email": "teacher@example.com",
            "student_email": "student@example.com",
            "status": "reviewed",
        },
    )

    assert result.is_valid is False
    assert result.normalised_data is None


def test_validate_graded_submission_requires_score() -> None:
    result = validate_assignment_submission_row(
        {
            "assignment_title": "Homework",
            "course_title": "Physics",
            "teacher_email": "teacher@example.com",
            "student_email": "student@example.com",
            "status": "graded",
            "graded_by_email": "teacher@example.com",
        },
    )

    assert result.is_valid is False
    assert result.normalised_data is None


def test_validate_graded_submission_requires_grader() -> None:
    result = validate_assignment_submission_row(
        {
            "assignment_title": "Homework",
            "course_title": "Physics",
            "teacher_email": "teacher@example.com",
            "student_email": "student@example.com",
            "status": "graded",
            "score": 75,
        },
    )

    assert result.is_valid is False
    assert result.normalised_data is None


def test_validate_assignment_submission_rejects_negative_score() -> None:
    result = validate_assignment_submission_row(
        {
            "assignment_title": "Homework",
            "course_title": "Physics",
            "teacher_email": "teacher@example.com",
            "student_email": "student@example.com",
            "status": "graded",
            "score": -1,
            "graded_by_email": "teacher@example.com",
        },
    )

    assert result.is_valid is False
    assert result.normalised_data is None


def test_validate_assignment_submission_accepts_iso_timestamps() -> None:
    result = validate_assignment_submission_row(
        {
            "assignment_title": "Homework",
            "course_title": "Physics",
            "teacher_email": "teacher@example.com",
            "student_email": "student@example.com",
            "status": "graded",
            "submitted_at": "2026-09-01T09:00:00Z",
            "score": 75,
            "graded_by_email": "teacher@example.com",
            "graded_at": "2026-09-02T10:30:00+00:00",
        },
    )

    assert result.is_valid is True
    assert result.errors == []


def test_validate_assignment_submission_rejects_invalid_timestamp() -> None:
    result = validate_assignment_submission_row(
        {
            "assignment_title": "Homework",
            "course_title": "Physics",
            "teacher_email": "teacher@example.com",
            "student_email": "student@example.com",
            "submitted_at": "yesterday morning",
        },
    )

    assert result.is_valid is False
    assert result.normalised_data is None


@pytest.mark.asyncio
async def test_process_assignment_submission_invalid_school(
    db_session: AsyncSession,
) -> None:
    with pytest.raises(
        ValueError,
        match="school_id must be a positive integer",
    ):
        await process_assignment_submission_row(
            db_session,
            {
                "assignment_title": "Homework",
                "course_title": "Physics",
                "teacher_email": "teacher@example.com",
                "student_email": "student@example.com",
            },
            0,
        )


@pytest.mark.asyncio
async def test_process_assignment_submission_missing_teacher(
    db_session: AsyncSession,
    school_admin_user: User,
) -> None:
    school_id = school_admin_user.school_id

    assert school_id is not None

    with pytest.raises(
        ValueError,
        match="No teacher with email",
    ):
        await process_assignment_submission_row(
            db_session,
            {
                "assignment_title": "Homework",
                "course_title": "Physics",
                "teacher_email": "missing@example.com",
                "student_email": "student@example.com",
            },
            school_id,
        )


@pytest.mark.asyncio
async def test_process_assignment_submission_rejects_non_teacher(
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
        await process_assignment_submission_row(
            db_session,
            {
                "assignment_title": "Homework",
                "course_title": "Physics",
                "teacher_email": student_user.email,
                "student_email": student_user.email,
            },
            school_id,
        )


@pytest.mark.asyncio
async def test_process_assignment_submission_missing_student(
    db_session: AsyncSession,
    school_admin_user: User,
    teacher_user: User,
) -> None:
    school_id = school_admin_user.school_id

    assert school_id is not None
    assert teacher_user.school_id == school_id

    with pytest.raises(
        ValueError,
        match="No student with email",
    ):
        await process_assignment_submission_row(
            db_session,
            {
                "assignment_title": "Homework",
                "course_title": "Physics",
                "teacher_email": teacher_user.email,
                "student_email": "missing@example.com",
            },
            school_id,
        )


@pytest.mark.asyncio
async def test_process_assignment_submission_rejects_non_student(
    db_session: AsyncSession,
    school_admin_user: User,
    teacher_user: User,
) -> None:
    school_id = school_admin_user.school_id

    assert school_id is not None

    with pytest.raises(
        ValueError,
        match="is not registered as a student",
    ):
        await process_assignment_submission_row(
            db_session,
            {
                "assignment_title": "Homework",
                "course_title": "Physics",
                "teacher_email": teacher_user.email,
                "student_email": teacher_user.email,
            },
            school_id,
        )


@pytest.mark.asyncio
async def test_process_assignment_submission_missing_course(
    db_session: AsyncSession,
    school_admin_user: User,
    teacher_user: User,
    student_user: User,
) -> None:
    school_id = school_admin_user.school_id

    assert school_id is not None
    assert teacher_user.school_id == school_id
    assert student_user.school_id == school_id

    with pytest.raises(
        ValueError,
        match="No course titled",
    ):
        await process_assignment_submission_row(
            db_session,
            {
                "assignment_title": "Homework",
                "course_title": "Unknown Course",
                "teacher_email": teacher_user.email,
                "student_email": student_user.email,
            },
            school_id,
        )


@pytest.mark.asyncio
async def test_process_assignment_submission_missing_assignment(
    db_session: AsyncSession,
    school_admin_user: User,
    teacher_user: User,
    student_user: User,
) -> None:
    school_id = school_admin_user.school_id

    assert school_id is not None

    course = Course(
        title="Physics",
        description="Course for submission-import testing.",
        teacher_id=teacher_user.id,
        school_id=school_id,
        published=True,
    )

    db_session.add(
        course,
    )
    await db_session.commit()
    await db_session.refresh(
        course,
    )

    with pytest.raises(
        ValueError,
        match="No assignment titled",
    ):
        await process_assignment_submission_row(
            db_session,
            {
                "assignment_title": "Missing Homework",
                "course_title": course.title,
                "teacher_email": teacher_user.email,
                "student_email": student_user.email,
            },
            school_id,
        )


@pytest.mark.asyncio
async def test_process_assignment_submission_creates_submission(
    db_session: AsyncSession,
    school_admin_user: User,
    teacher_user: User,
    student_user: User,
) -> None:
    school_id = school_admin_user.school_id

    assert school_id is not None
    assert teacher_user.school_id == school_id
    assert student_user.school_id == school_id

    course = Course(
        title="Physics",
        description="Physics course",
        teacher_id=teacher_user.id,
        school_id=school_id,
        published=True,
    )

    db_session.add(
        course,
    )
    await db_session.commit()
    await db_session.refresh(
        course,
    )

    assignment = Assignment(
        title="Homework 1",
        description="Complete questions 1-10",
        course_id=course.id,
        school_id=school_id,
        created_by=teacher_user.id,
        max_score=100,
        is_published=True,
    )

    db_session.add(
        assignment,
    )
    await db_session.commit()
    await db_session.refresh(
        assignment,
    )

    result = await process_assignment_submission_row(
        db_session,
        {
            "assignment_title": assignment.title,
            "course_title": course.title,
            "teacher_email": teacher_user.email,
            "student_email": student_user.email,
            "submission_text": "My homework",
            "status": "submitted",
        },
        school_id,
    )

    await db_session.commit()

    assert result.action == RowProcessingAction.CREATED
    assert result.entity_id is not None

    submission = await db_session.get(
        AssignmentSubmission,
        result.entity_id,
    )

    assert submission is not None
    assert submission.assignment_id == assignment.id
    assert submission.student_id == student_user.id
    assert submission.school_id == school_id
    assert submission.submission_text == "My homework"
    assert submission.status == "submitted"
    assert submission.submitted_at is not None


@pytest.mark.asyncio
async def test_process_assignment_submission_updates_existing_submission(
    db_session: AsyncSession,
    school_admin_user: User,
    teacher_user: User,
    student_user: User,
) -> None:
    school_id = school_admin_user.school_id

    assert school_id is not None
    assert teacher_user.school_id == school_id
    assert student_user.school_id == school_id

    course = Course(
        title="Physics",
        description="Physics course",
        teacher_id=teacher_user.id,
        school_id=school_id,
        published=True,
    )

    db_session.add(
        course,
    )
    await db_session.commit()
    await db_session.refresh(
        course,
    )

    assignment = Assignment(
        title="Homework 1",
        description="Complete questions",
        course_id=course.id,
        school_id=school_id,
        created_by=teacher_user.id,
        max_score=100,
        is_published=True,
    )

    db_session.add(
        assignment,
    )
    await db_session.commit()
    await db_session.refresh(
        assignment,
    )

    submission = AssignmentSubmission(
        assignment_id=assignment.id,
        student_id=student_user.id,
        school_id=school_id,
        submission_text="Old work",
        attachment_url=None,
        status="submitted",
    )

    db_session.add(
        submission,
    )
    await db_session.commit()
    await db_session.refresh(
        submission,
    )

    submission_id = submission.id

    result = await process_assignment_submission_row(
        db_session,
        {
            "assignment_title": assignment.title,
            "course_title": course.title,
            "teacher_email": teacher_user.email,
            "student_email": student_user.email,
            "submission_text": "Updated work",
            "attachment_url": "https://example.com/updated-work.pdf",
            "status": "submitted",
        },
        school_id,
    )

    await db_session.commit()
    await db_session.refresh(
        submission,
    )

    assert result.action == RowProcessingAction.UPDATED
    assert result.entity_id == submission_id
    assert submission.submission_text == "Updated work"
    assert submission.attachment_url == ("https://example.com/updated-work.pdf")
    assert submission.status == "submitted"
    assert submission.submitted_at is not None
