from __future__ import annotations

from decimal import Decimal
from typing import Any

import pytest

import app.models  # noqa: F401
from app.models.assessment_moderation import (
    AssessmentModerationItem,
    AssessmentModerationItemOutcome,
    AssessmentModerationOutcome,
    AssessmentModerationReview,
    AssessmentModerationReviewStatus,
    AssessmentModerationSamplingMethod,
)
from app.repositories.assessment_moderation import (
    AssessmentModerationRepository,
)


class _FakeScalarResult:
    def __init__(
        self,
        *,
        one: Any = None,
        many: list[Any] | None = None,
    ) -> None:
        self._one = one
        self._many = list(
            many or [],
        )

    def unique(self) -> _FakeScalarResult:
        return self

    def one_or_none(self) -> Any:
        return self._one

    def all(self) -> list[Any]:
        return list(
            self._many,
        )


class _FakeResult:
    def __init__(
        self,
        *,
        scalar: Any = None,
        one: Any = None,
        many: list[Any] | None = None,
    ) -> None:
        self._scalar = scalar
        self._one = one
        self._many = list(
            many or [],
        )

    def scalars(self) -> _FakeScalarResult:
        return _FakeScalarResult(
            one=self._one,
            many=self._many,
        )

    def scalar_one_or_none(self) -> Any:
        return self._scalar


class _FakeAsyncSession:
    def __init__(
        self,
        results: list[_FakeResult] | None = None,
    ) -> None:
        self.results = list(
            results or [],
        )

        self.executed_statements: list[Any] = []
        self.added: list[Any] = []
        self.flushed = 0
        self.refreshed: list[Any] = []
        self.commits = 0

    async def execute(
        self,
        statement: Any,
    ) -> _FakeResult:
        self.executed_statements.append(
            statement,
        )

        if not self.results:
            raise AssertionError(
                "No fake result was queued for this execute call.",
            )

        return self.results.pop(
            0,
        )

    def add(
        self,
        value: Any,
    ) -> None:
        self.added.append(
            value,
        )

    async def flush(self) -> None:
        self.flushed += 1

    async def refresh(
        self,
        value: Any,
    ) -> None:
        self.refreshed.append(
            value,
        )

    async def commit(self) -> None:
        self.commits += 1


def _review(
    *,
    review_id: int = 1,
    school_id: int = 10,
    assessment_id: int = 20,
    candidate_id: int = 30,
    script_id: int = 40,
    review_number: int = 1,
    moderator_id: int = 50,
    initiated_by_id: int = 60,
    status: AssessmentModerationReviewStatus = (
        AssessmentModerationReviewStatus.PENDING
    ),
    outcome: AssessmentModerationOutcome | None = None,
) -> AssessmentModerationReview:
    return AssessmentModerationReview(
        id=review_id,
        school_id=school_id,
        assessment_id=assessment_id,
        candidate_id=candidate_id,
        script_id=script_id,
        review_number=review_number,
        status=status,
        outcome=outcome,
        sampling_method=AssessmentModerationSamplingMethod.MANUAL,
        moderator_id=moderator_id,
        initiated_by_id=initiated_by_id,
    )


def _item(
    *,
    item_id: int = 1,
    review_id: int = 1,
    response_id: int = 2,
    marking_decision_id: int = 3,
    reviewed_by_id: int = 4,
    outcome: AssessmentModerationItemOutcome = (
        AssessmentModerationItemOutcome.CONFIRMED
    ),
) -> AssessmentModerationItem:
    return AssessmentModerationItem(
        id=item_id,
        review_id=review_id,
        response_id=response_id,
        marking_decision_id=marking_decision_id,
        outcome=outcome,
        mark_before_snapshot=Decimal("5.00"),
        mark_after_snapshot=Decimal("5.00"),
        maximum_mark_snapshot=Decimal("6.00"),
        mark_changed=False,
        decision_status_before_snapshot="marked",
        decision_status_after_snapshot="reviewed",
        reviewed_by_id=reviewed_by_id,
    )


def _sql(
    statement: Any,
) -> str:
    return " ".join(
        str(
            statement,
        )
        .lower()
        .split(),
    )


@pytest.mark.asyncio
async def test_get_review_by_id_returns_review() -> None:
    review = _review()

    db = _FakeAsyncSession(
        [
            _FakeResult(
                one=review,
            ),
        ],
    )

    repository = AssessmentModerationRepository(
        db,  # type: ignore[arg-type]
    )

    result = await repository.get_review_by_id(
        1,
    )

    assert result is review
    assert len(db.executed_statements) == 1

    sql = _sql(
        db.executed_statements[0],
    )

    assert "assessment_moderation_reviews.id" in sql


