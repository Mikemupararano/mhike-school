from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.imports.registry import (
    ImportOptions,
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

    value = row.get(
        field_name,
    )

    if value is None:
        raise ValueError(
            f"Class import field '{field_name}' is required.",
        )

    cleaned = str(
        value,
    ).strip()

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

    value = row.get(
        field_name,
    )

    if value is None:
        return None

    cleaned = str(
        value,
    ).strip()

    return cleaned or None


def _boolean_import_option(
    import_options: ImportOptions,
    field_name: str,
    *,
    default: bool,
) -> bool:
    """
    Return one boolean import option using strict boolean semantics.

    Persisted import options should contain real JSON booleans. Malformed
    values are rejected rather than relying on Python truthiness.
    """

    value = import_options.get(
        field_name,
    )

    if value is None:
        return default

    if not isinstance(
        value,
        bool,
    ):
        raise ValueError(
            f"Import option '{field_name}' must be a boolean.",
        )

    return value


def _should_update_existing_records(
    import_options: ImportOptions | None,
) -> bool:
    """
    Return whether an existing class may be modified.

    ``None`` preserves historical behaviour for direct processor calls made
    outside the generic import-batch framework.

    When batch options are supplied, updating existing records is opt-in and
    therefore defaults to False when the option is absent.
    """

    if import_options is None:
        return True

    return _boolean_import_option(
        import_options,
        "update_existing_records",
        default=False,
    )


async def _resolve_teacher_id(
    db: AsyncSession,
    *,
    teacher_email: str | None,
    school_id: int,
) -> int | None:
    """
    Resolve an optional teacher email to a same-school teacher user.

    Class imports deliberately require the explicit teacher role, matching
    the existing class-management behaviour. Broader permissions are not used
    because imports should not silently widen teacher-assignment rules.
    """

    if teacher_email is None:
        return None

    normalised_email = teacher_email.strip().lower()

    teacher = await UserRepository(
        db,
    ).get_by_email(
        email=normalised_email,
        school_id=school_id,
    )

    if teacher is None:
        raise ValueError(
            f"No teacher with email '{normalised_email}' " "exists in this school.",
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
    import_options: ImportOptions | None = None,
) -> RowProcessingResult:
    """
    Create, update or skip one class group from validated import data.

    Matching is performed using the class name within the authenticated
    school.

    Behaviour:

    - create a class when no matching school-scoped name exists;
    - update the optional teacher assignment only when
      ``update_existing_records`` is enabled;
    - leave an existing class unchanged and return ``SKIPPED`` when updates
      are disabled;
    - leave enrolments to the separate enrolment import workflow;
    - never commit or roll back the session.

    Direct processor calls that omit ``import_options`` retain the historical
    update-existing behaviour for backwards compatibility with existing
    processor consumers and tests.

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

    repository = ClassGroupRepository(
        db,
    )

    existing_class = await repository.get_by_name_and_school(
        name=name,
        school_id=school_id,
        include_relationships=False,
    )

    # ------------------------------------------------------------------
    # Create a new class.
    # ------------------------------------------------------------------

    if existing_class is None:
        teacher_id = await _resolve_teacher_id(
            db,
            teacher_email=teacher_email,
            school_id=school_id,
        )

        class_group = ClassGroup(
            name=name,
            school_id=school_id,
            teacher_id=teacher_id,
        )

        class_group = await repository.create(
            class_group,
        )

        await db.flush()

        return RowProcessingResult(
            action=RowProcessingAction.CREATED,
            entity_id=class_group.id,
            message=f"Created class '{name}'.",
        )

    # ------------------------------------------------------------------
    # Existing class: leave untouched when updates are disabled.
    # ------------------------------------------------------------------

    if not _should_update_existing_records(
        import_options,
    ):
        return RowProcessingResult(
            action=RowProcessingAction.SKIPPED,
            entity_id=existing_class.id,
            message=(
                f"Skipped existing class '{name}' because updating "
                "existing records is disabled."
            ),
        )

    # ------------------------------------------------------------------
    # Existing class: update when explicitly permitted.
    # ------------------------------------------------------------------

    teacher_id = await _resolve_teacher_id(
        db,
        teacher_email=teacher_email,
        school_id=school_id,
    )

    existing_class.name = name
    existing_class.teacher_id = teacher_id

    existing_class = await repository.save(
        existing_class,
    )

    await db.flush()

    return RowProcessingResult(
        action=RowProcessingAction.UPDATED,
        entity_id=existing_class.id,
        message=f"Updated class '{name}'.",
    )
