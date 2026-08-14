from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

import app.services.published_assessment_results_service as service

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _user(
    *,
    user_id: int,
    **attributes,
):
    return SimpleNamespace(
        id=user_id,
        **attributes,
    )


def _publication(
    *,
    assessment_id: int = 100,
    visible_to_students: bool = True,
    visible_to_parents: bool = True,
    include_mark: bool = True,
    include_percentage: bool = True,
    include_grade: bool = True,
    include_question_breakdown: bool = False,
    release_message: str | None = "Results released.",
):
    return SimpleNamespace(
        assessment_id=assessment_id,
        visible_to_students=visible_to_students,
        visible_to_parents=visible_to_parents,
        include_mark=include_mark,
        include_percentage=include_percentage,
        include_grade=include_grade,
        include_question_breakdown=include_question_breakdown,
        release_message=release_message,
        published_at=datetime(
            2026,
            8,
            12,
            12,
            0,
            tzinfo=timezone.utc,
        ),
    )


def _candidate_result(
    *,
    candidate_id: int = 200,
    assessment_id: int = 100,
    student_id: int = 300,
    latest_script_id: int = 999,
    latest_script_version: int = 3,
    latest_mark: Decimal = Decimal("9.00"),
    latest_percentage: Decimal = Decimal("90.00"),
):
    """
    Return a candidate result containing a deliberately newer script.

    Published-result tests must prove that this convenience latest-script view
    does not override the authoritative historical outcome.
    """

    return {
        "assessment_id": assessment_id,
        "candidate_id": candidate_id,
        "student_id": student_id,
        "candidate_number": "PUB-001",
        "latest_script_result": {
            "script_id": latest_script_id,
            "script_version": latest_script_version,
            "finalised_mark_awarded": latest_mark,
            "finalised_percentage": latest_percentage,
            "questions": [
                {
                    "question_id": 99,
                    "question_number": "99",
                    "maximum_mark": Decimal("10.00"),
                    "mark_awarded": latest_mark,
                },
            ],
        },
    }


def _authoritative_outcome(
    *,
    outcome_id: int = 500,
    candidate_id: int = 200,
    assessment_id: int = 100,
    script_id: int = 400,
    script_version: int = 1,
    mark_awarded: Decimal = Decimal("6.00"),
    maximum_mark: Decimal = Decimal("8.00"),
    percentage: Decimal = Decimal("75.00"),
    grade: str | None = "8",
    grade_points: Decimal | None = Decimal("8.00"),
    is_pass: bool | None = True,
):
    return {
        "id": outcome_id,
        "school_id": 10,
        "assessment_id": assessment_id,
        "candidate_id": candidate_id,
        "script_id": script_id,
        "version": 1,
        "status": "authoritative",
        "change_type": "initial",
        "supersedes_id": None,
        "is_authoritative": True,
        "mark_awarded_snapshot": mark_awarded,
        "maximum_mark_snapshot": maximum_mark,
        "percentage_snapshot": percentage,
        "grading_scheme_id_snapshot": 20,
        "grading_scheme_name_snapshot": "GCSE",
        "grading_basis_snapshot": "percentage",
        "grade_boundary_id_snapshot": 30,
        "grade_label_snapshot": grade,
        "grade_points_snapshot": grade_points,
        "is_pass_snapshot": is_pass,
        "script_version_snapshot": script_version,
        "reason": None,
        "notes": None,
        "effective_at": datetime(
            2026,
            8,
            12,
            11,
            0,
            tzinfo=timezone.utc,
        ),
        "recorded_by_id": 40,
        "recorded_at": datetime(
            2026,
            8,
            12,
            11,
            0,
            tzinfo=timezone.utc,
        ),
        "withdrawn_at": None,
        "withdrawn_by_id": None,
        "withdrawal_reason": None,
    }


