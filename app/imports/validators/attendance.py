from __future__ import annotations

from collections.abc import Mapping
from datetime import date
from typing import Any

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    field_validator,
)

from app.models.attendance_record import AttendanceStatus
from app.models.attendance_session import AttendanceSessionType
from app.services.import_service import (
    RowValidationResult,
    validate_row_with_schema,
)


class AttendanceImportSchema(BaseModel):
    """
    Validation schema for one attendance import row.
    """

    model_config = ConfigDict(
        extra="allow",
        str_strip_whitespace=True,
    )

    class_name: str = Field(
        min_length=1,
        max_length=255,
    )

    session_date: date

    session_type: AttendanceSessionType

    student_email: EmailStr

    status: AttendanceStatus

    marked_by_email: EmailStr | None = None

    notes: str | None = Field(
        default=None,
        max_length=500,
    )

    @field_validator("notes")
    @classmethod
    def normalise_notes(
        cls,
        value: str | None,
    ) -> str | None:
        """
        Trim optional notes and convert blank text to None.
        """

        if value is None:
            return None

        cleaned = value.strip()

        return cleaned or None


def validate_attendance_row(
    row: Mapping[str, Any],
) -> RowValidationResult:
    """
    Validate and normalise one attendance import row.
    """

    return validate_row_with_schema(
        row,
        schema=AttendanceImportSchema,
    )
