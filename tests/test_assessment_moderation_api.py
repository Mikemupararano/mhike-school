from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.v1.endpoints import assessment_moderation
from app.models.assessment_moderation import (
    AssessmentModerationItemOutcome,
    AssessmentModerationOutcome,
    AssessmentModerationReviewStatus,
    AssessmentModerationSamplingMethod,
)


def _now() -> datetime:
    return datetime.now(
        timezone.utc,
    )


def _review(
    *,
    review_id: int = 1,
    script_id: int = 40,
    status: AssessmentModerationReviewStatus = (
        AssessmentModerationReviewStatus.PENDING
    ),
    outcome: AssessmentModerationOutcome | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        id=review_id,
        school_id=10,
        assessment_id=20,
        candidate_id=30,
        script_id=script_id,
        review_number=1,
        status=status,
        outcome=outcome,
        sampling_method=AssessmentModerationSamplingMethod.MANUAL,
        moderator_id=100,
        initiated_by_id=100,
        reason="QA sample",
        notes=None,
        sample_description=None,
        created_at=_now(),
        started_at=None,
        completed_at=None,
        cancelled_at=None,
        cancelled_by_id=None,
        cancellation_reason=None,
        items=[],
    )


def _item(
    *,
    item_id: int = 1,
    review_id: int = 1,
    outcome: AssessmentModerationItemOutcome = (
        AssessmentModerationItemOutcome.CONFIRMED
    ),
) -> SimpleNamespace:
    return SimpleNamespace(
        id=item_id,
        review_id=review_id,
        response_id=200,
        marking_decision_id=300,
        outcome=outcome,
        mark_before_snapshot=Decimal("5.00"),
        mark_after_snapshot=Decimal("5.00"),
        maximum_mark_snapshot=Decimal("10.00"),
        mark_changed=False,
        decision_status_before_snapshot="marked",
        decision_status_after_snapshot="reviewed",
        moderator_comment="Confirmed.",
        evidence_notes=None,
        reviewed_by_id=100,
        reviewed_at=_now(),
    )


class _FakeDB:
    pass


@pytest.fixture
def app() -> FastAPI:
    test_app = FastAPI()

    test_app.include_router(
        assessment_moderation.router,
    )

    async def override_db():
        yield _FakeDB()

    async def override_user():
        return SimpleNamespace(
            id=100,
            school_id=10,
            roles=[
                "school_admin",
            ],
        )

    test_app.dependency_overrides[assessment_moderation.get_db] = override_db

    test_app.dependency_overrides[assessment_moderation.get_current_user] = (
        override_user
    )

    return test_app


@pytest.fixture
def client(
    app: FastAPI,
) -> TestClient:
    return TestClient(
        app,
    )


def test_router_exposes_eight_routes() -> None:
    assert (
        len(
            assessment_moderation.router.routes,
        )
        == 8
    )


def test_create_review_returns_201(
    client: TestClient,
    monkeypatch,
) -> None:
    review = _review()

    captured: dict[str, Any] = {}

    async def fake_create(
        db,
        current_user,
        script_id,
        *,
        moderator_id,
        sampling_method,
        reason,
        notes,
        sample_description,
    ):
        captured.update(
            {
                "db": db,
                "current_user": current_user,
                "script_id": script_id,
                "moderator_id": moderator_id,
                "sampling_method": sampling_method,
                "reason": reason,
                "notes": notes,
                "sample_description": sample_description,
            },
        )

        return review

    monkeypatch.setattr(
        assessment_moderation,
        "create_moderation_review",
        fake_create,
    )

    response = client.post(
        "/assessment-moderation/scripts/40/reviews",
        json={
            "moderator_id": 100,
            "sampling_method": "manual",
            "reason": "QA sample",
        },
    )

    assert response.status_code == 201

    body = response.json()

    assert body["id"] == 1
    assert body["script_id"] == 40
    assert body["status"] == "pending"
    assert body["sampling_method"] == "manual"

    assert captured["script_id"] == 40
    assert captured["moderator_id"] == 100
    assert captured["sampling_method"] == AssessmentModerationSamplingMethod.MANUAL
    assert captured["reason"] == "QA sample"


def test_create_review_rejects_invalid_moderator_id(
    client: TestClient,
) -> None:
    response = client.post(
        "/assessment-moderation/scripts/40/reviews",
        json={
            "moderator_id": 0,
        },
    )

    assert response.status_code == 422


def test_create_review_rejects_unknown_fields(
    client: TestClient,
) -> None:
    response = client.post(
        "/assessment-moderation/scripts/40/reviews",
        json={
            "moderator_id": 100,
            "school_id": 999,
        },
    )

    assert response.status_code == 422


