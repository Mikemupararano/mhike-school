from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
)

from app.services.import_service import (
    RowValidationResult,
    validate_row_with_schema,
)


class EnrollmentImportSchema(BaseModel):
    """
    Validate one staged enrolment import row.

    Enrolment imports use stable identifiers rather than database IDs:

    - ``student_email`` identifies a student within the current school;
    - ``class_name`` identifies a class group within the current school.

    Database-dependent checks—including student existence, class existence,
    school membership, student-role validation and duplicate enrolments—are
    intentionally deferred to the enrolment processor.
    """

    model_config = ConfigDict(
        extra="allow",
        str_strip_whitespace=True,
    )

    student_email: EmailStr

    class_name: str = Field(
        min_length=1,
        max_length=255,
    )


def validate_enrollment_row(
    row: Mapping[str, Any],
) -> RowValidationResult:
    """
    Validate and normalise one staged enrolment import row.

    Database lookups are intentionally deferred to the processor.
    """

    return validate_row_with_schema(
        row,
        schema=EnrollmentImportSchema,
    )
