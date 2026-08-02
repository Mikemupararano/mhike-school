from __future__ import annotations

from collections.abc import Mapping
from datetime import time
from typing import Any

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    model_validator,
)

from app.services.import_service import (
    RowValidationResult,
    validate_row_with_schema,
)


class TimetablePeriodImportSchema(BaseModel):
    """
    Validation schema for one staged timetable-period import row.

    The school identifier is never trusted from the uploaded file. It is
    supplied by the authenticated import context during processing.

    Additional columns are retained so the timetable-period import format can
    grow without redesigning the generic import framework.
    """

    model_config = ConfigDict(
        extra="allow",
        str_strip_whitespace=True,
    )

    name: str = Field(
        min_length=1,
        max_length=100,
    )

    short_name: str = Field(
        min_length=1,
        max_length=20,
    )

    period_number: int = Field(
        ge=1,
    )

    start_time: time
    end_time: time

    is_registration: bool = False
    is_break: bool = False
    is_lunch: bool = False
    is_active: bool = True

    @model_validator(mode="after")
    def validate_time_range(
        self,
    ) -> TimetablePeriodImportSchema:
        """
        Ensure each period finishes after it starts.
        """

        if self.end_time <= self.start_time:
            raise ValueError(
                "end_time must be later than start_time.",
            )

        return self


def validate_timetable_period_row(
    row: Mapping[str, Any],
) -> RowValidationResult:
    """
    Validate and normalise one timetable-period import row.

    Database-dependent rules belong in the processor, including:

    - school isolation;
    - matching an existing period by number;
    - duplicate short-name detection;
    - create-versus-update behaviour.
    """

    return validate_row_with_schema(
        row,
        schema=TimetablePeriodImportSchema,
    )
