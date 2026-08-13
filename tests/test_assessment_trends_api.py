from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

import pytest
from fastapi import HTTPException
from httpx import AsyncClient

from app.api.v1.endpoints import assessment_trends as endpoint

STUDENT_TREND_URL = "/api/v1/assessment-trends/student"

PARENT_TREND_URL = "/api/v1/assessment-trends/parent/students/{student_id}"


# ---------------------------------------------------------------------------
# Payload helpers
# ---------------------------------------------------------------------------


def _trend_point(
    *,
    assessment_id: int = 1001,
    candidate_id: int = 1,
    student_id: int = 100,
    assessment_title: str = "Forces Test",
    percentage: Decimal | None = Decimal("80.00"),
    percentage_change: Decimal | None = None,
    grade: str | None = "A",
    grade_points: Decimal | None = Decimal("5.00"),
):
    return {
        "assessment_id": assessment_id,
        "candidate_id": candidate_id,
        "student_id": student_id,
        "assessment_title": assessment_title,
        "assessment_type": "end_of_topic_test",
        "academic_year": "2026/27",
        "term": "Autumn",
        "scheduled_at": datetime(
            2026,
            9,
            10,
            9,
            0,
            tzinfo=timezone.utc,
        ),
        "assessment_date": datetime(
            2026,
            9,
            10,
            9,
            0,
            tzinfo=timezone.utc,
        ),
        "course_id": 20,
        "course_title": "OCR A Level Physics A",
        "subject_id": 10,
        "subject_name": "Physics",
        "subject_code": "PHY",
        "exam_board": "OCR",
        "qualification": "A Level",
        "specification_code": "H556",
        "script_id": 2001,
        "script_version": 1,
        "mark_awarded": Decimal("40.00"),
        "percentage": percentage,
        "grade": grade,
        "grade_points": grade_points,
        "is_pass": True if grade is not None else None,
        "published_at": datetime(
            2026,
            9,
            11,
            12,
            0,
            tzinfo=timezone.utc,
        ),
        "visibility": {
            "include_mark": True,
            "include_percentage": percentage is not None,
            "include_grade": grade is not None,
            "include_question_breakdown": False,
        },
        "percentage_change": percentage_change,
    }


def _student_payload(
    *,
    student_id: int = 100,
):
    return {
        "student_id": student_id,
        "audience": "student",
        "filters": {
            "school_id": None,
            "course_id": None,
            "subject_id": None,
            "academic_year": None,
            "term": None,
        },
        "assessment_count": 2,
        "percentage_result_count": 2,
        "average_percentage": Decimal("70.00"),
        "first_percentage": Decimal("60.00"),
        "latest_percentage": Decimal("80.00"),
        "overall_percentage_change": Decimal("20.00"),
        "highest_percentage": Decimal("80.00"),
        "lowest_percentage": Decimal("60.00"),
        "grade_points_result_count": 2,
        "average_grade_points": Decimal("4.50"),
        "first_grade_points": Decimal("4.00"),
        "latest_grade_points": Decimal("5.00"),
        "overall_grade_points_change": Decimal("1.00"),
        "points": [
            _trend_point(
                assessment_id=1001,
                candidate_id=1,
                student_id=student_id,
                assessment_title="Forces Test",
                percentage=Decimal("60.00"),
                percentage_change=None,
                grade="B",
                grade_points=Decimal("4.00"),
            ),
            _trend_point(
                assessment_id=1002,
                candidate_id=2,
                student_id=student_id,
                assessment_title="Momentum Test",
                percentage=Decimal("80.00"),
                percentage_change=Decimal("20.00"),
                grade="A",
                grade_points=Decimal("5.00"),
            ),
        ],
    }


def _parent_payload(
    *,
    student_id: int = 100,
):
    payload = _student_payload(
        student_id=student_id,
    )

    payload["audience"] = "parent"

    return payload


# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_student_trend_requires_authentication(
    client: AsyncClient,
):
    response = await client.get(
        STUDENT_TREND_URL,
    )

    assert response.status_code in {
        401,
        403,
    }


@pytest.mark.asyncio
async def test_parent_trend_requires_authentication(
    client: AsyncClient,
):
    response = await client.get(
        PARENT_TREND_URL.format(
            student_id=100,
        ),
    )

    assert response.status_code in {
        401,
        403,
    }


