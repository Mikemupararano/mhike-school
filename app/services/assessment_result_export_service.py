from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from io import StringIO

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.assessment_result_outcome import (
    AssessmentResultChangeType,
)
from app.models.user import User
from app.repositories.assessment_result_outcome import (
    AssessmentResultOutcomeRepository,
)
from app.repositories.assessment_results import (
    AssessmentResultsRepository,
)
from app.services.assessment_results_service import (
    _ensure_assessment_results_access,
    _get_assessment_or_404,
)

_SAFE_FILENAME_PATTERN = re.compile(
    r"[^A-Za-z0-9._-]+",
)


# ---------------------------------------------------------------------------
# Export data structures
# ---------------------------------------------------------------------------


@dataclass(
    frozen=True,
    slots=True,
)
class OfficialAssessmentResultExportRow:
    """
    One current authoritative assessment result prepared for export.

    All formal result values are taken from AssessmentResultOutcome snapshot
    fields. Live marking decisions and latest-script calculations are
    deliberately excluded from this representation.
    """

    outcome_id: int

    assessment_id: int
    assessment_title: str

    candidate_id: int
    candidate_number: str | None

    student_id: int
    student_name: str | None
    student_email: str | None

    script_id: int
    script_version: int

    outcome_version: int
    change_type: AssessmentResultChangeType

    mark_awarded: Decimal
    maximum_mark: Decimal
    percentage: Decimal | None

    grading_scheme_name: str | None
    grading_basis: str | None
    grade_label: str | None
    grade_points: Decimal | None
    is_pass: bool | None

    effective_at: datetime

    recorded_by_id: int
    recorded_at: datetime


@dataclass(
    frozen=True,
    slots=True,
)
class OfficialAssessmentResultExport:
    """
    Complete current-authoritative result export for one assessment.

    ``candidate_count`` represents all candidates allocated to the assessment.

    ``authoritative_result_count`` represents only candidates that currently
    have an official authoritative result outcome.
    """

    assessment_id: int
    assessment_title: str
    school_id: int

    candidate_count: int
    authoritative_result_count: int

    rows: tuple[
        OfficialAssessmentResultExportRow,
        ...,
    ]


# ---------------------------------------------------------------------------
# Filename helpers
# ---------------------------------------------------------------------------


def _clean_filename_component(
    value: str,
    *,
    fallback: str,
) -> str:
    """
    Return a filesystem-safe component for an exported filename.
    """

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


def build_official_assessment_results_filename(
    export: OfficialAssessmentResultExport,
) -> str:
    """
    Return a safe and predictable filename for the official results CSV.
    """

    title = _clean_filename_component(
        export.assessment_title,
        fallback="assessment",
    )

    return f"assessment_{export.assessment_id}_" f"{title}_official_results.csv"


# ---------------------------------------------------------------------------
# Student lookup
# ---------------------------------------------------------------------------


async def _load_students_by_ids(
    db: AsyncSession,
    student_ids: set[int],
) -> dict[int, User]:
    """
    Load all students required by the export using one set-based query.

    This avoids per-row ORM relationship access and therefore avoids an N+1
    query pattern when exporting large assessment cohorts.
    """

    if not student_ids:
        return {}

    result = await db.execute(
        select(
            User,
        ).where(
            User.id.in_(
                sorted(
                    student_ids,
                ),
            ),
        )
    )

    return {user.id: user for user in result.scalars().all()}


# ---------------------------------------------------------------------------
# Official authoritative-result export
# ---------------------------------------------------------------------------


