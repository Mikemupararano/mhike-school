from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace
from typing import Any

import pytest
from fastapi import HTTPException

from app.models.assessment_candidate import (
    AssessmentScript,
    AssessmentScriptStatus,
)
from app.models.assessment_moderation import (
    AssessmentModerationItem,
    AssessmentModerationItemOutcome,
    AssessmentModerationOutcome,
    AssessmentModerationReview,
    AssessmentModerationReviewStatus,
    AssessmentModerationSamplingMethod,
)
from app.models.assessment_response import MarkingDecisionStatus
from app.models.user import UserRole
import app.services.assessment_moderation_service as service

# ----------------------------------------------------------------------
# Test doubles
# ----------------------------------------------------------------------


class _FakeDB:
    def __init__(self) -> None:
        self.commits = 0
        self.rollbacks = 0
        self.flushes = 0
        self.added: list[Any] = []

    def add(
        self,
        value: Any,
    ) -> None:
        self.added.append(
            value,
        )

    async def flush(self) -> None:
        self.flushes += 1

    async def commit(self) -> None:
        self.commits += 1

    async def rollback(self) -> None:
        self.rollbacks += 1


class _FakeModerationRepository:
    def __init__(self) -> None:
        self.reviews: dict[int, AssessmentModerationReview] = {}
        self.items: dict[int, AssessmentModerationItem] = {}

        self.next_review_id = 1
        self.next_item_id = 1

        self.create_review_calls: list[dict[str, Any]] = []
        self.create_item_calls: list[dict[str, Any]] = []
        self.saved_reviews: list[AssessmentModerationReview] = []

        self.script_reviews: list[AssessmentModerationReview] = []

    async def create_review(
        self,
        **kwargs: Any,
    ) -> AssessmentModerationReview:
        self.create_review_calls.append(
            dict(
                kwargs,
            ),
        )

        review = AssessmentModerationReview(
            id=self.next_review_id,
            review_number=1,
            status=AssessmentModerationReviewStatus.PENDING,
            outcome=None,
            **kwargs,
        )

        self.next_review_id += 1

        review.items = []

        self.reviews[review.id] = review
        self.script_reviews.append(
            review,
        )

        return review

    async def get_review_by_id(
        self,
        review_id: int,
        *,
        include_relationships: bool = False,
        include_items: bool = False,
    ) -> AssessmentModerationReview | None:
        del include_relationships
        del include_items

        return self.reviews.get(
            review_id,
        )

    async def save_review(
        self,
        review: AssessmentModerationReview,
    ) -> AssessmentModerationReview:
        self.saved_reviews.append(
            review,
        )

        self.reviews[review.id] = review

        return review

    async def create_item(
        self,
        **kwargs: Any,
    ) -> AssessmentModerationItem:
        self.create_item_calls.append(
            dict(
                kwargs,
            ),
        )

        review = self.reviews.get(
            kwargs["review_id"],
        )

        if review is not None:
            for existing in review.items:
                if existing.response_id == kwargs["response_id"]:
                    raise ValueError(
                        "This response has already been recorded "
                        "in the moderation review.",
                    )

        item = AssessmentModerationItem(
            id=self.next_item_id,
            **kwargs,
        )

        self.next_item_id += 1

        self.items[item.id] = item

        if review is not None:
            review.items.append(
                item,
            )

        return item

    async def list_reviews_for_script(
        self,
        script_id: int,
        *,
        include_relationships: bool = False,
        include_items: bool = False,
    ) -> list[AssessmentModerationReview]:
        del include_relationships
        del include_items

        return [
            review for review in self.script_reviews if review.script_id == script_id
        ]

    async def list_reviews_for_assessment(
        self,
        assessment_id: int,
        *,
        school_id: int | None = None,
        status: AssessmentModerationReviewStatus | None = None,
        outcome: AssessmentModerationOutcome | None = None,
        include_relationships: bool = False,
        include_items: bool = False,
    ) -> list[AssessmentModerationReview]:
        del include_relationships
        del include_items

        reviews = [
            review
            for review in self.script_reviews
            if review.assessment_id == assessment_id
        ]

        if school_id is not None:
            reviews = [review for review in reviews if review.school_id == school_id]

        if status is not None:
            reviews = [review for review in reviews if review.status == status]

        if outcome is not None:
            reviews = [review for review in reviews if review.outcome == outcome]

        return reviews


# ----------------------------------------------------------------------
# Factories
# ----------------------------------------------------------------------


def _user(
    *,
    user_id: int = 100,
    school_id: int | None = 10,
    roles: list[UserRole] | None = None,
):
    selected_roles = roles or [
        UserRole.SCHOOL_ADMIN,
    ]

    return SimpleNamespace(
        id=user_id,
        school_id=school_id,
        roles=[role.value for role in selected_roles],
    )


def _script(
    *,
    script_id: int = 40,
    candidate_id: int = 30,
    script_status: AssessmentScriptStatus = AssessmentScriptStatus.MARKED,
) -> AssessmentScript:
    return AssessmentScript(
        id=script_id,
        candidate_id=candidate_id,
        version=1,
        status=script_status,
    )


