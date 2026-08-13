from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

import app.services.assessment_cohort_performance_service as service
from app.models.user import UserRole

# ---------------------------------------------------------------------------
# Test-data helpers
# ---------------------------------------------------------------------------


def _user(
    *,
    user_id: int,
    school_id: int | None,
    roles: list[str],
):
    return SimpleNamespace(
        id=user_id,
        school_id=school_id,
        roles=roles,
    )


def _teacher_user(
    *,
    user_id: int = 10,
    school_id: int = 1,
):
    return _user(
        user_id=user_id,
        school_id=school_id,
        roles=[UserRole.TEACHER.value],
    )


def _school_admin_user(
    *,
    user_id: int = 20,
    school_id: int = 1,
):
    return _user(
        user_id=user_id,
        school_id=school_id,
        roles=[UserRole.SCHOOL_ADMIN.value],
    )


def _platform_admin_user(
    *,
    user_id: int = 30,
):
    return _user(
        user_id=user_id,
        school_id=None,
        roles=[UserRole.PLATFORM_ADMIN.value],
    )


def _student_user(
    *,
    user_id: int = 40,
    school_id: int = 1,
):
    return _user(
        user_id=user_id,
        school_id=school_id,
        roles=[UserRole.STUDENT.value],
    )


def _subject(
    *,
    subject_id: int = 100,
    name: str = "Physics",
):
    return SimpleNamespace(
        id=subject_id,
        name=name,
    )


def _course(
    *,
    course_id: int,
    school_id: int = 1,
    teacher_id: int = 10,
    title: str | None = None,
    subject=None,
):
    subject_value = subject if subject is not None else _subject()

    return SimpleNamespace(
        id=course_id,
        school_id=school_id,
        teacher_id=teacher_id,
        title=(title if title is not None else f"Course {course_id}"),
        subject_id=(subject_value.id if subject_value is not None else None),
        subject=subject_value,
    )


def _assessment(
    *,
    assessment_id: int,
    school_id: int = 1,
    course=None,
    title: str | None = None,
    academic_year: str | None = "2026/27",
    term: str | None = "Autumn",
    assessment_type: str | None = "end_of_topic_test",
    scheduled_at: datetime | None = None,
):
    course_value = (
        course
        if course is not None
        else _course(
            course_id=assessment_id + 100,
        )
    )

    return SimpleNamespace(
        id=assessment_id,
        school_id=school_id,
        course_id=course_value.id,
        course=course_value,
        title=(title if title is not None else f"Assessment {assessment_id}"),
        assessment_type=assessment_type,
        academic_year=academic_year,
        term=term,
        scheduled_at=scheduled_at,
    )


def _ranking_row(
    *,
    candidate_id: int,
    student_id: int,
    percentage: Decimal | None,
    mark_awarded: Decimal | None = None,
    grade: str | None = None,
    is_pass: bool | None = None,
):
    return {
        "candidate_id": candidate_id,
        "student_id": student_id,
        "candidate_number": f"C-{candidate_id}",
        "candidate_status": "submitted",
        "script_id": candidate_id + 1000,
        "script_version": 1,
        "mark_awarded": (
            mark_awarded
            if mark_awarded is not None
            else (percentage / Decimal("2") if percentage is not None else None)
        ),
        "maximum_mark": Decimal("50.00"),
        "percentage": percentage,
        "grade": grade,
        "grade_points": None,
        "is_pass": is_pass,
        "rank": 1,
    }


