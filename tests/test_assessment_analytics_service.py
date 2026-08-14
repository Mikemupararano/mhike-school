from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

import app.services.assessment_analytics_service as service

# ---------------------------------------------------------------------------
# Test-data helpers
# ---------------------------------------------------------------------------


def _script(
    *,
    script_id: int,
    version: int,
):
    return SimpleNamespace(
        id=script_id,
        version=version,
    )


def _candidate(
    *,
    candidate_id: int,
    student_id: int,
    candidate_number: str,
    scripts=None,
):
    return SimpleNamespace(
        id=candidate_id,
        student_id=student_id,
        candidate_number=candidate_number,
        status="submitted",
        scripts=list(
            scripts or [],
        ),
    )


def _summary(
    *,
    assessment_id: int = 100,
    candidate_count: int = 3,
    script_count: int = 3,
):
    return {
        "assessment_id": assessment_id,
        "title": "Mechanics End of Topic Test",
        "status": "published",
        "maximum_mark": Decimal("50.00"),
        "markable_question_count": 5,
        "candidate_count": candidate_count,
        "script_count": script_count,
        "expected_question_decisions": 15,
        "completed_decision_count": 15,
        "finalised_decision_count": 15,
        "marking_completion_percentage": Decimal("100.00"),
        "finalisation_completion_percentage": Decimal("100.00"),
        "total_awarded_marks": Decimal("105.00"),
        "completed_awarded_marks": Decimal("105.00"),
        "finalised_awarded_marks": Decimal("105.00"),
    }


def _latest_result(
    *,
    candidate_id: int,
    student_id: int,
    script_id: int,
    script_version: int,
    mark: Decimal | None,
    percentage: Decimal | None,
    maximum_mark: Decimal = Decimal("50.00"),
    fully_marked: bool = True,
    fully_finalised: bool = True,
):
    return {
        "assessment_id": 100,
        "candidate_id": candidate_id,
        "student_id": student_id,
        "script_id": script_id,
        "script_version": script_version,
        "script_status": "submitted",
        "maximum_mark": maximum_mark,
        "mark_awarded": mark,
        "completed_mark_awarded": mark,
        "finalised_mark_awarded": mark,
        "percentage": percentage,
        "completed_percentage": percentage,
        "finalised_percentage": percentage,
        "markable_question_count": 5,
        "response_count": 5,
        "submitted_response_count": 5,
        "decision_count": 5,
        "marked_question_count": (5 if fully_marked else 4),
        "finalised_question_count": (5 if fully_finalised else 4),
        "response_completion_percentage": Decimal("100.00"),
        "marking_completion_percentage": (
            Decimal("100.00") if fully_marked else Decimal("80.00")
        ),
        "finalisation_completion_percentage": (
            Decimal("100.00") if fully_finalised else Decimal("80.00")
        ),
        "is_fully_responded": True,
        "is_fully_marked": fully_marked,
        "is_fully_finalised": fully_finalised,
        "questions": [],
    }


def _candidate_result(
    *,
    candidate_id: int,
    student_id: int,
    latest: dict | None,
):
    return {
        "assessment_id": 100,
        "candidate_id": candidate_id,
        "student_id": student_id,
        "candidate_number": f"C-{candidate_id}",
        "candidate_status": "submitted",
        "script_count": (1 if latest is not None else 0),
        "scripts": ([latest] if latest is not None else []),
        "latest_script_result": latest,
    }


def _outcome(
    *,
    outcome_id: int,
    candidate_id: int,
    script_id: int,
    script_version: int = 1,
    assessment_id: int = 100,
    mark: Decimal = Decimal("40.00"),
    maximum_mark: Decimal = Decimal("50.00"),
    percentage: Decimal = Decimal("80.00"),
    grade: str | None = "8",
    grade_points: Decimal | None = Decimal("8.00"),
    is_pass: bool | None = True,
    is_authoritative: bool = True,
):
    """
    Return a lightweight authoritative-outcome object.

    The analytics service consumes model attributes only, so SimpleNamespace
    gives these unit tests a focused representation without requiring database
    persistence.
    """

    return SimpleNamespace(
        id=outcome_id,
        school_id=10,
        assessment_id=assessment_id,
        candidate_id=candidate_id,
        script_id=script_id,
        version=1,
        status=("authoritative" if is_authoritative else "draft"),
        change_type="initial",
        supersedes_id=None,
        is_authoritative=is_authoritative,
        mark_awarded_snapshot=mark,
        maximum_mark_snapshot=maximum_mark,
        percentage_snapshot=percentage,
        grading_scheme_id_snapshot=1,
        grading_scheme_name_snapshot="GCSE",
        grading_basis_snapshot="percentage",
        grade_boundary_id_snapshot=1,
        grade_label_snapshot=grade,
        grade_points_snapshot=grade_points,
        is_pass_snapshot=is_pass,
        script_version_snapshot=script_version,
    )


