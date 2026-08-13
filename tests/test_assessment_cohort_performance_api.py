from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

import pytest
from fastapi import HTTPException
from httpx import AsyncClient

from app.api.v1.endpoints import assessment_cohort_performance as endpoint

COHORT_URL = "/api/v1/assessment-cohort-performance"

COURSE_URL = "/api/v1/assessment-cohort-performance/courses/{course_id}"

SUBJECT_URL = "/api/v1/assessment-cohort-performance/subjects/{subject_id}"

TEACHER_URL = "/api/v1/assessment-cohort-performance/teachers/{teacher_id}"


# ---------------------------------------------------------------------------
# Payload helpers
# ---------------------------------------------------------------------------


def _assessment_row(
    *,
    assessment_id: int = 1,
    course_id: int = 100,
    teacher_id: int = 10,
    subject_id: int = 200,
):
    return {
        "assessment_id": assessment_id,
        "assessment_title": f"Assessment {assessment_id}",
        "assessment_type": "end_of_topic_test",
        "academic_year": "2026/27",
        "term": "Autumn",
        "scheduled_at": datetime(
            2026,
            9,
            assessment_id,
            9,
            0,
            tzinfo=timezone.utc,
        ),
        "course_id": course_id,
        "course_title": f"Course {course_id}",
        "teacher_id": teacher_id,
        "subject_id": subject_id,
        "subject_name": "Physics",
        "candidate_count": 3,
        "included_candidate_count": 3,
        "excluded_incomplete_candidate_count": 0,
        "mean_percentage": Decimal("70.00"),
        "median_percentage": Decimal("70.00"),
        "lowest_percentage": Decimal("50.00"),
        "highest_percentage": Decimal("90.00"),
        "graded_candidate_count": 3,
        "ungraded_candidate_count": 0,
        "pass_count": 2,
        "fail_count": 1,
        "pass_percentage": Decimal("66.67"),
    }


def _payload(
    *,
    school_id: int | None = 1,
    course_id: int | None = None,
    subject_id: int | None = None,
    teacher_id: int | None = None,
    academic_year: str | None = None,
    term: str | None = None,
):
    return {
        "scope": {
            "school_id": school_id,
            "course_id": course_id,
            "subject_id": subject_id,
            "teacher_id": teacher_id,
            "academic_year": academic_year,
            "term": term,
        },
        "result_stage": "finalised",
        "script_selection": "latest",
        "selected_assessment_count": 2,
        "assessments_with_results": 2,
        "assessments_without_results": 0,
        "candidate_allocation_count": 6,
        "included_result_count": 6,
        "excluded_incomplete_result_count": 0,
        "unique_student_count": 4,
        "candidate_inclusion_percentage": Decimal("100.00"),
        "mean_percentage": Decimal("72.50"),
        "median_percentage": Decimal("72.50"),
        "lowest_percentage": Decimal("50.00"),
        "highest_percentage": Decimal("95.00"),
        "graded_result_count": 6,
        "ungraded_result_count": 0,
        "pass_count": 4,
        "fail_count": 2,
        "pass_percentage": Decimal("66.67"),
        "grade_distribution": [
            {
                "grade": "A",
                "count": 3,
                "percentage": Decimal("50.00"),
            },
            {
                "grade": "B",
                "count": 2,
                "percentage": Decimal("33.33"),
            },
            {
                "grade": "D",
                "count": 1,
                "percentage": Decimal("16.67"),
            },
        ],
        "assessments": [
            _assessment_row(
                assessment_id=1,
                course_id=course_id or 100,
                teacher_id=teacher_id or 10,
                subject_id=subject_id or 200,
            ),
            _assessment_row(
                assessment_id=2,
                course_id=course_id or 100,
                teacher_id=teacher_id or 10,
                subject_id=subject_id or 200,
            ),
        ],
    }


# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_general_cohort_requires_authentication(
    client: AsyncClient,
):
    response = await client.get(
        COHORT_URL,
    )

    assert response.status_code in {
        401,
        403,
    }


@pytest.mark.asyncio
async def test_course_view_requires_authentication(
    client: AsyncClient,
):
    response = await client.get(
        COURSE_URL.format(
            course_id=100,
        ),
    )

    assert response.status_code in {
        401,
        403,
    }


@pytest.mark.asyncio
async def test_subject_view_requires_authentication(
    client: AsyncClient,
):
    response = await client.get(
        SUBJECT_URL.format(
            subject_id=200,
        ),
    )

    assert response.status_code in {
        401,
        403,
    }


