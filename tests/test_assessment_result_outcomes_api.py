from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

import app.api.v1.endpoints.assessment_result_outcomes as api
from app.models.assessment_result_outcome import (
    AssessmentResultChangeType,
    AssessmentResultOutcomeStatus,
)
from app.schemas.assessment_result_outcome import (
    AssessmentResultOutcomeCreate,
    AssessmentResultOutcomeUpdate,
    AssessmentResultOutcomeWithdraw,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _now() -> datetime:
    return datetime(
        2026,
        8,
        13,
        20,
        0,
        tzinfo=timezone.utc,
    )


def _user():
    class User:
        id = 10
        school_id = 1
        full_name = "Test Teacher"

    return User()


def _outcome_payload(
    *,
    outcome_id: int = 1,
    candidate_id: int = 200,
    assessment_id: int = 100,
    script_id: int = 300,
    version: int = 1,
    status_value: str = "authoritative",
    change_type: str = "initial",
    supersedes_id: int | None = None,
    is_authoritative: bool = True,
    mark: Decimal = Decimal("72"),
    maximum: Decimal = Decimal("80"),
    percentage: Decimal | None = Decimal("90"),
    reason: str | None = None,
    notes: str | None = None,
):
    return {
        "id": outcome_id,
        "school_id": 1,
        "assessment_id": assessment_id,
        "candidate_id": candidate_id,
        "script_id": script_id,
        "version": version,
        "status": status_value,
        "change_type": change_type,
        "supersedes_id": supersedes_id,
        "is_authoritative": is_authoritative,
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
        "script_version_snapshot": 1,
        "reason": reason,
        "notes": notes,
        "effective_at": _now(),
        "recorded_by_id": 10,
        "recorded_by_name": "Test Teacher",
        "recorded_at": _now(),
        "withdrawn_at": None,
        "withdrawn_by_id": None,
        "withdrawn_by_name": None,
        "withdrawal_reason": None,
    }


# ---------------------------------------------------------------------------
# Schema validation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "change_type",
    [
        "initial",
        "retake",
        "remark",
        "correction",
        "moderation",
        "administrative",
    ],
)
def test_create_schema_accepts_all_change_types(
    change_type,
):
    payload = AssessmentResultOutcomeCreate(
        script_id=1,
        change_type=change_type,
    )

    assert payload.change_type == change_type


def test_create_schema_defaults_to_draft_workflow():
    payload = AssessmentResultOutcomeCreate(
        script_id=1,
        change_type="initial",
    )

    assert payload.make_authoritative is False


def test_create_schema_accepts_immediate_authorisation():
    payload = AssessmentResultOutcomeCreate(
        script_id=1,
        change_type="initial",
        make_authoritative=True,
    )

    assert payload.make_authoritative is True


@pytest.mark.parametrize(
    "script_id",
    [
        0,
        -1,
    ],
)
def test_create_schema_rejects_non_positive_script_id(
    script_id,
):
    with pytest.raises(ValidationError):
        AssessmentResultOutcomeCreate(
            script_id=script_id,
            change_type="initial",
        )


def test_create_schema_rejects_unknown_change_type():
    with pytest.raises(ValidationError):
        AssessmentResultOutcomeCreate(
            script_id=1,
            change_type="unexpected",
        )


def test_withdraw_schema_rejects_empty_reason():
    with pytest.raises(ValidationError):
        AssessmentResultOutcomeWithdraw(
            withdrawal_reason="",
        )


def test_update_schema_preserves_omitted_fields():
    payload = AssessmentResultOutcomeUpdate()

    assert (
        payload.model_dump(
            exclude_unset=True,
        )
        == {}
    )


def test_update_schema_preserves_explicit_null():
    payload = AssessmentResultOutcomeUpdate(
        notes=None,
    )

    assert payload.model_dump(
        exclude_unset=True,
    ) == {
        "notes": None,
    }


# ---------------------------------------------------------------------------
# POST create
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_result_outcome(
    monkeypatch,
):
    captured = {}

    async def fake_create(
        db,
        current_user,
        **kwargs,
    ):
        captured.update(
            kwargs,
        )

        return _outcome_payload(
            status_value="draft",
            is_authoritative=False,
        )

    monkeypatch.setattr(
        api,
        "create_assessment_result_outcome",
        fake_create,
    )

    payload = AssessmentResultOutcomeCreate(
        script_id=300,
        change_type="initial",
    )

    result = await api.create_result_outcome(
        payload=payload,
        db=object(),
        current_user=_user(),
    )

    assert result.id == 1
    assert result.script_id == 300
    assert result.status == "draft"
    assert result.is_authoritative is False

    assert captured["script_id"] == 300
    assert captured["change_type"] == "initial"
    assert captured["make_authoritative"] is False


