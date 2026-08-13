from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

import app.services.assessment_trends_service as service

# ---------------------------------------------------------------------------
# Test-data helpers
# ---------------------------------------------------------------------------


def _subject(
    *,
    subject_id: int = 10,
    name: str = "Physics",
    code: str | None = "PHY",
):
    return SimpleNamespace(
        id=subject_id,
        name=name,
        code=code,
    )


def _course(
    *,
    course_id: int = 20,
    title: str = "OCR A Level Physics A",
    subject=None,
    exam_board: str | None = "OCR",
    qualification: str | None = "A Level",
    specification_code: str | None = "H556",
):
    subject_value = subject if subject is not None else _subject()

    return SimpleNamespace(
        id=course_id,
        title=title,
        subject_id=(subject_value.id if subject_value is not None else None),
        subject=subject_value,
        exam_board=exam_board,
        qualification=qualification,
        specification_code=specification_code,
    )


def _assessment(
    *,
    assessment_id: int,
    course=None,
    title: str | None = None,
    assessment_type: str | None = "end_of_topic_test",
    academic_year: str | None = "2026/27",
    term: str | None = "Autumn",
    scheduled_at: datetime | None = None,
):
    course_value = course if course is not None else _course()

    return SimpleNamespace(
        id=assessment_id,
        course_id=course_value.id,
        course=course_value,
        title=(title if title is not None else f"Assessment {assessment_id}"),
        assessment_type=assessment_type,
        academic_year=academic_year,
        term=term,
        scheduled_at=scheduled_at,
    )


def _candidate(
    *,
    candidate_id: int,
    student_id: int = 100,
    assessment=None,
    allocated_at: datetime | None = None,
    started_at: datetime | None = None,
    submitted_at: datetime | None = None,
):
    assessment_value = (
        assessment
        if assessment is not None
        else _assessment(
            assessment_id=candidate_id + 1000,
        )
    )

    return SimpleNamespace(
        id=candidate_id,
        student_id=student_id,
        assessment_id=assessment_value.id,
        assessment=assessment_value,
        allocated_at=(
            allocated_at
            if allocated_at is not None
            else datetime(
                2026,
                9,
                1,
                tzinfo=timezone.utc,
            )
        ),
        started_at=started_at,
        submitted_at=submitted_at,
    )


def _published_result(
    *,
    candidate_id: int,
    student_id: int = 100,
    assessment_id: int | None = None,
    mark_awarded: Decimal | None = Decimal("40.00"),
    percentage: Decimal | None = Decimal("80.00"),
    grade: str | None = "A",
    grade_points: Decimal | None = Decimal("5.00"),
    is_pass: bool | None = True,
    published_at: datetime | None = None,
):
    return {
        "assessment_id": (
            assessment_id if assessment_id is not None else candidate_id + 1000
        ),
        "candidate_id": candidate_id,
        "student_id": student_id,
        "candidate_number": f"C-{candidate_id}",
        "script_id": candidate_id + 2000,
        "script_version": 1,
        "mark_awarded": mark_awarded,
        "percentage": percentage,
        "grade": grade,
        "grade_points": grade_points,
        "is_pass": is_pass,
        "question_breakdown": None,
        "release_message": None,
        "published_at": (
            published_at
            if published_at is not None
            else datetime(
                2026,
                9,
                10,
                tzinfo=timezone.utc,
            )
        ),
        "visibility": {
            "include_mark": mark_awarded is not None,
            "include_percentage": percentage is not None,
            "include_grade": grade is not None,
            "include_question_breakdown": False,
        },
    }


def _student_user(
    *,
    user_id: int = 100,
):
    return SimpleNamespace(
        id=user_id,
    )


def _parent_user(
    *,
    user_id: int = 500,
    student_ids: list[int] | None = None,
):
    return SimpleNamespace(
        id=user_id,
        students=[
            SimpleNamespace(
                id=student_id,
            )
            for student_id in (student_ids or [100])
        ],
    )