def _authoritative_script_result(
    *,
    candidate_id: int = 200,
    assessment_id: int = 100,
    script_id: int = 400,
    script_version: int = 1,
    mark_awarded: Decimal = Decimal("6.00"),
    percentage: Decimal = Decimal("75.00"),
):
    return {
        "assessment_id": assessment_id,
        "candidate_id": candidate_id,
        "student_id": 300,
        "script_id": script_id,
        "script_version": script_version,
        "script_status": "finalised",
        "maximum_mark": Decimal("8.00"),
        "mark_awarded": mark_awarded,
        "completed_mark_awarded": mark_awarded,
        "finalised_mark_awarded": mark_awarded,
        "percentage": percentage,
        "completed_percentage": percentage,
        "finalised_percentage": percentage,
        "questions": [
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
        ],
    }


async def _patch_candidate_result(
    monkeypatch,
    candidate_result,
):
    async def fake_get_candidate_result(
        *,
        db,
        current_user,
        candidate_id,
    ):
        return candidate_result

    monkeypatch.setattr(
        service,
        "get_candidate_result",
        fake_get_candidate_result,
    )


async def _patch_publication(
    monkeypatch,
    publication,
):
    async def fake_get_publication(
        db,
        *,
        assessment_id,
    ):
        return publication

    monkeypatch.setattr(
        service,
        "get_published_result_visibility",
        fake_get_publication,
    )


async def _patch_authoritative_outcome(
    monkeypatch,
    outcome,
):
    async def fake_get_authoritative_outcome(
        db,
        current_user,
        *,
        candidate_id,
    ):
        if isinstance(
            outcome,
            Exception,
        ):
            raise outcome

        return outcome

    monkeypatch.setattr(
        service,
        "get_authoritative_assessment_result_outcome",
        fake_get_authoritative_outcome,
    )


async def _patch_script_result(
    monkeypatch,
    script_result,
):
    async def fake_get_script_result(
        *,
        db,
        current_user,
        script_id,
    ):
        if isinstance(
            script_result,
            Exception,
        ):
            raise script_result

        return script_result

    monkeypatch.setattr(
        service,
        "get_script_result",
        fake_get_script_result,
    )


async def _prepare_student_result(
    monkeypatch,
    *,
    candidate_result=None,
    publication=None,
    outcome=None,
):
    candidate_result = candidate_result or _candidate_result()
    publication = publication or _publication()
    outcome = outcome or _authoritative_outcome()

    await _patch_candidate_result(
        monkeypatch,
        candidate_result,
    )

    await _patch_publication(
        monkeypatch,
        publication,
    )

    await _patch_authoritative_outcome(
        monkeypatch,
        outcome,
    )

    return (
        candidate_result,
        publication,
        outcome,
    )


# ---------------------------------------------------------------------------
# Publication hiding
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_student_result_is_hidden_when_not_published(
    db_session: AsyncSession,
    monkeypatch,
):
    candidate_result = _candidate_result()

    await _patch_candidate_result(
        monkeypatch,
        candidate_result,
    )

    await _patch_publication(
        monkeypatch,
        None,
    )

    student = _user(
        user_id=candidate_result["student_id"],
    )

    with pytest.raises(
        HTTPException,
    ) as exc:
        await service.get_student_published_assessment_result(
            db_session,
            student,
            candidate_id=candidate_result["candidate_id"],
        )

    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_parent_result_is_hidden_when_not_published(
    db_session: AsyncSession,
    monkeypatch,
):
    candidate_result = _candidate_result()

    await _patch_candidate_result(
        monkeypatch,
        candidate_result,
    )

    await _patch_publication(
        monkeypatch,
        None,
    )

    parent = _user(
        user_id=500,
        students=[
            SimpleNamespace(
                id=candidate_result["student_id"],
            ),
        ],
    )

    with pytest.raises(
        HTTPException,
    ) as exc:
        await service.get_parent_published_assessment_result(
            db_session,
            parent,
            candidate_id=candidate_result["candidate_id"],
        )

    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_published_result_is_hidden_without_authoritative_outcome(
    db_session: AsyncSession,
    monkeypatch,
):
    candidate_result = _candidate_result()

    await _patch_candidate_result(
        monkeypatch,
        candidate_result,
    )

    await _patch_publication(
        monkeypatch,
        _publication(),
    )

    await _patch_authoritative_outcome(
        monkeypatch,
        HTTPException(
            status_code=404,
            detail="No authoritative result.",
        ),
    )

    student = _user(
        user_id=candidate_result["student_id"],
    )

    with pytest.raises(
        HTTPException,
    ) as exc:
        await service.get_student_published_assessment_result(
            db_session,
            student,
            candidate_id=candidate_result["candidate_id"],
        )

    assert exc.value.status_code == 404
    assert exc.value.detail == "Published assessment result not found."


