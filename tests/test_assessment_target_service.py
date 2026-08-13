from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

import app.services.assessment_target_service as service
from app.models.user import UserRole
from app.repositories.assessment_target import _UNSET

# ---------------------------------------------------------------------------
# Test-data helpers
# ---------------------------------------------------------------------------


def _user(
    *,
    user_id: int,
    school_id: int | None,
    roles: list[str],
    full_name: str | None = None,
):
    return SimpleNamespace(
        id=user_id,
        school_id=school_id,
        roles=roles,
        full_name=full_name or f"User {user_id}",
    )


def _teacher(
    *,
    user_id: int = 10,
    school_id: int = 1,
):
    return _user(
        user_id=user_id,
        school_id=school_id,
        roles=[UserRole.TEACHER.value],
        full_name="Teacher One",
    )


def _school_admin(
    *,
    user_id: int = 20,
    school_id: int = 1,
):
    return _user(
        user_id=user_id,
        school_id=school_id,
        roles=[UserRole.SCHOOL_ADMIN.value],
        full_name="School Admin",
    )


def _platform_admin(
    *,
    user_id: int = 30,
    school_id: int | None = None,
):
    return _user(
        user_id=user_id,
        school_id=school_id,
        roles=[UserRole.PLATFORM_ADMIN.value],
        full_name="Platform Admin",
    )


def _student(
    *,
    user_id: int = 40,
    school_id: int = 1,
):
    return _user(
        user_id=user_id,
        school_id=school_id,
        roles=[UserRole.STUDENT.value],
        full_name="Student One",
    )


def _parent(
    *,
    user_id: int = 50,
    school_id: int = 1,
):
    return _user(
        user_id=user_id,
        school_id=school_id,
        roles=[UserRole.PARENT.value],
        full_name="Parent One",
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
    course_id: int = 200,
    school_id: int = 1,
    teacher_id: int = 10,
    title: str = "OCR A Level Physics A",
    subject_id: int = 100,
):
    subject = _subject(
        subject_id=subject_id,
    )

    return SimpleNamespace(
        id=course_id,
        school_id=school_id,
        teacher_id=teacher_id,
        title=title,
        subject_id=subject.id,
        subject=subject,
    )


def _target(
    *,
    target_id: int = 1,
    school_id: int = 1,
    student_id: int = 40,
    course_id: int = 200,
    grade_label: str = "A",
    grade_points: Decimal | None = Decimal("5.00"),
    academic_year: str | None = "2026/27",
    notes: str | None = "Maintain strong performance.",
    set_by_id: int = 10,
    course=None,
    student=None,
    setter=None,
):
    course_value = course or _course(
        course_id=course_id,
        school_id=school_id,
        teacher_id=set_by_id,
    )

    student_value = student or _student(
        user_id=student_id,
        school_id=school_id,
    )

    setter_value = setter or _teacher(
        user_id=set_by_id,
        school_id=school_id,
    )

    return SimpleNamespace(
        id=target_id,
        school_id=school_id,
        student_id=student_id,
        course_id=course_id,
        grade_label=grade_label,
        grade_points=grade_points,
        academic_year=academic_year,
        notes=notes,
        set_by_id=set_by_id,
        created_at=datetime(
            2026,
            9,
            1,
            tzinfo=timezone.utc,
        ),
        updated_at=datetime(
            2026,
            9,
            2,
            tzinfo=timezone.utc,
        ),
        course=course_value,
        student=student_value,
        set_by=setter_value,
    )


# ---------------------------------------------------------------------------
# Repository patch helper
# ---------------------------------------------------------------------------