async def get_official_assessment_result_export(
    db: AsyncSession,
    current_user: User,
    *,
    assessment_id: int,
) -> OfficialAssessmentResultExport:
    """
    Build the official current-result export for an assessment.

    Access follows the existing assessment-results policy:

    - the owning course teacher may export their own assessment;
    - School Admin may export assessments within their school;
    - Platform Admin may export across schools;
    - unrelated teachers remain blocked;
    - normal school-isolation rules remain in force.

    Only current authoritative AssessmentResultOutcome rows are exported.

    Candidates without an authoritative outcome are intentionally omitted
    rather than receiving a result derived from mutable live marking data.

    Retakes, remarks, corrections, moderation changes and administrative
    changes therefore appear only when the corresponding result outcome has
    explicitly become authoritative.
    """

    assessment = await _get_assessment_or_404(
        db,
        assessment_id,
        include_results=False,
    )

    await _ensure_assessment_results_access(
        db,
        current_user,
        assessment,
    )

    # Count every candidate allocated to the assessment independently of
    # whether that candidate currently has an authoritative result.
    #
    # Do not rely on assessment.candidates here because include_results=False
    # does not make relationship-loading behaviour part of this service's
    # contract.
    candidate_count = await AssessmentResultsRepository(
        db,
    ).count_assessment_candidates(
        assessment.id,
    )

    # The authoritative outcome repository is the formal source of truth.
    #
    # In particular, do not derive official results from the latest script or
    # from current mutable marking decisions.
    outcomes = await AssessmentResultOutcomeRepository(
        db,
    ).list_for_assessment(
        assessment.id,
        school_id=assessment.school_id,
        authoritative_only=True,
        include_relationships=True,
    )

    student_ids = {outcome.candidate.student_id for outcome in outcomes}

    students_by_id = await _load_students_by_ids(
        db,
        student_ids,
    )

    rows: list[OfficialAssessmentResultExportRow] = []

    for outcome in outcomes:
        candidate = outcome.candidate

        student = students_by_id.get(
            candidate.student_id,
        )

        rows.append(
            OfficialAssessmentResultExportRow(
                outcome_id=outcome.id,
                assessment_id=assessment.id,
                assessment_title=assessment.title,
                candidate_id=candidate.id,
                candidate_number=candidate.candidate_number,
                student_id=candidate.student_id,
                student_name=(student.full_name if student is not None else None),
                student_email=(student.email if student is not None else None),
                script_id=outcome.script_id,
                script_version=(outcome.script_version_snapshot),
                outcome_version=outcome.version,
                change_type=outcome.change_type,
                mark_awarded=(outcome.mark_awarded_snapshot),
                maximum_mark=(outcome.maximum_mark_snapshot),
                percentage=(outcome.percentage_snapshot),
                grading_scheme_name=(outcome.grading_scheme_name_snapshot),
                grading_basis=(outcome.grading_basis_snapshot),
                grade_label=(outcome.grade_label_snapshot),
                grade_points=(outcome.grade_points_snapshot),
                is_pass=(outcome.is_pass_snapshot),
                effective_at=outcome.effective_at,
                recorded_by_id=outcome.recorded_by_id,
                recorded_at=outcome.recorded_at,
            )
        )

    return OfficialAssessmentResultExport(
        assessment_id=assessment.id,
        assessment_title=assessment.title,
        school_id=assessment.school_id,
        candidate_count=candidate_count,
        authoritative_result_count=len(
            rows,
        ),
        rows=tuple(
            rows,
        ),
    )


# ---------------------------------------------------------------------------
# CSV value normalisation
# ---------------------------------------------------------------------------


def _csv_value(
    value: object | None,
) -> object:
    """
    Convert Python values into stable CSV-safe representations.

    Rules:

    - None becomes an empty cell;
    - booleans become lowercase true/false;
    - datetimes use ISO 8601;
    - Decimals retain their exact decimal representation;
    - Enum-like values use their underlying value;
    - all other values are passed directly to csv.writer.
    """

    if value is None:
        return ""

    if isinstance(
        value,
        bool,
    ):
        return "true" if value else "false"

    if isinstance(
        value,
        datetime,
    ):
        return value.isoformat()

    if isinstance(
        value,
        Decimal,
    ):
        return str(
            value,
        )

    if hasattr(
        value,
        "value",
    ):
        return str(
            value.value,
        )

    return value


# ---------------------------------------------------------------------------
# CSV rendering
# ---------------------------------------------------------------------------


def render_official_assessment_results_csv(
    export: OfficialAssessmentResultExport,
) -> str:
    """
    Render an official authoritative-results export as CSV text.

    The CSV contains one row for each candidate with a current authoritative
    result outcome.

    It deliberately exports immutable result snapshots rather than recalculated
    live marking values.
    """

    output = StringIO(
        newline="",
    )

    writer = csv.writer(
        output,
        lineterminator="\r\n",
    )

    writer.writerow(
        [
            "outcome_id",
            "assessment_id",
            "assessment_title",
            "candidate_id",
            "candidate_number",
            "student_id",
            "student_name",
            "student_email",
            "script_id",
            "script_version",
            "outcome_version",
            "change_type",
            "mark_awarded",
            "maximum_mark",
            "percentage",
            "grading_scheme_name",
            "grading_basis",
            "grade_label",
            "grade_points",
            "is_pass",
            "effective_at",
            "recorded_by_id",
            "recorded_at",
        ]
    )

    for row in export.rows:
        writer.writerow(
            [
                _csv_value(
                    row.outcome_id,
                ),
                _csv_value(
                    row.assessment_id,
                ),
                _csv_value(
                    row.assessment_title,
                ),
                _csv_value(
                    row.candidate_id,
                ),
                _csv_value(
                    row.candidate_number,
                ),
                _csv_value(
                    row.student_id,
                ),
                _csv_value(
                    row.student_name,
                ),
                _csv_value(
                    row.student_email,
                ),
                _csv_value(
                    row.script_id,
                ),
                _csv_value(
                    row.script_version,
                ),
                _csv_value(
                    row.outcome_version,
                ),
                _csv_value(
                    row.change_type,
                ),
                _csv_value(
                    row.mark_awarded,
                ),
                _csv_value(
                    row.maximum_mark,
                ),
                _csv_value(
                    row.percentage,
                ),
                _csv_value(
                    row.grading_scheme_name,
                ),
                _csv_value(
                    row.grading_basis,
                ),
                _csv_value(
                    row.grade_label,
                ),
                _csv_value(
                    row.grade_points,
                ),
                _csv_value(
                    row.is_pass,
                ),
                _csv_value(
                    row.effective_at,
                ),
                _csv_value(
                    row.recorded_by_id,
                ),
                _csv_value(
                    row.recorded_at,
                ),
            ]
        )

    return output.getvalue()
