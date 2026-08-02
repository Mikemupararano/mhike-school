from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.services.import_service import (
    RowValidationResult,
    validate_row_with_schema,
)


class EnrollmentImportSchema(BaseModel):
    """
    Validation schema for one staged enrolment import row.

    Imports use stable identifiers rather than database IDs.

    Required fields:

    - student_email
    - class_name

    Database-dependent checks (student existence, class existence,
    duplicate enrolments, school membership and student role) belong
    in the enrolment processor.
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
    Validate and normalise one enrolment import row.

    Database lookups are intentionally deferred to the processor.
    """

    return validate_row_with_schema(
        row,
        schema=EnrollmentImportSchema,
    )
