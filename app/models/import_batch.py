from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    Enum as SqlEnum,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.ext.mutable import MutableDict, MutableList
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.school import School
    from app.models.user import User


class ImportOperation(str, Enum):
    CREATE = "create"
    UPDATE = "update"
    UPSERT = "upsert"


class ImportStatus(str, Enum):
    UPLOADED = "uploaded"
    PARSING = "parsing"
    VALIDATING = "validating"
    READY = "ready"
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    COMPLETED_WITH_ERRORS = "completed_with_errors"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ImportRowStatus(str, Enum):
    PENDING = "pending"
    VALID = "valid"
    WARNING = "warning"
    INVALID = "invalid"
    QUEUED = "queued"
    PROCESSING = "processing"
    IMPORTED = "imported"
    UPDATED = "updated"
    SKIPPED = "skipped"
    FAILED = "failed"


class ImportBatch(Base):
    """
    Permanent audit record for a bulk import.

    Import batches and their row-level records are retained indefinitely.
    Normal application workflows archive batches rather than deleting them.

    ``import_type`` is stored as a string so new import handlers can be added
    without changing the database schema.
    """

    __tablename__ = "import_batches"

    __table_args__ = (
        CheckConstraint(
            "total_rows >= 0",
            name="ck_import_batches_total_rows_non_negative",
        ),
        CheckConstraint(
            "validated_rows >= 0",
            name="ck_import_batches_validated_rows_non_negative",
        ),
        CheckConstraint(
            "processed_rows >= 0",
            name="ck_import_batches_processed_rows_non_negative",
        ),
        CheckConstraint(
            "successful_rows >= 0",
            name="ck_import_batches_successful_rows_non_negative",
        ),
        CheckConstraint(
            "warning_rows >= 0",
            name="ck_import_batches_warning_rows_non_negative",
        ),
        CheckConstraint(
            "failed_rows >= 0",
            name="ck_import_batches_failed_rows_non_negative",
        ),
        CheckConstraint(
            "skipped_rows >= 0",
            name="ck_import_batches_skipped_rows_non_negative",
        ),
        CheckConstraint(
            "file_size_bytes IS NULL OR file_size_bytes >= 0",
            name="ck_import_batches_file_size_non_negative",
        ),
        Index(
            "ix_import_batches_school_type_created",
            "school_id",
            "import_type",
            "created_at",
        ),
        Index(
            "ix_import_batches_school_status_created",
            "school_id",
            "status",
            "created_at",
        ),
        Index(
            "ix_import_batches_school_archived_created",
            "school_id",
            "is_archived",
            "created_at",
        ),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True,
    )

    school_id: Mapped[int] = mapped_column(
        ForeignKey(
            "schools.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
        index=True,
    )

    uploaded_by_id: Mapped[int] = mapped_column(
        ForeignKey(
            "users.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
        index=True,
    )

    import_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )

    operation: Mapped[ImportOperation] = mapped_column(
        SqlEnum(
            ImportOperation,
            name="import_operation",
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
            native_enum=False,
            validate_strings=True,
            create_constraint=True,
        ),
        default=ImportOperation.CREATE,
        nullable=False,
        index=True,
    )

    status: Mapped[ImportStatus] = mapped_column(
        SqlEnum(
            ImportStatus,
            name="import_status",
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
            native_enum=False,
            validate_strings=True,
            create_constraint=True,
        ),
        default=ImportStatus.UPLOADED,
        nullable=False,
        index=True,
    )

    original_filename: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    stored_filename: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    file_format: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )

    mime_type: Mapped[str | None] = mapped_column(
        String(150),
        nullable=True,
    )

    file_size_bytes: Mapped[int | None] = mapped_column(
        BigInteger,
        nullable=True,
    )

    file_hash: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
        index=True,
    )

    column_mapping: Mapped[dict[str, Any]] = mapped_column(
        MutableDict.as_mutable(JSON),
        default=dict,
        nullable=False,
    )

    import_options: Mapped[dict[str, Any]] = mapped_column(
        MutableDict.as_mutable(JSON),
        default=dict,
        nullable=False,
    )

    total_rows: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    validated_rows: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    processed_rows: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    successful_rows: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    warning_rows: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    failed_rows: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    skipped_rows: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    current_stage: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    validation_summary: Mapped[dict[str, Any]] = mapped_column(
        MutableDict.as_mutable(JSON),
        default=dict,
        nullable=False,
    )

    result_summary: Mapped[dict[str, Any]] = mapped_column(
        MutableDict.as_mutable(JSON),
        default=dict,
        nullable=False,
    )

    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    error_report_path: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    confirmed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    queued_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    cancelled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    is_archived: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        index=True,
    )

    archived_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    archived_by_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "users.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    archive_reason: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    school: Mapped["School"] = relationship(
        "School",
        foreign_keys=[school_id],
        lazy="selectin",
    )

    uploaded_by: Mapped["User"] = relationship(
        "User",
        foreign_keys=[uploaded_by_id],
        lazy="selectin",
    )

    archived_by: Mapped["User | None"] = relationship(
        "User",
        foreign_keys=[archived_by_id],
        lazy="selectin",
    )

    rows: Mapped[list["ImportRow"]] = relationship(
        "ImportRow",
        back_populates="batch",
        order_by="ImportRow.row_number",
        lazy="selectin",
    )

    @property
    def progress_percentage(self) -> int:
        if self.total_rows <= 0:
            return 0

        return min(
            100,
            max(
                0,
                round((self.processed_rows / self.total_rows) * 100),
            ),
        )

    @property
    def validation_percentage(self) -> int:
        if self.total_rows <= 0:
            return 0

        return min(
            100,
            max(
                0,
                round((self.validated_rows / self.total_rows) * 100),
            ),
        )

    @property
    def is_finished(self) -> bool:
        return self.status in {
            ImportStatus.COMPLETED,
            ImportStatus.COMPLETED_WITH_ERRORS,
            ImportStatus.FAILED,
            ImportStatus.CANCELLED,
        }

    @property
    def can_be_confirmed(self) -> bool:
        return (
            self.status == ImportStatus.READY
            and not self.is_archived
            and self.total_rows > 0
            and self.failed_rows < self.total_rows
        )

    @property
    def can_be_cancelled(self) -> bool:
        return not self.is_archived and self.status in {
            ImportStatus.UPLOADED,
            ImportStatus.PARSING,
            ImportStatus.VALIDATING,
            ImportStatus.READY,
            ImportStatus.QUEUED,
        }

    @property
    def has_errors(self) -> bool:
        return self.failed_rows > 0 or self.status in {
            ImportStatus.COMPLETED_WITH_ERRORS,
            ImportStatus.FAILED,
        }

    def __repr__(self) -> str:
        operation = (
            self.operation.value
            if isinstance(self.operation, ImportOperation)
            else str(self.operation)
        )

        status = (
            self.status.value
            if isinstance(self.status, ImportStatus)
            else str(self.status)
        )

        return (
            f"<ImportBatch "
            f"id={self.id} "
            f"school_id={self.school_id} "
            f"import_type={self.import_type!r} "
            f"operation={operation!r} "
            f"status={status!r}>"
        )


