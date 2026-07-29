from __future__ import annotations

import csv
import io
from collections import Counter
from collections.abc import Awaitable, Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.import_batch import (
    ImportBatch,
    ImportRow,
    ImportRowStatus,
    ImportStatus,
)
from app.repositories.import_batches import (
    create_import_rows,
    delete_import_rows_for_batch,
    list_import_rows,
    set_import_batch_status,
    set_import_row_result,
    update_import_batch_counters,
)
from app.schemas.import_batch import ImportRowCreate


class ImportServiceError(Exception):
    """Base exception for import-service failures."""


class ImportFileError(ImportServiceError):
    """Raised when an uploaded import file cannot be read safely."""


class ImportHeaderError(ImportServiceError):
    """Raised when required CSV headers are missing or invalid."""


class ImportBatchStateError(ImportServiceError):
    """Raised when an import operation is invalid for the batch state."""


@dataclass(slots=True, frozen=True)
class ParsedImportFile:
    """Normalised representation of a parsed CSV file."""

    headers: list[str]
    rows: list[dict[str, str | None]]
    encoding: str
    delimiter: str


@dataclass(slots=True, frozen=True)
class RowValidationResult:
    """Result produced by a row validator."""

    is_valid: bool
    normalised_data: dict[str, Any] | None = None
    errors: list[Any] | None = None
    warnings: list[Any] | None = None


@dataclass(slots=True, frozen=True)
class BatchValidationSummary:
    """Aggregate result from validating all rows in one batch."""

    total_rows: int
    valid_rows: int
    invalid_rows: int
    warning_rows: int


RowValidator = Callable[
    [Mapping[str, Any]],
    RowValidationResult | Awaitable[RowValidationResult],
]


def normalise_header(value: str) -> str:
    """
    Convert a CSV header into a stable snake_case field name.

    Examples:
        ``First Name`` -> ``first_name``
        ``E-mail Address`` -> ``e_mail_address``
    """

    cleaned = value.strip().lower()

    output: list[str] = []
    previous_was_separator = False

    for character in cleaned:
        if character.isalnum():
            output.append(character)
            previous_was_separator = False
        elif not previous_was_separator:
            output.append("_")
            previous_was_separator = True

    return "".join(output).strip("_")


def normalise_cell(value: Any) -> str | None:
    """Trim a CSV cell and convert empty values to ``None``."""

    if value is None:
        return None

    cleaned = str(value).strip()
    return cleaned or None


def decode_import_file(
    content: bytes,
    *,
    encodings: Sequence[str] = (
        "utf-8-sig",
        "utf-8",
        "cp1252",
        "latin-1",
    ),
) -> tuple[str, str]:
    """Decode uploaded bytes using a controlled encoding fallback list."""

    if not content:
        raise ImportFileError("The uploaded import file is empty.")

    for encoding in encodings:
        try:
            return content.decode(encoding), encoding
        except UnicodeDecodeError:
            continue

    raise ImportFileError(
        "The import file could not be decoded using a supported encoding.",
    )


def detect_csv_dialect(text: str) -> csv.Dialect:
    """Detect a likely CSV dialect, falling back to standard Excel CSV."""

    sample = text[:8192]

    try:
        return csv.Sniffer().sniff(
            sample,
            delimiters=",;\t|",
        )
    except csv.Error:
        return csv.excel


def parse_csv_bytes(
    content: bytes,
    *,
    required_headers: Sequence[str] | None = None,
    maximum_rows: int = 50_000,
) -> ParsedImportFile:
    """
    Decode and parse CSV bytes.

    Headers are converted to snake_case and cell values are stripped.
    Completely blank rows are ignored.
    """

    if maximum_rows < 1:
        raise ValueError("maximum_rows must be at least 1")

    text, encoding = decode_import_file(content)
    dialect = detect_csv_dialect(text)

    stream = io.StringIO(text, newline="")
    reader = csv.DictReader(stream, dialect=dialect)

    if reader.fieldnames is None:
        raise ImportHeaderError(
            "The import file does not contain a header row.",
        )

    original_headers = [
        str(header).strip() for header in reader.fieldnames if header is not None
    ]

    if not original_headers:
        raise ImportHeaderError(
            "The import file does not contain any usable headers.",
        )

    normalised_headers = [normalise_header(header) for header in original_headers]

    if any(not header for header in normalised_headers):
        raise ImportHeaderError(
            "One or more import headers are blank or invalid.",
        )

    duplicate_headers = [
        header for header, count in Counter(normalised_headers).items() if count > 1
    ]

    if duplicate_headers:
        duplicates = ", ".join(sorted(duplicate_headers))
        raise ImportHeaderError(
            f"Duplicate import headers were found: {duplicates}.",
        )

    if required_headers:
        required = {normalise_header(header) for header in required_headers}
        present = set(normalised_headers)
        missing = sorted(required - present)

        if missing:
            raise ImportHeaderError(
                "Missing required import headers: " + ", ".join(missing),
            )

    header_map = dict(
        zip(original_headers, normalised_headers, strict=True),
    )

    parsed_rows: list[dict[str, str | None]] = []

    for raw_row in reader:
        parsed_row = {
            header_map[original_header]: normalise_cell(
                raw_row.get(original_header),
            )
            for original_header in original_headers
        }

        if not any(value is not None for value in parsed_row.values()):
            continue

        parsed_rows.append(parsed_row)

        if len(parsed_rows) > maximum_rows:
            raise ImportFileError(
                f"The import file exceeds the maximum of "
                f"{maximum_rows:,} data rows.",
            )

    if not parsed_rows:
        raise ImportFileError(
            "The import file does not contain any data rows.",
        )

    return ParsedImportFile(
        headers=normalised_headers,
        rows=parsed_rows,
        encoding=encoding,
        delimiter=dialect.delimiter,
    )


