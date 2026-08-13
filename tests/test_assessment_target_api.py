from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

import pytest
from fastapi import HTTPException
from httpx import AsyncClient

from app.api.v1.endpoints import assessment_targets as endpoint

TARGETS_URL = "/api/v1/assessment-targets"

TARGET_URL = "/api/v1/assessment-targets/{target_id}"

STUDENT_PROGRESS_URL = "/api/v1/assessment-targets/student/courses/{course_id}/progress"

PARENT_PROGRESS_URL = (
    "/api/v1/assessment-targets/"
    "parent/students/{student_id}/courses/{course_id}/progress"
)


# ---------------------------------------------------------------------------
# Payload helpers
# ---------------------------------------------------------------------------


def _target_payload(
    *,
    target_id: int = 1,
    school_id: int = 1,
    student_id: int = 10,
    course_id: int = 20,
    grade_label: str = "A",
    grade_points: Decimal | None = Decimal("5.00"),
    academic_year: str | None = "2026/27",
    notes: str | None = "Maintain strong performance.",
    set_by_id: int = 30,
):
    return {
        "id": target_id,
        "school_id": school_id,
        "student_id": student_id,
        "student_name": "Student One",
        "course_id": course_id,
        "course_title": "OCR A Level Physics A",
        "subject_id": 100,
        "subject_name": "Physics",
        "grade_label": grade_label,
        "grade_points": grade_points,
        "academic_year": academic_year,
        "notes": notes,
        "set_by_id": set_by_id,
        "set_by_name": "Teacher One",
        "created_at": datetime(
            2026,
            9,
            1,
            9,
            0,
            tzinfo=timezone.utc,
        ),
        "updated_at": datetime(
            2026,
            9,
            2,
            10,
            0,
            tzinfo=timezone.utc,
        ),
    }


def _latest_result_payload(
    *,
    course_id: int = 20,
    grade: str | None = "A",
    grade_points: Decimal | None = Decimal("5.00"),
):
    return {
        "assessment_id": 101,
        "candidate_id": 201,
        "student_id": 10,
        "assessment_title": "Mechanics Test",
        "assessment_type": "end_of_topic_test",
        "academic_year": "2026/27",
        "term": "Autumn",
        "scheduled_at": datetime(
            2026,
            10,
            1,
            9,
            0,
            tzinfo=timezone.utc,
        ),
        "course_id": course_id,
        "course_title": "OCR A Level Physics A",
        "subject_id": 100,
        "subject_name": "Physics",
        "script_id": 301,
        "script_version": 1,
        "mark_awarded": Decimal("42.00"),
        "percentage": Decimal("84.00"),
        "grade": grade,
        "grade_points": grade_points,
        "is_pass": True,
        "published_at": datetime(
            2026,
            10,
            5,
            12,
            0,
            tzinfo=timezone.utc,
        ),
    }


def _progress_payload(
    *,
    audience: str,
    student_id: int = 10,
    course_id: int = 20,
    status_value: str = "on_target",
    target_grade_label: str = "A",
    target_grade_points: Decimal | None = Decimal("5.00"),
    current_grade: str | None = "A",
    current_grade_points: Decimal | None = Decimal("5.00"),
    difference: Decimal | None = Decimal("0.00"),
    include_latest_result: bool = True,
):
    return {
        "audience": audience,
        "target": _target_payload(
            student_id=student_id,
            course_id=course_id,
            grade_label=target_grade_label,
            grade_points=target_grade_points,
        ),
        "latest_result": (
            _latest_result_payload(
                course_id=course_id,
                grade=current_grade,
                grade_points=current_grade_points,
            )
            if include_latest_result
            else None
        ),
        "status": status_value,
        "grade_points_difference": difference,
        "target_grade_label": target_grade_label,
        "target_grade_points": target_grade_points,
        "current_grade": current_grade,
        "current_grade_points": current_grade_points,
    }


# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_requires_authentication(
    client: AsyncClient,
):
    response = await client.post(
        TARGETS_URL,
        json={
            "student_id": 10,
            "course_id": 20,
            "grade_label": "A",
        },
    )

    assert response.status_code in {
        401,
        403,
    }


