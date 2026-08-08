from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.imports.registry import (
    ImportOptions,
    RowProcessingAction,
    RowProcessingResult,
)
from app.models.class_group import ClassGroup
from app.models.course import Course
from app.models.timetable_entry import TimetableDay
from app.models.user import User, UserRole
from app.repositories.class_group import ClassGroupRepository
from app.repositories.course import CourseRepository
from app.repositories.timetable import TimetableRepository
from app.repositories.user import UserRepository
from app.schemas.timetable import TimetableEntryCreate


def _required_string(
    row: dict[str, Any],
    field_name: str,
) -> str:
    """
    Return a required, trimmed string value.

    Validation should normally reject malformed rows before processing.
    These checks protect direct processor calls and defensive code paths.
    """

    value = row.get(
        field_name,
    )

    if value is None:
        raise ValueError(
            f"Timetable entry import field '{field_name}' is required.",
        )

    cleaned = str(
        value,
    ).strip()

    if not cleaned:
        raise ValueError(
            f"Timetable entry import field '{field_name}' cannot be blank.",
        )

    return cleaned


def _optional_string(
    row: dict[str, Any],
    field_name: str,
    *,
    max_length: int | None = None,
) -> str | None:
    """
    Return a trimmed optional string value.
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
            f"Timetable entry import field '{field_name}' "
            f"cannot exceed {max_length} characters.",
        )

    return cleaned


def _required_positive_integer(
    row: dict[str, Any],
    field_name: str,
) -> int:
    """
    Return a required positive integer.
    """

    value = row.get(
        field_name,
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
            f"Timetable entry import field '{field_name}' "
            "must be a positive integer.",
        )

    return value


def _required_day(
    row: dict[str, Any],
    field_name: str,
) -> TimetableDay:
    """
    Return a valid timetable day.

    Validated rows are stored as JSON, so enum values normally arrive as
    strings such as ``monday``. Direct processor calls may supply the enum.
    """

    value = row.get(
        field_name,
    )

    if isinstance(
        value,
        TimetableDay,
    ):
        return value

    if isinstance(
        value,
        str,
    ):
        cleaned = value.strip().lower()

        if cleaned:
            try:
                return TimetableDay(
                    cleaned,
                )
            except ValueError:
                pass

    raise ValueError(
        f"Timetable entry import field '{field_name}' "
        "must be a valid timetable day.",
    )


def _boolean_import_option(
    import_options: ImportOptions,
    field_name: str,
    *,
    default: bool,
) -> bool:
    """
    Return one boolean import option using strict boolean semantics.
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
    Return whether an existing timetable entry may be modified.

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


async def _resolve_teacher(
    db: AsyncSession,
    *,
    teacher_email: str | None,
    school_id: int,
) -> User | None:
    """
    Resolve an optional teacher within the current school.
    """

    if teacher_email is None:
        return None

    teacher = await UserRepository(
        db,
    ).get_by_email(
        email=teacher_email,
        school_id=school_id,
    )

    if teacher is None:
        raise ValueError(
            f"No teacher with email '{teacher_email}' exists in this school.",
        )

    if not teacher.has_role(
        UserRole.TEACHER,
    ):
        raise ValueError(
            f"The user with email '{teacher_email}' is not "
            "registered as a teacher in this school.",
        )

    return teacher


async def _resolve_class_group(
    db: AsyncSession,
    *,
    class_name: str | None,
    school_id: int,
) -> ClassGroup | None:
    """
    Resolve an optional class group within the current school.
    """

    if class_name is None:
        return None

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

    return class_group


