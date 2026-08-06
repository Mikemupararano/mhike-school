from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.services.import_service import (
    RowValidationResult,
    validate_row_with_schema,
)


class CourseImportSchema(BaseModel):
    """
    Validation schema for one staged course import row.

    A course requires:

    - a title;
    - a teacher email used to resolve the owning teacher within the
      current school.

    The description is optional.

    Imported courses are always created unpublished. Publishing and
    unpublishing remain explicit application workflows and are never
    performed implicitly during import.

    Additional CSV columns are intentionally preserved so future course
    import fields can be introduced without redesigning the generic
    import framework.
    """

    model_config = ConfigDict(
        extra="allow",
        str_strip_whitespace=True,
    )

    title: str = Field(
        min_length=1,
        max_length=255,
    )

    description: str | None = Field(
        default=None,
        max_length=2000,
    )

    teacher_email: EmailStr


def validate_course_row(
    row: Mapping[str, Any],
) -> RowValidationResult:
    """
    Validate and normalise one staged course import row.

    This validator performs only schema-level validation.

    Database-dependent validation intentionally belongs in the course
    processor, including:

    - teacher existence;
    - teacher school membership;
    - teacher role validation;
    - matching existing courses by school, teacher and title.
    """

    return validate_row_with_schema(
        row,
        schema=CourseImportSchema,
    )
