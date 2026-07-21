from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ReportGroupContentScope(BaseModel):
    """
    Identifies one shared reporting-content record.

    Shared content is scoped by:

    - reporting session;
    - class group;
    - subject.

    The school is derived from the authenticated user and must never be
    accepted directly from the client.
    """

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    report_session_id: int = Field(
        ge=1,
    )

    class_group_id: int = Field(
        ge=1,
    )

    subject_name: str = Field(
        min_length=1,
        max_length=100,
    )

    @field_validator("subject_name")
    @classmethod
    def validate_subject_name(cls, value: str) -> str:
        """
        Reject an empty subject after whitespace normalisation.

        ConfigDict strips leading and trailing whitespace before this
        validator runs.
        """

        if not value:
            raise ValueError("Subject name must not be empty.")

        return value


class ReportGroupContentCreate(ReportGroupContentScope):
    """
    Payload for creating shared work-covered content.

    Creation is idempotent at the service/repository layer: callers should
    normally use the upsert endpoint so the same scope can be created or
    updated without first checking whether it exists.
    """

    work_covered: str = Field(
        default="",
        max_length=20_000,
    )


class ReportGroupContentUpdate(BaseModel):
    """
    Payload for changing the shared work-covered text.

    Scope fields are deliberately excluded. Moving a record to another
    reporting session, class or subject would change its identity and should
    instead be handled by creating the correct scoped record.
    """

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    work_covered: str = Field(
        max_length=20_000,
    )


class ReportGroupContentUpsert(ReportGroupContentScope):
    """
    Payload for creating or updating shared content in one operation.
    """

    work_covered: str = Field(
        default="",
        max_length=20_000,
    )


class ReportGroupContentRead(ReportGroupContentScope):
    """
    Shared reporting content returned by the API.
    """

    id: int = Field(
        ge=1,
    )

    school_id: int = Field(
        ge=1,
    )

    work_covered: str

    updated_by_id: int | None = Field(
        default=None,
        ge=1,
    )

    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
        extra="forbid",
        str_strip_whitespace=True,
    )