# ---------------------------------------------------------------------------
# Student trend
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_student_can_get_assessment_trend(
    client: AsyncClient,
    student_user,
    auth_headers,
    monkeypatch,
):
    async def fake_service(
        *,
        db,
        current_user,
        school_id,
        course_id,
        subject_id,
        academic_year,
        term,
    ):
        assert current_user.id == student_user.id

        assert school_id is None
        assert course_id is None
        assert subject_id is None
        assert academic_year is None
        assert term is None

        return _student_payload(
            student_id=student_user.id,
        )

    monkeypatch.setattr(
        endpoint,
        "get_student_assessment_trend",
        fake_service,
    )

    response = await client.get(
        STUDENT_TREND_URL,
        headers=auth_headers(
            student_user,
        ),
    )

    assert response.status_code == 200, response.text

    payload = response.json()

    assert payload["student_id"] == student_user.id
    assert payload["audience"] == "student"
    assert payload["assessment_count"] == 2

    assert Decimal(
        str(
            payload["average_percentage"],
        )
    ) == Decimal("70.00")

    assert Decimal(
        str(
            payload["overall_percentage_change"],
        )
    ) == Decimal("20.00")

    assert (
        len(
            payload["points"],
        )
        == 2
    )


@pytest.mark.asyncio
async def test_student_trend_serialises_chronological_points(
    client: AsyncClient,
    student_user,
    auth_headers,
    monkeypatch,
):
    async def fake_service(
        *,
        db,
        current_user,
        school_id,
        course_id,
        subject_id,
        academic_year,
        term,
    ):
        return _student_payload(
            student_id=student_user.id,
        )

    monkeypatch.setattr(
        endpoint,
        "get_student_assessment_trend",
        fake_service,
    )

    response = await client.get(
        STUDENT_TREND_URL,
        headers=auth_headers(
            student_user,
        ),
    )

    assert response.status_code == 200, response.text

    points = response.json()["points"]

    assert [point["assessment_id"] for point in points] == [
        1001,
        1002,
    ]

    assert points[0]["assessment_title"] == "Forces Test"
    assert points[1]["assessment_title"] == "Momentum Test"

    assert Decimal(
        str(
            points[1]["percentage_change"],
        )
    ) == Decimal("20.00")


@pytest.mark.asyncio
async def test_student_trend_preserves_hidden_percentage(
    client: AsyncClient,
    student_user,
    auth_headers,
    monkeypatch,
):
    payload = _student_payload(
        student_id=student_user.id,
    )

    payload["assessment_count"] = 1
    payload["percentage_result_count"] = 0
    payload["average_percentage"] = None
    payload["first_percentage"] = None
    payload["latest_percentage"] = None
    payload["overall_percentage_change"] = None
    payload["highest_percentage"] = None
    payload["lowest_percentage"] = None

    payload["points"] = [
        _trend_point(
            student_id=student_user.id,
            percentage=None,
            percentage_change=None,
        ),
    ]

    async def fake_service(
        *,
        db,
        current_user,
        school_id,
        course_id,
        subject_id,
        academic_year,
        term,
    ):
        return payload

    monkeypatch.setattr(
        endpoint,
        "get_student_assessment_trend",
        fake_service,
    )

    response = await client.get(
        STUDENT_TREND_URL,
        headers=auth_headers(
            student_user,
        ),
    )

    assert response.status_code == 200, response.text

    body = response.json()

    assert body["percentage_result_count"] == 0
    assert body["average_percentage"] is None
    assert body["points"][0]["percentage"] is None


# ---------------------------------------------------------------------------
# Student filters
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_student_trend_passes_all_filters(
    client: AsyncClient,
    student_user,
    auth_headers,
    monkeypatch,
):
    received: dict = {}

    async def fake_service(
        *,
        db,
        current_user,
        school_id,
        course_id,
        subject_id,
        academic_year,
        term,
    ):
        received.update(
            {
                "school_id": school_id,
                "course_id": course_id,
                "subject_id": subject_id,
                "academic_year": academic_year,
                "term": term,
            }
        )

        payload = _student_payload(
            student_id=student_user.id,
        )

        payload["filters"] = {
            "school_id": school_id,
            "course_id": course_id,
            "subject_id": subject_id,
            "academic_year": academic_year,
            "term": term,
        }

        return payload

    monkeypatch.setattr(
        endpoint,
        "get_student_assessment_trend",
        fake_service,
    )

    response = await client.get(
        STUDENT_TREND_URL,
        params={
            "school_id": 7,
            "course_id": 20,
            "subject_id": 10,
            "academic_year": "2026/27",
            "term": "Autumn",
        },
        headers=auth_headers(
            student_user,
        ),
    )

    assert response.status_code == 200, response.text

    assert received == {
        "school_id": 7,
        "course_id": 20,
        "subject_id": 10,
        "academic_year": "2026/27",
        "term": "Autumn",
    }

    filters = response.json()["filters"]

    assert filters["school_id"] == 7
    assert filters["course_id"] == 20
    assert filters["subject_id"] == 10
    assert filters["academic_year"] == "2026/27"
    assert filters["term"] == "Autumn"


