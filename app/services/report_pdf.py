from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, datetime
from io import BytesIO
from typing import Iterable

try:
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.pdfbase.pdfmetrics import stringWidth
    from reportlab.platypus import (
        BaseDocTemplate,
        Frame,
        KeepTogether,
        PageTemplate,
        Paragraph,
        Spacer,
        Table,
        TableStyle,
    )
except ImportError as exc:  # pragma: no cover - depends on deployment environment
    raise RuntimeError(
        "PDF generation requires ReportLab. Install it with "
        "'python -m pip install reportlab'."
    ) from exc


_SAFE_FILENAME_PATTERN = re.compile(r"[^A-Za-z0-9._-]+")
_WHITESPACE_PATTERN = re.compile(r"\s+")


@dataclass(frozen=True, slots=True)
class ReportPdfField:
    """A labelled field displayed in the summary section of a report PDF."""

    label: str
    value: str | int | float | None


@dataclass(frozen=True, slots=True)
class ReportPdfSection:
    """A titled free-text section displayed in the report PDF."""

    title: str
    content: str


@dataclass(frozen=True, slots=True)
class ReportPdfData:
    """
    Structured data used to generate a single pupil report PDF.

    This object deliberately contains no SQLAlchemy model dependencies. API
    endpoints or repositories should map database records into this structure.
    """

    school_name: str
    student_name: str
    report_title: str
    academic_year: str | None = None
    term: str | None = None
    year_group: str | None = None
    subject: str | None = None
    teacher_name: str | None = None
    grade: str | None = None
    report_text: str | None = None
    published_at: date | datetime | None = None
    fields: tuple[ReportPdfField, ...] = field(default_factory=tuple)
    sections: tuple[ReportPdfSection, ...] = field(default_factory=tuple)
    footer_text: str | None = None


class _ReportDocumentTemplate(BaseDocTemplate):
    """ReportLab document template with a consistent header and footer."""

    def __init__(
        self,
        buffer: BytesIO,
        *,
        title: str,
        school_name: str,
        footer_text: str | None,
    ) -> None:
        super().__init__(
            buffer,
            pagesize=A4,
            rightMargin=18 * mm,
            leftMargin=18 * mm,
            topMargin=28 * mm,
            bottomMargin=22 * mm,
            title=title,
            author=school_name,
            subject="Student report",
        )

        self.school_name = school_name
        self.footer_text = footer_text

        frame = Frame(
            self.leftMargin,
            self.bottomMargin,
            self.width,
            self.height,
            id="report-frame",
        )

        self.addPageTemplates(
            [
                PageTemplate(
                    id="report-page",
                    frames=[frame],
                    onPage=self._draw_header_and_footer,
                ),
            ],
        )

    def _draw_header_and_footer(self, canvas, document) -> None:  # type: ignore[no-untyped-def]
        canvas.saveState()

        page_width, page_height = A4

        canvas.setStrokeColor(colors.HexColor("#D9DEE8"))
        canvas.setLineWidth(0.6)
        canvas.line(
            self.leftMargin,
            page_height - 20 * mm,
            page_width - self.rightMargin,
            page_height - 20 * mm,
        )

        canvas.setFillColor(colors.HexColor("#0E1433"))
        canvas.setFont("Helvetica-Bold", 10)
        canvas.drawString(
            self.leftMargin,
            page_height - 15.5 * mm,
            _truncate_canvas_text(
                self.school_name,
                max_width=self.width,
                font_name="Helvetica-Bold",
                font_size=10,
            ),
        )

        canvas.setStrokeColor(colors.HexColor("#D9DEE8"))
        canvas.line(
            self.leftMargin,
            16 * mm,
            page_width - self.rightMargin,
            16 * mm,
        )

        canvas.setFillColor(colors.HexColor("#555B66"))
        canvas.setFont("Helvetica", 8)

        if self.footer_text:
            canvas.drawString(
                self.leftMargin,
                11 * mm,
                _truncate_canvas_text(
                    self.footer_text,
                    max_width=self.width - 28 * mm,
                    font_name="Helvetica",
                    font_size=8,
                ),
            )

        page_label = f"Page {document.page}"
        canvas.drawRightString(
            page_width - self.rightMargin,
            11 * mm,
            page_label,
        )

        canvas.restoreState()