def _grade_result(
    *,
    grade: str | None,
    grade_points: Decimal | None = None,
    is_pass: bool | None = None,
    minimum_value: Decimal | None = None,
):
    """
    Grade-distribution helper input.

    This no longer represents a live grading-service response. It simply
    exercises the generic grade-distribution helper.
    """

    return {
        "grade": grade,
        "minimum_value": minimum_value,
        "grade_points": grade_points,
        "is_pass": is_pass,
    }


# ---------------------------------------------------------------------------
# Monkeypatch helpers
# ---------------------------------------------------------------------------


async def _patch_context(
    monkeypatch,
    *,
    candidates,
    summary=None,
):
    summary_value = (
        summary
        if summary is not None
        else _summary(
            candidate_count=len(
                candidates,
            ),
            script_count=sum(
                len(
                    candidate.scripts,
                )
                for candidate in candidates
            ),
        )
    )

    async def fake_summary(
        *,
        db,
        current_user,
        assessment_id,
    ):
        return summary_value

    monkeypatch.setattr(
        service,
        "get_assessment_results_summary",
        fake_summary,
    )

    assessment = SimpleNamespace(
        id=summary_value["assessment_id"],
        candidates=candidates,
    )

    class FakeRepository:
        def __init__(
            self,
            db,
        ):
            self.db = db

        async def get_assessment_by_id(
            self,
            assessment_id,
            *,
            include_results,
        ):
            assert include_results is True

            if assessment_id != summary_value["assessment_id"]:
                return None

            return assessment

    monkeypatch.setattr(
        service,
        "AssessmentResultsRepository",
        FakeRepository,
    )


async def _patch_candidate_results(
    monkeypatch,
    *,
    results_by_candidate_id,
):
    async def fake_candidate_result(
        *,
        db,
        current_user,
        candidate_id,
    ):
        return results_by_candidate_id[candidate_id]

    monkeypatch.setattr(
        service,
        "get_candidate_result",
        fake_candidate_result,
    )


async def _patch_outcomes(
    monkeypatch,
    *,
    outcomes,
):
    class FakeOutcomeRepository:
        def __init__(
            self,
            db,
        ):
            self.db = db

        async def list_for_assessment(
            self,
            assessment_id,
            *,
            authoritative_only=False,
        ):
            assert assessment_id == 100
            assert authoritative_only is True

            return list(
                outcomes,
            )

    monkeypatch.setattr(
        service,
        "AssessmentResultOutcomeRepository",
        FakeOutcomeRepository,
    )


async def _patch_questions(
    monkeypatch,
    *,
    questions=None,
):
    question_rows = (
        questions
        if questions is not None
        else [
            {
                "question_id": 1,
                "question_number": "1",
                "title": "Forces",
                "maximum_mark": Decimal("5.00"),
                "response_count": 3,
                "marked_count": 3,
                "mark_sum": Decimal("12.00"),
                "mark_average": Decimal("4.00"),
                "mark_minimum": Decimal("3.00"),
                "mark_maximum": Decimal("5.00"),
                "average_percentage": Decimal("80.00"),
            },
        ]
    )

    async def fake_question_analysis(
        *,
        db,
        current_user,
        assessment_id,
        completed_only,
    ):
        assert completed_only is True

        return question_rows

    monkeypatch.setattr(
        service,
        "get_assessment_question_analysis",
        fake_question_analysis,
    )


# ---------------------------------------------------------------------------
# Numeric helpers
# ---------------------------------------------------------------------------


def test_mean_uses_two_decimal_rounding():
    result = service._mean(
        [
            Decimal("1"),
            Decimal("2"),
            Decimal("2"),
        ],
    )

    assert result == Decimal("1.67")


def test_median_of_odd_number_of_values():
    result = service._median(
        [
            Decimal("10"),
            Decimal("30"),
            Decimal("20"),
        ],
    )

    assert result == Decimal("20.00")


def test_median_of_even_number_of_values():
    result = service._median(
        [
            Decimal("10"),
            Decimal("20"),
            Decimal("30"),
            Decimal("40"),
        ],
    )

    assert result == Decimal("25.00")


def test_empty_mean_and_median_are_none():
    assert (
        service._mean(
            [],
        )
        is None
    )

    assert (
        service._median(
            [],
        )
        is None
    )


# ---------------------------------------------------------------------------
# Latest-script operational semantics
# ---------------------------------------------------------------------------


