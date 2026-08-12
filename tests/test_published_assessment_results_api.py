from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

import pytest
from fastapi import HTTPException
from httpx import AsyncClient

from app.api.v1.endpoints import published_assessment_results as endpoint

STUDENT_RESULT_URL = (
    "/api/v1/published-assessment-results/student/candidates/{candidate_id}"
)

PARENT_RESULT_URL = (
    "/api/v1/published-assessment-results/parent/candidates/{candidate_id}"
)


# ---------------------------------------------------------------------------
# Response helpers
# ---------------------------------------------------------------------------


def _published_at() -> datetime:
    return datetime(
        2026,
        8,
        12,
        12,
        0,
        0,
        tzinfo=timezone.utc,
    )


def _student_result(
    *,
    assessment_id: int = 100,
    candidate_id: int = 200,
    student_id: int = 300,
    mark_awarded: Decimal | None = Decimal("42.00"),
    percentage: Decimal | None = Decimal("84.00"),
    grade: str | None = "8",
    grade_points: Decimal | None = Decimal("8.00"),
    is_pass: bool | None = True,
    question_breakdown=None,
) -> dict:
    return {
        "assessment_id": assessment_id,
        "candidate_id": candidate_id,
        "student_id": student_id,
        "candidate_number": "PUB-001",
        "script_id": 400,
        "script_version": 1,
        "mark_awarded": mark_awarded,
        "percentage": percentage,
        "grade": grade,
        "grade_points": grade_points,
        "is_pass": is_pass,
        "question_breakdown": question_breakdown,
        "release_message": "Well done.",
        "published_at": _published_at(),
        "visibility": {
            "include_mark": mark_awarded is not None,
            "include_percentage": percentage is not None,
            "include_grade": grade is not None,
            "include_question_breakdown": question_breakdown is not None,
        },
    }


def _parent_result(
    *,
    assessment_id: int = 100,
    candidate_id: int = 200,
    student_id: int = 300,
    mark_awarded: Decimal | None = Decimal("42.00"),
    percentage: Decimal | None = Decimal("84.00"),
    grade: str | None = "8",
    grade_points: Decimal | None = Decimal("8.00"),
    is_pass: bool | None = True,
    question_breakdown=None,
) -> dict:
    return {
        "assessment_id": assessment_id,
        "candidate_id": candidate_id,
        "student_id": student_id,
        "candidate_number": "PUB-001",
        "script_id": 400,
        "script_version": 1,
        "mark_awarded": mark_awarded,
        "percentage": percentage,
        "grade": grade,
        "grade_points": grade_points,
        "is_pass": is_pass,
        "question_breakdown": question_breakdown,
        "release_message": "Well done.",
        "published_at": _published_at(),
        "visibility": {
            "include_mark": mark_awarded is not None,
            "include_percentage": percentage is not None,
            "include_grade": grade is not None,
            "include_question_breakdown": question_breakdown is not None,
        },
    }


# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_student_published_result_requires_authentication(
    client: AsyncClient,
):
    response = await client.get(
        STUDENT_RESULT_URL.format(
            candidate_id=200,
        ),
    )

    assert response.status_code in {
        401,
        403,
    }


@pytest.mark.asyncio
async def test_parent_published_result_requires_authentication(
    client: AsyncClient,
):
    response = await client.get(
        PARENT_RESULT_URL.format(
            candidate_id=200,
        ),
    )

    assert response.status_code in {
        401,
        403,
    }


# ---------------------------------------------------------------------------
# Student endpoint
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_student_can_get_published_assessment_result(
    client: AsyncClient,
    student_user,
    auth_headers,
    monkeypatch,
):
    candidate_id = 200

    async def fake_service(
        *,
        db,
        current_user,
        candidate_id,
    ):
        assert current_user.id == student_user.id
        assert candidate_id == 200

        return _student_result(
            candidate_id=candidate_id,
            student_id=student_user.id,
        )

    monkeypatch.setattr(
        endpoint,
        "get_student_published_assessment_result",
        fake_service,
    )

    response = await client.get(
        STUDENT_RESULT_URL.format(
            candidate_id=candidate_id,
        ),
        headers=auth_headers(
            student_user,
        ),
    )

    assert response.status_code == 200, response.text

    payload = response.json()

    assert payload["assessment_id"] == 100
    assert payload["candidate_id"] == candidate_id
    assert payload["student_id"] == student_user.id
    assert payload["candidate_number"] == "PUB-001"

    assert Decimal(
        str(
            payload["mark_awarded"],
        )
    ) == Decimal("42.00")

    assert Decimal(
        str(
            payload["percentage"],
        )
    ) == Decimal("84.00")

    assert payload["grade"] == "8"
    assert payload["is_pass"] is True
    assert payload["release_message"] == "Well done."


