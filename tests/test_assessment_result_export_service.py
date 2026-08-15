from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

import app.services.assessment_result_export_service as service
from app.models.assessment_result_outcome import (
    AssessmentResultChangeType,
)

# ---------------------------------------------------------------------------
# Test-data helpers
# ---------------------------------------------------------------------------


def _user(
    *,
    user_id: int = 10,
    school_id: int = 1,
    full_name: str | None = None,
    email: str | None = None,
):
    return SimpleNamespace(
        id=user_id,
        school_id=school_id,
        full_name=full_name or f"User {user_id}",
        email=email or f"user{user_id}@example.com",
        roles=["teacher"],
    )


def _assessment(
    *,
    assessment_id: int = 100,
    school_id: int = 1,
    title: str = "End of Topic Test",
):
    return SimpleNamespace(
        id=assessment_id,
        school_id=school_id,
        course_id=20,
        title=title,
    )


def _candidate(
    *,
    candidate_id: int = 200,
    student_id: int = 400,
    candidate_number: str | None = "C001",
):
    return SimpleNamespace(
        id=candidate_id,
        student_id=student_id,
        candidate_number=candidate_number,
    )


def _outcome(
    *,
    outcome_id: int = 1,
    assessment_id: int = 100,
    candidate_id: int = 200,
    student_id: int = 400,
    script_id: int = 300,
    script_version: int = 1,
    outcome_version: int = 1,
    change_type: AssessmentResultChangeType = (AssessmentResultChangeType.INITIAL),
    mark: Decimal = Decimal("72"),
    maximum: Decimal = Decimal("80"),
    percentage: Decimal | None = Decimal("90.00"),
    grade_label: str | None = "9",
    grade_points: Decimal | None = Decimal("9"),
    is_pass: bool | None = True,
):
    candidate = _candidate(
        candidate_id=candidate_id,
        student_id=student_id,
    )

    return SimpleNamespace(
        id=outcome_id,
        assessment_id=assessment_id,
        candidate_id=candidate_id,
        candidate=candidate,
        script_id=script_id,
        script_version_snapshot=script_version,
        version=outcome_version,
        change_type=change_type,
        mark_awarded_snapshot=mark,
        maximum_mark_snapshot=maximum,
        percentage_snapshot=percentage,
        grading_scheme_name_snapshot="GCSE 9-1",
        grading_basis_snapshot="percentage",
        grade_label_snapshot=grade_label,
        grade_points_snapshot=grade_points,
        is_pass_snapshot=is_pass,
        effective_at=datetime(
            2026,
            8,
            14,
            12,
            0,
            tzinfo=timezone.utc,
        ),
        recorded_by_id=10,
        recorded_at=datetime(
            2026,
            8,
            14,
            12,
            1,
            tzinfo=timezone.utc,
        ),
    )


class FakeDB:
    pass


def _patch_export_dependencies(
    monkeypatch,
    *,
    assessment=None,
    outcomes=None,
    students=None,
    candidate_count: int = 1,
):
    assessment = assessment or _assessment()
    outcomes = list(outcomes or [])
    students = dict(students or {})

    calls: list[tuple] = []

    async def fake_get_assessment(
        db,
        assessment_id,
        *,
        include_results=True,
    ):
        calls.append(
            (
                "get_assessment",
                assessment_id,
                include_results,
            )
        )

        return assessment

    async def fake_access(
        db,
        current_user,
        supplied_assessment,
    ):
        calls.append(
            (
                "access",
                current_user.id,
                supplied_assessment.id,
            )
        )

        return SimpleNamespace(
            id=20,
            school_id=assessment.school_id,
            teacher_id=current_user.id,
        )

    async def fake_load_students(
        db,
        student_ids,
    ):
        calls.append(
            (
                "load_students",
                set(student_ids),
            )
        )

        return students

    class FakeOutcomeRepository:
        def __init__(
            self,
            db,
        ):
            self.db = db

        async def list_for_assessment(
            self,
            assessment_id,
            *,
            school_id=None,
            authoritative_only=False,
            include_relationships=True,
        ):
            calls.append(
                (
                    "list_for_assessment",
                    assessment_id,
                    school_id,
                    authoritative_only,
                    include_relationships,
                )
            )

            return outcomes

    class FakeResultsRepository:
        def __init__(
            self,
            db,
        ):
            self.db = db

        async def count_assessment_candidates(
            self,
            assessment_id,
        ):
            calls.append(
                (
                    "count_candidates",
                    assessment_id,
                )
            )

            return candidate_count

    monkeypatch.setattr(
        service,
        "_get_assessment_or_404",
        fake_get_assessment,
    )

    monkeypatch.setattr(
        service,
        "_ensure_assessment_results_access",
        fake_access,
    )

    monkeypatch.setattr(
        service,
        "_load_students_by_ids",
        fake_load_students,
    )

    monkeypatch.setattr(
        service,
        "AssessmentResultOutcomeRepository",
        FakeOutcomeRepository,
    )

    monkeypatch.setattr(
        service,
        "AssessmentResultsRepository",
        FakeResultsRepository,
    )

    return calls


