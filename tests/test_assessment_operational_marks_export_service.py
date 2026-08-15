from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace

import pytest

import app.services.assessment_operational_marks_export_service as service
from app.models.assessment import AssessmentStatus
from app.models.assessment_candidate import AssessmentScriptStatus


def _grid(
    *,
    scripts: list[dict] | None = None,
):
    return {
        "assessment_id": 100,
        "title": "Physics Operational Test",
        "status": AssessmentStatus.DRAFT,
        "maximum_mark": Decimal("80.00"),
        "markable_question_count": 8,
        "script_count": len(
            scripts or [],
        ),
        "scripts": scripts or [],
    }


def _script(
    *,
    script_id: int,
    candidate_id: int,
    version: int,
    mark_awarded: Decimal = Decimal("40.00"),
    percentage: Decimal | None = Decimal("50.00"),
    response_count: int = 8,
    decision_count: int = 8,
    completed_decision_count: int = 8,
    finalised_decision_count: int = 0,
    is_fully_marked: bool = True,
    is_fully_finalised: bool = False,
):
    return {
        "script_id": script_id,
        "candidate_id": candidate_id,
        "version": version,
        "script_status": AssessmentScriptStatus.MARKED,
        "response_count": response_count,
        "decision_count": decision_count,
        "mark_awarded": mark_awarded,
        "maximum_mark": Decimal("80.00"),
        "percentage": percentage,
        "completed_decision_count": completed_decision_count,
        "finalised_decision_count": finalised_decision_count,
        "marking_completion_percentage": Decimal("100.00"),
        "finalisation_completion_percentage": Decimal("0.00"),
        "is_fully_marked": is_fully_marked,
        "is_fully_finalised": is_fully_finalised,
    }


def _identity(
    *,
    candidate_id: int,
    student_id: int,
    candidate_number: str,
    student_name: str,
    student_email: str,
):
    return service._CandidateStudentIdentity(
        candidate_id=candidate_id,
        candidate_number=candidate_number,
        student_id=student_id,
        student_name=student_name,
        student_email=student_email,
    )


@pytest.mark.asyncio
async def test_export_uses_operational_result_grid(
    monkeypatch,
):
    scripts = [
        _script(
            script_id=301,
            candidate_id=201,
            version=1,
        ),
    ]

    captured = {}

    async def fake_grid(
        db,
        current_user,
        assessment_id,
    ):
        captured["assessment_id"] = assessment_id
        return _grid(
            scripts=scripts,
        )

    async def fake_identities(
        db,
        candidate_ids,
    ):
        assert candidate_ids == {
            201,
        }

        return {
            201: _identity(
                candidate_id=201,
                student_id=401,
                candidate_number="PHY-001",
                student_name="Alice Student",
                student_email="alice@example.com",
            ),
        }

    monkeypatch.setattr(
        service,
        "get_assessment_result_grid",
        fake_grid,
    )

    monkeypatch.setattr(
        service,
        "_load_candidate_student_identities",
        fake_identities,
    )

    export = await service.get_operational_assessment_marks_export(
        object(),
        SimpleNamespace(
            id=10,
        ),
        assessment_id=100,
    )

    assert captured["assessment_id"] == 100

    assert export.assessment_id == 100
    assert export.assessment_title == "Physics Operational Test"
    assert export.assessment_status == AssessmentStatus.DRAFT
    assert export.maximum_mark == Decimal("80.00")
    assert export.markable_question_count == 8

    assert export.candidate_count == 1
    assert export.script_count == 1
    assert len(export.rows) == 1


