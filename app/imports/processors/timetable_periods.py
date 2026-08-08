from __future__ import annotations

from datetime import time
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.imports.registry import (
    ImportOptions,
    RowProcessingAction,
    RowProcessingResult,
)
from app.repositories.timetable import TimetableRepository
from app.schemas.timetable import TimetablePeriodCreate


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
            f"Timetable period import field '{field_name}' is required.",
        )

    cleaned = str(
        value,
    ).strip()

    if not cleaned:
        raise ValueError(
            f"Timetable period import field '{field_name}' cannot be blank.",
        )

    return cleaned


def _required_positive_integer(
    row: dict[str, Any],
    field_name: str,
) -> int:
    """
    Return a required positive integer value.

    Boolean values are explicitly rejected because ``bool`` is a subclass
    of ``int`` in Python.
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
            f"Timetable period import field '{field_name}' "
            "must be a positive integer.",
        )

    return value


def _required_time(
    row: dict[str, Any],
    field_name: str,
) -> time:
    """
    Return a required ``datetime.time`` value.

    Validated staged rows are persisted as JSON, so time values normally
    arrive as ISO-formatted strings such as ``09:00:00``. Direct processor
    calls may provide ``datetime.time`` instances.
    """

    value = row.get(
        field_name,
    )

    if isinstance(
        value,
        time,
    ):
        return value

    if isinstance(
        value,
        str,
    ):
        cleaned = value.strip()

        if cleaned:
            try:
                return time.fromisoformat(
                    cleaned,
                )
            except ValueError:
                pass

    raise ValueError(
        f"Timetable period import field '{field_name}' must be a valid time.",
    )


def _optional_boolean(
    row: dict[str, Any],
    field_name: str,
    *,
    default: bool,
) -> bool:
    """
    Return an optional boolean value.

    Schema validation should already normalise accepted source values.
    Defensive processor calls must therefore provide an actual ``bool``.
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
            f"Timetable period import field '{field_name}' must be a boolean.",
        )

    return value


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
    Return whether an existing timetable period may be modified.

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


async def process_timetable_period_row(
    db: AsyncSession,
    row: dict[str, Any],
    school_id: int,
    import_options: ImportOptions | None = None,
) -> RowProcessingResult:
    """
    Create, update or skip one timetable period from validated import data.

    Existing periods are matched using ``period_number`` within the
    authenticated school.

    ``short_name`` must also be unique within the school. A matching short
    name is allowed only when it belongs to the same period being updated.

    Existing period behaviour is controlled by the batch-level
    ``update_existing_records`` option.

    When updates are disabled, an existing period is left unchanged and the
    row returns ``SKIPPED``.

    When updates are enabled, imported period fields may be applied to the
    existing record.

    Direct processor calls that omit ``import_options`` retain historical
    update-existing behaviour for backwards compatibility.

    New records are passed to the repository as ``TimetablePeriodCreate``
    schemas, matching the repository contract. Existing records are updated
    as ORM entities through ``save_period``.

    Transaction ownership belongs to the generic import service or background
    task. This processor never commits or rolls back the session.
    """

    _validate_school_id(
        school_id,
    )

    name = _required_string(
        row,
        "name",
    )

    short_name = _required_string(
        row,
        "short_name",
    )

    period_number = _required_positive_integer(
        row,
        "period_number",
    )

    if len(name) > 100:
        raise ValueError(
            "Timetable period import field 'name' cannot exceed 100 characters.",
        )

    if len(short_name) > 20:
        raise ValueError(
            "Timetable period import field 'short_name' "
            "cannot exceed 20 characters.",
        )

    start_time_value = _required_time(
        row,
        "start_time",
    )

    end_time_value = _required_time(
        row,
        "end_time",
    )

    if end_time_value <= start_time_value:
        raise ValueError(
            "Timetable period import field 'end_time' "
            "must be later than start_time.",
        )

    is_registration = _optional_boolean(
        row,
        "is_registration",
        default=False,
    )

    is_break = _optional_boolean(
        row,
        "is_break",
        default=False,
    )

    is_lunch = _optional_boolean(
        row,
        "is_lunch",
        default=False,
    )

    is_active = _optional_boolean(
        row,
        "is_active",
        default=True,
    )

    repository = TimetableRepository(
        db,
    )

    existing_period = await repository.get_period_by_number(
        school_id=school_id,
        period_number=period_number,
    )

    # ------------------------------------------------------------------
    # Existing period: leave untouched when updates are disabled.
    # ------------------------------------------------------------------

    if existing_period is not None and not _should_update_existing_records(
        import_options,
    ):
        return RowProcessingResult(
            action=RowProcessingAction.SKIPPED,
            entity_id=existing_period.id,
            message=(
                f"Skipped existing timetable period '{existing_period.name}' "
                f"(period {period_number}) because updating existing records "
                "is disabled."
            ),
        )

    # ------------------------------------------------------------------
    # Short-name uniqueness only needs to be enforced when creating or
    # updating a record.
    # ------------------------------------------------------------------

    short_name_match = await repository.get_period_by_short_name(
        school_id=school_id,
        short_name=short_name,
    )

    if short_name_match is not None and (
        existing_period is None or short_name_match.id != existing_period.id
    ):
        raise ValueError(
            "Another timetable period with short name "
            f"'{short_name}' already exists in this school.",
        )

    # ------------------------------------------------------------------
    # Create a new period.
    # ------------------------------------------------------------------

    if existing_period is None:
        period = await repository.create_period(
            TimetablePeriodCreate(
                school_id=school_id,
                name=name,
                short_name=short_name,
                period_number=period_number,
                start_time=start_time_value,
                end_time=end_time_value,
                is_registration=is_registration,
                is_break=is_break,
                is_lunch=is_lunch,
                is_active=is_active,
            ),
        )

        await db.flush()

        return RowProcessingResult(
            action=RowProcessingAction.CREATED,
            entity_id=period.id,
            message=(f"Created timetable period '{name}' ({short_name})."),
        )

    # ------------------------------------------------------------------
    # Existing period: update when explicitly permitted.
    # ------------------------------------------------------------------

    existing_period.name = name
    existing_period.short_name = short_name
    existing_period.period_number = period_number
    existing_period.start_time = start_time_value
    existing_period.end_time = end_time_value
    existing_period.is_registration = is_registration
    existing_period.is_break = is_break
    existing_period.is_lunch = is_lunch
    existing_period.is_active = is_active

    existing_period = await repository.save_period(
        existing_period,
    )

    await db.flush()

    return RowProcessingResult(
        action=RowProcessingAction.UPDATED,
        entity_id=existing_period.id,
        message=(f"Updated timetable period '{name}' ({short_name})."),
    )