def _patch_repository(
    monkeypatch,
    *,
    existing_target=None,
    targets=None,
):
    calls: list[tuple] = []

    class FakeRepository:
        def __init__(
            self,
            db,
        ):
            self.db = db

        async def get_by_student_and_course(
            self,
            *,
            student_id,
            course_id,
            school_id=None,
            include_relationships=True,
        ):
            calls.append(
                (
                    "get_by_student_and_course",
                    student_id,
                    course_id,
                    school_id,
                    include_relationships,
                )
            )

            return existing_target

        async def get_by_id_and_school(
            self,
            target_id,
            school_id,
            *,
            include_relationships=True,
        ):
            calls.append(
                (
                    "get_by_id_and_school",
                    target_id,
                    school_id,
                    include_relationships,
                )
            )

            return existing_target

        async def list_by_school(
            self,
            school_id,
            *,
            student_id=None,
            course_id=None,
            set_by_id=None,
            academic_year=None,
            include_relationships=True,
        ):
            calls.append(
                (
                    "list_by_school",
                    school_id,
                    student_id,
                    course_id,
                    academic_year,
                )
            )

            return list(
                targets or [],
            )

        async def create(
            self,
            *,
            school_id,
            student_id,
            course_id,
            grade_label,
            set_by_id,
            grade_points=None,
            academic_year=None,
            notes=None,
        ):
            calls.append(
                (
                    "create",
                    school_id,
                    student_id,
                    course_id,
                    grade_label,
                    grade_points,
                    academic_year,
                    notes,
                    set_by_id,
                )
            )

            return _target(
                target_id=99,
                school_id=school_id,
                student_id=student_id,
                course_id=course_id,
                grade_label=grade_label,
                grade_points=grade_points,
                academic_year=academic_year,
                notes=notes,
                set_by_id=set_by_id,
            )

        async def update(
            self,
            target,
            *,
            grade_label=_UNSET,
            grade_points=_UNSET,
            academic_year=_UNSET,
            notes=_UNSET,
            set_by_id=_UNSET,
        ):
            calls.append(
                (
                    "update",
                    grade_label,
                    grade_points,
                    academic_year,
                    notes,
                    set_by_id,
                )
            )

            if grade_label is not _UNSET:
                target.grade_label = grade_label

            if grade_points is not _UNSET:
                target.grade_points = grade_points

            if academic_year is not _UNSET:
                target.academic_year = academic_year

            if notes is not _UNSET:
                target.notes = notes

            if set_by_id is not _UNSET:
                target.set_by_id = set_by_id

            return target

        async def delete(
            self,
            target,
        ):
            calls.append(
                (
                    "delete",
                    target.id,
                )
            )

    monkeypatch.setattr(
        service,
        "AssessmentTargetRepository",
        FakeRepository,
    )

    return calls


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
    with pytest.raises(
        HTTPException,
    ) as exc:
        service._validate_positive_integer(
            value,
            field_name="course_id",
        )

    assert exc.value.status_code == 422


def test_normalise_grade_label_trims():
    assert (
        service._normalise_grade_label(
            "  A*  ",
        )
        == "A*"
    )


def test_normalise_grade_label_rejects_blank():
    with pytest.raises(
        HTTPException,
    ) as exc:
        service._normalise_grade_label(
            "   ",
        )

    assert exc.value.status_code == 422


def test_normalise_grade_points_allows_none():
    assert (
        service._normalise_grade_points(
            None,
        )
        is None
    )


def test_normalise_grade_points_rejects_negative():
    with pytest.raises(
        HTTPException,
    ) as exc:
        service._normalise_grade_points(
            "-1",
        )

    assert exc.value.status_code == 422


# ---------------------------------------------------------------------------
# Roles and school scope
# ---------------------------------------------------------------------------


def test_student_cannot_manage_targets():
    with pytest.raises(
        HTTPException,
    ) as exc:
        service._ensure_target_staff_role(
            _student(),
        )

    assert exc.value.status_code == 403


def test_teacher_can_manage_targets():
    service._ensure_target_staff_role(
        _teacher(),
    )


def test_school_admin_can_manage_targets():
    service._ensure_target_staff_role(
        _school_admin(),
    )


def test_platform_admin_can_manage_targets():
    service._ensure_target_staff_role(
        _platform_admin(),
    )


def test_school_user_school_is_forced():
    teacher = _teacher(
        school_id=1,
    )

    assert (
        service._resolve_school_id(
            teacher,
            None,
        )
        == 1
    )


def test_school_user_cannot_request_other_school():
    teacher = _teacher(
        school_id=1,
    )

    with pytest.raises(
        HTTPException,
    ) as exc:
        service._resolve_school_id(
            teacher,
            2,
        )

    assert exc.value.status_code == 403


def test_platform_admin_must_supply_school_when_unscoped():
    admin = _platform_admin(
        school_id=None,
    )

    with pytest.raises(
        HTTPException,
    ) as exc:
        service._resolve_school_id(
            admin,
            None,
        )

    assert exc.value.status_code == 422


def test_platform_admin_can_supply_school():
    assert (
        service._resolve_school_id(
            _platform_admin(),
            7,
        )
        == 7
    )