def _review(
    *,
    review_id: int = 1,
    school_id: int = 10,
    assessment_id: int = 20,
    candidate_id: int = 30,
    script_id: int = 40,
    moderator_id: int = 100,
    review_status: AssessmentModerationReviewStatus = (
        AssessmentModerationReviewStatus.PENDING
    ),
    outcome: AssessmentModerationOutcome | None = None,
) -> AssessmentModerationReview:
    review = AssessmentModerationReview(
        id=review_id,
        school_id=school_id,
        assessment_id=assessment_id,
        candidate_id=candidate_id,
        script_id=script_id,
        review_number=1,
        status=review_status,
        outcome=outcome,
        sampling_method=AssessmentModerationSamplingMethod.MANUAL,
        moderator_id=moderator_id,
        initiated_by_id=100,
    )

    review.items = []

    return review


def _moderation_item(
    *,
    item_id: int = 1,
    review_id: int = 1,
    response_id: int = 200,
    decision_id: int = 300,
    outcome: AssessmentModerationItemOutcome = (
        AssessmentModerationItemOutcome.CONFIRMED
    ),
    mark_before: Decimal = Decimal("5.00"),
    mark_after: Decimal = Decimal("5.00"),
    maximum_mark: Decimal = Decimal("10.00"),
    mark_changed: bool = False,
) -> AssessmentModerationItem:
    return AssessmentModerationItem(
        id=item_id,
        review_id=review_id,
        response_id=response_id,
        marking_decision_id=decision_id,
        outcome=outcome,
        mark_before_snapshot=mark_before,
        mark_after_snapshot=mark_after,
        maximum_mark_snapshot=maximum_mark,
        mark_changed=mark_changed,
        decision_status_before_snapshot="marked",
        decision_status_after_snapshot="reviewed",
        reviewed_by_id=100,
    )


def _install_repository(
    monkeypatch,
    repository: _FakeModerationRepository,
) -> None:
    monkeypatch.setattr(
        service,
        "AssessmentModerationRepository",
        lambda db: repository,
    )


# ----------------------------------------------------------------------
# Role helpers
# ----------------------------------------------------------------------


def test_school_admin_has_moderation_authority() -> None:
    user = _user(
        roles=[
            UserRole.SCHOOL_ADMIN,
        ],
    )

    service._ensure_moderation_admin_role(
        user,
    )


def test_platform_admin_has_moderation_authority() -> None:
    user = _user(
        school_id=None,
        roles=[
            UserRole.PLATFORM_ADMIN,
        ],
    )

    service._ensure_moderation_admin_role(
        user,
    )


def test_teacher_cannot_moderate() -> None:
    user = _user(
        roles=[
            UserRole.TEACHER,
        ],
    )

    with pytest.raises(
        HTTPException,
    ) as exc:
        service._ensure_moderation_admin_role(
            user,
        )

    assert exc.value.status_code == 403


# ----------------------------------------------------------------------
# Normalisation
# ----------------------------------------------------------------------


def test_sampling_method_normalises_string() -> None:
    result = service._normalise_sampling_method(
        "targeted",
    )

    assert result == AssessmentModerationSamplingMethod.TARGETED


def test_invalid_sampling_method_rejected() -> None:
    with pytest.raises(
        HTTPException,
    ) as exc:
        service._normalise_sampling_method(
            "something_invalid",
        )

    assert exc.value.status_code == 400


def test_non_finite_mark_rejected() -> None:
    with pytest.raises(
        HTTPException,
    ) as exc:
        service._normalise_decimal(
            "NaN",
            field_name="mark_after",
        )

    assert exc.value.status_code == 422


# ----------------------------------------------------------------------
# Review creation
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_review_moves_marked_script_to_moderation(
    monkeypatch,
) -> None:
    db = _FakeDB()
    repository = _FakeModerationRepository()

    _install_repository(
        monkeypatch,
        repository,
    )

    script = _script(
        script_status=AssessmentScriptStatus.MARKED,
    )

    candidate = SimpleNamespace(
        id=30,
        assessment_id=20,
    )

    assessment = SimpleNamespace(
        id=20,
        school_id=10,
        course_id=5,
    )

    async def fake_get_script(
        db,
        script_id,
    ):
        del db
        del script_id

        return script

    async def fake_ensure_access(
        db,
        current_user,
        supplied_script,
    ):
        del db
        del current_user

        assert supplied_script is script

        return candidate, assessment

    async def fake_moderator_validation(
        db,
        moderator_id,
        *,
        school_id,
    ):
        del db

        assert moderator_id == 100
        assert school_id == 10

        return _user()

    async def fake_get_review(
        db,
        review_id,
        *,
        include_items=False,
    ):
        del db
        del include_items

        return repository.reviews[review_id]

    monkeypatch.setattr(
        service,
        "_get_script_or_404",
        fake_get_script,
    )
    monkeypatch.setattr(
        service,
        "_ensure_script_moderation_access",
        fake_ensure_access,
    )
    monkeypatch.setattr(
        service,
        "_ensure_moderator_assignment_valid",
        fake_moderator_validation,
    )
    monkeypatch.setattr(
        service,
        "_get_review_or_404",
        fake_get_review,
    )

    result = await service.create_moderation_review(
        db,
        _user(),
        40,
        moderator_id=100,
        sampling_method="targeted",
        reason="Grade boundary sample",
    )

    assert result.script_id == 40
    assert result.moderator_id == 100
    assert result.sampling_method == AssessmentModerationSamplingMethod.TARGETED
    assert result.reason == "Grade boundary sample"

    assert script.status == AssessmentScriptStatus.MODERATION

    assert db.commits == 1
    assert db.rollbacks == 0