def _analytics(
    *,
    assessment_id: int,
    candidate_count: int,
    included_count: int,
    excluded_count: int = 0,
    ranking=None,
    graded_count: int = 0,
    ungraded_count: int = 0,
    pass_count: int = 0,
    fail_count: int = 0,
):
    ranking_rows = list(
        ranking or [],
    )

    percentages = [
        row["percentage"] for row in ranking_rows if row.get("percentage") is not None
    ]

    return {
        "assessment_id": assessment_id,
        "title": f"Assessment {assessment_id}",
        "status": "published",
        "result_stage": "finalised",
        "script_selection": "latest",
        "maximum_mark": Decimal("50.00"),
        "markable_question_count": 5,
        "candidate_count": candidate_count,
        "script_count": candidate_count,
        "candidates_with_script": candidate_count,
        "candidates_without_script": 0,
        "fully_marked_candidate_count": included_count,
        "fully_finalised_candidate_count": included_count,
        "included_candidate_count": included_count,
        "excluded_incomplete_candidate_count": excluded_count,
        "candidate_inclusion_percentage": (
            Decimal("100.00")
            if candidate_count == included_count and candidate_count > 0
            else None
        ),
        "marking_completion_percentage": Decimal("100.00"),
        "finalisation_completion_percentage": Decimal("100.00"),
        "mean_mark": None,
        "median_mark": None,
        "lowest_mark": None,
        "highest_mark": None,
        "mean_percentage": (
            service._mean(
                percentages,
            )
            if percentages
            else None
        ),
        "median_percentage": (
            service._median(
                percentages,
            )
            if percentages
            else None
        ),
        "lowest_percentage": (min(percentages) if percentages else None),
        "highest_percentage": (max(percentages) if percentages else None),
        "graded_candidate_count": graded_count,
        "ungraded_candidate_count": ungraded_count,
        "pass_count": pass_count,
        "fail_count": fail_count,
        "pass_percentage": (
            service._percentage(
                pass_count,
                pass_count + fail_count,
            )
            if pass_count + fail_count > 0
            else None
        ),
        "grade_distribution": [],
        "ranking": ranking_rows,
        "questions": [],
    }


def _patch_assessment_repository(
    monkeypatch,
    *,
    assessments,
):
    calls: list[dict] = []

    class FakeRepository:
        def __init__(
            self,
            db,
        ):
            self.db = db

        async def list_by_school(
            self,
            school_id,
            *,
            course_id=None,
            created_by_id=None,
            status=None,
            academic_year=None,
            term=None,
            include_relationships=True,
        ):
            calls.append(
                {
                    "method": "list_by_school",
                    "school_id": school_id,
                    "course_id": course_id,
                    "created_by_id": created_by_id,
                    "status": status,
                    "academic_year": academic_year,
                    "term": term,
                    "include_relationships": include_relationships,
                }
            )

            result = [
                assessment
                for assessment in assessments
                if assessment.school_id == school_id
            ]

            if course_id is not None:
                result = [
                    assessment
                    for assessment in result
                    if assessment.course_id == course_id
                ]

            if academic_year is not None:
                result = [
                    assessment
                    for assessment in result
                    if assessment.academic_year == academic_year
                ]

            if term is not None:
                result = [
                    assessment for assessment in result if assessment.term == term
                ]

            return result

        async def list_all(
            self,
            *,
            status=None,
            include_relationships=True,
        ):
            calls.append(
                {
                    "method": "list_all",
                    "status": status,
                    "include_relationships": include_relationships,
                }
            )

            return list(
                assessments,
            )

    monkeypatch.setattr(
        service,
        "AssessmentRepository",
        FakeRepository,
    )

    return calls


def _patch_analytics(
    monkeypatch,
    *,
    analytics_by_assessment_id,
):
    calls: list[int] = []

    async def fake_analytics(
        *,
        db,
        current_user,
        assessment_id,
    ):
        calls.append(
            assessment_id,
        )

        value = analytics_by_assessment_id[assessment_id]

        if isinstance(
            value,
            Exception,
        ):
            raise value

        return value

    monkeypatch.setattr(
        service,
        "get_assessment_analytics",
        fake_analytics,
    )

    return calls


# ---------------------------------------------------------------------------
# Numeric helpers
# ---------------------------------------------------------------------------


def test_mean_returns_none_for_empty_values():
    assert service._mean([]) is None


def test_mean_uses_candidate_values():
    assert service._mean(
        [
            Decimal("60"),
            Decimal("70"),
            Decimal("80"),
        ]
    ) == Decimal("70.00")


def test_median_handles_even_number_of_values():
    assert service._median(
        [
            Decimal("50"),
            Decimal("60"),
            Decimal("70"),
            Decimal("90"),
        ]
    ) == Decimal("65.00")


