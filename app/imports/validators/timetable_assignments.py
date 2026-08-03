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

from app.models.timetable_assignment import TimetableAssignmentType
from app.services.import_service import (
    RowValidationResult,
    validate_row_with_schema,
)


class TimetableAssignmentImportSchema(BaseModel):
    """
    Validation schema for one timetable-assignment import row.
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

    assignment_type: TimetableAssignmentType

    user_email: EmailStr | None = None

    class_name: str | None = Field(
        default=None,
        max_length=255,
    )

    @model_validator(mode="after")
    def validate_assignment_target(
        self,
    ) -> TimetableAssignmentImportSchema:
        """
        Ensure the correct target field is supplied for each assignment type.
        """

        if self.assignment_type in {
            TimetableAssignmentType.STUDENT,
            TimetableAssignmentType.TEACHER,
        }:
            if self.user_email is None:
                raise ValueError(
                    "user_email is required when assignment_type is "
                    f"'{self.assignment_type.value}'.",
                )

            if self.class_name:
                raise ValueError(
                    "class_name must not be supplied when assignment_type is "
                    f"'{self.assignment_type.value}'.",
                )

        elif self.assignment_type == TimetableAssignmentType.CLASS_GROUP:
            if not self.class_name:
                raise ValueError(
                    "class_name is required when assignment_type is " "'class_group'.",
                )

            if self.user_email is not None:
                raise ValueError(
                    "user_email must not be supplied when assignment_type is "
                    "'class_group'.",
                )

        return self


def validate_timetable_assignment_row(
    row: Mapping[str, Any],
) -> RowValidationResult:
    """
    Validate and normalise one timetable-assignment import row.
    """

    return validate_row_with_schema(
        row,
        schema=TimetableAssignmentImportSchema,
    )
