from __future__ import annotations

from datetime import time
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.imports.registry import (
    RowProcessingAction,
    RowProcessingResult,
)
from app.models.timetable_period import TimetablePeriod
from app.repositories.timetable import TimetableRepository


def _required_string(
    row: dict[str, Any],
    field_name: str,
) -> str:
    """
    Return a required, trimmed string value.

    The validator should normally reject malformed rows before processing.
    These checks protect direct processor calls and defensive code paths.
    """

    value = row.get(field_name)

    if value is None:
        raise ValueError(
            f"Timetable period import field '{field_name}' is required.",
        )

    cleaned = str(value).strip()

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
    """

    value = row.get(field_name)

    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
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

    Validated import rows are stored in JSON, so time values normally arrive
    as ISO-formatted strings such as ``09:00:00``. Direct processor calls may
    still provide ``datetime.time`` instances.
    """

    value = row.get(field_name)

    if isinstance(value, time):
        return value

    if isinstance(value, str):
        cleaned = value.strip()

        if cleaned:
            try:
                return time.fromisoformat(cleaned)
            except ValueError:
                pass

    raise ValueError(
        f"Timetable period import field '{field_name}' " "must be a valid time.",
    )


def _optional_boolean(
    row: dict[str, Any],
    field_name: str,
    *,
    default: bool,
) -> bool:
    """
    Return an optional boolean value.

    The generic validator should already coerce accepted source values.
    This processor therefore requires an actual bool when the field exists.
    """

    value = row.get(
        field_name,
        default,
    )

    if not isinstance(value, bool):
        raise ValueError(
            f"Timetable period import field '{field_name}' " "must be a boolean.",
        )

    return value


async def process_timetable_period_row(
    db: AsyncSession,
    row: dict[str, Any],
    school_id: int,
) -> RowProcessingResult:
    """
    Create or update one timetable period from validated import data.

    Matching is performed using ``period_number`` within the current school.

    Duplicate short names are rejected when they belong to a different
    period in the same school.

    Transaction ownership belongs to the generic import service or task.
    This processor therefore never commits or rolls back the session.
    """

    if not isinstance(school_id, int) or isinstance(school_id, bool) or school_id < 1:
        raise ValueError(
            "school_id must be a positive integer.",
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

    start_time_value = _required_time(
        row,
        "start_time",
    )

    end_time_value = _required_time(
        row,
        "end_time",
    )

    if len(name) > 100:
        raise ValueError(
            "Timetable period import field 'name' " "cannot exceed 100 characters.",
        )

    if len(short_name) > 20:
        raise ValueError(
            "Timetable period import field 'short_name' "
            "cannot exceed 20 characters.",
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

    if existing_period is None:
        period = TimetablePeriod(
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
        )

        db.add(
            period,
        )
        await db.flush()
        await db.refresh(
            period,
        )

        return RowProcessingResult(
            action=RowProcessingAction.CREATED,
            entity_id=period.id,
            message=(f"Created timetable period '{name}' ({short_name})."),
        )

    existing_period.name = name
    existing_period.short_name = short_name
    existing_period.period_number = period_number
    existing_period.start_time = start_time_value
    existing_period.end_time = end_time_value
    existing_period.is_registration = is_registration
    existing_period.is_break = is_break
    existing_period.is_lunch = is_lunch
    existing_period.is_active = is_active

    await repository.save_period(
        existing_period,
    )

    return RowProcessingResult(
        action=RowProcessingAction.UPDATED,
        entity_id=existing_period.id,
        message=(f"Updated timetable period '{name}' ({short_name})."),
    )
