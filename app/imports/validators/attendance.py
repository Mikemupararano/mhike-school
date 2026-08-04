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

    Field descriptions, examples, types, required status and validation
    constraints are also used to generate metadata-driven CSV templates and
    frontend import guidance.
    """

    model_config = ConfigDict(
        extra="allow",
        str_strip_whitespace=True,
    )

    class_name: str = Field(
        min_length=1,
        max_length=255,
        description=(
            "Name of the class associated with the attendance session. "
            "The class must already exist in the current school."
        ),
        examples=["Year 10 Physics"],
    )

    session_date: date = Field(
        description=("Date of the attendance session in ISO format: YYYY-MM-DD."),
        examples=["2026-08-04"],
    )

    session_type: AttendanceSessionType = Field(
        description=(
            "Attendance session type. Use one of the supported values "
            "published in the template metadata."
        ),
        examples=["am"],
    )

    student_email: EmailStr = Field(
        description=(
            "Email address of the student whose attendance is being recorded. "
            "The student must already belong to the current school."
        ),
        examples=["student@example.com"],
    )

    status: AttendanceStatus = Field(
        description=(
            "Attendance status for the student. Use one of the supported "
            "values published in the template metadata."
        ),
        examples=["present"],
    )

    marked_by_email: EmailStr | None = Field(
        default=None,
        description=(
            "Optional email address of the staff member who marked the "
            "attendance record. The user must belong to the current school."
        ),
        examples=["teacher@example.com"],
    )

    notes: str | None = Field(
        default=None,
        max_length=500,
        description=(
            "Optional attendance note providing additional context, such as "
            "a reason for lateness or absence."
        ),
        examples=["Arrived 10 minutes late due to transport disruption."],
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