# ---------------------------------------------------------------------------
# Course access
# ---------------------------------------------------------------------------


def test_teacher_can_manage_own_course():
    teacher = _teacher(
        user_id=10,
    )

    service._ensure_course_management_access(
        teacher,
        _course(
            teacher_id=10,
        ),
    )


def test_teacher_cannot_manage_other_teachers_course():
    teacher = _teacher(
        user_id=10,
    )

    with pytest.raises(
        HTTPException,
    ) as exc:
        service._ensure_course_management_access(
            teacher,
            _course(
                teacher_id=99,
            ),
        )

    assert exc.value.status_code == 403


def test_school_admin_can_manage_other_teachers_course():
    service._ensure_course_management_access(
        _school_admin(),
        _course(
            teacher_id=99,
        ),
    )


# ---------------------------------------------------------------------------
# Progress comparison
# ---------------------------------------------------------------------------


def test_progress_above_target():
    result = service._calculate_progress_comparison(
        target_grade_label="B",
        target_grade_points=Decimal("4"),
        current_grade="A",
        current_grade_points=Decimal("5"),
    )

    assert result["status"] == "above_target"
    assert result["grade_points_difference"] == Decimal("1.00")


def test_progress_on_target():
    result = service._calculate_progress_comparison(
        target_grade_label="A",
        target_grade_points=Decimal("5"),
        current_grade="A",
        current_grade_points=Decimal("5"),
    )

    assert result["status"] == "on_target"
    assert result["grade_points_difference"] == Decimal("0.00")


def test_progress_below_target():
    result = service._calculate_progress_comparison(
        target_grade_label="A",
        target_grade_points=Decimal("5"),
        current_grade="B",
        current_grade_points=Decimal("4"),
    )

    assert result["status"] == "below_target"
    assert result["grade_points_difference"] == Decimal("-1.00")


def test_progress_not_comparable_without_target_points():
    result = service._calculate_progress_comparison(
        target_grade_label="A",
        target_grade_points=None,
        current_grade="A",
        current_grade_points=Decimal("5"),
    )

    assert result["status"] == "not_comparable"
    assert result["grade_points_difference"] is None


def test_progress_not_comparable_without_current_points():
    result = service._calculate_progress_comparison(
        target_grade_label="A",
        target_grade_points=Decimal("5"),
        current_grade="A",
        current_grade_points=None,
    )

    assert result["status"] == "not_comparable"
    assert result["grade_points_difference"] is None


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_target_rejects_duplicate(
    db_session: AsyncSession,
    monkeypatch,
):
    teacher = _teacher()

    existing = _target()

    _patch_repository(
        monkeypatch,
        existing_target=existing,
    )

    async def fake_student(
        db,
        *,
        student_id,
        school_id,
    ):
        return _student(
            user_id=student_id,
            school_id=school_id,
        )

    async def fake_course(
        db,
        *,
        course_id,
        school_id,
    ):
        return _course(
            course_id=course_id,
            school_id=school_id,
            teacher_id=teacher.id,
        )

    monkeypatch.setattr(
        service,
        "_get_student_or_404",
        fake_student,
    )

    monkeypatch.setattr(
        service,
        "_get_course_or_404",
        fake_course,
    )

    with pytest.raises(
        HTTPException,
    ) as exc:
        await service.create_assessment_target(
            db_session,
            teacher,
            student_id=40,
            course_id=200,
            grade_label="A",
        )

    assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_create_target_passes_clean_values_to_repository(
    db_session: AsyncSession,
    monkeypatch,
):
    teacher = _teacher()

    calls = _patch_repository(
        monkeypatch,
        existing_target=None,
    )

    async def fake_student(
        db,
        *,
        student_id,
        school_id,
    ):
        return _student(
            user_id=student_id,
            school_id=school_id,
        )

    async def fake_course(
        db,
        *,
        course_id,
        school_id,
    ):
        return _course(
            course_id=course_id,
            school_id=school_id,
            teacher_id=teacher.id,
        )

    async def fake_commit(
        db,
        *,
        duplicate_detail,
    ):
        return None

    monkeypatch.setattr(
        service,
        "_get_student_or_404",
        fake_student,
    )

    monkeypatch.setattr(
        service,
        "_get_course_or_404",
        fake_course,
    )

    monkeypatch.setattr(
        service,
        "_commit_target_change",
        fake_commit,
    )

    async def fake_refresh(
        obj,
    ):
        return None

    monkeypatch.setattr(
        db_session,
        "refresh",
        fake_refresh,
    )

    created = _target(
        target_id=99,
        set_by_id=teacher.id,
    )

    class FakeRepository(service.AssessmentTargetRepository):
        pass

    # Make the reload return a populated target.
    for index, call in enumerate(calls):
        assert call is not None

    repository_calls = calls

    async def fake_get_by_id_and_school(
        self,
        target_id,
        school_id,
        *,
        include_relationships=True,
    ):
        return created

    monkeypatch.setattr(
        service.AssessmentTargetRepository,
        "get_by_id_and_school",
        fake_get_by_id_and_school,
        raising=False,
    )

    result = await service.create_assessment_target(
        db_session,
        teacher,
        student_id=40,
        course_id=200,
        grade_label="  A  ",
        grade_points="5",
        academic_year=" 2026/27 ",
        notes=" Keep progressing. ",
    )

    create_calls = [call for call in repository_calls if call[0] == "create"]

    assert len(create_calls) == 1

    _, _, _, _, grade_label, grade_points, academic_year, notes, setter_id = (
        create_calls[0]
    )

    assert grade_label == "A"
    assert grade_points == Decimal("5")
    assert academic_year == "2026/27"
    assert notes == "Keep progressing."
    assert setter_id == teacher.id
    assert result["grade_label"] == "A"


