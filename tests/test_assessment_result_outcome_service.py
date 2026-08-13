from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError

import app.services.assessment_result_outcome_service as service
from app.models.assessment_result_outcome import (
    AssessmentResultChangeType,
    AssessmentResultOutcomeStatus,
)
from app.repositories.assessment_result_outcome import _UNSET

# ---------------------------------------------------------------------------
# Test-data helpers
# ---------------------------------------------------------------------------


def _user(
    *,
    user_id: int = 10,
    school_id: int = 1,
):
    return SimpleNamespace(
        id=user_id,
        school_id=school_id,
        full_name=f"User {user_id}",
        roles=["teacher"],
    )


def _outcome(
    *,
    outcome_id: int = 1,
    school_id: int = 1,
    assessment_id: int = 100,
    candidate_id: int = 200,
    script_id: int = 300,
    version: int = 1,
    status_value: AssessmentResultOutcomeStatus = (
        AssessmentResultOutcomeStatus.AUTHORITATIVE
    ),
    change_type: AssessmentResultChangeType = (AssessmentResultChangeType.INITIAL),
    supersedes_id: int | None = None,
    is_authoritative: bool = True,
    mark: Decimal = Decimal("72"),
    maximum: Decimal = Decimal("80"),
    percentage: Decimal | None = Decimal("90"),
    script_version: int = 1,
    reason: str | None = None,
    notes: str | None = None,
    effective_at: datetime | None = None,
    recorded_by_id: int = 10,
    withdrawn_at: datetime | None = None,
    withdrawn_by_id: int | None = None,
    withdrawal_reason: str | None = None,
):
    recorded_by = _user(
        user_id=recorded_by_id,
        school_id=school_id,
    )

    withdrawn_by = (
        _user(
            user_id=withdrawn_by_id,
            school_id=school_id,
        )
        if withdrawn_by_id is not None
        else None
    )

    return SimpleNamespace(
        id=outcome_id,
        school_id=school_id,
        assessment_id=assessment_id,
        candidate_id=candidate_id,
        script_id=script_id,
        version=version,
        status=status_value,
        change_type=change_type,
        supersedes_id=supersedes_id,
        is_authoritative=is_authoritative,
        mark_awarded_snapshot=mark,
        maximum_mark_snapshot=maximum,
        percentage_snapshot=percentage,
        grading_scheme_id_snapshot=50,
        grading_scheme_name_snapshot="GCSE 9-1",
        grading_basis_snapshot="percentage",
        grade_boundary_id_snapshot=51,
        grade_label_snapshot="9",
        grade_points_snapshot=Decimal("9"),
        is_pass_snapshot=True,
        script_version_snapshot=script_version,
        reason=reason,
        notes=notes,
        effective_at=(
            effective_at
            or datetime(
                2026,
                8,
                13,
                12,
                0,
                tzinfo=timezone.utc,
            )
        ),
        recorded_by_id=recorded_by_id,
        recorded_at=datetime(
            2026,
            8,
            13,
            12,
            1,
            tzinfo=timezone.utc,
        ),
        withdrawn_at=withdrawn_at,
        withdrawn_by_id=withdrawn_by_id,
        withdrawal_reason=withdrawal_reason,
        recorded_by=recorded_by,
        withdrawn_by=withdrawn_by,
    )


def _snapshot(
    *,
    school_id: int = 1,
    assessment_id: int = 100,
    candidate_id: int = 200,
    student_id: int = 400,
    script_id: int = 300,
    script_version: int = 1,
    mark: Decimal = Decimal("72"),
    maximum: Decimal = Decimal("80"),
    percentage: Decimal | None = Decimal("90"),
):
    return {
        "school_id": school_id,
        "assessment_id": assessment_id,
        "candidate_id": candidate_id,
        "student_id": student_id,
        "script_id": script_id,
        "script_version_snapshot": script_version,
        "mark_awarded_snapshot": mark,
        "maximum_mark_snapshot": maximum,
        "percentage_snapshot": percentage,
        "grading_scheme_id_snapshot": 50,
        "grading_scheme_name_snapshot": "GCSE 9-1",
        "grading_basis_snapshot": "percentage",
        "grade_boundary_id_snapshot": 51,
        "grade_label_snapshot": "9",
        "grade_points_snapshot": Decimal("9"),
        "is_pass_snapshot": True,
    }


def _script_result(
    *,
    assessment_id: int = 100,
    candidate_id: int = 200,
    student_id: int = 400,
    script_id: int = 300,
    script_version: int = 1,
    fully_finalised: bool = True,
    finalised_mark: Decimal | None = Decimal("72"),
    maximum_mark: Decimal | None = Decimal("80"),
    finalised_percentage: Decimal | None = Decimal("90"),
):
    return {
        "assessment_id": assessment_id,
        "candidate_id": candidate_id,
        "student_id": student_id,
        "script_id": script_id,
        "script_version": script_version,
        "is_fully_finalised": fully_finalised,
        "finalised_mark_awarded": finalised_mark,
        "maximum_mark": maximum_mark,
        "finalised_percentage": finalised_percentage,
    }


def _grade_result():
    return {
        "grading_scheme_id": 50,
        "grading_scheme_name": "GCSE 9-1",
        "basis": SimpleNamespace(
            value="percentage",
        ),
        "boundary_id": 51,
        "grade": "9",
        "grade_points": Decimal("9"),
        "is_pass": True,
    }


