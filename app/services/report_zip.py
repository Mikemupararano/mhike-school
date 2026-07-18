from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from zipfile import ZIP_DEFLATED, ZipFile

from app.services.report_pdf import (
    ReportPdfData,
    build_report_pdf_filename,
    generate_report_pdf_bytes,
)


@dataclass(slots=True, frozen=True)
class ReportZipItem:
    """
    One report to be included in the ZIP archive.
    """

    report: ReportPdfData


def generate_report_zip_bytes(
    reports: list[ReportZipItem],
) -> bytes:
    """
    Generate a ZIP archive containing one PDF per report.

    The PDFs are generated entirely in memory and returned as ZIP bytes.
    """

    if not reports:
        raise ValueError("At least one report is required.")

    output = BytesIO()

    with ZipFile(
        output,
        mode="w",
        compression=ZIP_DEFLATED,
    ) as archive:
        used_names: set[str] = set()

        for item in reports:
            pdf_bytes = generate_report_pdf_bytes(item.report)

            filename = build_report_pdf_filename(item.report)

            # Ensure filenames remain unique within the archive.
            if filename in used_names:
                stem, extension = filename.rsplit(".", 1)

                index = 2
                candidate = f"{stem}_{index}.{extension}"

                while candidate in used_names:
                    index += 1
                    candidate = f"{stem}_{index}.{extension}"

                filename = candidate

            used_names.add(filename)

            archive.writestr(filename, pdf_bytes)

    return output.getvalue()