@pytest.mark.asyncio
async def test_list_requires_authentication(
    client: AsyncClient,
):
    response = await client.get(
        TARGETS_URL,
    )

    assert response.status_code in {
        401,
        403,
    }


@pytest.mark.asyncio
async def test_get_requires_authentication(
    client: AsyncClient,
):
    response = await client.get(
        TARGET_URL.format(
            target_id=1,
        ),
    )

    assert response.status_code in {
        401,
        403,
    }


@pytest.mark.asyncio
async def test_student_progress_requires_authentication(
    client: AsyncClient,
):
    response = await client.get(
        STUDENT_PROGRESS_URL.format(
            course_id=20,
        ),
    )

    assert response.status_code in {
        401,
        403,
    }


@pytest.mark.asyncio
async def test_parent_progress_requires_authentication(
    client: AsyncClient,
):
    response = await client.get(
        PARENT_PROGRESS_URL.format(
            student_id=10,
            course_id=20,
        ),
    )

    assert response.status_code in {
        401,
        403,
    }


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_target(
    client: AsyncClient,
    teacher_user,
    auth_headers,
    monkeypatch,
):
    received: dict = {}

    async def fake_service(
        db,
        current_user,
        *,
        student_id,
        course_id,
        grade_label,
        grade_points,
        academic_year,
        notes,
        school_id,
    ):
        received.update(
            {
                "student_id": student_id,
                "course_id": course_id,
                "grade_label": grade_label,
                "grade_points": grade_points,
                "academic_year": academic_year,
                "notes": notes,
                "school_id": school_id,
            }
        )

        return _target_payload(
            school_id=current_user.school_id,
            student_id=student_id,
            course_id=course_id,
            grade_label=grade_label,
            grade_points=grade_points,
            academic_year=academic_year,
            notes=notes,
            set_by_id=current_user.id,
        )

    monkeypatch.setattr(
        endpoint,
        "create_assessment_target",
        fake_service,
    )

    response = await client.post(
        TARGETS_URL,
        json={
            "student_id": 10,
            "course_id": 20,
            "grade_label": "A",
            "grade_points": 5,
            "academic_year": "2026/27",
            "notes": "Maintain strong performance.",
        },
        headers=auth_headers(
            teacher_user,
        ),
    )

    assert response.status_code == 201, response.text

    assert received == {
        "student_id": 10,
        "course_id": 20,
        "grade_label": "A",
        "grade_points": Decimal("5"),
        "academic_year": "2026/27",
        "notes": "Maintain strong performance.",
        "school_id": None,
    }

    payload = response.json()

    assert payload["student_id"] == 10
    assert payload["course_id"] == 20
    assert payload["grade_label"] == "A"


@pytest.mark.asyncio
async def test_create_target_accepts_platform_school_id(
    client: AsyncClient,
    platform_admin_user,
    auth_headers,
    monkeypatch,
):
    received_school_ids: list[int | None] = []

    async def fake_service(
        db,
        current_user,
        *,
        student_id,
        course_id,
        grade_label,
        grade_points,
        academic_year,
        notes,
        school_id,
    ):
        received_school_ids.append(
            school_id,
        )

        return _target_payload(
            school_id=school_id or 1,
            student_id=student_id,
            course_id=course_id,
            grade_label=grade_label,
            grade_points=grade_points,
            academic_year=academic_year,
            notes=notes,
            set_by_id=current_user.id,
        )

    monkeypatch.setattr(
        endpoint,
        "create_assessment_target",
        fake_service,
    )

    response = await client.post(
        TARGETS_URL,
        json={
            "school_id": 7,
            "student_id": 10,
            "course_id": 20,
            "grade_label": "B",
        },
        headers=auth_headers(
            platform_admin_user,
        ),
    )

    assert response.status_code == 201, response.text
    assert received_school_ids == [7]