@pytest.mark.asyncio
async def test_authoritative_history_conflict_is_hidden_from_public_user(
    db_session: AsyncSession,
    monkeypatch,
):
    candidate_result = _candidate_result()

    await _patch_candidate_result(
        monkeypatch,
        candidate_result,
    )

    await _patch_publication(
        monkeypatch,
        _publication(),
    )

    await _patch_authoritative_outcome(
        monkeypatch,
        HTTPException(
            status_code=409,
            detail="Result history inconsistent.",
        ),
    )

    student = _user(
        user_id=candidate_result["student_id"],
    )

    with pytest.raises(
        HTTPException,
    ) as exc:
        await service.get_student_published_assessment_result(
            db_session,
            student,
            candidate_id=candidate_result["candidate_id"],
        )

    assert exc.value.status_code == 404
    assert exc.value.detail == "Published assessment result not found."


# ---------------------------------------------------------------------------
# Student ownership
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_student_can_view_own_authoritative_published_result(
    db_session: AsyncSession,
    monkeypatch,
):
    (
        candidate_result,
        _,
        outcome,
    ) = await _prepare_student_result(
        monkeypatch,
    )

    student = _user(
        user_id=candidate_result["student_id"],
    )

    result = await service.get_student_published_assessment_result(
        db_session,
        student,
        candidate_id=candidate_result["candidate_id"],
    )

    assert result["student_id"] == student.id

    assert result["script_id"] == outcome["script_id"]
    assert result["script_version"] == outcome["script_version_snapshot"]

    assert result["mark_awarded"] == Decimal("6.00")
    assert result["percentage"] == Decimal("75.00")

    assert result["grade"] == "8"
    assert result["grade_points"] == Decimal("8.00")
    assert result["is_pass"] is True


@pytest.mark.asyncio
async def test_student_cannot_view_another_students_result(
    db_session: AsyncSession,
    monkeypatch,
):
    candidate_result = _candidate_result(
        student_id=300,
    )

    await _patch_candidate_result(
        monkeypatch,
        candidate_result,
    )

    student = _user(
        user_id=999,
    )

    with pytest.raises(
        HTTPException,
    ) as exc:
        await service.get_student_published_assessment_result(
            db_session,
            student,
            candidate_id=candidate_result["candidate_id"],
        )

    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_student_result_hidden_when_student_visibility_disabled(
    db_session: AsyncSession,
    monkeypatch,
):
    candidate_result = _candidate_result()

    await _patch_candidate_result(
        monkeypatch,
        candidate_result,
    )

    await _patch_publication(
        monkeypatch,
        _publication(
            visible_to_students=False,
        ),
    )

    student = _user(
        user_id=candidate_result["student_id"],
    )

    with pytest.raises(
        HTTPException,
    ) as exc:
        await service.get_student_published_assessment_result(
            db_session,
            student,
            candidate_id=candidate_result["candidate_id"],
        )

    assert exc.value.status_code == 404