@pytest.mark.asyncio
async def test_create_review_does_not_reopen_finalised_script(
    monkeypatch,
) -> None:
    db = _FakeDB()
    repository = _FakeModerationRepository()

    _install_repository(
        monkeypatch,
        repository,
    )

    script = _script(
        script_status=AssessmentScriptStatus.FINALISED,
    )

    candidate = SimpleNamespace(
        id=30,
        assessment_id=20,
    )

    assessment = SimpleNamespace(
        id=20,
        school_id=10,
    )

    async def fake_get_script(
        db,
        script_id,
    ):
        del db
        del script_id

        return script

    async def fake_access(
        db,
        current_user,
        supplied_script,
    ):
        del db
        del current_user
        del supplied_script

        return candidate, assessment

    async def fake_moderator_validation(
        db,
        moderator_id,
        *,
        school_id,
    ):
        del db
        del moderator_id
        del school_id

        return _user()

    async def fake_get_review(
        db,
        review_id,
        *,
        include_items=False,
    ):
        del db
        del include_items

        return repository.reviews[review_id]

    monkeypatch.setattr(
        service,
        "_get_script_or_404",
        fake_get_script,
    )
    monkeypatch.setattr(
        service,
        "_ensure_script_moderation_access",
        fake_access,
    )
    monkeypatch.setattr(
        service,
        "_ensure_moderator_assignment_valid",
        fake_moderator_validation,
    )
    monkeypatch.setattr(
        service,
        "_get_review_or_404",
        fake_get_review,
    )

    await service.create_moderation_review(
        db,
        _user(),
        40,
        moderator_id=100,
    )

    assert script.status == AssessmentScriptStatus.FINALISED


@pytest.mark.asyncio
async def test_unmarked_script_cannot_enter_moderation(
    monkeypatch,
) -> None:
    db = _FakeDB()

    script = _script(
        script_status=AssessmentScriptStatus.MARKING,
    )

    async def fake_get_script(
        db,
        script_id,
    ):
        del db
        del script_id

        return script

    async def fake_access(
        db,
        current_user,
        supplied_script,
    ):
        del db
        del current_user
        del supplied_script

        return (
            SimpleNamespace(
                id=30,
                assessment_id=20,
            ),
            SimpleNamespace(
                id=20,
                school_id=10,
            ),
        )

    monkeypatch.setattr(
        service,
        "_get_script_or_404",
        fake_get_script,
    )
    monkeypatch.setattr(
        service,
        "_ensure_script_moderation_access",
        fake_access,
    )

    with pytest.raises(
        HTTPException,
    ) as exc:
        await service.create_moderation_review(
            db,
            _user(),
            40,
            moderator_id=100,
        )

    assert exc.value.status_code == 409


# ----------------------------------------------------------------------
# Starting reviews
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_assigned_moderator_can_start_review(
    monkeypatch,
) -> None:
    db = _FakeDB()
    repository = _FakeModerationRepository()

    review = _review()

    repository.reviews[review.id] = review

    _install_repository(
        monkeypatch,
        repository,
    )

    async def fake_review_lookup(
        db,
        review_id,
        *,
        include_items=False,
    ):
        del db
        del include_items

        return repository.reviews[review_id]

    async def fake_access(
        db,
        current_user,
        supplied_review,
    ):
        del db
        del current_user
        del supplied_review

        return _script(
            script_status=AssessmentScriptStatus.MODERATION,
        )

    monkeypatch.setattr(
        service,
        "_get_review_or_404",
        fake_review_lookup,
    )
    monkeypatch.setattr(
        service,
        "_ensure_review_access",
        fake_access,
    )

    result = await service.start_moderation_review(
        db,
        _user(
            user_id=100,
        ),
        review.id,
    )

    assert result.status == AssessmentModerationReviewStatus.IN_PROGRESS
    assert result.started_at is not None
    assert db.commits == 1


@pytest.mark.asyncio
async def test_other_school_admin_cannot_work_assigned_review(
    monkeypatch,
) -> None:
    db = _FakeDB()

    review = _review(
        moderator_id=100,
    )

    async def fake_review_lookup(
        db,
        review_id,
        *,
        include_items=False,
    ):
        del db
        del review_id
        del include_items

        return review

    async def fake_access(
        db,
        current_user,
        supplied_review,
    ):
        del db
        del current_user
        del supplied_review

        return _script(
            script_status=AssessmentScriptStatus.MODERATION,
        )

    monkeypatch.setattr(
        service,
        "_get_review_or_404",
        fake_review_lookup,
    )
    monkeypatch.setattr(
        service,
        "_ensure_review_access",
        fake_access,
    )

    with pytest.raises(
        HTTPException,
    ) as exc:
        await service.start_moderation_review(
            db,
            _user(
                user_id=999,
            ),
            review.id,
        )

    assert exc.value.status_code == 403