def test_latest_candidate_script_uses_highest_version():
    candidate = _candidate(
        candidate_id=1,
        student_id=101,
        candidate_number="A001",
        scripts=[
            _script(
                script_id=10,
                version=1,
            ),
            _script(
                script_id=11,
                version=3,
            ),
            _script(
                script_id=12,
                version=2,
            ),
        ],
    )

    latest = service._latest_candidate_script(
        candidate,
    )

    assert latest.id == 11
    assert latest.version == 3


def test_latest_candidate_script_uses_id_as_tiebreaker():
    candidate = _candidate(
        candidate_id=1,
        student_id=101,
        candidate_number="A001",
        scripts=[
            _script(
                script_id=10,
                version=2,
            ),
            _script(
                script_id=12,
                version=2,
            ),
        ],
    )

    latest = service._latest_candidate_script(
        candidate,
    )

    assert latest.id == 12


def test_candidate_without_scripts_has_no_latest_script():
    candidate = _candidate(
        candidate_id=1,
        student_id=101,
        candidate_number="A001",
    )

    assert (
        service._latest_candidate_script(
            candidate,
        )
        is None
    )


# ---------------------------------------------------------------------------
# Ranking
# ---------------------------------------------------------------------------


def test_competition_ranking_handles_ties():
    rows = [
        {
            "candidate_id": 1,
            "percentage": Decimal("90.00"),
            "mark_awarded": Decimal("45.00"),
        },
        {
            "candidate_id": 2,
            "percentage": Decimal("90.00"),
            "mark_awarded": Decimal("45.00"),
        },
        {
            "candidate_id": 3,
            "percentage": Decimal("80.00"),
            "mark_awarded": Decimal("40.00"),
        },
    ]

    ranked = service._apply_competition_ranks(
        rows,
    )

    assert [row["rank"] for row in ranked] == [
        1,
        1,
        3,
    ]


def test_ranking_orders_highest_percentage_first():
    rows = [
        {
            "candidate_id": 1,
            "percentage": Decimal("60.00"),
            "mark_awarded": Decimal("30.00"),
        },
        {
            "candidate_id": 2,
            "percentage": Decimal("90.00"),
            "mark_awarded": Decimal("45.00"),
        },
    ]

    ranked = service._apply_competition_ranks(
        rows,
    )

    assert ranked[0]["candidate_id"] == 2
    assert ranked[0]["rank"] == 1
    assert ranked[1]["rank"] == 2


# ---------------------------------------------------------------------------
# Grade distribution
# ---------------------------------------------------------------------------


def test_grade_distribution_counts_resolved_grades():
    grades = [
        _grade_result(
            grade="9",
            grade_points=Decimal("9"),
            is_pass=True,
        ),
        _grade_result(
            grade="9",
            grade_points=Decimal("9"),
            is_pass=True,
        ),
        _grade_result(
            grade="8",
            grade_points=Decimal("8"),
            is_pass=True,
        ),
    ]

    distribution = service._build_grade_distribution(
        grades,
    )

    assert distribution[0]["grade"] == "9"
    assert distribution[0]["count"] == 2
    assert distribution[0]["percentage"] == Decimal("66.67")

    assert distribution[1]["grade"] == "8"
    assert distribution[1]["count"] == 1
    assert distribution[1]["percentage"] == Decimal("33.33")


def test_unresolved_grades_are_excluded_from_distribution():
    distribution = service._build_grade_distribution(
        [
            _grade_result(
                grade=None,
            ),
            _grade_result(
                grade="7",
            ),
        ],
    )

    assert (
        len(
            distribution,
        )
        == 1
    )

    assert distribution[0]["grade"] == "7"
    assert distribution[0]["count"] == 1


def test_authoritative_grade_distribution_does_not_invent_boundary_minimum():
    outcome = _outcome(
        outcome_id=1,
        candidate_id=1,
        script_id=11,
        grade="8",
        grade_points=Decimal("8.00"),
        is_pass=True,
    )

    result = service._build_authoritative_grade_result(
        outcome,
    )

    assert result == {
        "grade": "8",
        "minimum_value": None,
        "grade_points": Decimal("8.00"),
        "is_pass": True,
    }


# ---------------------------------------------------------------------------
# Authoritative outcome validation
# ---------------------------------------------------------------------------


def test_authoritative_outcome_map_indexes_by_candidate():
    outcomes = [
        _outcome(
            outcome_id=1,
            candidate_id=10,
            script_id=100,
        ),
        _outcome(
            outcome_id=2,
            candidate_id=20,
            script_id=200,
        ),
    ]

    result = service._authoritative_outcome_map(
        outcomes,
        assessment_id=100,
    )

    assert result[10] is outcomes[0]
    assert result[20] is outcomes[1]