def test_get_review_returns_full_review(
    client: TestClient,
    monkeypatch,
) -> None:
    review = _review()

    review.items = [
        _item(),
    ]

    async def fake_get(
        db,
        current_user,
        review_id,
    ):
        del db
        del current_user

        assert review_id == 1

        return review

    monkeypatch.setattr(
        assessment_moderation,
        "get_moderation_review",
        fake_get,
    )

    response = client.get(
        "/assessment-moderation/reviews/1",
    )

    assert response.status_code == 200

    body = response.json()

    assert body["id"] == 1
    assert (
        len(
            body["items"],
        )
        == 1
    )
    assert body["items"][0]["response_id"] == 200


def test_list_script_reviews_returns_collection(
    client: TestClient,
    monkeypatch,
) -> None:
    reviews = [
        _review(
            review_id=1,
        ),
        _review(
            review_id=2,
        ),
    ]

    async def fake_list(
        db,
        current_user,
        script_id,
    ):
        del db
        del current_user

        assert script_id == 40

        return reviews

    monkeypatch.setattr(
        assessment_moderation,
        "list_script_moderation_reviews",
        fake_list,
    )

    response = client.get(
        "/assessment-moderation/scripts/40/reviews",
    )

    assert response.status_code == 200

    body = response.json()

    assert body["total"] == 2
    assert (
        len(
            body["items"],
        )
        == 2
    )
    assert body["items"][0]["id"] == 1
    assert body["items"][1]["id"] == 2


def test_list_assessment_reviews_passes_filters(
    client: TestClient,
    monkeypatch,
) -> None:
    captured: dict[str, Any] = {}

    reviews = [
        _review(
            status=AssessmentModerationReviewStatus.COMPLETED,
            outcome=AssessmentModerationOutcome.CONFIRMED,
        ),
    ]

    async def fake_list(
        db,
        current_user,
        assessment_id,
        *,
        review_status=None,
        outcome=None,
    ):
        del db
        del current_user

        captured["assessment_id"] = assessment_id
        captured["review_status"] = review_status
        captured["outcome"] = outcome

        return reviews

    monkeypatch.setattr(
        assessment_moderation,
        "list_assessment_moderation_reviews",
        fake_list,
    )

    response = client.get(
        (
            "/assessment-moderation/assessments/20/reviews"
            "?status=completed&outcome=confirmed"
        ),
    )

    assert response.status_code == 200

    body = response.json()

    assert body["total"] == 1

    assert captured["assessment_id"] == 20
    assert captured["review_status"] == AssessmentModerationReviewStatus.COMPLETED
    assert captured["outcome"] == AssessmentModerationOutcome.CONFIRMED


def test_list_assessment_reviews_rejects_invalid_status(
    client: TestClient,
) -> None:
    response = client.get(
        ("/assessment-moderation/assessments/20/reviews" "?status=invalid"),
    )

    assert response.status_code == 422


def test_start_review_delegates_to_service(
    client: TestClient,
    monkeypatch,
) -> None:
    review = _review(
        status=AssessmentModerationReviewStatus.IN_PROGRESS,
    )

    review.started_at = _now()

    async def fake_start(
        db,
        current_user,
        review_id,
    ):
        del db
        del current_user

        assert review_id == 1

        return review

    monkeypatch.setattr(
        assessment_moderation,
        "start_moderation_review",
        fake_start,
    )

    response = client.post(
        "/assessment-moderation/reviews/1/start",
    )

    assert response.status_code == 200
    assert response.json()["status"] == "in_progress"


def test_create_review_item_returns_201(
    client: TestClient,
    monkeypatch,
) -> None:
    item = _item(
        outcome=AssessmentModerationItemOutcome.ADJUSTED,
    )

    item.mark_after_snapshot = Decimal("6.00")
    item.mark_changed = True

    captured: dict[str, Any] = {}

    async def fake_add(
        db,
        current_user,
        review_id,
        *,
        response_id,
        marking_decision_id,
        outcome,
        mark_after,
        moderator_comment,
        evidence_notes,
    ):
        del db
        del current_user

        captured.update(
            {
                "review_id": review_id,
                "response_id": response_id,
                "marking_decision_id": marking_decision_id,
                "outcome": outcome,
                "mark_after": mark_after,
                "moderator_comment": moderator_comment,
                "evidence_notes": evidence_notes,
            },
        )

        return item

    monkeypatch.setattr(
        assessment_moderation,
        "add_moderation_item",
        fake_add,
    )

    response = client.post(
        "/assessment-moderation/reviews/1/items",
        json={
            "response_id": 200,
            "marking_decision_id": 300,
            "outcome": "adjusted",
            "mark_after": "6.00",
            "moderator_comment": "One mark added.",
            "evidence_notes": "Mark scheme checked.",
        },
    )

    assert response.status_code == 201

    body = response.json()

    assert body["review_id"] == 1
    assert body["outcome"] == "adjusted"
    assert body["mark_changed"] is True
    assert body["mark_after_snapshot"] == "6.00"

    assert captured["review_id"] == 1
    assert captured["response_id"] == 200
    assert captured["marking_decision_id"] == 300
    assert captured["outcome"] == AssessmentModerationItemOutcome.ADJUSTED
    assert captured["mark_after"] == Decimal("6.00")


