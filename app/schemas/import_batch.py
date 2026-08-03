from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.import_batch import (
    ImportOperation,
    ImportRowStatus,
    ImportStatus,
)


class ImportTypeRead(BaseModel):
    """
    Public description of one supported import type.
    """

    value: str = Field(
        min_length=1,
        max_length=100,
    )

    label: str = Field(
        min_length=1,
        max_length=150,
    )

    description: str | None = Field(
        default=None,
        max_length=500,
    )


class ImportBatchBase(BaseModel):
    """Fields supplied when an import batch is created."""

    model_config = ConfigDict(
        str_strip_whitespace=True,
    )

    import_type: str = Field(
        min_length=1,
        max_length=100,
    )

    operation: ImportOperation = ImportOperation.CREATE

    original_filename: str = Field(
        min_length=1,
        max_length=255,
    )

    stored_filename: str | None = Field(
        default=None,
        max_length=500,
    )

    file_format: str | None = Field(
        default=None,
        max_length=20,
    )

    mime_type: str | None = Field(
        default=None,
        max_length=150,
    )

    file_size_bytes: int | None = Field(
        default=None,
        ge=0,
    )

    file_hash: str | None = Field(
        default=None,
        max_length=128,
    )

    column_mapping: dict[str, Any] = Field(
        default_factory=dict,
    )

    import_options: dict[str, Any] = Field(
        default_factory=dict,
    )


class ImportBatchCreate(ImportBatchBase):
    """Payload used to create a new import batch."""


class ImportBatchUpdate(BaseModel):
    """
    User-editable and workflow-related import batch fields.

    School ownership, uploader details and counters are controlled by the
    application and are deliberately excluded.
    """

    model_config = ConfigDict(
        str_strip_whitespace=True,
    )

    operation: ImportOperation | None = None

    column_mapping: dict[str, Any] | None = None

    import_options: dict[str, Any] | None = None

    current_stage: str | None = Field(
        default=None,
        max_length=100,
    )

    validation_summary: dict[str, Any] | None = None

    result_summary: dict[str, Any] | None = None

    error_message: str | None = None

    error_report_path: str | None = Field(
        default=None,
        max_length=500,
    )


class ImportBatchRead(ImportBatchBase):
    """Complete persisted representation of an import batch."""

    model_config = ConfigDict(
        from_attributes=True,
    )

    id: int
    school_id: int
    uploaded_by_id: int
    status: ImportStatus

    total_rows: int = Field(
        ge=0,
    )

    validated_rows: int = Field(
        ge=0,
    )

    processed_rows: int = Field(
        ge=0,
    )

    successful_rows: int = Field(
        ge=0,
    )

    warning_rows: int = Field(
        ge=0,
    )

    failed_rows: int = Field(
        ge=0,
    )

    skipped_rows: int = Field(
        ge=0,
    )

    current_stage: str | None

    validation_summary: dict[str, Any]

    result_summary: dict[str, Any]

    error_message: str | None

    error_report_path: str | None

    confirmed_at: datetime | None

    queued_at: datetime | None

    started_at: datetime | None

    completed_at: datetime | None

    cancelled_at: datetime | None

    created_at: datetime

    updated_at: datetime

    is_archived: bool

    archived_at: datetime | None

    archived_by_id: int | None

    archive_reason: str | None


class ImportBatchSummary(BaseModel):
    """Compact representation used by import-batch listing endpoints."""

    model_config = ConfigDict(
        from_attributes=True,
    )

    id: int

    import_type: str

    operation: ImportOperation

    status: ImportStatus

    original_filename: str

    total_rows: int = Field(
        ge=0,
    )

    successful_rows: int = Field(
        ge=0,
    )

    warning_rows: int = Field(
        ge=0,
    )

    failed_rows: int = Field(
        ge=0,
    )

    skipped_rows: int = Field(
        ge=0,
    )

    current_stage: str | None

    created_at: datetime

    completed_at: datetime | None

    is_archived: bool


class ImportBatchProgress(BaseModel):
    """
    Current validation and processing progress for one import batch.

    Values are derived from persisted counters so clients can poll the
    progress endpoint without loading the batch's individual rows.
    """

    model_config = ConfigDict(
        from_attributes=True,
    )

    id: int

    school_id: int

    import_type: str

    status: ImportStatus

    current_stage: str | None

    total_rows: int = Field(
        ge=0,
    )

    validated_rows: int = Field(
        ge=0,
    )

    processed_rows: int = Field(
        ge=0,
    )

    successful_rows: int = Field(
        ge=0,
    )

    warning_rows: int = Field(
        ge=0,
    )

    failed_rows: int = Field(
        ge=0,
    )

    skipped_rows: int = Field(
        ge=0,
    )

    validation_percentage: int = Field(
        ge=0,
        le=100,
    )

    progress_percentage: int = Field(
        ge=0,
        le=100,
    )

    remaining_validation_rows: int = Field(
        ge=0,
    )

    remaining_processing_rows: int = Field(
        ge=0,
    )

    is_finished: bool

    is_archived: bool

    error_message: str | None

    queued_at: datetime | None

    started_at: datetime | None

    completed_at: datetime | None

    cancelled_at: datetime | None

    updated_at: datetime


class ImportRowBase(BaseModel):
    """Common fields belonging to every staged import row."""

    row_number: int = Field(
        gt=0,
    )

    original_data: dict[str, Any] = Field(
        default_factory=dict,
    )

    normalised_data: dict[str, Any] = Field(
        default_factory=dict,
    )

    validation_errors: list[Any] = Field(
        default_factory=list,
    )

    validation_warnings: list[Any] = Field(
        default_factory=list,
    )

    entity_type: str | None = Field(
        default=None,
        max_length=100,
    )


class ImportRowCreate(ImportRowBase):
    """Payload used to persist a staged import row."""

    batch_id: int = Field(
        gt=0,
    )

    school_id: int = Field(
        gt=0,
    )

    status: ImportRowStatus = ImportRowStatus.PENDING


class ImportRowUpdate(BaseModel):
    """Fields that may change while a row is validated or processed."""

    status: ImportRowStatus | None = None

    normalised_data: dict[str, Any] | None = None

    validation_errors: list[Any] | None = None

    validation_warnings: list[Any] | None = None

    entity_type: str | None = Field(
        default=None,
        max_length=100,
    )

    created_entity_id: int | None = Field(
        default=None,
        gt=0,
    )

    attempt_count: int | None = Field(
        default=None,
        ge=0,
    )

    error_message: str | None = None

    processed_at: datetime | None = None


class ImportRowRead(ImportRowBase):
    """Complete persisted representation of an import row."""

    model_config = ConfigDict(
        from_attributes=True,
    )

    id: int

    batch_id: int

    school_id: int

    status: ImportRowStatus

    created_entity_id: int | None

    attempt_count: int = Field(
        ge=0,
    )

    error_message: str | None

    processed_at: datetime | None

    created_at: datetime

    updated_at: datetime