def test_authoritative_outcome_map_rejects_wrong_assessment():
    outcome = _outcome(
        outcome_id=1,
        candidate_id=10,
        script_id=100,
        assessment_id=999,
    )

    with pytest.raises(
        HTTPException,
    ) as exc:
        service._authoritative_outcome_map(
            [outcome],
            assessment_id=100,
        )

    assert exc.value.status_code == 409


def test_authoritative_outcome_map_rejects_non_authoritative_row():
    outcome = _outcome(
        outcome_id=1,
        candidate_id=10,
        script_id=100,
        is_authoritative=False,
    )

    with pytest.raises(
        HTTPException,
    ) as exc:
        service._authoritative_outcome_map(
            [outcome],
            assessment_id=100,
        )

    assert exc.value.status_code == 409


def test_authoritative_outcome_map_rejects_duplicate_candidate():
    outcomes = [
        _outcome(
            outcome_id=1,
            candidate_id=10,
            script_id=100,
        ),
        _outcome(
            outcome_id=2,
            candidate_id=10,
            script_id=101,
        ),
    ]

    with pytest.raises(
        HTTPException,
    ) as exc:
        service._authoritative_outcome_map(
            outcomes,
            assessment_id=100,
        )

    assert exc.value.status_code == 409


# ---------------------------------------------------------------------------
# Main authoritative analytics
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_assessment_analytics_calculates_authoritative_cohort_statistics(
    db_session: AsyncSession,
    teacher_user,
    monkeypatch,
):
    candidates = [
        _candidate(
            candidate_id=1,
            student_id=101,
            candidate_number="A001",
            scripts=[
                _script(
                    script_id=11,
                    version=1,
                ),
            ],
        ),
        _candidate(
            candidate_id=2,
            student_id=102,
            candidate_number="A002",
            scripts=[
                _script(
                    script_id=21,
                    version=1,
                ),
            ],
        ),
        _candidate(
            candidate_id=3,
            student_id=103,
            candidate_number="A003",
            scripts=[
                _script(
                    script_id=31,
                    version=1,
                ),
            ],
        ),
    ]

    await _patch_context(
        monkeypatch,
        candidates=candidates,
    )

    await _patch_candidate_results(
        monkeypatch,
        results_by_candidate_id={
            1: _candidate_result(
                candidate_id=1,
                student_id=101,
                latest=_latest_result(
                    candidate_id=1,
                    student_id=101,
                    script_id=11,
                    script_version=1,
                    mark=Decimal("41"),
                    percentage=Decimal("82"),
                ),
            ),
            2: _candidate_result(
                candidate_id=2,
                student_id=102,
                latest=_latest_result(
                    candidate_id=2,
                    student_id=102,
                    script_id=21,
                    script_version=1,
                    mark=Decimal("31"),
                    percentage=Decimal("62"),
                ),
            ),
            3: _candidate_result(
                candidate_id=3,
                student_id=103,
                latest=_latest_result(
                    candidate_id=3,
                    student_id=103,
                    script_id=31,
                    script_version=1,
                    mark=Decimal("36"),
                    percentage=Decimal("72"),
                ),
            ),
        },
    )

    await _patch_outcomes(
        monkeypatch,
        outcomes=[
            _outcome(
                outcome_id=101,
                candidate_id=1,
                script_id=11,
                mark=Decimal("40"),
                percentage=Decimal("80"),
                grade="8",
                grade_points=Decimal("8"),
                is_pass=True,
            ),
            _outcome(
                outcome_id=102,
                candidate_id=2,
                script_id=21,
                mark=Decimal("30"),
                percentage=Decimal("60"),
                grade="6",
                grade_points=Decimal("6"),
                is_pass=True,
            ),
            _outcome(
                outcome_id=103,
                candidate_id=3,
                script_id=31,
                mark=Decimal("35"),
                percentage=Decimal("70"),
                grade="7",
                grade_points=Decimal("7"),
                is_pass=True,
            ),
        ],
    )

    await _patch_questions(
        monkeypatch,
    )

    result = await service.get_assessment_analytics(
        db_session,
        teacher_user,
        100,
    )

    assert result["result_stage"] == "authoritative"
    assert result["script_selection"] == "authoritative"

    assert result["candidate_count"] == 3
    assert result["included_candidate_count"] == 3

    assert result["candidates_without_authoritative_result"] == 0

    assert result["mean_mark"] == Decimal("35.00")
    assert result["median_mark"] == Decimal("35.00")
    assert result["lowest_mark"] == Decimal("30.00")
    assert result["highest_mark"] == Decimal("40.00")

    assert result["mean_percentage"] == Decimal("70.00")
    assert result["median_percentage"] == Decimal("70.00")
    assert result["lowest_percentage"] == Decimal("60.00")
    assert result["highest_percentage"] == Decimal("80.00")

    assert [row["candidate_id"] for row in result["ranking"]] == [
        1,
        3,
        2,
    ]

    # Proves analytics used snapshots rather than the slightly newer live
    # finalised values in candidate_result.
    assert result["ranking"][0]["mark_awarded"] == Decimal("40.00")