class FakeDB:
    def __init__(self):
        self.committed = False
        self.rolled_back = False
        self.deleted = []
        self.refreshed = []

    async def commit(self):
        self.committed = True

    async def rollback(self):
        self.rolled_back = True

    async def refresh(self, obj):
        self.refreshed.append(obj)

    async def delete(self, obj):
        self.deleted.append(obj)

    async def get(self, model, object_id):
        return None


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "value",
    [
        0,
        -1,
        True,
    ],
)
def test_validate_positive_integer_rejects_invalid_values(
    value,
):
    with pytest.raises(HTTPException) as exc:
        service._validate_positive_integer(
            value,
            field_name="script_id",
        )

    assert exc.value.status_code == 422


def test_normalise_optional_text_trims():
    assert (
        service._normalise_optional_text(
            "  corrected result  ",
            field_name="reason",
        )
        == "corrected result"
    )


def test_normalise_optional_text_blank_becomes_none():
    assert (
        service._normalise_optional_text(
            "   ",
            field_name="reason",
        )
        is None
    )


def test_normalise_optional_text_rejects_non_string():
    with pytest.raises(HTTPException) as exc:
        service._normalise_optional_text(
            123,
            field_name="reason",
        )

    assert exc.value.status_code == 422


def test_normalise_required_text_rejects_blank():
    with pytest.raises(HTTPException) as exc:
        service._normalise_required_text(
            "   ",
            field_name="withdrawal_reason",
        )

    assert exc.value.status_code == 422


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (
            "initial",
            AssessmentResultChangeType.INITIAL,
        ),
        (
            "retake",
            AssessmentResultChangeType.RETAKE,
        ),
        (
            "remark",
            AssessmentResultChangeType.REMARK,
        ),
        (
            "correction",
            AssessmentResultChangeType.CORRECTION,
        ),
        (
            "moderation",
            AssessmentResultChangeType.MODERATION,
        ),
        (
            "administrative",
            AssessmentResultChangeType.ADMINISTRATIVE,
        ),
    ],
)
def test_normalise_change_type(
    raw,
    expected,
):
    assert service._normalise_change_type(raw) == expected


def test_normalise_change_type_rejects_invalid_value():
    with pytest.raises(HTTPException) as exc:
        service._normalise_change_type(
            "something_else",
        )

    assert exc.value.status_code == 422


def test_normalise_effective_at_defaults_to_now(
    monkeypatch,
):
    fixed = datetime(
        2026,
        8,
        13,
        20,
        0,
        tzinfo=timezone.utc,
    )

    monkeypatch.setattr(
        service,
        "_utc_now",
        lambda: fixed,
    )

    assert service._normalise_effective_at(None) == fixed


# ---------------------------------------------------------------------------
# Reason requirements
# ---------------------------------------------------------------------------


def test_initial_outcome_does_not_require_reason():
    service._validate_reason_requirement(
        change_type=AssessmentResultChangeType.INITIAL,
        reason=None,
    )


@pytest.mark.parametrize(
    "change_type",
    [
        AssessmentResultChangeType.RETAKE,
        AssessmentResultChangeType.REMARK,
        AssessmentResultChangeType.CORRECTION,
        AssessmentResultChangeType.MODERATION,
        AssessmentResultChangeType.ADMINISTRATIVE,
    ],
)
def test_non_initial_outcome_requires_reason(
    change_type,
):
    with pytest.raises(HTTPException) as exc:
        service._validate_reason_requirement(
            change_type=change_type,
            reason=None,
        )

    assert exc.value.status_code == 422


# ---------------------------------------------------------------------------
# Snapshot building
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_build_snapshot_requires_fully_finalised_script(
    monkeypatch,
):
    async def fake_result(**kwargs):
        return _script_result(
            fully_finalised=False,
        )

    monkeypatch.setattr(
        service,
        "get_script_result",
        fake_result,
    )

    with pytest.raises(HTTPException) as exc:
        await service._build_result_snapshot(
            FakeDB(),
            _user(),
            script_id=300,
        )

    assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_build_snapshot_requires_finalised_mark(
    monkeypatch,
):
    async def fake_result(**kwargs):
        return _script_result(
            finalised_mark=None,
        )

    monkeypatch.setattr(
        service,
        "get_script_result",
        fake_result,
    )

    with pytest.raises(HTTPException) as exc:
        await service._build_result_snapshot(
            FakeDB(),
            _user(),
            script_id=300,
        )

    assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_build_snapshot_requires_maximum_mark(
    monkeypatch,
):
    async def fake_result(**kwargs):
        return _script_result(
            maximum_mark=None,
        )

    monkeypatch.setattr(
        service,
        "get_script_result",
        fake_result,
    )

    with pytest.raises(HTTPException) as exc:
        await service._build_result_snapshot(
            FakeDB(),
            _user(),
            script_id=300,
        )

    assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_build_snapshot_includes_grade_data(
    monkeypatch,
):
    async def fake_result(**kwargs):
        return _script_result()

    async def fake_school(
        db,
        *,
        assessment_id,
    ):
        return 1

    async def fake_grade(
        db,
        current_user,
        *,
        script_id,
    ):
        return _grade_result()

    monkeypatch.setattr(
        service,
        "get_script_result",
        fake_result,
    )
    monkeypatch.setattr(
        service,
        "_get_assessment_school_id",
        fake_school,
    )
    monkeypatch.setattr(
        service,
        "_get_optional_grade_snapshot",
        fake_grade,
    )

    result = await service._build_result_snapshot(
        FakeDB(),
        _user(),
        script_id=300,
    )

    assert result["mark_awarded_snapshot"] == Decimal("72")
    assert result["maximum_mark_snapshot"] == Decimal("80")
    assert result["percentage_snapshot"] == Decimal("90")
    assert result["grade_label_snapshot"] == "9"
    assert result["grade_points_snapshot"] == Decimal("9")