# ---------------------------------------------------------------------------
# Get/list
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_target_returns_serialised_payload(
    db_session: AsyncSession,
    monkeypatch,
):
    teacher = _teacher()
    target = _target(
        set_by_id=teacher.id,
        course=_course(
            teacher_id=teacher.id,
        ),
    )

    async def fake_get_target(
        db,
        current_user,
        *,
        target_id,
        school_id=None,
    ):
        return target

    monkeypatch.setattr(
        service,
        "_get_target_or_404",
        fake_get_target,
    )

    result = await service.get_assessment_target(
        db_session,
        teacher,
        target_id=target.id,
    )

    assert result["id"] == target.id
    assert result["student_id"] == target.student_id
    assert result["course_id"] == target.course_id
    assert result["grade_label"] == "A"
    assert result["subject_name"] == "Physics"


@pytest.mark.asyncio
async def test_teacher_list_filters_out_other_teachers_courses(
    db_session: AsyncSession,
    monkeypatch,
):
    teacher = _teacher(
        user_id=10,
    )

    own = _target(
        target_id=1,
        course=_course(
            course_id=200,
            teacher_id=10,
        ),
    )

    other = _target(
        target_id=2,
        course=_course(
            course_id=201,
            teacher_id=99,
        ),
    )

    _patch_repository(
        monkeypatch,
        targets=[
            own,
            other,
        ],
    )

    result = await service.list_assessment_targets(
        db_session,
        teacher,
    )

    assert [row["id"] for row in result] == [1]


@pytest.mark.asyncio
async def test_school_admin_list_can_see_multiple_teachers(
    db_session: AsyncSession,
    monkeypatch,
):
    admin = _school_admin()

    targets = [
        _target(
            target_id=1,
            course=_course(
                teacher_id=10,
            ),
        ),
        _target(
            target_id=2,
            course=_course(
                course_id=201,
                teacher_id=99,
            ),
        ),
    ]

    _patch_repository(
        monkeypatch,
        targets=targets,
    )

    result = await service.list_assessment_targets(
        db_session,
        admin,
    )

    assert len(result) == 2


