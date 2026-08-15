from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

import pytest

import app.services.assessment_result_pdf_export_service as service
from app.models.assessment_result_outcome import (
    AssessmentResultChangeType,
)
from app.services.assessment_result_export_service import (
    OfficialAssessmentResultExport,
    OfficialAssessmentResultExportRow,
)

# ---------------------------------------------------------------------------
# Test-data helpers
# ---------------------------------------------------------------------------


def _row(
    *,
    outcome_id: int = 501,
    candidate_id: int = 201,
    candidate_number: str | None = "PHY001",
    student_id: int = 401,
    student_name: str | None = "Alice Student",
    student_email: str | None = "alice@example.com",
    script_id: int = 301,
    script_version: int = 1,
    outcome_version: int = 1,
    change_type: AssessmentResultChangeType = (AssessmentResultChangeType.INITIAL),
    mark_awarded: Decimal | None = Decimal("72.00"),
    maximum_mark: Decimal | None = Decimal("80.00"),
    percentage: Decimal | None = Decimal("90.00"),
    grade_label: str | None = "9",
    grade_points: Decimal | None = Decimal("9.00"),
    is_pass: bool | None = True,
) -> OfficialAssessmentResultExportRow:
    return OfficialAssessmentResultExportRow(
        outcome_id=outcome_id,
        assessment_id=100,
        assessment_title="Physics Forces Test",
        candidate_id=candidate_id,
        candidate_number=candidate_number,
        student_id=student_id,
        student_name=student_name,
        student_email=student_email,
        script_id=script_id,
        script_version=script_version,
        outcome_version=outcome_version,
        change_type=change_type,
        mark_awarded=mark_awarded,
        maximum_mark=maximum_mark,
        percentage=percentage,
        grading_scheme_name="GCSE 9-1",
        grading_basis="percentage",
        grade_label=grade_label,
        grade_points=grade_points,
        is_pass=is_pass,
        effective_at=datetime(
            2026,
            8,
            15,
            12,
            0,
            tzinfo=timezone.utc,
        ),
        recorded_by_id=10,
        recorded_at=datetime(
            2026,
            8,
            15,
            12,
            1,
            tzinfo=timezone.utc,
        ),
    )


def _export(
    *,
    rows: tuple[OfficialAssessmentResultExportRow, ...] | None = None,
    assessment_title: str = "Physics Forces Test",
) -> OfficialAssessmentResultExport:
    if rows is None:
        rows = (_row(),)

    return OfficialAssessmentResultExport(
        assessment_id=100,
        assessment_title=assessment_title,
        school_id=1,
        candidate_count=1,
        authoritative_result_count=len(
            rows,
        ),
        rows=rows,
    )


# ---------------------------------------------------------------------------
# Filename
# ---------------------------------------------------------------------------


def test_build_official_pdf_filename():
    export = _export()

    filename = service.build_official_assessment_results_pdf_filename(
        export,
    )

    assert filename == ("assessment_100_" "Physics-Forces-Test_official_results.pdf")


def test_build_official_pdf_filename_is_safe():
    export = _export(
        assessment_title="Physics / Forces: Test?",
    )

    filename = service.build_official_assessment_results_pdf_filename(
        export,
    )

    assert filename == ("assessment_100_" "Physics-Forces-Test_official_results.pdf")

    assert "/" not in filename
    assert ":" not in filename
    assert "?" not in filename


# ---------------------------------------------------------------------------
# Pure PDF renderer
# ---------------------------------------------------------------------------


def test_renderer_generates_valid_pdf():
    pdf_bytes = service.generate_official_assessment_results_pdf_bytes(
        _export(),
        school_name="MHike School",
    )

    assert isinstance(
        pdf_bytes,
        bytes,
    )

    assert pdf_bytes.startswith(
        b"%PDF",
    )

    assert (
        len(
            pdf_bytes,
        )
        > 100
    )


