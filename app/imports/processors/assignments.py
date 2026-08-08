from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.imports.registry import (
    ImportOptions,
    RowProcessingAction,
    RowProcessingResult,
)
from app.models.assignment import Assignment
from app.models.course import Course
from app.models.user import User, UserRole
from app.repositories.assignment import AssignmentRepository
from app.repositories.course import CourseRepository
from app.repositories.user import UserRepository

STAFF_ROLES = {
    UserRole.TEACHER,
    UserRole.SCHOOL_ADMIN,
    UserRole.PLATFORM_ADMIN,
}


def _required_string(
    row: dict[str, Any],
    field_name: str,
    *,
    max_length: int,
) -> str:
    """
    Return a required, trimmed string within the supplied length limit.

    The validator should normally reject malformed rows before processing.
    These defensive checks also protect direct processor calls and staged
    rows created outside the normal validation workflow.
    """

    value = row.get(
        field_name,
    )

    if value is None:
        raise ValueError(
            f"Assignment import field '{field_name}' is required.",
        )

    cleaned = str(
        value,
    ).strip()

    if not cleaned:
        raise ValueError(
            f"Assignment import field '{field_name}' cannot be blank.",
        )

    if len(cleaned) > max_length:
        raise ValueError(
            f"Assignment import field '{field_name}' cannot exceed "
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

    Blank strings are normalised to ``None``.
    """

    value = row.get(
        field_name,
    )

    if value is None:
        return None

    cleaned = str(
        value,
    ).strip()

    if not cleaned:
        return None

    if max_length is not None and len(cleaned) > max_length:
        raise ValueError(
            f"Assignment import field '{field_name}' cannot exceed "
            f"{max_length} characters.",
        )

    return cleaned


def _optional_datetime(
    row: dict[str, Any],
    field_name: str,
) -> datetime | None:
    """
    Return an optional datetime.

    Staged import rows are persisted as JSON, so validated datetimes normally
    arrive as ISO-formatted strings. Direct processor calls may still supply
    ``datetime`` instances.

    A trailing ``Z`` is accepted and interpreted as UTC.
    """

    value = row.get(
        field_name,
    )

    if value is None:
        return None

    if isinstance(
        value,
        datetime,
    ):
        return value

    if isinstance(
        value,
        str,
    ):
        cleaned = value.strip()

        if not cleaned:
            return None

        if cleaned.endswith("Z"):
            cleaned = f"{cleaned[:-1]}+00:00"

        try:
            return datetime.fromisoformat(
                cleaned,
            )
        except ValueError:
            pass

    raise ValueError(
        f"Assignment import field '{field_name}' must be a valid ISO datetime.",
    )


def _optional_positive_integer(
    row: dict[str, Any],
    field_name: str,
    *,
    default: int,
) -> int:
    """
    Return an optional positive integer with a default value.
    """

    value = row.get(
        field_name,
        default,
    )

    if (
        not isinstance(
            value,
            int,
        )
        or isinstance(
            value,
            bool,
        )
        or value < 1
    ):
        raise ValueError(
            f"Assignment import field '{field_name}' must be a positive integer.",
        )

    return value


def _optional_boolean(
    row: dict[str, Any],
    field_name: str,
    *,
    default: bool,
) -> bool:
    """
    Return an optional boolean value.

    The generic validator should already coerce acceptable CSV values.
    The processor therefore requires a real boolean in normalised data.
    """

    value = row.get(
        field_name,
        default,
    )

    if not isinstance(
        value,
        bool,
    ):
        raise ValueError(
            f"Assignment import field '{field_name}' must be a boolean.",
        )

    return value


def _validate_school_id(
    school_id: int,
) -> None:
    """
    Require a positive integer school identifier.

    Boolean values are rejected explicitly because ``bool`` is a subclass
    of ``int`` in Python.
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
    Return whether an existing assignment may be modified.

    ``None`` preserves historical behaviour for direct processor calls made
    outside the generic import-batch framework.

    When batch options are supplied, updating existing records is opt-in and
    defaults to False when the option is absent.
    """

    if import_options is None:
        return True

    return _boolean_import_option(
        import_options,
        "update_existing_records",
        default=False,
    )


def _normalise_email(
    value: str,
    field_name: str,
) -> str:
    """
    Return a trimmed, lowercase email address.

    Structural email validation belongs to the Pydantic validator. This
    helper protects direct processor calls from blank values.
    """

    normalised_email = value.strip().lower()

    if not normalised_email:
        raise ValueError(
            f"Assignment import field '{field_name}' cannot be blank.",
        )

    return normalised_email


def _has_any_role(
    user: User,
    roles: set[UserRole],
) -> bool:
    """
    Return whether the user has at least one of the supplied roles.
    """

    return any(
        user.has_role(
            role,
        )
        for role in roles
    )


async def _resolve_teacher(
    db: AsyncSession,
    *,
    teacher_email: str,
    school_id: int,
) -> User:
    """
    Resolve and validate the teacher who owns the imported course.
    """

    normalised_email = _normalise_email(
        teacher_email,
        "teacher_email",
    )

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

    return teacher


async def _resolve_creator(
    db: AsyncSession,
    *,
    created_by_email: str | None,
    teacher: User,
    school_id: int,
) -> User:
    """
    Resolve the assignment creator.

    When ``created_by_email`` is omitted, the course teacher becomes the
    creator. Explicit creators must be members of staff in the same school.
    """

    if created_by_email is None:
        return teacher

    normalised_email = _normalise_email(
        created_by_email,
        "created_by_email",
    )

    creator = await UserRepository(
        db,
    ).get_by_email(
        email=normalised_email,
        school_id=school_id,
    )

    if creator is None:
        raise ValueError(
            f"No assignment creator with email '{normalised_email}' "
            "exists in this school.",
        )

    if not _has_any_role(
        creator,
        STAFF_ROLES,
    ):
        raise ValueError(
            f"The user with email '{normalised_email}' is not "
            "registered as an authorised staff member in this school.",
        )

    return creator


async def _resolve_course(
    db: AsyncSession,
    *,
    course_title: str,
    teacher: User,
    school_id: int,
) -> Course:
    """
    Resolve the course using title, teacher, and school.

    This follows the existing stable course import identity.
    """

    course = await CourseRepository(
        db,
    ).get_by_title_and_teacher(
        title=course_title,
        teacher_id=teacher.id,
        school_id=school_id,
        include_relationships=False,
    )

    if course is None:
        raise ValueError(
            f"No course titled '{course_title}' assigned to "
            f"teacher '{teacher.email}' exists in this school.",
        )

    return course


async def process_assignment_row(
    db: AsyncSession,
    row: dict[str, Any],
    school_id: int,
    import_options: ImportOptions | None = None,
) -> RowProcessingResult:
    """
    Create, update or skip one assignment from validated import data.

    Matching is performed using the school-scoped natural key:

    - ``school_id``;
    - ``course_id``;
    - normalised ``title``.

    The course is resolved through its stable import identity of title,
    owning teacher and school.

    Existing assignment behaviour is controlled by the batch-level
    ``update_existing_records`` option.

    When updates are disabled, an existing assignment is left unchanged and
    the row returns ``SKIPPED``.

    When updates are enabled, imported assignment fields may be applied to
    the existing record.

    Direct processor calls that omit ``import_options`` retain historical
    update-existing behaviour for backwards compatibility.

    When ``created_by_email`` is omitted, the owning course teacher becomes
    the assignment creator.

    Transaction ownership belongs to the generic import service or background
    task. This processor never commits or rolls back the session.
    """

    _validate_school_id(
        school_id,
    )

    title = _required_string(
        row,
        "title",
        max_length=255,
    )

    course_title = _required_string(
        row,
        "course_title",
        max_length=255,
    )

    teacher_email = _required_string(
        row,
        "teacher_email",
        max_length=320,
    )

    created_by_email = _optional_string(
        row,
        "created_by_email",
        max_length=320,
    )

    description = _optional_string(
        row,
        "description",
    )

    due_date = _optional_datetime(
        row,
        "due_date",
    )

    max_score = _optional_positive_integer(
        row,
        "max_score",
        default=100,
    )

    is_published = _optional_boolean(
        row,
        "is_published",
        default=False,
    )

    teacher = await _resolve_teacher(
        db,
        teacher_email=teacher_email,
        school_id=school_id,
    )

    course = await _resolve_course(
        db,
        course_title=course_title,
        teacher=teacher,
        school_id=school_id,
    )

    repository = AssignmentRepository(
        db,
    )

    existing_assignment = await repository.get_by_title_and_course(
        title=title,
        course_id=course.id,
        school_id=school_id,
        include_relationships=False,
    )

    # ------------------------------------------------------------------
    # Existing assignment: leave untouched when updates are disabled.
    # ------------------------------------------------------------------

    if existing_assignment is not None and not _should_update_existing_records(
        import_options,
    ):
        return RowProcessingResult(
            action=RowProcessingAction.SKIPPED,
            entity_id=existing_assignment.id,
            message=(
                f"Skipped existing assignment '{title}' because updating "
                "existing records is disabled."
            ),
        )

    # Resolve the creator only when an assignment will actually be created
    # or updated.
    creator = await _resolve_creator(
        db,
        created_by_email=created_by_email,
        teacher=teacher,
        school_id=school_id,
    )

    # ------------------------------------------------------------------
    # Create a new assignment.
    # ------------------------------------------------------------------

    if existing_assignment is None:
        assignment = Assignment(
            title=title,
            description=description,
            due_date=due_date,
            max_score=max_score,
            is_published=is_published,
            course_id=course.id,
            school_id=school_id,
            created_by=creator.id,
        )

        assignment = await repository.create(
            assignment,
        )

        await db.flush()

        return RowProcessingResult(
            action=RowProcessingAction.CREATED,
            entity_id=assignment.id,
            message=f"Created assignment '{title}'.",
        )

    # ------------------------------------------------------------------
    # Existing assignment: update when explicitly permitted.
    # ------------------------------------------------------------------

    existing_assignment.title = title
    existing_assignment.description = description
    existing_assignment.due_date = due_date
    existing_assignment.max_score = max_score
    existing_assignment.is_published = is_published
    existing_assignment.course_id = course.id
    existing_assignment.created_by = creator.id

    existing_assignment = await repository.save(
        existing_assignment,
    )

    await db.flush()

    return RowProcessingResult(
        action=RowProcessingAction.UPDATED,
        entity_id=existing_assignment.id,
        message=f"Updated assignment '{title}'.",
    )