def test_percentage_returns_none_for_zero_denominator():
    assert (
        service._percentage(
            1,
            0,
        )
        is None
    )


# ---------------------------------------------------------------------------
# Roles and validation
# ---------------------------------------------------------------------------


def test_student_role_cannot_access_cohort_performance():
    student = _student_user()

    with pytest.raises(
        HTTPException,
    ) as exc:
        service._ensure_cohort_staff_role(
            student,
        )

    assert exc.value.status_code == 403


def test_teacher_role_is_allowed():
    service._ensure_cohort_staff_role(
        _teacher_user(),
    )


def test_school_admin_role_is_allowed():
    service._ensure_cohort_staff_role(
        _school_admin_user(),
    )


def test_platform_admin_role_is_allowed():
    service._ensure_cohort_staff_role(
        _platform_admin_user(),
    )


@pytest.mark.parametrize(
    "value",
    [
        0,
        -1,
        True,
    ],
)
def test_optional_positive_integer_validation_rejects_invalid_values(
    value,
):
    with pytest.raises(
        HTTPException,
    ) as exc:
        service._validate_optional_positive_integer(
            value,
            field_name="course_id",
        )

    assert exc.value.status_code == 422


def test_optional_text_normalises_blank_to_none():
    assert (
        service._normalise_optional_text(
            "   ",
            field_name="term",
            max_length=100,
        )
        is None
    )


# ---------------------------------------------------------------------------
# Assessment scope
# ---------------------------------------------------------------------------


def test_teacher_can_only_match_own_course():
    teacher = _teacher_user(
        user_id=10,
    )

    own = _assessment(
        assessment_id=1,
        course=_course(
            course_id=101,
            teacher_id=10,
        ),
    )

    other = _assessment(
        assessment_id=2,
        course=_course(
            course_id=102,
            teacher_id=99,
        ),
    )

    assert service._assessment_matches_scope(
        own,
        teacher,
        subject_id=None,
        teacher_id=None,
    )

    assert not service._assessment_matches_scope(
        other,
        teacher,
        subject_id=None,
        teacher_id=None,
    )


def test_school_admin_can_match_other_teachers_course():
    admin = _school_admin_user()

    assessment = _assessment(
        assessment_id=1,
        course=_course(
            course_id=101,
            teacher_id=99,
        ),
    )

    assert service._assessment_matches_scope(
        assessment,
        admin,
        subject_id=None,
        teacher_id=None,
    )


def test_subject_filter_is_applied():
    teacher = _teacher_user()

    assessment = _assessment(
        assessment_id=1,
        course=_course(
            course_id=101,
            teacher_id=teacher.id,
            subject=_subject(
                subject_id=200,
                name="Chemistry",
            ),
        ),
    )

    assert service._assessment_matches_scope(
        assessment,
        teacher,
        subject_id=200,
        teacher_id=None,
    )

    assert not service._assessment_matches_scope(
        assessment,
        teacher,
        subject_id=201,
        teacher_id=None,
    )


# ---------------------------------------------------------------------------
# Accessible assessment listing
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_teacher_school_scope_is_forced_to_own_school(
    db_session: AsyncSession,
    monkeypatch,
):
    teacher = _teacher_user(
        school_id=1,
    )

    assessment = _assessment(
        assessment_id=1,
        school_id=1,
        course=_course(
            course_id=101,
            school_id=1,
            teacher_id=teacher.id,
        ),
    )

    calls = _patch_assessment_repository(
        monkeypatch,
        assessments=[
            assessment,
        ],
    )

    school_id, assessments = await service._list_accessible_assessments(
        db_session,
        teacher,
        school_id=None,
        course_id=None,
        subject_id=None,
        teacher_id=None,
        academic_year=None,
        term=None,
    )

    assert school_id == 1
    assert assessments == [assessment]
    assert calls[0]["method"] == "list_by_school"
    assert calls[0]["school_id"] == 1