# ----------------------------------------------------------------------
# Moderation item recording
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_confirmed_item_records_snapshot_and_reviews_marked_decision(
    monkeypatch,
) -> None:
    db = _FakeDB()
    repository = _FakeModerationRepository()

    review = _review(
        review_status=AssessmentModerationReviewStatus.IN_PROGRESS,
    )

    repository.reviews[review.id] = review

    _install_repository(
        monkeypatch,
        repository,
    )

    response = SimpleNamespace(
        id=200,
        script_id=40,
        question_id=500,
    )

    decision = SimpleNamespace(
        id=300,
        response_id=200,
        status=MarkingDecisionStatus.MARKED,
        mark_awarded=Decimal("6.00"),
        reviewed_at=None,
        moderation_comment=None,
    )

    question = SimpleNamespace(
        id=500,
        assessment_id=20,
        maximum_mark=Decimal("10.00"),
    )

    async def fake_review_lookup(
        db,
        review_id,
        *,
        include_items=False,
    ):
        del db
        del review_id
        del include_items

        return review

    async def fake_review_access(
        db,
        current_user,
        supplied_review,
    ):
        del db
        del current_user
        del supplied_review

        return _script(
            script_status=AssessmentScriptStatus.MODERATION,
        )

    async def fake_response(
        db,
        response_id,
    ):
        del db
        del response_id

        return response

    async def fake_decision(
        db,
        decision_id,
    ):
        del db
        del decision_id

        return decision

    async def fake_question(
        db,
        question_id,
    ):
        del db
        del question_id

        return question

    monkeypatch.setattr(
        service,
        "_get_review_or_404",
        fake_review_lookup,
    )
    monkeypatch.setattr(
        service,
        "_ensure_review_access",
        fake_review_access,
    )
    monkeypatch.setattr(
        service,
        "_get_response_or_404",
        fake_response,
    )
    monkeypatch.setattr(
        service,
        "_get_decision_or_404",
        fake_decision,
    )
    monkeypatch.setattr(
        service,
        "_get_question_or_404",
        fake_question,
    )

    result = await service.add_moderation_item(
        db,
        _user(),
        review.id,
        response_id=200,
        marking_decision_id=300,
        outcome=AssessmentModerationItemOutcome.CONFIRMED,
        moderator_comment="Mark confirmed.",
    )

    assert result.outcome == AssessmentModerationItemOutcome.CONFIRMED
    assert result.mark_before_snapshot == Decimal("6.00")
    assert result.mark_after_snapshot == Decimal("6.00")
    assert result.mark_changed is False

    assert decision.mark_awarded == Decimal("6.00")
    assert decision.status == MarkingDecisionStatus.REVIEWED
    assert decision.reviewed_at is not None
    assert decision.moderation_comment == "Mark confirmed."

    assert db.commits == 1


@pytest.mark.asyncio
async def test_adjusted_item_changes_current_operational_mark(
    monkeypatch,
) -> None:
    db = _FakeDB()
    repository = _FakeModerationRepository()

    review = _review(
        review_status=AssessmentModerationReviewStatus.IN_PROGRESS,
    )

    repository.reviews[review.id] = review

    _install_repository(
        monkeypatch,
        repository,
    )

    response = SimpleNamespace(
        id=200,
        script_id=40,
        question_id=500,
    )

    decision = SimpleNamespace(
        id=300,
        response_id=200,
        status=MarkingDecisionStatus.MARKED,
        mark_awarded=Decimal("5.00"),
        reviewed_at=None,
        moderation_comment=None,
    )

    question = SimpleNamespace(
        id=500,
        assessment_id=20,
        maximum_mark=Decimal("10.00"),
    )

    async def fake_review_lookup(
        db,
        review_id,
        *,
        include_items=False,
    ):
        del db
        del review_id
        del include_items

        return review

    async def fake_access(
        db,
        current_user,
        supplied_review,
    ):
        del db
        del current_user
        del supplied_review

        return _script(
            script_status=AssessmentScriptStatus.MODERATION,
        )

    async def fake_response(
        db,
        response_id,
    ):
        del db
        del response_id

        return response

    async def fake_decision(
        db,
        decision_id,
    ):
        del db
        del decision_id

        return decision

    async def fake_question(
        db,
        question_id,
    ):
        del db
        del question_id

        return question

    monkeypatch.setattr(
        service,
        "_get_review_or_404",
        fake_review_lookup,
    )
    monkeypatch.setattr(
        service,
        "_ensure_review_access",
        fake_access,
    )
    monkeypatch.setattr(
        service,
        "_get_response_or_404",
        fake_response,
    )
    monkeypatch.setattr(
        service,
        "_get_decision_or_404",
        fake_decision,
    )
    monkeypatch.setattr(
        service,
        "_get_question_or_404",
        fake_question,
    )

    result = await service.add_moderation_item(
        db,
        _user(),
        review.id,
        response_id=200,
        marking_decision_id=300,
        outcome=AssessmentModerationItemOutcome.ADJUSTED,
        mark_after=Decimal("6.00"),
    )

    assert result.mark_before_snapshot == Decimal("5.00")
    assert result.mark_after_snapshot == Decimal("6.00")
    assert result.mark_changed is True

    assert decision.mark_awarded == Decimal("6.00")
    assert decision.status == MarkingDecisionStatus.REVIEWED


