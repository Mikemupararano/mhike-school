from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.services.import_service import (
    RowValidationResult,
    validate_row_with_schema,
)


class ClassImportSchema(BaseModel):
    """
    Validation schema for one staged class import row.

    A class requires a name. Teacher assignment is optional and, when
    supplied, is resolved by teacher email within the current school.

    Additional columns are retained so future class-import fields can be
    introduced without redesigning the generic import framework.
    """

    model_config = ConfigDict(
        extra="allow",
        str_strip_whitespace=True,
    )

    name: str = Field(
        min_length=1,
        max_length=255,
    )

    teacher_email: EmailStr | None = None


def validate_class_row(
    row: Mapping[str, Any],
) -> RowValidationResult:
    """
    Validate and normalise one class import row.

    Database-dependent checks belong in the class processor, including:

    - duplicate class names within a school;
    - teacher existence;
    - teacher school membership;
    - teacher role validation.
    """

    return validate_row_with_schema(
        row,
        schema=ClassImportSchema,
    )