@pytest.mark.asyncio
async def test_export_preserves_live_script_marking_values(
    monkeypatch,
):
    scripts = [
        _script(
            script_id=301,
            candidate_id=201,
            version=1,
            mark_awarded=Decimal("43.50"),
            percentage=Decimal("54.38"),
            completed_decision_count=6,
            finalised_decision_count=4,
            is_fully_marked=False,
            is_fully_finalised=False,
        ),
    ]

    async def fake_grid(
        db,
        current_user,
        assessment_id,
    ):
        return _grid(
            scripts=scripts,
        )

    async def fake_identities(
        db,
        candidate_ids,
    ):
        return {
            201: _identity(
                candidate_id=201,
                student_id=401,
                candidate_number="PHY-001",
                student_name="Alice Student",
                student_email="alice@example.com",
            ),
        }

    monkeypatch.setattr(
        service,
        "get_assessment_result_grid",
        fake_grid,
    )

    monkeypatch.setattr(
        service,
        "_load_candidate_student_identities",
        fake_identities,
    )

    export = await service.get_operational_assessment_marks_export(
        object(),
        SimpleNamespace(
            id=10,
        ),
        assessment_id=100,
    )

    row = export.rows[0]

    assert row.mark_awarded == Decimal("43.50")
    assert row.maximum_mark == Decimal("80.00")
    assert row.percentage == Decimal("54.38")

    assert row.completed_decision_count == 6
    assert row.finalised_decision_count == 4

    assert row.is_fully_marked is False
    assert row.is_fully_finalised is False


@pytest.mark.asyncio
async def test_export_preserves_multiple_script_versions(
    monkeypatch,
):
    scripts = [
        _script(
            script_id=301,
            candidate_id=201,
            version=1,
            mark_awarded=Decimal("40.00"),
        ),
        _script(
            script_id=302,
            candidate_id=201,
            version=2,
            mark_awarded=Decimal("52.00"),
        ),
    ]

    async def fake_grid(
        db,
        current_user,
        assessment_id,
    ):
        return _grid(
            scripts=scripts,
        )

    async def fake_identities(
        db,
        candidate_ids,
    ):
        return {
            201: _identity(
                candidate_id=201,
                student_id=401,
                candidate_number="PHY-001",
                student_name="Alice Student",
                student_email="alice@example.com",
            ),
        }

    monkeypatch.setattr(
        service,
        "get_assessment_result_grid",
        fake_grid,
    )

    monkeypatch.setattr(
        service,
        "_load_candidate_student_identities",
        fake_identities,
    )

    export = await service.get_operational_assessment_marks_export(
        object(),
        SimpleNamespace(
            id=10,
        ),
        assessment_id=100,
    )

    assert export.candidate_count == 1
    assert export.script_count == 2
    assert len(export.rows) == 2

    first, second = export.rows

    assert first.script_id == 301
    assert first.script_version == 1
    assert first.is_latest_script is False

    assert second.script_id == 302
    assert second.script_version == 2
    assert second.is_latest_script is True


def test_latest_script_selection_uses_version_then_id():
    scripts = [
        {
            "candidate_id": 201,
            "script_id": 300,
            "version": 1,
        },
        {
            "candidate_id": 201,
            "script_id": 301,
            "version": 2,
        },
        {
            "candidate_id": 201,
            "script_id": 302,
            "version": 2,
        },
        {
            "candidate_id": 202,
            "script_id": 400,
            "version": 3,
        },
    ]

    result = service._latest_script_ids_by_candidate(
        scripts,
    )

    assert result == {
        201: 302,
        202: 400,
    }


@pytest.mark.asyncio
async def test_missing_candidate_identity_is_rejected(
    monkeypatch,
):
    scripts = [
        _script(
            script_id=301,
            candidate_id=201,
            version=1,
        ),
    ]

    async def fake_grid(
        db,
        current_user,
        assessment_id,
    ):
        return _grid(
            scripts=scripts,
        )

    async def fake_identities(
        db,
        candidate_ids,
    ):
        return {}

    monkeypatch.setattr(
        service,
        "get_assessment_result_grid",
        fake_grid,
    )

    monkeypatch.setattr(
        service,
        "_load_candidate_student_identities",
        fake_identities,
    )

    with pytest.raises(
        RuntimeError,
        match=("candidate 201.*identity data could not be loaded"),
    ):
        await service.get_operational_assessment_marks_export(
            object(),
            SimpleNamespace(
                id=10,
            ),
            assessment_id=100,
        )


