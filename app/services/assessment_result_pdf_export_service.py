from __future__ import annotations

import re
from io import BytesIO

try:
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import (
        BaseDocTemplate,
        Frame,
        PageTemplate,
        Paragraph,
        Spacer,
        Table,
        TableStyle,
    )
except ImportError as exc:  # pragma: no cover - deployment dependency
    raise RuntimeError(
        "PDF generation requires ReportLab. Install it with "
        "'python -m pip install reportlab'."
    ) from exc

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.school import School
from app.models.user import User
from app.services.assessment_result_export_service import (
    OfficialAssessmentResultExport,
    OfficialAssessmentResultExportRow,
    get_official_assessment_result_export,
)

_SAFE_FILENAME_PATTERN = re.compile(
    r"[^A-Za-z0-9._-]+",
)

_DEFAULT_PRIMARY_COLOUR = "#0E1433"
_DEFAULT_ACCENT_COLOUR = "#E8ECF5"
_DEFAULT_BORDER_COLOUR = "#D9DEE8"
_DEFAULT_TEXT_COLOUR = "#202124"
_DEFAULT_MUTED_TEXT_COLOUR = "#555B66"

_MIN_VALID_PDF_SIZE = 100


# ---------------------------------------------------------------------------
# Filename
# ---------------------------------------------------------------------------


def _clean_filename_component(
    value: str,
    *,
    fallback: str,
) -> str:
    cleaned = _SAFE_FILENAME_PATTERN.sub(
        "-",
        str(
            value,
        ).strip(),
    )

    cleaned = cleaned.strip(
        "._-",
    )

    return cleaned or fallback


def build_official_assessment_results_pdf_filename(
    export: OfficialAssessmentResultExport,
) -> str:
    """
    Build a safe filename for the official assessment-results PDF.
    """

    title = _clean_filename_component(
        export.assessment_title,
        fallback="assessment",
    )

    return f"assessment_{export.assessment_id}_" f"{title}_official_results.pdf"


# ---------------------------------------------------------------------------
# School lookup
# ---------------------------------------------------------------------------


async def _get_school_name(
    db: AsyncSession,
    *,
    school_id: int,
) -> str:
    """
    Return the owning school's name.

    The current School model contains only the school's identity/name and
    audit metadata, so no contact or logo details are inferred here.
    """

    result = await db.execute(
        select(
            School.name,
        ).where(
            School.id == school_id,
        ),
    )

    school_name = result.scalar_one_or_none()

    if school_name is None:
        raise RuntimeError(
            (
                "Official assessment export references "
                f"school {school_id}, but the school could not be loaded."
            )
        )

    cleaned = str(
        school_name,
    ).strip()

    if not cleaned:
        raise RuntimeError(
            ("Official assessment export references a school " "without a usable name.")
        )

    return cleaned


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------


def _text(
    value,
) -> str:
    if value is None:
        return ""

    enum_value = getattr(
        value,
        "value",
        None,
    )

    if enum_value is not None:
        return str(
            enum_value,
        )

    return str(
        value,
    )


def _display_decimal(
    value,
) -> str:
    if value is None:
        return "-"

    return str(
        value,
    )


def _display_boolean(
    value: bool | None,
) -> str:
    if value is True:
        return "Yes"

    if value is False:
        return "No"

    return "-"


def _display_grade(
    row: OfficialAssessmentResultExportRow,
) -> str:
    if row.grade_label:
        return row.grade_label

    return "-"


# ---------------------------------------------------------------------------
# Styles
# ---------------------------------------------------------------------------