# ---------------------------------------------------------------------------
# Parent-child authorisation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_parent_can_view_linked_child_authoritative_result(
    db_session: AsyncSession,
    monkeypatch,
):
    candidate_result = _candidate_result()

    await _patch_candidate_result(
        monkeypatch,
        candidate_result,
    )

    await _patch_publication(
        monkeypatch,
        _publication(),
    )

    await _patch_authoritative_outcome(
        monkeypatch,
        _authoritative_outcome(),
    )

    parent = _user(
        user_id=500,
        students=[
            SimpleNamespace(
                id=candidate_result["student_id"],
            ),
        ],
    )

    result = await service.get_parent_published_assessment_result(
        db_session,
        parent,
        candidate_id=candidate_result["candidate_id"],
    )

    assert result["student_id"] == candidate_result["student_id"]
    assert result["grade"] == "8"
    assert result["mark_awarded"] == Decimal("6.00")


@pytest.mark.asyncio
async def test_parent_student_link_object_is_supported(
    db_session: AsyncSession,
    monkeypatch,
):
    candidate_result = _candidate_result()

    await _patch_candidate_result(
        monkeypatch,
        candidate_result,
    )

    await _patch_publication(
        monkeypatch,
        _publication(),
    )

    await _patch_authoritative_outcome(
        monkeypatch,
        _authoritative_outcome(),
    )

    parent = _user(
        user_id=500,
        parent_students=[
            SimpleNamespace(
                student_id=candidate_result["student_id"],
            ),
        ],
    )

    result = await service.get_parent_published_assessment_result(
        db_session,
        parent,
        candidate_id=candidate_result["candidate_id"],
    )

    assert result["student_id"] == candidate_result["student_id"]


@pytest.mark.asyncio
async def test_parent_cannot_view_unrelated_child_result(
    db_session: AsyncSession,
    monkeypatch,
):
    candidate_result = _candidate_result()

    await _patch_candidate_result(
        monkeypatch,
        candidate_result,
    )

    parent = _user(
        user_id=500,
        students=[
            SimpleNamespace(
                id=999,
            ),
        ],
    )

    with pytest.raises(
        HTTPException,
    ) as exc:
        await service.get_parent_published_assessment_result(
            db_session,
            parent,
            candidate_id=candidate_result["candidate_id"],
        )

    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_parent_result_hidden_when_parent_visibility_disabled(
    db_session: AsyncSession,
    monkeypatch,
):
    candidate_result = _candidate_result()

    await _patch_candidate_result(
        monkeypatch,
        candidate_result,
    )

    await _patch_publication(
        monkeypatch,
        _publication(
            visible_to_parents=False,
        ),
    )

    parent = _user(
        user_id=500,
        students=[
            SimpleNamespace(
                id=candidate_result["student_id"],
            ),
        ],
    )

    with pytest.raises(
        HTTPException,
    ) as exc:
        await service.get_parent_published_assessment_result(
            db_session,
            parent,
            candidate_id=candidate_result["candidate_id"],
        )

    assert exc.value.status_code == 404


# ---------------------------------------------------------------------------
# Authoritative-result semantics
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_latest_script_does_not_replace_authoritative_result(
    db_session: AsyncSession,
    monkeypatch,
):
    candidate_result = _candidate_result(
        latest_script_id=900,
        latest_script_version=4,
        latest_mark=Decimal("10.00"),
        latest_percentage=Decimal("100.00"),
    )

    outcome = _authoritative_outcome(
        script_id=400,
        script_version=1,
        mark_awarded=Decimal("6.00"),
        percentage=Decimal("75.00"),
        grade="8",
    )

    await _prepare_student_result(
        monkeypatch,
        candidate_result=candidate_result,
        outcome=outcome,
    )

    student = _user(
        user_id=candidate_result["student_id"],
    )

    result = await service.get_student_published_assessment_result(
        db_session,
        student,
        candidate_id=candidate_result["candidate_id"],
    )

    assert result["script_id"] == 400
    assert result["script_version"] == 1
    assert result["mark_awarded"] == Decimal("6.00")
    assert result["percentage"] == Decimal("75.00")
    assert result["grade"] == "8"

    assert result["script_id"] != 900
    assert result["mark_awarded"] != Decimal("10.00")


