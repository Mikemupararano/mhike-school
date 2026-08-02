from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.imports.registry import (
    RowProcessingAction,
    RowProcessingResult,
)
from app.models.course import Course
from app.models.user import UserRole
from app.repositories.course import CourseRepository
from app.repositories.user import UserRepository


def _required_string(
    row: dict[str, Any],
    field_name: str,
) -> str:
    """
    Return a required, trimmed string value from an imported row.

    Validation should normally reject malformed rows before processing.
    These checks protect direct processor calls and defensive code paths.
    """

    value = row.get(field_name)

    if value is None:
        raise ValueError(
            f"Course import field '{field_name}' is required.",
        )

    cleaned = str(value).strip()

    if not cleaned:
        raise ValueError(
            f"Course import field '{field_name}' cannot be blank.",
        )

    return cleaned


def _optional_string(
    row: dict[str, Any],
    field_name: str,
) -> str | None:
    """
    Return an optional, trimmed string value.
    """

    value = row.get(field_name)

    if value is None:
        return None

    cleaned = str(value).strip()

    return cleaned or None


async def _resolve_teacher_id(
    db: AsyncSession,
    *,
    teacher_email: str,
    school_id: int,
) -> int:
    """
    Resolve a teacher email to a same-school teacher user.

    Course ownership requires an explicit teacher role, matching the
    existing course and class assignment rules.
    """

    normalised_email = teacher_email.lower()

    teacher = await UserRepository(
        db,
    ).get_by_email(
        email=normalised_email,
        school_id=school_id,
    )

    if teacher is None:
        raise ValueError(
            f"No teacher with email '{normalised_email}' exists " "in this school.",
        )

    if not teacher.has_role(
        UserRole.TEACHER,
    ):
        raise ValueError(
            f"The user with email '{normalised_email}' is not "
            "registered as a teacher in this school.",
        )

    return teacher.id


async def process_course_row(
    db: AsyncSession,
    row: dict[str, Any],
    school_id: int,
) -> RowProcessingResult:
    """
    Create or update one course from validated import data.

    Matching is performed using the combination of:

    - school_id;
    - teacher_id;
    - title.

    Imported courses always remain unpublished. Publishing is a separate,
    explicit workflow and is never performed implicitly by an import.

    Transaction ownership belongs to the generic import service or task.
    This processor therefore never commits or rolls back the session.
    """

    if (
        not isinstance(
            school_id,
            int,
        )
        or isinstance(
            school_id,
            bool,
        )
        or school_id < 1
    ):
        raise ValueError(
            "school_id must be a positive integer.",
        )

    title = _required_string(
        row,
        "title",
    )

    if len(title) > 255:
        raise ValueError(
            "Course import field 'title' cannot exceed 255 characters.",
        )

    teacher_email = _required_string(
        row,
        "teacher_email",
    )

    description = _optional_string(
        row,
        "description",
    )

    if description is not None and len(description) > 2000:
        raise ValueError(
            "Course import field 'description' cannot exceed 2000 characters.",
        )

    teacher_id = await _resolve_teacher_id(
        db,
        teacher_email=teacher_email,
        school_id=school_id,
    )

    repository = CourseRepository(
        db,
    )

    existing_course = await repository.get_by_title_and_teacher(
        title=title,
        teacher_id=teacher_id,
        school_id=school_id,
        include_relationships=False,
    )

    if existing_course is None:
        course = Course(
            title=title,
            description=description,
            teacher_id=teacher_id,
            school_id=school_id,
            published=False,
        )

        await repository.create(
            course,
        )

        return RowProcessingResult(
            action=RowProcessingAction.CREATED,
            entity_id=course.id,
            message=f"Created course '{title}'.",
        )

    existing_course.title = title
    existing_course.description = description

    # Preserve the publication state of an existing course.
    # An import must never publish or unpublish a course implicitly.
    existing_course.teacher_id = teacher_id

    await repository.save(
        existing_course,
    )

    return RowProcessingResult(
        action=RowProcessingAction.UPDATED,
        entity_id=existing_course.id,
        message=f"Updated course '{title}'.",
    )
