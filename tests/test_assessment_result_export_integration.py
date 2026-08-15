from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.assessment import (
    Assessment,
    AssessmentStatus,
)
from app.models.assessment_candidate import (
    AssessmentCandidate,
    AssessmentCandidateStatus,
    AssessmentScript,
)
from app.models.assessment_result_outcome import (
    AssessmentResultChangeType,
    AssessmentResultOutcome,
    AssessmentResultOutcomeStatus,
)
from app.models.course import Course
from app.models.user import UserRole
from app.services.assessment_result_export_service import (
    get_official_assessment_result_export,
    render_official_assessment_results_csv,
)
from tests.conftest import create_test_user

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _dt(
    hour: int,
    minute: int = 0,
) -> datetime:
    return datetime(
        2026,
        8,
        15,
        hour,
        minute,
        tzinfo=timezone.utc,
    )


def _as_utc(
    value: datetime,
) -> datetime:
    """
    Normalise a persisted datetime to UTC for deterministic comparison.

    The test database may return timezone-aware SQLAlchemy DateTime values
    without tzinfo even when the model column is declared timezone=True.
    """
    if value.tzinfo is None:
        return value.replace(
            tzinfo=timezone.utc,
        )

    return value.astimezone(
        timezone.utc,
    )


async def _create_course(
    db_session: AsyncSession,
    *,
    teacher_id: int,
    school_id: int,
) -> Course:
    course = Course(
        title="Official Export Integration Course",
        description=("Course used to verify authoritative assessment-result exports."),
        teacher_id=teacher_id,
        school_id=school_id,
        published=True,
    )

    db_session.add(
        course,
    )

    await db_session.flush()
    await db_session.refresh(
        course,
    )

    return course


async def _create_assessment(
    db_session: AsyncSession,
    *,
    course_id: int,
    created_by_id: int,
    school_id: int,
) -> Assessment:
    assessment = Assessment(
        school_id=school_id,
        course_id=course_id,
        created_by_id=created_by_id,
        title="Physics Forces Integration Test",
        description=("Assessment used to verify official result export integration."),
        assessment_type="test",
        academic_year="2026/27",
        term="Autumn",
        status=AssessmentStatus.DRAFT,
        anonymous_marking=False,
    )

    db_session.add(
        assessment,
    )

    await db_session.flush()
    await db_session.refresh(
        assessment,
    )

    return assessment


async def _create_student(
    db_session: AsyncSession,
    *,
    school_id: int,
):
    return await create_test_user(
        db_session,
        email="official.export.student@example.com",
        full_name="Alice Export Student",
        roles=[
            UserRole.STUDENT,
        ],
        school_id=school_id,
    )


async def _create_candidate(
    db_session: AsyncSession,
    *,
    assessment_id: int,
    student_id: int,
) -> AssessmentCandidate:
    candidate = AssessmentCandidate(
        assessment_id=assessment_id,
        student_id=student_id,
        status=AssessmentCandidateStatus.ALLOCATED,
        candidate_number="PHY-EXP-001",
        access_arrangements=None,
    )

    db_session.add(
        candidate,
    )

    await db_session.flush()
    await db_session.refresh(
        candidate,
    )

    return candidate


async def _create_script(
    db_session: AsyncSession,
    *,
    candidate_id: int,
) -> AssessmentScript:
    script = AssessmentScript(
        candidate_id=candidate_id,
        version=1,
        source_type="browser",
        source_filename=None,
        storage_key=None,
        mime_type=None,
        checksum=None,
    )

    db_session.add(
        script,
    )

    await db_session.flush()
    await db_session.refresh(
        script,
    )

    return script


async def _create_outcome(
    db_session: AsyncSession,
    *,
    school_id: int,
    assessment_id: int,
    candidate_id: int,
    script_id: int,
    recorded_by_id: int,
    version: int,
    status: AssessmentResultOutcomeStatus,
    change_type: AssessmentResultChangeType,
    is_authoritative: bool,
    mark: Decimal,
    percentage: Decimal,
    grade_label: str,
    reason: str | None = None,
    effective_at: datetime,
    recorded_at: datetime,
) -> AssessmentResultOutcome:
    outcome = AssessmentResultOutcome(
        school_id=school_id,
        assessment_id=assessment_id,
        candidate_id=candidate_id,
        script_id=script_id,
        version=version,
        status=status,
        change_type=change_type,
        supersedes_id=None,
        is_authoritative=is_authoritative,
        mark_awarded_snapshot=mark,
        maximum_mark_snapshot=Decimal("80.00"),
        percentage_snapshot=percentage,
        grading_scheme_id_snapshot=50,
        grading_scheme_name_snapshot="GCSE 9-1",
        grading_basis_snapshot="percentage",
        grade_boundary_id_snapshot=51,
        grade_label_snapshot=grade_label,
        grade_points_snapshot=Decimal(grade_label),
        is_pass_snapshot=True,
        script_version_snapshot=1,
        reason=reason,
        notes=None,
        effective_at=effective_at,
        recorded_by_id=recorded_by_id,
        recorded_at=recorded_at,
    )

    db_session.add(
        outcome,
    )

    await db_session.flush()
    await db_session.refresh(
        outcome,
    )

    return outcome