@pytest.mark.asyncio
async def test_school_scoped_user_cannot_request_other_school(
    db_session: AsyncSession,
    monkeypatch,
):
    teacher = _teacher_user(
        school_id=1,
    )

    _patch_assessment_repository(
        monkeypatch,
        assessments=[],
    )

    with pytest.raises(
        HTTPException,
    ) as exc:
        await service._list_accessible_assessments(
            db_session,
            teacher,
            school_id=2,
            course_id=None,
            subject_id=None,
            teacher_id=None,
            academic_year=None,
            term=None,
        )

    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_platform_admin_without_school_uses_list_all(
    db_session: AsyncSession,
    monkeypatch,
):
    admin = _platform_admin_user()

    assessment = _assessment(
        assessment_id=1,
        school_id=2,
        course=_course(
            course_id=101,
            school_id=2,
            teacher_id=99,
        ),
    )

    calls = _patch_assessment_repository(
        monkeypatch,
        assessments=[
            assessment,
        ],
    )

    school_id, assessments = await service._list_accessible_assessments(
        db_session,
        admin,
        school_id=None,
        course_id=None,
        subject_id=None,
        teacher_id=None,
        academic_year=None,
        term=None,
    )

    assert school_id is None
    assert assessments == [assessment]
    assert calls[0]["method"] == "list_all"


@pytest.mark.asyncio
async def test_teacher_filter_applies_before_analytics(
    db_session: AsyncSession,
    monkeypatch,
):
    admin = _school_admin_user()

    assessments = [
        _assessment(
            assessment_id=1,
            course=_course(
                course_id=101,
                teacher_id=10,
            ),
        ),
        _assessment(
            assessment_id=2,
            course=_course(
                course_id=102,
                teacher_id=11,
            ),
        ),
    ]

    _patch_assessment_repository(
        monkeypatch,
        assessments=assessments,
    )

    _, result = await service._list_accessible_assessments(
        db_session,
        admin,
        school_id=None,
        course_id=None,
        subject_id=None,
        teacher_id=11,
        academic_year=None,
        term=None,
    )

    assert [assessment.id for assessment in result] == [2]


# ---------------------------------------------------------------------------
# Grade aggregation
# ---------------------------------------------------------------------------


def test_cohort_grade_distribution_aggregates_labels():
    rows = [
        {
            "grade": "A",
        },
        {
            "grade": "A",
        },
        {
            "grade": "B",
        },
        {
            "grade": None,
        },
    ]

    distribution = service._build_cohort_grade_distribution(
        rows,
    )

    assert distribution == [
        {
            "grade": "A",
            "count": 2,
            "percentage": Decimal("66.67"),
        },
        {
            "grade": "B",
            "count": 1,
            "percentage": Decimal("33.33"),
        },
    ]


# ---------------------------------------------------------------------------
# Core aggregation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cohort_uses_individual_candidate_percentages_not_average_of_averages(
    db_session: AsyncSession,
    monkeypatch,
):
    admin = _school_admin_user()

    a1 = _assessment(
        assessment_id=1,
        scheduled_at=datetime(
            2026,
            9,
            1,
            tzinfo=timezone.utc,
        ),
    )

    a2 = _assessment(
        assessment_id=2,
        scheduled_at=datetime(
            2026,
            10,
            1,
            tzinfo=timezone.utc,
        ),
    )

    _patch_assessment_repository(
        monkeypatch,
        assessments=[
            a1,
            a2,
        ],
    )

    _patch_analytics(
        monkeypatch,
        analytics_by_assessment_id={
            1: _analytics(
                assessment_id=1,
                candidate_count=1,
                included_count=1,
                ranking=[
                    _ranking_row(
                        candidate_id=1,
                        student_id=101,
                        percentage=Decimal("100"),
                    ),
                ],
            ),
            2: _analytics(
                assessment_id=2,
                candidate_count=3,
                included_count=3,
                ranking=[
                    _ranking_row(
                        candidate_id=2,
                        student_id=102,
                        percentage=Decimal("0"),
                    ),
                    _ranking_row(
                        candidate_id=3,
                        student_id=103,
                        percentage=Decimal("0"),
                    ),
                    _ranking_row(
                        candidate_id=4,
                        student_id=104,
                        percentage=Decimal("0"),
                    ),
                ],
            ),
        },
    )

    result = await service.get_assessment_cohort_performance(
        db_session,
        admin,
    )

    # Averaging assessment means would incorrectly give 50%.
    # Individual candidate weighting gives 25%.
    assert result["mean_percentage"] == Decimal("25.00")
    assert result["included_result_count"] == 4


