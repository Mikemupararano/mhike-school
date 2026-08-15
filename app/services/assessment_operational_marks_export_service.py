from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from decimal import Decimal
from io import StringIO

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.assessment import AssessmentStatus
from app.models.assessment_candidate import (
    AssessmentCandidate,
    AssessmentScriptStatus,
)
from app.models.user import User
from app.services.assessment_results_service import (
    get_assessment_result_grid,
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
class OperationalAssessmentMarkExportRow:
    """
    One operational assessment-script result prepared for CSV export.

    This row represents current live marking state for one script version.

    It is deliberately not an official result-history record. Values such as
    ``mark_awarded`` may include provisional question-level marking and may
    therefore change as marking, review and moderation continue.
    """

    assessment_id: int
    assessment_title: str

    candidate_id: int
    candidate_number: str | None

    student_id: int
    student_name: str | None
    student_email: str | None

    script_id: int
    script_version: int
    script_status: AssessmentScriptStatus

    is_latest_script: bool

    response_count: int
    decision_count: int

    mark_awarded: Decimal
    maximum_mark: Decimal
    percentage: Decimal | None

    completed_decision_count: int
    finalised_decision_count: int

    marking_completion_percentage: Decimal | None
    finalisation_completion_percentage: Decimal | None

    is_fully_marked: bool
    is_fully_finalised: bool


@dataclass(
    frozen=True,
    slots=True,
)
class OperationalAssessmentMarksExport:
    """
    Complete operational marking export for one assessment.

    Unlike the official assessment-result export, this representation is built
    from the live assessment-results grid and can contain multiple script
    versions for the same candidate.
    """

    assessment_id: int
    assessment_title: str
    assessment_status: AssessmentStatus

    maximum_mark: Decimal
    markable_question_count: int

    candidate_count: int
    script_count: int

    rows: tuple[
        OperationalAssessmentMarkExportRow,
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


def build_operational_assessment_marks_filename(
    export: OperationalAssessmentMarksExport,
) -> str:
    """
    Return a safe filename for the operational assessment-marks CSV.
    """

    title = _clean_filename_component(
        export.assessment_title,
        fallback="assessment",
    )

    return f"assessment_{export.assessment_id}_" f"{title}_operational_marks.csv"


# ---------------------------------------------------------------------------
# Candidate/student enrichment
# ---------------------------------------------------------------------------


@dataclass(
    frozen=True,
    slots=True,
)
class _CandidateStudentIdentity:
    candidate_id: int
    candidate_number: str | None

    student_id: int
    student_name: str | None
    student_email: str | None


async def _load_candidate_student_identities(
    db: AsyncSession,
    candidate_ids: set[int],
) -> dict[int, _CandidateStudentIdentity]:
    """
    Load candidate and student identity data in one set-based query.

    The operational result grid intentionally contains compact marking data
    only. This enrichment query avoids per-row ORM lookups and therefore
    avoids an N+1 pattern for large assessment cohorts.
    """

    if not candidate_ids:
        return {}

    statement = (
        select(
            AssessmentCandidate.id.label(
                "candidate_id",
            ),
            AssessmentCandidate.candidate_number.label(
                "candidate_number",
            ),
            User.id.label(
                "student_id",
            ),
            User.full_name.label(
                "student_name",
            ),
            User.email.label(
                "student_email",
            ),
        )
        .join(
            User,
            User.id == AssessmentCandidate.student_id,
        )
        .where(
            AssessmentCandidate.id.in_(
                sorted(
                    candidate_ids,
                )
            ),
        )
        .order_by(
            AssessmentCandidate.id.asc(),
        )
    )

    result = await db.execute(
        statement,
    )

    identities: dict[int, _CandidateStudentIdentity] = {}

    for row in result.all():
        candidate_id = int(
            row.candidate_id,
        )

        identities[candidate_id] = _CandidateStudentIdentity(
            candidate_id=candidate_id,
            candidate_number=row.candidate_number,
            student_id=int(
                row.student_id,
            ),
            student_name=row.student_name,
            student_email=row.student_email,
        )

    return identities


# ---------------------------------------------------------------------------
# Export construction
# ---------------------------------------------------------------------------


def _latest_script_ids_by_candidate(
    scripts: list[dict],
) -> dict[int, int]:
    """
    Return the deterministic latest script ID for each candidate.

    Highest script version wins. Script ID is used as a deterministic
    tiebreaker, matching the assessment-results service's version-history
    conventions.
    """

    latest: dict[int, tuple[int, int]] = {}

    for script in scripts:
        candidate_id = int(
            script["candidate_id"],
        )
        script_id = int(
            script["script_id"],
        )
        version = int(
            script["version"],
        )

        current = latest.get(
            candidate_id,
        )

        if (
            current is None
            or (
                version,
                script_id,
            )
            > current
        ):
            latest[candidate_id] = (
                version,
                script_id,
            )

    return {
        candidate_id: script_id
        for candidate_id, (
            _version,
            script_id,
        ) in latest.items()
    }


async def get_operational_assessment_marks_export(
    db: AsyncSession,
    current_user: User,
    *,
    assessment_id: int,
) -> OperationalAssessmentMarksExport:
    """
    Build the live operational marking export for one assessment.

    Access control and marking aggregation are delegated to
    ``get_assessment_result_grid`` so this export cannot drift from the
    established assessment-results rules.

    Important semantic distinction:

    * this export reflects live operational script/marking state;
    * it may include provisional marks;
    * it includes every script version;
    * it is not authoritative result history;
    * it must not be used as a substitute for the official-results export.
    """

    grid = await get_assessment_result_grid(
        db,
        current_user,
        assessment_id,
    )

    scripts = list(
        grid["scripts"],
    )

    candidate_ids = {
        int(
            script["candidate_id"],
        )
        for script in scripts
    }

    identities = await _load_candidate_student_identities(
        db,
        candidate_ids,
    )

    latest_script_ids = _latest_script_ids_by_candidate(
        scripts,
    )

    rows: list[OperationalAssessmentMarkExportRow] = []

    for script in scripts:
        candidate_id = int(
            script["candidate_id"],
        )

        identity = identities.get(
            candidate_id,
        )

        if identity is None:
            raise RuntimeError(
                (
                    "Operational assessment-result grid references "
                    f"candidate {candidate_id}, but candidate/student "
                    "identity data could not be loaded."
                )
            )

        script_id = int(
            script["script_id"],
        )

        rows.append(
            OperationalAssessmentMarkExportRow(
                assessment_id=int(
                    grid["assessment_id"],
                ),
                assessment_title=str(
                    grid["title"],
                ),
                candidate_id=candidate_id,
                candidate_number=identity.candidate_number,
                student_id=identity.student_id,
                student_name=identity.student_name,
                student_email=identity.student_email,
                script_id=script_id,
                script_version=int(
                    script["version"],
                ),
                script_status=script["script_status"],
                is_latest_script=(
                    latest_script_ids.get(
                        candidate_id,
                    )
                    == script_id
                ),
                response_count=int(
                    script["response_count"],
                ),
                decision_count=int(
                    script["decision_count"],
                ),
                mark_awarded=Decimal(
                    str(
                        script["mark_awarded"],
                    )
                ),
                maximum_mark=Decimal(
                    str(
                        script["maximum_mark"],
                    )
                ),
                percentage=(
                    Decimal(
                        str(
                            script["percentage"],
                        )
                    )
                    if script["percentage"] is not None
                    else None
                ),
                completed_decision_count=int(
                    script["completed_decision_count"],
                ),
                finalised_decision_count=int(
                    script["finalised_decision_count"],
                ),
                marking_completion_percentage=(
                    Decimal(
                        str(
                            script["marking_completion_percentage"],
                        )
                    )
                    if script["marking_completion_percentage"] is not None
                    else None
                ),
                finalisation_completion_percentage=(
                    Decimal(
                        str(
                            script["finalisation_completion_percentage"],
                        )
                    )
                    if script["finalisation_completion_percentage"] is not None
                    else None
                ),
                is_fully_marked=bool(
                    script["is_fully_marked"],
                ),
                is_fully_finalised=bool(
                    script["is_fully_finalised"],
                ),
            )
        )

    return OperationalAssessmentMarksExport(
        assessment_id=int(
            grid["assessment_id"],
        ),
        assessment_title=str(
            grid["title"],
        ),
        assessment_status=grid["status"],
        maximum_mark=Decimal(
            str(
                grid["maximum_mark"],
            )
        ),
        markable_question_count=int(
            grid["markable_question_count"],
        ),
        candidate_count=len(
            candidate_ids,
        ),
        script_count=int(
            grid["script_count"],
        ),
        rows=tuple(
            rows,
        ),
    )


# ---------------------------------------------------------------------------
# CSV rendering
# ---------------------------------------------------------------------------


_OPERATIONAL_CSV_COLUMNS = (
    "assessment_id",
    "assessment_title",
    "candidate_id",
    "candidate_number",
    "student_id",
    "student_name",
    "student_email",
    "script_id",
    "script_version",
    "script_status",
    "is_latest_script",
    "response_count",
    "decision_count",
    "mark_awarded",
    "maximum_mark",
    "percentage",
    "completed_decision_count",
    "finalised_decision_count",
    "marking_completion_percentage",
    "finalisation_completion_percentage",
    "is_fully_marked",
    "is_fully_finalised",
)


def _csv_value(
    value,
):
    if value is None:
        return ""

    if isinstance(
        value,
        bool,
    ):
        return "true" if value else "false"

    if isinstance(
        value,
        Decimal,
    ):
        return str(
            value,
        )

    enum_value = getattr(
        value,
        "value",
        None,
    )

    if enum_value is not None:
        return enum_value

    return value


def render_operational_assessment_marks_csv(
    export: OperationalAssessmentMarksExport,
) -> str:
    """
    Render an operational assessment-marks export as CSV.
    """

    buffer = StringIO(
        newline="",
    )

    writer = csv.writer(
        buffer,
        lineterminator="\r\n",
    )

    writer.writerow(
        _OPERATIONAL_CSV_COLUMNS,
    )

    for row in export.rows:
        writer.writerow(
            [
                _csv_value(
                    getattr(
                        row,
                        column,
                    )
                )
                for column in _OPERATIONAL_CSV_COLUMNS
            ]
        )

    return buffer.getvalue()