@pytest.mark.asyncio
async def test_student_trend_allows_empty_result_set(
    client: AsyncClient,
    student_user,
    auth_headers,
    monkeypatch,
):
    async def fake_service(
        *,
        db,
        current_user,
        school_id,
        course_id,
        subject_id,
        academic_year,
        term,
    ):
        return {
            "student_id": student_user.id,
            "audience": "student",
            "filters": {
                "school_id": school_id,
                "course_id": course_id,
                "subject_id": subject_id,
                "academic_year": academic_year,
                "term": term,
            },
            "assessment_count": 0,
            "percentage_result_count": 0,
            "average_percentage": None,
            "first_percentage": None,
            "latest_percentage": None,
            "overall_percentage_change": None,
            "highest_percentage": None,
            "lowest_percentage": None,
            "grade_points_result_count": 0,
            "average_grade_points": None,
            "first_grade_points": None,
            "latest_grade_points": None,
            "overall_grade_points_change": None,
            "points": [],
        }

    monkeypatch.setattr(
        endpoint,
        "get_student_assessment_trend",
        fake_service,
    )

    response = await client.get(
        STUDENT_TREND_URL,
        headers=auth_headers(
            student_user,
        ),
    )

    assert response.status_code == 200, response.text

    payload = response.json()

    assert payload["assessment_count"] == 0
    assert payload["points"] == []


# ---------------------------------------------------------------------------
# Parent trend
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_parent_can_get_linked_student_trend(
    client: AsyncClient,
    parent_user,
    auth_headers,
    monkeypatch,
):
    student_id = 100

    async def fake_service(
        *,
        db,
        current_user,
        student_id,
        school_id,
        course_id,
        subject_id,
        academic_year,
        term,
    ):
        assert current_user.id == parent_user.id
        assert student_id == 100

        return _parent_payload(
            student_id=student_id,
        )

    monkeypatch.setattr(
        endpoint,
        "get_parent_student_assessment_trend",
        fake_service,
    )

    response = await client.get(
        PARENT_TREND_URL.format(
            student_id=student_id,
        ),
        headers=auth_headers(
            parent_user,
        ),
    )

    assert response.status_code == 200, response.text

    payload = response.json()

    assert payload["student_id"] == student_id
    assert payload["audience"] == "parent"
    assert payload["assessment_count"] == 2


@pytest.mark.asyncio
async def test_parent_trend_passes_student_id_to_service(
    client: AsyncClient,
    parent_user,
    auth_headers,
    monkeypatch,
):
    received_student_ids: list[int] = []

    async def fake_service(
        *,
        db,
        current_user,
        student_id,
        school_id,
        course_id,
        subject_id,
        academic_year,
        term,
    ):
        received_student_ids.append(
            student_id,
        )

        return _parent_payload(
            student_id=student_id,
        )

    monkeypatch.setattr(
        endpoint,
        "get_parent_student_assessment_trend",
        fake_service,
    )

    response = await client.get(
        PARENT_TREND_URL.format(
            student_id=321,
        ),
        headers=auth_headers(
            parent_user,
        ),
    )

    assert response.status_code == 200, response.text
    assert received_student_ids == [321]
    assert response.json()["student_id"] == 321


@pytest.mark.asyncio
async def test_parent_trend_passes_filters(
    client: AsyncClient,
    parent_user,
    auth_headers,
    monkeypatch,
):
    received: dict = {}

    async def fake_service(
        *,
        db,
        current_user,
        student_id,
        school_id,
        course_id,
        subject_id,
        academic_year,
        term,
    ):
        received.update(
            {
                "student_id": student_id,
                "school_id": school_id,
                "course_id": course_id,
                "subject_id": subject_id,
                "academic_year": academic_year,
                "term": term,
            }
        )

        payload = _parent_payload(
            student_id=student_id,
        )

        payload["filters"] = {
            "school_id": school_id,
            "course_id": course_id,
            "subject_id": subject_id,
            "academic_year": academic_year,
            "term": term,
        }

        return payload

    monkeypatch.setattr(
        endpoint,
        "get_parent_student_assessment_trend",
        fake_service,
    )

    response = await client.get(
        PARENT_TREND_URL.format(
            student_id=100,
        ),
        params={
            "school_id": 7,
            "course_id": 20,
            "subject_id": 10,
            "academic_year": "2026/27",
            "term": "Autumn",
        },
        headers=auth_headers(
            parent_user,
        ),
    )

    assert response.status_code == 200, response.text

    assert received == {
        "student_id": 100,
        "school_id": 7,
        "course_id": 20,
        "subject_id": 10,
        "academic_year": "2026/27",
        "term": "Autumn",
    }


