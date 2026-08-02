from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.imports.registry import (
    RowProcessingAction,
    RowProcessingResult,
)
from app.models.class_group import ClassGroup
from app.models.user import UserRole
from app.repositories.class_group import ClassGroupRepository
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
            f"Class import field '{field_name}' is required.",
        )

    cleaned = str(value).strip()

    if not cleaned:
        raise ValueError(
            f"Class import field '{field_name}' cannot be blank.",
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
    teacher_email: str | None,
    school_id: int,
) -> int | None:
    """
    Resolve an optional teacher email to a same-school teacher user.

    The class import deliberately requires the explicit teacher role, matching
    the existing ClassService behaviour. Broader teaching permissions are not
    used here because imports should not silently widen assignment rules.
    """

    if teacher_email is None:
        return None

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


async def process_class_row(
    db: AsyncSession,
    row: dict[str, Any],
    school_id: int,
) -> RowProcessingResult:
    """
    Create or update one class group from validated import data.

    Matching is performed using the class name within the current school.

    Behaviour:

    - create a class when no matching school-scoped name exists;
    - update the optional teacher assignment when the class already exists;
    - leave enrolments to the separate enrolment import workflow;
    - never commit or roll back the session.

    Transaction ownership belongs to the generic import service or task.
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

    name = _required_string(
        row,
        "name",
    )

    if len(name) > 255:
        raise ValueError(
            "Class import field 'name' cannot exceed 255 characters.",
        )

    teacher_email = _optional_string(
        row,
        "teacher_email",
    )

    teacher_id = await _resolve_teacher_id(
        db,
        teacher_email=teacher_email,
        school_id=school_id,
    )

    repository = ClassGroupRepository(
        db,
    )

    existing_class = await repository.get_by_name_and_school(
        name=name,
        school_id=school_id,
        include_relationships=False,
    )

    if existing_class is None:
        class_group = ClassGroup(
            name=name,
            school_id=school_id,
            teacher_id=teacher_id,
        )

        await repository.create(
            class_group,
        )

        return RowProcessingResult(
            action=RowProcessingAction.CREATED,
            entity_id=class_group.id,
            message=f"Created class '{name}'.",
        )

    existing_class.name = name
    existing_class.teacher_id = teacher_id

    await repository.save(
        existing_class,
    )

    return RowProcessingResult(
        action=RowProcessingAction.UPDATED,
        entity_id=existing_class.id,
        message=f"Updated class '{name}'.",
    )
