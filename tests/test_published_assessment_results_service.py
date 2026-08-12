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
):
    return {
        "assessment_id": assessment_id,
        "candidate_id": candidate_id,
        "student_id": student_id,
        "candidate_number": "PUB-001",
        "latest_script_result": {
            "script_id": 400,
            "script_version": 1,
            "finalised_mark_awarded": Decimal("6.00"),
            "finalised_percentage": Decimal("75.00"),
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
        },
    }


def _grade_result():
    return {
        "grade": "8",
        "grade_points": Decimal("8.00"),
        "is_pass": True,
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


async def _patch_grade(
    monkeypatch,
    grade_result,
):
    async def fake_grade_candidate_latest_result(
        *,
        db,
        current_user,
        candidate_id,
        result_stage,
    ):
        return grade_result

    monkeypatch.setattr(
        service,
        "grade_candidate_latest_result",
        fake_grade_candidate_latest_result,
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

    with pytest.raises(HTTPException) as exc:
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

    with pytest.raises(HTTPException) as exc:
        await service.get_parent_published_assessment_result(
            db_session,
            parent,
            candidate_id=candidate_result["candidate_id"],
        )

    assert exc.value.status_code == 404


# ---------------------------------------------------------------------------
# Student ownership
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_student_can_view_own_published_result(
    db_session: AsyncSession,
    monkeypatch,
):
    candidate_result = _candidate_result()
    publication = _publication()

    await _patch_candidate_result(
        monkeypatch,
        candidate_result,
    )

    await _patch_publication(
        monkeypatch,
        publication,
    )

    await _patch_grade(
        monkeypatch,
        _grade_result(),
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
    assert result["mark_awarded"] == Decimal("6.00")
    assert result["percentage"] == Decimal("75.00")
    assert result["grade"] == "8"


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

    with pytest.raises(HTTPException) as exc:
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

    with pytest.raises(HTTPException) as exc:
        await service.get_student_published_assessment_result(
            db_session,
            student,
            candidate_id=candidate_result["candidate_id"],
        )

    assert exc.value.status_code == 404


# ---------------------------------------------------------------------------
# Parent-child authorization
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_parent_can_view_linked_child_result(
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

    await _patch_grade(
        monkeypatch,
        _grade_result(),
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

    await _patch_grade(
        monkeypatch,
        _grade_result(),
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

    with pytest.raises(HTTPException) as exc:
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

    with pytest.raises(HTTPException) as exc:
        await service.get_parent_published_assessment_result(
            db_session,
            parent,
            candidate_id=candidate_result["candidate_id"],
        )

    assert exc.value.status_code == 404


# ---------------------------------------------------------------------------
# Field visibility
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_mark_can_be_hidden_while_percentage_remains_visible(
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
            include_mark=False,
            include_percentage=True,
        ),
    )

    await _patch_grade(
        monkeypatch,
        _grade_result(),
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

    await _patch_candidate_result(
        monkeypatch,
        candidate_result,
    )

    await _patch_publication(
        monkeypatch,
        _publication(
            include_mark=True,
            include_percentage=False,
        ),
    )

    await _patch_grade(
        monkeypatch,
        _grade_result(),
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

    await _patch_candidate_result(
        monkeypatch,
        candidate_result,
    )

    await _patch_publication(
        monkeypatch,
        _publication(
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


@pytest.mark.asyncio
async def test_question_breakdown_hidden_by_default(
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
            include_question_breakdown=False,
        ),
    )

    await _patch_grade(
        monkeypatch,
        _grade_result(),
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
async def test_question_breakdown_returned_when_enabled(
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
            include_question_breakdown=True,
        ),
    )

    await _patch_grade(
        monkeypatch,
        _grade_result(),
    )

    student = _user(
        user_id=candidate_result["student_id"],
    )

    result = await service.get_student_published_assessment_result(
        db_session,
        student,
        candidate_id=candidate_result["candidate_id"],
    )

    assert result["question_breakdown"] is not None
    assert len(result["question_breakdown"]) == 2
    assert result["question_breakdown"][0]["question_id"] == 1


@pytest.mark.asyncio
async def test_all_result_fields_can_be_hidden_independently(
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
# Grade-resolution resilience
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_missing_grading_scheme_does_not_hide_published_marks(
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
            include_grade=True,
        ),
    )

    async def missing_grade(
        *,
        db,
        current_user,
        candidate_id,
        result_stage,
    ):
        raise HTTPException(
            status_code=404,
            detail="No grading scheme.",
        )

    monkeypatch.setattr(
        service,
        "grade_candidate_latest_result",
        missing_grade,
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


@pytest.mark.asyncio
async def test_ungradable_candidate_does_not_hide_published_marks(
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
            include_grade=True,
        ),
    )

    async def unavailable_grade(
        *,
        db,
        current_user,
        candidate_id,
        result_stage,
    ):
        raise HTTPException(
            status_code=409,
            detail="Candidate cannot yet be graded.",
        )

    monkeypatch.setattr(
        service,
        "grade_candidate_latest_result",
        unavailable_grade,
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
    assert result["grade"] is None


@pytest.mark.asyncio
async def test_unexpected_grading_error_is_not_suppressed(
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

    async def forbidden_grade(
        *,
        db,
        current_user,
        candidate_id,
        result_stage,
    ):
        raise HTTPException(
            status_code=403,
            detail="Forbidden.",
        )

    monkeypatch.setattr(
        service,
        "grade_candidate_latest_result",
        forbidden_grade,
    )

    student = _user(
        user_id=candidate_result["student_id"],
    )

    with pytest.raises(HTTPException) as exc:
        await service.get_student_published_assessment_result(
            db_session,
            student,
            candidate_id=candidate_result["candidate_id"],
        )

    assert exc.value.status_code == 403


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

    await _patch_candidate_result(
        monkeypatch,
        candidate_result,
    )

    await _patch_publication(
        monkeypatch,
        publication,
    )

    await _patch_grade(
        monkeypatch,
        _grade_result(),
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
        include_question_breakdown=True,
    )

    await _patch_candidate_result(
        monkeypatch,
        candidate_result,
    )

    await _patch_publication(
        monkeypatch,
        publication,
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
        "include_question_breakdown": True,
    }