@pytest.mark.asyncio
async def test_build_snapshot_allows_no_grading_scheme(
    monkeypatch,
):
    async def fake_result(**kwargs):
        return _script_result()

    async def fake_school(
        db,
        *,
        assessment_id,
    ):
        return 1

    async def fake_grade(
        db,
        current_user,
        *,
        script_id,
    ):
        return None

    monkeypatch.setattr(
        service,
        "get_script_result",
        fake_result,
    )
    monkeypatch.setattr(
        service,
        "_get_assessment_school_id",
        fake_school,
    )
    monkeypatch.setattr(
        service,
        "_get_optional_grade_snapshot",
        fake_grade,
    )

    result = await service._build_result_snapshot(
        FakeDB(),
        _user(),
        script_id=300,
    )

    assert result["grade_label_snapshot"] is None
    assert result["grading_scheme_id_snapshot"] is None
    assert result["grade_points_snapshot"] is None


@pytest.mark.asyncio
async def test_optional_grade_snapshot_swallows_only_missing_scheme(
    monkeypatch,
):
    async def fake_grade(**kwargs):
        raise HTTPException(
            status_code=404,
            detail=("No active grading scheme is configured " "for this assessment."),
        )

    monkeypatch.setattr(
        service,
        "grade_script_result",
        fake_grade,
    )

    result = await service._get_optional_grade_snapshot(
        FakeDB(),
        _user(),
        script_id=300,
    )

    assert result is None


@pytest.mark.asyncio
async def test_optional_grade_snapshot_propagates_other_404(
    monkeypatch,
):
    async def fake_grade(**kwargs):
        raise HTTPException(
            status_code=404,
            detail="Assessment not found.",
        )

    monkeypatch.setattr(
        service,
        "grade_script_result",
        fake_grade,
    )

    with pytest.raises(HTTPException) as exc:
        await service._get_optional_grade_snapshot(
            FakeDB(),
            _user(),
            script_id=300,
        )

    assert exc.value.detail == "Assessment not found."


# ---------------------------------------------------------------------------
# Transition rules
# ---------------------------------------------------------------------------


def test_initial_allowed_with_no_history():
    service._validate_new_outcome_transition(
        change_type=AssessmentResultChangeType.INITIAL,
        snapshot=_snapshot(),
        latest=None,
        current=None,
    )


def test_initial_rejected_when_history_exists():
    with pytest.raises(HTTPException) as exc:
        service._validate_new_outcome_transition(
            change_type=AssessmentResultChangeType.INITIAL,
            snapshot=_snapshot(),
            latest=_outcome(),
            current=_outcome(),
        )

    assert exc.value.status_code == 409


def test_new_outcome_rejected_when_draft_already_exists():
    latest = _outcome(
        status_value=AssessmentResultOutcomeStatus.DRAFT,
        is_authoritative=False,
    )

    with pytest.raises(HTTPException) as exc:
        service._validate_new_outcome_transition(
            change_type=AssessmentResultChangeType.REMARK,
            snapshot=_snapshot(),
            latest=latest,
            current=_outcome(),
        )

    assert exc.value.status_code == 409


@pytest.mark.parametrize(
    "change_type",
    [
        AssessmentResultChangeType.RETAKE,
        AssessmentResultChangeType.REMARK,
        AssessmentResultChangeType.CORRECTION,
        AssessmentResultChangeType.MODERATION,
        AssessmentResultChangeType.ADMINISTRATIVE,
    ],
)
def test_non_initial_requires_current_authoritative_outcome(
    change_type,
):
    with pytest.raises(HTTPException) as exc:
        service._validate_new_outcome_transition(
            change_type=change_type,
            snapshot=_snapshot(),
            latest=None,
            current=None,
        )

    assert exc.value.status_code == 409


def test_retake_requires_different_script():
    current = _outcome(
        script_id=300,
        script_version=1,
    )

    with pytest.raises(HTTPException) as exc:
        service._validate_new_outcome_transition(
            change_type=AssessmentResultChangeType.RETAKE,
            snapshot=_snapshot(
                script_id=300,
                script_version=2,
            ),
            latest=current,
            current=current,
        )

    assert exc.value.status_code == 409


def test_retake_requires_later_script_version():
    current = _outcome(
        script_id=300,
        script_version=2,
    )

    with pytest.raises(HTTPException) as exc:
        service._validate_new_outcome_transition(
            change_type=AssessmentResultChangeType.RETAKE,
            snapshot=_snapshot(
                script_id=301,
                script_version=2,
            ),
            latest=current,
            current=current,
        )

    assert exc.value.status_code == 409


def test_retake_allows_later_different_script():
    current = _outcome(
        script_id=300,
        script_version=1,
    )

    service._validate_new_outcome_transition(
        change_type=AssessmentResultChangeType.RETAKE,
        snapshot=_snapshot(
            script_id=301,
            script_version=2,
        ),
        latest=current,
        current=current,
    )