@pytest.mark.asyncio
async def test_finalised_script_without_authoritative_outcome_is_not_included(
    db_session: AsyncSession,
    teacher_user,
    monkeypatch,
):
    candidates = [
        _candidate(
            candidate_id=1,
            student_id=101,
            candidate_number="A001",
            scripts=[
                _script(
                    script_id=11,
                    version=1,
                ),
            ],
        ),
    ]

    await _patch_context(
        monkeypatch,
        candidates=candidates,
    )

    await _patch_candidate_results(
        monkeypatch,
        results_by_candidate_id={
            1: _candidate_result(
                candidate_id=1,
                student_id=101,
                latest=_latest_result(
                    candidate_id=1,
                    student_id=101,
                    script_id=11,
                    script_version=1,
                    mark=Decimal("40"),
                    percentage=Decimal("80"),
                ),
            ),
        },
    )

    await _patch_outcomes(
        monkeypatch,
        outcomes=[],
    )

    await _patch_questions(
        monkeypatch,
    )

    result = await service.get_assessment_analytics(
        db_session,
        teacher_user,
        100,
    )

    assert result["fully_finalised_candidate_count"] == 1
    assert result["included_candidate_count"] == 0

    assert result["candidates_without_authoritative_result"] == 1

    assert result["mean_mark"] is None
    assert result["ranking"] == []


@pytest.mark.asyncio
async def test_incomplete_latest_script_is_operationally_counted_but_authoritative_result_remains_included(
    db_session: AsyncSession,
    teacher_user,
    monkeypatch,
):
    """
    A newer incomplete retake must not remove the existing official result.
    """

    candidates = [
        _candidate(
            candidate_id=1,
            student_id=101,
            candidate_number="A001",
            scripts=[
                _script(
                    script_id=11,
                    version=1,
                ),
                _script(
                    script_id=12,
                    version=2,
                ),
            ],
        ),
    ]

    await _patch_context(
        monkeypatch,
        candidates=candidates,
    )

    await _patch_candidate_results(
        monkeypatch,
        results_by_candidate_id={
            1: _candidate_result(
                candidate_id=1,
                student_id=101,
                latest=_latest_result(
                    candidate_id=1,
                    student_id=101,
                    script_id=12,
                    script_version=2,
                    mark=Decimal("25"),
                    percentage=Decimal("50"),
                    fully_finalised=False,
                ),
            ),
        },
    )

    await _patch_outcomes(
        monkeypatch,
        outcomes=[
            _outcome(
                outcome_id=1,
                candidate_id=1,
                script_id=11,
                script_version=1,
                mark=Decimal("40"),
                percentage=Decimal("80"),
                grade="8",
            ),
        ],
    )

    await _patch_questions(
        monkeypatch,
    )

    result = await service.get_assessment_analytics(
        db_session,
        teacher_user,
        100,
    )

    assert result["fully_finalised_candidate_count"] == 0

    assert result["excluded_incomplete_candidate_count"] == 1

    assert result["included_candidate_count"] == 1

    assert result["candidates_without_authoritative_result"] == 0

    assert result["mean_mark"] == Decimal("40.00")

    assert result["ranking"][0]["script_id"] == 11
    assert result["ranking"][0]["script_version"] == 1


@pytest.mark.asyncio
async def test_candidate_without_script_is_counted_but_not_included(
    db_session: AsyncSession,
    teacher_user,
    monkeypatch,
):
    candidates = [
        _candidate(
            candidate_id=1,
            student_id=101,
            candidate_number="A001",
            scripts=[],
        ),
    ]

    await _patch_context(
        monkeypatch,
        candidates=candidates,
    )

    await _patch_candidate_results(
        monkeypatch,
        results_by_candidate_id={},
    )

    await _patch_outcomes(
        monkeypatch,
        outcomes=[],
    )

    await _patch_questions(
        monkeypatch,
    )

    result = await service.get_assessment_analytics(
        db_session,
        teacher_user,
        100,
    )

    assert result["candidate_count"] == 1
    assert result["candidates_without_script"] == 1
    assert result["candidates_with_script"] == 0

    assert result["candidates_without_authoritative_result"] == 1

    assert result["included_candidate_count"] == 0
    assert result["mean_mark"] is None
    assert result["ranking"] == []