@pytest.mark.asyncio
async def test_student_endpoint_passes_candidate_id_to_service(
    client: AsyncClient,
    student_user,
    auth_headers,
    monkeypatch,
):
    received_candidate_ids: list[int] = []

    async def fake_service(
        *,
        db,
        current_user,
        candidate_id,
    ):
        received_candidate_ids.append(
            candidate_id,
        )

        return _student_result(
            candidate_id=candidate_id,
            student_id=student_user.id,
        )

    monkeypatch.setattr(
        endpoint,
        "get_student_published_assessment_result",
        fake_service,
    )

    response = await client.get(
        STUDENT_RESULT_URL.format(
            candidate_id=987,
        ),
        headers=auth_headers(
            student_user,
        ),
    )

    assert response.status_code == 200, response.text
    assert received_candidate_ids == [987]


@pytest.mark.asyncio
async def test_student_endpoint_returns_hidden_mark_as_null(
    client: AsyncClient,
    student_user,
    auth_headers,
    monkeypatch,
):
    async def fake_service(
        *,
        db,
        current_user,
        candidate_id,
    ):
        return _student_result(
            candidate_id=candidate_id,
            student_id=student_user.id,
            mark_awarded=None,
        )

    monkeypatch.setattr(
        endpoint,
        "get_student_published_assessment_result",
        fake_service,
    )

    response = await client.get(
        STUDENT_RESULT_URL.format(
            candidate_id=200,
        ),
        headers=auth_headers(
            student_user,
        ),
    )

    assert response.status_code == 200, response.text
    assert response.json()["mark_awarded"] is None


@pytest.mark.asyncio
async def test_student_endpoint_returns_hidden_percentage_as_null(
    client: AsyncClient,
    student_user,
    auth_headers,
    monkeypatch,
):
    async def fake_service(
        *,
        db,
        current_user,
        candidate_id,
    ):
        return _student_result(
            candidate_id=candidate_id,
            student_id=student_user.id,
            percentage=None,
        )

    monkeypatch.setattr(
        endpoint,
        "get_student_published_assessment_result",
        fake_service,
    )

    response = await client.get(
        STUDENT_RESULT_URL.format(
            candidate_id=200,
        ),
        headers=auth_headers(
            student_user,
        ),
    )

    assert response.status_code == 200, response.text
    assert response.json()["percentage"] is None


@pytest.mark.asyncio
async def test_student_endpoint_returns_hidden_grade_as_null(
    client: AsyncClient,
    student_user,
    auth_headers,
    monkeypatch,
):
    async def fake_service(
        *,
        db,
        current_user,
        candidate_id,
    ):
        return _student_result(
            candidate_id=candidate_id,
            student_id=student_user.id,
            grade=None,
            grade_points=None,
            is_pass=None,
        )

    monkeypatch.setattr(
        endpoint,
        "get_student_published_assessment_result",
        fake_service,
    )

    response = await client.get(
        STUDENT_RESULT_URL.format(
            candidate_id=200,
        ),
        headers=auth_headers(
            student_user,
        ),
    )

    assert response.status_code == 200, response.text

    payload = response.json()

    assert payload["grade"] is None
    assert payload["grade_points"] is None
    assert payload["is_pass"] is None


@pytest.mark.asyncio
async def test_student_endpoint_returns_question_breakdown(
    client: AsyncClient,
    student_user,
    auth_headers,
    monkeypatch,
):
    breakdown = [
        {
            "question_id": 1,
            "question_number": "1",
            "maximum_mark": Decimal("5.00"),
            "mark_awarded": Decimal("4.00"),
        },
        {
            "question_id": 2,
            "question_number": "2",
            "maximum_mark": Decimal("3.00"),
            "mark_awarded": Decimal("2.00"),
        },
    ]

    async def fake_service(
        *,
        db,
        current_user,
        candidate_id,
    ):
        return _student_result(
            candidate_id=candidate_id,
            student_id=student_user.id,
            question_breakdown=breakdown,
        )

    monkeypatch.setattr(
        endpoint,
        "get_student_published_assessment_result",
        fake_service,
    )

    response = await client.get(
        STUDENT_RESULT_URL.format(
            candidate_id=200,
        ),
        headers=auth_headers(
            student_user,
        ),
    )

    assert response.status_code == 200, response.text

    payload = response.json()

    assert (
        len(
            payload["question_breakdown"],
        )
        == 2
    )

    assert payload["question_breakdown"][0]["question_id"] == 1

    assert payload["question_breakdown"][0]["question_number"] == "1"


