from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.imports.registry import (
    RowProcessingAction,
    RowProcessingResult,
)
from app.models.enrollment import Enrollment
from app.models.user import UserRole
from app.repositories.class_group import ClassGroupRepository
from app.repositories.enrollment import EnrollmentRepository
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
            f"Enrollment import field '{field_name}' is required.",
        )

    cleaned = str(value).strip()

    if not cleaned:
        raise ValueError(
            f"Enrollment import field '{field_name}' cannot be blank.",
        )

    return cleaned


async def process_enrollment_row(
    db: AsyncSession,
    row: dict[str, Any],
    school_id: int,
) -> RowProcessingResult:
    """
    Create one student-to-class enrolment from validated import data.

    Stable import identifiers are used:

    - ``student_email`` resolves the student within the current school;
    - ``class_name`` resolves the class within the current school.

    Existing identical enrolments are treated as successful no-op outcomes
    and return ``RowProcessingAction.SKIPPED``.

    Missing students, missing classes, wrong-role users and cross-school
    references fail the row.

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

    student_email = _required_string(
        row,
        "student_email",
    ).lower()

    class_name = _required_string(
        row,
        "class_name",
    )

    if len(class_name) > 255:
        raise ValueError(
            "Enrollment import field 'class_name' " "cannot exceed 255 characters.",
        )

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

    repository = EnrollmentRepository(
        db,
    )

    existing_enrollment = await repository.get_by_student_and_class_in_school(
        student_id=student.id,
        class_id=class_group.id,
        school_id=school_id,
        include_relationships=False,
    )

    if existing_enrollment is not None:
        return RowProcessingResult(
            action=RowProcessingAction.SKIPPED,
            entity_id=existing_enrollment.id,
            message=(
                f"Student '{student_email}' is already enrolled "
                f"in class '{class_name}'."
            ),
        )

    enrollment = Enrollment(
        user_id=student.id,
        class_id=class_group.id,
    )

    await repository.create(
        enrollment,
    )

    return RowProcessingResult(
        action=RowProcessingAction.CREATED,
        entity_id=enrollment.id,
        message=(f"Enrolled student '{student_email}' " f"in class '{class_name}'."),
    )