async def _resolve_course(
    db: AsyncSession,
    *,
    course_title: str | None,
    teacher: User | None,
    school_id: int,
) -> Course | None:
    """
    Resolve an optional course within the current school.

    When a teacher is supplied, the more specific title/teacher/school
    identity is used. Otherwise, the course is resolved by title and school.
    """

    if course_title is None:
        return None

    repository = CourseRepository(
        db,
    )

    if teacher is not None:
        course = await repository.get_by_title_and_teacher(
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

    course = await repository.get_by_title_and_school(
        title=course_title,
        school_id=school_id,
        include_relationships=False,
    )

    if course is None:
        raise ValueError(
            f"No course titled '{course_title}' exists in this school.",
        )

    return course


async def process_timetable_entry_row(
    db: AsyncSession,
    row: dict[str, Any],
    school_id: int,
    import_options: ImportOptions | None = None,
) -> RowProcessingResult:
    """
    Create, update or skip one timetable entry from validated import data.

    Human-readable import fields are resolved within the authenticated school:

    - timetable_name + academic_year;
    - period_number;
    - class_name;
    - course_title;
    - teacher_email.

    Existing timetable entries are matched by:

    - school;
    - timetable;
    - day;
    - period;
    - class;
    - course;
    - teacher.

    Room, title, and notes are treated as mutable entry details.

    Existing entry behaviour is controlled by the batch-level
    ``update_existing_records`` option.

    When updates are disabled, an existing entry is left unchanged and the
    row returns ``SKIPPED``.

    When updates are enabled, room, title and notes may be updated.

    Direct processor calls that omit ``import_options`` retain historical
    update-existing behaviour for backwards compatibility.

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

    timetable_name = _required_string(
        row,
        "timetable_name",
    )

    academic_year = _required_string(
        row,
        "academic_year",
    )

    day_of_week = _required_day(
        row,
        "day_of_week",
    )

    period_number = _required_positive_integer(
        row,
        "period_number",
    )

    class_name = _optional_string(
        row,
        "class_name",
        max_length=255,
    )

    course_title = _optional_string(
        row,
        "course_title",
        max_length=255,
    )

    teacher_email = _optional_string(
        row,
        "teacher_email",
    )

    if teacher_email is not None:
        teacher_email = teacher_email.lower()

    room = _optional_string(
        row,
        "room",
        max_length=100,
    )

    title = _optional_string(
        row,
        "title",
        max_length=200,
    )

    notes = _optional_string(
        row,
        "notes",
    )

    if len(timetable_name) > 150:
        raise ValueError(
            "Timetable entry import field 'timetable_name' "
            "cannot exceed 150 characters.",
        )

    if len(academic_year) > 20:
        raise ValueError(
            "Timetable entry import field 'academic_year' "
            "cannot exceed 20 characters.",
        )

    if not any(
        (
            class_name,
            course_title,
            teacher_email,
        )
    ):
        raise ValueError(
            "At least one of class_name, course_title, "
            "or teacher_email must be provided.",
        )

    timetable_repository = TimetableRepository(
        db,
    )

    timetable = await timetable_repository.get_timetable_by_name_and_year(
        school_id=school_id,
        name=timetable_name,
        academic_year=academic_year,
    )

    if timetable is None:
        raise ValueError(
            f"No timetable named '{timetable_name}' for academic year "
            f"'{academic_year}' exists in this school.",
        )

    period = await timetable_repository.get_period_by_number(
        school_id=school_id,
        period_number=period_number,
    )

    if period is None:
        raise ValueError(
            f"No timetable period numbered {period_number} exists " "in this school.",
        )

    teacher = await _resolve_teacher(
        db,
        teacher_email=teacher_email,
        school_id=school_id,
    )

    class_group = await _resolve_class_group(
        db,
        class_name=class_name,
        school_id=school_id,
    )

    course = await _resolve_course(
        db,
        course_title=course_title,
        teacher=teacher,
        school_id=school_id,
    )

    if teacher is not None and course is not None and course.teacher_id != teacher.id:
        raise ValueError(
            f"Course '{course.title}' is not assigned to "
            f"teacher '{teacher.email}'.",
        )

    existing_entry = await timetable_repository.find_matching_entry(
        school_id=school_id,
        timetable_id=timetable.id,
        timetable_period_id=period.id,
        day_of_week=day_of_week,
        class_group_id=(class_group.id if class_group is not None else None),
        course_id=(course.id if course is not None else None),
        teacher_id=(teacher.id if teacher is not None else None),
    )

    # ------------------------------------------------------------------
    # Existing entry: leave untouched when updates are disabled.
    # ------------------------------------------------------------------

    if existing_entry is not None and not _should_update_existing_records(
        import_options,
    ):
        return RowProcessingResult(
            action=RowProcessingAction.SKIPPED,
            entity_id=existing_entry.id,
            message=(
                f"Skipped existing timetable entry for "
                f"{day_of_week.value}, period {period_number} because "
                "updating existing records is disabled."
            ),
        )

    # ------------------------------------------------------------------
    # Create a new timetable entry.
    # ------------------------------------------------------------------

    if existing_entry is None:
        entry = await timetable_repository.create_entry(
            TimetableEntryCreate(
                timetable_id=timetable.id,
                school_id=school_id,
                class_group_id=(class_group.id if class_group is not None else None),
                course_id=(course.id if course is not None else None),
                teacher_id=(teacher.id if teacher is not None else None),
                timetable_period_id=period.id,
                day_of_week=day_of_week,
                room=room,
                title=title,
                notes=notes,
            ),
        )

        await db.flush()

        return RowProcessingResult(
            action=RowProcessingAction.CREATED,
            entity_id=entry.id,
            message=(
                f"Created timetable entry for "
                f"{day_of_week.value}, period {period_number}."
            ),
        )

    # ------------------------------------------------------------------
    # Existing entry: update when explicitly permitted.
    # ------------------------------------------------------------------

    existing_entry.room = room
    existing_entry.title = title
    existing_entry.notes = notes

    existing_entry = await timetable_repository.save_entry(
        existing_entry,
    )

    await db.flush()

    return RowProcessingResult(
        action=RowProcessingAction.UPDATED,
        entity_id=existing_entry.id,
        message=(
            f"Updated timetable entry for "
            f"{day_of_week.value}, period {period_number}."
        ),
    )