@pytest.mark.asyncio
async def test_student_endpoint_propagates_not_found(
    client: AsyncClient,
    student_user,
    auth_headers,
    monkeypatch,
):
    async def fake_service(
        *,
        db,
        current_user,
        candidate_id,
    ):
        raise HTTPException(
            status_code=404,
            detail="Published assessment result not found.",
        )

    monkeypatch.setattr(
        endpoint,
        "get_student_published_assessment_result",
        fake_service,
    )

    response = await client.get(
        STUDENT_RESULT_URL.format(
            candidate_id=999,
        ),
        headers=auth_headers(
            student_user,
        ),
    )

    assert response.status_code == 404

    # The application uses a global error envelope, so this endpoint test
    # verifies propagation through the HTTP status code rather than
    # coupling itself to the global response-body shape.


@pytest.mark.asyncio
async def test_student_endpoint_propagates_forbidden(
    client: AsyncClient,
    student_user,
    auth_headers,
    monkeypatch,
):
    async def fake_service(
        *,
        db,
        current_user,
        candidate_id,
    ):
        raise HTTPException(
            status_code=403,
            detail="Forbidden.",
        )

    monkeypatch.setattr(
        endpoint,
        "get_student_published_assessment_result",
        fake_service,
    )

    response = await client.get(
        STUDENT_RESULT_URL.format(
            candidate_id=200,
        ),
        headers=auth_headers(
            student_user,
        ),
    )

    assert response.status_code == 403
    # The application uses a global error envelope, so this endpoint test
    # verifies propagation through the HTTP status code rather than
    # coupling itself to the global response-body shape.


# ---------------------------------------------------------------------------
# Parent endpoint
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_parent_can_get_published_assessment_result(
    client: AsyncClient,
    parent_user,
    auth_headers,
    monkeypatch,
):
    candidate_id = 200
    student_id = 300

    async def fake_service(
        *,
        db,
        current_user,
        candidate_id,
    ):
        assert current_user.id == parent_user.id
        assert candidate_id == 200

        return _parent_result(
            candidate_id=candidate_id,
            student_id=student_id,
        )

    monkeypatch.setattr(
        endpoint,
        "get_parent_published_assessment_result",
        fake_service,
    )

    response = await client.get(
        PARENT_RESULT_URL.format(
            candidate_id=candidate_id,
        ),
        headers=auth_headers(
            parent_user,
        ),
    )

    assert response.status_code == 200, response.text

    payload = response.json()

    assert payload["assessment_id"] == 100
    assert payload["candidate_id"] == candidate_id
    assert payload["student_id"] == student_id
    assert payload["candidate_number"] == "PUB-001"

    assert Decimal(
        str(
            payload["mark_awarded"],
        )
    ) == Decimal("42.00")

    assert Decimal(
        str(
            payload["percentage"],
        )
    ) == Decimal("84.00")

    assert payload["grade"] == "8"


@pytest.mark.asyncio
async def test_parent_endpoint_passes_candidate_id_to_service(
    client: AsyncClient,
    parent_user,
    auth_headers,
    monkeypatch,
):
    received_candidate_ids: list[int] = []

    async def fake_service(
        *,
        db,
        current_user,
        candidate_id,
    ):
        received_candidate_ids.append(
            candidate_id,
        )

        return _parent_result(
            candidate_id=candidate_id,
        )

    monkeypatch.setattr(
        endpoint,
        "get_parent_published_assessment_result",
        fake_service,
    )

    response = await client.get(
        PARENT_RESULT_URL.format(
            candidate_id=654,
        ),
        headers=auth_headers(
            parent_user,
        ),
    )

    assert response.status_code == 200, response.text
    assert received_candidate_ids == [654]


