from __future__ import annotations

from collections.abc import Mapping
from datetime import date
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


class TimetableImportSchema(BaseModel):
    """
    Validate one staged master-timetable import row.

    The school identifier is never trusted from the uploaded file. It is
    supplied by the authenticated import context during processing.

    Additional columns are retained so future timetable import fields can be
    introduced without redesigning the generic import framework.
    """

    model_config = ConfigDict(
        extra="allow",
        str_strip_whitespace=True,
    )

    name: str = Field(
        min_length=1,
        max_length=150,
    )

    academic_year: str = Field(
        min_length=1,
        max_length=20,
    )

    effective_from: date

    effective_to: date | None = None

    is_active: bool = True

    @model_validator(
        mode="after",
    )
    def validate_effective_date_range(
        self,
    ) -> TimetableImportSchema:
        """
        Require the optional end date to be on or after the start date.
        """

        if self.effective_to is not None and self.effective_to < self.effective_from:
            raise ValueError(
                "effective_to cannot be earlier than effective_from.",
            )

        return self


def validate_timetable_row(
    row: Mapping[str, Any],
) -> RowValidationResult:
    """
    Validate and normalise one staged master-timetable import row.

    Database-dependent rules intentionally belong in the processor,
    including:

    - school isolation;
    - matching by name and academic year;
    - create-versus-update behaviour;
    - duplicate timetable handling.
    """

    return validate_row_with_schema(
        row,
        schema=TimetableImportSchema,
    )
