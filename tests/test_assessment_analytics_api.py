from __future__ import annotations

from decimal import Decimal

import pytest
from fastapi import HTTPException
from httpx import AsyncClient

from app.api.v1.endpoints import assessment_analytics as endpoint

FULL_URL = "/api/v1/assessment-analytics/assessments/{assessment_id}"

SUMMARY_URL = "/api/v1/assessment-analytics/assessments/{assessment_id}/summary"

RANKING_URL = "/api/v1/assessment-analytics/assessments/{assessment_id}/ranking"

GRADE_DISTRIBUTION_URL = (
    "/api/v1/assessment-analytics/assessments/" "{assessment_id}/grade-distribution"
)


# ---------------------------------------------------------------------------
# Payload helpers
# ---------------------------------------------------------------------------


def _grade_distribution():
    return [
        {
            "grade": "8",
            "minimum_value": Decimal("75.00"),
            "grade_points": Decimal("8.00"),
            "is_pass": True,
            "count": 2,
            "percentage": Decimal("66.67"),
        },
        {
            "grade": "6",
            "minimum_value": Decimal("55.00"),
            "grade_points": Decimal("6.00"),
            "is_pass": True,
            "count": 1,
            "percentage": Decimal("33.33"),
        },
    ]


def _ranking():
    return [
        {
            "candidate_id": 1,
            "student_id": 101,
            "candidate_number": "A001",
            "candidate_status": "submitted",
            "script_id": 11,
            "script_version": 1,
            "mark_awarded": Decimal("40.00"),
            "maximum_mark": Decimal("50.00"),
            "percentage": Decimal("80.00"),
            "grade": "8",
            "grade_points": Decimal("8.00"),
            "is_pass": True,
            "rank": 1,
        },
        {
            "candidate_id": 2,
            "student_id": 102,
            "candidate_number": "A002",
            "candidate_status": "submitted",
            "script_id": 21,
            "script_version": 1,
            "mark_awarded": Decimal("30.00"),
            "maximum_mark": Decimal("50.00"),
            "percentage": Decimal("60.00"),
            "grade": "6",
            "grade_points": Decimal("6.00"),
            "is_pass": True,
            "rank": 2,
        },
    ]


def _questions():
    return [
        {
            "question_id": 1,
            "question_number": "1",
            "title": "Forces",
            "maximum_mark": Decimal("5.00"),
            "response_count": 3,
            "marked_count": 3,
            "mark_sum": Decimal("12.00"),
            "mark_average": Decimal("4.00"),
            "mark_minimum": Decimal("3.00"),
            "mark_maximum": Decimal("5.00"),
            "average_percentage": Decimal("80.00"),
        },
    ]


def _full_payload(
    *,
    assessment_id: int = 100,
):
    return {
        "assessment_id": assessment_id,
        "title": "Mechanics End of Topic Test",
        "status": "published",
        "result_stage": "finalised",
        "script_selection": "latest",
        "maximum_mark": Decimal("50.00"),
        "markable_question_count": 5,
        "candidate_count": 3,
        "script_count": 3,
        "candidates_with_script": 3,
        "candidates_without_script": 0,
        "fully_marked_candidate_count": 3,
        "fully_finalised_candidate_count": 3,
        "included_candidate_count": 3,
        "excluded_incomplete_candidate_count": 0,
        "candidate_inclusion_percentage": Decimal("100.00"),
        "marking_completion_percentage": Decimal("100.00"),
        "finalisation_completion_percentage": Decimal("100.00"),
        "mean_mark": Decimal("35.00"),
        "median_mark": Decimal("35.00"),
        "lowest_mark": Decimal("30.00"),
        "highest_mark": Decimal("40.00"),
        "mean_percentage": Decimal("70.00"),
        "median_percentage": Decimal("70.00"),
        "lowest_percentage": Decimal("60.00"),
        "highest_percentage": Decimal("80.00"),
        "graded_candidate_count": 3,
        "ungraded_candidate_count": 0,
        "pass_count": 3,
        "fail_count": 0,
        "pass_percentage": Decimal("100.00"),
        "grade_distribution": _grade_distribution(),
        "ranking": _ranking(),
        "questions": _questions(),
    }


def _summary_payload(
    *,
    assessment_id: int = 100,
):
    payload = _full_payload(
        assessment_id=assessment_id,
    )

    payload.pop(
        "ranking",
    )

    payload.pop(
        "questions",
    )

    return payload


def _grade_distribution_payload(
    *,
    assessment_id: int = 100,
):
    return {
        "assessment_id": assessment_id,
        "graded_candidate_count": 3,
        "ungraded_candidate_count": 0,
        "pass_count": 3,
        "fail_count": 0,
        "pass_percentage": Decimal("100.00"),
        "grades": _grade_distribution(),
    }


# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_full_analytics_requires_authentication(
    client: AsyncClient,
):
    response = await client.get(
        FULL_URL.format(
            assessment_id=100,
        ),
    )

    assert response.status_code in {
        401,
        403,
    }


@pytest.mark.asyncio
async def test_summary_requires_authentication(
    client: AsyncClient,
):
    response = await client.get(
        SUMMARY_URL.format(
            assessment_id=100,
        ),
    )

    assert response.status_code in {
        401,
        403,
    }


@pytest.mark.asyncio
async def test_ranking_requires_authentication(
    client: AsyncClient,
):
    response = await client.get(
        RANKING_URL.format(
            assessment_id=100,
        ),
    )

    assert response.status_code in {
        401,
        403,
    }


@pytest.mark.asyncio
async def test_grade_distribution_requires_authentication(
    client: AsyncClient,
):
    response = await client.get(
        GRADE_DISTRIBUTION_URL.format(
            assessment_id=100,
        ),
    )

    assert response.status_code in {
        401,
        403,
    }


# ---------------------------------------------------------------------------
# Full analytics
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_teacher_can_get_full_assessment_analytics(
    client: AsyncClient,
    teacher_user,
    auth_headers,
    monkeypatch,
):
    async def fake_service(
        *,
        db,
        current_user,
        assessment_id,
    ):
        assert current_user.id == teacher_user.id
        assert assessment_id == 100

        return _full_payload(
            assessment_id=assessment_id,
        )

    monkeypatch.setattr(
        endpoint,
        "get_assessment_analytics",
        fake_service,
    )

    response = await client.get(
        FULL_URL.format(
            assessment_id=100,
        ),
        headers=auth_headers(
            teacher_user,
        ),
    )

    assert response.status_code == 200, response.text

    payload = response.json()

    assert payload["assessment_id"] == 100
    assert payload["title"] == "Mechanics End of Topic Test"
    assert payload["result_stage"] == "finalised"
    assert payload["script_selection"] == "latest"

    assert Decimal(
        str(
            payload["mean_mark"],
        )
    ) == Decimal("35.00")

    assert Decimal(
        str(
            payload["mean_percentage"],
        )
    ) == Decimal("70.00")

    assert (
        len(
            payload["ranking"],
        )
        == 2
    )

    assert (
        len(
            payload["questions"],
        )
        == 1
    )


@pytest.mark.asyncio
async def test_full_analytics_passes_assessment_id_to_service(
    client: AsyncClient,
    teacher_user,
    auth_headers,
    monkeypatch,
):
    received_ids: list[int] = []

    async def fake_service(
        *,
        db,
        current_user,
        assessment_id,
    ):
        received_ids.append(
            assessment_id,
        )

        return _full_payload(
            assessment_id=assessment_id,
        )

    monkeypatch.setattr(
        endpoint,
        "get_assessment_analytics",
        fake_service,
    )

    response = await client.get(
        FULL_URL.format(
            assessment_id=777,
        ),
        headers=auth_headers(
            teacher_user,
        ),
    )

    assert response.status_code == 200, response.text
    assert received_ids == [777]
    assert response.json()["assessment_id"] == 777


@pytest.mark.asyncio
async def test_full_analytics_serialises_grade_distribution(
    client: AsyncClient,
    teacher_user,
    auth_headers,
    monkeypatch,
):
    async def fake_service(
        *,
        db,
        current_user,
        assessment_id,
    ):
        return _full_payload(
            assessment_id=assessment_id,
        )

    monkeypatch.setattr(
        endpoint,
        "get_assessment_analytics",
        fake_service,
    )

    response = await client.get(
        FULL_URL.format(
            assessment_id=100,
        ),
        headers=auth_headers(
            teacher_user,
        ),
    )

    assert response.status_code == 200, response.text

    grades = response.json()["grade_distribution"]

    assert grades[0]["grade"] == "8"
    assert grades[0]["count"] == 2

    assert Decimal(
        str(
            grades[0]["percentage"],
        )
    ) == Decimal("66.67")


@pytest.mark.asyncio
async def test_full_analytics_serialises_candidate_ranking(
    client: AsyncClient,
    teacher_user,
    auth_headers,
    monkeypatch,
):
    async def fake_service(
        *,
        db,
        current_user,
        assessment_id,
    ):
        return _full_payload(
            assessment_id=assessment_id,
        )

    monkeypatch.setattr(
        endpoint,
        "get_assessment_analytics",
        fake_service,
    )

    response = await client.get(
        FULL_URL.format(
            assessment_id=100,
        ),
        headers=auth_headers(
            teacher_user,
        ),
    )

    assert response.status_code == 200, response.text

    ranking = response.json()["ranking"]

    assert ranking[0]["candidate_id"] == 1
    assert ranking[0]["rank"] == 1
    assert ranking[1]["candidate_id"] == 2
    assert ranking[1]["rank"] == 2