def _patch_repository(
    monkeypatch,
    *,
    candidates,
    expected_student_id: int | None = None,
    expected_school_id: int | None = None,
):
    calls: list[dict] = []

    class FakeRepository:
        def __init__(
            self,
            db,
        ):
            self.db = db

        async def list_candidates_by_student(
            self,
            student_id,
            *,
            school_id=None,
            status=None,
            include_relationships=True,
        ):
            calls.append(
                {
                    "student_id": student_id,
                    "school_id": school_id,
                    "status": status,
                    "include_relationships": include_relationships,
                }
            )

            if expected_student_id is not None:
                assert student_id == expected_student_id

            if expected_school_id is not None:
                assert school_id == expected_school_id

            assert include_relationships is True

            return list(
                candidates,
            )

    monkeypatch.setattr(
        service,
        "AssessmentCandidateRepository",
        FakeRepository,
    )

    return calls


def _patch_student_results(
    monkeypatch,
    *,
    results_by_candidate_id,
):
    calls: list[int] = []

    async def fake_result(
        *,
        db,
        current_user,
        candidate_id,
    ):
        calls.append(
            candidate_id,
        )

        value = results_by_candidate_id[candidate_id]

        if isinstance(
            value,
            Exception,
        ):
            raise value

        return value

    monkeypatch.setattr(
        service,
        "get_student_published_assessment_result",
        fake_result,
    )

    return calls


def _patch_parent_results(
    monkeypatch,
    *,
    results_by_candidate_id,
):
    calls: list[int] = []

    async def fake_result(
        *,
        db,
        current_user,
        candidate_id,
    ):
        calls.append(
            candidate_id,
        )

        value = results_by_candidate_id[candidate_id]

        if isinstance(
            value,
            Exception,
        ):
            raise value

        return value

    monkeypatch.setattr(
        service,
        "get_parent_published_assessment_result",
        fake_result,
    )

    return calls


# ---------------------------------------------------------------------------
# Numeric helpers
# ---------------------------------------------------------------------------


def test_mean_returns_none_for_empty_values():
    assert service._mean([]) is None


def test_mean_rounds_to_two_decimal_places():
    result = service._mean(
        [
            Decimal("70"),
            Decimal("80"),
            Decimal("83"),
        ]
    )

    assert result == Decimal("77.67")


def test_round_decimal_uses_half_up():
    assert service._round_decimal(
        Decimal("1.235"),
    ) == Decimal("1.24")


# ---------------------------------------------------------------------------
# Date ordering
# ---------------------------------------------------------------------------


def test_candidate_date_prefers_scheduled_at():
    scheduled_at = datetime(
        2026,
        10,
        5,
        tzinfo=timezone.utc,
    )

    candidate = _candidate(
        candidate_id=1,
        assessment=_assessment(
            assessment_id=1001,
            scheduled_at=scheduled_at,
        ),
        submitted_at=datetime(
            2026,
            10,
            6,
            tzinfo=timezone.utc,
        ),
    )

    assert (
        service._candidate_assessment_datetime(
            candidate,
        )
        == scheduled_at
    )


def test_candidate_date_falls_back_to_submitted_at():
    submitted_at = datetime(
        2026,
        10,
        6,
        tzinfo=timezone.utc,
    )

    candidate = _candidate(
        candidate_id=1,
        assessment=_assessment(
            assessment_id=1001,
            scheduled_at=None,
        ),
        submitted_at=submitted_at,
    )

    assert (
        service._candidate_assessment_datetime(
            candidate,
        )
        == submitted_at
    )


def test_naive_candidate_datetime_is_normalised_to_utc():
    naive = datetime(
        2026,
        10,
        6,
        10,
        0,
    )

    candidate = _candidate(
        candidate_id=1,
        assessment=_assessment(
            assessment_id=1001,
            scheduled_at=naive,
        ),
    )

    result = service._candidate_assessment_datetime(
        candidate,
    )

    assert result.tzinfo is not None
    assert result.utcoffset() == timezone.utc.utcoffset(
        result,
    )


# ---------------------------------------------------------------------------
# Filtering
# ---------------------------------------------------------------------------


def test_candidate_matches_course_subject_year_and_term():
    subject = _subject(
        subject_id=10,
    )

    course = _course(
        course_id=20,
        subject=subject,
    )

    candidate = _candidate(
        candidate_id=1,
        assessment=_assessment(
            assessment_id=1001,
            course=course,
            academic_year="2026/27",
            term="Autumn",
        ),
    )

    assert service._candidate_matches_filters(
        candidate,
        course_id=20,
        subject_id=10,
        academic_year="2026/27",
        term="autumn",
    )


