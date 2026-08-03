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
    model_validator,
)

from app.services.import_service import (
    RowValidationResult,
    validate_row_with_schema,
)

ASSIGNMENT_SUBMISSION_STATUSES = {
    "submitted",
    "graded",
}


class AssignmentSubmissionImportSchema(BaseModel):
    """
    Validation schema for one assignment-submission import row.
    """

    model_config = ConfigDict(
        extra="allow",
        str_strip_whitespace=True,
    )

    assignment_title: str = Field(
        min_length=1,
        max_length=255,
    )

    course_title: str = Field(
        min_length=1,
        max_length=255,
    )

    teacher_email: EmailStr
    student_email: EmailStr

    submission_text: str | None = None

    attachment_url: str | None = Field(
        default=None,
        max_length=1000,
    )

    status: str = "submitted"

    submitted_at: datetime | None = None

    score: int | None = Field(
        default=None,
        ge=0,
    )

    feedback: str | None = None

    graded_by_email: EmailStr | None = None
    graded_at: datetime | None = None

    @field_validator(
        "submission_text",
        "attachment_url",
        "feedback",
    )
    @classmethod
    def normalise_optional_text(
        cls,
        value: str | None,
    ) -> str | None:
        """
        Trim optional text fields and convert blanks to None.
        """

        if value is None:
            return None

        cleaned = value.strip()

        return cleaned or None

    @field_validator("status")
    @classmethod
    def normalise_status(
        cls,
        value: str,
    ) -> str:
        """
        Normalise and validate the submission status.
        """

        cleaned = value.strip().lower()

        if cleaned not in ASSIGNMENT_SUBMISSION_STATUSES:
            raise ValueError(
                "status must be one of: submitted, graded.",
            )

        return cleaned

    @model_validator(mode="after")
    def validate_status_fields(
        self,
    ) -> AssignmentSubmissionImportSchema:
        """
        Enforce fields required for graded submissions.
        """

        if self.status == "graded":
            if self.score is None:
                raise ValueError(
                    "score is required when status is 'graded'.",
                )

            if self.graded_by_email is None:
                raise ValueError(
                    "graded_by_email is required when status is 'graded'.",
                )

        return self


def validate_assignment_submission_row(
    row: Mapping[str, Any],
) -> RowValidationResult:
    """
    Validate and normalise one assignment-submission import row.
    """

    return validate_row_with_schema(
        row,
        schema=AssignmentSubmissionImportSchema,
    )
