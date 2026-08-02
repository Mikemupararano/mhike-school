from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.services.import_service import (
    RowValidationResult,
    validate_row_with_schema,
)


class ParentImportSchema(BaseModel):
    """
    Validation schema for one staged parent import row.

    Parent imports resolve the linked student using the student's email
    address. The processor creates or reuses the parent account and then
    creates the parent-student relationship.

    Additional columns are retained so future parent-import fields can be
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

    Database-dependent checks belong in the parent processor, including:

    - student existence;
    - student school membership;
    - student role validation;
    - existing parent account checks;
    - parent role checks;
    - duplicate parent-student relationship detection.
    """

    return validate_row_with_schema(
        row,
        schema=ParentImportSchema,
    )