@pytest.mark.asyncio
async def test_create_propagates_duplicate_conflict(
    client: AsyncClient,
    teacher_user,
    auth_headers,
    monkeypatch,
):
    async def fake_service(
        db,
        current_user,
        **kwargs,
    ):
        raise HTTPException(
            status_code=409,
            detail="Assessment target already exists.",
        )

    monkeypatch.setattr(
        endpoint,
        "create_assessment_target",
        fake_service,
    )

    response = await client.post(
        TARGETS_URL,
        json={
            "student_id": 10,
            "course_id": 20,
            "grade_label": "A",
        },
        headers=auth_headers(
            teacher_user,
        ),
    )

    assert response.status_code == 409


# ---------------------------------------------------------------------------
# List
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_targets(
    client: AsyncClient,
    school_admin_user,
    auth_headers,
    monkeypatch,
):
    async def fake_service(
        db,
        current_user,
        *,
        school_id,
        student_id,
        course_id,
        academic_year,
    ):
        return [
            _target_payload(
                target_id=1,
            ),
            _target_payload(
                target_id=2,
                student_id=11,
                grade_label="B",
            ),
        ]

    monkeypatch.setattr(
        endpoint,
        "list_assessment_targets",
        fake_service,
    )

    response = await client.get(
        TARGETS_URL,
        headers=auth_headers(
            school_admin_user,
        ),
    )

    assert response.status_code == 200, response.text

    payload = response.json()

    assert len(payload) == 2
    assert payload[0]["id"] == 1
    assert payload[1]["id"] == 2


@pytest.mark.asyncio
async def test_list_passes_filters(
    client: AsyncClient,
    school_admin_user,
    auth_headers,
    monkeypatch,
):
    received: dict = {}

    async def fake_service(
        db,
        current_user,
        *,
        school_id,
        student_id,
        course_id,
        academic_year,
    ):
        received.update(
            {
                "school_id": school_id,
                "student_id": student_id,
                "course_id": course_id,
                "academic_year": academic_year,
            }
        )

        return []

    monkeypatch.setattr(
        endpoint,
        "list_assessment_targets",
        fake_service,
    )

    response = await client.get(
        TARGETS_URL,
        params={
            "school_id": 1,
            "student_id": 10,
            "course_id": 20,
            "academic_year": "2026/27",
        },
        headers=auth_headers(
            school_admin_user,
        ),
    )

    assert response.status_code == 200, response.text

    assert received == {
        "school_id": 1,
        "student_id": 10,
        "course_id": 20,
        "academic_year": "2026/27",
    }


# ---------------------------------------------------------------------------
# Get
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_target(
    client: AsyncClient,
    teacher_user,
    auth_headers,
    monkeypatch,
):
    received: dict = {}

    async def fake_service(
        db,
        current_user,
        *,
        target_id,
        school_id,
    ):
        received["target_id"] = target_id
        received["school_id"] = school_id

        return _target_payload(
            target_id=target_id,
            school_id=current_user.school_id,
            set_by_id=current_user.id,
        )

    monkeypatch.setattr(
        endpoint,
        "get_assessment_target",
        fake_service,
    )

    response = await client.get(
        TARGET_URL.format(
            target_id=123,
        ),
        headers=auth_headers(
            teacher_user,
        ),
    )

    assert response.status_code == 200, response.text
    assert received["target_id"] == 123
    assert received["school_id"] is None
    assert response.json()["id"] == 123


@pytest.mark.asyncio
async def test_get_propagates_not_found(
    client: AsyncClient,
    teacher_user,
    auth_headers,
    monkeypatch,
):
    async def fake_service(
        db,
        current_user,
        *,
        target_id,
        school_id,
    ):
        raise HTTPException(
            status_code=404,
            detail="Assessment target not found.",
        )

    monkeypatch.setattr(
        endpoint,
        "get_assessment_target",
        fake_service,
    )

    response = await client.get(
        TARGET_URL.format(
            target_id=999,
        ),
        headers=auth_headers(
            teacher_user,
        ),
    )

    assert response.status_code == 404