@pytest.mark.asyncio
async def test_get_review_by_id_returns_none() -> None:
    db = _FakeAsyncSession(
        [
            _FakeResult(
                one=None,
            ),
        ],
    )

    repository = AssessmentModerationRepository(
        db,  # type: ignore[arg-type]
    )

    result = await repository.get_review_by_id(
        999,
    )

    assert result is None


@pytest.mark.asyncio
async def test_get_review_by_id_for_school_applies_school_scope() -> None:
    review = _review(
        school_id=10,
    )

    db = _FakeAsyncSession(
        [
            _FakeResult(
                one=review,
            ),
        ],
    )

    repository = AssessmentModerationRepository(
        db,  # type: ignore[arg-type]
    )

    result = await repository.get_review_by_id_for_school(
        1,
        10,
    )

    assert result is review

    sql = _sql(
        db.executed_statements[0],
    )

    assert "assessment_moderation_reviews.id" in sql
    assert "assessment_moderation_reviews.school_id" in sql


@pytest.mark.asyncio
async def test_list_reviews_for_script_returns_review_number_order() -> None:
    first = _review(
        review_id=1,
        review_number=1,
    )
    second = _review(
        review_id=2,
        review_number=2,
    )

    db = _FakeAsyncSession(
        [
            _FakeResult(
                many=[
                    first,
                    second,
                ],
            ),
        ],
    )

    repository = AssessmentModerationRepository(
        db,  # type: ignore[arg-type]
    )

    result = await repository.list_reviews_for_script(
        40,
    )

    assert result == [
        first,
        second,
    ]

    sql = _sql(
        db.executed_statements[0],
    )

    assert "assessment_moderation_reviews.script_id" in sql
    assert "order by" in sql
    assert "assessment_moderation_reviews.review_number asc" in sql


@pytest.mark.asyncio
async def test_list_reviews_for_candidate_applies_candidate_filter() -> None:
    review = _review()

    db = _FakeAsyncSession(
        [
            _FakeResult(
                many=[
                    review,
                ],
            ),
        ],
    )

    repository = AssessmentModerationRepository(
        db,  # type: ignore[arg-type]
    )

    result = await repository.list_reviews_for_candidate(
        30,
    )

    assert result == [
        review,
    ]

    sql = _sql(
        db.executed_statements[0],
    )

    assert "assessment_moderation_reviews.candidate_id" in sql


@pytest.mark.asyncio
async def test_list_reviews_for_assessment_supports_filters() -> None:
    review = _review(
        status=AssessmentModerationReviewStatus.COMPLETED,
        outcome=AssessmentModerationOutcome.CONFIRMED,
    )

    db = _FakeAsyncSession(
        [
            _FakeResult(
                many=[
                    review,
                ],
            ),
        ],
    )

    repository = AssessmentModerationRepository(
        db,  # type: ignore[arg-type]
    )

    result = await repository.list_reviews_for_assessment(
        20,
        school_id=10,
        status=AssessmentModerationReviewStatus.COMPLETED,
        outcome=AssessmentModerationOutcome.CONFIRMED,
    )

    assert result == [
        review,
    ]

    sql = _sql(
        db.executed_statements[0],
    )

    assert "assessment_moderation_reviews.assessment_id" in sql
    assert "assessment_moderation_reviews.school_id" in sql
    assert "assessment_moderation_reviews.status" in sql
    assert "assessment_moderation_reviews.outcome" in sql


@pytest.mark.asyncio
async def test_list_reviews_for_moderator_supports_school_and_status() -> None:
    review = _review(
        status=AssessmentModerationReviewStatus.IN_PROGRESS,
    )

    db = _FakeAsyncSession(
        [
            _FakeResult(
                many=[
                    review,
                ],
            ),
        ],
    )

    repository = AssessmentModerationRepository(
        db,  # type: ignore[arg-type]
    )

    result = await repository.list_reviews_for_moderator(
        50,
        school_id=10,
        status=AssessmentModerationReviewStatus.IN_PROGRESS,
    )

    assert result == [
        review,
    ]

    sql = _sql(
        db.executed_statements[0],
    )

    assert "assessment_moderation_reviews.moderator_id" in sql
    assert "assessment_moderation_reviews.school_id" in sql
    assert "assessment_moderation_reviews.status" in sql


@pytest.mark.asyncio
async def test_next_review_number_is_one_when_no_existing_review() -> None:
    db = _FakeAsyncSession(
        [
            _FakeResult(
                scalar=40,
            ),
            _FakeResult(
                scalar=None,
            ),
        ],
    )

    repository = AssessmentModerationRepository(
        db,  # type: ignore[arg-type]
    )

    result = await repository.get_next_review_number(
        40,
    )

    assert result == 1
    assert len(db.executed_statements) == 2

    script_sql = _sql(
        db.executed_statements[0],
    )
    max_sql = _sql(
        db.executed_statements[1],
    )

    assert "assessment_scripts.id" in script_sql
    assert "for update" in script_sql
    assert "max(assessment_moderation_reviews.review_number)" in max_sql