def _build_styles():
    styles = getSampleStyleSheet()

    primary = colors.HexColor(
        _DEFAULT_PRIMARY_COLOUR,
    )

    return {
        "title": ParagraphStyle(
            "AssessmentResultTitle",
            parent=styles["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=18,
            leading=21,
            textColor=primary,
            alignment=TA_LEFT,
            spaceAfter=4 * mm,
        ),
        "subtitle": ParagraphStyle(
            "AssessmentResultSubtitle",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=9,
            leading=12,
            textColor=colors.HexColor(
                _DEFAULT_MUTED_TEXT_COLOUR,
            ),
            alignment=TA_LEFT,
        ),
        "summary_label": ParagraphStyle(
            "AssessmentResultSummaryLabel",
            parent=styles["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=10,
            textColor=colors.HexColor(
                _DEFAULT_TEXT_COLOUR,
            ),
        ),
        "summary_value": ParagraphStyle(
            "AssessmentResultSummaryValue",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=8,
            leading=10,
            textColor=colors.HexColor(
                _DEFAULT_TEXT_COLOUR,
            ),
        ),
        "table_header": ParagraphStyle(
            "AssessmentResultTableHeader",
            parent=styles["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=7,
            leading=8.5,
            textColor=colors.white,
            alignment=TA_CENTER,
        ),
        "table_text": ParagraphStyle(
            "AssessmentResultTableText",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=7,
            leading=8.5,
            textColor=colors.HexColor(
                _DEFAULT_TEXT_COLOUR,
            ),
            alignment=TA_LEFT,
        ),
        "table_center": ParagraphStyle(
            "AssessmentResultTableCenter",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=7,
            leading=8.5,
            textColor=colors.HexColor(
                _DEFAULT_TEXT_COLOUR,
            ),
            alignment=TA_CENTER,
        ),
        "table_number": ParagraphStyle(
            "AssessmentResultTableNumber",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=7,
            leading=8.5,
            textColor=colors.HexColor(
                _DEFAULT_TEXT_COLOUR,
            ),
            alignment=TA_RIGHT,
        ),
        "empty": ParagraphStyle(
            "AssessmentResultEmpty",
            parent=styles["BodyText"],
            fontName="Helvetica-Oblique",
            fontSize=9,
            leading=12,
            textColor=colors.HexColor(
                _DEFAULT_MUTED_TEXT_COLOUR,
            ),
        ),
    }


# ---------------------------------------------------------------------------
# Document template
# ---------------------------------------------------------------------------


class _AssessmentResultsDocumentTemplate(
    BaseDocTemplate,
):
    """
    Landscape A4 assessment-results document with consistent page furniture.
    """

    def __init__(
        self,
        buffer: BytesIO,
        *,
        title: str,
        school_name: str,
    ) -> None:
        page_size = landscape(
            A4,
        )

        super().__init__(
            buffer,
            pagesize=page_size,
            leftMargin=12 * mm,
            rightMargin=12 * mm,
            topMargin=24 * mm,
            bottomMargin=18 * mm,
            title=title,
            author=school_name,
            subject="Official assessment results",
            creator="MHike School",
            keywords=("assessment results, official results, school assessment"),
        )

        self.school_name = school_name

        frame = Frame(
            self.leftMargin,
            self.bottomMargin,
            self.width,
            self.height,
            id="assessment-results-frame",
            showBoundary=0,
        )

        self.addPageTemplates(
            [
                PageTemplate(
                    id="assessment-results-page",
                    frames=[
                        frame,
                    ],
                    onPage=self._draw_header_footer,
                ),
            ],
        )

    def _draw_header_footer(
        self,
        canvas,
        document,
    ) -> None:
        canvas.saveState()

        page_width, page_height = landscape(
            A4,
        )

        canvas.setFillColor(
            colors.HexColor(
                _DEFAULT_PRIMARY_COLOUR,
            ),
        )

        canvas.setFont(
            "Helvetica-Bold",
            10,
        )

        canvas.drawString(
            self.leftMargin,
            page_height - 13 * mm,
            self.school_name,
        )

        canvas.setStrokeColor(
            colors.HexColor(
                _DEFAULT_BORDER_COLOUR,
            ),
        )

        canvas.setLineWidth(
            0.6,
        )

        canvas.line(
            self.leftMargin,
            page_height - 17 * mm,
            page_width - self.rightMargin,
            page_height - 17 * mm,
        )

        canvas.line(
            self.leftMargin,
            12 * mm,
            page_width - self.rightMargin,
            12 * mm,
        )

        canvas.setFillColor(
            colors.HexColor(
                _DEFAULT_MUTED_TEXT_COLOUR,
            ),
        )

        canvas.setFont(
            "Helvetica",
            7.5,
        )

        canvas.drawString(
            self.leftMargin,
            7.5 * mm,
            "Confidential - Official assessment results",
        )

        canvas.drawRightString(
            page_width - self.rightMargin,
            7.5 * mm,
            f"Page {document.page}",
        )

        canvas.restoreState()


# ---------------------------------------------------------------------------
# PDF table
# ---------------------------------------------------------------------------


def _build_results_table(
    export: OfficialAssessmentResultExport,
    *,
    styles,
) -> Table | None:
    if not export.rows:
        return None

    header_labels = (
        "Candidate",
        "Student",
        "Script",
        "Outcome",
        "Type",
        "Mark",
        "Max",
        "%",
        "Grade",
        "Points",
        "Pass",
        "Effective",
    )

    table_data = [
        [
            Paragraph(
                label,
                styles["table_header"],
            )
            for label in header_labels
        ]
    ]

    for row in export.rows:
        table_data.append(
            [
                Paragraph(
                    row.candidate_number
                    or str(
                        row.candidate_id,
                    ),
                    styles["table_text"],
                ),
                Paragraph(
                    row.student_name
                    or row.student_email
                    or str(
                        row.student_id,
                    ),
                    styles["table_text"],
                ),
                Paragraph(
                    (f"{row.script_id} " f"(v{row.script_version})"),
                    styles["table_center"],
                ),
                Paragraph(
                    f"v{row.outcome_version}",
                    styles["table_center"],
                ),
                Paragraph(
                    _text(
                        row.change_type,
                    ),
                    styles["table_center"],
                ),
                Paragraph(
                    _display_decimal(
                        row.mark_awarded,
                    ),
                    styles["table_number"],
                ),
                Paragraph(
                    _display_decimal(
                        row.maximum_mark,
                    ),
                    styles["table_number"],
                ),
                Paragraph(
                    _display_decimal(
                        row.percentage,
                    ),
                    styles["table_number"],
                ),
                Paragraph(
                    _display_grade(
                        row,
                    ),
                    styles["table_center"],
                ),
                Paragraph(
                    _display_decimal(
                        row.grade_points,
                    ),
                    styles["table_number"],
                ),
                Paragraph(
                    _display_boolean(
                        row.is_pass,
                    ),
                    styles["table_center"],
                ),
                Paragraph(
                    row.effective_at.isoformat(
                        timespec="minutes",
                    ),
                    styles["table_text"],
                ),
            ]
        )

    table = Table(
        table_data,
        repeatRows=1,
        hAlign="LEFT",
        colWidths=[
            21 * mm,
            42 * mm,
            22 * mm,
            17 * mm,
            21 * mm,
            16 * mm,
            16 * mm,
            18 * mm,
            17 * mm,
            16 * mm,
            14 * mm,
            37 * mm,
        ],
    )

    table.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, 0),
                    colors.HexColor(
                        _DEFAULT_PRIMARY_COLOUR,
                    ),
                ),
                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.4,
                    colors.HexColor(
                        _DEFAULT_BORDER_COLOUR,
                    ),
                ),
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "TOP",
                ),
                (
                    "LEFTPADDING",
                    (0, 0),
                    (-1, -1),
                    4,
                ),
                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    4,
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    4,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    4,
                ),
                (
                    "ROWBACKGROUNDS",
                    (0, 1),
                    (-1, -1),
                    [
                        colors.white,
                        colors.HexColor(
                            "#F7F8FB",
                        ),
                    ],
                ),
            ]
        )
    )

    return table


