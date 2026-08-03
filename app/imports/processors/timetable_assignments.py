from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.imports.registry import (
    RowProcessingAction,
    RowProcessingResult,
)
from app.models.class_group import ClassGroup
from app.models.timetable_assignment import (
    TimetableAssignment,
    TimetableAssignmentType,
)
from app.models.user import User, UserRole
from app.repositories.class_group import ClassGroupRepository
from app.repositories.timetable import TimetableRepository
from app.repositories.user import UserRepository


def _required_string(
    row: dict[str, Any],
    field_name: str,
    *,
    max_length: int,
) -> str:
    """
    Return a required, trimmed string within the supplied length limit.

    The validator should normally reject malformed rows before processing.
    These checks protect direct processor calls and background-task paths.
    """

    value = row.get(field_name)

    if value is None:
        raise ValueError(
            f"Timetable assignment import field " f"'{field_name}' is required.",
        )

    cleaned = str(value).strip()

    if not cleaned:
        raise ValueError(
            f"Timetable assignment import field " f"'{field_name}' cannot be blank.",
        )

    if len(cleaned) > max_length:
        raise ValueError(
            f"Timetable assignment import field "
            f"'{field_name}' cannot exceed "
            f"{max_length} characters.",
        )

    return cleaned


def _optional_string(
    row: dict[str, Any],
    field_name: str,
    *,
    max_length: int | None = None,
) -> str | None:
    """
    Return a trimmed optional string.
    """

    value = row.get(field_name)

    if value is None:
        return None

    cleaned = str(value).strip()

    if not cleaned:
        return None

    if max_length is not None and len(cleaned) > max_length:
        raise ValueError(
            f"Timetable assignment import field "
            f"'{field_name}' cannot exceed "
            f"{max_length} characters.",
        )

    return cleaned


def _required_assignment_type(
    row: dict[str, Any],
) -> TimetableAssignmentType:
    """
    Return a valid timetable-assignment type.

    Validated rows are JSON-backed, so enum values normally arrive as strings.
    Direct processor calls may provide the enum itself.
    """

    value = row.get("assignment_type")

    if isinstance(value, TimetableAssignmentType):
        return value

    if isinstance(value, str):
        cleaned = value.strip().lower()

        if cleaned:
            try:
                return TimetableAssignmentType(cleaned)
            except ValueError:
                pass

    valid_values = ", ".join(
        assignment_type.value for assignment_type in TimetableAssignmentType
    )

    raise ValueError(
        "Timetable assignment import field "
        "'assignment_type' must be one of: "
        f"{valid_values}.",
    )


async def _resolve_user(
    db: AsyncSession,
    *,
    user_email: str,
    assignment_type: TimetableAssignmentType,
    school_id: int,
) -> User:
    """
    Resolve and role-check a student or teacher within one school.
    """

    normalised_email = user_email.strip().lower()

    user = await UserRepository(
        db,
    ).get_by_email(
        email=normalised_email,
        school_id=school_id,
    )

    if user is None:
        raise ValueError(
            f"No user with email '{normalised_email}' " "exists in this school.",
        )

    required_role = (
        UserRole.STUDENT
        if assignment_type == TimetableAssignmentType.STUDENT
        else UserRole.TEACHER
    )

    if not user.has_role(required_role):
        raise ValueError(
            f"The user with email '{normalised_email}' is not "
            f"registered as a {required_role.value} in this school.",
        )

    return user


async def _resolve_class_group(
    db: AsyncSession,
    *,
    class_name: str,
    school_id: int,
) -> ClassGroup:
    """
    Resolve a class group within one school.
    """

    class_group = await ClassGroupRepository(
        db,
    ).get_by_name_and_school(
        name=class_name,
        school_id=school_id,
        include_relationships=False,
    )

    if class_group is None:
        raise ValueError(
            f"No class named '{class_name}' exists in this school.",
        )

    return class_group