# ---------------------------------------------------------------------------
# Real database integration
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_official_export_reads_only_current_authoritative_database_outcome(
    db_session: AsyncSession,
    school_admin_user,
):
    """
    Prove the official export against the real database/repository stack.

    The candidate has two historical result outcomes:

    * version 1 is superseded;
    * version 2 is the current authoritative remark.

    Only version 2 must appear in the official export.
    """

    school_id = school_admin_user.school_id

    assert school_id is not None

    course = await _create_course(
        db_session,
        teacher_id=school_admin_user.id,
        school_id=school_id,
    )

    assessment = await _create_assessment(
        db_session,
        course_id=course.id,
        created_by_id=school_admin_user.id,
        school_id=school_id,
    )

    student = await _create_student(
        db_session,
        school_id=school_id,
    )

    candidate = await _create_candidate(
        db_session,
        assessment_id=assessment.id,
        student_id=student.id,
    )

    script = await _create_script(
        db_session,
        candidate_id=candidate.id,
    )

    superseded = await _create_outcome(
        db_session,
        school_id=school_id,
        assessment_id=assessment.id,
        candidate_id=candidate.id,
        script_id=script.id,
        recorded_by_id=school_admin_user.id,
        version=1,
        status=AssessmentResultOutcomeStatus.SUPERSEDED,
        change_type=AssessmentResultChangeType.INITIAL,
        is_authoritative=False,
        mark=Decimal("68.00"),
        percentage=Decimal("85.00"),
        grade_label="8",
        effective_at=_dt(
            10,
        ),
        recorded_at=_dt(
            10,
            5,
        ),
    )

    authoritative = await _create_outcome(
        db_session,
        school_id=school_id,
        assessment_id=assessment.id,
        candidate_id=candidate.id,
        script_id=script.id,
        recorded_by_id=school_admin_user.id,
        version=2,
        status=AssessmentResultOutcomeStatus.AUTHORITATIVE,
        change_type=AssessmentResultChangeType.REMARK,
        is_authoritative=True,
        mark=Decimal("72.00"),
        percentage=Decimal("90.00"),
        grade_label="9",
        reason="Remark increased the official result.",
        effective_at=_dt(
            11,
        ),
        recorded_at=_dt(
            11,
            5,
        ),
    )

    await db_session.commit()

    export = await get_official_assessment_result_export(
        db_session,
        school_admin_user,
        assessment_id=assessment.id,
    )

    # ------------------------------------------------------------------
    # Assessment-level export metadata
    # ------------------------------------------------------------------

    assert export.assessment_id == assessment.id
    assert export.assessment_title == assessment.title
    assert export.school_id == school_id

    assert export.candidate_count == 1
    assert export.authoritative_result_count == 1
    assert len(export.rows) == 1

    # ------------------------------------------------------------------
    # Only the current authoritative outcome is exported
    # ------------------------------------------------------------------

    row = export.rows[0]

    assert row.outcome_id == authoritative.id
    assert row.outcome_id != superseded.id

    assert row.assessment_id == assessment.id
    assert row.assessment_title == assessment.title

    assert row.candidate_id == candidate.id
    assert row.candidate_number == "PHY-EXP-001"

    assert row.student_id == student.id
    assert row.student_name == "Alice Export Student"
    assert row.student_email == "official.export.student@example.com"

    assert row.script_id == script.id
    assert row.script_version == 1

    assert row.outcome_version == 2
    assert row.change_type == AssessmentResultChangeType.REMARK

    # ------------------------------------------------------------------
    # Immutable official snapshot values
    # ------------------------------------------------------------------

    assert row.mark_awarded == Decimal("72.00")
    assert row.maximum_mark == Decimal("80.00")
    assert row.percentage == Decimal("90.00")

    assert row.grading_scheme_name == "GCSE 9-1"
    assert row.grading_basis == "percentage"
    assert row.grade_label == "9"
    assert row.grade_points == Decimal("9.00")
    assert row.is_pass is True

    assert _as_utc(
        row.effective_at,
    ) == _dt(
        11,
    )

    assert row.recorded_by_id == school_admin_user.id

    assert _as_utc(
        row.recorded_at,
    ) == _dt(
        11,
        5,
    )

    # ------------------------------------------------------------------
    # CSV renderer receives the real authoritative snapshot
    # ------------------------------------------------------------------

    csv_content = render_official_assessment_results_csv(
        export,
    )

    assert "Alice Export Student" in csv_content
    assert "official.export.student@example.com" in csv_content
    assert "PHY-EXP-001" in csv_content
    assert "remark" in csv_content
    assert "72.00" in csv_content
    assert "80.00" in csv_content
    assert "90.00" in csv_content
    assert "GCSE 9-1" in csv_content

    # The superseded historical mark must not leak into the official export.
    assert "68.00" not in csv_content