# ---------------------------------------------------------------------------
# PATCH semantics
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_patch_forwards_only_explicitly_supplied_fields(
    client: AsyncClient,
    teacher_user,
    auth_headers,
    monkeypatch,
):
    received: dict = {}

    async def fake_service(
        db,
        current_user,
        *,
        target_id,
        school_id,
        **kwargs,
    ):
        received["target_id"] = target_id
        received["school_id"] = school_id
        received["kwargs"] = kwargs

        return _target_payload(
            target_id=target_id,
            school_id=current_user.school_id,
            grade_label=kwargs.get(
                "grade_label",
                "B",
            ),
            grade_points=Decimal("4.00"),
            academic_year="2026/27",
            notes="Existing notes",
            set_by_id=current_user.id,
        )

    monkeypatch.setattr(
        endpoint,
        "update_assessment_target",
        fake_service,
    )

    response = await client.patch(
        TARGET_URL.format(
            target_id=1,
        ),
        json={
            "grade_label": "A",
        },
        headers=auth_headers(
            teacher_user,
        ),
    )

    assert response.status_code == 200, response.text

    assert received["kwargs"] == {
        "grade_label": "A",
    }


@pytest.mark.asyncio
async def test_patch_explicit_null_is_forwarded_for_nullable_fields(
    client: AsyncClient,
    teacher_user,
    auth_headers,
    monkeypatch,
):
    received: dict = {}

    async def fake_service(
        db,
        current_user,
        *,
        target_id,
        school_id,
        **kwargs,
    ):
        received.update(
            kwargs,
        )

        return _target_payload(
            target_id=target_id,
            school_id=current_user.school_id,
            grade_points=None,
            academic_year=None,
            notes=None,
            set_by_id=current_user.id,
        )

    monkeypatch.setattr(
        endpoint,
        "update_assessment_target",
        fake_service,
    )

    response = await client.patch(
        TARGET_URL.format(
            target_id=1,
        ),
        json={
            "grade_points": None,
            "academic_year": None,
            "notes": None,
        },
        headers=auth_headers(
            teacher_user,
        ),
    )

    assert response.status_code == 200, response.text

    assert received == {
        "grade_points": None,
        "academic_year": None,
        "notes": None,
    }

    payload = response.json()

    assert payload["grade_points"] is None
    assert payload["academic_year"] is None
    assert payload["notes"] is None


@pytest.mark.asyncio
async def test_patch_empty_object_preserves_all_fields(
    client: AsyncClient,
    teacher_user,
    auth_headers,
    monkeypatch,
):
    received_kwargs: list[dict] = []

    async def fake_service(
        db,
        current_user,
        *,
        target_id,
        school_id,
        **kwargs,
    ):
        received_kwargs.append(
            kwargs,
        )

        return _target_payload(
            target_id=target_id,
            school_id=current_user.school_id,
            set_by_id=current_user.id,
        )

    monkeypatch.setattr(
        endpoint,
        "update_assessment_target",
        fake_service,
    )

    response = await client.patch(
        TARGET_URL.format(
            target_id=1,
        ),
        json={},
        headers=auth_headers(
            teacher_user,
        ),
    )

    assert response.status_code == 200, response.text
    assert received_kwargs == [{}]


@pytest.mark.asyncio
async def test_patch_propagates_forbidden(
    client: AsyncClient,
    teacher_user,
    auth_headers,
    monkeypatch,
):
    async def fake_service(
        db,
        current_user,
        *,
        target_id,
        school_id,
        **kwargs,
    ):
        raise HTTPException(
            status_code=403,
            detail="Forbidden.",
        )

    monkeypatch.setattr(
        endpoint,
        "update_assessment_target",
        fake_service,
    )

    response = await client.patch(
        TARGET_URL.format(
            target_id=1,
        ),
        json={
            "grade_label": "A",
        },
        headers=auth_headers(
            teacher_user,
        ),
    )

    assert response.status_code == 403


# ---------------------------------------------------------------------------
# Delete
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_delete_target_returns_204(
    client: AsyncClient,
    teacher_user,
    auth_headers,
    monkeypatch,
):
    received_ids: list[int] = []

    async def fake_service(
        db,
        current_user,
        *,
        target_id,
        school_id,
    ):
        received_ids.append(
            target_id,
        )

    monkeypatch.setattr(
        endpoint,
        "delete_assessment_target",
        fake_service,
    )

    response = await client.delete(
        TARGET_URL.format(
            target_id=88,
        ),
        headers=auth_headers(
            teacher_user,
        ),
    )

    assert response.status_code == 204
    assert response.content == b""
    assert received_ids == [88]