@pytest.mark.asyncio
async def test_next_review_number_increments_current_maximum() -> None:
    db = _FakeAsyncSession(
        [
            _FakeResult(
                scalar=40,
            ),
            _FakeResult(
                scalar=3,
            ),
        ],
    )

    repository = AssessmentModerationRepository(
        db,  # type: ignore[arg-type]
    )

    result = await repository.get_next_review_number(
        40,
    )

    assert result == 4


@pytest.mark.asyncio
async def test_next_review_number_rejects_missing_script() -> None:
    db = _FakeAsyncSession(
        [
            _FakeResult(
                scalar=None,
            ),
        ],
    )

    repository = AssessmentModerationRepository(
        db,  # type: ignore[arg-type]
    )

    with pytest.raises(
        ValueError,
        match="Assessment script does not exist",
    ):
        await repository.get_next_review_number(
            999,
        )


@pytest.mark.asyncio
async def test_create_review_allocates_review_number() -> None:
    db = _FakeAsyncSession(
        [
            _FakeResult(
                scalar=40,
            ),
            _FakeResult(
                scalar=2,
            ),
        ],
    )

    repository = AssessmentModerationRepository(
        db,  # type: ignore[arg-type]
    )

    review = await repository.create_review(
        school_id=10,
        assessment_id=20,
        candidate_id=30,
        script_id=40,
        moderator_id=50,
        initiated_by_id=60,
        sampling_method=AssessmentModerationSamplingMethod.TARGETED,
        reason="Grade-boundary quality assurance",
    )

    assert review.review_number == 3
    assert review.school_id == 10
    assert review.assessment_id == 20
    assert review.candidate_id == 30
    assert review.script_id == 40
    assert review.moderator_id == 50
    assert review.initiated_by_id == 60
    assert review.sampling_method == AssessmentModerationSamplingMethod.TARGETED
    assert review.reason == "Grade-boundary quality assurance"

    assert db.added == [
        review,
    ]
    assert db.flushed == 1
    assert db.refreshed == [
        review,
    ]
    assert db.commits == 0


@pytest.mark.asyncio
async def test_create_review_accepts_explicit_review_number() -> None:
    db = _FakeAsyncSession()

    repository = AssessmentModerationRepository(
        db,  # type: ignore[arg-type]
    )

    review = await repository.create_review(
        school_id=10,
        assessment_id=20,
        candidate_id=30,
        script_id=40,
        moderator_id=50,
        initiated_by_id=60,
        review_number=7,
    )

    assert review.review_number == 7
    assert db.executed_statements == []
    assert db.flushed == 1
    assert db.commits == 0


@pytest.mark.asyncio
async def test_save_review_flushes_without_commit() -> None:
    review = _review()

    db = _FakeAsyncSession()

    repository = AssessmentModerationRepository(
        db,  # type: ignore[arg-type]
    )

    result = await repository.save_review(
        review,
    )

    assert result is review
    assert db.added == [
        review,
    ]
    assert db.flushed == 1
    assert db.refreshed == [
        review,
    ]
    assert db.commits == 0


@pytest.mark.asyncio
async def test_get_item_by_id_returns_item() -> None:
    item = _item()

    db = _FakeAsyncSession(
        [
            _FakeResult(
                one=item,
            ),
        ],
    )

    repository = AssessmentModerationRepository(
        db,  # type: ignore[arg-type]
    )

    result = await repository.get_item_by_id(
        1,
    )

    assert result is item

    sql = _sql(
        db.executed_statements[0],
    )

    assert "assessment_moderation_items.id" in sql


@pytest.mark.asyncio
async def test_get_item_by_id_for_school_joins_parent_review() -> None:
    item = _item()

    db = _FakeAsyncSession(
        [
            _FakeResult(
                one=item,
            ),
        ],
    )

    repository = AssessmentModerationRepository(
        db,  # type: ignore[arg-type]
    )

    result = await repository.get_item_by_id_for_school(
        1,
        10,
    )

    assert result is item

    sql = _sql(
        db.executed_statements[0],
    )

    assert "join assessment_moderation_reviews" in sql
    assert "assessment_moderation_items.id" in sql
    assert "assessment_moderation_reviews.school_id" in sql