# ---------------------------------------------------------------------------
# Export assembly
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_official_export_uses_authoritative_repository_query(
    monkeypatch,
):
    outcome = _outcome()

    student = _user(
        user_id=400,
        full_name="Alice Student",
        email="alice@example.com",
    )

    calls = _patch_export_dependencies(
        monkeypatch,
        outcomes=[
            outcome,
        ],
        students={
            400: student,
        },
    )

    result = await service.get_official_assessment_result_export(
        FakeDB(),
        _user(),
        assessment_id=100,
    )

    assert (
        "list_for_assessment",
        100,
        1,
        True,
        True,
    ) in calls

    assert result.assessment_id == 100
    assert result.assessment_title == "End of Topic Test"
    assert result.authoritative_result_count == 1

    row = result.rows[0]

    assert row.outcome_id == 1
    assert row.candidate_id == 200
    assert row.student_id == 400
    assert row.student_name == "Alice Student"
    assert row.student_email == "alice@example.com"

    assert row.mark_awarded == Decimal("72")
    assert row.maximum_mark == Decimal("80")
    assert row.percentage == Decimal("90.00")
    assert row.grade_label == "9"


@pytest.mark.asyncio
async def test_official_export_reports_total_candidate_count_separately(
    monkeypatch,
):
    outcome = _outcome()

    _patch_export_dependencies(
        monkeypatch,
        outcomes=[
            outcome,
        ],
        students={
            400: _user(
                user_id=400,
            ),
        },
        candidate_count=3,
    )

    result = await service.get_official_assessment_result_export(
        FakeDB(),
        _user(),
        assessment_id=100,
    )

    assert result.candidate_count == 3
    assert result.authoritative_result_count == 1
    assert len(result.rows) == 1


@pytest.mark.asyncio
async def test_candidate_without_authoritative_result_is_not_invented(
    monkeypatch,
):
    _patch_export_dependencies(
        monkeypatch,
        outcomes=[],
        students={},
        candidate_count=2,
    )

    result = await service.get_official_assessment_result_export(
        FakeDB(),
        _user(),
        assessment_id=100,
    )

    assert result.candidate_count == 2
    assert result.authoritative_result_count == 0
    assert result.rows == ()


@pytest.mark.asyncio
async def test_current_retake_outcome_is_exported_as_official_result(
    monkeypatch,
):
    retake = _outcome(
        outcome_id=2,
        script_id=301,
        script_version=2,
        outcome_version=2,
        change_type=AssessmentResultChangeType.RETAKE,
        mark=Decimal("78"),
        percentage=Decimal("97.50"),
    )

    _patch_export_dependencies(
        monkeypatch,
        outcomes=[
            retake,
        ],
        students={
            400: _user(
                user_id=400,
                full_name="Retake Student",
            ),
        },
    )

    result = await service.get_official_assessment_result_export(
        FakeDB(),
        _user(),
        assessment_id=100,
    )

    assert len(result.rows) == 1

    row = result.rows[0]

    assert row.outcome_id == 2
    assert row.change_type == AssessmentResultChangeType.RETAKE
    assert row.script_id == 301
    assert row.script_version == 2
    assert row.outcome_version == 2
    assert row.mark_awarded == Decimal("78")
    assert row.percentage == Decimal("97.50")


@pytest.mark.asyncio
async def test_current_remark_snapshot_is_used_without_live_recalculation(
    monkeypatch,
):
    remark = _outcome(
        outcome_id=3,
        outcome_version=2,
        change_type=AssessmentResultChangeType.REMARK,
        mark=Decimal("74"),
        percentage=Decimal("92.50"),
    )

    _patch_export_dependencies(
        monkeypatch,
        outcomes=[
            remark,
        ],
        students={
            400: _user(
                user_id=400,
            ),
        },
    )

    result = await service.get_official_assessment_result_export(
        FakeDB(),
        _user(),
        assessment_id=100,
    )

    row = result.rows[0]

    assert row.change_type == AssessmentResultChangeType.REMARK
    assert row.mark_awarded == Decimal("74")
    assert row.percentage == Decimal("92.50")