@pytest.mark.asyncio
async def test_teacher_view_requires_authentication(
    client: AsyncClient,
):
    response = await client.get(
        TEACHER_URL.format(
            teacher_id=10,
        ),
    )

    assert response.status_code in {
        401,
        403,
    }


# ---------------------------------------------------------------------------
# General cohort
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_staff_can_get_general_cohort_performance(
    client: AsyncClient,
    teacher_user,
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
        teacher_id,
        academic_year,
        term,
    ):
        assert current_user.id == teacher_user.id

        return _payload(
            school_id=teacher_user.school_id,
        )

    monkeypatch.setattr(
        endpoint,
        "get_assessment_cohort_performance",
        fake_service,
    )

    response = await client.get(
        COHORT_URL,
        headers=auth_headers(
            teacher_user,
        ),
    )

    assert response.status_code == 200, response.text

    payload = response.json()

    assert payload["result_stage"] == "finalised"
    assert payload["script_selection"] == "latest"
    assert payload["selected_assessment_count"] == 2
    assert payload["included_result_count"] == 6
    assert payload["unique_student_count"] == 4

    assert Decimal(
        str(
            payload["mean_percentage"],
        )
    ) == Decimal("72.50")

    assert (
        len(
            payload["assessments"],
        )
        == 2
    )


@pytest.mark.asyncio
async def test_general_cohort_passes_all_filters(
    client: AsyncClient,
    school_admin_user,
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
        teacher_id,
        academic_year,
        term,
    ):
        received.update(
            {
                "school_id": school_id,
                "course_id": course_id,
                "subject_id": subject_id,
                "teacher_id": teacher_id,
                "academic_year": academic_year,
                "term": term,
            }
        )

        return _payload(
            school_id=school_id,
            course_id=course_id,
            subject_id=subject_id,
            teacher_id=teacher_id,
            academic_year=academic_year,
            term=term,
        )

    monkeypatch.setattr(
        endpoint,
        "get_assessment_cohort_performance",
        fake_service,
    )

    response = await client.get(
        COHORT_URL,
        params={
            "school_id": 1,
            "course_id": 100,
            "subject_id": 200,
            "teacher_id": 10,
            "academic_year": "2026/27",
            "term": "Autumn",
        },
        headers=auth_headers(
            school_admin_user,
        ),
    )

    assert response.status_code == 200, response.text

    assert received == {
        "school_id": 1,
        "course_id": 100,
        "subject_id": 200,
        "teacher_id": 10,
        "academic_year": "2026/27",
        "term": "Autumn",
    }

    scope = response.json()["scope"]

    assert scope["course_id"] == 100
    assert scope["subject_id"] == 200
    assert scope["teacher_id"] == 10


@pytest.mark.asyncio
async def test_general_cohort_allows_empty_payload(
    client: AsyncClient,
    school_admin_user,
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
        teacher_id,
        academic_year,
        term,
    ):
        return {
            "scope": {
                "school_id": current_user.school_id,
                "course_id": None,
                "subject_id": None,
                "teacher_id": None,
                "academic_year": None,
                "term": None,
            },
            "result_stage": "finalised",
            "script_selection": "latest",
            "selected_assessment_count": 0,
            "assessments_with_results": 0,
            "assessments_without_results": 0,
            "candidate_allocation_count": 0,
            "included_result_count": 0,
            "excluded_incomplete_result_count": 0,
            "unique_student_count": 0,
            "candidate_inclusion_percentage": None,
            "mean_percentage": None,
            "median_percentage": None,
            "lowest_percentage": None,
            "highest_percentage": None,
            "graded_result_count": 0,
            "ungraded_result_count": 0,
            "pass_count": 0,
            "fail_count": 0,
            "pass_percentage": None,
            "grade_distribution": [],
            "assessments": [],
        }

    monkeypatch.setattr(
        endpoint,
        "get_assessment_cohort_performance",
        fake_service,
    )

    response = await client.get(
        COHORT_URL,
        headers=auth_headers(
            school_admin_user,
        ),
    )

    assert response.status_code == 200, response.text

    payload = response.json()

    assert payload["selected_assessment_count"] == 0
    assert payload["assessments"] == []
    assert payload["mean_percentage"] is None


# ---------------------------------------------------------------------------
# Course view
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_course_view_passes_course_id(
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
        course_id,
        school_id,
        academic_year,
        term,
    ):
        received_ids.append(
            course_id,
        )

        return _payload(
            school_id=current_user.school_id,
            course_id=course_id,
            academic_year=academic_year,
            term=term,
        )

    monkeypatch.setattr(
        endpoint,
        "get_course_assessment_performance",
        fake_service,
    )

    response = await client.get(
        COURSE_URL.format(
            course_id=321,
        ),
        headers=auth_headers(
            teacher_user,
        ),
    )

    assert response.status_code == 200, response.text
    assert received_ids == [321]
    assert response.json()["scope"]["course_id"] == 321