def test_candidate_filter_rejects_wrong_course():
    candidate = _candidate(
        candidate_id=1,
    )

    assert not service._candidate_matches_filters(
        candidate,
        course_id=999,
        subject_id=None,
        academic_year=None,
        term=None,
    )


def test_candidate_filter_rejects_wrong_subject():
    candidate = _candidate(
        candidate_id=1,
    )

    assert not service._candidate_matches_filters(
        candidate,
        course_id=None,
        subject_id=999,
        academic_year=None,
        term=None,
    )


def test_text_filters_are_case_insensitive():
    candidate = _candidate(
        candidate_id=1,
        assessment=_assessment(
            assessment_id=1001,
            academic_year="2026/27",
            term="Autumn",
        ),
    )

    assert service._candidate_matches_filters(
        candidate,
        course_id=None,
        subject_id=None,
        academic_year="2026/27",
        term="AUTUMN",
    )


# ---------------------------------------------------------------------------
# Movement calculations
# ---------------------------------------------------------------------------


def test_percentage_movements_are_chronological():
    points = [
        {
            "percentage": Decimal("60.00"),
        },
        {
            "percentage": Decimal("70.00"),
        },
        {
            "percentage": Decimal("65.00"),
        },
    ]

    service._add_percentage_movements(
        points,
    )

    assert points[0]["percentage_change"] is None
    assert points[1]["percentage_change"] == Decimal("10.00")
    assert points[2]["percentage_change"] == Decimal("-5.00")


def test_hidden_percentage_does_not_change_previous_visible_value():
    points = [
        {
            "percentage": Decimal("60.00"),
        },
        {
            "percentage": None,
        },
        {
            "percentage": Decimal("75.00"),
        },
    ]

    service._add_percentage_movements(
        points,
    )

    assert points[1]["percentage_change"] is None

    assert points[2]["percentage_change"] == Decimal("15.00")


def test_percentage_summary_ignores_hidden_percentages():
    result = service._calculate_percentage_summary(
        [
            {
                "percentage": Decimal("60"),
            },
            {
                "percentage": None,
            },
            {
                "percentage": Decimal("80"),
            },
        ]
    )

    assert result["percentage_result_count"] == 2
    assert result["average_percentage"] == Decimal("70.00")
    assert result["first_percentage"] == Decimal("60")
    assert result["latest_percentage"] == Decimal("80")
    assert result["overall_percentage_change"] == Decimal("20.00")
    assert result["highest_percentage"] == Decimal("80")
    assert result["lowest_percentage"] == Decimal("60")


def test_grade_points_summary_calculates_change():
    result = service._calculate_grade_points_summary(
        [
            {
                "grade_points": Decimal("4"),
            },
            {
                "grade_points": Decimal("5"),
            },
            {
                "grade_points": Decimal("6"),
            },
        ]
    )

    assert result["grade_points_result_count"] == 3
    assert result["average_grade_points"] == Decimal("5.00")
    assert result["first_grade_points"] == Decimal("4")
    assert result["latest_grade_points"] == Decimal("6")
    assert result["overall_grade_points_change"] == Decimal("2.00")


# ---------------------------------------------------------------------------
# Student trend
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_student_trend_returns_published_results_chronologically(
    db_session: AsyncSession,
    monkeypatch,
):
    student = _student_user()

    early = _candidate(
        candidate_id=1,
        student_id=student.id,
        assessment=_assessment(
            assessment_id=1001,
            title="Forces Test",
            scheduled_at=datetime(
                2026,
                9,
                10,
                tzinfo=timezone.utc,
            ),
        ),
    )

    late = _candidate(
        candidate_id=2,
        student_id=student.id,
        assessment=_assessment(
            assessment_id=1002,
            title="Momentum Test",
            scheduled_at=datetime(
                2026,
                10,
                10,
                tzinfo=timezone.utc,
            ),
        ),
    )

    # Repository deliberately returns newest first.
    _patch_repository(
        monkeypatch,
        candidates=[
            late,
            early,
        ],
        expected_student_id=student.id,
    )

    _patch_student_results(
        monkeypatch,
        results_by_candidate_id={
            1: _published_result(
                candidate_id=1,
                student_id=student.id,
                assessment_id=1001,
                percentage=Decimal("60"),
            ),
            2: _published_result(
                candidate_id=2,
                student_id=student.id,
                assessment_id=1002,
                percentage=Decimal("80"),
            ),
        },
    )

    result = await service.get_student_assessment_trend(
        db_session,
        student,
    )

    assert result["student_id"] == student.id
    assert result["audience"] == "student"
    assert result["assessment_count"] == 2

    assert [point["assessment_id"] for point in result["points"]] == [
        1001,
        1002,
    ]

    assert result["average_percentage"] == Decimal("70.00")

    assert result["overall_percentage_change"] == Decimal("20.00")

    assert result["points"][1]["percentage_change"] == Decimal("20.00")


