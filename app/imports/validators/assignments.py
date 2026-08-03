from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Any

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    field_validator,
)

from app.services.import_service import (
    RowValidationResult,
    validate_row_with_schema,
)


class AssignmentImportSchema(BaseModel):
    """
    Validation schema for one assignment import row.

    Human-readable values are imported so that related entities
    can be resolved by the processor.

    Database-dependent validation belongs in the processor.
    """

    model_config = ConfigDict(
        extra="allow",
        str_strip_whitespace=True,
    )

    title: str = Field(
        min_length=1,
        max_length=255,
    )

    course_title: str = Field(
        min_length=1,
        max_length=255,
    )

    teacher_email: EmailStr

    created_by_email: EmailStr | None = None

    description: str | None = None

    due_date: datetime | None = None

    max_score: int = Field(
        default=100,
        ge=1,
    )

    is_published: bool = False

    @field_validator(
        "description",
    )
    @classmethod
    def normalise_description(
        cls,
        value: str | None,
    ) -> str | None:
        """
        Trim optional descriptions.
        """

        if value is None:
            return None

        value = value.strip()

        return value or None


def validate_assignment_row(
    row: Mapping[str, Any],
) -> RowValidationResult:
    """
    Validate and normalise one assignment import row.

    Database-dependent checks belong in the processor, including:

    - course lookup
    - teacher lookup
    - creator lookup
    - school ownership
    - duplicate detection
    """

    return validate_row_with_schema(
        row,
        schema=AssignmentImportSchema,
    )
