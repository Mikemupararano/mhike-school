from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

import pytest
from fastapi import HTTPException
from httpx import AsyncClient

import app.api.v1.endpoints.assessment_result_exports as endpoint
from app.models.assessment import AssessmentStatus
from app.models.assessment_candidate import AssessmentScriptStatus
from app.models.assessment_result_outcome import (
    AssessmentResultChangeType,
)
from app.services.assessment_operational_marks_export_service import (
    OperationalAssessmentMarkExportRow,
    OperationalAssessmentMarksExport,
)
from app.services.assessment_result_export_service import (
    OfficialAssessmentResultExport,
    OfficialAssessmentResultExportRow,
)

# ---------------------------------------------------------------------------
# Test-data helpers
# ---------------------------------------------------------------------------


def _official_export(
    *,
    assessment_id: int = 100,
    assessment_title: str = "Physics Forces Test",
) -> OfficialAssessmentResultExport:
    row = OfficialAssessmentResultExportRow(
        outcome_id=501,
        assessment_id=assessment_id,
        assessment_title=assessment_title,
        candidate_id=201,
        candidate_number="PHY001",
        student_id=401,
        student_name="Alice Student",
        student_email="alice@example.com",
        script_id=301,
        script_version=1,
        outcome_version=1,
        change_type=AssessmentResultChangeType.INITIAL,
        mark_awarded=Decimal("72"),
        maximum_mark=Decimal("80"),
        percentage=Decimal("90.00"),
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

    return OfficialAssessmentResultExport(
        assessment_id=assessment_id,
        assessment_title=assessment_title,
        school_id=1,
        candidate_count=1,
        authoritative_result_count=1,
        rows=(row,),
    )


def _operational_export(
    *,
    assessment_id: int = 100,
    assessment_title: str = "Physics Forces Test",
) -> OperationalAssessmentMarksExport:
    row = OperationalAssessmentMarkExportRow(
        assessment_id=assessment_id,
        assessment_title=assessment_title,
        candidate_id=201,
        candidate_number="PHY001",
        student_id=401,
        student_name="Alice Student",
        student_email="alice@example.com",
        script_id=301,
        script_version=2,
        script_status=AssessmentScriptStatus.MARKED,
        is_latest_script=True,
        response_count=8,
        decision_count=8,
        mark_awarded=Decimal("45.00"),
        maximum_mark=Decimal("80.00"),
        percentage=Decimal("56.25"),
        completed_decision_count=8,
        finalised_decision_count=4,
        marking_completion_percentage=Decimal("100.00"),
        finalisation_completion_percentage=Decimal("50.00"),
        is_fully_marked=True,
        is_fully_finalised=False,
    )

    return OperationalAssessmentMarksExport(
        assessment_id=assessment_id,
        assessment_title=assessment_title,
        assessment_status=AssessmentStatus.DRAFT,
        maximum_mark=Decimal("80.00"),
        markable_question_count=8,
        candidate_count=1,
        script_count=1,
        rows=(row,),
    )


def _http_error(
    message: str,
) -> dict:
    """
    Return the application's standard HTTP-error response envelope.
    """

    return {
        "success": False,
        "error": {
            "code": "HTTP_ERROR",
            "message": message,
        },
    }


# ---------------------------------------------------------------------------
# Successful official CSV export
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_staff_can_download_official_assessment_results_csv(
    client: AsyncClient,
    school_admin_user,
    auth_headers,
    monkeypatch,
):
    calls: list[tuple[int, int]] = []

    async def fake_get_export(
        db,
        current_user,
        *,
        assessment_id,
    ):
        calls.append(
            (
                current_user.id,
                assessment_id,
            )
        )

        return _official_export(
            assessment_id=assessment_id,
        )

    monkeypatch.setattr(
        endpoint,
        "get_official_assessment_result_export",
        fake_get_export,
    )

    response = await client.get(
        ("/api/v1/assessment-result-exports/" "assessments/100/official.csv"),
        headers=auth_headers(
            school_admin_user,
        ),
    )

    assert response.status_code == 200

    assert response.headers["content-type"].startswith(
        "text/csv",
    )

    assert "attachment" in response.headers["content-disposition"]

    assert (
        "assessment_100_"
        "Physics-Forces-Test_official_results.csv"
        in response.headers["content-disposition"]
    )

    assert (
        school_admin_user.id,
        100,
    ) in calls

    csv_text = response.text

    assert (
        "outcome_id,assessment_id,assessment_title,"
        "candidate_id,candidate_number" in csv_text
    )

    assert "Alice Student" in csv_text
    assert "alice@example.com" in csv_text
    assert "72" in csv_text
    assert "80" in csv_text
    assert "90.00" in csv_text
    assert "GCSE 9-1" in csv_text
    assert ",9," in csv_text


# ---------------------------------------------------------------------------
# Empty authoritative-result set
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_export_allows_assessment_with_no_authoritative_results(
    client: AsyncClient,
    school_admin_user,
    auth_headers,
    monkeypatch,
):
    async def fake_get_export(
        db,
        current_user,
        *,
        assessment_id,
    ):
        return OfficialAssessmentResultExport(
            assessment_id=assessment_id,
            assessment_title="Empty Assessment",
            school_id=school_admin_user.school_id,
            candidate_count=3,
            authoritative_result_count=0,
            rows=(),
        )

    monkeypatch.setattr(
        endpoint,
        "get_official_assessment_result_export",
        fake_get_export,
    )

    response = await client.get(
        ("/api/v1/assessment-result-exports/" "assessments/100/official.csv"),
        headers=auth_headers(
            school_admin_user,
        ),
    )

    assert response.status_code == 200

    assert response.headers["content-type"].startswith(
        "text/csv",
    )

    lines = response.text.splitlines()

    assert (
        len(
            lines,
        )
        == 1
    )

    assert lines[0].startswith("outcome_id,assessment_id,assessment_title,")


# ---------------------------------------------------------------------------
# Existing official-service errors propagate through global API envelope
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_export_propagates_assessment_not_found(
    client: AsyncClient,
    school_admin_user,
    auth_headers,
    monkeypatch,
):
    async def fake_get_export(
        db,
        current_user,
        *,
        assessment_id,
    ):
        raise HTTPException(
            status_code=404,
            detail="Assessment not found",
        )

    monkeypatch.setattr(
        endpoint,
        "get_official_assessment_result_export",
        fake_get_export,
    )

    response = await client.get(
        ("/api/v1/assessment-result-exports/" "assessments/999/official.csv"),
        headers=auth_headers(
            school_admin_user,
        ),
    )

    assert response.status_code == 404

    assert response.json() == _http_error(
        "Assessment not found",
    )


@pytest.mark.asyncio
async def test_export_propagates_cross_school_access_denial(
    client: AsyncClient,
    school_admin_user,
    auth_headers,
    monkeypatch,
):
    async def fake_get_export(
        db,
        current_user,
        *,
        assessment_id,
    ):
        raise HTTPException(
            status_code=403,
            detail="Assessment does not belong to your school",
        )

    monkeypatch.setattr(
        endpoint,
        "get_official_assessment_result_export",
        fake_get_export,
    )

    response = await client.get(
        ("/api/v1/assessment-result-exports/" "assessments/100/official.csv"),
        headers=auth_headers(
            school_admin_user,
        ),
    )

    assert response.status_code == 403

    assert response.json() == _http_error(
        "Assessment does not belong to your school",
    )


@pytest.mark.asyncio
async def test_export_propagates_unrelated_teacher_access_denial(
    client: AsyncClient,
    teacher_user,
    auth_headers,
    monkeypatch,
):
    async def fake_get_export(
        db,
        current_user,
        *,
        assessment_id,
    ):
        raise HTTPException(
            status_code=403,
            detail=("You can only view results for your own courses"),
        )

    monkeypatch.setattr(
        endpoint,
        "get_official_assessment_result_export",
        fake_get_export,
    )

    response = await client.get(
        ("/api/v1/assessment-result-exports/" "assessments/100/official.csv"),
        headers=auth_headers(
            teacher_user,
        ),
    )

    assert response.status_code == 403

    assert response.json() == _http_error(
        "You can only view results for your own courses",
    )


# ---------------------------------------------------------------------------
# Official-export authentication
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_official_results_export_requires_authentication(
    client: AsyncClient,
):
    response = await client.get(
        ("/api/v1/assessment-result-exports/" "assessments/100/official.csv"),
    )

    assert response.status_code in {
        401,
        403,
    }


# ---------------------------------------------------------------------------
# Successful operational CSV export
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_staff_can_download_operational_assessment_marks_csv(
    client: AsyncClient,
    school_admin_user,
    auth_headers,
    monkeypatch,
):
    calls: list[tuple[int, int]] = []

    async def fake_get_export(
        db,
        current_user,
        *,
        assessment_id,
    ):
        calls.append(
            (
                current_user.id,
                assessment_id,
            )
        )

        return _operational_export(
            assessment_id=assessment_id,
        )

    monkeypatch.setattr(
        endpoint,
        "get_operational_assessment_marks_export",
        fake_get_export,
    )

    response = await client.get(
        ("/api/v1/assessment-result-exports/" "assessments/100/operational.csv"),
        headers=auth_headers(
            school_admin_user,
        ),
    )

    assert response.status_code == 200

    assert response.headers["content-type"].startswith(
        "text/csv",
    )

    assert "attachment" in response.headers["content-disposition"]

    assert (
        "assessment_100_"
        "Physics-Forces-Test_operational_marks.csv"
        in response.headers["content-disposition"]
    )

    assert (
        school_admin_user.id,
        100,
    ) in calls

    csv_text = response.text

    assert "assessment_id,assessment_title,candidate_id," "candidate_number" in csv_text

    assert "Alice Student" in csv_text
    assert "alice@example.com" in csv_text
    assert "PHY001" in csv_text

    assert "45.00" in csv_text
    assert "80.00" in csv_text
    assert "56.25" in csv_text

    assert "marked" in csv_text
    assert "100.00" in csv_text
    assert "50.00" in csv_text


# ---------------------------------------------------------------------------
# Empty operational script set
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_operational_export_allows_assessment_with_no_scripts(
    client: AsyncClient,
    school_admin_user,
    auth_headers,
    monkeypatch,
):
    async def fake_get_export(
        db,
        current_user,
        *,
        assessment_id,
    ):
        return OperationalAssessmentMarksExport(
            assessment_id=assessment_id,
            assessment_title="Empty Assessment",
            assessment_status=AssessmentStatus.DRAFT,
            maximum_mark=Decimal("80.00"),
            markable_question_count=8,
            candidate_count=3,
            script_count=0,
            rows=(),
        )

    monkeypatch.setattr(
        endpoint,
        "get_operational_assessment_marks_export",
        fake_get_export,
    )

    response = await client.get(
        ("/api/v1/assessment-result-exports/" "assessments/100/operational.csv"),
        headers=auth_headers(
            school_admin_user,
        ),
    )

    assert response.status_code == 200

    assert response.headers["content-type"].startswith(
        "text/csv",
    )

    lines = response.text.splitlines()

    assert (
        len(
            lines,
        )
        == 1
    )

    assert lines[0].startswith("assessment_id,assessment_title,candidate_id,")


# ---------------------------------------------------------------------------
# Operational-service errors propagate through global API envelope
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_operational_export_propagates_assessment_not_found(
    client: AsyncClient,
    school_admin_user,
    auth_headers,
    monkeypatch,
):
    async def fake_get_export(
        db,
        current_user,
        *,
        assessment_id,
    ):
        raise HTTPException(
            status_code=404,
            detail="Assessment not found",
        )

    monkeypatch.setattr(
        endpoint,
        "get_operational_assessment_marks_export",
        fake_get_export,
    )

    response = await client.get(
        ("/api/v1/assessment-result-exports/" "assessments/999/operational.csv"),
        headers=auth_headers(
            school_admin_user,
        ),
    )

    assert response.status_code == 404

    assert response.json() == _http_error(
        "Assessment not found",
    )


@pytest.mark.asyncio
async def test_operational_export_propagates_cross_school_access_denial(
    client: AsyncClient,
    school_admin_user,
    auth_headers,
    monkeypatch,
):
    async def fake_get_export(
        db,
        current_user,
        *,
        assessment_id,
    ):
        raise HTTPException(
            status_code=403,
            detail="Assessment does not belong to your school",
        )

    monkeypatch.setattr(
        endpoint,
        "get_operational_assessment_marks_export",
        fake_get_export,
    )

    response = await client.get(
        ("/api/v1/assessment-result-exports/" "assessments/100/operational.csv"),
        headers=auth_headers(
            school_admin_user,
        ),
    )

    assert response.status_code == 403

    assert response.json() == _http_error(
        "Assessment does not belong to your school",
    )


@pytest.mark.asyncio
async def test_operational_export_propagates_unrelated_teacher_access_denial(
    client: AsyncClient,
    teacher_user,
    auth_headers,
    monkeypatch,
):
    async def fake_get_export(
        db,
        current_user,
        *,
        assessment_id,
    ):
        raise HTTPException(
            status_code=403,
            detail=("You can only view results for your own courses"),
        )

    monkeypatch.setattr(
        endpoint,
        "get_operational_assessment_marks_export",
        fake_get_export,
    )

    response = await client.get(
        ("/api/v1/assessment-result-exports/" "assessments/100/operational.csv"),
        headers=auth_headers(
            teacher_user,
        ),
    )

    assert response.status_code == 403

    assert response.json() == _http_error(
        "You can only view results for your own courses",
    )


# ---------------------------------------------------------------------------
# Operational-export authentication
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_operational_marks_export_requires_authentication(
    client: AsyncClient,
):
    response = await client.get(
        ("/api/v1/assessment-result-exports/" "assessments/100/operational.csv"),
    )

    assert response.status_code in {
        401,
        403,
    }


# ---------------------------------------------------------------------------
# Successful official PDF export
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_staff_can_download_official_assessment_results_pdf(
    client: AsyncClient,
    school_admin_user,
    auth_headers,
    monkeypatch,
):
    calls: list[tuple[int, int]] = []

    pdf_bytes = b"%PDF-1.4\n" b"MHike School assessment results test PDF\n"

    async def fake_get_pdf(
        db,
        current_user,
        *,
        assessment_id,
    ):
        calls.append(
            (
                current_user.id,
                assessment_id,
            )
        )

        return (
            _official_export(
                assessment_id=assessment_id,
            ),
            pdf_bytes,
        )

    monkeypatch.setattr(
        endpoint,
        "get_official_assessment_results_pdf",
        fake_get_pdf,
    )

    response = await client.get(
        ("/api/v1/assessment-result-exports/" "assessments/100/official.pdf"),
        headers=auth_headers(
            school_admin_user,
        ),
    )

    assert response.status_code == 200

    assert response.headers["content-type"].startswith(
        "application/pdf",
    )

    assert "attachment" in response.headers["content-disposition"]

    assert (
        "assessment_100_"
        "Physics-Forces-Test_official_results.pdf"
        in response.headers["content-disposition"]
    )

    assert response.headers["cache-control"] == ("private, no-store")

    assert response.content == pdf_bytes

    assert response.content.startswith(
        b"%PDF",
    )

    assert (
        school_admin_user.id,
        100,
    ) in calls


@pytest.mark.asyncio
async def test_official_pdf_sets_content_length(
    client: AsyncClient,
    school_admin_user,
    auth_headers,
    monkeypatch,
):
    pdf_bytes = b"%PDF-1.4\n" b"1234567890"

    async def fake_get_pdf(
        db,
        current_user,
        *,
        assessment_id,
    ):
        return (
            _official_export(
                assessment_id=assessment_id,
            ),
            pdf_bytes,
        )

    monkeypatch.setattr(
        endpoint,
        "get_official_assessment_results_pdf",
        fake_get_pdf,
    )

    response = await client.get(
        ("/api/v1/assessment-result-exports/" "assessments/100/official.pdf"),
        headers=auth_headers(
            school_admin_user,
        ),
    )

    assert response.status_code == 200

    assert response.headers["content-length"] == str(
        len(
            pdf_bytes,
        )
    )

    assert len(
        response.content,
    ) == len(
        pdf_bytes,
    )


# ---------------------------------------------------------------------------
# Official PDF errors propagate through global API envelope
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_official_pdf_propagates_assessment_not_found(
    client: AsyncClient,
    school_admin_user,
    auth_headers,
    monkeypatch,
):
    async def fake_get_pdf(
        db,
        current_user,
        *,
        assessment_id,
    ):
        raise HTTPException(
            status_code=404,
            detail="Assessment not found",
        )

    monkeypatch.setattr(
        endpoint,
        "get_official_assessment_results_pdf",
        fake_get_pdf,
    )

    response = await client.get(
        ("/api/v1/assessment-result-exports/" "assessments/999/official.pdf"),
        headers=auth_headers(
            school_admin_user,
        ),
    )

    assert response.status_code == 404

    assert response.json() == _http_error(
        "Assessment not found",
    )


@pytest.mark.asyncio
async def test_official_pdf_propagates_cross_school_access_denial(
    client: AsyncClient,
    school_admin_user,
    auth_headers,
    monkeypatch,
):
    async def fake_get_pdf(
        db,
        current_user,
        *,
        assessment_id,
    ):
        raise HTTPException(
            status_code=403,
            detail="Assessment does not belong to your school",
        )

    monkeypatch.setattr(
        endpoint,
        "get_official_assessment_results_pdf",
        fake_get_pdf,
    )

    response = await client.get(
        ("/api/v1/assessment-result-exports/" "assessments/100/official.pdf"),
        headers=auth_headers(
            school_admin_user,
        ),
    )

    assert response.status_code == 403

    assert response.json() == _http_error(
        "Assessment does not belong to your school",
    )


@pytest.mark.asyncio
async def test_official_pdf_propagates_unrelated_teacher_access_denial(
    client: AsyncClient,
    teacher_user,
    auth_headers,
    monkeypatch,
):
    async def fake_get_pdf(
        db,
        current_user,
        *,
        assessment_id,
    ):
        raise HTTPException(
            status_code=403,
            detail=("You can only view results for your own courses"),
        )

    monkeypatch.setattr(
        endpoint,
        "get_official_assessment_results_pdf",
        fake_get_pdf,
    )

    response = await client.get(
        ("/api/v1/assessment-result-exports/" "assessments/100/official.pdf"),
        headers=auth_headers(
            teacher_user,
        ),
    )

    assert response.status_code == 403

    assert response.json() == _http_error(
        "You can only view results for your own courses",
    )


# ---------------------------------------------------------------------------
# Official PDF authentication
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_official_pdf_requires_authentication(
    client: AsyncClient,
):
    response = await client.get(
        ("/api/v1/assessment-result-exports/" "assessments/100/official.pdf"),
    )

    assert response.status_code in {
        401,
        403,
    }