@pytest.mark.asyncio
async def test_student_trend_skips_unpublished_result(
    db_session: AsyncSession,
    monkeypatch,
):
    student = _student_user()

    candidates = [
        _candidate(
            candidate_id=1,
            student_id=student.id,
        ),
        _candidate(
            candidate_id=2,
            student_id=student.id,
        ),
    ]

    _patch_repository(
        monkeypatch,
        candidates=candidates,
    )

    _patch_student_results(
        monkeypatch,
        results_by_candidate_id={
            1: _published_result(
                candidate_id=1,
                student_id=student.id,
            ),
            2: HTTPException(
                status_code=404,
                detail="Published assessment result not found.",
            ),
        },
    )

    result = await service.get_student_assessment_trend(
        db_session,
        student,
    )

    assert result["assessment_count"] == 1
    assert len(result["points"]) == 1
    assert result["points"][0]["candidate_id"] == 1


@pytest.mark.asyncio
async def test_student_trend_propagates_non_404_result_error(
    db_session: AsyncSession,
    monkeypatch,
):
    student = _student_user()

    _patch_repository(
        monkeypatch,
        candidates=[
            _candidate(
                candidate_id=1,
                student_id=student.id,
            ),
        ],
    )

    _patch_student_results(
        monkeypatch,
        results_by_candidate_id={
            1: HTTPException(
                status_code=403,
                detail="Forbidden.",
            ),
        },
    )

    with pytest.raises(
        HTTPException,
    ) as exc:
        await service.get_student_assessment_trend(
            db_session,
            student,
        )

    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_student_trend_preserves_hidden_percentage(
    db_session: AsyncSession,
    monkeypatch,
):
    student = _student_user()

    _patch_repository(
        monkeypatch,
        candidates=[
            _candidate(
                candidate_id=1,
                student_id=student.id,
            ),
        ],
    )

    _patch_student_results(
        monkeypatch,
        results_by_candidate_id={
            1: _published_result(
                candidate_id=1,
                student_id=student.id,
                percentage=None,
            ),
        },
    )

    result = await service.get_student_assessment_trend(
        db_session,
        student,
    )

    assert result["assessment_count"] == 1
    assert result["percentage_result_count"] == 0
    assert result["average_percentage"] is None
    assert result["points"][0]["percentage"] is None


@pytest.mark.asyncio
async def test_student_trend_passes_school_scope_to_repository(
    db_session: AsyncSession,
    monkeypatch,
):
    student = _student_user()

    calls = _patch_repository(
        monkeypatch,
        candidates=[],
        expected_student_id=student.id,
        expected_school_id=7,
    )

    _patch_student_results(
        monkeypatch,
        results_by_candidate_id={},
    )

    result = await service.get_student_assessment_trend(
        db_session,
        student,
        school_id=7,
    )

    assert result["assessment_count"] == 0
    assert calls[0]["school_id"] == 7


