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
    Return a required, stripped string value from an imported row.

    Validation should normally catch missing values before processing begins.
    This defensive check protects the processor when it is called directly or
    receives malformed data.
    """

    value = row.get(
        field_name,
    )

    if value is None:
        raise ValueError(
            f"Student import field '{field_name}' is required.",
        )

    cleaned = str(
        value,
    ).strip()

    if not cleaned:
        raise ValueError(
            f"Student import field '{field_name}' cannot be blank.",
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


def _has_student_role_assignment(
    user: User,
) -> bool:
    """Return whether the user has a persisted student role assignment."""

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
        == UserRole.STUDENT.value
        for assignment in assignments
    )


def _is_existing_student(
    user: User,
) -> bool:
    """
    Return whether an existing account is already recognised as a student.

    Both the authoritative multi-role assignments and the legacy primary-role
    field are considered. This permits old student-only records to be repaired
    without converting unrelated staff or parent accounts.
    """

    if _has_student_role_assignment(
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
        == UserRole.STUDENT.value
    )


async def _ensure_student_role_assignment(
    db: AsyncSession,
    *,
    user: User,
) -> bool:
    """
    Ensure the user has a persisted student role assignment.

    Returns True when a new assignment was created and False when the
    assignment already existed.
    """

    if _has_student_role_assignment(
        user,
    ):
        return False

    db.add(
        UserRoleAssignment(
            user_id=user.id,
            role=UserRole.STUDENT,
        ),
    )

    await db.flush()

    return True


async def process_student_row(
    db: AsyncSession,
    row: dict[str, Any],
    school_id: int,
) -> RowProcessingResult:
    """
    Create or update one student from validated import data.

    Matching is performed using the email address within the specified school.

    Transaction ownership belongs to the generic import-batch task. This
    processor therefore flushes changes but does not commit or roll back the
    session.

    Existing accounts are updated only when they are already recognised as
    students through either the multi-role assignment table or the legacy
    primary-role field. Unrelated staff and parent accounts are not converted
    automatically.

    Legacy student accounts missing their user_roles assignment are repaired
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
        student = User(
            email=email,
            hashed_password=None,
            full_name=full_name,
            role=UserRole.STUDENT,
            status=UserStatus.ACTIVE,
            is_active=True,
            school_id=school_id,
        )

        student = await repository.create(
            student,
        )

        await _ensure_student_role_assignment(
            db,
            user=student,
        )

        await db.flush()

        return RowProcessingResult(
            action=RowProcessingAction.CREATED,
            entity_id=student.id,
            message=f"Created student '{full_name}'.",
        )

    if not _is_existing_student(
        existing_user,
    ):
        raise ValueError(
            f"A non-student user with email '{email}' already exists "
            "in this school.",
        )

    existing_user.email = email
    existing_user.full_name = full_name
    existing_user.status = UserStatus.ACTIVE
    existing_user.is_active = True

    existing_user = await repository.save(
        existing_user,
    )

    assignment_created = await _ensure_student_role_assignment(
        db,
        user=existing_user,
    )

    await db.flush()

    message = (
        f"Updated student '{full_name}' and restored the student role " "assignment."
        if assignment_created
        else f"Updated student '{full_name}'."
    )

    return RowProcessingResult(
        action=RowProcessingAction.UPDATED,
        entity_id=existing_user.id,
        message=message,
    )