@pytest.mark.asyncio
async def test_authoritative_remark_snapshot_changes_public_result(
    db_session: AsyncSession,
    monkeypatch,
):
    candidate_result = _candidate_result()

    remark_outcome = _authoritative_outcome(
        outcome_id=501,
        script_id=400,
        script_version=1,
        mark_awarded=Decimal("7.00"),
        percentage=Decimal("87.50"),
        grade="9",
        grade_points=Decimal("9.00"),
        is_pass=True,
    )

    await _prepare_student_result(
        monkeypatch,
        candidate_result=candidate_result,
        outcome=remark_outcome,
    )

    student = _user(
        user_id=candidate_result["student_id"],
    )

    result = await service.get_student_published_assessment_result(
        db_session,
        student,
        candidate_id=candidate_result["candidate_id"],
    )

    assert result["script_id"] == 400
    assert result["script_version"] == 1
    assert result["mark_awarded"] == Decimal("7.00")
    assert result["percentage"] == Decimal("87.50")
    assert result["grade"] == "9"
    assert result["grade_points"] == Decimal("9.00")


@pytest.mark.asyncio
async def test_snapshotted_grade_is_not_recalculated_from_current_scheme(
    db_session: AsyncSession,
    monkeypatch,
):
    candidate_result = _candidate_result()

    outcome = _authoritative_outcome(
        grade="7",
        grade_points=Decimal("7.00"),
        is_pass=True,
    )

    await _prepare_student_result(
        monkeypatch,
        candidate_result=candidate_result,
        outcome=outcome,
    )

    student = _user(
        user_id=candidate_result["student_id"],
    )

    result = await service.get_student_published_assessment_result(
        db_session,
        student,
        candidate_id=candidate_result["candidate_id"],
    )

    assert result["grade"] == "7"
    assert result["grade_points"] == Decimal("7.00")
    assert result["is_pass"] is True


@pytest.mark.asyncio
async def test_authoritative_result_can_have_no_grade_snapshot(
    db_session: AsyncSession,
    monkeypatch,
):
    candidate_result = _candidate_result()

    outcome = _authoritative_outcome(
        grade=None,
        grade_points=None,
        is_pass=None,
    )

    await _prepare_student_result(
        monkeypatch,
        candidate_result=candidate_result,
        outcome=outcome,
    )

    student = _user(
        user_id=candidate_result["student_id"],
    )

    result = await service.get_student_published_assessment_result(
        db_session,
        student,
        candidate_id=candidate_result["candidate_id"],
    )

    assert result["mark_awarded"] == Decimal("6.00")
    assert result["percentage"] == Decimal("75.00")

    assert result["grade"] is None
    assert result["grade_points"] is None
    assert result["is_pass"] is None


# ---------------------------------------------------------------------------
# Field visibility
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_mark_can_be_hidden_while_percentage_remains_visible(
    db_session: AsyncSession,
    monkeypatch,
):
    candidate_result = _candidate_result()

    await _prepare_student_result(
        monkeypatch,
        candidate_result=candidate_result,
        publication=_publication(
            include_mark=False,
            include_percentage=True,
        ),
    )

    student = _user(
        user_id=candidate_result["student_id"],
    )

    result = await service.get_student_published_assessment_result(
        db_session,
        student,
        candidate_id=candidate_result["candidate_id"],
    )

    assert result["mark_awarded"] is None
    assert result["percentage"] == Decimal("75.00")