@pytest.mark.asyncio
async def test_adjusted_outcome_requires_mark_change(
    monkeypatch,
) -> None:
    db = _FakeDB()
    repository = _FakeModerationRepository()

    review = _review(
        review_status=AssessmentModerationReviewStatus.IN_PROGRESS,
    )

    repository.reviews[review.id] = review

    _install_repository(
        monkeypatch,
        repository,
    )

    response = SimpleNamespace(
        id=200,
        script_id=40,
        question_id=500,
    )

    decision = SimpleNamespace(
        id=300,
        response_id=200,
        status=MarkingDecisionStatus.MARKED,
        mark_awarded=Decimal("5.00"),
        reviewed_at=None,
        moderation_comment=None,
    )

    question = SimpleNamespace(
        id=500,
        assessment_id=20,
        maximum_mark=Decimal("10.00"),
    )

    async def fake_review_lookup(*args, **kwargs):
        return review

    async def fake_access(*args, **kwargs):
        return _script(
            script_status=AssessmentScriptStatus.MODERATION,
        )

    async def fake_response(*args, **kwargs):
        return response

    async def fake_decision(*args, **kwargs):
        return decision

    async def fake_question(*args, **kwargs):
        return question

    monkeypatch.setattr(
        service,
        "_get_review_or_404",
        fake_review_lookup,
    )
    monkeypatch.setattr(
        service,
        "_ensure_review_access",
        fake_access,
    )
    monkeypatch.setattr(
        service,
        "_get_response_or_404",
        fake_response,
    )
    monkeypatch.setattr(
        service,
        "_get_decision_or_404",
        fake_decision,
    )
    monkeypatch.setattr(
        service,
        "_get_question_or_404",
        fake_question,
    )

    with pytest.raises(
        HTTPException,
    ) as exc:
        await service.add_moderation_item(
            db,
            _user(),
            review.id,
            response_id=200,
            marking_decision_id=300,
            outcome=AssessmentModerationItemOutcome.ADJUSTED,
            mark_after=Decimal("5.00"),
        )

    assert exc.value.status_code == 422


@pytest.mark.asyncio
async def test_confirmed_outcome_cannot_change_mark(
    monkeypatch,
) -> None:
    db = _FakeDB()
    repository = _FakeModerationRepository()

    review = _review(
        review_status=AssessmentModerationReviewStatus.IN_PROGRESS,
    )

    repository.reviews[review.id] = review

    _install_repository(
        monkeypatch,
        repository,
    )

    response = SimpleNamespace(
        id=200,
        script_id=40,
        question_id=500,
    )

    decision = SimpleNamespace(
        id=300,
        response_id=200,
        status=MarkingDecisionStatus.MARKED,
        mark_awarded=Decimal("5.00"),
        reviewed_at=None,
        moderation_comment=None,
    )

    question = SimpleNamespace(
        id=500,
        assessment_id=20,
        maximum_mark=Decimal("10.00"),
    )

    async def fake_review_lookup(*args, **kwargs):
        return review

    async def fake_access(*args, **kwargs):
        return _script(
            script_status=AssessmentScriptStatus.MODERATION,
        )

    async def fake_response(*args, **kwargs):
        return response

    async def fake_decision(*args, **kwargs):
        return decision

    async def fake_question(*args, **kwargs):
        return question

    monkeypatch.setattr(
        service,
        "_get_review_or_404",
        fake_review_lookup,
    )
    monkeypatch.setattr(
        service,
        "_ensure_review_access",
        fake_access,
    )
    monkeypatch.setattr(
        service,
        "_get_response_or_404",
        fake_response,
    )
    monkeypatch.setattr(
        service,
        "_get_decision_or_404",
        fake_decision,
    )
    monkeypatch.setattr(
        service,
        "_get_question_or_404",
        fake_question,
    )

    with pytest.raises(
        HTTPException,
    ) as exc:
        await service.add_moderation_item(
            db,
            _user(),
            review.id,
            response_id=200,
            marking_decision_id=300,
            outcome=AssessmentModerationItemOutcome.CONFIRMED,
            mark_after=Decimal("6.00"),
        )

    assert exc.value.status_code == 422