@pytest.mark.asyncio
async def test_student_trend_applies_course_filter_before_result_lookup(
    db_session: AsyncSession,
    monkeypatch,
):
    student = _student_user()

    course_a = _course(
        course_id=20,
    )

    course_b = _course(
        course_id=21,
    )

    candidates = [
        _candidate(
            candidate_id=1,
            student_id=student.id,
            assessment=_assessment(
                assessment_id=1001,
                course=course_a,
            ),
        ),
        _candidate(
            candidate_id=2,
            student_id=student.id,
            assessment=_assessment(
                assessment_id=1002,
                course=course_b,
            ),
        ),
    ]

    _patch_repository(
        monkeypatch,
        candidates=candidates,
    )

    result_calls = _patch_student_results(
        monkeypatch,
        results_by_candidate_id={
            1: _published_result(
                candidate_id=1,
                student_id=student.id,
            ),
            2: _published_result(
                candidate_id=2,
                student_id=student.id,
            ),
        },
    )

    result = await service.get_student_assessment_trend(
        db_session,
        student,
        course_id=20,
    )

    assert result["assessment_count"] == 1
    assert result["points"][0]["course_id"] == 20

    assert result_calls == [1]


@pytest.mark.asyncio
async def test_student_trend_applies_subject_filter(
    db_session: AsyncSession,
    monkeypatch,
):
    student = _student_user()

    physics = _subject(
        subject_id=10,
        name="Physics",
    )

    chemistry = _subject(
        subject_id=11,
        name="Chemistry",
    )

    candidates = [
        _candidate(
            candidate_id=1,
            student_id=student.id,
            assessment=_assessment(
                assessment_id=1001,
                course=_course(
                    course_id=20,
                    subject=physics,
                ),
            ),
        ),
        _candidate(
            candidate_id=2,
            student_id=student.id,
            assessment=_assessment(
                assessment_id=1002,
                course=_course(
                    course_id=21,
                    subject=chemistry,
                ),
            ),
        ),
    ]

    _patch_repository(
        monkeypatch,
        candidates=candidates,
    )

    result_calls = _patch_student_results(
        monkeypatch,
        results_by_candidate_id={
            1: _published_result(
                candidate_id=1,
                student_id=student.id,
            ),
            2: _published_result(
                candidate_id=2,
                student_id=student.id,
            ),
        },
    )

    result = await service.get_student_assessment_trend(
        db_session,
        student,
        subject_id=10,
    )

    assert result["assessment_count"] == 1
    assert result["points"][0]["subject_name"] == "Physics"
    assert result_calls == [1]


@pytest.mark.asyncio
async def test_student_trend_normalises_year_and_term_filters(
    db_session: AsyncSession,
    monkeypatch,
):
    student = _student_user()

    candidate = _candidate(
        candidate_id=1,
        student_id=student.id,
        assessment=_assessment(
            assessment_id=1001,
            academic_year="2026/27",
            term="Autumn",
        ),
    )

    _patch_repository(
        monkeypatch,
        candidates=[
            candidate,
        ],
    )

    _patch_student_results(
        monkeypatch,
        results_by_candidate_id={
            1: _published_result(
                candidate_id=1,
                student_id=student.id,
            ),
        },
    )

    result = await service.get_student_assessment_trend(
        db_session,
        student,
        academic_year=" 2026/27 ",
        term=" autumn ",
    )

    assert result["assessment_count"] == 1

    assert result["filters"]["academic_year"] == "2026/27"
    assert result["filters"]["term"] == "autumn"


# ---------------------------------------------------------------------------
# Trend-point metadata
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_trend_point_contains_course_and_subject_metadata(
    db_session: AsyncSession,
    monkeypatch,
):
    student = _student_user()

    physics = _subject(
        subject_id=10,
        name="Physics",
        code="PHY",
    )

    course = _course(
        course_id=20,
        title="OCR A Level Physics A",
        subject=physics,
        exam_board="OCR",
        qualification="A Level",
        specification_code="H556",
    )

    candidate = _candidate(
        candidate_id=1,
        student_id=student.id,
        assessment=_assessment(
            assessment_id=1001,
            course=course,
            title="Mechanics Test",
        ),
    )

    _patch_repository(
        monkeypatch,
        candidates=[
            candidate,
        ],
    )

    _patch_student_results(
        monkeypatch,
        results_by_candidate_id={
            1: _published_result(
                candidate_id=1,
                student_id=student.id,
            ),
        },
    )

    result = await service.get_student_assessment_trend(
        db_session,
        student,
    )

    point = result["points"][0]

    assert point["assessment_title"] == "Mechanics Test"
    assert point["course_id"] == 20
    assert point["course_title"] == "OCR A Level Physics A"
    assert point["subject_id"] == 10
    assert point["subject_name"] == "Physics"
    assert point["subject_code"] == "PHY"
    assert point["exam_board"] == "OCR"
    assert point["qualification"] == "A Level"
    assert point["specification_code"] == "H556"