@pytest.mark.asyncio
async def test_course_view_passes_optional_filters(
    client: AsyncClient,
    school_admin_user,
    auth_headers,
    monkeypatch,
):
    received: dict = {}

    async def fake_service(
        *,
        db,
        current_user,
        course_id,
        school_id,
        academic_year,
        term,
    ):
        received.update(
            {
                "course_id": course_id,
                "school_id": school_id,
                "academic_year": academic_year,
                "term": term,
            }
        )

        return _payload(
            school_id=school_id,
            course_id=course_id,
            academic_year=academic_year,
            term=term,
        )

    monkeypatch.setattr(
        endpoint,
        "get_course_assessment_performance",
        fake_service,
    )

    response = await client.get(
        COURSE_URL.format(
            course_id=100,
        ),
        params={
            "school_id": 1,
            "academic_year": "2026/27",
            "term": "Autumn",
        },
        headers=auth_headers(
            school_admin_user,
        ),
    )

    assert response.status_code == 200, response.text

    assert received == {
        "course_id": 100,
        "school_id": 1,
        "academic_year": "2026/27",
        "term": "Autumn",
    }


# ---------------------------------------------------------------------------
# Subject view
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_subject_view_passes_subject_id(
    client: AsyncClient,
    school_admin_user,
    auth_headers,
    monkeypatch,
):
    received_ids: list[int] = []

    async def fake_service(
        *,
        db,
        current_user,
        subject_id,
        school_id,
        academic_year,
        term,
    ):
        received_ids.append(
            subject_id,
        )

        return _payload(
            school_id=current_user.school_id,
            subject_id=subject_id,
            academic_year=academic_year,
            term=term,
        )

    monkeypatch.setattr(
        endpoint,
        "get_subject_assessment_performance",
        fake_service,
    )

    response = await client.get(
        SUBJECT_URL.format(
            subject_id=777,
        ),
        headers=auth_headers(
            school_admin_user,
        ),
    )

    assert response.status_code == 200, response.text
    assert received_ids == [777]
    assert response.json()["scope"]["subject_id"] == 777


# ---------------------------------------------------------------------------
# Teacher view
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_teacher_view_passes_teacher_id(
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
        teacher_id,
        school_id,
        academic_year,
        term,
    ):
        received_ids.append(
            teacher_id,
        )

        return _payload(
            school_id=current_user.school_id,
            teacher_id=teacher_id,
            academic_year=academic_year,
            term=term,
        )

    monkeypatch.setattr(
        endpoint,
        "get_teacher_assessment_performance",
        fake_service,
    )

    response = await client.get(
        TEACHER_URL.format(
            teacher_id=teacher_user.id,
        ),
        headers=auth_headers(
            teacher_user,
        ),
    )

    assert response.status_code == 200, response.text
    assert received_ids == [teacher_user.id]


@pytest.mark.asyncio
async def test_teacher_view_propagates_forbidden(
    client: AsyncClient,
    teacher_user,
    auth_headers,
    monkeypatch,
):
    async def fake_service(
        *,
        db,
        current_user,
        teacher_id,
        school_id,
        academic_year,
        term,
    ):
        raise HTTPException(
            status_code=403,
            detail="You can only view cohort performance for your own courses.",
        )

    monkeypatch.setattr(
        endpoint,
        "get_teacher_assessment_performance",
        fake_service,
    )

    response = await client.get(
        TEACHER_URL.format(
            teacher_id=999,
        ),
        headers=auth_headers(
            teacher_user,
        ),
    )

    assert response.status_code == 403