@pytest.mark.parametrize(
    "change_type",
    [
        AssessmentResultChangeType.REMARK,
        AssessmentResultChangeType.CORRECTION,
        AssessmentResultChangeType.MODERATION,
    ],
)
def test_same_script_changes_require_same_script(
    change_type,
):
    current = _outcome(
        script_id=300,
    )

    with pytest.raises(HTTPException) as exc:
        service._validate_new_outcome_transition(
            change_type=change_type,
            snapshot=_snapshot(
                script_id=301,
            ),
            latest=current,
            current=current,
        )

    assert exc.value.status_code == 409


@pytest.mark.parametrize(
    "change_type",
    [
        AssessmentResultChangeType.REMARK,
        AssessmentResultChangeType.CORRECTION,
        AssessmentResultChangeType.MODERATION,
    ],
)
def test_same_script_changes_allow_same_script(
    change_type,
):
    current = _outcome(
        script_id=300,
    )

    service._validate_new_outcome_transition(
        change_type=change_type,
        snapshot=_snapshot(
            script_id=300,
        ),
        latest=current,
        current=current,
    )


# ---------------------------------------------------------------------------
# Serialisation
# ---------------------------------------------------------------------------


def test_outcome_serialisation_contains_history_and_audit_fields():
    outcome = _outcome(
        outcome_id=9,
        supersedes_id=8,
        reason="Remark completed.",
        notes="Two marks added.",
        withdrawn_by_id=20,
        withdrawal_reason="Administrative withdrawal.",
    )

    payload = service._outcome_to_dict(
        outcome,
    )

    assert payload["id"] == 9
    assert payload["supersedes_id"] == 8
    assert payload["mark_awarded_snapshot"] == Decimal("72")
    assert payload["grade_label_snapshot"] == "9"
    assert payload["recorded_by_name"] == "User 10"
    assert payload["withdrawn_by_name"] == "User 20"


# ---------------------------------------------------------------------------
# Repository fake
# ---------------------------------------------------------------------------


def _patch_repository(
    monkeypatch,
    *,
    current=None,
    latest=None,
    history=None,
    by_id=None,
):
    calls: list[tuple] = []
    created: list = []

    class FakeRepository:
        def __init__(self, db):
            self.db = db

        async def get_authoritative_for_candidate(
            self,
            candidate_id,
            *,
            school_id=None,
            include_relationships=True,
            for_update=False,
        ):
            calls.append(
                (
                    "get_authoritative",
                    candidate_id,
                    school_id,
                    for_update,
                )
            )
            return current

        async def get_latest_for_candidate(
            self,
            candidate_id,
            *,
            school_id=None,
            include_relationships=True,
        ):
            calls.append(
                (
                    "get_latest",
                    candidate_id,
                    school_id,
                )
            )
            return latest

        async def get_next_version(
            self,
            candidate_id,
            *,
            lock_history=False,
        ):
            calls.append(
                (
                    "get_next_version",
                    candidate_id,
                    lock_history,
                )
            )
            return 1 if latest is None else latest.version + 1

        async def create_outcome(self, **kwargs):
            calls.append(
                (
                    "create_outcome",
                    kwargs,
                )
            )

            outcome = _outcome(
                outcome_id=99,
                school_id=kwargs["school_id"],
                assessment_id=kwargs["assessment_id"],
                candidate_id=kwargs["candidate_id"],
                script_id=kwargs["script_id"],
                version=kwargs["version"],
                status_value=kwargs["status"],
                change_type=kwargs["change_type"],
                supersedes_id=kwargs["supersedes_id"],
                is_authoritative=kwargs["is_authoritative"],
                mark=kwargs["mark_awarded_snapshot"],
                maximum=kwargs["maximum_mark_snapshot"],
                percentage=kwargs["percentage_snapshot"],
                script_version=kwargs["script_version_snapshot"],
                reason=kwargs["reason"],
                notes=kwargs["notes"],
                effective_at=kwargs["effective_at"],
                recorded_by_id=kwargs["recorded_by_id"],
            )

            outcome.grading_scheme_id_snapshot = kwargs["grading_scheme_id_snapshot"]
            outcome.grading_scheme_name_snapshot = kwargs[
                "grading_scheme_name_snapshot"
            ]
            outcome.grading_basis_snapshot = kwargs["grading_basis_snapshot"]
            outcome.grade_boundary_id_snapshot = kwargs["grade_boundary_id_snapshot"]
            outcome.grade_label_snapshot = kwargs["grade_label_snapshot"]
            outcome.grade_points_snapshot = kwargs["grade_points_snapshot"]
            outcome.is_pass_snapshot = kwargs["is_pass_snapshot"]

            created.append(outcome)
            return outcome

        async def flush(self):
            calls.append(
                ("flush",),
            )

        async def supersede_outcome(
            self,
            outcome,
        ):
            calls.append(
                (
                    "supersede",
                    outcome.id,
                )
            )
            outcome.status = AssessmentResultOutcomeStatus.SUPERSEDED
            outcome.is_authoritative = False
            return outcome

        async def make_authoritative(
            self,
            outcome,
        ):
            calls.append(
                (
                    "make_authoritative",
                    outcome.id,
                )
            )
            outcome.status = AssessmentResultOutcomeStatus.AUTHORITATIVE
            outcome.is_authoritative = True
            return outcome

        async def get_by_id(
            self,
            outcome_id,
            *,
            include_relationships=True,
        ):
            calls.append(
                (
                    "get_by_id",
                    outcome_id,
                )
            )

            if by_id is not None:
                return by_id

            if created:
                return created[-1]

            return None

        async def list_for_candidate(
            self,
            candidate_id,
            *,
            school_id=None,
            include_relationships=True,
        ):
            calls.append(
                (
                    "list_for_candidate",
                    candidate_id,
                )
            )
            return history or []

        async def update_draft_metadata(
            self,
            outcome,
            *,
            reason=_UNSET,
            notes=_UNSET,
            effective_at=_UNSET,
        ):
            calls.append(
                (
                    "update_draft_metadata",
                    reason,
                    notes,
                    effective_at,
                )
            )

            if reason is not _UNSET:
                outcome.reason = reason

            if notes is not _UNSET:
                outcome.notes = notes

            if effective_at is not _UNSET:
                outcome.effective_at = effective_at

            return outcome

        async def withdraw_outcome(
            self,
            outcome,
            *,
            withdrawn_at,
            withdrawn_by_id,
            withdrawal_reason,
        ):
            calls.append(
                (
                    "withdraw_outcome",
                    outcome.id,
                    withdrawal_reason,
                )
            )

            outcome.status = AssessmentResultOutcomeStatus.WITHDRAWN
            outcome.is_authoritative = False
            outcome.withdrawn_at = withdrawn_at
            outcome.withdrawn_by_id = withdrawn_by_id
            outcome.withdrawal_reason = withdrawal_reason
            return outcome

        async def delete_draft(
            self,
            outcome,
        ):
            calls.append(
                (
                    "delete_draft",
                    outcome.id,
                )
            )

    monkeypatch.setattr(
        service,
        "AssessmentResultOutcomeRepository",
        FakeRepository,
    )

    return calls, created