# ---------------------------------------------------------------------------
# Parent trend
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_parent_can_view_linked_child_trend(
    db_session: AsyncSession,
    monkeypatch,
):
    parent = _parent_user(
        student_ids=[
            100,
        ],
    )

    candidate = _candidate(
        candidate_id=1,
        student_id=100,
    )

    _patch_repository(
        monkeypatch,
        candidates=[
            candidate,
        ],
        expected_student_id=100,
    )

    calls = _patch_parent_results(
        monkeypatch,
        results_by_candidate_id={
            1: _published_result(
                candidate_id=1,
                student_id=100,
            ),
        },
    )

    result = await service.get_parent_student_assessment_trend(
        db_session,
        parent,
        student_id=100,
    )

    assert result["student_id"] == 100
    assert result["audience"] == "parent"
    assert result["assessment_count"] == 1
    assert calls == [1]


@pytest.mark.asyncio
async def test_parent_cannot_view_unlinked_child_trend(
    db_session: AsyncSession,
):
    parent = _parent_user(
        student_ids=[
            100,
        ],
    )

    with pytest.raises(
        HTTPException,
    ) as exc:
        await service.get_parent_student_assessment_trend(
            db_session,
            parent,
            student_id=999,
        )

    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_parent_student_link_object_is_supported(
    db_session: AsyncSession,
    monkeypatch,
):
    parent = SimpleNamespace(
        id=500,
        parent_students=[
            SimpleNamespace(
                student_id=100,
            ),
        ],
    )

    _patch_repository(
        monkeypatch,
        candidates=[],
        expected_student_id=100,
    )

    _patch_parent_results(
        monkeypatch,
        results_by_candidate_id={},
    )

    result = await service.get_parent_student_assessment_trend(
        db_session,
        parent,
        student_id=100,
    )

    assert result["student_id"] == 100
    assert result["assessment_count"] == 0


@pytest.mark.asyncio
async def test_parent_trend_skips_parent_hidden_result(
    db_session: AsyncSession,
    monkeypatch,
):
    parent = _parent_user()

    candidates = [
        _candidate(
            candidate_id=1,
            student_id=100,
        ),
        _candidate(
            candidate_id=2,
            student_id=100,
        ),
    ]

    _patch_repository(
        monkeypatch,
        candidates=candidates,
    )

    _patch_parent_results(
        monkeypatch,
        results_by_candidate_id={
            1: _published_result(
                candidate_id=1,
                student_id=100,
            ),
            2: HTTPException(
                status_code=404,
                detail="Published assessment result not found.",
            ),
        },
    )

    result = await service.get_parent_student_assessment_trend(
        db_session,
        parent,
        student_id=100,
    )

    assert result["assessment_count"] == 1


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_parent_trend_rejects_non_positive_student_id(
    db_session: AsyncSession,
):
    parent = _parent_user()

    with pytest.raises(
        HTTPException,
    ) as exc:
        await service.get_parent_student_assessment_trend(
            db_session,
            parent,
            student_id=0,
        )

    assert exc.value.status_code == 422


@pytest.mark.asyncio
async def test_student_trend_rejects_non_positive_school_id(
    db_session: AsyncSession,
):
    student = _student_user()

    with pytest.raises(
        HTTPException,
    ) as exc:
        await service.get_student_assessment_trend(
            db_session,
            student,
            school_id=0,
        )

    assert exc.value.status_code == 422


@pytest.mark.asyncio
async def test_student_trend_rejects_non_positive_course_id(
    db_session: AsyncSession,
):
    student = _student_user()

    with pytest.raises(
        HTTPException,
    ) as exc:
        await service.get_student_assessment_trend(
            db_session,
            student,
            course_id=-1,
        )

    assert exc.value.status_code == 422


@pytest.mark.asyncio
async def test_student_trend_rejects_non_positive_subject_id(
    db_session: AsyncSession,
):
    student = _student_user()

    with pytest.raises(
        HTTPException,
    ) as exc:
        await service.get_student_assessment_trend(
            db_session,
            student,
            subject_id=0,
        )

    assert exc.value.status_code == 422