@pytest.mark.asyncio
async def test_export_propagates_existing_results_access_denial(
    monkeypatch,
):
    assessment = _assessment()

    async def fake_get_assessment(
        db,
        assessment_id,
        *,
        include_results=True,
    ):
        return assessment

    async def fake_access(
        db,
        current_user,
        supplied_assessment,
    ):
        raise HTTPException(
            status_code=403,
            detail="You can only view results for your own courses",
        )

    monkeypatch.setattr(
        service,
        "_get_assessment_or_404",
        fake_get_assessment,
    )

    monkeypatch.setattr(
        service,
        "_ensure_assessment_results_access",
        fake_access,
    )

    with pytest.raises(HTTPException) as exc:
        await service.get_official_assessment_result_export(
            FakeDB(),
            _user(),
            assessment_id=100,
        )

    assert exc.value.status_code == 403
    assert exc.value.detail == "You can only view results for your own courses"


# ---------------------------------------------------------------------------
# CSV rendering
# ---------------------------------------------------------------------------


def _export_for_csv():
    row = service.OfficialAssessmentResultExportRow(
        outcome_id=1,
        assessment_id=100,
        assessment_title='Physics, "Forces"',
        candidate_id=200,
        candidate_number="P001",
        student_id=400,
        student_name="Student, Alice",
        student_email="alice@example.com",
        script_id=300,
        script_version=1,
        outcome_version=1,
        change_type=AssessmentResultChangeType.INITIAL,
        mark_awarded=Decimal("72.50"),
        maximum_mark=Decimal("80"),
        percentage=Decimal("90.63"),
        grading_scheme_name="GCSE 9-1",
        grading_basis="percentage",
        grade_label="9",
        grade_points=Decimal("9"),
        is_pass=True,
        effective_at=datetime(
            2026,
            8,
            14,
            12,
            0,
            tzinfo=timezone.utc,
        ),
        recorded_by_id=10,
        recorded_at=datetime(
            2026,
            8,
            14,
            12,
            1,
            tzinfo=timezone.utc,
        ),
    )

    return service.OfficialAssessmentResultExport(
        assessment_id=100,
        assessment_title='Physics, "Forces"',
        school_id=1,
        candidate_count=1,
        authoritative_result_count=1,
        rows=(row,),
    )


def test_csv_renderer_outputs_official_snapshot_fields():
    csv_text = service.render_official_assessment_results_csv(
        _export_for_csv(),
    )

    assert (
        "outcome_id,assessment_id,assessment_title,"
        "candidate_id,candidate_number" in csv_text
    )

    assert '"Physics, ""Forces"""' in csv_text
    assert '"Student, Alice"' in csv_text

    assert "72.50" in csv_text
    assert "80" in csv_text
    assert "90.63" in csv_text
    assert "initial" in csv_text
    assert "GCSE 9-1" in csv_text
    assert ",true," in csv_text

    assert "2026-08-14T12:00:00+00:00" in csv_text


def test_csv_renderer_handles_optional_values_as_blank():
    export = _export_for_csv()
    source_row = export.rows[0]

    row = service.OfficialAssessmentResultExportRow(
        outcome_id=source_row.outcome_id,
        assessment_id=source_row.assessment_id,
        assessment_title=source_row.assessment_title,
        candidate_id=source_row.candidate_id,
        candidate_number=None,
        student_id=source_row.student_id,
        student_name=None,
        student_email=None,
        script_id=source_row.script_id,
        script_version=source_row.script_version,
        outcome_version=source_row.outcome_version,
        change_type=source_row.change_type,
        mark_awarded=source_row.mark_awarded,
        maximum_mark=source_row.maximum_mark,
        percentage=None,
        grading_scheme_name=None,
        grading_basis=None,
        grade_label=None,
        grade_points=None,
        is_pass=None,
        effective_at=source_row.effective_at,
        recorded_by_id=source_row.recorded_by_id,
        recorded_at=source_row.recorded_at,
    )

    csv_text = service.render_official_assessment_results_csv(
        service.OfficialAssessmentResultExport(
            assessment_id=export.assessment_id,
            assessment_title=export.assessment_title,
            school_id=export.school_id,
            candidate_count=1,
            authoritative_result_count=1,
            rows=(row,),
        )
    )

    assert "None" not in csv_text


# ---------------------------------------------------------------------------
# Filename
# ---------------------------------------------------------------------------


def test_official_export_filename_is_safe_and_predictable():
    export = service.OfficialAssessmentResultExport(
        assessment_id=100,
        assessment_title="Physics: Forces / Motion?",
        school_id=1,
        candidate_count=0,
        authoritative_result_count=0,
        rows=(),
    )

    filename = service.build_official_assessment_results_filename(
        export,
    )

    assert filename == ("assessment_100_" "Physics-Forces-Motion_official_results.csv")

    assert "/" not in filename
    assert "?" not in filename
    assert ":" not in filename