@pytest.mark.asyncio
async def test_parent_endpoint_returns_hidden_fields_as_null(
    client: AsyncClient,
    parent_user,
    auth_headers,
    monkeypatch,
):
    async def fake_service(
        *,
        db,
        current_user,
        candidate_id,
    ):
        return _parent_result(
            candidate_id=candidate_id,
            mark_awarded=None,
            percentage=None,
            grade=None,
            grade_points=None,
            is_pass=None,
        )

    monkeypatch.setattr(
        endpoint,
        "get_parent_published_assessment_result",
        fake_service,
    )

    response = await client.get(
        PARENT_RESULT_URL.format(
            candidate_id=200,
        ),
        headers=auth_headers(
            parent_user,
        ),
    )

    assert response.status_code == 200, response.text

    payload = response.json()

    assert payload["mark_awarded"] is None
    assert payload["percentage"] is None
    assert payload["grade"] is None
    assert payload["grade_points"] is None
    assert payload["is_pass"] is None


@pytest.mark.asyncio
async def test_parent_endpoint_returns_question_breakdown(
    client: AsyncClient,
    parent_user,
    auth_headers,
    monkeypatch,
):
    breakdown = [
        {
            "question_id": 1,
            "question_number": "1",
            "maximum_mark": Decimal("10.00"),
            "mark_awarded": Decimal("8.00"),
        },
    ]

    async def fake_service(
        *,
        db,
        current_user,
        candidate_id,
    ):
        return _parent_result(
            candidate_id=candidate_id,
            question_breakdown=breakdown,
        )

    monkeypatch.setattr(
        endpoint,
        "get_parent_published_assessment_result",
        fake_service,
    )

    response = await client.get(
        PARENT_RESULT_URL.format(
            candidate_id=200,
        ),
        headers=auth_headers(
            parent_user,
        ),
    )

    assert response.status_code == 200, response.text

    payload = response.json()

    assert (
        len(
            payload["question_breakdown"],
        )
        == 1
    )

    assert payload["question_breakdown"][0]["question_id"] == 1


@pytest.mark.asyncio
async def test_parent_endpoint_propagates_not_found(
    client: AsyncClient,
    parent_user,
    auth_headers,
    monkeypatch,
):
    async def fake_service(
        *,
        db,
        current_user,
        candidate_id,
    ):
        raise HTTPException(
            status_code=404,
            detail="Published assessment result not found.",
        )

    monkeypatch.setattr(
        endpoint,
        "get_parent_published_assessment_result",
        fake_service,
    )

    response = await client.get(
        PARENT_RESULT_URL.format(
            candidate_id=999,
        ),
        headers=auth_headers(
            parent_user,
        ),
    )

    assert response.status_code == 404

    # The application uses a global error envelope, so this endpoint test
    # verifies propagation through the HTTP status code rather than
    # coupling itself to the global response-body shape.


@pytest.mark.asyncio
async def test_parent_endpoint_propagates_forbidden(
    client: AsyncClient,
    parent_user,
    auth_headers,
    monkeypatch,
):
    async def fake_service(
        *,
        db,
        current_user,
        candidate_id,
    ):
        raise HTTPException(
            status_code=403,
            detail="Forbidden.",
        )

    monkeypatch.setattr(
        endpoint,
        "get_parent_published_assessment_result",
        fake_service,
    )

    response = await client.get(
        PARENT_RESULT_URL.format(
            candidate_id=200,
        ),
        headers=auth_headers(
            parent_user,
        ),
    )

    assert response.status_code == 403
    # The application uses a global error envelope, so this endpoint test
    # verifies propagation through the HTTP status code rather than
    # coupling itself to the global response-body shape.


# ---------------------------------------------------------------------------
# Path validation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_student_candidate_id_must_be_integer(
    client: AsyncClient,
    student_user,
    auth_headers,
):
    response = await client.get(
        ("/api/v1/published-assessment-results/" "student/candidates/not-an-integer"),
        headers=auth_headers(
            student_user,
        ),
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_parent_candidate_id_must_be_integer(
    client: AsyncClient,
    parent_user,
    auth_headers,
):
    response = await client.get(
        ("/api/v1/published-assessment-results/" "parent/candidates/not-an-integer"),
        headers=auth_headers(
            parent_user,
        ),
    )

    assert response.status_code == 422
