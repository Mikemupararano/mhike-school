from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.imports.registry import (
    ImportOptions,
    RowProcessingAction,
    RowProcessingResult,
)
from app.models.course import Course
from app.models.user import UserRole
from app.repositories.course import CourseRepository
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
            f"Course import field '{field_name}' is required.",
        )

    cleaned = str(
        value,
    ).strip()

    if not cleaned:
        raise ValueError(
            f"Course import field '{field_name}' cannot be blank.",
        )

    return cleaned


def _optional_string(
    row: dict[str, Any],
    field_name: str,
) -> str | None:
    """
    Return an optional, trimmed string value.

    Missing, null and whitespace-only values are normalised to ``None``.
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


def _validate_school_id(
    school_id: int,
) -> None:
    """
    Require a positive integer school identifier.
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
    Return whether an existing course may be modified.

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
    teacher_email: str,
    school_id: int,
) -> int:
    """
    Resolve a teacher email to a same-school teacher user.

    Course ownership requires an explicit teacher role, matching the
    established course and class assignment rules.
    """

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


async def process_course_row(
    db: AsyncSession,
    row: dict[str, Any],
    school_id: int,
    import_options: ImportOptions | None = None,
) -> RowProcessingResult:
    """
    Create, update or skip one course from validated import data.

    Matching is performed using the school-scoped natural key:

    - ``school_id``;
    - ``teacher_id``;
    - normalised ``title``.

    Behaviour for existing courses is controlled by the batch-level
    ``update_existing_records`` option.

    When updates are disabled:

    - existing courses are left unchanged;
    - the row returns ``RowProcessingAction.SKIPPED``.

    When updates are enabled:

    - title, description and teacher ownership may be updated;
    - publication state is preserved.

    Imported courses are always created unpublished. Existing publication
    state is preserved during updates because publishing and unpublishing are
    explicit application workflows and must never happen implicitly during
    import.

    Direct processor calls that omit ``import_options`` retain historical
    update-existing behaviour for backwards compatibility.

    Transaction ownership belongs to the generic import service or background
    task. This processor therefore flushes through repositories but never
    commits or rolls back the session.
    """

    _validate_school_id(
        school_id,
    )

    title = _required_string(
        row,
        "title",
    )

    if len(title) > 255:
        raise ValueError(
            "Course import field 'title' cannot exceed 255 characters.",
        )

    teacher_email = _required_string(
        row,
        "teacher_email",
    )

    description = _optional_string(
        row,
        "description",
    )

    if description is not None and len(description) > 2000:
        raise ValueError(
            "Course import field 'description' cannot exceed 2000 characters.",
        )

    teacher_id = await _resolve_teacher_id(
        db,
        teacher_email=teacher_email,
        school_id=school_id,
    )

    repository = CourseRepository(
        db,
    )

    existing_course = await repository.get_by_title_and_teacher(
        title=title,
        teacher_id=teacher_id,
        school_id=school_id,
        include_relationships=False,
    )

    # ------------------------------------------------------------------
    # Create a new course.
    # ------------------------------------------------------------------

    if existing_course is None:
        course = Course(
            title=title,
            description=description,
            teacher_id=teacher_id,
            school_id=school_id,
            published=False,
        )

        course = await repository.create(
            course,
        )

        await db.flush()

        return RowProcessingResult(
            action=RowProcessingAction.CREATED,
            entity_id=course.id,
            message=f"Created course '{title}'.",
        )

    # ------------------------------------------------------------------
    # Existing course: leave untouched when updates are disabled.
    # ------------------------------------------------------------------

    if not _should_update_existing_records(
        import_options,
    ):
        return RowProcessingResult(
            action=RowProcessingAction.SKIPPED,
            entity_id=existing_course.id,
            message=(
                f"Skipped existing course '{title}' because updating "
                "existing records is disabled."
            ),
        )

    # ------------------------------------------------------------------
    # Existing course: update when explicitly permitted.
    # ------------------------------------------------------------------

    existing_course.title = title
    existing_course.description = description
    existing_course.teacher_id = teacher_id

    # Deliberately preserve ``published``. Imports must never publish or
    # unpublish an existing course as a side effect.
    existing_course = await repository.save(
        existing_course,
    )

    await db.flush()

    return RowProcessingResult(
        action=RowProcessingAction.UPDATED,
        entity_id=existing_course.id,
        message=f"Updated course '{title}'.",
    )