@pytest.mark.asyncio
async def test_cohort_calculates_median_high_low(
    db_session: AsyncSession,
    monkeypatch,
):
    admin = _school_admin_user()

    assessment = _assessment(
        assessment_id=1,
    )

    _patch_assessment_repository(
        monkeypatch,
        assessments=[
            assessment,
        ],
    )

    _patch_analytics(
        monkeypatch,
        analytics_by_assessment_id={
            1: _analytics(
                assessment_id=1,
                candidate_count=4,
                included_count=4,
                ranking=[
                    _ranking_row(
                        candidate_id=1,
                        student_id=101,
                        percentage=Decimal("40"),
                    ),
                    _ranking_row(
                        candidate_id=2,
                        student_id=102,
                        percentage=Decimal("60"),
                    ),
                    _ranking_row(
                        candidate_id=3,
                        student_id=103,
                        percentage=Decimal("80"),
                    ),
                    _ranking_row(
                        candidate_id=4,
                        student_id=104,
                        percentage=Decimal("100"),
                    ),
                ],
            ),
        },
    )

    result = await service.get_assessment_cohort_performance(
        db_session,
        admin,
    )

    assert result["mean_percentage"] == Decimal("70.00")
    assert result["median_percentage"] == Decimal("70.00")
    assert result["lowest_percentage"] == Decimal("40.00")
    assert result["highest_percentage"] == Decimal("100.00")


@pytest.mark.asyncio
async def test_unique_student_count_deduplicates_across_assessments(
    db_session: AsyncSession,
    monkeypatch,
):
    admin = _school_admin_user()

    assessments = [
        _assessment(
            assessment_id=1,
        ),
        _assessment(
            assessment_id=2,
        ),
    ]

    _patch_assessment_repository(
        monkeypatch,
        assessments=assessments,
    )

    _patch_analytics(
        monkeypatch,
        analytics_by_assessment_id={
            1: _analytics(
                assessment_id=1,
                candidate_count=2,
                included_count=2,
                ranking=[
                    _ranking_row(
                        candidate_id=1,
                        student_id=101,
                        percentage=Decimal("70"),
                    ),
                    _ranking_row(
                        candidate_id=2,
                        student_id=102,
                        percentage=Decimal("80"),
                    ),
                ],
            ),
            2: _analytics(
                assessment_id=2,
                candidate_count=2,
                included_count=2,
                ranking=[
                    _ranking_row(
                        candidate_id=3,
                        student_id=101,
                        percentage=Decimal("75"),
                    ),
                    _ranking_row(
                        candidate_id=4,
                        student_id=103,
                        percentage=Decimal("85"),
                    ),
                ],
            ),
        },
    )

    result = await service.get_assessment_cohort_performance(
        db_session,
        admin,
    )

    assert result["included_result_count"] == 4
    assert result["unique_student_count"] == 3


@pytest.mark.asyncio
async def test_incomplete_results_are_counted_but_not_in_percentages(
    db_session: AsyncSession,
    monkeypatch,
):
    admin = _school_admin_user()

    assessment = _assessment(
        assessment_id=1,
    )

    _patch_assessment_repository(
        monkeypatch,
        assessments=[
            assessment,
        ],
    )

    _patch_analytics(
        monkeypatch,
        analytics_by_assessment_id={
            1: _analytics(
                assessment_id=1,
                candidate_count=3,
                included_count=2,
                excluded_count=1,
                ranking=[
                    _ranking_row(
                        candidate_id=1,
                        student_id=101,
                        percentage=Decimal("60"),
                    ),
                    _ranking_row(
                        candidate_id=2,
                        student_id=102,
                        percentage=Decimal("80"),
                    ),
                ],
            ),
        },
    )

    result = await service.get_assessment_cohort_performance(
        db_session,
        admin,
    )

    assert result["candidate_allocation_count"] == 3
    assert result["included_result_count"] == 2
    assert result["excluded_incomplete_result_count"] == 1
    assert result["mean_percentage"] == Decimal("70.00")