@pytest.mark.asyncio
async def test_delete_propagates_not_found(
    client: AsyncClient,
    teacher_user,
    auth_headers,
    monkeypatch,
):
    async def fake_service(
        db,
        current_user,
        *,
        target_id,
        school_id,
    ):
        raise HTTPException(
            status_code=404,
            detail="Assessment target not found.",
        )

    monkeypatch.setattr(
        endpoint,
        "delete_assessment_target",
        fake_service,
    )

    response = await client.delete(
        TARGET_URL.format(
            target_id=999,
        ),
        headers=auth_headers(
            teacher_user,
        ),
    )

    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Student progress
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_student_can_get_target_progress(
    client: AsyncClient,
    student_user,
    auth_headers,
    monkeypatch,
):
    received_course_ids: list[int] = []

    async def fake_service(
        db,
        current_user,
        *,
        course_id,
    ):
        received_course_ids.append(
            course_id,
        )

        return _progress_payload(
            audience="student",
            student_id=current_user.id,
            course_id=course_id,
            status_value="above_target",
            target_grade_label="B",
            target_grade_points=Decimal("4"),
            current_grade="A",
            current_grade_points=Decimal("5"),
            difference=Decimal("1"),
        )

    monkeypatch.setattr(
        endpoint,
        "get_student_target_progress",
        fake_service,
    )

    response = await client.get(
        STUDENT_PROGRESS_URL.format(
            course_id=20,
        ),
        headers=auth_headers(
            student_user,
        ),
    )

    assert response.status_code == 200, response.text

    payload = response.json()

    assert received_course_ids == [20]
    assert payload["audience"] == "student"
    assert payload["status"] == "above_target"

    assert Decimal(
        str(
            payload["grade_points_difference"],
        )
    ) == Decimal("1")


@pytest.mark.asyncio
async def test_student_progress_supports_no_latest_result(
    client: AsyncClient,
    student_user,
    auth_headers,
    monkeypatch,
):
    async def fake_service(
        db,
        current_user,
        *,
        course_id,
    ):
        return _progress_payload(
            audience="student",
            student_id=current_user.id,
            course_id=course_id,
            status_value="not_comparable",
            current_grade=None,
            current_grade_points=None,
            difference=None,
            include_latest_result=False,
        )

    monkeypatch.setattr(
        endpoint,
        "get_student_target_progress",
        fake_service,
    )

    response = await client.get(
        STUDENT_PROGRESS_URL.format(
            course_id=20,
        ),
        headers=auth_headers(
            student_user,
        ),
    )

    assert response.status_code == 200, response.text

    payload = response.json()

    assert payload["status"] == "not_comparable"
    assert payload["latest_result"] is None
    assert payload["current_grade"] is None


@pytest.mark.asyncio
async def test_student_progress_propagates_forbidden(
    client: AsyncClient,
    teacher_user,
    auth_headers,
    monkeypatch,
):
    async def fake_service(
        db,
        current_user,
        *,
        course_id,
    ):
        raise HTTPException(
            status_code=403,
            detail="Only students can access this view.",
        )

    monkeypatch.setattr(
        endpoint,
        "get_student_target_progress",
        fake_service,
    )

    response = await client.get(
        STUDENT_PROGRESS_URL.format(
            course_id=20,
        ),
        headers=auth_headers(
            teacher_user,
        ),
    )

    assert response.status_code == 403


# ---------------------------------------------------------------------------
# Parent progress
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_parent_can_get_child_target_progress(
    client: AsyncClient,
    parent_user,
    auth_headers,
    monkeypatch,
):
    received: dict = {}

    async def fake_service(
        db,
        current_user,
        *,
        student_id,
        course_id,
    ):
        received["student_id"] = student_id
        received["course_id"] = course_id

        return _progress_payload(
            audience="parent",
            student_id=student_id,
            course_id=course_id,
        )

    monkeypatch.setattr(
        endpoint,
        "get_parent_student_target_progress",
        fake_service,
    )

    response = await client.get(
        PARENT_PROGRESS_URL.format(
            student_id=10,
            course_id=20,
        ),
        headers=auth_headers(
            parent_user,
        ),
    )

    assert response.status_code == 200, response.text

    assert received == {
        "student_id": 10,
        "course_id": 20,
    }

    assert response.json()["audience"] == "parent"