@pytest.mark.asyncio
async def test_empty_grid_produces_empty_export(
    monkeypatch,
):
    async def fake_grid(
        db,
        current_user,
        assessment_id,
    ):
        return _grid(
            scripts=[],
        )

    async def fake_identities(
        db,
        candidate_ids,
    ):
        assert candidate_ids == set()
        return {}

    monkeypatch.setattr(
        service,
        "get_assessment_result_grid",
        fake_grid,
    )

    monkeypatch.setattr(
        service,
        "_load_candidate_student_identities",
        fake_identities,
    )

    export = await service.get_operational_assessment_marks_export(
        object(),
        SimpleNamespace(
            id=10,
        ),
        assessment_id=100,
    )

    assert export.candidate_count == 0
    assert export.script_count == 0
    assert export.rows == ()


def test_csv_contains_operational_marking_fields():
    export = service.OperationalAssessmentMarksExport(
        assessment_id=100,
        assessment_title="Physics Operational Test",
        assessment_status=AssessmentStatus.DRAFT,
        maximum_mark=Decimal("80.00"),
        markable_question_count=8,
        candidate_count=1,
        script_count=1,
        rows=(
            service.OperationalAssessmentMarkExportRow(
                assessment_id=100,
                assessment_title="Physics Operational Test",
                candidate_id=201,
                candidate_number="PHY-001",
                student_id=401,
                student_name="Alice Student",
                student_email="alice@example.com",
                script_id=301,
                script_version=1,
                script_status=AssessmentScriptStatus.MARKED,
                is_latest_script=True,
                response_count=8,
                decision_count=8,
                mark_awarded=Decimal("43.50"),
                maximum_mark=Decimal("80.00"),
                percentage=Decimal("54.38"),
                completed_decision_count=6,
                finalised_decision_count=4,
                marking_completion_percentage=Decimal("75.00"),
                finalisation_completion_percentage=Decimal("50.00"),
                is_fully_marked=False,
                is_fully_finalised=False,
            ),
        ),
    )

    csv_content = service.render_operational_assessment_marks_csv(
        export,
    )

    assert (
        "assessment_id,assessment_title,candidate_id," "candidate_number"
    ) in csv_content

    assert "Alice Student" in csv_content
    assert "alice@example.com" in csv_content
    assert "PHY-001" in csv_content

    assert "43.50" in csv_content
    assert "54.38" in csv_content
    assert "75.00" in csv_content
    assert "50.00" in csv_content

    assert "marked" in csv_content
    assert "true" in csv_content
    assert "false" in csv_content


def test_csv_escapes_text_and_renders_none_as_blank():
    export = service.OperationalAssessmentMarksExport(
        assessment_id=100,
        assessment_title="Physics, Forces",
        assessment_status=AssessmentStatus.DRAFT,
        maximum_mark=Decimal("80.00"),
        markable_question_count=8,
        candidate_count=1,
        script_count=1,
        rows=(
            service.OperationalAssessmentMarkExportRow(
                assessment_id=100,
                assessment_title="Physics, Forces",
                candidate_id=201,
                candidate_number=None,
                student_id=401,
                student_name='Alice "A" Student',
                student_email=None,
                script_id=301,
                script_version=1,
                script_status=AssessmentScriptStatus.MARKED,
                is_latest_script=True,
                response_count=0,
                decision_count=0,
                mark_awarded=Decimal("0"),
                maximum_mark=Decimal("80.00"),
                percentage=None,
                completed_decision_count=0,
                finalised_decision_count=0,
                marking_completion_percentage=None,
                finalisation_completion_percentage=None,
                is_fully_marked=False,
                is_fully_finalised=False,
            ),
        ),
    )

    csv_content = service.render_operational_assessment_marks_csv(
        export,
    )

    assert '"Physics, Forces"' in csv_content
    assert '"Alice ""A"" Student"' in csv_content

    # Optional values render as empty CSV cells.
    assert ",,401," in csv_content


def test_operational_filename_is_safe():
    export = service.OperationalAssessmentMarksExport(
        assessment_id=100,
        assessment_title="Physics / Forces: Test?",
        assessment_status=AssessmentStatus.DRAFT,
        maximum_mark=Decimal("80.00"),
        markable_question_count=8,
        candidate_count=0,
        script_count=0,
        rows=(),
    )

    filename = service.build_operational_assessment_marks_filename(
        export,
    )

    assert filename == ("assessment_100_" "Physics-Forces-Test_operational_marks.csv")
