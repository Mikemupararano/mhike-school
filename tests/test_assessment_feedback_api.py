from __future__ import annotations

from datetime import datetime, timezone

import pytest
from fastapi import HTTPException
from httpx import AsyncClient

from app.api.v1.endpoints import assessment_feedback as endpoint

BASE_URL = "/api/v1/assessment-feedback"


# ---------------------------------------------------------------------------
# Payload helpers
# ---------------------------------------------------------------------------


def _feedback_payload(
    *,
    feedback_id: int = 1,
    school_id: int = 1,
    script_id: int = 500,
    overall_comment: str | None = "A strong assessment.",
    strengths: str | None = "Good mechanics.",
    areas_for_improvement: str | None = "Show working more clearly.",
    next_steps: str | None = "Practise momentum questions.",
    status_value: str = "draft",
    include_with_result: bool = True,
    created_by_id: int = 10,
    updated_by_id: int | None = None,
    finalised_at: datetime | None = None,
    finalised_by_id: int | None = None,
):
    return {
        "id": feedback_id,
        "school_id": school_id,
        "script_id": script_id,
        "overall_comment": overall_comment,
        "strengths": strengths,
        "areas_for_improvement": areas_for_improvement,
        "next_steps": next_steps,
        "status": status_value,
        "include_with_result": include_with_result,
        "created_by_id": created_by_id,
        "created_by_name": "Teacher One",
        "updated_by_id": updated_by_id,
        "updated_by_name": ("Teacher Two" if updated_by_id is not None else None),
        "finalised_at": finalised_at,
        "finalised_by_id": finalised_by_id,
        "finalised_by_name": ("Teacher One" if finalised_by_id is not None else None),
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


def _question_feedback_payload(
    *,
    question_feedback_id: int = 2,
    school_id: int = 1,
    response_id: int = 600,
    feedback_text: str | None = "Correct method.",
    strength: str | None = "Clear substitution.",
    improvement: str | None = "Include the unit.",
    include_with_result: bool = True,
    created_by_id: int = 10,
    updated_by_id: int | None = None,
):
    return {
        "id": question_feedback_id,
        "school_id": school_id,
        "response_id": response_id,
        "feedback_text": feedback_text,
        "strength": strength,
        "improvement": improvement,
        "include_with_result": include_with_result,
        "created_by_id": created_by_id,
        "created_by_name": "Teacher One",
        "updated_by_id": updated_by_id,
        "updated_by_name": ("Teacher Two" if updated_by_id is not None else None),
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


# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_feedback_requires_authentication(
    client: AsyncClient,
):
    response = await client.post(
        BASE_URL,
        json={
            "script_id": 500,
            "overall_comment": "Good work.",
        },
    )

    assert response.status_code in {
        401,
        403,
    }


@pytest.mark.asyncio
async def test_get_feedback_requires_authentication(
    client: AsyncClient,
):
    response = await client.get(
        f"{BASE_URL}/1",
    )

    assert response.status_code in {
        401,
        403,
    }


@pytest.mark.asyncio
async def test_create_question_feedback_requires_authentication(
    client: AsyncClient,
):
    response = await client.post(
        f"{BASE_URL}/questions",
        json={
            "response_id": 600,
            "feedback_text": "Good answer.",
        },
    )

    assert response.status_code in {
        401,
        403,
    }


# ---------------------------------------------------------------------------
# Overall feedback create
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_feedback(
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
        school_id,
        script_id,
        overall_comment,
        strengths,
        areas_for_improvement,
        next_steps,
        include_with_result,
    ):
        received.update(
            {
                "school_id": school_id,
                "script_id": script_id,
                "overall_comment": overall_comment,
                "strengths": strengths,
                "areas_for_improvement": areas_for_improvement,
                "next_steps": next_steps,
                "include_with_result": include_with_result,
            }
        )

        return _feedback_payload(
            school_id=current_user.school_id,
            script_id=script_id,
            overall_comment=overall_comment,
            strengths=strengths,
            areas_for_improvement=areas_for_improvement,
            next_steps=next_steps,
            include_with_result=include_with_result,
            created_by_id=current_user.id,
        )

    monkeypatch.setattr(
        endpoint,
        "create_assessment_feedback",
        fake_service,
    )

    response = await client.post(
        BASE_URL,
        json={
            "script_id": 500,
            "overall_comment": "Good work.",
            "strengths": "Strong mechanics.",
            "areas_for_improvement": "Show more working.",
            "next_steps": "Practise momentum.",
            "include_with_result": True,
        },
        headers=auth_headers(
            teacher_user,
        ),
    )

    assert response.status_code == 201, response.text

    assert received == {
        "school_id": None,
        "script_id": 500,
        "overall_comment": "Good work.",
        "strengths": "Strong mechanics.",
        "areas_for_improvement": "Show more working.",
        "next_steps": "Practise momentum.",
        "include_with_result": True,
    }

    payload = response.json()

    assert payload["script_id"] == 500
    assert payload["status"] == "draft"


@pytest.mark.asyncio
async def test_create_feedback_accepts_platform_school_id(
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
        school_id,
        script_id,
        overall_comment,
        strengths,
        areas_for_improvement,
        next_steps,
        include_with_result,
    ):
        received_school_ids.append(
            school_id,
        )

        return _feedback_payload(
            school_id=school_id or 1,
            script_id=script_id,
            overall_comment=overall_comment,
            strengths=strengths,
            areas_for_improvement=areas_for_improvement,
            next_steps=next_steps,
            include_with_result=include_with_result,
            created_by_id=current_user.id,
        )

    monkeypatch.setattr(
        endpoint,
        "create_assessment_feedback",
        fake_service,
    )

    response = await client.post(
        BASE_URL,
        json={
            "school_id": 7,
            "script_id": 500,
            "overall_comment": "Good work.",
        },
        headers=auth_headers(
            platform_admin_user,
        ),
    )

    assert response.status_code == 201, response.text
    assert received_school_ids == [7]


@pytest.mark.asyncio
async def test_create_feedback_propagates_duplicate_conflict(
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
            detail="Assessment feedback already exists for this script.",
        )

    monkeypatch.setattr(
        endpoint,
        "create_assessment_feedback",
        fake_service,
    )

    response = await client.post(
        BASE_URL,
        json={
            "script_id": 500,
            "overall_comment": "Good work.",
        },
        headers=auth_headers(
            teacher_user,
        ),
    )

    assert response.status_code == 409


# ---------------------------------------------------------------------------
# Overall feedback reads
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_feedback(
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
        feedback_id,
        school_id,
    ):
        received["feedback_id"] = feedback_id
        received["school_id"] = school_id

        return _feedback_payload(
            feedback_id=feedback_id,
            school_id=current_user.school_id,
            created_by_id=current_user.id,
        )

    monkeypatch.setattr(
        endpoint,
        "get_assessment_feedback",
        fake_service,
    )

    response = await client.get(
        f"{BASE_URL}/12",
        headers=auth_headers(
            teacher_user,
        ),
    )

    assert response.status_code == 200, response.text
    assert received == {
        "feedback_id": 12,
        "school_id": None,
    }
    assert response.json()["id"] == 12


@pytest.mark.asyncio
async def test_get_feedback_for_script(
    client: AsyncClient,
    teacher_user,
    auth_headers,
    monkeypatch,
):
    received_script_ids: list[int] = []

    async def fake_service(
        db,
        current_user,
        *,
        script_id,
        school_id,
    ):
        received_script_ids.append(
            script_id,
        )

        return _feedback_payload(
            script_id=script_id,
            school_id=current_user.school_id,
            created_by_id=current_user.id,
        )

    monkeypatch.setattr(
        endpoint,
        "get_assessment_feedback_for_script",
        fake_service,
    )

    response = await client.get(
        f"{BASE_URL}/scripts/500",
        headers=auth_headers(
            teacher_user,
        ),
    )

    assert response.status_code == 200, response.text
    assert received_script_ids == [500]
    assert response.json()["script_id"] == 500


@pytest.mark.asyncio
async def test_get_feedback_propagates_not_found(
    client: AsyncClient,
    teacher_user,
    auth_headers,
    monkeypatch,
):
    async def fake_service(
        db,
        current_user,
        *,
        feedback_id,
        school_id,
    ):
        raise HTTPException(
            status_code=404,
            detail="Assessment feedback not found.",
        )

    monkeypatch.setattr(
        endpoint,
        "get_assessment_feedback",
        fake_service,
    )

    response = await client.get(
        f"{BASE_URL}/999",
        headers=auth_headers(
            teacher_user,
        ),
    )

    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Overall PATCH semantics
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_patch_feedback_forwards_only_supplied_fields(
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
        feedback_id,
        school_id,
        **kwargs,
    ):
        received["feedback_id"] = feedback_id
        received["school_id"] = school_id
        received["kwargs"] = kwargs

        return _feedback_payload(
            feedback_id=feedback_id,
            school_id=current_user.school_id,
            overall_comment=kwargs.get(
                "overall_comment",
                "Existing comment",
            ),
            created_by_id=current_user.id,
        )

    monkeypatch.setattr(
        endpoint,
        "update_assessment_feedback",
        fake_service,
    )

    response = await client.patch(
        f"{BASE_URL}/1",
        json={
            "overall_comment": "Updated.",
        },
        headers=auth_headers(
            teacher_user,
        ),
    )

    assert response.status_code == 200, response.text
    assert received["kwargs"] == {
        "overall_comment": "Updated.",
    }


@pytest.mark.asyncio
async def test_patch_feedback_forwards_explicit_nulls(
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
        feedback_id,
        school_id,
        **kwargs,
    ):
        received.update(
            kwargs,
        )

        return _feedback_payload(
            feedback_id=feedback_id,
            school_id=current_user.school_id,
            overall_comment=None,
            strengths=None,
            areas_for_improvement=None,
            next_steps=None,
            created_by_id=current_user.id,
        )

    monkeypatch.setattr(
        endpoint,
        "update_assessment_feedback",
        fake_service,
    )

    response = await client.patch(
        f"{BASE_URL}/1",
        json={
            "overall_comment": None,
            "strengths": None,
            "areas_for_improvement": None,
            "next_steps": None,
        },
        headers=auth_headers(
            teacher_user,
        ),
    )

    assert response.status_code == 200, response.text

    assert received == {
        "overall_comment": None,
        "strengths": None,
        "areas_for_improvement": None,
        "next_steps": None,
    }


@pytest.mark.asyncio
async def test_patch_feedback_empty_object_preserves_fields(
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
        feedback_id,
        school_id,
        **kwargs,
    ):
        received_kwargs.append(
            kwargs,
        )

        return _feedback_payload(
            feedback_id=feedback_id,
            school_id=current_user.school_id,
            created_by_id=current_user.id,
        )

    monkeypatch.setattr(
        endpoint,
        "update_assessment_feedback",
        fake_service,
    )

    response = await client.patch(
        f"{BASE_URL}/1",
        json={},
        headers=auth_headers(
            teacher_user,
        ),
    )

    assert response.status_code == 200, response.text
    assert received_kwargs == [{}]


@pytest.mark.asyncio
async def test_patch_feedback_propagates_finalised_conflict(
    client: AsyncClient,
    teacher_user,
    auth_headers,
    monkeypatch,
):
    async def fake_service(
        db,
        current_user,
        *,
        feedback_id,
        school_id,
        **kwargs,
    ):
        raise HTTPException(
            status_code=409,
            detail="Finalised assessment feedback must be reopened before editing.",
        )

    monkeypatch.setattr(
        endpoint,
        "update_assessment_feedback",
        fake_service,
    )

    response = await client.patch(
        f"{BASE_URL}/1",
        json={
            "overall_comment": "Changed.",
        },
        headers=auth_headers(
            teacher_user,
        ),
    )

    assert response.status_code == 409


# ---------------------------------------------------------------------------
# Finalise / reopen
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_finalise_feedback(
    client: AsyncClient,
    teacher_user,
    auth_headers,
    monkeypatch,
):
    finalised_at = datetime(
        2026,
        9,
        10,
        12,
        0,
        tzinfo=timezone.utc,
    )

    async def fake_service(
        db,
        current_user,
        *,
        feedback_id,
        school_id,
    ):
        return {
            "id": feedback_id,
            "status": "finalised",
            "finalised_at": finalised_at,
            "finalised_by_id": current_user.id,
            "finalised_by_name": "Teacher One",
        }

    monkeypatch.setattr(
        endpoint,
        "finalise_assessment_feedback",
        fake_service,
    )

    response = await client.post(
        f"{BASE_URL}/1/finalise",
        headers=auth_headers(
            teacher_user,
        ),
    )

    assert response.status_code == 200, response.text

    payload = response.json()

    assert payload["id"] == 1
    assert payload["status"] == "finalised"
    assert payload["finalised_by_id"] == teacher_user.id


@pytest.mark.asyncio
async def test_finalise_feedback_propagates_conflict(
    client: AsyncClient,
    teacher_user,
    auth_headers,
    monkeypatch,
):
    async def fake_service(
        db,
        current_user,
        *,
        feedback_id,
        school_id,
    ):
        raise HTTPException(
            status_code=409,
            detail="Assessment feedback cannot be finalised while empty.",
        )

    monkeypatch.setattr(
        endpoint,
        "finalise_assessment_feedback",
        fake_service,
    )

    response = await client.post(
        f"{BASE_URL}/1/finalise",
        headers=auth_headers(
            teacher_user,
        ),
    )

    assert response.status_code == 409


@pytest.mark.asyncio
async def test_reopen_feedback(
    client: AsyncClient,
    teacher_user,
    auth_headers,
    monkeypatch,
):
    async def fake_service(
        db,
        current_user,
        *,
        feedback_id,
        school_id,
    ):
        return {
            "id": feedback_id,
            "status": "draft",
            "finalised_at": None,
            "finalised_by_id": None,
            "finalised_by_name": None,
        }

    monkeypatch.setattr(
        endpoint,
        "reopen_assessment_feedback",
        fake_service,
    )

    response = await client.post(
        f"{BASE_URL}/1/reopen",
        headers=auth_headers(
            teacher_user,
        ),
    )

    assert response.status_code == 200, response.text

    payload = response.json()

    assert payload["status"] == "draft"
    assert payload["finalised_at"] is None


# ---------------------------------------------------------------------------
# Overall delete
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_delete_feedback_returns_204(
    client: AsyncClient,
    teacher_user,
    auth_headers,
    monkeypatch,
):
    received: list[int] = []

    async def fake_service(
        db,
        current_user,
        *,
        feedback_id,
        school_id,
    ):
        received.append(
            feedback_id,
        )

    monkeypatch.setattr(
        endpoint,
        "delete_assessment_feedback",
        fake_service,
    )

    response = await client.delete(
        f"{BASE_URL}/88",
        headers=auth_headers(
            teacher_user,
        ),
    )

    assert response.status_code == 204
    assert response.content == b""
    assert received == [88]


@pytest.mark.asyncio
async def test_delete_feedback_propagates_conflict(
    client: AsyncClient,
    teacher_user,
    auth_headers,
    monkeypatch,
):
    async def fake_service(
        db,
        current_user,
        *,
        feedback_id,
        school_id,
    ):
        raise HTTPException(
            status_code=409,
            detail="Finalised assessment feedback must be reopened before deletion.",
        )

    monkeypatch.setattr(
        endpoint,
        "delete_assessment_feedback",
        fake_service,
    )

    response = await client.delete(
        f"{BASE_URL}/1",
        headers=auth_headers(
            teacher_user,
        ),
    )

    assert response.status_code == 409


# ---------------------------------------------------------------------------
# Question feedback create
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_question_feedback(
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
        school_id,
        response_id,
        feedback_text,
        strength,
        improvement,
        include_with_result,
    ):
        received.update(
            {
                "school_id": school_id,
                "response_id": response_id,
                "feedback_text": feedback_text,
                "strength": strength,
                "improvement": improvement,
                "include_with_result": include_with_result,
            }
        )

        return _question_feedback_payload(
            school_id=current_user.school_id,
            response_id=response_id,
            feedback_text=feedback_text,
            strength=strength,
            improvement=improvement,
            include_with_result=include_with_result,
            created_by_id=current_user.id,
        )

    monkeypatch.setattr(
        endpoint,
        "create_assessment_question_feedback",
        fake_service,
    )

    response = await client.post(
        f"{BASE_URL}/questions",
        json={
            "response_id": 600,
            "feedback_text": "Correct method.",
            "strength": "Good substitution.",
            "improvement": "Add the unit.",
        },
        headers=auth_headers(
            teacher_user,
        ),
    )

    assert response.status_code == 201, response.text

    assert received == {
        "school_id": None,
        "response_id": 600,
        "feedback_text": "Correct method.",
        "strength": "Good substitution.",
        "improvement": "Add the unit.",
        "include_with_result": True,
    }


@pytest.mark.asyncio
async def test_create_question_feedback_propagates_duplicate_conflict(
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
            detail="Assessment question feedback already exists for this response.",
        )

    monkeypatch.setattr(
        endpoint,
        "create_assessment_question_feedback",
        fake_service,
    )

    response = await client.post(
        f"{BASE_URL}/questions",
        json={
            "response_id": 600,
            "feedback_text": "Good answer.",
        },
        headers=auth_headers(
            teacher_user,
        ),
    )

    assert response.status_code == 409


# ---------------------------------------------------------------------------
# Question feedback reads
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_question_feedback(
    client: AsyncClient,
    teacher_user,
    auth_headers,
    monkeypatch,
):
    async def fake_service(
        db,
        current_user,
        *,
        question_feedback_id,
        school_id,
    ):
        return _question_feedback_payload(
            question_feedback_id=question_feedback_id,
            school_id=current_user.school_id,
            created_by_id=current_user.id,
        )

    monkeypatch.setattr(
        endpoint,
        "get_assessment_question_feedback",
        fake_service,
    )

    response = await client.get(
        f"{BASE_URL}/questions/2",
        headers=auth_headers(
            teacher_user,
        ),
    )

    assert response.status_code == 200, response.text
    assert response.json()["id"] == 2


@pytest.mark.asyncio
async def test_get_question_feedback_for_response(
    client: AsyncClient,
    teacher_user,
    auth_headers,
    monkeypatch,
):
    received_response_ids: list[int] = []

    async def fake_service(
        db,
        current_user,
        *,
        response_id,
        school_id,
    ):
        received_response_ids.append(
            response_id,
        )

        return _question_feedback_payload(
            response_id=response_id,
            school_id=current_user.school_id,
            created_by_id=current_user.id,
        )

    monkeypatch.setattr(
        endpoint,
        "get_assessment_question_feedback_for_response",
        fake_service,
    )

    response = await client.get(
        f"{BASE_URL}/responses/600/question-feedback",
        headers=auth_headers(
            teacher_user,
        ),
    )

    assert response.status_code == 200, response.text
    assert received_response_ids == [600]


# ---------------------------------------------------------------------------
# Question PATCH semantics
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_patch_question_feedback_forwards_only_supplied_fields(
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
        question_feedback_id,
        school_id,
        **kwargs,
    ):
        received["kwargs"] = kwargs

        return _question_feedback_payload(
            question_feedback_id=question_feedback_id,
            school_id=current_user.school_id,
            feedback_text=kwargs.get(
                "feedback_text",
                "Existing",
            ),
            created_by_id=current_user.id,
        )

    monkeypatch.setattr(
        endpoint,
        "update_assessment_question_feedback",
        fake_service,
    )

    response = await client.patch(
        f"{BASE_URL}/questions/2",
        json={
            "feedback_text": "Updated.",
        },
        headers=auth_headers(
            teacher_user,
        ),
    )

    assert response.status_code == 200, response.text
    assert received["kwargs"] == {
        "feedback_text": "Updated.",
    }


@pytest.mark.asyncio
async def test_patch_question_feedback_forwards_explicit_nulls(
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
        question_feedback_id,
        school_id,
        **kwargs,
    ):
        received.update(
            kwargs,
        )

        return _question_feedback_payload(
            question_feedback_id=question_feedback_id,
            school_id=current_user.school_id,
            feedback_text=None,
            strength=None,
            improvement=None,
            created_by_id=current_user.id,
        )

    monkeypatch.setattr(
        endpoint,
        "update_assessment_question_feedback",
        fake_service,
    )

    response = await client.patch(
        f"{BASE_URL}/questions/2",
        json={
            "feedback_text": None,
            "strength": None,
            "improvement": None,
        },
        headers=auth_headers(
            teacher_user,
        ),
    )

    assert response.status_code == 200, response.text

    assert received == {
        "feedback_text": None,
        "strength": None,
        "improvement": None,
    }


@pytest.mark.asyncio
async def test_patch_question_feedback_empty_object_preserves_fields(
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
        question_feedback_id,
        school_id,
        **kwargs,
    ):
        received_kwargs.append(
            kwargs,
        )

        return _question_feedback_payload(
            question_feedback_id=question_feedback_id,
            school_id=current_user.school_id,
            created_by_id=current_user.id,
        )

    monkeypatch.setattr(
        endpoint,
        "update_assessment_question_feedback",
        fake_service,
    )

    response = await client.patch(
        f"{BASE_URL}/questions/2",
        json={},
        headers=auth_headers(
            teacher_user,
        ),
    )

    assert response.status_code == 200, response.text
    assert received_kwargs == [{}]


# ---------------------------------------------------------------------------
# Question delete
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_delete_question_feedback_returns_204(
    client: AsyncClient,
    teacher_user,
    auth_headers,
    monkeypatch,
):
    received: list[int] = []

    async def fake_service(
        db,
        current_user,
        *,
        question_feedback_id,
        school_id,
    ):
        received.append(
            question_feedback_id,
        )

    monkeypatch.setattr(
        endpoint,
        "delete_assessment_question_feedback",
        fake_service,
    )

    response = await client.delete(
        f"{BASE_URL}/questions/2",
        headers=auth_headers(
            teacher_user,
        ),
    )

    assert response.status_code == 204
    assert response.content == b""
    assert received == [2]


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_feedback_script_id_must_be_positive(
    client: AsyncClient,
    teacher_user,
    auth_headers,
):
    response = await client.post(
        BASE_URL,
        json={
            "script_id": 0,
            "overall_comment": "Good work.",
        },
        headers=auth_headers(
            teacher_user,
        ),
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_feedback_school_id_must_be_positive(
    client: AsyncClient,
    platform_admin_user,
    auth_headers,
):
    response = await client.post(
        BASE_URL,
        json={
            "school_id": 0,
            "script_id": 500,
            "overall_comment": "Good work.",
        },
        headers=auth_headers(
            platform_admin_user,
        ),
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_question_feedback_response_id_must_be_positive(
    client: AsyncClient,
    teacher_user,
    auth_headers,
):
    response = await client.post(
        f"{BASE_URL}/questions",
        json={
            "response_id": 0,
            "feedback_text": "Good answer.",
        },
        headers=auth_headers(
            teacher_user,
        ),
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_get_feedback_school_query_must_be_positive(
    client: AsyncClient,
    teacher_user,
    auth_headers,
):
    response = await client.get(
        f"{BASE_URL}/1",
        params={
            "school_id": 0,
        },
        headers=auth_headers(
            teacher_user,
        ),
    )

    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Path validation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_feedback_id_must_be_integer(
    client: AsyncClient,
    teacher_user,
    auth_headers,
):
    response = await client.get(
        f"{BASE_URL}/not-an-integer",
        headers=auth_headers(
            teacher_user,
        ),
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_script_id_must_be_integer(
    client: AsyncClient,
    teacher_user,
    auth_headers,
):
    response = await client.get(
        f"{BASE_URL}/scripts/not-an-integer",
        headers=auth_headers(
            teacher_user,
        ),
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_question_feedback_id_must_be_integer(
    client: AsyncClient,
    teacher_user,
    auth_headers,
):
    response = await client.get(
        f"{BASE_URL}/questions/not-an-integer",
        headers=auth_headers(
            teacher_user,
        ),
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_response_id_must_be_integer(
    client: AsyncClient,
    teacher_user,
    auth_headers,
):
    response = await client.get(
        f"{BASE_URL}/responses/not-an-integer/question-feedback",
        headers=auth_headers(
            teacher_user,
        ),
    )

    assert response.status_code == 422