# ---------------------------------------------------------------------------
# Error propagation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_student_trend_propagates_forbidden(
    client: AsyncClient,
    student_user,
    auth_headers,
    monkeypatch,
):
    async def fake_service(
        *,
        db,
        current_user,
        school_id,
        course_id,
        subject_id,
        academic_year,
        term,
    ):
        raise HTTPException(
            status_code=403,
            detail="Forbidden.",
        )

    monkeypatch.setattr(
        endpoint,
        "get_student_assessment_trend",
        fake_service,
    )

    response = await client.get(
        STUDENT_TREND_URL,
        headers=auth_headers(
            student_user,
        ),
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_parent_trend_propagates_not_found(
    client: AsyncClient,
    parent_user,
    auth_headers,
    monkeypatch,
):
    async def fake_service(
        *,
        db,
        current_user,
        student_id,
        school_id,
        course_id,
        subject_id,
        academic_year,
        term,
    ):
        raise HTTPException(
            status_code=404,
            detail="Published assessment trend not found.",
        )

    monkeypatch.setattr(
        endpoint,
        "get_parent_student_assessment_trend",
        fake_service,
    )

    response = await client.get(
        PARENT_TREND_URL.format(
            student_id=999,
        ),
        headers=auth_headers(
            parent_user,
        ),
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_parent_trend_propagates_forbidden(
    client: AsyncClient,
    parent_user,
    auth_headers,
    monkeypatch,
):
    async def fake_service(
        *,
        db,
        current_user,
        student_id,
        school_id,
        course_id,
        subject_id,
        academic_year,
        term,
    ):
        raise HTTPException(
            status_code=403,
            detail="Forbidden.",
        )

    monkeypatch.setattr(
        endpoint,
        "get_parent_student_assessment_trend",
        fake_service,
    )

    response = await client.get(
        PARENT_TREND_URL.format(
            student_id=100,
        ),
        headers=auth_headers(
            parent_user,
        ),
    )

    assert response.status_code == 403


# ---------------------------------------------------------------------------
# Query validation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_student_school_id_must_be_positive(
    client: AsyncClient,
    student_user,
    auth_headers,
):
    response = await client.get(
        STUDENT_TREND_URL,
        params={
            "school_id": 0,
        },
        headers=auth_headers(
            student_user,
        ),
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_student_course_id_must_be_positive(
    client: AsyncClient,
    student_user,
    auth_headers,
):
    response = await client.get(
        STUDENT_TREND_URL,
        params={
            "course_id": 0,
        },
        headers=auth_headers(
            student_user,
        ),
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_student_subject_id_must_be_positive(
    client: AsyncClient,
    student_user,
    auth_headers,
):
    response = await client.get(
        STUDENT_TREND_URL,
        params={
            "subject_id": -1,
        },
        headers=auth_headers(
            student_user,
        ),
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_student_academic_year_max_length_is_enforced(
    client: AsyncClient,
    student_user,
    auth_headers,
):
    response = await client.get(
        STUDENT_TREND_URL,
        params={
            "academic_year": "X" * 51,
        },
        headers=auth_headers(
            student_user,
        ),
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_student_term_max_length_is_enforced(
    client: AsyncClient,
    student_user,
    auth_headers,
):
    response = await client.get(
        STUDENT_TREND_URL,
        params={
            "term": "X" * 101,
        },
        headers=auth_headers(
            student_user,
        ),
    )

    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Parent path/query validation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_parent_student_id_must_be_integer(
    client: AsyncClient,
    parent_user,
    auth_headers,
):
    response = await client.get(
        "/api/v1/assessment-trends/parent/students/not-an-integer",
        headers=auth_headers(
            parent_user,
        ),
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_parent_school_id_must_be_positive(
    client: AsyncClient,
    parent_user,
    auth_headers,
):
    response = await client.get(
        PARENT_TREND_URL.format(
            student_id=100,
        ),
        params={
            "school_id": 0,
        },
        headers=auth_headers(
            parent_user,
        ),
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_parent_course_id_must_be_positive(
    client: AsyncClient,
    parent_user,
    auth_headers,
):
    response = await client.get(
        PARENT_TREND_URL.format(
            student_id=100,
        ),
        params={
            "course_id": -1,
        },
        headers=auth_headers(
            parent_user,
        ),
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_parent_subject_id_must_be_positive(
    client: AsyncClient,
    parent_user,
    auth_headers,
):
    response = await client.get(
        PARENT_TREND_URL.format(
            student_id=100,
        ),
        params={
            "subject_id": 0,
        },
        headers=auth_headers(
            parent_user,
        ),
    )

    assert response.status_code == 422
