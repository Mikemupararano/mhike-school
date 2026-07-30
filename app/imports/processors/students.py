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
    Return a required, stripped string value from an imported row.

    Validation should normally catch missing values before processing begins.
    This defensive check protects the processor when it is called directly or
    receives malformed data.
    """

    value = row.get(field_name)

    if value is None:
        raise ValueError(f"Student import field '{field_name}' is required.")

    cleaned = str(value).strip()

    if not cleaned:
        raise ValueError(f"Student import field '{field_name}' cannot be blank.")

    return cleaned


async def process_student_row(
    db: AsyncSession,
    row: dict[str, Any],
    school_id: int,
) -> RowProcessingResult:
    """
    Create or update one student from validated import data.

    Matching is performed using the email address within the specified school.

    Transaction ownership belongs to the generic import-batch service or task.
    This processor therefore does not commit or roll back the session.

    Existing non-student accounts are not converted automatically because that
    could overwrite a staff or parent account. Multi-role assignment must be
    handled through an explicit role-management workflow.
    """

    if school_id < 1:
        raise ValueError("school_id must be a positive integer.")

    email = _required_string(row, "email").lower()
    first_name = _required_string(row, "first_name")
    last_name = _required_string(row, "last_name")
    full_name = f"{first_name} {last_name}".strip()

    repository = UserRepository(db)

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

        await repository.create(student)
        await db.flush()

        return RowProcessingResult(
            action=RowProcessingAction.CREATED,
            entity_id=student.id,
            message=f"Created student '{full_name}'.",
        )

    if not existing_user.is_student:
        raise ValueError(
            f"A non-student user with email '{email}' already exists " "in this school."
        )

    existing_user.email = email
    existing_user.full_name = full_name
    existing_user.status = UserStatus.ACTIVE
    existing_user.is_active = True

    await repository.save(existing_user)
    await db.flush()

    return RowProcessingResult(
        action=RowProcessingAction.UPDATED,
        entity_id=existing_user.id,
        message=f"Updated student '{full_name}'.",
    )