# ---------------------------------------------------------------------------
# Update
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_update_target_supports_explicit_nullable_clearing(
    db_session: AsyncSession,
    monkeypatch,
):
    teacher = _teacher()

    target = _target(
        grade_points=Decimal("5"),
        academic_year="2026/27",
        notes="Old notes",
        set_by_id=teacher.id,
        course=_course(
            teacher_id=teacher.id,
        ),
    )

    calls = _patch_repository(
        monkeypatch,
        existing_target=target,
    )

    async def fake_authorised_target(
        db,
        current_user,
        *,
        target_id,
        school_id=None,
    ):
        return target

    async def fake_commit(
        db,
        *,
        duplicate_detail,
    ):
        return None

    async def fake_refresh(
        obj,
    ):
        return None

    monkeypatch.setattr(
        service,
        "_get_target_or_404",
        fake_authorised_target,
    )

    monkeypatch.setattr(
        service,
        "_commit_target_change",
        fake_commit,
    )

    monkeypatch.setattr(
        db_session,
        "refresh",
        fake_refresh,
    )

    result = await service.update_assessment_target(
        db_session,
        teacher,
        target_id=target.id,
        grade_points=None,
        academic_year=None,
        notes=None,
    )

    update_calls = [call for call in calls if call[0] == "update"]

    assert len(update_calls) == 1

    _, _, grade_points, academic_year, notes, setter_id = update_calls[0]

    assert grade_points is None
    assert academic_year is None
    assert notes is None
    assert setter_id == teacher.id

    assert result["grade_points"] is None
    assert result["academic_year"] is None
    assert result["notes"] is None


@pytest.mark.asyncio
async def test_update_target_preserves_unsupplied_fields(
    db_session: AsyncSession,
    monkeypatch,
):
    teacher = _teacher()

    target = _target(
        grade_label="B",
        grade_points=Decimal("4"),
        academic_year="2026/27",
        notes="Existing",
        set_by_id=teacher.id,
        course=_course(
            teacher_id=teacher.id,
        ),
    )

    calls = _patch_repository(
        monkeypatch,
        existing_target=target,
    )

    async def fake_authorised_target(
        db,
        current_user,
        *,
        target_id,
        school_id=None,
    ):
        return target

    async def fake_commit(
        db,
        *,
        duplicate_detail,
    ):
        return None

    async def fake_refresh(
        obj,
    ):
        return None

    monkeypatch.setattr(
        service,
        "_get_target_or_404",
        fake_authorised_target,
    )

    monkeypatch.setattr(
        service,
        "_commit_target_change",
        fake_commit,
    )

    monkeypatch.setattr(
        db_session,
        "refresh",
        fake_refresh,
    )

    await service.update_assessment_target(
        db_session,
        teacher,
        target_id=target.id,
        grade_label="A",
    )

    update_call = [call for call in calls if call[0] == "update"][0]

    assert update_call[1] == "A"
    assert update_call[2] is _UNSET
    assert update_call[3] is _UNSET
    assert update_call[4] is _UNSET


# ---------------------------------------------------------------------------
# Delete
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_delete_target_delegates_to_repository(
    db_session: AsyncSession,
    monkeypatch,
):
    teacher = _teacher()

    target = _target(
        course=_course(
            teacher_id=teacher.id,
        ),
    )

    calls = _patch_repository(
        monkeypatch,
        existing_target=target,
    )

    async def fake_authorised_target(
        db,
        current_user,
        *,
        target_id,
        school_id=None,
    ):
        return target

    async def fake_commit(
        db,
        *,
        duplicate_detail,
    ):
        return None

    monkeypatch.setattr(
        service,
        "_get_target_or_404",
        fake_authorised_target,
    )

    monkeypatch.setattr(
        service,
        "_commit_target_change",
        fake_commit,
    )

    await service.delete_assessment_target(
        db_session,
        teacher,
        target_id=target.id,
    )

    assert (
        "delete",
        target.id,
    ) in calls


# ---------------------------------------------------------------------------
# Transaction handling
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_commit_integrity_error_becomes_conflict(
    monkeypatch,
):
    db = SimpleNamespace()

    async def fake_commit():
        raise IntegrityError(
            "statement",
            {},
            Exception("duplicate"),
        )

    rollback_called = False

    async def fake_rollback():
        nonlocal rollback_called
        rollback_called = True

    db.commit = fake_commit
    db.rollback = fake_rollback

    with pytest.raises(
        HTTPException,
    ) as exc:
        await service._commit_target_change(
            db,
            duplicate_detail="Duplicate target.",
        )

    assert exc.value.status_code == 409
    assert exc.value.detail == "Duplicate target."
    assert rollback_called is True


