from __future__ import annotations

from datetime import date, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.imports.registry import (
    RowProcessingAction,
    RowProcessingResult,
)
from app.repositories.timetable import TimetableRepository
from app.schemas.timetable import TimetableCreate


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
            f"Timetable import field '{field_name}' is required.",
        )

    cleaned = str(
        value,
    ).strip()

    if not cleaned:
        raise ValueError(
            f"Timetable import field '{field_name}' cannot be blank.",
        )

    return cleaned


def _required_date(
    row: dict[str, Any],
    field_name: str,
) -> date:
    """
    Return a required date value.

    Validated staged rows normally contain ISO-formatted strings because
    import rows are persisted as JSON. Direct processor calls may provide
    either ``date`` or ``datetime`` instances.
    """

    value = row.get(
        field_name,
    )

    if isinstance(
        value,
        datetime,
    ):
        return value.date()

    if isinstance(
        value,
        date,
    ):
        return value

    if isinstance(
        value,
        str,
    ):
        cleaned = value.strip()

        if cleaned:
            try:
                return date.fromisoformat(
                    cleaned,
                )
            except ValueError:
                pass

    raise ValueError(
        f"Timetable import field '{field_name}' must be a valid date.",
    )


def _optional_date(
    row: dict[str, Any],
    field_name: str,
) -> date | None:
    """
    Return an optional date value.

    Missing, null and whitespace-only values are normalised to ``None``.
    Direct processor calls may provide either ``date`` or ``datetime``
    instances.
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
        return value.date()

    if isinstance(
        value,
        date,
    ):
        return value

    if isinstance(
        value,
        str,
    ):
        cleaned = value.strip()

        if not cleaned:
            return None

        try:
            return date.fromisoformat(
                cleaned,
            )
        except ValueError:
            pass

    raise ValueError(
        f"Timetable import field '{field_name}' must be a valid date.",
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
            f"Timetable import field '{field_name}' must be a boolean.",
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


async def process_timetable_row(
    db: AsyncSession,
    row: dict[str, Any],
    school_id: int,
) -> RowProcessingResult:
    """
    Create or update one master timetable from validated import data.

    Existing timetables are matched using the school-scoped natural key:

    - ``school_id``;
    - normalised ``name``;
    - normalised ``academic_year``.

    The authenticated import context supplies ``school_id``. Any school
    identifier included in the uploaded row is ignored.

    New records are passed to the repository as ``TimetableCreate`` schemas,
    matching the repository contract. Existing records are updated as ORM
    entities through ``save_timetable``.

    Transaction ownership belongs to the generic import service or
    background task. This processor never commits or rolls back the session.
    """

    _validate_school_id(
        school_id,
    )

    name = _required_string(
        row,
        "name",
    )

    academic_year = _required_string(
        row,
        "academic_year",
    )

    if len(name) > 150:
        raise ValueError(
            "Timetable import field 'name' cannot exceed 150 characters.",
        )

    if len(academic_year) > 20:
        raise ValueError(
            "Timetable import field 'academic_year' " "cannot exceed 20 characters.",
        )

    effective_from = _required_date(
        row,
        "effective_from",
    )

    effective_to = _optional_date(
        row,
        "effective_to",
    )

    if effective_to is not None and effective_to < effective_from:
        raise ValueError(
            "Timetable import field 'effective_to' "
            "cannot be earlier than effective_from.",
        )

    is_active = _optional_boolean(
        row,
        "is_active",
        default=True,
    )

    repository = TimetableRepository(
        db,
    )

    existing_timetable = await repository.get_timetable_by_name_and_year(
        school_id=school_id,
        name=name,
        academic_year=academic_year,
    )

    if existing_timetable is None:
        timetable = await repository.create_timetable(
            TimetableCreate(
                school_id=school_id,
                name=name,
                academic_year=academic_year,
                effective_from=effective_from,
                effective_to=effective_to,
                is_active=is_active,
            ),
        )

        return RowProcessingResult(
            action=RowProcessingAction.CREATED,
            entity_id=timetable.id,
            message=(
                f"Created timetable '{name}' " f"for academic year '{academic_year}'."
            ),
        )

    existing_timetable.name = name
    existing_timetable.academic_year = academic_year
    existing_timetable.effective_from = effective_from
    existing_timetable.effective_to = effective_to
    existing_timetable.is_active = is_active

    existing_timetable = await repository.save_timetable(
        existing_timetable,
    )

    return RowProcessingResult(
        action=RowProcessingAction.UPDATED,
        entity_id=existing_timetable.id,
        message=(
            f"Updated timetable '{name}' " f"for academic year '{academic_year}'."
        ),
    )