@pytest.mark.asyncio
async def test_create_result_outcome_passes_reason_notes_and_effective_at(
    monkeypatch,
):
    captured = {}

    async def fake_create(
        db,
        current_user,
        **kwargs,
    ):
        captured.update(
            kwargs,
        )

        return _outcome_payload(
            status_value="draft",
            change_type="remark",
            is_authoritative=False,
            reason="Remark requested.",
            notes="Clerical review complete.",
        )

    monkeypatch.setattr(
        api,
        "create_assessment_result_outcome",
        fake_create,
    )

    effective_at = _now()

    payload = AssessmentResultOutcomeCreate(
        script_id=300,
        change_type="remark",
        reason="Remark requested.",
        notes="Clerical review complete.",
        effective_at=effective_at,
    )

    await api.create_result_outcome(
        payload=payload,
        db=object(),
        current_user=_user(),
    )

    assert captured["reason"] == "Remark requested."
    assert captured["notes"] == "Clerical review complete."
    assert captured["effective_at"] == effective_at


@pytest.mark.asyncio
async def test_create_result_outcome_supports_immediate_authorisation(
    monkeypatch,
):
    captured = {}

    async def fake_create(
        db,
        current_user,
        **kwargs,
    ):
        captured.update(
            kwargs,
        )

        return _outcome_payload()

    monkeypatch.setattr(
        api,
        "create_assessment_result_outcome",
        fake_create,
    )

    payload = AssessmentResultOutcomeCreate(
        script_id=300,
        change_type="initial",
        make_authoritative=True,
    )

    result = await api.create_result_outcome(
        payload=payload,
        db=object(),
        current_user=_user(),
    )

    assert captured["make_authoritative"] is True
    assert result.is_authoritative is True
    assert result.status == "authoritative"


@pytest.mark.asyncio
async def test_create_result_outcome_propagates_service_error(
    monkeypatch,
):
    async def fake_create(
        db,
        current_user,
        **kwargs,
    ):
        raise HTTPException(
            status_code=409,
            detail="Script is not fully finalised.",
        )

    monkeypatch.setattr(
        api,
        "create_assessment_result_outcome",
        fake_create,
    )

    payload = AssessmentResultOutcomeCreate(
        script_id=300,
        change_type="initial",
    )

    with pytest.raises(HTTPException) as exc:
        await api.create_result_outcome(
            payload=payload,
            db=object(),
            current_user=_user(),
        )

    assert exc.value.status_code == 409
    assert exc.value.detail == "Script is not fully finalised."


# ---------------------------------------------------------------------------
# GET single outcome
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_result_outcome(
    monkeypatch,
):
    captured = {}

    async def fake_get(
        db,
        current_user,
        *,
        outcome_id,
    ):
        captured["outcome_id"] = outcome_id
        return _outcome_payload(
            outcome_id=17,
        )

    monkeypatch.setattr(
        api,
        "get_assessment_result_outcome",
        fake_get,
    )

    result = await api.get_result_outcome(
        outcome_id=17,
        db=object(),
        current_user=_user(),
    )

    assert captured["outcome_id"] == 17
    assert result.id == 17


@pytest.mark.asyncio
async def test_get_result_outcome_propagates_not_found(
    monkeypatch,
):
    async def fake_get(
        db,
        current_user,
        *,
        outcome_id,
    ):
        raise HTTPException(
            status_code=404,
            detail="Assessment result outcome not found.",
        )

    monkeypatch.setattr(
        api,
        "get_assessment_result_outcome",
        fake_get,
    )

    with pytest.raises(HTTPException) as exc:
        await api.get_result_outcome(
            outcome_id=999,
            db=object(),
            current_user=_user(),
        )

    assert exc.value.status_code == 404


# ---------------------------------------------------------------------------
# GET current authoritative outcome
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_authoritative_result_outcome(
    monkeypatch,
):
    captured = {}

    async def fake_get(
        db,
        current_user,
        *,
        candidate_id,
    ):
        captured["candidate_id"] = candidate_id

        return _outcome_payload(
            candidate_id=candidate_id,
        )

    monkeypatch.setattr(
        api,
        "get_authoritative_assessment_result_outcome",
        fake_get,
    )

    result = await api.get_authoritative_result_outcome(
        candidate_id=200,
        db=object(),
        current_user=_user(),
    )

    assert captured["candidate_id"] == 200
    assert result.candidate_id == 200
    assert result.is_authoritative is True


