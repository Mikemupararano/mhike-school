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


class ParentImportSchema(BaseModel):
    """
    Validate one staged parent import row.

    Parent imports resolve the linked student using ``student_email``. The
    processor creates or updates the parent account and then creates or reuses
    the parent-student relationship.

    Additional columns are retained so future parent-specific fields can be
    introduced without redesigning the generic import framework.
    """

    model_config = ConfigDict(
        extra="allow",
        str_strip_whitespace=True,
    )

    email: EmailStr

    first_name: str = Field(
        min_length=1,
        max_length=100,
    )

    last_name: str = Field(
        min_length=1,
        max_length=100,
    )

    phone: str | None = Field(
        default=None,
        max_length=50,
    )

    student_email: EmailStr


def validate_parent_row(
    row: Mapping[str, Any],
) -> RowValidationResult:
    """
    Validate and normalise one staged parent import row.

    Database-dependent checks belong in the parent processor, including
    student existence, school membership, role validation, parent account
    conflicts and duplicate parent-student relationships.
    """

    return validate_row_with_schema(
        row,
        schema=ParentImportSchema,
    )