# ---------------------------------------------------------------------------
# Compact summary
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_teacher_can_get_compact_analytics_summary(
    client: AsyncClient,
    teacher_user,
    auth_headers,
    monkeypatch,
):
    async def fake_service(
        *,
        db,
        current_user,
        assessment_id,
    ):
        return _summary_payload(
            assessment_id=assessment_id,
        )

    monkeypatch.setattr(
        endpoint,
        "get_assessment_analytics_summary",
        fake_service,
    )

    response = await client.get(
        SUMMARY_URL.format(
            assessment_id=100,
        ),
        headers=auth_headers(
            teacher_user,
        ),
    )

    assert response.status_code == 200, response.text

    payload = response.json()

    assert payload["assessment_id"] == 100
    assert payload["candidate_count"] == 3

    assert "ranking" not in payload
    assert "questions" not in payload


@pytest.mark.asyncio
async def test_summary_passes_assessment_id_to_service(
    client: AsyncClient,
    teacher_user,
    auth_headers,
    monkeypatch,
):
    received_ids: list[int] = []

    async def fake_service(
        *,
        db,
        current_user,
        assessment_id,
    ):
        received_ids.append(
            assessment_id,
        )

        return _summary_payload(
            assessment_id=assessment_id,
        )

    monkeypatch.setattr(
        endpoint,
        "get_assessment_analytics_summary",
        fake_service,
    )

    response = await client.get(
        SUMMARY_URL.format(
            assessment_id=321,
        ),
        headers=auth_headers(
            teacher_user,
        ),
    )

    assert response.status_code == 200, response.text
    assert received_ids == [321]


# ---------------------------------------------------------------------------
# Ranking
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_teacher_can_get_candidate_ranking(
    client: AsyncClient,
    teacher_user,
    auth_headers,
    monkeypatch,
):
    async def fake_service(
        *,
        db,
        current_user,
        assessment_id,
    ):
        assert assessment_id == 100
        return _ranking()

    monkeypatch.setattr(
        endpoint,
        "get_assessment_candidate_ranking",
        fake_service,
    )

    response = await client.get(
        RANKING_URL.format(
            assessment_id=100,
        ),
        headers=auth_headers(
            teacher_user,
        ),
    )

    assert response.status_code == 200, response.text

    payload = response.json()

    assert (
        len(
            payload,
        )
        == 2
    )

    assert payload[0]["candidate_id"] == 1
    assert payload[0]["rank"] == 1


@pytest.mark.asyncio
async def test_ranking_can_be_empty(
    client: AsyncClient,
    teacher_user,
    auth_headers,
    monkeypatch,
):
    async def fake_service(
        *,
        db,
        current_user,
        assessment_id,
    ):
        return []

    monkeypatch.setattr(
        endpoint,
        "get_assessment_candidate_ranking",
        fake_service,
    )

    response = await client.get(
        RANKING_URL.format(
            assessment_id=100,
        ),
        headers=auth_headers(
            teacher_user,
        ),
    )

    assert response.status_code == 200, response.text
    assert response.json() == []


# ---------------------------------------------------------------------------
# Grade distribution
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_teacher_can_get_grade_distribution(
    client: AsyncClient,
    teacher_user,
    auth_headers,
    monkeypatch,
):
    async def fake_service(
        *,
        db,
        current_user,
        assessment_id,
    ):
        return _grade_distribution_payload(
            assessment_id=assessment_id,
        )

    monkeypatch.setattr(
        endpoint,
        "get_assessment_grade_distribution",
        fake_service,
    )

    response = await client.get(
        GRADE_DISTRIBUTION_URL.format(
            assessment_id=100,
        ),
        headers=auth_headers(
            teacher_user,
        ),
    )

    assert response.status_code == 200, response.text

    payload = response.json()

    assert payload["assessment_id"] == 100
    assert payload["graded_candidate_count"] == 3
    assert payload["ungraded_candidate_count"] == 0
    assert payload["pass_count"] == 3
    assert payload["fail_count"] == 0

    assert (
        len(
            payload["grades"],
        )
        == 2
    )


@pytest.mark.asyncio
async def test_grade_distribution_can_be_empty_without_active_scheme(
    client: AsyncClient,
    teacher_user,
    auth_headers,
    monkeypatch,
):
    async def fake_service(
        *,
        db,
        current_user,
        assessment_id,
    ):
        return {
            "assessment_id": assessment_id,
            "graded_candidate_count": 0,
            "ungraded_candidate_count": 3,
            "pass_count": 0,
            "fail_count": 0,
            "pass_percentage": None,
            "grades": [],
        }

    monkeypatch.setattr(
        endpoint,
        "get_assessment_grade_distribution",
        fake_service,
    )

    response = await client.get(
        GRADE_DISTRIBUTION_URL.format(
            assessment_id=100,
        ),
        headers=auth_headers(
            teacher_user,
        ),
    )

    assert response.status_code == 200, response.text

    payload = response.json()

    assert payload["graded_candidate_count"] == 0
    assert payload["ungraded_candidate_count"] == 3
    assert payload["pass_percentage"] is None
    assert payload["grades"] == []


