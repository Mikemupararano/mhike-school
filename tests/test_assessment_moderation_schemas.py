from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from app.models.assessment_moderation import (
    AssessmentModerationItemOutcome,
    AssessmentModerationOutcome,
    AssessmentModerationReviewStatus,
    AssessmentModerationSamplingMethod,
)
from app.schemas.assessment_moderation import (
    AssessmentModerationItemCreate,
    AssessmentModerationItemRead,
    AssessmentModerationReviewCancel,
    AssessmentModerationReviewComplete,
    AssessmentModerationReviewCreate,
    AssessmentModerationReviewList,
    AssessmentModerationReviewRead,
    AssessmentModerationReviewSummary,
)


def _now() -> datetime:
    return datetime.now(
        timezone.utc,
    )


def test_review_create_defaults_to_manual_sampling() -> None:
    payload = AssessmentModerationReviewCreate(
        moderator_id=10,
    )

    assert payload.moderator_id == 10
    assert payload.sampling_method == AssessmentModerationSamplingMethod.MANUAL
    assert payload.reason is None
    assert payload.notes is None
    assert payload.sample_description is None


def test_review_create_accepts_explicit_sampling_method() -> None:
    payload = AssessmentModerationReviewCreate(
        moderator_id=10,
        sampling_method=AssessmentModerationSamplingMethod.TARGETED,
        reason="Grade-boundary sample",
        notes="Priority review",
        sample_description="Questions 2 and 4",
    )

    assert payload.sampling_method == AssessmentModerationSamplingMethod.TARGETED
    assert payload.reason == "Grade-boundary sample"
    assert payload.notes == "Priority review"
    assert payload.sample_description == "Questions 2 and 4"


def test_review_create_rejects_non_positive_moderator_id() -> None:
    with pytest.raises(
        ValidationError,
    ):
        AssessmentModerationReviewCreate(
            moderator_id=0,
        )


def test_review_create_rejects_unknown_fields() -> None:
    with pytest.raises(
        ValidationError,
    ):
        AssessmentModerationReviewCreate(
            moderator_id=10,
            school_id=99,
        )


def test_review_create_rejects_overlong_reason() -> None:
    with pytest.raises(
        ValidationError,
    ):
        AssessmentModerationReviewCreate(
            moderator_id=10,
            reason="x" * 1001,
        )


def test_review_complete_accepts_valid_outcome() -> None:
    payload = AssessmentModerationReviewComplete(
        outcome=AssessmentModerationOutcome.CONFIRMED,
        notes="Sampling complete.",
    )

    assert payload.outcome == AssessmentModerationOutcome.CONFIRMED
    assert payload.notes == "Sampling complete."


def test_review_complete_rejects_unknown_fields() -> None:
    with pytest.raises(
        ValidationError,
    ):
        AssessmentModerationReviewComplete(
            outcome=AssessmentModerationOutcome.CONFIRMED,
            completed_by_id=10,
        )


def test_review_cancel_accepts_reason() -> None:
    payload = AssessmentModerationReviewCancel(
        cancellation_reason="Created in error.",
    )

    assert payload.cancellation_reason == "Created in error."


def test_review_cancel_rejects_empty_reason() -> None:
    with pytest.raises(
        ValidationError,
    ):
        AssessmentModerationReviewCancel(
            cancellation_reason="",
        )


def test_review_cancel_rejects_overlong_reason() -> None:
    with pytest.raises(
        ValidationError,
    ):
        AssessmentModerationReviewCancel(
            cancellation_reason="x" * 1001,
        )


def test_item_create_accepts_confirmed_without_mark_after() -> None:
    payload = AssessmentModerationItemCreate(
        response_id=20,
        marking_decision_id=30,
        expected_revision=0,
        outcome=AssessmentModerationItemOutcome.CONFIRMED,
    )

    assert payload.response_id == 20
    assert payload.marking_decision_id == 30
    assert payload.outcome == AssessmentModerationItemOutcome.CONFIRMED
    assert payload.mark_after is None


def test_item_create_accepts_decimal_mark() -> None:
    payload = AssessmentModerationItemCreate(
        response_id=20,
        marking_decision_id=30,
        expected_revision=0,
        outcome=AssessmentModerationItemOutcome.ADJUSTED,
        mark_after=Decimal("7.50"),
    )

    assert payload.mark_after == Decimal("7.50")


def test_item_create_coerces_numeric_string_to_decimal() -> None:
    payload = AssessmentModerationItemCreate(
        response_id=20,
        marking_decision_id=30,
        expected_revision=0,
        outcome=AssessmentModerationItemOutcome.ADJUSTED,
        mark_after="6.25",
    )

    assert payload.mark_after == Decimal("6.25")


def test_item_create_rejects_negative_mark() -> None:
    with pytest.raises(
        ValidationError,
    ):
        AssessmentModerationItemCreate(
            response_id=20,
            marking_decision_id=30,
            outcome=AssessmentModerationItemOutcome.ADJUSTED,
            mark_after=Decimal("-1.00"),
        )


def test_item_create_rejects_non_positive_response_id() -> None:
    with pytest.raises(
        ValidationError,
    ):
        AssessmentModerationItemCreate(
            response_id=0,
            marking_decision_id=30,
            outcome=AssessmentModerationItemOutcome.CONFIRMED,
        )


def test_item_create_rejects_non_positive_decision_id() -> None:
    with pytest.raises(
        ValidationError,
    ):
        AssessmentModerationItemCreate(
            response_id=20,
            marking_decision_id=0,
            outcome=AssessmentModerationItemOutcome.CONFIRMED,
        )