def validate_row_with_schema(
    raw_data: Mapping[str, Any],
    *,
    schema: type[BaseModel],
) -> RowValidationResult:
    """Validate and normalise row data using a Pydantic schema."""

    try:
        validated = schema.model_validate(dict(raw_data))
    except ValidationError as exc:
        return RowValidationResult(
            is_valid=False,
            normalised_data=None,
            errors=exc.errors(),
            warnings=[],
        )

    return RowValidationResult(
        is_valid=True,
        normalised_data=validated.model_dump(mode="json"),
        errors=[],
        warnings=[],
    )


async def stage_csv_rows(
    db: AsyncSession,
    *,
    batch: ImportBatch,
    content: bytes,
    required_headers: Sequence[str] | None = None,
    maximum_rows: int = 50_000,
    replace_existing: bool = False,
    commit: bool = True,
) -> ParsedImportFile:
    """
    Parse a CSV file and stage its rows for later validation.

    Row numbering starts at 2 because row 1 is the CSV header.
    """

    if batch.status in {
        ImportStatus.PROCESSING,
        ImportStatus.COMPLETED,
        ImportStatus.COMPLETED_WITH_ERRORS,
    }:
        raise ImportBatchStateError(
            "Rows cannot be staged after processing has started or completed.",
        )

    parsed = parse_csv_bytes(
        content,
        required_headers=required_headers,
        maximum_rows=maximum_rows,
    )

    if replace_existing:
        await delete_import_rows_for_batch(
            db,
            batch_id=batch.id,
            school_id=batch.school_id,
            commit=False,
        )
    else:
        existing_rows = await list_import_rows(
            db,
            batch_id=batch.id,
            school_id=batch.school_id,
            offset=0,
            limit=1,
        )

        if existing_rows:
            raise ImportBatchStateError(
                "This import batch already contains staged rows.",
            )

    row_payloads = [
        ImportRowCreate(
            batch_id=batch.id,
            school_id=batch.school_id,
            row_number=row_number,
            raw_data=row_data,
            status=ImportRowStatus.PENDING,
        )
        for row_number, row_data in enumerate(
            parsed.rows,
            start=2,
        )
    ]

    await create_import_rows(
        db,
        rows=row_payloads,
        commit=False,
    )

    batch.original_headers = parsed.headers
    batch.file_encoding = parsed.encoding
    batch.file_delimiter = parsed.delimiter
    batch.total_rows = len(row_payloads)
    batch.validated_rows = 0
    batch.processed_rows = 0
    batch.successful_rows = 0
    batch.warning_rows = 0
    batch.failed_rows = 0
    batch.skipped_rows = 0
    batch.current_stage = "staged"
    batch.status = ImportStatus.UPLOADED
    batch.error_message = None

    if commit:
        await db.commit()
        await db.refresh(batch)
    else:
        await db.flush()

    return parsed


async def _resolve_validation_result(
    validator: RowValidator,
    raw_data: Mapping[str, Any],
) -> RowValidationResult:
    """Run either a synchronous or asynchronous row validator."""

    result = validator(raw_data)

    if hasattr(result, "__await__"):
        result = await result

    if not isinstance(result, RowValidationResult):
        raise TypeError(
            "Row validators must return RowValidationResult.",
        )

    return result