@pytest.mark.asyncio
async def test_pass_fail_counts_are_aggregated(
    db_session: AsyncSession,
    monkeypatch,
):
    admin = _school_admin_user()

    assessments = [
        _assessment(
            assessment_id=1,
        ),
        _assessment(
            assessment_id=2,
        ),
    ]

    _patch_assessment_repository(
        monkeypatch,
        assessments=assessments,
    )

    _patch_analytics(
        monkeypatch,
        analytics_by_assessment_id={
            1: _analytics(
                assessment_id=1,
                candidate_count=3,
                included_count=3,
                graded_count=3,
                pass_count=2,
                fail_count=1,
                ranking=[
                    _ranking_row(
                        candidate_id=1,
                        student_id=101,
                        percentage=Decimal("70"),
                        grade="A",
                        is_pass=True,
                    ),
                    _ranking_row(
                        candidate_id=2,
                        student_id=102,
                        percentage=Decimal("65"),
                        grade="B",
                        is_pass=True,
                    ),
                    _ranking_row(
                        candidate_id=3,
                        student_id=103,
                        percentage=Decimal("30"),
                        grade="D",
                        is_pass=False,
                    ),
                ],
            ),
            2: _analytics(
                assessment_id=2,
                candidate_count=2,
                included_count=2,
                graded_count=2,
                pass_count=1,
                fail_count=1,
                ranking=[
                    _ranking_row(
                        candidate_id=4,
                        student_id=104,
                        percentage=Decimal("80"),
                        grade="A",
                        is_pass=True,
                    ),
                    _ranking_row(
                        candidate_id=5,
                        student_id=105,
                        percentage=Decimal("35"),
                        grade="D",
                        is_pass=False,
                    ),
                ],
            ),
        },
    )

    result = await service.get_assessment_cohort_performance(
        db_session,
        admin,
    )

    assert result["pass_count"] == 3
    assert result["fail_count"] == 2
    assert result["pass_percentage"] == Decimal("60.00")


@pytest.mark.asyncio
async def test_assessments_with_and_without_results_are_counted(
    db_session: AsyncSession,
    monkeypatch,
):
    admin = _school_admin_user()

    assessments = [
        _assessment(
            assessment_id=1,
        ),
        _assessment(
            assessment_id=2,
        ),
    ]

    _patch_assessment_repository(
        monkeypatch,
        assessments=assessments,
    )

    _patch_analytics(
        monkeypatch,
        analytics_by_assessment_id={
            1: _analytics(
                assessment_id=1,
                candidate_count=1,
                included_count=1,
                ranking=[
                    _ranking_row(
                        candidate_id=1,
                        student_id=101,
                        percentage=Decimal("70"),
                    ),
                ],
            ),
            2: _analytics(
                assessment_id=2,
                candidate_count=2,
                included_count=0,
                excluded_count=2,
                ranking=[],
            ),
        },
    )

    result = await service.get_assessment_cohort_performance(
        db_session,
        admin,
    )

    assert result["selected_assessment_count"] == 2
    assert result["assessments_with_results"] == 1
    assert result["assessments_without_results"] == 1


@pytest.mark.asyncio
async def test_empty_cohort_returns_empty_statistics(
    db_session: AsyncSession,
    monkeypatch,
):
    admin = _school_admin_user()

    _patch_assessment_repository(
        monkeypatch,
        assessments=[],
    )

    _patch_analytics(
        monkeypatch,
        analytics_by_assessment_id={},
    )

    result = await service.get_assessment_cohort_performance(
        db_session,
        admin,
    )

    assert result["selected_assessment_count"] == 0
    assert result["candidate_allocation_count"] == 0
    assert result["included_result_count"] == 0
    assert result["unique_student_count"] == 0
    assert result["mean_percentage"] is None
    assert result["median_percentage"] is None
    assert result["lowest_percentage"] is None
    assert result["highest_percentage"] is None
    assert result["pass_percentage"] is None
    assert result["grade_distribution"] == []
    assert result["assessments"] == []