@pytest.mark.asyncio
async def test_authoritative_result_without_grade_remains_in_mark_statistics(
    db_session: AsyncSession,
    teacher_user,
    monkeypatch,
):
    candidates = [
        _candidate(
            candidate_id=1,
            student_id=101,
            candidate_number="A001",
            scripts=[
                _script(
                    script_id=11,
                    version=1,
                ),
            ],
        ),
    ]

    await _patch_context(
        monkeypatch,
        candidates=candidates,
    )

    await _patch_candidate_results(
        monkeypatch,
        results_by_candidate_id={
            1: _candidate_result(
                candidate_id=1,
                student_id=101,
                latest=_latest_result(
                    candidate_id=1,
                    student_id=101,
                    script_id=11,
                    script_version=1,
                    mark=Decimal("40"),
                    percentage=Decimal("80"),
                ),
            ),
        },
    )

    await _patch_outcomes(
        monkeypatch,
        outcomes=[
            _outcome(
                outcome_id=1,
                candidate_id=1,
                script_id=11,
                mark=Decimal("40"),
                percentage=Decimal("80"),
                grade=None,
                grade_points=None,
                is_pass=None,
            ),
        ],
    )

    await _patch_questions(
        monkeypatch,
    )

    result = await service.get_assessment_analytics(
        db_session,
        teacher_user,
        100,
    )

    assert result["included_candidate_count"] == 1

    assert result["mean_mark"] == Decimal("40.00")
    assert result["mean_percentage"] == Decimal("80.00")

    assert result["graded_candidate_count"] == 0
    assert result["ungraded_candidate_count"] == 1
    assert result["grade_distribution"] == []


@pytest.mark.asyncio
async def test_newer_retake_does_not_replace_authoritative_analytics_result(
    db_session: AsyncSession,
    teacher_user,
    monkeypatch,
):
    candidates = [
        _candidate(
            candidate_id=1,
            student_id=101,
            candidate_number="A001",
            scripts=[
                _script(
                    script_id=11,
                    version=1,
                ),
                _script(
                    script_id=12,
                    version=2,
                ),
            ],
        ),
    ]

    await _patch_context(
        monkeypatch,
        candidates=candidates,
    )

    await _patch_candidate_results(
        monkeypatch,
        results_by_candidate_id={
            1: _candidate_result(
                candidate_id=1,
                student_id=101,
                latest=_latest_result(
                    candidate_id=1,
                    student_id=101,
                    script_id=12,
                    script_version=2,
                    mark=Decimal("50"),
                    percentage=Decimal("100"),
                ),
            ),
        },
    )

    await _patch_outcomes(
        monkeypatch,
        outcomes=[
            _outcome(
                outcome_id=1,
                candidate_id=1,
                script_id=11,
                script_version=1,
                mark=Decimal("35"),
                percentage=Decimal("70"),
                grade="7",
                grade_points=Decimal("7"),
            ),
        ],
    )

    await _patch_questions(
        monkeypatch,
    )

    result = await service.get_assessment_analytics(
        db_session,
        teacher_user,
        100,
    )

    row = result["ranking"][0]

    assert row["script_id"] == 11
    assert row["script_version"] == 1
    assert row["mark_awarded"] == Decimal("35.00")
    assert row["percentage"] == Decimal("70.00")
    assert row["grade"] == "7"


@pytest.mark.asyncio
async def test_authoritative_remark_changes_formal_analytics(
    db_session: AsyncSession,
    teacher_user,
    monkeypatch,
):
    candidates = [
        _candidate(
            candidate_id=1,
            student_id=101,
            candidate_number="A001",
            scripts=[
                _script(
                    script_id=11,
                    version=1,
                ),
            ],
        ),
    ]

    await _patch_context(
        monkeypatch,
        candidates=candidates,
    )

    await _patch_candidate_results(
        monkeypatch,
        results_by_candidate_id={
            1: _candidate_result(
                candidate_id=1,
                student_id=101,
                latest=_latest_result(
                    candidate_id=1,
                    student_id=101,
                    script_id=11,
                    script_version=1,
                    mark=Decimal("42"),
                    percentage=Decimal("84"),
                ),
            ),
        },
    )

    await _patch_outcomes(
        monkeypatch,
        outcomes=[
            _outcome(
                outcome_id=2,
                candidate_id=1,
                script_id=11,
                script_version=1,
                mark=Decimal("42"),
                percentage=Decimal("84"),
                grade="9",
                grade_points=Decimal("9"),
                is_pass=True,
            ),
        ],
    )

    await _patch_questions(
        monkeypatch,
    )

    result = await service.get_assessment_analytics(
        db_session,
        teacher_user,
        100,
    )

    assert result["mean_mark"] == Decimal("42.00")
    assert result["mean_percentage"] == Decimal("84.00")
    assert result["ranking"][0]["grade"] == "9"