# ---------------------------------------------------------------------------
# Student-facing progress
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_student_target_progress_above_target(
    db_session: AsyncSession,
    monkeypatch,
):
    student = _student(
        user_id=40,
    )

    target = _target(
        student_id=student.id,
        grade_label="B",
        grade_points=Decimal("4"),
    )

    _patch_repository(
        monkeypatch,
        existing_target=target,
    )

    async def fake_trend(
        *,
        db,
        current_user,
        school_id,
        course_id,
        subject_id,
        academic_year,
        term,
    ):
        return {
            "points": [
                {
                    "grade": "A",
                    "grade_points": Decimal("5"),
                }
            ]
        }

    monkeypatch.setattr(
        service,
        "get_student_assessment_trend",
        fake_trend,
    )

    result = await service.get_student_target_progress(
        db_session,
        student,
        course_id=target.course_id,
    )

    assert result["audience"] == "student"
    assert result["status"] == "above_target"
    assert result["grade_points_difference"] == Decimal("1.00")


@pytest.mark.asyncio
async def test_student_target_progress_no_result_is_not_comparable(
    db_session: AsyncSession,
    monkeypatch,
):
    student = _student()

    target = _target(
        student_id=student.id,
    )

    _patch_repository(
        monkeypatch,
        existing_target=target,
    )

    async def fake_trend(
        *,
        db,
        current_user,
        school_id,
        course_id,
        subject_id,
        academic_year,
        term,
    ):
        return {
            "points": [],
        }

    monkeypatch.setattr(
        service,
        "get_student_assessment_trend",
        fake_trend,
    )

    result = await service.get_student_target_progress(
        db_session,
        student,
        course_id=target.course_id,
    )

    assert result["latest_result"] is None
    assert result["status"] == "not_comparable"
    assert result["grade_points_difference"] is None


@pytest.mark.asyncio
async def test_non_student_cannot_use_student_progress_view(
    db_session: AsyncSession,
):
    with pytest.raises(
        HTTPException,
    ) as exc:
        await service.get_student_target_progress(
            db_session,
            _teacher(),
            course_id=200,
        )

    assert exc.value.status_code == 403


# ---------------------------------------------------------------------------
# Parent-facing progress
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_parent_target_progress_uses_parent_trend_authorisation(
    db_session: AsyncSession,
    monkeypatch,
):
    parent = _parent()

    target = _target(
        student_id=40,
        grade_label="A",
        grade_points=Decimal("5"),
    )

    _patch_repository(
        monkeypatch,
        existing_target=target,
    )

    received: dict = {}

    async def fake_parent_trend(
        *,
        db,
        current_user,
        student_id,
        school_id,
        course_id,
        subject_id,
        academic_year,
        term,
    ):
        received.update(
            {
                "student_id": student_id,
                "school_id": school_id,
                "course_id": course_id,
                "academic_year": academic_year,
            }
        )

        return {
            "points": [
                {
                    "grade": "A",
                    "grade_points": Decimal("5"),
                }
            ]
        }

    monkeypatch.setattr(
        service,
        "get_parent_student_assessment_trend",
        fake_parent_trend,
    )

    result = await service.get_parent_student_target_progress(
        db_session,
        parent,
        student_id=40,
        course_id=200,
    )

    assert result["audience"] == "parent"
    assert result["status"] == "on_target"

    assert received == {
        "student_id": 40,
        "school_id": target.school_id,
        "course_id": 200,
        "academic_year": target.academic_year,
    }


@pytest.mark.asyncio
async def test_parent_target_progress_propagates_forbidden_from_parent_trend(
    db_session: AsyncSession,
    monkeypatch,
):
    parent = _parent()

    target = _target(
        student_id=40,
    )

    _patch_repository(
        monkeypatch,
        existing_target=target,
    )

    async def fake_parent_trend(
        *,
        db,
        current_user,
        student_id,
        school_id,
        course_id,
        subject_id,
        academic_year,
        term,
    ):
        raise HTTPException(
            status_code=403,
            detail="Forbidden.",
        )

    monkeypatch.setattr(
        service,
        "get_parent_student_assessment_trend",
        fake_parent_trend,
    )

    with pytest.raises(
        HTTPException,
    ) as exc:
        await service.get_parent_student_target_progress(
            db_session,
            parent,
            student_id=40,
            course_id=200,
        )

    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_parent_target_progress_missing_target_returns_404(
    db_session: AsyncSession,
    monkeypatch,
):
    parent = _parent()

    _patch_repository(
        monkeypatch,
        existing_target=None,
    )

    with pytest.raises(
        HTTPException,
    ) as exc:
        await service.get_parent_student_target_progress(
            db_session,
            parent,
            student_id=40,
            course_id=200,
        )

    assert exc.value.status_code == 404