# ---------------------------------------------------------------------------
# Create initial outcome
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_initial_outcome_as_draft(
    monkeypatch,
):
    db = FakeDB()
    user = _user()

    calls, created = _patch_repository(
        monkeypatch,
        current=None,
        latest=None,
    )

    async def fake_snapshot(
        db,
        current_user,
        *,
        script_id,
    ):
        return _snapshot(
            script_id=script_id,
        )

    monkeypatch.setattr(
        service,
        "_build_result_snapshot",
        fake_snapshot,
    )

    result = await service.create_assessment_result_outcome(
        db,
        user,
        script_id=300,
        change_type="initial",
    )

    assert db.committed is True
    assert created[0].status == AssessmentResultOutcomeStatus.DRAFT
    assert created[0].is_authoritative is False
    assert result["version"] == 1
    assert result["change_type"] == AssessmentResultChangeType.INITIAL

    assert (
        "get_next_version",
        200,
        True,
    ) in calls


@pytest.mark.asyncio
async def test_create_initial_outcome_can_be_authoritative_immediately(
    monkeypatch,
):
    db = FakeDB()

    calls, created = _patch_repository(
        monkeypatch,
        current=None,
        latest=None,
    )

    async def fake_snapshot(
        db,
        current_user,
        *,
        script_id,
    ):
        return _snapshot(
            script_id=script_id,
        )

    monkeypatch.setattr(
        service,
        "_build_result_snapshot",
        fake_snapshot,
    )

    result = await service.create_assessment_result_outcome(
        db,
        _user(),
        script_id=300,
        change_type="initial",
        make_authoritative=True,
    )

    assert created[0].status == AssessmentResultOutcomeStatus.AUTHORITATIVE
    assert created[0].is_authoritative is True
    assert (
        "make_authoritative",
        99,
    ) in calls
    assert result["is_authoritative"] is True


# ---------------------------------------------------------------------------
# Create superseding outcomes
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_remark_supersedes_current_when_authoritative(
    monkeypatch,
):
    db = FakeDB()

    current = _outcome(
        outcome_id=1,
        script_id=300,
        script_version=1,
    )

    latest = current

    calls, created = _patch_repository(
        monkeypatch,
        current=current,
        latest=latest,
    )

    async def fake_snapshot(
        db,
        current_user,
        *,
        script_id,
    ):
        return _snapshot(
            script_id=300,
            script_version=1,
            mark=Decimal("74"),
        )

    monkeypatch.setattr(
        service,
        "_build_result_snapshot",
        fake_snapshot,
    )

    result = await service.create_assessment_result_outcome(
        db,
        _user(),
        script_id=300,
        change_type="remark",
        reason="Remark increased the mark.",
        make_authoritative=True,
    )

    assert current.status == AssessmentResultOutcomeStatus.SUPERSEDED
    assert current.is_authoritative is False

    assert created[0].supersedes_id == current.id
    assert created[0].status == AssessmentResultOutcomeStatus.AUTHORITATIVE

    assert (
        "supersede",
        1,
    ) in calls

    assert result["mark_awarded_snapshot"] == Decimal("74")