@pytest.mark.asyncio
async def test_response_must_belong_to_review_script(
    monkeypatch,
) -> None:
    db = _FakeDB()

    review = _review(
        script_id=40,
        review_status=AssessmentModerationReviewStatus.IN_PROGRESS,
    )

    response = SimpleNamespace(
        id=200,
        script_id=999,
        question_id=500,
    )

    async def fake_review_lookup(*args, **kwargs):
        return review

    async def fake_access(*args, **kwargs):
        return _script(
            script_id=40,
            script_status=AssessmentScriptStatus.MODERATION,
        )

    async def fake_response(*args, **kwargs):
        return response

    monkeypatch.setattr(
        service,
        "_get_review_or_404",
        fake_review_lookup,
    )
    monkeypatch.setattr(
        service,
        "_ensure_review_access",
        fake_access,
    )
    monkeypatch.setattr(
        service,
        "_get_response_or_404",
        fake_response,
    )

    with pytest.raises(
        HTTPException,
    ) as exc:
        await service.add_moderation_item(
            db,
            _user(),
            review.id,
            response_id=200,
            marking_decision_id=300,
            outcome=AssessmentModerationItemOutcome.CONFIRMED,
        )

    assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_marking_decision_must_belong_to_response(
    monkeypatch,
) -> None:
    db = _FakeDB()

    review = _review(
        review_status=AssessmentModerationReviewStatus.IN_PROGRESS,
    )

    response = SimpleNamespace(
        id=200,
        script_id=40,
        question_id=500,
    )

    decision = SimpleNamespace(
        id=300,
        response_id=999,
        status=MarkingDecisionStatus.MARKED,
        mark_awarded=Decimal("5.00"),
    )

    async def fake_review_lookup(*args, **kwargs):
        return review

    async def fake_access(*args, **kwargs):
        return _script(
            script_status=AssessmentScriptStatus.MODERATION,
        )

    async def fake_response(*args, **kwargs):
        return response

    async def fake_decision(*args, **kwargs):
        return decision

    monkeypatch.setattr(
        service,
        "_get_review_or_404",
        fake_review_lookup,
    )
    monkeypatch.setattr(
        service,
        "_ensure_review_access",
        fake_access,
    )
    monkeypatch.setattr(
        service,
        "_get_response_or_404",
        fake_response,
    )
    monkeypatch.setattr(
        service,
        "_get_decision_or_404",
        fake_decision,
    )

    with pytest.raises(
        HTTPException,
    ) as exc:
        await service.add_moderation_item(
            db,
            _user(),
            review.id,
            response_id=200,
            marking_decision_id=300,
            outcome=AssessmentModerationItemOutcome.CONFIRMED,
        )

    assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_moderated_mark_cannot_exceed_question_maximum(
    monkeypatch,
) -> None:
    db = _FakeDB()

    review = _review(
        review_status=AssessmentModerationReviewStatus.IN_PROGRESS,
    )

    response = SimpleNamespace(
        id=200,
        script_id=40,
        question_id=500,
    )

    decision = SimpleNamespace(
        id=300,
        response_id=200,
        status=MarkingDecisionStatus.MARKED,
        mark_awarded=Decimal("5.00"),
        reviewed_at=None,
        moderation_comment=None,
    )

    question = SimpleNamespace(
        id=500,
        assessment_id=20,
        maximum_mark=Decimal("10.00"),
    )

    async def fake_review_lookup(*args, **kwargs):
        return review

    async def fake_access(*args, **kwargs):
        return _script(
            script_status=AssessmentScriptStatus.MODERATION,
        )

    async def fake_response(*args, **kwargs):
        return response

    async def fake_decision(*args, **kwargs):
        return decision

    async def fake_question(*args, **kwargs):
        return question

    monkeypatch.setattr(
        service,
        "_get_review_or_404",
        fake_review_lookup,
    )
    monkeypatch.setattr(
        service,
        "_ensure_review_access",
        fake_access,
    )
    monkeypatch.setattr(
        service,
        "_get_response_or_404",
        fake_response,
    )
    monkeypatch.setattr(
        service,
        "_get_decision_or_404",
        fake_decision,
    )
    monkeypatch.setattr(
        service,
        "_get_question_or_404",
        fake_question,
    )

    with pytest.raises(
        HTTPException,
    ) as exc:
        await service.add_moderation_item(
            db,
            _user(),
            review.id,
            response_id=200,
            marking_decision_id=300,
            outcome=AssessmentModerationItemOutcome.ADJUSTED,
            mark_after=Decimal("11.00"),
        )

    assert exc.value.status_code == 422


@pytest.mark.asyncio
async def test_finalised_decision_can_be_adjusted_only_through_moderation(
    monkeypatch,
) -> None:
    db = _FakeDB()
    repository = _FakeModerationRepository()

    review = _review(
        review_status=AssessmentModerationReviewStatus.IN_PROGRESS,
    )

    repository.reviews[review.id] = review

    _install_repository(
        monkeypatch,
        repository,
    )

    response = SimpleNamespace(
        id=200,
        script_id=40,
        question_id=500,
    )

    decision = SimpleNamespace(
        id=300,
        response_id=200,
        status=MarkingDecisionStatus.FINALISED,
        mark_awarded=Decimal("7.00"),
        reviewed_at=None,
        moderation_comment=None,
    )

    question = SimpleNamespace(
        id=500,
        assessment_id=20,
        maximum_mark=Decimal("10.00"),
    )

    async def fake_review_lookup(*args, **kwargs):
        return review

    async def fake_access(*args, **kwargs):
        return _script(
            script_status=AssessmentScriptStatus.FINALISED,
        )

    async def fake_response(*args, **kwargs):
        return response

    async def fake_decision(*args, **kwargs):
        return decision

    async def fake_question(*args, **kwargs):
        return question

    monkeypatch.setattr(
        service,
        "_get_review_or_404",
        fake_review_lookup,
    )
    monkeypatch.setattr(
        service,
        "_ensure_review_access",
        fake_access,
    )
    monkeypatch.setattr(
        service,
        "_get_response_or_404",
        fake_response,
    )
    monkeypatch.setattr(
        service,
        "_get_decision_or_404",
        fake_decision,
    )
    monkeypatch.setattr(
        service,
        "_get_question_or_404",
        fake_question,
    )

    result = await service.add_moderation_item(
        db,
        _user(),
        review.id,
        response_id=200,
        marking_decision_id=300,
        outcome=AssessmentModerationItemOutcome.ADJUSTED,
        mark_after=Decimal("8.00"),
    )

    assert result.mark_changed is True
    assert decision.mark_awarded == Decimal("8.00")

    # A finalised decision remains finalised.
    assert decision.status == MarkingDecisionStatus.FINALISED