@pytest.mark.asyncio
async def test_percentage_can_be_hidden_while_mark_remains_visible(
    db_session: AsyncSession,
    monkeypatch,
):
    candidate_result = _candidate_result()

    await _prepare_student_result(
        monkeypatch,
        candidate_result=candidate_result,
        publication=_publication(
            include_mark=True,
            include_percentage=False,
        ),
    )

    student = _user(
        user_id=candidate_result["student_id"],
    )

    result = await service.get_student_published_assessment_result(
        db_session,
        student,
        candidate_id=candidate_result["candidate_id"],
    )

    assert result["mark_awarded"] == Decimal("6.00")
    assert result["percentage"] is None


@pytest.mark.asyncio
async def test_grade_can_be_hidden(
    db_session: AsyncSession,
    monkeypatch,
):
    candidate_result = _candidate_result()

    await _prepare_student_result(
        monkeypatch,
        candidate_result=candidate_result,
        publication=_publication(
            include_grade=False,
        ),
    )

    student = _user(
        user_id=candidate_result["student_id"],
    )

    result = await service.get_student_published_assessment_result(
        db_session,
        student,
        candidate_id=candidate_result["candidate_id"],
    )

    assert result["grade"] is None
    assert result["grade_points"] is None
    assert result["is_pass"] is None

    assert result["mark_awarded"] == Decimal("6.00")


@pytest.mark.asyncio
async def test_all_result_fields_can_be_hidden_independently(
    db_session: AsyncSession,
    monkeypatch,
):
    candidate_result = _candidate_result()

    await _prepare_student_result(
        monkeypatch,
        candidate_result=candidate_result,
        publication=_publication(
            include_mark=False,
            include_percentage=False,
            include_grade=False,
            include_question_breakdown=False,
        ),
    )

    student = _user(
        user_id=candidate_result["student_id"],
    )

    result = await service.get_student_published_assessment_result(
        db_session,
        student,
        candidate_id=candidate_result["candidate_id"],
    )

    assert result["mark_awarded"] is None
    assert result["percentage"] is None
    assert result["grade"] is None
    assert result["grade_points"] is None
    assert result["is_pass"] is None
    assert result["question_breakdown"] is None


# ---------------------------------------------------------------------------
# Question-breakdown safety
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_question_breakdown_hidden_by_default(
    db_session: AsyncSession,
    monkeypatch,
):
    candidate_result = _candidate_result()

    await _prepare_student_result(
        monkeypatch,
        candidate_result=candidate_result,
        publication=_publication(
            include_question_breakdown=False,
        ),
    )

    async def should_not_load_script_result(
        **kwargs,
    ):
        raise AssertionError(
            "Question result must not be loaded when breakdown is hidden.",
        )

    monkeypatch.setattr(
        service,
        "get_script_result",
        should_not_load_script_result,
    )

    student = _user(
        user_id=candidate_result["student_id"],
    )

    result = await service.get_student_published_assessment_result(
        db_session,
        student,
        candidate_id=candidate_result["candidate_id"],
    )

    assert result["question_breakdown"] is None


@pytest.mark.asyncio
async def test_question_breakdown_uses_authoritative_script_when_enabled(
    db_session: AsyncSession,
    monkeypatch,
):
    candidate_result = _candidate_result(
        latest_script_id=999,
        latest_script_version=3,
    )

    outcome = _authoritative_outcome(
        script_id=400,
        script_version=1,
    )

    await _prepare_student_result(
        monkeypatch,
        candidate_result=candidate_result,
        publication=_publication(
            include_question_breakdown=True,
        ),
        outcome=outcome,
    )

    script_result = _authoritative_script_result(
        script_id=400,
        script_version=1,
    )

    requested_script_ids: list[int] = []

    async def fake_get_script_result(
        *,
        db,
        current_user,
        script_id,
    ):
        requested_script_ids.append(
            script_id,
        )

        return script_result

    monkeypatch.setattr(
        service,
        "get_script_result",
        fake_get_script_result,
    )

    student = _user(
        user_id=candidate_result["student_id"],
    )

    result = await service.get_student_published_assessment_result(
        db_session,
        student,
        candidate_id=candidate_result["candidate_id"],
    )

    assert requested_script_ids == [400]

    assert result["question_breakdown"] is not None
    assert len(result["question_breakdown"]) == 2
    assert result["question_breakdown"][0]["question_id"] == 1


