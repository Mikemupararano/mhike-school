from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from datetime import date, datetime
from html import escape
from io import BytesIO
from pathlib import Path
from typing import Iterable, Sequence

try:
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.pdfbase.pdfmetrics import stringWidth
    from reportlab.platypus import (
        BaseDocTemplate,
        Flowable,
        Frame,
        Image,
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


logger = logging.getLogger(__name__)

_SAFE_FILENAME_PATTERN = re.compile(r"[^A-Za-z0-9._-]+")
_WHITESPACE_PATTERN = re.compile(r"\s+")
_PARAGRAPH_SPLIT_PATTERN = re.compile(r"\n\s*\n")
_HEX_COLOUR_PATTERN = re.compile(r"^#[0-9A-Fa-f]{6}$")

_DEFAULT_PRIMARY_COLOUR = "#0E1433"
_DEFAULT_ACCENT_COLOUR = "#E8ECF5"
_DEFAULT_BORDER_COLOUR = "#D9DEE8"
_DEFAULT_TEXT_COLOUR = "#202124"
_DEFAULT_MUTED_TEXT_COLOUR = "#555B66"
_DEFAULT_EMPTY_TEXT_COLOUR = "#6B7280"

_MAX_LOGO_WIDTH = 32 * mm
_MAX_LOGO_HEIGHT = 14 * mm
_MAX_GRADE_CARD_COLUMNS = 4


@dataclass(frozen=True, slots=True)
class ReportPdfField:
    """A labelled field displayed in the report-details table."""

    label: str
    value: str | int | float | None


@dataclass(frozen=True, slots=True)
class ReportPdfSection:
    """A titled free-text section displayed in the report PDF."""

    title: str
    content: str


@dataclass(frozen=True, slots=True)
class ReportPdfGrade:
    """A prominent grade or metric displayed in the grade-card section."""

    label: str
    value: str | int | float | None


@dataclass(frozen=True, slots=True)
class ReportPdfData:
    """
    Structured data used to generate one pupil report PDF.

    The DTO deliberately has no SQLAlchemy dependencies. Endpoints, repositories,
    or mapping services should convert database records into this structure.
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

    # Optional presentation and branding data.
    school_logo_path: str | None = None
    school_address: str | None = None
    school_phone: str | None = None
    school_email: str | None = None
    school_website: str | None = None
    student_reference: str | None = None
    grades: tuple[ReportPdfGrade, ...] = field(default_factory=tuple)
    watermark_text: str | None = None
    confidentiality_text: str | None = "Confidential"
    generated_at: date | datetime | None = None

    # Optional theme overrides. Invalid values safely fall back to defaults.
    primary_colour: str = _DEFAULT_PRIMARY_COLOUR
    accent_colour: str = _DEFAULT_ACCENT_COLOUR


class _ReportDocumentTemplate(BaseDocTemplate):
    """ReportLab document template with consistent branding on every page."""

    def __init__(
        self,
        buffer: BytesIO,
        *,
        title: str,
        school_name: str,
        footer_text: str | None,
        school_logo_path: str | None,
        school_contact_line: str | None,
        watermark_text: str | None,
        confidentiality_text: str | None,
        primary_colour: colors.Color,
    ) -> None:
        super().__init__(
            buffer,
            pagesize=A4,
            rightMargin=18 * mm,
            leftMargin=18 * mm,
            topMargin=31 * mm,
            bottomMargin=23 * mm,
            title=title,
            author=school_name,
            subject="Student report",
            creator="MHike School",
            keywords="student report, school report",
        )

        self.school_name = school_name
        self.footer_text = footer_text
        self.school_logo_path = school_logo_path
        self.school_contact_line = school_contact_line
        self.watermark_text = watermark_text
        self.confidentiality_text = confidentiality_text
        self.primary_colour = primary_colour

        frame = Frame(
            self.leftMargin,
            self.bottomMargin,
            self.width,
            self.height,
            id="report-frame",
            showBoundary=0,
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
        header_line_y = page_height - 22 * mm

        if self.watermark_text:
            self._draw_watermark(canvas, page_width, page_height)

        logo_drawn = self._draw_logo(canvas, page_height)

        school_name_x = self.leftMargin
        school_name_max_width = self.width

        if logo_drawn:
            school_name_x += _MAX_LOGO_WIDTH + 5 * mm
            school_name_max_width -= _MAX_LOGO_WIDTH + 5 * mm

        canvas.setFillColor(self.primary_colour)
        canvas.setFont("Helvetica-Bold", 10.5)
        canvas.drawString(
            school_name_x,
            page_height - 14.5 * mm,
            _truncate_canvas_text(
                self.school_name,
                max_width=school_name_max_width,
                font_name="Helvetica-Bold",
                font_size=10.5,
            ),
        )

        if self.school_contact_line:
            canvas.setFillColor(colors.HexColor(_DEFAULT_MUTED_TEXT_COLOUR))
            canvas.setFont("Helvetica", 7.5)
            canvas.drawString(
                school_name_x,
                page_height - 18.5 * mm,
                _truncate_canvas_text(
                    self.school_contact_line,
                    max_width=school_name_max_width,
                    font_name="Helvetica",
                    font_size=7.5,
                ),
            )

        canvas.setStrokeColor(colors.HexColor(_DEFAULT_BORDER_COLOUR))
        canvas.setLineWidth(0.6)
        canvas.line(
            self.leftMargin,
            header_line_y,
            page_width - self.rightMargin,
            header_line_y,
        )

        canvas.line(
            self.leftMargin,
            16 * mm,
            page_width - self.rightMargin,
            16 * mm,
        )

        canvas.setFillColor(colors.HexColor(_DEFAULT_MUTED_TEXT_COLOUR))
        canvas.setFont("Helvetica", 8)

        left_footer = self.footer_text or self.confidentiality_text
        if left_footer:
            canvas.drawString(
                self.leftMargin,
                11 * mm,
                _truncate_canvas_text(
                    left_footer,
                    max_width=self.width - 33 * mm,
                    font_name="Helvetica",
                    font_size=8,
                ),
            )

        canvas.drawRightString(
            page_width - self.rightMargin,
            11 * mm,
            f"Page {document.page}",
        )

        canvas.restoreState()

    def _draw_logo(self, canvas, page_height: float) -> bool:  # type: ignore[no-untyped-def]
        logo_path = _resolve_existing_file(self.school_logo_path)
        if logo_path is None:
            return False

        try:
            from reportlab.lib.utils import ImageReader

            reader = ImageReader(str(logo_path))
            image_width, image_height = reader.getSize()

            if image_width <= 0 or image_height <= 0:
                return False

            scale = min(
                _MAX_LOGO_WIDTH / image_width,
                _MAX_LOGO_HEIGHT / image_height,
            )
            draw_width = image_width * scale
            draw_height = image_height * scale

            canvas.drawImage(
                reader,
                self.leftMargin,
                page_height - 9 * mm - draw_height,
                width=draw_width,
                height=draw_height,
                preserveAspectRatio=True,
                mask="auto",
            )
            return True
        except Exception:
            logger.warning(
                "Unable to render report PDF school logo: %s",
                logo_path,
                exc_info=True,
            )
            return False

    def _draw_watermark(
        self,
        canvas,  # type: ignore[no-untyped-def]
        page_width: float,
        page_height: float,
    ) -> None:
        watermark = _clean_text(self.watermark_text)
        if not watermark:
            return

        canvas.saveState()
        canvas.translate(page_width / 2, page_height / 2)
        canvas.rotate(38)
        canvas.setFillColor(colors.Color(0.82, 0.84, 0.88, alpha=0.22))
        canvas.setFont("Helvetica-Bold", 46)
        canvas.drawCentredString(
            0,
            0,
            _truncate_canvas_text(
                watermark.upper(),
                max_width=page_width * 0.74,
                font_name="Helvetica-Bold",
                font_size=46,
            ),
        )
        canvas.restoreState()


def _clean_text(value: object | None) -> str:
    if value is None:
        return ""

    return _WHITESPACE_PATTERN.sub(" ", str(value).strip())


def _xml_text(value: object | None) -> str:
    """Return cleaned, XML-safe text for ReportLab Paragraph content."""

    return escape(_clean_text(value), quote=False)


def _normalise_multiline_text(value: str | None) -> str:
    if not value:
        return ""

    paragraphs = [
        _WHITESPACE_PATTERN.sub(" ", paragraph.strip())
        for paragraph in _PARAGRAPH_SPLIT_PATTERN.split(value.strip())
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


def _normalise_colour(value: str, *, fallback: str) -> colors.Color:
    candidate = _clean_text(value)

    if not _HEX_COLOUR_PATTERN.fullmatch(candidate):
        candidate = fallback

    return colors.HexColor(candidate)


def _resolve_existing_file(value: str | None) -> Path | None:
    path_text = _clean_text(value)
    if not path_text:
        return None

    try:
        path = Path(path_text).expanduser().resolve(strict=False)
    except (OSError, RuntimeError):
        return None

    if not path.is_file():
        return None

    return path


def _build_school_contact_line(data: ReportPdfData) -> str | None:
    parts = [
        _clean_text(data.school_address),
        _clean_text(data.school_phone),
        _clean_text(data.school_email),
        _clean_text(data.school_website),
    ]
    return " | ".join(part for part in parts if part) or None


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

    if not cleaned:
        return ""

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


def _build_styles(
    *,
    primary_colour: colors.Color,
) -> dict[str, ParagraphStyle]:
    styles = getSampleStyleSheet()

    return {
        "title": ParagraphStyle(
            "ReportTitle",
            parent=styles["Title"],
            fontName="Helvetica-Bold",
            fontSize=18,
            leading=22,
            alignment=TA_CENTER,
            textColor=primary_colour,
            spaceAfter=4 * mm,
        ),
        "student": ParagraphStyle(
            "StudentName",
            parent=styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=14,
            leading=18,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#20263D"),
            spaceAfter=1.5 * mm,
        ),
        "student_reference": ParagraphStyle(
            "StudentReference",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=8.5,
            leading=11,
            alignment=TA_CENTER,
            textColor=colors.HexColor(_DEFAULT_MUTED_TEXT_COLOUR),
            spaceAfter=5 * mm,
        ),
        "section": ParagraphStyle(
            "SectionHeading",
            parent=styles["Heading3"],
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=14,
            textColor=primary_colour,
            spaceBefore=4 * mm,
            spaceAfter=2.5 * mm,
            keepWithNext=True,
        ),
        "body": ParagraphStyle(
            "ReportBody",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=10.5,
            leading=15,
            alignment=TA_LEFT,
            textColor=colors.HexColor(_DEFAULT_TEXT_COLOUR),
            spaceAfter=3 * mm,
            allowWidows=0,
            allowOrphans=0,
        ),
        "label": ParagraphStyle(
            "SummaryLabel",
            parent=styles["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=9.5,
            leading=12,
            textColor=primary_colour,
        ),
        "value": ParagraphStyle(
            "SummaryValue",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=9.5,
            leading=12,
            textColor=colors.HexColor(_DEFAULT_TEXT_COLOUR),
        ),
        "grade_label": ParagraphStyle(
            "GradeCardLabel",
            parent=styles["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=10,
            alignment=TA_CENTER,
            textColor=colors.HexColor(_DEFAULT_MUTED_TEXT_COLOUR),
            spaceAfter=1.5 * mm,
        ),
        "grade_value": ParagraphStyle(
            "GradeCardValue",
            parent=styles["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=15,
            leading=18,
            alignment=TA_CENTER,
            textColor=primary_colour,
        ),
        "empty": ParagraphStyle(
            "EmptyText",
            parent=styles["BodyText"],
            fontName="Helvetica-Oblique",
            fontSize=9.5,
            leading=13,
            textColor=colors.HexColor(_DEFAULT_EMPTY_TEXT_COLOUR),
        ),
        "generated": ParagraphStyle(
            "GeneratedText",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=7.5,
            leading=10,
            alignment=TA_LEFT,
            textColor=colors.HexColor(_DEFAULT_EMPTY_TEXT_COLOUR),
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

    return [
        Paragraph(escape(paragraph, quote=False), style)
        for paragraph in normalised.split("\n\n")
    ]


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
                Paragraph(_xml_text(clean_label), styles["label"]),
                Paragraph(_xml_text(clean_value), styles["value"]),
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
        splitByRow=1,
    )

    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#F2F4F8")),
                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.5,
                    colors.HexColor(_DEFAULT_BORDER_COLOUR),
                ),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 7),
                ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ],
        ),
    )

    return table


def _effective_grades(data: ReportPdfData) -> tuple[ReportPdfGrade, ...]:
    explicit_grades = tuple(
        grade
        for grade in data.grades
        if _clean_text(grade.label) and _clean_text(grade.value)
    )
    if explicit_grades:
        return explicit_grades

    if _clean_text(data.grade):
        return (ReportPdfGrade(label="Grade", value=data.grade),)

    return ()


def _chunked(
    values: Sequence[ReportPdfGrade],
    size: int,
) -> Iterable[Sequence[ReportPdfGrade]]:
    for index in range(0, len(values), size):
        yield values[index : index + size]


def _build_grade_card(
    grades: tuple[ReportPdfGrade, ...],
    *,
    styles: dict[str, ParagraphStyle],
    accent_colour: colors.Color,
) -> Table | None:
    if not grades:
        return None

    table_rows: list[list[Table]] = []

    for grade_group in _chunked(grades, _MAX_GRADE_CARD_COLUMNS):
        cards: list[Table] = []

        for grade in grade_group:
            card = Table(
                [
                    [Paragraph(_xml_text(grade.label), styles["grade_label"])],
                    [Paragraph(_xml_text(grade.value), styles["grade_value"])],
                ],
                colWidths=[37.5 * mm],
                rowHeights=[8 * mm, 13 * mm],
            )
            card.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, -1), accent_colour),
                        (
                            "BOX",
                            (0, 0),
                            (-1, -1),
                            0.7,
                            colors.HexColor(_DEFAULT_BORDER_COLOUR),
                        ),
                        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                        ("LEFTPADDING", (0, 0), (-1, -1), 4),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                        ("TOPPADDING", (0, 0), (-1, -1), 3),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                    ],
                ),
            )
            cards.append(card)

        while len(cards) < _MAX_GRADE_CARD_COLUMNS:
            cards.append(
                Table(
                    [[""]],
                    colWidths=[37.5 * mm],
                    rowHeights=[21 * mm],
                    style=TableStyle([("BOX", (0, 0), (-1, -1), 0, colors.white)]),
                )
            )

        table_rows.append(cards)

    outer = Table(
        table_rows,
        colWidths=[39 * mm] * _MAX_GRADE_CARD_COLUMNS,
        hAlign="LEFT",
    )
    outer.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 1.5 * mm),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2 * mm),
            ],
        )
    )
    return outer


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


def _append_section(
    story: list[Flowable],
    *,
    section: ReportPdfSection,
    styles: dict[str, ParagraphStyle],
) -> None:
    heading = Paragraph(_xml_text(section.title), styles["section"])
    paragraphs = _paragraphs_from_text(section.content, style=styles["body"])

    if not paragraphs:
        return

    # Keep the heading with the first paragraph, but allow long sections to flow
    # naturally across pages.
    story.append(KeepTogether([heading, paragraphs[0]]))
    story.extend(paragraphs[1:])


def _validate_required_identity(data: ReportPdfData) -> tuple[str, str, str]:
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

    return school_name, student_name, report_title


def generate_report_pdf_bytes(data: ReportPdfData) -> bytes:
    """
    Generate a complete pupil report PDF and return the resulting bytes.

    Raises:
        ValueError: If required identity fields are missing.
        RuntimeError: If ReportLab cannot build a valid PDF.
    """

    school_name, student_name, report_title = _validate_required_identity(data)

    primary_colour = _normalise_colour(
        data.primary_colour,
        fallback=_DEFAULT_PRIMARY_COLOUR,
    )
    accent_colour = _normalise_colour(
        data.accent_colour,
        fallback=_DEFAULT_ACCENT_COLOUR,
    )

    buffer = BytesIO()
    styles = _build_styles(primary_colour=primary_colour)

    document = _ReportDocumentTemplate(
        buffer,
        title=report_title,
        school_name=school_name,
        footer_text=_clean_text(data.footer_text) or None,
        school_logo_path=data.school_logo_path,
        school_contact_line=_build_school_contact_line(data),
        watermark_text=_clean_text(data.watermark_text) or None,
        confidentiality_text=_clean_text(data.confidentiality_text) or None,
        primary_colour=primary_colour,
    )

    story: list[Flowable] = [
        Paragraph(_xml_text(report_title), styles["title"]),
        Paragraph(_xml_text(student_name), styles["student"]),
    ]

    if _clean_text(data.student_reference):
        story.append(
            Paragraph(
                f"Student reference: {_xml_text(data.student_reference)}",
                styles["student_reference"],
            )
        )
    else:
        story.append(Spacer(1, 3.5 * mm))

    grade_card = _build_grade_card(
        _effective_grades(data),
        styles=styles,
        accent_colour=accent_colour,
    )
    if grade_card is not None:
        story.extend(
            [
                Paragraph("Grades and attainment", styles["section"]),
                grade_card,
                Spacer(1, 1.5 * mm),
            ]
        )

    summary_rows = _build_summary_rows(data, styles)
    summary_table = _build_summary_table(summary_rows)

    if summary_table is not None:
        story.extend(
            [
                KeepTogether(
                    [
                        Paragraph("Report Details", styles["section"]),
                        summary_table,
                    ]
                ),
                Spacer(1, 4 * mm),
            ]
        )

    sections = list(_iter_sections(data))

    if sections:
        for section in sections:
            _append_section(story, section=section, styles=styles)
    else:
        story.extend(
            [
                Paragraph("Teacher Report", styles["section"]),
                Paragraph(
                    "No report content is available.",
                    styles["empty"],
                ),
            ]
        )

    generated_at = data.generated_at
    if generated_at is not None:
        story.extend(
            [
                Spacer(1, 5 * mm),
                Paragraph(
                    f"Generated on {_xml_text(_format_date(generated_at))}.",
                    styles["generated"],
                ),
            ]
        )

    try:
        document.build(story)
        pdf_bytes = buffer.getvalue()
    except Exception as exc:
        logger.exception(
            "Unable to generate report PDF for student=%r title=%r.",
            student_name,
            report_title,
        )
        raise RuntimeError("Unable to generate the report PDF.") from exc
    finally:
        buffer.close()

    if not pdf_bytes.startswith(b"%PDF"):
        raise RuntimeError("The generated report is not a valid PDF document.")

    if len(pdf_bytes) < 100:
        raise RuntimeError("The generated report PDF is unexpectedly empty.")

    return pdf_bytes