@pytest.mark.asyncio
async def test_create_retake_supersedes_current_when_authoritative(
    monkeypatch,
):
    db = FakeDB()

    current = _outcome(
        outcome_id=1,
        script_id=300,
        script_version=1,
    )

    calls, created = _patch_repository(
        monkeypatch,
        current=current,
        latest=current,
    )

    async def fake_snapshot(
        db,
        current_user,
        *,
        script_id,
    ):
        return _snapshot(
            script_id=301,
            script_version=2,
            mark=Decimal("78"),
        )

    monkeypatch.setattr(
        service,
        "_build_result_snapshot",
        fake_snapshot,
    )

    result = await service.create_assessment_result_outcome(
        db,
        _user(),
        script_id=301,
        change_type="retake",
        reason="Second sitting.",
        make_authoritative=True,
    )

    assert current.status == AssessmentResultOutcomeStatus.SUPERSEDED
    assert created[0].script_id == 301
    assert created[0].script_version_snapshot == 2
    assert result["change_type"] == AssessmentResultChangeType.RETAKE


@pytest.mark.asyncio
async def test_latest_script_does_not_automatically_become_authoritative(
    monkeypatch,
):
    db = FakeDB()

    current = _outcome(
        outcome_id=1,
        script_id=300,
        script_version=1,
    )

    calls, created = _patch_repository(
        monkeypatch,
        current=current,
        latest=current,
    )

    async def fake_snapshot(
        db,
        current_user,
        *,
        script_id,
    ):
        return _snapshot(
            script_id=301,
            script_version=2,
        )

    monkeypatch.setattr(
        service,
        "_build_result_snapshot",
        fake_snapshot,
    )

    result = await service.create_assessment_result_outcome(
        db,
        _user(),
        script_id=301,
        change_type="retake",
        reason="Second sitting.",
        make_authoritative=False,
    )

    assert current.status == AssessmentResultOutcomeStatus.AUTHORITATIVE
    assert current.is_authoritative is True

    assert created[0].status == AssessmentResultOutcomeStatus.DRAFT
    assert created[0].is_authoritative is False

    assert not any(call[0] == "supersede" for call in calls)

    assert result["status"] == AssessmentResultOutcomeStatus.DRAFT


# ---------------------------------------------------------------------------
# Reads
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_outcome_returns_serialised_payload(
    monkeypatch,
):
    outcome = _outcome(
        outcome_id=12,
    )

    async def fake_get(
        db,
        current_user,
        *,
        outcome_id,
    ):
        return outcome

    monkeypatch.setattr(
        service,
        "_get_outcome_or_404",
        fake_get,
    )

    result = await service.get_assessment_result_outcome(
        FakeDB(),
        _user(),
        outcome_id=12,
    )

    assert result["id"] == 12


@pytest.mark.asyncio
async def test_get_authoritative_outcome(
    monkeypatch,
):
    outcome = _outcome()

    _patch_repository(
        monkeypatch,
        current=outcome,
    )

    async def fake_candidate(
        db,
        current_user,
        *,
        candidate_id,
    ):
        return {
            "assessment_id": 100,
            "candidate_id": candidate_id,
        }

    monkeypatch.setattr(
        service,
        "_authorise_candidate_access",
        fake_candidate,
    )

    result = await service.get_authoritative_assessment_result_outcome(
        FakeDB(),
        _user(),
        candidate_id=200,
    )

    assert result["id"] == outcome.id
    assert result["is_authoritative"] is True


@pytest.mark.asyncio
async def test_get_authoritative_outcome_returns_404_when_missing(
    monkeypatch,
):
    _patch_repository(
        monkeypatch,
        current=None,
    )

    async def fake_candidate(
        db,
        current_user,
        *,
        candidate_id,
    ):
        return {
            "assessment_id": 100,
        }

    monkeypatch.setattr(
        service,
        "_authorise_candidate_access",
        fake_candidate,
    )

    with pytest.raises(HTTPException) as exc:
        await service.get_authoritative_assessment_result_outcome(
            FakeDB(),
            _user(),
            candidate_id=200,
        )

    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_list_history_preserves_all_versions(
    monkeypatch,
):
    history = [
        _outcome(
            outcome_id=1,
            version=1,
            status_value=AssessmentResultOutcomeStatus.SUPERSEDED,
            is_authoritative=False,
        ),
        _outcome(
            outcome_id=2,
            version=2,
            change_type=AssessmentResultChangeType.REMARK,
            supersedes_id=1,
        ),
    ]

    _patch_repository(
        monkeypatch,
        history=history,
    )

    async def fake_candidate(
        db,
        current_user,
        *,
        candidate_id,
    ):
        return {
            "assessment_id": 100,
        }

    monkeypatch.setattr(
        service,
        "_authorise_candidate_access",
        fake_candidate,
    )

    result = await service.list_assessment_result_outcome_history(
        FakeDB(),
        _user(),
        candidate_id=200,
    )

    assert len(result) == 2
    assert result[0]["version"] == 1
    assert result[1]["version"] == 2
    assert result[1]["supersedes_id"] == 1


# ---------------------------------------------------------------------------
# Draft metadata updates
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_update_draft_metadata_supports_explicit_clearing(
    monkeypatch,
):
    db = FakeDB()

    outcome = _outcome(
        status_value=AssessmentResultOutcomeStatus.DRAFT,
        is_authoritative=False,
        reason=None,
        notes="Existing notes",
    )
    outcome.change_type = AssessmentResultChangeType.INITIAL

    calls, _ = _patch_repository(
        monkeypatch,
        by_id=outcome,
    )

    async def fake_get(
        db,
        current_user,
        *,
        outcome_id,
    ):
        return outcome

    monkeypatch.setattr(
        service,
        "_get_outcome_or_404",
        fake_get,
    )

    result = await service.update_assessment_result_outcome_draft(
        db,
        _user(),
        outcome_id=outcome.id,
        notes=None,
    )

    update_call = [call for call in calls if call[0] == "update_draft_metadata"][0]

    assert update_call[1] is _UNSET
    assert update_call[2] is None
    assert result["notes"] is None