def _clean_text(value: object | None) -> str:
    if value is None:
        return ""

    return _WHITESPACE_PATTERN.sub(" ", str(value).strip())


def _normalise_multiline_text(value: str | None) -> str:
    if not value:
        return ""

    paragraphs = [
        _WHITESPACE_PATTERN.sub(" ", paragraph.strip())
        for paragraph in re.split(r"\n\s*\n", value.strip())
        if paragraph.strip()
    ]

    return "\n\n".join(paragraphs)


def _format_date(value: date | datetime | None) -> str:
    if value is None:
        return ""

    return value.strftime("%d %B %Y")


def _safe_filename_component(value: str, *, fallback: str) -> str:
    cleaned = _SAFE_FILENAME_PATTERN.sub("-", _clean_text(value))
    cleaned = cleaned.strip("._-")

    return cleaned or fallback


def build_report_pdf_filename(data: ReportPdfData) -> str:
    """Return a safe, predictable filename for a generated report PDF."""

    student = _safe_filename_component(data.student_name, fallback="student")
    title = _safe_filename_component(data.report_title, fallback="report")
    year = _safe_filename_component(data.academic_year or "", fallback="")

    parts = [student, title]

    if year:
        parts.append(year)

    return "_".join(parts) + ".pdf"


def _truncate_canvas_text(
    text: str,
    *,
    max_width: float,
    font_name: str,
    font_size: float,
) -> str:
    cleaned = _clean_text(text)

    if stringWidth(cleaned, font_name, font_size) <= max_width:
        return cleaned

    ellipsis = "..."
    available_width = max_width - stringWidth(
        ellipsis,
        font_name,
        font_size,
    )

    if available_width <= 0:
        return ellipsis

    output: list[str] = []

    for character in cleaned:
        candidate = "".join(output) + character

        if stringWidth(candidate, font_name, font_size) > available_width:
            break

        output.append(character)

    return "".join(output).rstrip() + ellipsis


def _build_styles() -> dict[str, ParagraphStyle]:
    styles = getSampleStyleSheet()

    return {
        "title": ParagraphStyle(
            "ReportTitle",
            parent=styles["Title"],
            fontName="Helvetica-Bold",
            fontSize=18,
            leading=22,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#0E1433"),
            spaceAfter=5 * mm,
        ),
        "student": ParagraphStyle(
            "StudentName",
            parent=styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=14,
            leading=18,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#20263D"),
            spaceAfter=6 * mm,
        ),
        "section": ParagraphStyle(
            "SectionHeading",
            parent=styles["Heading3"],
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=14,
            textColor=colors.HexColor("#0E1433"),
            spaceBefore=4 * mm,
            spaceAfter=2.5 * mm,
        ),
        "body": ParagraphStyle(
            "ReportBody",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=10.5,
            leading=15,
            alignment=TA_LEFT,
            textColor=colors.HexColor("#202124"),
            spaceAfter=3 * mm,
        ),
        "label": ParagraphStyle(
            "SummaryLabel",
            parent=styles["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=9.5,
            leading=12,
            textColor=colors.HexColor("#0E1433"),
        ),
        "value": ParagraphStyle(
            "SummaryValue",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=9.5,
            leading=12,
            textColor=colors.HexColor("#202124"),
        ),
        "empty": ParagraphStyle(
            "EmptyText",
            parent=styles["BodyText"],
            fontName="Helvetica-Oblique",
            fontSize=9.5,
            leading=13,
            textColor=colors.HexColor("#6B7280"),
        ),
    }


def _paragraphs_from_text(
    text: str,
    *,
    style: ParagraphStyle,
) -> list[Paragraph]:
    normalised = _normalise_multiline_text(text)

    if not normalised:
        return []

    return [Paragraph(paragraph, style) for paragraph in normalised.split("\n\n")]


def _build_summary_rows(
    data: ReportPdfData,
    styles: dict[str, ParagraphStyle],
) -> list[list[Paragraph]]:
    rows: list[tuple[str, object | None]] = [
        ("Academic year", data.academic_year),
        ("Term", data.term),
        ("Year group", data.year_group),
        ("Subject", data.subject),
        ("Teacher", data.teacher_name),
        ("Grade", data.grade),
        ("Published", _format_date(data.published_at)),
    ]

    rows.extend((field.label, field.value) for field in data.fields)

    output: list[list[Paragraph]] = []

    for label, value in rows:
        clean_label = _clean_text(label)
        clean_value = _clean_text(value)

        if not clean_label or not clean_value:
            continue

        output.append(
            [
                Paragraph(clean_label, styles["label"]),
                Paragraph(clean_value, styles["value"]),
            ],
        )

    return output


def _build_summary_table(
    rows: list[list[Paragraph]],
) -> Table | None:
    if not rows:
        return None

    table = Table(
        rows,
        colWidths=[47 * mm, 109 * mm],
        hAlign="LEFT",
        repeatRows=0,
    )

    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#F2F4F8")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#D9DEE8")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 7),
                ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ],
        ),
    )

    return table


