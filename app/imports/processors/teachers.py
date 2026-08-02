from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.imports.registry import (
    RowProcessingAction,
    RowProcessingResult,
)
from app.models.user import User, UserRole, UserStatus
from app.repositories.user import UserRepository


def _required_string(
    row: dict[str, Any],
    field_name: str,
) -> str:
    """
    Return a required, trimmed string value from an imported row.

    Validation should normally prevent missing values reaching the
    processor, but these checks protect against malformed data and
    direct processor calls.
    """

    value = row.get(field_name)

    if value is None:
        raise ValueError(f"Teacher import field '{field_name}' is required.")

    cleaned = str(value).strip()

    if not cleaned:
        raise ValueError(f"Teacher import field '{field_name}' cannot be blank.")

    return cleaned


async def process_teacher_row(
    db: AsyncSession,
    row: dict[str, Any],
    school_id: int,
) -> RowProcessingResult:
    """
    Create or update one teacher.

    Matching is performed by email address within the current school.

    Transaction ownership belongs to the generic import framework.
    This processor therefore never commits or rolls back.

    Existing non-teacher accounts are deliberately rejected rather
    than converted automatically to avoid unexpected privilege
    escalation or accidental role replacement.
    """

    if school_id < 1:
        raise ValueError("school_id must be a positive integer.")

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

    full_name = f"{first_name} {last_name}".strip()

    repository = UserRepository(db)

    existing_user = await repository.get_by_email(
        email=email,
        school_id=school_id,
    )

    #
    # Create
    #
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

        await repository.create(teacher)
        await db.flush()

        return RowProcessingResult(
            action=RowProcessingAction.CREATED,
            entity_id=teacher.id,
            message=f"Created teacher '{full_name}'.",
        )

    #
    # Existing account must already be recognised as a teacher.
    #
    if not existing_user.is_teacher:
        raise ValueError(
            f"A non-teacher user with email '{email}' "
            f"already exists in this school."
        )

    #
    # Update existing teacher.
    #
    existing_user.email = email
    existing_user.full_name = full_name
    existing_user.status = UserStatus.ACTIVE
    existing_user.is_active = True

    await repository.save(
        existing_user,
    )

    await db.flush()

    return RowProcessingResult(
        action=RowProcessingAction.UPDATED,
        entity_id=existing_user.id,
        message=f"Updated teacher '{full_name}'.",
    )
