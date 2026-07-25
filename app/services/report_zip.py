from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from io import BytesIO
from pathlib import PurePosixPath
from zipfile import ZIP_DEFLATED, BadZipFile, ZipFile

from app.services.report_pdf import (
    ReportPdfData,
    build_report_pdf_filename,
    generate_report_pdf_bytes,
)

logger = logging.getLogger(__name__)

_SAFE_ARCHIVE_PATH_PATTERN = re.compile(r"[^A-Za-z0-9._/-]+")
_MAX_ARCHIVE_ITEMS = 10_000
_MIN_VALID_PDF_SIZE = 100


@dataclass(slots=True, frozen=True)
class ReportZipItem:
    """
    One report to be included in a ZIP archive.

    ``archive_folder`` is optional and allows callers to group reports into
    safe, relative folders such as ``"Year 10/10A"``. Existing callers that
    provide only ``report`` remain fully supported.
    """

    report: ReportPdfData
    archive_folder: str | None = None


def _clean_archive_folder(value: str | None) -> str:
    """
    Return a safe relative POSIX folder path for use inside a ZIP archive.

    Absolute paths, parent traversal, drive prefixes, and empty path segments
    are removed so archive entries cannot escape the archive root.
    """

    if value is None:
        return ""

    cleaned = _SAFE_ARCHIVE_PATH_PATTERN.sub("-", str(value).strip())
    cleaned = cleaned.replace("\\", "/")

    safe_parts: list[str] = []

    for part in PurePosixPath(cleaned).parts:
        candidate = part.strip(" ._-")

        if not candidate or candidate in {".", "..", "/"}:
            continue

        # Reject Windows drive-like segments such as C:
        if candidate.endswith(":"):
            continue

        safe_parts.append(candidate)

    return "/".join(safe_parts)


def _build_archive_name(item: ReportZipItem) -> str:
    filename = build_report_pdf_filename(item.report)
    folder = _clean_archive_folder(item.archive_folder)

    if not folder:
        return filename

    return f"{folder}/{filename}"


def _make_unique_archive_name(
    desired_name: str,
    *,
    used_names: set[str],
) -> str:
    """
    Return a case-insensitively unique archive entry name.

    ZIP archives are case-sensitive, but many extraction targets are not.
    Case-folded comparison prevents collisions such as ``Report.pdf`` and
    ``report.pdf`` on Windows and macOS.
    """

    normalised = desired_name.casefold()

    if normalised not in used_names:
        used_names.add(normalised)
        return desired_name

    path = PurePosixPath(desired_name)
    suffix = path.suffix
    stem = path.stem
    parent = "" if str(path.parent) == "." else f"{path.parent}/"

    index = 2

    while True:
        candidate = f"{parent}{stem}_{index}{suffix}"
        normalised_candidate = candidate.casefold()

        if normalised_candidate not in used_names:
            used_names.add(normalised_candidate)
            return candidate

        index += 1


def _validate_pdf_bytes(pdf_bytes: bytes, *, archive_name: str) -> None:
    if not isinstance(pdf_bytes, bytes):
        raise RuntimeError(
            f"PDF generation returned an invalid value for {archive_name!r}."
        )

    if not pdf_bytes.startswith(b"%PDF"):
        raise RuntimeError(
            f"Generated content for {archive_name!r} is not a valid PDF."
        )

    if len(pdf_bytes) < _MIN_VALID_PDF_SIZE:
        raise RuntimeError(f"Generated PDF for {archive_name!r} is unexpectedly empty.")


def _validate_zip_bytes(zip_bytes: bytes, *, expected_items: int) -> None:
    if not zip_bytes.startswith(b"PK"):
        raise RuntimeError("The generated report archive is not a valid ZIP file.")

    try:
        with ZipFile(BytesIO(zip_bytes), mode="r") as archive:
            names = archive.namelist()

            if len(names) != expected_items:
                raise RuntimeError(
                    "The generated report archive contains an unexpected "
                    "number of files."
                )

            corrupt_entry = archive.testzip()
            if corrupt_entry is not None:
                raise RuntimeError(
                    f"The generated report archive contains a corrupt entry: "
                    f"{corrupt_entry!r}."
                )
    except BadZipFile as exc:
        raise RuntimeError(
            "The generated report archive is not a readable ZIP file."
        ) from exc


def generate_report_zip_bytes(
    reports: list[ReportZipItem],
) -> bytes:
    """
    Generate a ZIP archive containing one PDF per report.

    PDFs are generated entirely in memory. Filenames are made unique using
    case-insensitive comparison for safe extraction across operating systems.

    Raises:
        ValueError: If no reports are supplied or the batch is unreasonably
            large.
        RuntimeError: If PDF generation or ZIP construction fails.
    """

    if not reports:
        raise ValueError("At least one report is required.")

    if len(reports) > _MAX_ARCHIVE_ITEMS:
        raise ValueError(
            f"A maximum of {_MAX_ARCHIVE_ITEMS} reports may be exported "
            "in one archive."
        )

    output = BytesIO()
    expected_items = 0

    try:
        with ZipFile(
            output,
            mode="w",
            compression=ZIP_DEFLATED,
            compresslevel=6,
            allowZip64=True,
            strict_timestamps=True,
        ) as archive:
            archive.comment = b"MHike School student report export"

            used_names: set[str] = set()

            for index, item in enumerate(reports, start=1):
                if not isinstance(item, ReportZipItem):
                    raise TypeError(
                        "Each report ZIP entry must be a ReportZipItem instance."
                    )

                desired_name = _build_archive_name(item)
                archive_name = _make_unique_archive_name(
                    desired_name,
                    used_names=used_names,
                )

                try:
                    pdf_bytes = generate_report_pdf_bytes(item.report)
                    _validate_pdf_bytes(
                        pdf_bytes,
                        archive_name=archive_name,
                    )
                    archive.writestr(
                        archive_name,
                        pdf_bytes,
                        compress_type=ZIP_DEFLATED,
                        compresslevel=6,
                    )
                    expected_items += 1
                except Exception as exc:
                    logger.exception(
                        "Unable to add report %s of %s to ZIP archive: %s",
                        index,
                        len(reports),
                        archive_name,
                    )
                    raise RuntimeError(
                        f"Unable to generate report archive entry " f"{archive_name!r}."
                    ) from exc

        zip_bytes = output.getvalue()
    except (ValueError, TypeError, RuntimeError):
        raise
    except Exception as exc:
        logger.exception("Unable to generate report ZIP archive.")
        raise RuntimeError("Unable to generate the report ZIP archive.") from exc
    finally:
        output.close()

    _validate_zip_bytes(
        zip_bytes,
        expected_items=expected_items,
    )

    return zip_bytes