# ----------------------------------------------------------------------
# Review outcome validation
# ----------------------------------------------------------------------


def test_adjusted_item_requires_adjusted_or_escalated_review() -> None:
    items = [
        _moderation_item(
            outcome=AssessmentModerationItemOutcome.ADJUSTED,
            mark_before=Decimal("5.00"),
            mark_after=Decimal("6.00"),
            mark_changed=True,
        ),
    ]

    with pytest.raises(
        HTTPException,
    ) as exc:
        service._validate_review_outcome_against_items(
            review_outcome=AssessmentModerationOutcome.CONFIRMED,
            items=items,
        )

    assert exc.value.status_code == 409


def test_escalated_item_requires_escalated_review() -> None:
    items = [
        _moderation_item(
            outcome=AssessmentModerationItemOutcome.ESCALATED,
        ),
    ]

    with pytest.raises(
        HTTPException,
    ) as exc:
        service._validate_review_outcome_against_items(
            review_outcome=AssessmentModerationOutcome.RETURNED,
            items=items,
        )

    assert exc.value.status_code == 409


# ----------------------------------------------------------------------
# Review completion
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_confirmed_review_finalises_script_in_moderation(
    monkeypatch,
) -> None:
    db = _FakeDB()
    repository = _FakeModerationRepository()

    review = _review(
        review_status=AssessmentModerationReviewStatus.IN_PROGRESS,
    )

    review.items = [
        _moderation_item(),
    ]

    repository.reviews[review.id] = review

    _install_repository(
        monkeypatch,
        repository,
    )

    script = _script(
        script_status=AssessmentScriptStatus.MODERATION,
    )

    async def fake_review_lookup(
        db,
        review_id,
        *,
        include_items=False,
    ):
        del db
        del review_id
        del include_items

        return review

    async def fake_access(
        db,
        current_user,
        supplied_review,
    ):
        del db
        del current_user
        del supplied_review

        return script

    async def fake_marking_complete(
        db,
        script_id,
    ):
        del db

        assert script_id == script.id

    monkeypatch.setattr(
        service,
        "_get_review_or_404",
        fake_review_lookup,
    )
    monkeypatch.setattr(
        service,
        "_ensure_review_access",
        fake_access,
    )
    monkeypatch.setattr(
        service,
        "_ensure_script_marking_complete_for_finalisation",
        fake_marking_complete,
    )

    result = await service.complete_moderation_review(
        db,
        _user(),
        review.id,
        outcome=AssessmentModerationOutcome.CONFIRMED,
    )

    assert result.status == AssessmentModerationReviewStatus.COMPLETED
    assert result.outcome == AssessmentModerationOutcome.CONFIRMED
    assert result.completed_at is not None

    assert script.status == AssessmentScriptStatus.FINALISED
    assert db.commits == 1


@pytest.mark.asyncio
async def test_adjusted_review_finalises_script(
    monkeypatch,
) -> None:
    db = _FakeDB()
    repository = _FakeModerationRepository()

    review = _review(
        review_status=AssessmentModerationReviewStatus.IN_PROGRESS,
    )

    review.items = [
        _moderation_item(
            outcome=AssessmentModerationItemOutcome.ADJUSTED,
            mark_before=Decimal("5.00"),
            mark_after=Decimal("6.00"),
            mark_changed=True,
        ),
    ]

    repository.reviews[review.id] = review

    _install_repository(
        monkeypatch,
        repository,
    )

    script = _script(
        script_status=AssessmentScriptStatus.MODERATION,
    )

    async def fake_review_lookup(*args, **kwargs):
        return review

    async def fake_access(*args, **kwargs):
        return script

    async def fake_complete(*args, **kwargs):
        return None

    monkeypatch.setattr(
        service,
        "_get_review_or_404",
        fake_review_lookup,
    )
    monkeypatch.setattr(
        service,
        "_ensure_review_access",
        fake_access,
    )
    monkeypatch.setattr(
        service,
        "_ensure_script_marking_complete_for_finalisation",
        fake_complete,
    )

    result = await service.complete_moderation_review(
        db,
        _user(),
        review.id,
        outcome=AssessmentModerationOutcome.ADJUSTED,
    )

    assert result.outcome == AssessmentModerationOutcome.ADJUSTED
    assert script.status == AssessmentScriptStatus.FINALISED