@pytest.mark.asyncio
async def test_question_breakdown_hidden_when_pending_remark_changes_mark(
    db_session: AsyncSession,
    monkeypatch,
):
    candidate_result = _candidate_result()

    outcome = _authoritative_outcome(
        script_id=400,
        script_version=1,
        mark_awarded=Decimal("6.00"),
        percentage=Decimal("75.00"),
    )

    await _prepare_student_result(
        monkeypatch,
        candidate_result=candidate_result,
        publication=_publication(
            include_question_breakdown=True,
        ),
        outcome=outcome,
    )

    changed_script_result = _authoritative_script_result(
        script_id=400,
        script_version=1,
        mark_awarded=Decimal("7.00"),
        percentage=Decimal("87.50"),
    )

    await _patch_script_result(
        monkeypatch,
        changed_script_result,
    )

    student = _user(
        user_id=candidate_result["student_id"],
    )

    result = await service.get_student_published_assessment_result(
        db_session,
        student,
        candidate_id=candidate_result["candidate_id"],
    )

    # Official aggregate remains the immutable authoritative snapshot.
    assert result["mark_awarded"] == Decimal("6.00")
    assert result["percentage"] == Decimal("75.00")

    # Pending same-script remark details must not leak.
    assert result["question_breakdown"] is None


@pytest.mark.asyncio
async def test_question_breakdown_hidden_when_script_version_is_inconsistent(
    db_session: AsyncSession,
    monkeypatch,
):
    candidate_result = _candidate_result()

    outcome = _authoritative_outcome(
        script_id=400,
        script_version=1,
    )

    await _prepare_student_result(
        monkeypatch,
        candidate_result=candidate_result,
        publication=_publication(
            include_question_breakdown=True,
        ),
        outcome=outcome,
    )

    wrong_version = _authoritative_script_result(
        script_id=400,
        script_version=2,
    )

    await _patch_script_result(
        monkeypatch,
        wrong_version,
    )

    student = _user(
        user_id=candidate_result["student_id"],
    )

    result = await service.get_student_published_assessment_result(
        db_session,
        student,
        candidate_id=candidate_result["candidate_id"],
    )

    assert result["question_breakdown"] is None


@pytest.mark.asyncio
async def test_unavailable_authoritative_script_hides_question_breakdown_only(
    db_session: AsyncSession,
    monkeypatch,
):
    candidate_result = _candidate_result()

    await _prepare_student_result(
        monkeypatch,
        candidate_result=candidate_result,
        publication=_publication(
            include_question_breakdown=True,
        ),
    )

    await _patch_script_result(
        monkeypatch,
        HTTPException(
            status_code=404,
            detail="Script not found.",
        ),
    )

    student = _user(
        user_id=candidate_result["student_id"],
    )

    result = await service.get_student_published_assessment_result(
        db_session,
        student,
        candidate_id=candidate_result["candidate_id"],
    )

    assert result["mark_awarded"] == Decimal("6.00")
    assert result["grade"] == "8"
    assert result["question_breakdown"] is None


@pytest.mark.asyncio
async def test_unexpected_script_result_error_is_not_suppressed(
    db_session: AsyncSession,
    monkeypatch,
):
    candidate_result = _candidate_result()

    await _prepare_student_result(
        monkeypatch,
        candidate_result=candidate_result,
        publication=_publication(
            include_question_breakdown=True,
        ),
    )

    await _patch_script_result(
        monkeypatch,
        HTTPException(
            status_code=403,
            detail="Forbidden.",
        ),
    )

    student = _user(
        user_id=candidate_result["student_id"],
    )

    with pytest.raises(
        HTTPException,
    ) as exc:
        await service.get_student_published_assessment_result(
            db_session,
            student,
            candidate_id=candidate_result["candidate_id"],
        )

    assert exc.value.status_code == 403


