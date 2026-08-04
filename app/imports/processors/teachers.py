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
from app.models.user_role import UserRoleAssignment
from app.repositories.user import UserRepository


def _required_string(
    row: dict[str, Any],
    field_name: str,
) -> str:
    """
    Return a required, trimmed string value from an imported row.

    Validation should normally prevent missing values from reaching the
    processor, but these checks protect against malformed data and direct
    processor calls.
    """

    value = row.get(
        field_name,
    )

    if value is None:
        raise ValueError(
            f"Teacher import field '{field_name}' is required.",
        )

    cleaned = str(
        value,
    ).strip()

    if not cleaned:
        raise ValueError(
            f"Teacher import field '{field_name}' cannot be blank.",
        )

    return cleaned


def _normalise_role(
    role: object,
) -> str:
    """Return a stable string value for a role enum or string."""

    value = getattr(
        role,
        "value",
        role,
    )

    return str(value).strip().lower().replace("-", "_").replace(" ", "_")


def _has_teacher_role_assignment(
    user: User,
) -> bool:
    """Return whether the user has a persisted teacher role assignment."""

    assignments = getattr(
        user,
        "user_roles",
        None,
    )

    if not assignments:
        return False

    return any(
        _normalise_role(
            assignment.role,
        )
        == UserRole.TEACHER.value
        for assignment in assignments
    )


def _is_existing_teacher(
    user: User,
) -> bool:
    """
    Return whether an existing account is already recognised as a teacher.

    Both the authoritative multi-role assignments and the legacy primary-role
    field are considered. This allows legacy teacher records to be repaired
    without converting unrelated student or parent accounts.
    """

    if _has_teacher_role_assignment(
        user,
    ):
        return True

    legacy_role = getattr(
        user,
        "role",
        None,
    )

    return (
        legacy_role is not None
        and _normalise_role(
            legacy_role,
        )
        == UserRole.TEACHER.value
    )


async def _ensure_teacher_role_assignment(
    db: AsyncSession,
    *,
    user: User,
) -> bool:
    """
    Ensure the user has a persisted teacher role assignment.

    Returns True when a new assignment was created and False when the
    assignment already existed.
    """

    if _has_teacher_role_assignment(
        user,
    ):
        return False

    db.add(
        UserRoleAssignment(
            user_id=user.id,
            role=UserRole.TEACHER,
        ),
    )

    await db.flush()

    return True


async def process_teacher_row(
    db: AsyncSession,
    row: dict[str, Any],
    school_id: int,
) -> RowProcessingResult:
    """
    Create or update one teacher from validated import data.

    Matching is performed using the email address within the specified school.

    Transaction ownership belongs to the generic import framework. This
    processor therefore flushes changes but does not commit or roll back the
    session.

    Existing accounts are updated only when they are already recognised as
    teachers through either the multi-role assignment table or the legacy
    primary-role field. Unrelated student and parent accounts are not converted
    automatically.

    Legacy teacher accounts missing their user_roles assignment are repaired
    during import while preserving any other existing role assignments.
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

    full_name = (f"{first_name} {last_name}").strip()

    repository = UserRepository(
        db,
    )

    existing_user = await repository.get_by_email(
        email=email,
        school_id=school_id,
    )

    if existing_user is None:
        teacher = User(
            email=email,
            hashed_password=None,
            full_name=full_name,
            role=UserRole.TEACHER,
            status=UserStatus.ACTIVE,
            is_active=True,
            school_id=school_id,
        )

        teacher = await repository.create(
            teacher,
        )

        await _ensure_teacher_role_assignment(
            db,
            user=teacher,
        )

        await db.flush()

        return RowProcessingResult(
            action=RowProcessingAction.CREATED,
            entity_id=teacher.id,
            message=f"Created teacher '{full_name}'.",
        )

    if not _is_existing_teacher(
        existing_user,
    ):
        raise ValueError(
            f"A non-teacher user with email '{email}' already exists "
            "in this school.",
        )

    existing_user.email = email
    existing_user.full_name = full_name
    existing_user.status = UserStatus.ACTIVE
    existing_user.is_active = True

    existing_user = await repository.save(
        existing_user,
    )

    assignment_created = await _ensure_teacher_role_assignment(
        db,
        user=existing_user,
    )

    await db.flush()

    message = (
        f"Updated teacher '{full_name}' and restored the teacher role " "assignment."
        if assignment_created
        else f"Updated teacher '{full_name}'."
    )

    return RowProcessingResult(
        action=RowProcessingAction.UPDATED,
        entity_id=existing_user.id,
        message=message,
    )
