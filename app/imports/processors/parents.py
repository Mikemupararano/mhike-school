from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.imports.registry import (
    RowProcessingAction,
    RowProcessingResult,
)
from app.models.user import (
    User,
    UserRole,
    UserStatus,
)
from app.repositories.parent_student import ParentStudentRepository
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
            f"Parent import field '{field_name}' is required.",
        )

    cleaned = str(value).strip()

    if not cleaned:
        raise ValueError(
            f"Parent import field '{field_name}' cannot be blank.",
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


async def _resolve_student(
    db: AsyncSession,
    *,
    student_email: str,
    school_id: int,
) -> User:
    """
    Resolve a student by email within the current school.
    """

    student = await UserRepository(
        db,
    ).get_by_email(
        email=student_email,
        school_id=school_id,
    )

    if student is None:
        raise ValueError(
            f"No student with email '{student_email}' exists " "in this school.",
        )

    if not student.has_role(
        UserRole.STUDENT,
    ):
        raise ValueError(
            f"The user with email '{student_email}' is not "
            "registered as a student in this school.",
        )

    return student


async def _create_or_update_parent(
    db: AsyncSession,
    *,
    email: str,
    first_name: str,
    last_name: str,
    school_id: int,
) -> tuple[User, RowProcessingAction]:
    """
    Create a new parent or update an existing parent account.

    Existing non-parent users are rejected rather than automatically granted
    the parent role. This avoids silently changing account permissions during
    a bulk import.
    """

    repository = UserRepository(
        db,
    )

    existing_user = await repository.get_by_email(
        email=email,
        school_id=school_id,
    )

    full_name = f"{first_name} {last_name}".strip()

    if existing_user is None:
        parent = User(
            email=email,
            hashed_password=None,
            full_name=full_name,
            role=UserRole.PARENT,
            status=UserStatus.ACTIVE,
            is_active=True,
            school_id=school_id,
        )

        await repository.create(
            parent,
        )
        await db.flush()

        return (
            parent,
            RowProcessingAction.CREATED,
        )

    if not existing_user.has_role(
        UserRole.PARENT,
    ):
        raise ValueError(
            f"A non-parent user with email '{email}' already exists " "in this school."
        )

    existing_user.email = email
    existing_user.full_name = full_name
    existing_user.status = UserStatus.ACTIVE
    existing_user.is_active = True

    await repository.save(
        existing_user,
    )
    await db.flush()

    return (
        existing_user,
        RowProcessingAction.UPDATED,
    )


async def process_parent_row(
    db: AsyncSession,
    row: dict[str, Any],
    school_id: int,
) -> RowProcessingResult:
    """
    Create or update one parent and link the parent to one student.

    Stable import identifiers are used:

    - ``email`` identifies the parent within the current school;
    - ``student_email`` identifies the linked student.

    Behaviour:

    - create a new parent when no matching account exists;
    - update an existing parent account;
    - reject an existing account that does not already have the parent role;
    - create the parent-student relationship;
    - return ``SKIPPED`` when that relationship already exists.

    The optional ``phone`` field is currently validated but is not persisted,
    because the existing User model does not expose a confirmed phone field.

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

    email = _required_string(
        row,
        "email",
    ).lower()

    first_name = _required_string(
        row,
        "first_name",
    )

    last_name = _required_string(
        row,
        "last_name",
    )

    student_email = _required_string(
        row,
        "student_email",
    ).lower()

    phone = _optional_string(
        row,
        "phone",
    )

    if phone is not None and len(phone) > 50:
        raise ValueError(
            "Parent import field 'phone' cannot exceed 50 characters.",
        )

    student = await _resolve_student(
        db,
        student_email=student_email,
        school_id=school_id,
    )

    parent, parent_action = await _create_or_update_parent(
        db,
        email=email,
        first_name=first_name,
        last_name=last_name,
        school_id=school_id,
    )

    link_repository = ParentStudentRepository(
        db,
    )

    existing_link = await link_repository.get_link_in_school(
        parent_id=parent.id,
        student_id=student.id,
        school_id=school_id,
        include_relationships=False,
    )

    if existing_link is not None:
        return RowProcessingResult(
            action=RowProcessingAction.SKIPPED,
            entity_id=existing_link.id,
            message=(
                f"Parent '{email}' is already linked " f"to student '{student_email}'."
            ),
        )

    link = await link_repository.create_link(
        parent_id=parent.id,
        student_id=student.id,
    )

    if parent_action == RowProcessingAction.CREATED:
        message = (
            f"Created parent '{parent.full_name}' and linked "
            f"the parent to student '{student_email}'."
        )
    else:
        message = (
            f"Updated parent '{parent.full_name}' and linked "
            f"the parent to student '{student_email}'."
        )

    return RowProcessingResult(
        action=parent_action,
        entity_id=link.id,
        message=message,
    )
