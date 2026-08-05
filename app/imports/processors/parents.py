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

    value = row.get(
        field_name,
    )

    if value is None:
        raise ValueError(
            f"Parent import field '{field_name}' is required.",
        )

    cleaned = str(
        value,
    ).strip()

    if not cleaned:
        raise ValueError(
            f"Parent import field '{field_name}' cannot be blank.",
        )

    return cleaned


def _optional_string(
    row: dict[str, Any],
    field_name: str,
) -> str | None:
    """Return an optional, trimmed string value."""

    value = row.get(
        field_name,
    )

    if value is None:
        return None

    cleaned = str(
        value,
    ).strip()

    return cleaned or None


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


def _has_role_assignment(
    user: User,
    role: UserRole,
) -> bool:
    """Return whether the user has the specified persisted role assignment."""

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
        == role.value
        for assignment in assignments
    )


def _is_existing_role(
    user: User,
    role: UserRole,
) -> bool:
    """
    Return whether an account is already recognised as the supplied role.

    Both the authoritative multi-role assignments and the legacy primary-role
    field are considered so legacy accounts can be repaired safely.
    """

    if _has_role_assignment(
        user,
        role,
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
        == role.value
    )


async def _ensure_role_assignment(
    db: AsyncSession,
    *,
    user: User,
    role: UserRole,
) -> bool:
    """
    Ensure the user has the supplied persisted role assignment.

    Returns True when a new assignment was created and False when it already
    existed.
    """

    if _has_role_assignment(
        user,
        role,
    ):
        return False

    db.add(
        UserRoleAssignment(
            user_id=user.id,
            role=role,
        ),
    )

    await db.flush()

    return True


async def _resolve_student(
    db: AsyncSession,
    *,
    student_email: str,
    school_id: int,
) -> User:
    """Resolve a student by email within the current school."""

    student = await UserRepository(
        db,
    ).get_by_email(
        email=student_email,
        school_id=school_id,
    )

    if student is None:
        raise ValueError(
            f"No student with email '{student_email}' exists in this school.",
        )

    if not _is_existing_role(
        student,
        UserRole.STUDENT,
    ):
        raise ValueError(
            f"The user with email '{student_email}' is not "
            "registered as a student in this school.",
        )

    await _ensure_role_assignment(
        db,
        user=student,
        role=UserRole.STUDENT,
    )

    return student


async def _create_or_update_parent(
    db: AsyncSession,
    *,
    email: str,
    first_name: str,
    last_name: str,
    school_id: int,
) -> tuple[User, RowProcessingAction, bool]:
    """
    Create or update one parent account.

    Existing non-parent users are rejected rather than being granted the parent
    role automatically. Legacy parent accounts missing their persisted role
    assignment are repaired.
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

        parent = await repository.create(
            parent,
        )

        await _ensure_role_assignment(
            db,
            user=parent,
            role=UserRole.PARENT,
        )

        return (
            parent,
            RowProcessingAction.CREATED,
            True,
        )

    if not _is_existing_role(
        existing_user,
        UserRole.PARENT,
    ):
        raise ValueError(
            f"A non-parent user with email '{email}' " "already exists in this school.",
        )

    existing_user.email = email
    existing_user.full_name = full_name
    existing_user.status = UserStatus.ACTIVE
    existing_user.is_active = True

    existing_user = await repository.save(
        existing_user,
    )

    assignment_created = await _ensure_role_assignment(
        db,
        user=existing_user,
        role=UserRole.PARENT,
    )

    return (
        existing_user,
        RowProcessingAction.UPDATED,
        assignment_created,
    )


async def process_parent_row(
    db: AsyncSession,
    row: dict[str, Any],
    school_id: int,
) -> RowProcessingResult:
    """
    Create or update one parent and link the parent to one student.

    Stable import identifiers are used:

    - email identifies the parent within the current school;
    - student_email identifies the linked student.

    Behaviour:

    - create a new parent when no matching account exists;
    - update an existing parent account;
    - repair legacy parent and student role assignments when missing;
    - reject an existing account that is not already recognised as a parent;
    - create the parent-student relationship;
    - return SKIPPED when that relationship already exists.

    The optional phone field is validated but is not persisted because the
    current User model does not expose a confirmed phone field.

    Transaction ownership belongs to the generic import service or task. This
    processor therefore flushes changes but never commits or rolls back.
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

    parent, parent_action, assignment_created = await _create_or_update_parent(
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
        message = (
            f"Parent '{email}' is already linked " f"to student '{student_email}'."
        )

        if assignment_created:
            message += " The parent role assignment was restored."

        return RowProcessingResult(
            action=RowProcessingAction.SKIPPED,
            entity_id=existing_link.id,
            message=message,
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
    elif assignment_created:
        message = (
            f"Updated parent '{parent.full_name}', restored the parent role "
            f"assignment and linked the parent to student '{student_email}'."
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