# ---------------------------------------------------------------------------
# Consistency protection
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_candidate_and_authoritative_outcome_must_match(
    db_session: AsyncSession,
    monkeypatch,
):
    candidate_result = _candidate_result(
        candidate_id=200,
    )

    wrong_outcome = _authoritative_outcome(
        candidate_id=201,
    )

    await _prepare_student_result(
        monkeypatch,
        candidate_result=candidate_result,
        outcome=wrong_outcome,
    )

    student = _user(
        user_id=candidate_result["student_id"],
    )

    with pytest.raises(
        HTTPException,
    ) as exc:
        await service.get_student_published_assessment_result(
            db_session,
            student,
            candidate_id=candidate_result["candidate_id"],
        )

    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_assessment_and_authoritative_outcome_must_match(
    db_session: AsyncSession,
    monkeypatch,
):
    candidate_result = _candidate_result(
        assessment_id=100,
    )

    wrong_outcome = _authoritative_outcome(
        assessment_id=101,
    )

    await _prepare_student_result(
        monkeypatch,
        candidate_result=candidate_result,
        outcome=wrong_outcome,
    )

    student = _user(
        user_id=candidate_result["student_id"],
    )

    with pytest.raises(
        HTTPException,
    ) as exc:
        await service.get_student_published_assessment_result(
            db_session,
            student,
            candidate_id=candidate_result["candidate_id"],
        )

    assert exc.value.status_code == 404


# ---------------------------------------------------------------------------
# Public representation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_public_result_contains_release_metadata(
    db_session: AsyncSession,
    monkeypatch,
):
    candidate_result = _candidate_result()

    publication = _publication(
        release_message="Well done.",
    )

    await _prepare_student_result(
        monkeypatch,
        candidate_result=candidate_result,
        publication=publication,
    )

    student = _user(
        user_id=candidate_result["student_id"],
    )

    result = await service.get_student_published_assessment_result(
        db_session,
        student,
        candidate_id=candidate_result["candidate_id"],
    )

    assert result["release_message"] == "Well done."
    assert result["published_at"] == publication.published_at


@pytest.mark.asyncio
async def test_public_result_reports_visibility_configuration(
    db_session: AsyncSession,
    monkeypatch,
):
    candidate_result = _candidate_result()

    publication = _publication(
        include_mark=False,
        include_percentage=True,
        include_grade=False,
        include_question_breakdown=False,
    )

    await _prepare_student_result(
        monkeypatch,
        candidate_result=candidate_result,
        publication=publication,
    )

    student = _user(
        user_id=candidate_result["student_id"],
    )

    result = await service.get_student_published_assessment_result(
        db_session,
        student,
        candidate_id=candidate_result["candidate_id"],
    )

    assert result["visibility"] == {
        "include_mark": False,
        "include_percentage": True,
        "include_grade": False,
        "include_question_breakdown": False,
    }


@pytest.mark.asyncio
async def test_public_result_identifies_authoritative_script(
    db_session: AsyncSession,
    monkeypatch,
):
    candidate_result = _candidate_result(
        latest_script_id=999,
        latest_script_version=5,
    )

    outcome = _authoritative_outcome(
        script_id=444,
        script_version=2,
    )

    await _prepare_student_result(
        monkeypatch,
        candidate_result=candidate_result,
        outcome=outcome,
    )

    student = _user(
        user_id=candidate_result["student_id"],
    )

    result = await service.get_student_published_assessment_result(
        db_session,
        student,
        candidate_id=candidate_result["candidate_id"],
    )

    assert result["script_id"] == 444
    assert result["script_version"] == 2