# ---------------------------------------------------------------------------
# Renderer
# ---------------------------------------------------------------------------


def generate_official_assessment_results_pdf_bytes(
    export: OfficialAssessmentResultExport,
    *,
    school_name: str,
) -> bytes:
    """
    Render an official assessment-results cohort PDF.

    The supplied export must already contain only current authoritative
    AssessmentResultOutcome snapshots. This renderer performs no result
    recalculation and does not consult live marking decisions.
    """

    cleaned_school_name = str(
        school_name,
    ).strip()

    if not cleaned_school_name:
        raise ValueError(
            "school_name is required for official assessment PDF generation."
        )

    buffer = BytesIO()

    styles = _build_styles()

    document = _AssessmentResultsDocumentTemplate(
        buffer,
        title=(f"{export.assessment_title} - Official Results"),
        school_name=cleaned_school_name,
    )

    story = [
        Paragraph(
            f"{export.assessment_title} - Official Results",
            styles["title"],
        ),
        Paragraph(
            (
                "Current authoritative assessment-result outcomes. "
                "Superseded, withdrawn, draft and live provisional "
                "marking data are not included."
            ),
            styles["subtitle"],
        ),
        Spacer(
            1,
            4 * mm,
        ),
    ]

    summary_table = Table(
        [
            [
                Paragraph(
                    "Assessment ID",
                    styles["summary_label"],
                ),
                Paragraph(
                    str(
                        export.assessment_id,
                    ),
                    styles["summary_value"],
                ),
                Paragraph(
                    "Candidates",
                    styles["summary_label"],
                ),
                Paragraph(
                    str(
                        export.candidate_count,
                    ),
                    styles["summary_value"],
                ),
                Paragraph(
                    "Authoritative results",
                    styles["summary_label"],
                ),
                Paragraph(
                    str(
                        export.authoritative_result_count,
                    ),
                    styles["summary_value"],
                ),
            ],
        ],
        colWidths=[
            24 * mm,
            22 * mm,
            22 * mm,
            18 * mm,
            31 * mm,
            18 * mm,
        ],
        hAlign="LEFT",
    )

    summary_table.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, -1),
                    colors.HexColor(
                        _DEFAULT_ACCENT_COLOUR,
                    ),
                ),
                (
                    "BOX",
                    (0, 0),
                    (-1, -1),
                    0.5,
                    colors.HexColor(
                        _DEFAULT_BORDER_COLOUR,
                    ),
                ),
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "MIDDLE",
                ),
                (
                    "LEFTPADDING",
                    (0, 0),
                    (-1, -1),
                    5,
                ),
                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    5,
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    5,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    5,
                ),
            ]
        )
    )

    story.extend(
        [
            summary_table,
            Spacer(
                1,
                5 * mm,
            ),
        ]
    )

    results_table = _build_results_table(
        export,
        styles=styles,
    )

    if results_table is None:
        story.append(
            Paragraph(
                (
                    "There are currently no authoritative results "
                    "for this assessment."
                ),
                styles["empty"],
            )
        )
    else:
        story.append(
            results_table,
        )

    try:
        document.build(
            story,
        )
    except Exception as exc:
        raise RuntimeError(
            "Unable to generate the official assessment-results PDF."
        ) from exc

    pdf_bytes = buffer.getvalue()
    buffer.close()

    if not isinstance(
        pdf_bytes,
        bytes,
    ):
        raise RuntimeError("Assessment PDF generation returned an invalid value.")

    if not pdf_bytes.startswith(
        b"%PDF",
    ):
        raise RuntimeError("Generated assessment result content is not a valid PDF.")

    if (
        len(
            pdf_bytes,
        )
        < _MIN_VALID_PDF_SIZE
    ):
        raise RuntimeError("Generated assessment-results PDF is unexpectedly empty.")

    return pdf_bytes


# ---------------------------------------------------------------------------
# End-to-end service
# ---------------------------------------------------------------------------


async def get_official_assessment_results_pdf(
    db: AsyncSession,
    current_user: User,
    *,
    assessment_id: int,
) -> tuple[
    OfficialAssessmentResultExport,
    bytes,
]:
    """
    Build the official assessment export and render it as PDF.

    The existing official-export service remains the single source of truth
    for access control and authoritative-result selection.
    """

    export = await get_official_assessment_result_export(
        db,
        current_user,
        assessment_id=assessment_id,
    )

    school_name = await _get_school_name(
        db,
        school_id=export.school_id,
    )

    pdf_bytes = generate_official_assessment_results_pdf_bytes(
        export,
        school_name=school_name,
    )

    return (
        export,
        pdf_bytes,
    )