class ImportRow(Base):
    """
    Permanent row-level audit record.

    The entity reference is polymorphic, so ``created_entity_id`` is not a
    foreign key. The combination of ``entity_type`` and ``created_entity_id``
    identifies the record created or updated by the import handler.
    """

    __tablename__ = "import_rows"

    __table_args__ = (
        UniqueConstraint(
            "batch_id",
            "row_number",
            name="uq_import_rows_batch_row_number",
        ),
        CheckConstraint(
            "row_number > 0",
            name="ck_import_rows_row_number_positive",
        ),
        CheckConstraint(
            "attempt_count >= 0",
            name="ck_import_rows_attempt_count_non_negative",
        ),
        Index(
            "ix_import_rows_batch_status",
            "batch_id",
            "status",
        ),
        Index(
            "ix_import_rows_school_status",
            "school_id",
            "status",
        ),
        Index(
            "ix_import_rows_entity_reference",
            "entity_type",
            "created_entity_id",
        ),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True,
    )

    batch_id: Mapped[int] = mapped_column(
        ForeignKey(
            "import_batches.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
        index=True,
    )

    school_id: Mapped[int] = mapped_column(
        ForeignKey(
            "schools.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
        index=True,
    )

    row_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    status: Mapped[ImportRowStatus] = mapped_column(
        SqlEnum(
            ImportRowStatus,
            name="import_row_status",
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
            native_enum=False,
            validate_strings=True,
            create_constraint=True,
        ),
        default=ImportRowStatus.PENDING,
        nullable=False,
        index=True,
    )

    original_data: Mapped[dict[str, Any]] = mapped_column(
        MutableDict.as_mutable(JSON),
        default=dict,
        nullable=False,
    )

    normalised_data: Mapped[dict[str, Any]] = mapped_column(
        MutableDict.as_mutable(JSON),
        default=dict,
        nullable=False,
    )

    validation_errors: Mapped[list[dict[str, Any]]] = mapped_column(
        MutableList.as_mutable(JSON),
        default=list,
        nullable=False,
    )

    validation_warnings: Mapped[list[dict[str, Any]]] = mapped_column(
        MutableList.as_mutable(JSON),
        default=list,
        nullable=False,
    )

    entity_type: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        index=True,
    )

    created_entity_id: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        index=True,
    )

    attempt_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    processed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    batch: Mapped["ImportBatch"] = relationship(
        "ImportBatch",
        back_populates="rows",
        foreign_keys=[batch_id],
        lazy="selectin",
    )

    school: Mapped["School"] = relationship(
        "School",
        foreign_keys=[school_id],
        lazy="selectin",
    )

    @property
    def has_errors(self) -> bool:
        return bool(self.validation_errors) or self.status in {
            ImportRowStatus.INVALID,
            ImportRowStatus.FAILED,
        }

    @property
    def has_warnings(self) -> bool:
        return bool(self.validation_warnings)

    @property
    def was_successful(self) -> bool:
        return self.status in {
            ImportRowStatus.IMPORTED,
            ImportRowStatus.UPDATED,
        }

    @property
    def can_be_processed(self) -> bool:
        return self.status in {
            ImportRowStatus.VALID,
            ImportRowStatus.WARNING,
            ImportRowStatus.QUEUED,
        }

    @property
    def can_be_retried(self) -> bool:
        return self.status in {
            ImportRowStatus.FAILED,
            ImportRowStatus.SKIPPED,
        }

    def __repr__(self) -> str:
        status = (
            self.status.value
            if isinstance(self.status, ImportRowStatus)
            else str(self.status)
        )

        return (
            f"<ImportRow "
            f"id={self.id} "
            f"batch_id={self.batch_id} "
            f"school_id={self.school_id} "
            f"row_number={self.row_number} "
            f"status={status!r}>"
        )