@pytest.mark.asyncio
async def test_snapshotted_grade_is_used_without_live_recalculation(
    db_session: AsyncSession,
    teacher_user,
    monkeypatch,
):
    candidates = [
        _candidate(
            candidate_id=1,
            student_id=101,
            candidate_number="A001",
            scripts=[
                _script(
                    script_id=11,
                    version=1,
                ),
            ],
        ),
    ]

    await _patch_context(
        monkeypatch,
        candidates=candidates,
    )

    await _patch_candidate_results(
        monkeypatch,
        results_by_candidate_id={
            1: _candidate_result(
                candidate_id=1,
                student_id=101,
                latest=_latest_result(
                    candidate_id=1,
                    student_id=101,
                    script_id=11,
                    script_version=1,
                    mark=Decimal("40"),
                    percentage=Decimal("80"),
                ),
            ),
        },
    )

    await _patch_outcomes(
        monkeypatch,
        outcomes=[
            _outcome(
                outcome_id=1,
                candidate_id=1,
                script_id=11,
                mark=Decimal("40"),
                percentage=Decimal("80"),
                grade="7",
                grade_points=Decimal("7"),
                is_pass=True,
            ),
        ],
    )

    await _patch_questions(
        monkeypatch,
    )

    result = await service.get_assessment_analytics(
        db_session,
        teacher_user,
        100,
    )

    assert result["ranking"][0]["grade"] == "7"

    assert result["grade_distribution"][0]["grade"] == "7"

    assert result["grade_distribution"][0]["grade_points"] == Decimal("7.00")


@pytest.mark.asyncio
async def test_pass_percentage_uses_only_authoritatively_classified_candidates(
    db_session: AsyncSession,
    teacher_user,
    monkeypatch,
):
    candidates = [
        _candidate(
            candidate_id=1,
            student_id=101,
            candidate_number="A001",
            scripts=[
                _script(
                    script_id=11,
                    version=1,
                ),
            ],
        ),
        _candidate(
            candidate_id=2,
            student_id=102,
            candidate_number="A002",
            scripts=[
                _script(
                    script_id=21,
                    version=1,
                ),
            ],
        ),
        _candidate(
            candidate_id=3,
            student_id=103,
            candidate_number="A003",
            scripts=[
                _script(
                    script_id=31,
                    version=1,
                ),
            ],
        ),
    ]

    await _patch_context(
        monkeypatch,
        candidates=candidates,
    )

    await _patch_candidate_results(
        monkeypatch,
        results_by_candidate_id={
            candidate.id: _candidate_result(
                candidate_id=candidate.id,
                student_id=candidate.student_id,
                latest=_latest_result(
                    candidate_id=candidate.id,
                    student_id=candidate.student_id,
                    script_id=candidate.scripts[0].id,
                    script_version=1,
                    mark=Decimal("30"),
                    percentage=Decimal("60"),
                ),
            )
            for candidate in candidates
        },
    )

    await _patch_outcomes(
        monkeypatch,
        outcomes=[
            _outcome(
                outcome_id=1,
                candidate_id=1,
                script_id=11,
                grade="6",
                is_pass=True,
            ),
            _outcome(
                outcome_id=2,
                candidate_id=2,
                script_id=21,
                grade="3",
                is_pass=False,
            ),
            _outcome(
                outcome_id=3,
                candidate_id=3,
                script_id=31,
                grade=None,
                grade_points=None,
                is_pass=None,
            ),
        ],
    )

    await _patch_questions(
        monkeypatch,
    )

    result = await service.get_assessment_analytics(
        db_session,
        teacher_user,
        100,
    )

    assert result["pass_count"] == 1
    assert result["fail_count"] == 1

    assert result["ungraded_candidate_count"] == 1

    assert result["pass_percentage"] == Decimal("50.00")