@pytest.mark.asyncio
async def test_get_authoritative_result_outcome_propagates_missing_result(
    monkeypatch,
):
    async def fake_get(
        db,
        current_user,
        *,
        candidate_id,
    ):
        raise HTTPException(
            status_code=404,
            detail=(
                "This assessment candidate does not have an "
                "authoritative result outcome."
            ),
        )

    monkeypatch.setattr(
        api,
        "get_authoritative_assessment_result_outcome",
        fake_get,
    )

    with pytest.raises(HTTPException) as exc:
        await api.get_authoritative_result_outcome(
            candidate_id=200,
            db=object(),
            current_user=_user(),
        )

    assert exc.value.status_code == 404


# ---------------------------------------------------------------------------
# GET candidate history
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_result_outcome_history(
    monkeypatch,
):
    async def fake_history(
        db,
        current_user,
        *,
        candidate_id,
    ):
        return [
            _outcome_payload(
                outcome_id=1,
                candidate_id=candidate_id,
                version=1,
                status_value="superseded",
                is_authoritative=False,
            ),
            _outcome_payload(
                outcome_id=2,
                candidate_id=candidate_id,
                version=2,
                status_value="authoritative",
                change_type="remark",
                supersedes_id=1,
                is_authoritative=True,
            ),
        ]

    monkeypatch.setattr(
        api,
        "list_assessment_result_outcome_history",
        fake_history,
    )

    result = await api.get_result_outcome_history(
        candidate_id=200,
        db=object(),
        current_user=_user(),
    )

    assert result.candidate_id == 200
    assert result.outcome_count == 2
    assert result.authoritative_outcome_id == 2
    assert len(result.outcomes) == 2
    assert result.outcomes[0].status == "superseded"
    assert result.outcomes[1].status == "authoritative"


@pytest.mark.asyncio
async def test_history_without_authoritative_outcome_returns_none(
    monkeypatch,
):
    async def fake_history(
        db,
        current_user,
        *,
        candidate_id,
    ):
        return [
            _outcome_payload(
                candidate_id=candidate_id,
                status_value="draft",
                is_authoritative=False,
            ),
        ]

    monkeypatch.setattr(
        api,
        "list_assessment_result_outcome_history",
        fake_history,
    )

    result = await api.get_result_outcome_history(
        candidate_id=200,
        db=object(),
        current_user=_user(),
    )

    assert result.outcome_count == 1
    assert result.authoritative_outcome_id is None


@pytest.mark.asyncio
async def test_empty_history(
    monkeypatch,
):
    async def fake_history(
        db,
        current_user,
        *,
        candidate_id,
    ):
        return []

    monkeypatch.setattr(
        api,
        "list_assessment_result_outcome_history",
        fake_history,
    )

    result = await api.get_result_outcome_history(
        candidate_id=200,
        db=object(),
        current_user=_user(),
    )

    assert result.candidate_id == 200
    assert result.outcome_count == 0
    assert result.authoritative_outcome_id is None
    assert result.outcomes == []


# ---------------------------------------------------------------------------
# PATCH draft metadata
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_patch_result_outcome_draft(
    monkeypatch,
):
    captured = {}

    async def fake_update(
        db,
        current_user,
        *,
        outcome_id,
        **kwargs,
    ):
        captured["outcome_id"] = outcome_id
        captured.update(
            kwargs,
        )

        return _outcome_payload(
            outcome_id=outcome_id,
            status_value="draft",
            is_authoritative=False,
            notes=kwargs.get(
                "notes",
            ),
        )

    monkeypatch.setattr(
        api,
        "update_assessment_result_outcome_draft",
        fake_update,
    )

    payload = AssessmentResultOutcomeUpdate(
        notes="Updated draft note.",
    )

    result = await api.update_result_outcome_draft(
        outcome_id=5,
        payload=payload,
        db=object(),
        current_user=_user(),
    )

    assert captured == {
        "outcome_id": 5,
        "notes": "Updated draft note.",
    }

    assert result.notes == "Updated draft note."


@pytest.mark.asyncio
async def test_patch_omitted_fields_are_not_forwarded(
    monkeypatch,
):
    captured = {}

    async def fake_update(
        db,
        current_user,
        *,
        outcome_id,
        **kwargs,
    ):
        captured.update(
            kwargs,
        )

        return _outcome_payload(
            status_value="draft",
            is_authoritative=False,
        )

    monkeypatch.setattr(
        api,
        "update_assessment_result_outcome_draft",
        fake_update,
    )

    payload = AssessmentResultOutcomeUpdate()

    await api.update_result_outcome_draft(
        outcome_id=5,
        payload=payload,
        db=object(),
        current_user=_user(),
    )

    assert captured == {}


