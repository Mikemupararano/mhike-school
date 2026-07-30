from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.services.import_service import (
    RowValidationResult,
    validate_row_with_schema,
)


class StudentImportSchema(BaseModel):
    """
    Validation schema for one staged student import row.

    Additional columns are retained so that future student-import fields
    can be processed without changing the generic validation framework.
    """

    model_config = ConfigDict(
        extra="allow",
        str_strip_whitespace=True,
    )

    email: EmailStr
    first_name: str = Field(min_length=1)
    last_name: str = Field(min_length=1)


def validate_student_row(
    row: Mapping[str, Any],
) -> RowValidationResult:
    """
    Validate and normalise one student import row.

    Database-dependent rules, including duplicate detection, existing-user
    checks, school membership and enrolment handling, belong in the student
    import processor rather than this validator.
    """

    return validate_row_with_schema(
        row,
        schema=StudentImportSchema,
    )