@pytest.mark.asyncio
async def test_analytics_access_error_is_propagated(
    db_session: AsyncSession,
    monkeypatch,
):
    admin = _school_admin_user()

    assessment = _assessment(
        assessment_id=1,
    )

    _patch_assessment_repository(
        monkeypatch,
        assessments=[
            assessment,
        ],
    )

    _patch_analytics(
        monkeypatch,
        analytics_by_assessment_id={
            1: HTTPException(
                status_code=403,
                detail="Forbidden.",
            ),
        },
    )

    with pytest.raises(
        HTTPException,
    ) as exc:
        await service.get_assessment_cohort_performance(
            db_session,
            admin,
        )

    assert exc.value.status_code == 403


# ---------------------------------------------------------------------------
# Filtering
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_course_filter_is_passed_to_repository(
    db_session: AsyncSession,
    monkeypatch,
):
    admin = _school_admin_user()

    assessment = _assessment(
        assessment_id=1,
        course=_course(
            course_id=200,
        ),
    )

    calls = _patch_assessment_repository(
        monkeypatch,
        assessments=[
            assessment,
        ],
    )

    _patch_analytics(
        monkeypatch,
        analytics_by_assessment_id={
            1: _analytics(
                assessment_id=1,
                candidate_count=0,
                included_count=0,
            ),
        },
    )

    result = await service.get_assessment_cohort_performance(
        db_session,
        admin,
        course_id=200,
    )

    assert calls[0]["course_id"] == 200
    assert result["scope"]["course_id"] == 200


@pytest.mark.asyncio
async def test_subject_filter_restricts_assessments_before_analytics(
    db_session: AsyncSession,
    monkeypatch,
):
    admin = _school_admin_user()

    physics = _subject(
        subject_id=100,
        name="Physics",
    )

    chemistry = _subject(
        subject_id=101,
        name="Chemistry",
    )

    assessments = [
        _assessment(
            assessment_id=1,
            course=_course(
                course_id=200,
                subject=physics,
            ),
        ),
        _assessment(
            assessment_id=2,
            course=_course(
                course_id=201,
                subject=chemistry,
            ),
        ),
    ]

    _patch_assessment_repository(
        monkeypatch,
        assessments=assessments,
    )

    analytics_calls = _patch_analytics(
        monkeypatch,
        analytics_by_assessment_id={
            1: _analytics(
                assessment_id=1,
                candidate_count=0,
                included_count=0,
            ),
            2: _analytics(
                assessment_id=2,
                candidate_count=0,
                included_count=0,
            ),
        },
    )

    result = await service.get_assessment_cohort_performance(
        db_session,
        admin,
        subject_id=100,
    )

    assert analytics_calls == [1]
    assert result["scope"]["subject_id"] == 100


@pytest.mark.asyncio
async def test_academic_year_and_term_are_normalised_and_passed(
    db_session: AsyncSession,
    monkeypatch,
):
    admin = _school_admin_user()

    assessment = _assessment(
        assessment_id=1,
        academic_year="2026/27",
        term="Autumn",
    )

    calls = _patch_assessment_repository(
        monkeypatch,
        assessments=[
            assessment,
        ],
    )

    _patch_analytics(
        monkeypatch,
        analytics_by_assessment_id={
            1: _analytics(
                assessment_id=1,
                candidate_count=0,
                included_count=0,
            ),
        },
    )

    result = await service.get_assessment_cohort_performance(
        db_session,
        admin,
        academic_year=" 2026/27 ",
        term=" Autumn ",
    )

    assert calls[0]["academic_year"] == "2026/27"
    assert calls[0]["term"] == "Autumn"

    assert result["scope"]["academic_year"] == "2026/27"
    assert result["scope"]["term"] == "Autumn"