def test_renderer_supports_empty_authoritative_result_set():
    export = OfficialAssessmentResultExport(
        assessment_id=100,
        assessment_title="Empty Assessment",
        school_id=1,
        candidate_count=3,
        authoritative_result_count=0,
        rows=(),
    )

    pdf_bytes = service.generate_official_assessment_results_pdf_bytes(
        export,
        school_name="MHike School",
    )

    assert pdf_bytes.startswith(
        b"%PDF",
    )


def test_renderer_supports_missing_optional_result_values():
    export = _export(
        rows=(
            _row(
                candidate_number=None,
                student_name=None,
                mark_awarded=None,
                maximum_mark=None,
                percentage=None,
                grade_label=None,
                grade_points=None,
                is_pass=None,
            ),
        ),
    )

    pdf_bytes = service.generate_official_assessment_results_pdf_bytes(
        export,
        school_name="MHike School",
    )

    assert pdf_bytes.startswith(
        b"%PDF",
    )


def test_renderer_rejects_blank_school_name():
    with pytest.raises(
        ValueError,
        match="school_name is required",
    ):
        service.generate_official_assessment_results_pdf_bytes(
            _export(),
            school_name="   ",
        )


# ---------------------------------------------------------------------------
# School lookup
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_school_name_returns_school_name():
    class _Result:
        def scalar_one_or_none(
            self,
        ):
            return "MHike School"

    class _Db:
        async def execute(
            self,
            statement,
        ):
            return _Result()

    school_name = await service._get_school_name(
        _Db(),
        school_id=1,
    )

    assert school_name == "MHike School"


@pytest.mark.asyncio
async def test_get_school_name_rejects_missing_school():
    class _Result:
        def scalar_one_or_none(
            self,
        ):
            return None

    class _Db:
        async def execute(
            self,
            statement,
        ):
            return _Result()

    with pytest.raises(
        RuntimeError,
        match="could not be loaded",
    ):
        await service._get_school_name(
            _Db(),
            school_id=999,
        )


@pytest.mark.asyncio
async def test_get_school_name_rejects_blank_school_name():
    class _Result:
        def scalar_one_or_none(
            self,
        ):
            return "   "

    class _Db:
        async def execute(
            self,
            statement,
        ):
            return _Result()

    with pytest.raises(
        RuntimeError,
        match="without a usable name",
    ):
        await service._get_school_name(
            _Db(),
            school_id=1,
        )


# ---------------------------------------------------------------------------
# End-to-end service orchestration
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_pdf_service_reuses_official_export_service(
    monkeypatch,
):
    export = _export()

    calls = {}

    async def fake_get_export(
        db,
        current_user,
        *,
        assessment_id,
    ):
        calls["db"] = db
        calls["current_user"] = current_user
        calls["assessment_id"] = assessment_id

        return export

    async def fake_get_school_name(
        db,
        *,
        school_id,
    ):
        calls["school_id"] = school_id

        return "MHike School"

    monkeypatch.setattr(
        service,
        "get_official_assessment_result_export",
        fake_get_export,
    )

    monkeypatch.setattr(
        service,
        "_get_school_name",
        fake_get_school_name,
    )

    db = object()
    current_user = object()

    returned_export, pdf_bytes = await service.get_official_assessment_results_pdf(
        db,
        current_user,
        assessment_id=100,
    )

    assert returned_export is export

    assert calls["db"] is db
    assert calls["current_user"] is current_user
    assert calls["assessment_id"] == 100
    assert calls["school_id"] == 1

    assert pdf_bytes.startswith(
        b"%PDF",
    )


@pytest.mark.asyncio
async def test_pdf_service_preserves_official_export_errors(
    monkeypatch,
):
    async def fake_get_export(
        db,
        current_user,
        *,
        assessment_id,
    ):
        raise RuntimeError(
            "official export failed",
        )

    monkeypatch.setattr(
        service,
        "get_official_assessment_result_export",
        fake_get_export,
    )

    with pytest.raises(
        RuntimeError,
        match="official export failed",
    ):
        await service.get_official_assessment_results_pdf(
            object(),
            object(),
            assessment_id=100,
        )