async def process_timetable_assignment_row(
    db: AsyncSession,
    row: dict[str, Any],
    school_id: int,
) -> RowProcessingResult:
    """
    Create one timetable assignment from validated import data.

    Supported assignment types:

    - ``student``: resolved through ``user_email``;
    - ``teacher``: resolved through ``user_email``;
    - ``class_group``: resolved through ``class_name``.

    Existing matching assignments are skipped to keep repeated imports
    idempotent.

    Transaction ownership belongs to the generic import service or task.
    This processor never commits or rolls back the session.
    """

    if not isinstance(school_id, int) or isinstance(school_id, bool) or school_id < 1:
        raise ValueError(
            "school_id must be a positive integer.",
        )

    timetable_name = _required_string(
        row,
        "timetable_name",
        max_length=150,
    )

    academic_year = _required_string(
        row,
        "academic_year",
        max_length=20,
    )

    assignment_type = _required_assignment_type(
        row,
    )

    user_email = _optional_string(
        row,
        "user_email",
        max_length=320,
    )

    class_name = _optional_string(
        row,
        "class_name",
        max_length=255,
    )

    if assignment_type in {
        TimetableAssignmentType.STUDENT,
        TimetableAssignmentType.TEACHER,
    }:
        if user_email is None:
            raise ValueError(
                "Timetable assignment import field 'user_email' "
                "is required when assignment_type is "
                f"'{assignment_type.value}'.",
            )

        if class_name is not None:
            raise ValueError(
                "Timetable assignment import field 'class_name' "
                "must not be supplied when assignment_type is "
                f"'{assignment_type.value}'.",
            )

    elif assignment_type == TimetableAssignmentType.CLASS_GROUP:
        if class_name is None:
            raise ValueError(
                "Timetable assignment import field 'class_name' "
                "is required when assignment_type is 'class_group'.",
            )

        if user_email is not None:
            raise ValueError(
                "Timetable assignment import field 'user_email' "
                "must not be supplied when assignment_type "
                "is 'class_group'.",
            )

    repository = TimetableRepository(
        db,
    )

    timetable = await repository.get_timetable_by_name_and_year(
        school_id=school_id,
        name=timetable_name,
        academic_year=academic_year,
    )

    if timetable is None:
        raise ValueError(
            f"No timetable named '{timetable_name}' for academic year "
            f"'{academic_year}' exists in this school.",
        )

    user: User | None = None
    class_group: ClassGroup | None = None

    if assignment_type in {
        TimetableAssignmentType.STUDENT,
        TimetableAssignmentType.TEACHER,
    }:
        user = await _resolve_user(
            db,
            user_email=user_email or "",
            assignment_type=assignment_type,
            school_id=school_id,
        )

    else:
        class_group = await _resolve_class_group(
            db,
            class_name=class_name or "",
            school_id=school_id,
        )

    existing_assignment = await repository.find_matching_assignment(
        school_id=school_id,
        timetable_id=timetable.id,
        assignment_type=assignment_type,
        user_id=(user.id if user is not None else None),
        class_group_id=(class_group.id if class_group is not None else None),
    )

    if existing_assignment is not None:
        return RowProcessingResult(
            action=RowProcessingAction.SKIPPED,
            entity_id=existing_assignment.id,
            message=(
                "Timetable assignment already exists for " f"'{assignment_type.value}'."
            ),
        )

    assignment = TimetableAssignment(
        timetable_id=timetable.id,
        school_id=school_id,
        assignment_type=assignment_type,
        user_id=(user.id if user is not None else None),
        class_group_id=(class_group.id if class_group is not None else None),
    )

    db.add(
        assignment,
    )
    await db.flush()
    await db.refresh(
        assignment,
    )

    target = user.email if user is not None else class_group.name

    return RowProcessingResult(
        action=RowProcessingAction.CREATED,
        entity_id=assignment.id,
        message=(
            f"Created {assignment_type.value} timetable assignment " f"for '{target}'."
        ),
    )