@pytest.mark.asyncio
async def test_returned_review_leaves_script_in_moderation(
    monkeypatch,
) -> None:
    db = _FakeDB()
    repository = _FakeModerationRepository()

    review = _review(
        review_status=AssessmentModerationReviewStatus.IN_PROGRESS,
    )

    review.items = [
        _moderation_item(
            outcome=AssessmentModerationItemOutcome.RETURNED,
        ),
    ]

    repository.reviews[review.id] = review

    _install_repository(
        monkeypatch,
        repository,
    )

    script = _script(
        script_status=AssessmentScriptStatus.MODERATION,
    )

    async def fake_review_lookup(*args, **kwargs):
        return review

    async def fake_access(*args, **kwargs):
        return script

    monkeypatch.setattr(
        service,
        "_get_review_or_404",
        fake_review_lookup,
    )
    monkeypatch.setattr(
        service,
        "_ensure_review_access",
        fake_access,
    )

    result = await service.complete_moderation_review(
        db,
        _user(),
        review.id,
        outcome=AssessmentModerationOutcome.RETURNED,
    )

    assert result.status == AssessmentModerationReviewStatus.COMPLETED
    assert result.outcome == AssessmentModerationOutcome.RETURNED

    assert script.status == AssessmentScriptStatus.MODERATION


@pytest.mark.asyncio
async def test_review_cannot_complete_without_items(
    monkeypatch,
) -> None:
    db = _FakeDB()

    review = _review(
        review_status=AssessmentModerationReviewStatus.IN_PROGRESS,
    )

    review.items = []

    async def fake_review_lookup(*args, **kwargs):
        return review

    async def fake_access(*args, **kwargs):
        return _script(
            script_status=AssessmentScriptStatus.MODERATION,
        )

    monkeypatch.setattr(
        service,
        "_get_review_or_404",
        fake_review_lookup,
    )
    monkeypatch.setattr(
        service,
        "_ensure_review_access",
        fake_access,
    )

    with pytest.raises(
        HTTPException,
    ) as exc:
        await service.complete_moderation_review(
            db,
            _user(),
            review.id,
            outcome=AssessmentModerationOutcome.CONFIRMED,
        )

    assert exc.value.status_code == 409


# ----------------------------------------------------------------------
# Cancellation
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cancel_only_review_returns_script_to_marked(
    monkeypatch,
) -> None:
    db = _FakeDB()
    repository = _FakeModerationRepository()

    review = _review(
        review_status=AssessmentModerationReviewStatus.PENDING,
    )

    repository.reviews[review.id] = review
    repository.script_reviews = [
        review,
    ]

    _install_repository(
        monkeypatch,
        repository,
    )

    script = _script(
        script_status=AssessmentScriptStatus.MODERATION,
    )

    async def fake_review_lookup(
        db,
        review_id,
        *,
        include_items=False,
    ):
        del db
        del review_id
        del include_items

        return review

    async def fake_access(
        db,
        current_user,
        supplied_review,
    ):
        del db
        del current_user
        del supplied_review

        return script

    monkeypatch.setattr(
        service,
        "_get_review_or_404",
        fake_review_lookup,
    )
    monkeypatch.setattr(
        service,
        "_ensure_review_access",
        fake_access,
    )

    result = await service.cancel_moderation_review(
        db,
        _user(),
        review.id,
        cancellation_reason="Review created in error.",
    )

    assert result.status == AssessmentModerationReviewStatus.CANCELLED
    assert result.cancelled_at is not None
    assert result.cancelled_by_id == 100
    assert result.cancellation_reason == "Review created in error."

    assert script.status == AssessmentScriptStatus.MARKED
    assert db.commits == 1


@pytest.mark.asyncio
async def test_completed_review_cannot_be_cancelled(
    monkeypatch,
) -> None:
    db = _FakeDB()

    review = _review(
        review_status=AssessmentModerationReviewStatus.COMPLETED,
        outcome=AssessmentModerationOutcome.CONFIRMED,
    )

    async def fake_review_lookup(*args, **kwargs):
        return review

    async def fake_access(*args, **kwargs):
        return _script(
            script_status=AssessmentScriptStatus.FINALISED,
        )

    monkeypatch.setattr(
        service,
        "_get_review_or_404",
        fake_review_lookup,
    )
    monkeypatch.setattr(
        service,
        "_ensure_review_access",
        fake_access,
    )

    with pytest.raises(
        HTTPException,
    ) as exc:
        await service.cancel_moderation_review(
            db,
            _user(),
            review.id,
            cancellation_reason="Attempted cancellation.",
        )

    assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_blank_cancellation_reason_rejected(
    monkeypatch,
) -> None:
    db = _FakeDB()

    review = _review(
        review_status=AssessmentModerationReviewStatus.PENDING,
    )

    async def fake_review_lookup(*args, **kwargs):
        return review

    async def fake_access(*args, **kwargs):
        return _script(
            script_status=AssessmentScriptStatus.MODERATION,
        )

    monkeypatch.setattr(
        service,
        "_get_review_or_404",
        fake_review_lookup,
    )
    monkeypatch.setattr(
        service,
        "_ensure_review_access",
        fake_access,
    )

    with pytest.raises(
        HTTPException,
    ) as exc:
        await service.cancel_moderation_review(
            db,
            _user(),
            review.id,
            cancellation_reason="   ",
        )

    assert exc.value.status_code == 422