def test_item_create_rejects_too_many_decimal_places() -> None:
    with pytest.raises(
        ValidationError,
    ):
        AssessmentModerationItemCreate(
            response_id=20,
            marking_decision_id=30,
            outcome=AssessmentModerationItemOutcome.ADJUSTED,
            mark_after=Decimal("1.234"),
        )


def test_item_create_rejects_too_many_digits() -> None:
    with pytest.raises(
        ValidationError,
    ):
        AssessmentModerationItemCreate(
            response_id=20,
            marking_decision_id=30,
            outcome=AssessmentModerationItemOutcome.ADJUSTED,
            mark_after=Decimal("1234567.89"),
        )


def test_item_create_rejects_snapshot_injection() -> None:
    with pytest.raises(
        ValidationError,
    ):
        AssessmentModerationItemCreate(
            response_id=20,
            marking_decision_id=30,
            outcome=AssessmentModerationItemOutcome.CONFIRMED,
            mark_before_snapshot=Decimal("5.00"),
        )


def test_item_read_supports_attribute_models() -> None:
    reviewed_at = _now()

    source = SimpleNamespace(
        id=1,
        review_id=2,
        response_id=3,
        marking_decision_id=4,
        outcome=AssessmentModerationItemOutcome.ADJUSTED,
        mark_before_snapshot=Decimal("5.00"),
        mark_after_snapshot=Decimal("6.00"),
        maximum_mark_snapshot=Decimal("10.00"),
        mark_changed=True,
        decision_status_before_snapshot="marked",
        decision_status_after_snapshot="reviewed",
        moderator_comment="One mark added.",
        evidence_notes="Mark scheme checked.",
        reviewed_by_id=5,
        reviewed_at=reviewed_at,
    )

    result = AssessmentModerationItemRead.model_validate(
        source,
    )

    assert result.id == 1
    assert result.review_id == 2
    assert result.mark_changed is True
    assert result.mark_after_snapshot == Decimal("6.00")
    assert result.reviewed_at == reviewed_at


def test_review_read_supports_attribute_models_with_items() -> None:
    created_at = _now()
    reviewed_at = _now()

    item = SimpleNamespace(
        id=100,
        review_id=1,
        response_id=200,
        marking_decision_id=300,
        outcome=AssessmentModerationItemOutcome.CONFIRMED,
        mark_before_snapshot=Decimal("5.00"),
        mark_after_snapshot=Decimal("5.00"),
        maximum_mark_snapshot=Decimal("10.00"),
        mark_changed=False,
        decision_status_before_snapshot="marked",
        decision_status_after_snapshot="reviewed",
        moderator_comment="Confirmed.",
        evidence_notes=None,
        reviewed_by_id=400,
        reviewed_at=reviewed_at,
    )

    review = SimpleNamespace(
        id=1,
        school_id=10,
        assessment_id=20,
        candidate_id=30,
        script_id=40,
        review_number=1,
        status=AssessmentModerationReviewStatus.IN_PROGRESS,
        outcome=None,
        sampling_method=AssessmentModerationSamplingMethod.TARGETED,
        moderator_id=50,
        initiated_by_id=60,
        reason="QA sample",
        notes=None,
        sample_description="Question 1",
        created_at=created_at,
        started_at=created_at,
        completed_at=None,
        cancelled_at=None,
        cancelled_by_id=None,
        cancellation_reason=None,
        items=[
            item,
        ],
    )

    result = AssessmentModerationReviewRead.model_validate(
        review,
    )

    assert result.id == 1
    assert result.school_id == 10
    assert result.status == AssessmentModerationReviewStatus.IN_PROGRESS
    assert len(result.items) == 1
    assert result.items[0].response_id == 200


def test_review_summary_omits_item_evidence() -> None:
    created_at = _now()

    source = SimpleNamespace(
        id=1,
        school_id=10,
        assessment_id=20,
        candidate_id=30,
        script_id=40,
        review_number=2,
        status=AssessmentModerationReviewStatus.COMPLETED,
        outcome=AssessmentModerationOutcome.CONFIRMED,
        sampling_method=AssessmentModerationSamplingMethod.RANDOM_SAMPLE,
        moderator_id=50,
        initiated_by_id=60,
        reason="Routine sample",
        created_at=created_at,
        started_at=created_at,
        completed_at=created_at,
        cancelled_at=None,
    )

    result = AssessmentModerationReviewSummary.model_validate(
        source,
    )

    assert result.review_number == 2
    assert result.outcome == AssessmentModerationOutcome.CONFIRMED
    assert not hasattr(
        result,
        "items",
    )


def test_review_list_accepts_summary_items() -> None:
    created_at = _now()

    summary = AssessmentModerationReviewSummary(
        id=1,
        school_id=10,
        assessment_id=20,
        candidate_id=30,
        script_id=40,
        review_number=1,
        status=AssessmentModerationReviewStatus.PENDING,
        outcome=None,
        sampling_method=AssessmentModerationSamplingMethod.MANUAL,
        moderator_id=50,
        initiated_by_id=60,
        reason=None,
        created_at=created_at,
        started_at=None,
        completed_at=None,
        cancelled_at=None,
    )

    result = AssessmentModerationReviewList(
        items=[
            summary,
        ],
        total=1,
    )

    assert result.total == 1
    assert len(result.items) == 1


def test_review_list_rejects_negative_total() -> None:
    with pytest.raises(
        ValidationError,
    ):
        AssessmentModerationReviewList(
            items=[],
            total=-1,
        )