def test_create_review_item_rejects_negative_mark(
    client: TestClient,
) -> None:
    response = client.post(
        "/assessment-moderation/reviews/1/items",
        json={
            "response_id": 200,
            "marking_decision_id": 300,
            "outcome": "adjusted",
            "mark_after": "-1.00",
        },
    )

    assert response.status_code == 422


def test_create_review_item_rejects_snapshot_injection(
    client: TestClient,
) -> None:
    response = client.post(
        "/assessment-moderation/reviews/1/items",
        json={
            "response_id": 200,
            "marking_decision_id": 300,
            "outcome": "confirmed",
            "mark_before_snapshot": "5.00",
        },
    )

    assert response.status_code == 422


def test_complete_review_delegates_outcome_and_notes(
    client: TestClient,
    monkeypatch,
) -> None:
    review = _review(
        status=AssessmentModerationReviewStatus.COMPLETED,
        outcome=AssessmentModerationOutcome.CONFIRMED,
    )

    review.completed_at = _now()

    captured: dict[str, Any] = {}

    async def fake_complete(
        db,
        current_user,
        review_id,
        *,
        outcome,
        notes,
    ):
        del db
        del current_user

        captured["review_id"] = review_id
        captured["outcome"] = outcome
        captured["notes"] = notes

        return review

    monkeypatch.setattr(
        assessment_moderation,
        "complete_moderation_review",
        fake_complete,
    )

    response = client.post(
        "/assessment-moderation/reviews/1/complete",
        json={
            "outcome": "confirmed",
            "notes": "Moderation complete.",
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert body["status"] == "completed"
    assert body["outcome"] == "confirmed"

    assert captured["review_id"] == 1
    assert captured["outcome"] == AssessmentModerationOutcome.CONFIRMED
    assert captured["notes"] == "Moderation complete."


def test_complete_review_rejects_invalid_outcome(
    client: TestClient,
) -> None:
    response = client.post(
        "/assessment-moderation/reviews/1/complete",
        json={
            "outcome": "invalid",
        },
    )

    assert response.status_code == 422


def test_cancel_review_delegates_reason(
    client: TestClient,
    monkeypatch,
) -> None:
    review = _review(
        status=AssessmentModerationReviewStatus.CANCELLED,
    )

    review.cancelled_at = _now()
    review.cancelled_by_id = 100
    review.cancellation_reason = "Created in error."

    captured: dict[str, Any] = {}

    async def fake_cancel(
        db,
        current_user,
        review_id,
        *,
        cancellation_reason,
    ):
        del db
        del current_user

        captured["review_id"] = review_id
        captured["cancellation_reason"] = cancellation_reason

        return review

    monkeypatch.setattr(
        assessment_moderation,
        "cancel_moderation_review",
        fake_cancel,
    )

    response = client.post(
        "/assessment-moderation/reviews/1/cancel",
        json={
            "cancellation_reason": "Created in error.",
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert body["status"] == "cancelled"
    assert body["cancelled_by_id"] == 100
    assert body["cancellation_reason"] == "Created in error."

    assert captured["review_id"] == 1
    assert captured["cancellation_reason"] == "Created in error."


def test_cancel_review_rejects_empty_reason(
    client: TestClient,
) -> None:
    response = client.post(
        "/assessment-moderation/reviews/1/cancel",
        json={
            "cancellation_reason": "",
        },
    )

    assert response.status_code == 422


def test_create_and_list_script_routes_do_not_conflict(
    client: TestClient,
    monkeypatch,
) -> None:
    review = _review()

    async def fake_create(
        *args,
        **kwargs,
    ):
        return review

    async def fake_list(
        *args,
        **kwargs,
    ):
        return [
            review,
        ]

    monkeypatch.setattr(
        assessment_moderation,
        "create_moderation_review",
        fake_create,
    )
    monkeypatch.setattr(
        assessment_moderation,
        "list_script_moderation_reviews",
        fake_list,
    )

    post_response = client.post(
        "/assessment-moderation/scripts/40/reviews",
        json={
            "moderator_id": 100,
        },
    )

    get_response = client.get(
        "/assessment-moderation/scripts/40/reviews",
    )

    assert post_response.status_code == 201
    assert get_response.status_code == 200
    assert get_response.json()["total"] == 1