# ---------------------------------------------------------------------------
# Error propagation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_general_cohort_propagates_forbidden(
    client: AsyncClient,
    teacher_user,
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
        teacher_id,
        academic_year,
        term,
    ):
        raise HTTPException(
            status_code=403,
            detail="Forbidden.",
        )

    monkeypatch.setattr(
        endpoint,
        "get_assessment_cohort_performance",
        fake_service,
    )

    response = await client.get(
        COHORT_URL,
        headers=auth_headers(
            teacher_user,
        ),
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_course_view_propagates_not_found(
    client: AsyncClient,
    teacher_user,
    auth_headers,
    monkeypatch,
):
    async def fake_service(
        *,
        db,
        current_user,
        course_id,
        school_id,
        academic_year,
        term,
    ):
        raise HTTPException(
            status_code=404,
            detail="Course not found.",
        )

    monkeypatch.setattr(
        endpoint,
        "get_course_assessment_performance",
        fake_service,
    )

    response = await client.get(
        COURSE_URL.format(
            course_id=999,
        ),
        headers=auth_headers(
            teacher_user,
        ),
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_subject_view_propagates_forbidden(
    client: AsyncClient,
    school_admin_user,
    auth_headers,
    monkeypatch,
):
    async def fake_service(
        *,
        db,
        current_user,
        subject_id,
        school_id,
        academic_year,
        term,
    ):
        raise HTTPException(
            status_code=403,
            detail="Forbidden.",
        )

    monkeypatch.setattr(
        endpoint,
        "get_subject_assessment_performance",
        fake_service,
    )

    response = await client.get(
        SUBJECT_URL.format(
            subject_id=200,
        ),
        headers=auth_headers(
            school_admin_user,
        ),
    )

    assert response.status_code == 403


# ---------------------------------------------------------------------------
# General query validation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_general_school_id_must_be_positive(
    client: AsyncClient,
    school_admin_user,
    auth_headers,
):
    response = await client.get(
        COHORT_URL,
        params={
            "school_id": 0,
        },
        headers=auth_headers(
            school_admin_user,
        ),
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_general_course_id_must_be_positive(
    client: AsyncClient,
    school_admin_user,
    auth_headers,
):
    response = await client.get(
        COHORT_URL,
        params={
            "course_id": 0,
        },
        headers=auth_headers(
            school_admin_user,
        ),
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_general_subject_id_must_be_positive(
    client: AsyncClient,
    school_admin_user,
    auth_headers,
):
    response = await client.get(
        COHORT_URL,
        params={
            "subject_id": -1,
        },
        headers=auth_headers(
            school_admin_user,
        ),
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_general_teacher_id_must_be_positive(
    client: AsyncClient,
    school_admin_user,
    auth_headers,
):
    response = await client.get(
        COHORT_URL,
        params={
            "teacher_id": 0,
        },
        headers=auth_headers(
            school_admin_user,
        ),
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_general_academic_year_max_length_is_enforced(
    client: AsyncClient,
    school_admin_user,
    auth_headers,
):
    response = await client.get(
        COHORT_URL,
        params={
            "academic_year": "X" * 51,
        },
        headers=auth_headers(
            school_admin_user,
        ),
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_general_term_max_length_is_enforced(
    client: AsyncClient,
    school_admin_user,
    auth_headers,
):
    response = await client.get(
        COHORT_URL,
        params={
            "term": "X" * 101,
        },
        headers=auth_headers(
            school_admin_user,
        ),
    )

    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Path validation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_course_id_must_be_integer(
    client: AsyncClient,
    teacher_user,
    auth_headers,
):
    response = await client.get(
        "/api/v1/assessment-cohort-performance/courses/not-an-integer",
        headers=auth_headers(
            teacher_user,
        ),
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_subject_id_must_be_integer(
    client: AsyncClient,
    school_admin_user,
    auth_headers,
):
    response = await client.get(
        "/api/v1/assessment-cohort-performance/subjects/not-an-integer",
        headers=auth_headers(
            school_admin_user,
        ),
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_teacher_id_must_be_integer(
    client: AsyncClient,
    teacher_user,
    auth_headers,
):
    response = await client.get(
        "/api/v1/assessment-cohort-performance/teachers/not-an-integer",
        headers=auth_headers(
            teacher_user,
        ),
    )

    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Wrapper query validation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_course_school_id_must_be_positive(
    client: AsyncClient,
    school_admin_user,
    auth_headers,
):
    response = await client.get(
        COURSE_URL.format(
            course_id=100,
        ),
        params={
            "school_id": 0,
        },
        headers=auth_headers(
            school_admin_user,
        ),
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_subject_school_id_must_be_positive(
    client: AsyncClient,
    school_admin_user,
    auth_headers,
):
    response = await client.get(
        SUBJECT_URL.format(
            subject_id=200,
        ),
        params={
            "school_id": 0,
        },
        headers=auth_headers(
            school_admin_user,
        ),
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_teacher_school_id_must_be_positive(
    client: AsyncClient,
    school_admin_user,
    auth_headers,
):
    response = await client.get(
        TEACHER_URL.format(
            teacher_id=10,
        ),
        params={
            "school_id": 0,
        },
        headers=auth_headers(
            school_admin_user,
        ),
    )

    assert response.status_code == 422