@pytest.mark.asyncio
async def test_non_draft_outcome_cannot_be_edited(
    monkeypatch,
):
    outcome = _outcome(
        status_value=AssessmentResultOutcomeStatus.AUTHORITATIVE,
    )

    async def fake_get(
        db,
        current_user,
        *,
        outcome_id,
    ):
        return outcome

    monkeypatch.setattr(
        service,
        "_get_outcome_or_404",
        fake_get,
    )

    with pytest.raises(HTTPException) as exc:
        await service.update_assessment_result_outcome_draft(
            FakeDB(),
            _user(),
            outcome_id=outcome.id,
            notes="Changed",
        )

    assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_non_initial_draft_cannot_clear_required_reason(
    monkeypatch,
):
    outcome = _outcome(
        status_value=AssessmentResultOutcomeStatus.DRAFT,
        is_authoritative=False,
        change_type=AssessmentResultChangeType.REMARK,
        reason="Required reason",
    )

    async def fake_get(
        db,
        current_user,
        *,
        outcome_id,
    ):
        return outcome

    monkeypatch.setattr(
        service,
        "_get_outcome_or_404",
        fake_get,
    )

    with pytest.raises(HTTPException) as exc:
        await service.update_assessment_result_outcome_draft(
            FakeDB(),
            _user(),
            outcome_id=outcome.id,
            reason=None,
        )

    assert exc.value.status_code == 422


# ---------------------------------------------------------------------------
# Authorising an existing draft
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_authorise_initial_draft(
    monkeypatch,
):
    db = FakeDB()

    draft = _outcome(
        outcome_id=2,
        version=1,
        status_value=AssessmentResultOutcomeStatus.DRAFT,
        is_authoritative=False,
        change_type=AssessmentResultChangeType.INITIAL,
    )

    calls, _ = _patch_repository(
        monkeypatch,
        current=None,
        latest=draft,
        by_id=draft,
    )

    async def fake_get(
        db,
        current_user,
        *,
        outcome_id,
    ):
        return draft

    monkeypatch.setattr(
        service,
        "_get_outcome_or_404",
        fake_get,
    )

    result = await service.authorise_assessment_result_outcome(
        db,
        _user(),
        outcome_id=draft.id,
    )

    assert (
        "make_authoritative",
        draft.id,
    ) in calls
    assert result["status"] == AssessmentResultOutcomeStatus.AUTHORITATIVE


@pytest.mark.asyncio
async def test_only_latest_draft_can_be_authorised(
    monkeypatch,
):
    older_draft = _outcome(
        outcome_id=2,
        version=2,
        status_value=AssessmentResultOutcomeStatus.DRAFT,
        is_authoritative=False,
        change_type=AssessmentResultChangeType.REMARK,
        reason="Remark",
    )

    newer = _outcome(
        outcome_id=3,
        version=3,
        status_value=AssessmentResultOutcomeStatus.DRAFT,
        is_authoritative=False,
        change_type=AssessmentResultChangeType.REMARK,
        reason="Newer remark",
    )

    _patch_repository(
        monkeypatch,
        latest=newer,
        by_id=older_draft,
    )

    async def fake_get(
        db,
        current_user,
        *,
        outcome_id,
    ):
        return older_draft

    monkeypatch.setattr(
        service,
        "_get_outcome_or_404",
        fake_get,
    )

    with pytest.raises(HTTPException) as exc:
        await service.authorise_assessment_result_outcome(
            FakeDB(),
            _user(),
            outcome_id=older_draft.id,
        )

    assert exc.value.status_code == 409


# ---------------------------------------------------------------------------
# Withdrawal
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_withdraw_authoritative_outcome(
    monkeypatch,
):
    db = FakeDB()

    outcome = _outcome()

    calls, _ = _patch_repository(
        monkeypatch,
        by_id=outcome,
    )

    async def fake_get(
        db,
        current_user,
        *,
        outcome_id,
    ):
        return outcome

    fixed_now = datetime(
        2026,
        8,
        13,
        21,
        0,
        tzinfo=timezone.utc,
    )

    monkeypatch.setattr(
        service,
        "_get_outcome_or_404",
        fake_get,
    )
    monkeypatch.setattr(
        service,
        "_utc_now",
        lambda: fixed_now,
    )

    result = await service.withdraw_assessment_result_outcome(
        db,
        _user(),
        outcome_id=outcome.id,
        withdrawal_reason="Result issued in error.",
    )

    assert result["status"] == AssessmentResultOutcomeStatus.WITHDRAWN
    assert result["is_authoritative"] is False
    assert result["withdrawal_reason"] == "Result issued in error."

    assert any(call[0] == "withdraw_outcome" for call in calls)