@pytest.mark.asyncio
async def test_patch_explicit_null_is_forwarded(
    monkeypatch,
):
    captured = {}

    async def fake_update(
        db,
        current_user,
        *,
        outcome_id,
        **kwargs,
    ):
        captured.update(
            kwargs,
        )

        return _outcome_payload(
            status_value="draft",
            is_authoritative=False,
            notes=None,
        )

    monkeypatch.setattr(
        api,
        "update_assessment_result_outcome_draft",
        fake_update,
    )

    payload = AssessmentResultOutcomeUpdate(
        notes=None,
    )

    await api.update_result_outcome_draft(
        outcome_id=5,
        payload=payload,
        db=object(),
        current_user=_user(),
    )

    assert captured == {
        "notes": None,
    }


@pytest.mark.asyncio
async def test_patch_propagates_non_draft_conflict(
    monkeypatch,
):
    async def fake_update(
        db,
        current_user,
        *,
        outcome_id,
        **kwargs,
    ):
        raise HTTPException(
            status_code=409,
            detail="Only draft result outcomes may be edited.",
        )

    monkeypatch.setattr(
        api,
        "update_assessment_result_outcome_draft",
        fake_update,
    )

    with pytest.raises(HTTPException) as exc:
        await api.update_result_outcome_draft(
            outcome_id=5,
            payload=AssessmentResultOutcomeUpdate(
                notes="No",
            ),
            db=object(),
            current_user=_user(),
        )

    assert exc.value.status_code == 409


# ---------------------------------------------------------------------------
# POST authorise
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_authorise_result_outcome(
    monkeypatch,
):
    captured = {}

    async def fake_authorise(
        db,
        current_user,
        *,
        outcome_id,
    ):
        captured["outcome_id"] = outcome_id

        return _outcome_payload(
            outcome_id=outcome_id,
        )

    monkeypatch.setattr(
        api,
        "authorise_assessment_result_outcome",
        fake_authorise,
    )

    result = await api.authorise_result_outcome(
        outcome_id=8,
        db=object(),
        current_user=_user(),
    )

    assert captured["outcome_id"] == 8
    assert result.id == 8
    assert result.status == "authoritative"


@pytest.mark.asyncio
async def test_authorise_result_outcome_propagates_conflict(
    monkeypatch,
):
    async def fake_authorise(
        db,
        current_user,
        *,
        outcome_id,
    ):
        raise HTTPException(
            status_code=409,
            detail=(
                "Only the candidate's latest result outcome "
                "may become authoritative."
            ),
        )

    monkeypatch.setattr(
        api,
        "authorise_assessment_result_outcome",
        fake_authorise,
    )

    with pytest.raises(HTTPException) as exc:
        await api.authorise_result_outcome(
            outcome_id=8,
            db=object(),
            current_user=_user(),
        )

    assert exc.value.status_code == 409


# ---------------------------------------------------------------------------
# POST withdraw
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_withdraw_result_outcome(
    monkeypatch,
):
    captured = {}

    async def fake_withdraw(
        db,
        current_user,
        *,
        outcome_id,
        withdrawal_reason,
    ):
        captured["outcome_id"] = outcome_id
        captured["withdrawal_reason"] = withdrawal_reason

        result = _outcome_payload(
            outcome_id=outcome_id,
            status_value="withdrawn",
            is_authoritative=False,
        )

        result["withdrawn_at"] = _now()
        result["withdrawn_by_id"] = 10
        result["withdrawn_by_name"] = "Test Teacher"
        result["withdrawal_reason"] = withdrawal_reason

        return result

    monkeypatch.setattr(
        api,
        "withdraw_assessment_result_outcome",
        fake_withdraw,
    )

    payload = AssessmentResultOutcomeWithdraw(
        withdrawal_reason="Result entered in error.",
    )

    result = await api.withdraw_result_outcome(
        outcome_id=4,
        payload=payload,
        db=object(),
        current_user=_user(),
    )

    assert captured == {
        "outcome_id": 4,
        "withdrawal_reason": "Result entered in error.",
    }

    assert result.status == "withdrawn"
    assert result.is_authoritative is False
    assert result.withdrawal_reason == "Result entered in error."