# ---------------------------------------------------------------------------
# Assessment comparison rows
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_assessment_comparison_rows_are_chronological(
    db_session: AsyncSession,
    monkeypatch,
):
    admin = _school_admin_user()

    late = _assessment(
        assessment_id=2,
        scheduled_at=datetime(
            2026,
            10,
            1,
            tzinfo=timezone.utc,
        ),
    )

    early = _assessment(
        assessment_id=1,
        scheduled_at=datetime(
            2026,
            9,
            1,
            tzinfo=timezone.utc,
        ),
    )

    _patch_assessment_repository(
        monkeypatch,
        assessments=[
            late,
            early,
        ],
    )

    _patch_analytics(
        monkeypatch,
        analytics_by_assessment_id={
            1: _analytics(
                assessment_id=1,
                candidate_count=0,
                included_count=0,
            ),
            2: _analytics(
                assessment_id=2,
                candidate_count=0,
                included_count=0,
            ),
        },
    )

    result = await service.get_assessment_cohort_performance(
        db_session,
        admin,
    )

    assert [row["assessment_id"] for row in result["assessments"]] == [
        1,
        2,
    ]


# ---------------------------------------------------------------------------
# Wrapper views
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_course_view_delegates_to_main_service(
    db_session: AsyncSession,
    monkeypatch,
):
    captured = {}

    async def fake_main(
        db,
        current_user,
        *,
        school_id=None,
        course_id=None,
        subject_id=None,
        teacher_id=None,
        academic_year=None,
        term=None,
    ):
        captured.update(
            {
                "school_id": school_id,
                "course_id": course_id,
                "subject_id": subject_id,
                "teacher_id": teacher_id,
                "academic_year": academic_year,
                "term": term,
            }
        )

        return {
            "ok": True,
        }

    monkeypatch.setattr(
        service,
        "get_assessment_cohort_performance",
        fake_main,
    )

    result = await service.get_course_assessment_performance(
        db_session,
        _school_admin_user(),
        course_id=200,
        school_id=1,
        academic_year="2026/27",
        term="Autumn",
    )

    assert result == {
        "ok": True,
    }

    assert captured["course_id"] == 200
    assert captured["school_id"] == 1


@pytest.mark.asyncio
async def test_subject_view_delegates_to_main_service(
    db_session: AsyncSession,
    monkeypatch,
):
    captured = {}

    async def fake_main(
        db,
        current_user,
        *,
        school_id=None,
        course_id=None,
        subject_id=None,
        teacher_id=None,
        academic_year=None,
        term=None,
    ):
        captured["subject_id"] = subject_id

        return {
            "ok": True,
        }

    monkeypatch.setattr(
        service,
        "get_assessment_cohort_performance",
        fake_main,
    )

    result = await service.get_subject_assessment_performance(
        db_session,
        _school_admin_user(),
        subject_id=100,
    )

    assert result == {
        "ok": True,
    }

    assert captured["subject_id"] == 100


@pytest.mark.asyncio
async def test_teacher_view_rejects_other_teacher_for_non_admin(
    db_session: AsyncSession,
):
    teacher = _teacher_user(
        user_id=10,
    )

    with pytest.raises(
        HTTPException,
    ) as exc:
        await service.get_teacher_assessment_performance(
            db_session,
            teacher,
            teacher_id=99,
        )

    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_teacher_view_allows_self_for_non_admin(
    db_session: AsyncSession,
    monkeypatch,
):
    teacher = _teacher_user(
        user_id=10,
    )

    captured = {}

    async def fake_main(
        db,
        current_user,
        *,
        school_id=None,
        course_id=None,
        subject_id=None,
        teacher_id=None,
        academic_year=None,
        term=None,
    ):
        captured["teacher_id"] = teacher_id

        return {
            "ok": True,
        }

    monkeypatch.setattr(
        service,
        "get_assessment_cohort_performance",
        fake_main,
    )

    result = await service.get_teacher_assessment_performance(
        db_session,
        teacher,
        teacher_id=10,
    )

    assert result == {
        "ok": True,
    }

    assert captured["teacher_id"] == 10