@pytest.mark.asyncio
async def test_authoritative_outcome_outside_candidate_set_is_rejected(
    db_session: AsyncSession,
    teacher_user,
    monkeypatch,
):
    candidates = [
        _candidate(
            candidate_id=1,
            student_id=101,
            candidate_number="A001",
            scripts=[
                _script(
                    script_id=11,
                    version=1,
                ),
            ],
        ),
    ]

    await _patch_context(
        monkeypatch,
        candidates=candidates,
    )

    await _patch_outcomes(
        monkeypatch,
        outcomes=[
            _outcome(
                outcome_id=99,
                candidate_id=999,
                script_id=9999,
            ),
        ],
    )

    await _patch_questions(
        monkeypatch,
    )

    with pytest.raises(
        HTTPException,
    ) as exc:
        await service.get_assessment_analytics(
            db_session,
            teacher_user,
            100,
        )

    assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_authoritative_outcome_without_loaded_script_is_rejected(
    db_session: AsyncSession,
    teacher_user,
    monkeypatch,
):
    candidates = [
        _candidate(
            candidate_id=1,
            student_id=101,
            candidate_number="A001",
            scripts=[],
        ),
    ]

    await _patch_context(
        monkeypatch,
        candidates=candidates,
    )

    await _patch_outcomes(
        monkeypatch,
        outcomes=[
            _outcome(
                outcome_id=1,
                candidate_id=1,
                script_id=11,
            ),
        ],
    )

    await _patch_questions(
        monkeypatch,
    )

    with pytest.raises(
        HTTPException,
    ) as exc:
        await service.get_assessment_analytics(
            db_session,
            teacher_user,
            100,
        )

    assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_existing_question_analysis_is_reused(
    db_session: AsyncSession,
    teacher_user,
    monkeypatch,
):
    candidates = []

    questions = [
        {
            "question_id": 10,
            "question_number": "2a",
            "title": "Momentum",
            "maximum_mark": Decimal("4.00"),
            "response_count": 8,
            "marked_count": 8,
            "mark_sum": Decimal("24.00"),
            "mark_average": Decimal("3.00"),
            "mark_minimum": Decimal("1.00"),
            "mark_maximum": Decimal("4.00"),
            "average_percentage": Decimal("75.00"),
        },
    ]

    await _patch_context(
        monkeypatch,
        candidates=candidates,
    )

    await _patch_candidate_results(
        monkeypatch,
        results_by_candidate_id={},
    )

    await _patch_outcomes(
        monkeypatch,
        outcomes=[],
    )

    await _patch_questions(
        monkeypatch,
        questions=questions,
    )

    result = await service.get_assessment_analytics(
        db_session,
        teacher_user,
        100,
    )

    assert result["questions"] == questions


# ---------------------------------------------------------------------------
# Derived views
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_analytics_summary_excludes_large_detail_sections(
    db_session: AsyncSession,
    teacher_user,
    monkeypatch,
):
    async def fake_analytics(
        *,
        db,
        current_user,
        assessment_id,
    ):
        return {
            "assessment_id": assessment_id,
            "mean_mark": Decimal("30.00"),
            "ranking": [
                {
                    "candidate_id": 1,
                },
            ],
            "questions": [
                {
                    "question_id": 1,
                },
            ],
        }

    monkeypatch.setattr(
        service,
        "get_assessment_analytics",
        fake_analytics,
    )

    result = await service.get_assessment_analytics_summary(
        db_session,
        teacher_user,
        100,
    )

    assert result == {
        "assessment_id": 100,
        "mean_mark": Decimal("30.00"),
    }


@pytest.mark.asyncio
async def test_ranking_view_returns_only_ranking(
    db_session: AsyncSession,
    teacher_user,
    monkeypatch,
):
    ranking = [
        {
            "candidate_id": 1,
            "rank": 1,
        },
        {
            "candidate_id": 2,
            "rank": 2,
        },
    ]

    async def fake_analytics(
        *,
        db,
        current_user,
        assessment_id,
    ):
        return {
            "ranking": ranking,
        }

    monkeypatch.setattr(
        service,
        "get_assessment_analytics",
        fake_analytics,
    )

    result = await service.get_assessment_candidate_ranking(
        db_session,
        teacher_user,
        100,
    )

    assert result == ranking


@pytest.mark.asyncio
async def test_grade_distribution_view_returns_compact_payload(
    db_session: AsyncSession,
    teacher_user,
    monkeypatch,
):
    async def fake_analytics(
        *,
        db,
        current_user,
        assessment_id,
    ):
        return {
            "assessment_id": assessment_id,
            "graded_candidate_count": 8,
            "ungraded_candidate_count": 2,
            "pass_count": 7,
            "fail_count": 1,
            "pass_percentage": Decimal("87.50"),
            "grade_distribution": [
                {
                    "grade": "9",
                    "count": 2,
                    "percentage": Decimal("25.00"),
                },
            ],
        }

    monkeypatch.setattr(
        service,
        "get_assessment_analytics",
        fake_analytics,
    )

    result = await service.get_assessment_grade_distribution(
        db_session,
        teacher_user,
        100,
    )

    assert result["assessment_id"] == 100
    assert result["graded_candidate_count"] == 8
    assert result["ungraded_candidate_count"] == 2
    assert result["pass_count"] == 7
    assert result["fail_count"] == 1

    assert result["pass_percentage"] == Decimal("87.50")

    assert result["grades"] == [
        {
            "grade": "9",
            "count": 2,
            "percentage": Decimal("25.00"),
        },
    ]
