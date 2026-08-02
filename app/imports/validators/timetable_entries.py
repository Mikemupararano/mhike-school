from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    model_validator,
)

from app.models.timetable_entry import TimetableDay
from app.services.import_service import (
    RowValidationResult,
    validate_row_with_schema,
)


class TimetableEntryImportSchema(BaseModel):
    """
    Validation schema for one staged timetable-entry import row.

    The school identifier is supplied by the authenticated import context and
    is never trusted from the uploaded file.

    Human-readable values are used to resolve related entities:

    - timetable_name + academic_year;
    - period_number;
    - class_name;
    - course_title;
    - teacher_email.

    At least one teaching-context field must be present so the entry is not an
    empty timetable slot.

    Additional columns are retained for future timetable-import expansion.
    """

    model_config = ConfigDict(
        extra="allow",
        str_strip_whitespace=True,
    )

    timetable_name: str = Field(
        min_length=1,
        max_length=150,
    )

    academic_year: str = Field(
        min_length=1,
        max_length=20,
    )

    day_of_week: TimetableDay

    period_number: int = Field(
        ge=1,
    )

    class_name: str | None = Field(
        default=None,
        max_length=255,
    )

    course_title: str | None = Field(
        default=None,
        max_length=255,
    )

    teacher_email: EmailStr | None = None

    room: str | None = Field(
        default=None,
        max_length=100,
    )

    title: str | None = Field(
        default=None,
        max_length=200,
    )

    notes: str | None = None

    @model_validator(mode="after")
    def validate_teaching_context(
        self,
    ) -> TimetableEntryImportSchema:
        """
        Require at least one class, course, or teacher reference.
        """

        if not any(
            (
                self.class_name,
                self.course_title,
                self.teacher_email,
            )
        ):
            raise ValueError(
                "At least one of class_name, course_title, "
                "or teacher_email must be provided.",
            )

        return self


def validate_timetable_entry_row(
    row: Mapping[str, Any],
) -> RowValidationResult:
    """
    Validate and normalise one staged timetable-entry import row.

    Database-dependent checks belong in the processor, including:

    - timetable existence and school ownership;
    - timetable-period existence and school ownership;
    - class, course, and teacher resolution;
    - teacher role validation;
    - course/teacher consistency;
    - duplicate entry detection;
    - create-versus-update behaviour.
    """

    return validate_row_with_schema(
        row,
        schema=TimetableEntryImportSchema,
    )
