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


class TeacherImportSchema(BaseModel):
    """
    Validate one staged teacher import row.

    Additional columns are retained so future teacher-specific fields can be
    introduced without redesigning the generic import framework.
    """

    model_config = ConfigDict(
        extra="allow",
        str_strip_whitespace=True,
    )

    email: EmailStr

    first_name: str = Field(
        min_length=1,
    )

    last_name: str = Field(
        min_length=1,
    )


def validate_teacher_row(
    row: Mapping[str, Any],
) -> RowValidationResult:
    """
    Validate and normalise one teacher import row.

    Database-dependent checks—including duplicate detection, existing-user
    role conflicts and school membership—belong in the teacher processor
    rather than this schema validator.
    """

    return validate_row_with_schema(
        row,
        schema=TeacherImportSchema,
    )