@pytest.mark.asyncio
async def test_draft_outcome_cannot_be_withdrawn(
    monkeypatch,
):
    outcome = _outcome(
        status_value=AssessmentResultOutcomeStatus.DRAFT,
        is_authoritative=False,
    )

    async def fake_get(
        db,
        current_user,
        *,
        outcome_id,
    ):
        return outcome

    monkeypatch.setattr(
        service,
        "_get_outcome_or_404",
        fake_get,
    )

    with pytest.raises(HTTPException) as exc:
        await service.withdraw_assessment_result_outcome(
            FakeDB(),
            _user(),
            outcome_id=outcome.id,
            withdrawal_reason="Not needed.",
        )

    assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_withdrawn_outcome_cannot_be_withdrawn_again(
    monkeypatch,
):
    outcome = _outcome(
        status_value=AssessmentResultOutcomeStatus.WITHDRAWN,
        is_authoritative=False,
    )

    async def fake_get(
        db,
        current_user,
        *,
        outcome_id,
    ):
        return outcome

    monkeypatch.setattr(
        service,
        "_get_outcome_or_404",
        fake_get,
    )

    with pytest.raises(HTTPException) as exc:
        await service.withdraw_assessment_result_outcome(
            FakeDB(),
            _user(),
            outcome_id=outcome.id,
            withdrawal_reason="Again.",
        )

    assert exc.value.status_code == 409


# ---------------------------------------------------------------------------
# Draft deletion / immutable history
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_delete_draft(
    monkeypatch,
):
    db = FakeDB()

    outcome = _outcome(
        status_value=AssessmentResultOutcomeStatus.DRAFT,
        is_authoritative=False,
    )

    calls, _ = _patch_repository(
        monkeypatch,
        by_id=outcome,
    )

    async def fake_get(
        db,
        current_user,
        *,
        outcome_id,
    ):
        return outcome

    monkeypatch.setattr(
        service,
        "_get_outcome_or_404",
        fake_get,
    )

    await service.delete_assessment_result_outcome_draft(
        db,
        _user(),
        outcome_id=outcome.id,
    )

    assert db.committed is True
    assert (
        "delete_draft",
        outcome.id,
    ) in calls


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "status_value",
    [
        AssessmentResultOutcomeStatus.AUTHORITATIVE,
        AssessmentResultOutcomeStatus.SUPERSEDED,
        AssessmentResultOutcomeStatus.WITHDRAWN,
    ],
)
async def test_historical_outcomes_cannot_be_deleted(
    monkeypatch,
    status_value,
):
    outcome = _outcome(
        status_value=status_value,
        is_authoritative=(status_value == AssessmentResultOutcomeStatus.AUTHORITATIVE),
    )

    async def fake_get(
        db,
        current_user,
        *,
        outcome_id,
    ):
        return outcome

    monkeypatch.setattr(
        service,
        "_get_outcome_or_404",
        fake_get,
    )

    with pytest.raises(HTTPException) as exc:
        await service.delete_assessment_result_outcome_draft(
            FakeDB(),
            _user(),
            outcome_id=outcome.id,
        )

    assert exc.value.status_code == 409


# ---------------------------------------------------------------------------
# Access consistency
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_authorise_outcome_access_rejects_candidate_mismatch(
    monkeypatch,
):
    outcome = _outcome(
        candidate_id=200,
    )

    async def fake_result(**kwargs):
        return {
            "candidate_id": 999,
            "assessment_id": 100,
        }

    monkeypatch.setattr(
        service,
        "get_script_result",
        fake_result,
    )

    with pytest.raises(HTTPException) as exc:
        await service._authorise_outcome_access(
            FakeDB(),
            _user(),
            outcome,
        )

    assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_authorise_outcome_access_rejects_assessment_mismatch(
    monkeypatch,
):
    outcome = _outcome(
        assessment_id=100,
    )

    async def fake_result(**kwargs):
        return {
            "candidate_id": 200,
            "assessment_id": 999,
        }

    monkeypatch.setattr(
        service,
        "get_script_result",
        fake_result,
    )

    with pytest.raises(HTTPException) as exc:
        await service._authorise_outcome_access(
            FakeDB(),
            _user(),
            outcome,
        )

    assert exc.value.status_code == 409


# ---------------------------------------------------------------------------
# Transaction conflict handling
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_commit_integrity_error_becomes_conflict():
    class ConflictDB(FakeDB):
        async def commit(self):
            raise IntegrityError(
                "statement",
                {},
                Exception("duplicate"),
            )

    db = ConflictDB()

    with pytest.raises(HTTPException) as exc:
        await service._commit_outcome_change(
            db,
            conflict_detail="Concurrent result outcome change.",
        )

    assert exc.value.status_code == 409
    assert exc.value.detail == "Concurrent result outcome change."
    assert db.rolled_back is True


@pytest.mark.asyncio
async def test_create_outcome_rolls_back_concurrent_conflict(
    monkeypatch,
):
    class ConflictDB(FakeDB):
        async def commit(self):
            raise IntegrityError(
                "statement",
                {},
                Exception("duplicate"),
            )

    db = ConflictDB()

    _patch_repository(
        monkeypatch,
        current=None,
        latest=None,
    )

    async def fake_snapshot(
        db,
        current_user,
        *,
        script_id,
    ):
        return _snapshot(
            script_id=script_id,
        )

    monkeypatch.setattr(
        service,
        "_build_result_snapshot",
        fake_snapshot,
    )

    with pytest.raises(HTTPException) as exc:
        await service.create_assessment_result_outcome(
            db,
            _user(),
            script_id=300,
            change_type="initial",
            make_authoritative=True,
        )

    assert exc.value.status_code == 409
    assert db.rolled_back is True