async def validate_import_batch(
    db: AsyncSession,
    *,
    batch: ImportBatch,
    validator: RowValidator,
    page_size: int = 500,
    commit: bool = True,
) -> BatchValidationSummary:
    """Validate every staged row in a batch."""

    if page_size < 1 or page_size > 500:
        raise ValueError("page_size must be between 1 and 500")

    if batch.status in {
        ImportStatus.PROCESSING,
        ImportStatus.COMPLETED,
        ImportStatus.COMPLETED_WITH_ERRORS,
        ImportStatus.CANCELLED,
    }:
        raise ImportBatchStateError(
            f"Batch status {batch.status.value!r} does not allow validation.",
        )

    batch.current_stage = "validating"
    batch.error_message = None
    await db.flush()

    total_rows = 0
    valid_rows = 0
    invalid_rows = 0
    warning_rows = 0
    offset = 0

    try:
        while True:
            rows = await list_import_rows(
                db,
                batch_id=batch.id,
                school_id=batch.school_id,
                offset=offset,
                limit=page_size,
            )

            if not rows:
                break

            for row in rows:
                total_rows += 1

                try:
                    result = await _resolve_validation_result(
                        validator,
                        row.raw_data or {},
                    )
                except Exception as exc:
                    result = RowValidationResult(
                        is_valid=False,
                        errors=[
                            {
                                "type": "validator_error",
                                "message": str(exc),
                            }
                        ],
                        warnings=[],
                    )

                warnings = result.warnings or []
                errors = result.errors or []

                if warnings:
                    warning_rows += 1

                if result.is_valid:
                    valid_rows += 1
                    row_status = ImportRowStatus.VALID
                else:
                    invalid_rows += 1
                    row_status = ImportRowStatus.INVALID

                await set_import_row_result(
                    db,
                    row=row,
                    status=row_status,
                    normalised_data=result.normalised_data,
                    validation_errors=errors,
                    validation_warnings=warnings,
                    error_message=(
                        "Row validation failed." if not result.is_valid else None
                    ),
                    commit=False,
                )

            offset += len(rows)
            await db.flush()

        final_status = (
            ImportStatus.READY if invalid_rows == 0 else ImportStatus.VALIDATION_FAILED
        )

        await update_import_batch_counters(
            db,
            batch=batch,
            total_rows=total_rows,
            validated_rows=total_rows,
            warning_rows=warning_rows,
            failed_rows=invalid_rows,
            commit=False,
        )

        await set_import_batch_status(
            db,
            batch=batch,
            status=final_status,
            current_stage=("ready" if invalid_rows == 0 else "validation_failed"),
            error_message=(
                None
                if invalid_rows == 0
                else f"{invalid_rows} row(s) failed validation."
            ),
            commit=False,
        )

        if commit:
            await db.commit()
            await db.refresh(batch)
        else:
            await db.flush()

    except Exception as exc:
        await db.rollback()

        batch.status = ImportStatus.FAILED
        batch.current_stage = "validation_failed"
        batch.error_message = str(exc)

        if commit:
            db.add(batch)
            await db.commit()
            await db.refresh(batch)

        raise

    return BatchValidationSummary(
        total_rows=total_rows,
        valid_rows=valid_rows,
        invalid_rows=invalid_rows,
        warning_rows=warning_rows,
    )


async def refresh_import_batch_counters(
    db: AsyncSession,
    *,
    batch: ImportBatch,
    commit: bool = True,
) -> ImportBatch:
    """Recalculate batch counters directly from its current row states."""

    rows = await list_import_rows(
        db,
        batch_id=batch.id,
        school_id=batch.school_id,
        offset=0,
        limit=500,
    )

    all_rows: list[ImportRow] = list(rows)
    offset = len(rows)

    while len(rows) == 500:
        rows = await list_import_rows(
            db,
            batch_id=batch.id,
            school_id=batch.school_id,
            offset=offset,
            limit=500,
        )
        all_rows.extend(rows)
        offset += len(rows)

    statuses = Counter(row.status for row in all_rows)

    validated_rows = sum(
        statuses.get(status, 0)
        for status in {
            ImportRowStatus.VALID,
            ImportRowStatus.INVALID,
            ImportRowStatus.IMPORTED,
            ImportRowStatus.UPDATED,
            ImportRowStatus.SKIPPED,
            ImportRowStatus.FAILED,
        }
    )

    processed_rows = sum(
        statuses.get(status, 0)
        for status in {
            ImportRowStatus.IMPORTED,
            ImportRowStatus.UPDATED,
            ImportRowStatus.SKIPPED,
            ImportRowStatus.FAILED,
        }
    )

    successful_rows = statuses.get(ImportRowStatus.IMPORTED, 0) + statuses.get(
        ImportRowStatus.UPDATED, 0
    )

    failed_rows = statuses.get(ImportRowStatus.INVALID, 0) + statuses.get(
        ImportRowStatus.FAILED, 0
    )

    skipped_rows = statuses.get(ImportRowStatus.SKIPPED, 0)

    warning_rows = sum(1 for row in all_rows if bool(row.validation_warnings))

    return await update_import_batch_counters(
        db,
        batch=batch,
        total_rows=len(all_rows),
        validated_rows=validated_rows,
        processed_rows=processed_rows,
        successful_rows=successful_rows,
        warning_rows=warning_rows,
        failed_rows=failed_rows,
        skipped_rows=skipped_rows,
        commit=commit,
    )


async def cancel_import_batch(
    db: AsyncSession,
    *,
    batch: ImportBatch,
    reason: str | None = None,
    commit: bool = True,
) -> ImportBatch:
    """Cancel an import batch that has not already completed."""

    if batch.status in {
        ImportStatus.COMPLETED,
        ImportStatus.COMPLETED_WITH_ERRORS,
    }:
        raise ImportBatchStateError(
            "A completed import batch cannot be cancelled.",
        )

    return await set_import_batch_status(
        db,
        batch=batch,
        status=ImportStatus.CANCELLED,
        current_stage="cancelled",
        error_message=reason,
        commit=commit,
    )