def _iter_sections(data: ReportPdfData) -> Iterable[ReportPdfSection]:
    report_text = _normalise_multiline_text(data.report_text)

    if report_text:
        yield ReportPdfSection(
            title="Teacher Report",
            content=report_text,
        )

    for section in data.sections:
        title = _clean_text(section.title)
        content = _normalise_multiline_text(section.content)

        if title and content:
            yield ReportPdfSection(title=title, content=content)


def generate_report_pdf_bytes(data: ReportPdfData) -> bytes:
    """
    Generate a complete pupil report PDF and return its bytes.

    Raises:
        ValueError: If required report identity fields are missing.
        RuntimeError: If ReportLab cannot build the document.
    """

    school_name = _clean_text(data.school_name)
    student_name = _clean_text(data.student_name)
    report_title = _clean_text(data.report_title)

    missing_fields = [
        field_name
        for field_name, value in (
            ("school_name", school_name),
            ("student_name", student_name),
            ("report_title", report_title),
        )
        if not value
    ]

    if missing_fields:
        raise ValueError(
            "Missing required PDF report fields: " + ", ".join(missing_fields) + "."
        )

    buffer = BytesIO()
    styles = _build_styles()

    document = _ReportDocumentTemplate(
        buffer,
        title=report_title,
        school_name=school_name,
        footer_text=_clean_text(data.footer_text) or None,
    )

    story: list[object] = [
        Paragraph(report_title, styles["title"]),
        Paragraph(student_name, styles["student"]),
    ]

    summary_rows = _build_summary_rows(data, styles)
    summary_table = _build_summary_table(summary_rows)

    if summary_table is not None:
        story.extend(
            [
                KeepTogether(
                    [
                        Paragraph("Report Details", styles["section"]),
                        summary_table,
                    ],
                ),
                Spacer(1, 4 * mm),
            ],
        )

    sections = list(_iter_sections(data))

    if sections:
        for section in sections:
            section_flowables: list[object] = [
                Paragraph(section.title, styles["section"]),
            ]
            section_flowables.extend(
                _paragraphs_from_text(
                    section.content,
                    style=styles["body"],
                ),
            )
            story.extend(section_flowables)
    else:
        story.extend(
            [
                Paragraph("Teacher Report", styles["section"]),
                Paragraph(
                    "No report content is available.",
                    styles["empty"],
                ),
            ],
        )

    try:
        document.build(story)
    except Exception as exc:
        raise RuntimeError("Unable to generate the report PDF.") from exc

    pdf_bytes = buffer.getvalue()
    buffer.close()

    if not pdf_bytes.startswith(b"%PDF"):
        raise RuntimeError("The generated report is not a valid PDF document.")

    return pdf_bytes