@pytest.mark.asyncio
async def test_get_item_for_response_scopes_to_review_and_response() -> None:
    item = _item()

    db = _FakeAsyncSession(
        [
            _FakeResult(
                one=item,
            ),
        ],
    )

    repository = AssessmentModerationRepository(
        db,  # type: ignore[arg-type]
    )

    result = await repository.get_item_for_response(
        1,
        2,
    )

    assert result is item

    sql = _sql(
        db.executed_statements[0],
    )

    assert "assessment_moderation_items.review_id" in sql
    assert "assessment_moderation_items.response_id" in sql


@pytest.mark.asyncio
async def test_list_items_for_review_returns_items() -> None:
    first = _item(
        item_id=1,
        response_id=2,
    )
    second = _item(
        item_id=2,
        response_id=3,
    )

    db = _FakeAsyncSession(
        [
            _FakeResult(
                many=[
                    first,
                    second,
                ],
            ),
        ],
    )

    repository = AssessmentModerationRepository(
        db,  # type: ignore[arg-type]
    )

    result = await repository.list_items_for_review(
        1,
    )

    assert result == [
        first,
        second,
    ]

    sql = _sql(
        db.executed_statements[0],
    )

    assert "assessment_moderation_items.review_id" in sql
    assert "order by assessment_moderation_items.id asc" in sql


@pytest.mark.asyncio
async def test_create_item_rejects_duplicate_response() -> None:
    existing = _item()

    db = _FakeAsyncSession(
        [
            _FakeResult(
                one=existing,
            ),
        ],
    )

    repository = AssessmentModerationRepository(
        db,  # type: ignore[arg-type]
    )

    with pytest.raises(
        ValueError,
        match="already been recorded",
    ):
        await repository.create_item(
            review_id=1,
            response_id=2,
            marking_decision_id=3,
            outcome=AssessmentModerationItemOutcome.CONFIRMED,
            reviewed_by_id=4,
        )

    assert db.added == []
    assert db.flushed == 0
    assert db.commits == 0


@pytest.mark.asyncio
async def test_create_item_persists_snapshot_without_commit() -> None:
    db = _FakeAsyncSession(
        [
            _FakeResult(
                one=None,
            ),
        ],
    )

    repository = AssessmentModerationRepository(
        db,  # type: ignore[arg-type]
    )

    item = await repository.create_item(
        review_id=1,
        response_id=2,
        marking_decision_id=3,
        outcome=AssessmentModerationItemOutcome.ADJUSTED,
        reviewed_by_id=4,
        mark_before_snapshot=Decimal("4.00"),
        mark_after_snapshot=Decimal("5.00"),
        maximum_mark_snapshot=Decimal("6.00"),
        mark_changed=True,
        decision_status_before_snapshot="marked",
        decision_status_after_snapshot="reviewed",
        moderator_comment="One additional method mark awarded.",
        evidence_notes="Checked against mark scheme item 2.",
    )

    assert item.review_id == 1
    assert item.response_id == 2
    assert item.marking_decision_id == 3
    assert item.outcome == AssessmentModerationItemOutcome.ADJUSTED
    assert item.mark_before_snapshot == Decimal("4.00")
    assert item.mark_after_snapshot == Decimal("5.00")
    assert item.maximum_mark_snapshot == Decimal("6.00")
    assert item.mark_changed is True
    assert item.decision_status_before_snapshot == "marked"
    assert item.decision_status_after_snapshot == "reviewed"
    assert item.reviewed_by_id == 4

    assert db.added == [
        item,
    ]
    assert db.flushed == 1
    assert db.refreshed == [
        item,
    ]
    assert db.commits == 0


@pytest.mark.asyncio
async def test_save_item_flushes_without_commit() -> None:
    item = _item()

    db = _FakeAsyncSession()

    repository = AssessmentModerationRepository(
        db,  # type: ignore[arg-type]
    )

    result = await repository.save_item(
        item,
    )

    assert result is item
    assert db.added == [
        item,
    ]
    assert db.flushed == 1
    assert db.refreshed == [
        item,
    ]
    assert db.commits == 0


def test_review_query_can_request_relationships_and_items() -> None:
    statement = AssessmentModerationRepository._review_query(
        include_relationships=True,
        include_items=True,
    )

    assert statement is not None
    assert len(statement._with_options) >= 7


def test_item_query_can_request_relationships() -> None:
    statement = AssessmentModerationRepository._item_query(
        include_relationships=True,
    )

    assert statement is not None
    assert len(statement._with_options) == 4


def test_repository_exposes_no_delete_review_method() -> None:
    assert not hasattr(
        AssessmentModerationRepository,
        "delete_review",
    )


def test_repository_exposes_no_delete_item_method() -> None:
    assert not hasattr(
        AssessmentModerationRepository,
        "delete_item",
    )