@pytest.mark.asyncio
async def test_parent_progress_propagates_forbidden(
    client: AsyncClient,
    parent_user,
    auth_headers,
    monkeypatch,
):
    async def fake_service(
        db,
        current_user,
        *,
        student_id,
        course_id,
    ):
        raise HTTPException(
            status_code=403,
            detail="Forbidden.",
        )

    monkeypatch.setattr(
        endpoint,
        "get_parent_student_target_progress",
        fake_service,
    )

    response = await client.get(
        PARENT_PROGRESS_URL.format(
            student_id=999,
            course_id=20,
        ),
        headers=auth_headers(
            parent_user,
        ),
    )

    assert response.status_code == 403


# ---------------------------------------------------------------------------
# Query/body validation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_student_id_must_be_positive(
    client: AsyncClient,
    teacher_user,
    auth_headers,
):
    response = await client.post(
        TARGETS_URL,
        json={
            "student_id": 0,
            "course_id": 20,
            "grade_label": "A",
        },
        headers=auth_headers(
            teacher_user,
        ),
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_course_id_must_be_positive(
    client: AsyncClient,
    teacher_user,
    auth_headers,
):
    response = await client.post(
        TARGETS_URL,
        json={
            "student_id": 10,
            "course_id": 0,
            "grade_label": "A",
        },
        headers=auth_headers(
            teacher_user,
        ),
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_grade_label_cannot_be_blank(
    client: AsyncClient,
    teacher_user,
    auth_headers,
):
    response = await client.post(
        TARGETS_URL,
        json={
            "student_id": 10,
            "course_id": 20,
            "grade_label": "",
        },
        headers=auth_headers(
            teacher_user,
        ),
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_grade_points_cannot_be_negative(
    client: AsyncClient,
    teacher_user,
    auth_headers,
):
    response = await client.post(
        TARGETS_URL,
        json={
            "student_id": 10,
            "course_id": 20,
            "grade_label": "A",
            "grade_points": -1,
        },
        headers=auth_headers(
            teacher_user,
        ),
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_list_school_id_must_be_positive(
    client: AsyncClient,
    school_admin_user,
    auth_headers,
):
    response = await client.get(
        TARGETS_URL,
        params={
            "school_id": 0,
        },
        headers=auth_headers(
            school_admin_user,
        ),
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_list_academic_year_max_length(
    client: AsyncClient,
    school_admin_user,
    auth_headers,
):
    response = await client.get(
        TARGETS_URL,
        params={
            "academic_year": "X" * 51,
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
async def test_target_id_must_be_integer(
    client: AsyncClient,
    teacher_user,
    auth_headers,
):
    response = await client.get(
        "/api/v1/assessment-targets/not-an-integer",
        headers=auth_headers(
            teacher_user,
        ),
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_student_progress_course_id_must_be_integer(
    client: AsyncClient,
    student_user,
    auth_headers,
):
    response = await client.get(
        "/api/v1/assessment-targets/student/courses/not-an-integer/progress",
        headers=auth_headers(
            student_user,
        ),
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_parent_progress_student_id_must_be_integer(
    client: AsyncClient,
    parent_user,
    auth_headers,
):
    response = await client.get(
        "/api/v1/assessment-targets/"
        "parent/students/not-an-integer/courses/20/progress",
        headers=auth_headers(
            parent_user,
        ),
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_parent_progress_course_id_must_be_integer(
    client: AsyncClient,
    parent_user,
    auth_headers,
):
    response = await client.get(
        "/api/v1/assessment-targets/"
        "parent/students/10/courses/not-an-integer/progress",
        headers=auth_headers(
            parent_user,
        ),
    )

    assert response.status_code == 422