@pytest.mark.asyncio
async def test_withdraw_result_outcome_propagates_conflict(
    monkeypatch,
):
    async def fake_withdraw(
        db,
        current_user,
        *,
        outcome_id,
        withdrawal_reason,
    ):
        raise HTTPException(
            status_code=409,
            detail="This result outcome has already been withdrawn.",
        )

    monkeypatch.setattr(
        api,
        "withdraw_assessment_result_outcome",
        fake_withdraw,
    )

    with pytest.raises(HTTPException) as exc:
        await api.withdraw_result_outcome(
            outcome_id=4,
            payload=AssessmentResultOutcomeWithdraw(
                withdrawal_reason="Again",
            ),
            db=object(),
            current_user=_user(),
        )

    assert exc.value.status_code == 409


# ---------------------------------------------------------------------------
# DELETE draft
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_delete_result_outcome_draft(
    monkeypatch,
):
    captured = {}

    async def fake_delete(
        db,
        current_user,
        *,
        outcome_id,
    ):
        captured["outcome_id"] = outcome_id

    monkeypatch.setattr(
        api,
        "delete_assessment_result_outcome_draft",
        fake_delete,
    )

    response = await api.delete_result_outcome_draft(
        outcome_id=9,
        db=object(),
        current_user=_user(),
    )

    assert captured["outcome_id"] == 9
    assert response.status_code == 204


@pytest.mark.asyncio
async def test_delete_result_outcome_draft_propagates_historical_conflict(
    monkeypatch,
):
    async def fake_delete(
        db,
        current_user,
        *,
        outcome_id,
    ):
        raise HTTPException(
            status_code=409,
            detail=(
                "Historical result outcomes cannot be deleted. "
                "Only drafts may be removed."
            ),
        )

    monkeypatch.setattr(
        api,
        "delete_assessment_result_outcome_draft",
        fake_delete,
    )

    with pytest.raises(HTTPException) as exc:
        await api.delete_result_outcome_draft(
            outcome_id=9,
            db=object(),
            current_user=_user(),
        )

    assert exc.value.status_code == 409


# ---------------------------------------------------------------------------
# Output contract
# ---------------------------------------------------------------------------


def test_output_accepts_enum_values_from_service():
    payload = _outcome_payload()

    payload["status"] = AssessmentResultOutcomeStatus.AUTHORITATIVE
    payload["change_type"] = AssessmentResultChangeType.INITIAL

    result = api.AssessmentResultOutcomeOut.model_validate(
        payload,
    )

    assert result.status == "authoritative"
    assert result.change_type == "initial"


def test_output_preserves_decimal_snapshot_values():
    payload = _outcome_payload(
        mark=Decimal("71.50"),
        maximum=Decimal("80.00"),
        percentage=Decimal("89.38"),
    )

    result = api.AssessmentResultOutcomeOut.model_validate(
        payload,
    )

    assert result.mark_awarded_snapshot == Decimal("71.50")
    assert result.maximum_mark_snapshot == Decimal("80.00")
    assert result.percentage_snapshot == Decimal("89.38")


def test_output_supports_marks_only_result_without_grade():
    payload = _outcome_payload()

    payload.update(
        {
            "grading_scheme_id_snapshot": None,
            "grading_scheme_name_snapshot": None,
            "grading_basis_snapshot": None,
            "grade_boundary_id_snapshot": None,
            "grade_label_snapshot": None,
            "grade_points_snapshot": None,
            "is_pass_snapshot": None,
        }
    )

    result = api.AssessmentResultOutcomeOut.model_validate(
        payload,
    )

    assert result.grade_label_snapshot is None
    assert result.grade_points_snapshot is None
    assert result.is_pass_snapshot is None


# ---------------------------------------------------------------------------
# Router contract
# ---------------------------------------------------------------------------


def test_router_contains_expected_result_outcome_routes():
    route_contract = {
        (
            route.path,
            frozenset(
                route.methods or [],
            ),
        )
        for route in api.router.routes
    }

    expected = {
        (
            "",
            frozenset(
                {"POST"},
            ),
        ),
        (
            "/{outcome_id}",
            frozenset(
                {"GET"},
            ),
        ),
        (
            "/candidates/{candidate_id}/authoritative",
            frozenset(
                {"GET"},
            ),
        ),
        (
            "/candidates/{candidate_id}/history",
            frozenset(
                {"GET"},
            ),
        ),
        (
            "/{outcome_id}",
            frozenset(
                {"PATCH"},
            ),
        ),
        (
            "/{outcome_id}/authorise",
            frozenset(
                {"POST"},
            ),
        ),
        (
            "/{outcome_id}/withdraw",
            frozenset(
                {"POST"},
            ),
        ),
        (
            "/{outcome_id}",
            frozenset(
                {"DELETE"},
            ),
        ),
    }

    assert expected.issubset(
        route_contract,
    )
