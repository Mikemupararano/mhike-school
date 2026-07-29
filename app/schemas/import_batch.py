from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.import_batch import (
    ImportOperation,
    ImportRowStatus,
    ImportStatus,
)


class ImportBatchBase(BaseModel):
    import_type: str = Field(min_length=1, max_length=100)
    operation: ImportOperation = ImportOperation.CREATE
    original_filename: str = Field(min_length=1, max_length=255)
    stored_filename: str | None = Field(default=None, max_length=500)
    file_format: str | None = Field(default=None, max_length=20)
    mime_type: str | None = Field(default=None, max_length=150)
    file_size_bytes: int | None = Field(default=None, ge=0)
    file_hash: str | None = Field(default=None, max_length=128)
    column_mapping: dict[str, Any] = Field(default_factory=dict)
    import_options: dict[str, Any] = Field(default_factory=dict)


class ImportBatchCreate(ImportBatchBase):
    pass


class ImportBatchUpdate(BaseModel):
    operation: ImportOperation | None = None
    column_mapping: dict[str, Any] | None = None
    import_options: dict[str, Any] | None = None
    current_stage: str | None = Field(default=None, max_length=100)
    validation_summary: dict[str, Any] | None = None
    result_summary: dict[str, Any] | None = None
    error_message: str | None = None
    error_report_path: str | None = Field(default=None, max_length=500)


class ImportBatchRead(ImportBatchBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    school_id: int
    uploaded_by_id: int
    status: ImportStatus

    total_rows: int
    validated_rows: int
    processed_rows: int
    successful_rows: int
    warning_rows: int
    failed_rows: int
    skipped_rows: int

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
    model_config = ConfigDict(from_attributes=True)

    id: int
    import_type: str
    operation: ImportOperation
    status: ImportStatus
    original_filename: str

    total_rows: int
    successful_rows: int
    warning_rows: int
    failed_rows: int
    skipped_rows: int

    current_stage: str | None
    created_at: datetime
    completed_at: datetime | None
    is_archived: bool


class ImportRowBase(BaseModel):
    row_number: int = Field(gt=0)
    original_data: dict[str, Any] = Field(default_factory=dict)
    normalised_data: dict[str, Any] = Field(default_factory=dict)
    validation_errors: list[Any] = Field(default_factory=list)
    validation_warnings: list[Any] = Field(default_factory=list)
    entity_type: str | None = Field(default=None, max_length=100)


class ImportRowCreate(ImportRowBase):
    batch_id: int
    school_id: int
    status: ImportRowStatus = ImportRowStatus.PENDING


class ImportRowUpdate(BaseModel):
    status: ImportRowStatus | None = None
    normalised_data: dict[str, Any] | None = None
    validation_errors: list[Any] | None = None
    validation_warnings: list[Any] | None = None
    entity_type: str | None = Field(default=None, max_length=100)
    created_entity_id: int | None = None
    attempt_count: int | None = Field(default=None, ge=0)
    error_message: str | None = None
    processed_at: datetime | None = None


class ImportRowRead(ImportRowBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    batch_id: int
    school_id: int
    status: ImportRowStatus
    created_entity_id: int | None
    attempt_count: int
    error_message: str | None
    processed_at: datetime | None
    created_at: datetime
    updated_at: datetime