# ---------------------------------------------------------------------------
# Error propagation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_full_analytics_propagates_not_found(
    client: AsyncClient,
    teacher_user,
    auth_headers,
    monkeypatch,
):
    async def fake_service(
        *,
        db,
        current_user,
        assessment_id,
    ):
        raise HTTPException(
            status_code=404,
            detail="Assessment not found",
        )

    monkeypatch.setattr(
        endpoint,
        "get_assessment_analytics",
        fake_service,
    )

    response = await client.get(
        FULL_URL.format(
            assessment_id=999,
        ),
        headers=auth_headers(
            teacher_user,
        ),
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_full_analytics_propagates_forbidden(
    client: AsyncClient,
    teacher_user,
    auth_headers,
    monkeypatch,
):
    async def fake_service(
        *,
        db,
        current_user,
        assessment_id,
    ):
        raise HTTPException(
            status_code=403,
            detail="You can only view results for your own courses",
        )

    monkeypatch.setattr(
        endpoint,
        "get_assessment_analytics",
        fake_service,
    )

    response = await client.get(
        FULL_URL.format(
            assessment_id=100,
        ),
        headers=auth_headers(
            teacher_user,
        ),
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_summary_propagates_forbidden(
    client: AsyncClient,
    teacher_user,
    auth_headers,
    monkeypatch,
):
    async def fake_service(
        *,
        db,
        current_user,
        assessment_id,
    ):
        raise HTTPException(
            status_code=403,
            detail="Forbidden.",
        )

    monkeypatch.setattr(
        endpoint,
        "get_assessment_analytics_summary",
        fake_service,
    )

    response = await client.get(
        SUMMARY_URL.format(
            assessment_id=100,
        ),
        headers=auth_headers(
            teacher_user,
        ),
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_ranking_propagates_not_found(
    client: AsyncClient,
    teacher_user,
    auth_headers,
    monkeypatch,
):
    async def fake_service(
        *,
        db,
        current_user,
        assessment_id,
    ):
        raise HTTPException(
            status_code=404,
            detail="Assessment not found",
        )

    monkeypatch.setattr(
        endpoint,
        "get_assessment_candidate_ranking",
        fake_service,
    )

    response = await client.get(
        RANKING_URL.format(
            assessment_id=999,
        ),
        headers=auth_headers(
            teacher_user,
        ),
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_grade_distribution_propagates_forbidden(
    client: AsyncClient,
    teacher_user,
    auth_headers,
    monkeypatch,
):
    async def fake_service(
        *,
        db,
        current_user,
        assessment_id,
    ):
        raise HTTPException(
            status_code=403,
            detail="Forbidden.",
        )

    monkeypatch.setattr(
        endpoint,
        "get_assessment_grade_distribution",
        fake_service,
    )

    response = await client.get(
        GRADE_DISTRIBUTION_URL.format(
            assessment_id=100,
        ),
        headers=auth_headers(
            teacher_user,
        ),
    )

    assert response.status_code == 403


# ---------------------------------------------------------------------------
# Path validation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_full_analytics_assessment_id_must_be_integer(
    client: AsyncClient,
    teacher_user,
    auth_headers,
):
    response = await client.get(
        "/api/v1/assessment-analytics/assessments/not-an-integer",
        headers=auth_headers(
            teacher_user,
        ),
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_summary_assessment_id_must_be_integer(
    client: AsyncClient,
    teacher_user,
    auth_headers,
):
    response = await client.get(
        ("/api/v1/assessment-analytics/" "assessments/not-an-integer/summary"),
        headers=auth_headers(
            teacher_user,
        ),
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_ranking_assessment_id_must_be_integer(
    client: AsyncClient,
    teacher_user,
    auth_headers,
):
    response = await client.get(
        ("/api/v1/assessment-analytics/" "assessments/not-an-integer/ranking"),
        headers=auth_headers(
            teacher_user,
        ),
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_grade_distribution_assessment_id_must_be_integer(
    client: AsyncClient,
    teacher_user,
    auth_headers,
):
    response = await client.get(
        (
            "/api/v1/assessment-analytics/"
            "assessments/not-an-integer/grade-distribution"
        ),
        headers=auth_headers(
            teacher_user,
        ),
    )

    assert response.status_code == 422
