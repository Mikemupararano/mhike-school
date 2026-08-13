from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

import app.services.assessment_feedback_service as service
from app.models.assessment_feedback import AssessmentFeedbackStatus
from app.models.user import UserRole
from app.repositories.assessment_feedback import _UNSET

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


def _course(
    *,
    course_id: int = 200,
    school_id: int = 1,
    teacher_id: int = 10,
):
    return SimpleNamespace(
        id=course_id,
        school_id=school_id,
        teacher_id=teacher_id,
        title="OCR A Level Physics A",
    )


def _assessment(
    *,
    assessment_id: int = 300,
    school_id: int = 1,
    course_id: int = 200,
):
    return SimpleNamespace(
        id=assessment_id,
        school_id=school_id,
        course_id=course_id,
        title="Mechanics Test",
    )


def _candidate(
    *,
    candidate_id: int = 400,
    assessment_id: int = 300,
    student_id: int = 40,
):
    return SimpleNamespace(
        id=candidate_id,
        assessment_id=assessment_id,
        student_id=student_id,
    )


def _script(
    *,
    script_id: int = 500,
    candidate_id: int = 400,
):
    return SimpleNamespace(
        id=script_id,
        candidate_id=candidate_id,
    )


def _response(
    *,
    response_id: int = 600,
    script_id: int = 500,
):
    return SimpleNamespace(
        id=response_id,
        script_id=script_id,
    )


def _feedback(
    *,
    feedback_id: int = 1,
    school_id: int = 1,
    script_id: int = 500,
    status_value: AssessmentFeedbackStatus = AssessmentFeedbackStatus.DRAFT,
    overall_comment: str | None = "A strong assessment.",
    strengths: str | None = "Good application of mechanics.",
    areas_for_improvement: str | None = "Show working more clearly.",
    next_steps: str | None = "Practise momentum questions.",
    include_with_result: bool = True,
    created_by_id: int = 10,
    updated_by_id: int | None = None,
    finalised_at: datetime | None = None,
    finalised_by_id: int | None = None,
):
    creator = _teacher(
        user_id=created_by_id,
        school_id=school_id,
    )

    updater = (
        _teacher(
            user_id=updated_by_id,
            school_id=school_id,
        )
        if updated_by_id is not None
        else None
    )

    finaliser = (
        _teacher(
            user_id=finalised_by_id,
            school_id=school_id,
        )
        if finalised_by_id is not None
        else None
    )

    return SimpleNamespace(
        id=feedback_id,
        school_id=school_id,
        script_id=script_id,
        overall_comment=overall_comment,
        strengths=strengths,
        areas_for_improvement=areas_for_improvement,
        next_steps=next_steps,
        status=status_value,
        include_with_result=include_with_result,
        created_by_id=created_by_id,
        updated_by_id=updated_by_id,
        finalised_at=finalised_at,
        finalised_by_id=finalised_by_id,
        created_at=datetime(
            2026,
            9,
            1,
            9,
            0,
            tzinfo=timezone.utc,
        ),
        updated_at=datetime(
            2026,
            9,
            2,
            10,
            0,
            tzinfo=timezone.utc,
        ),
        created_by=creator,
        updated_by=updater,
        finalised_by=finaliser,
    )


def _question_feedback(
    *,
    question_feedback_id: int = 2,
    school_id: int = 1,
    response_id: int = 600,
    feedback_text: str | None = "Correct method.",
    strength: str | None = "Clear substitution.",
    improvement: str | None = "Include the unit.",
    include_with_result: bool = True,
    created_by_id: int = 10,
    updated_by_id: int | None = None,
):
    creator = _teacher(
        user_id=created_by_id,
        school_id=school_id,
    )

    updater = (
        _teacher(
            user_id=updated_by_id,
            school_id=school_id,
        )
        if updated_by_id is not None
        else None
    )

    return SimpleNamespace(
        id=question_feedback_id,
        school_id=school_id,
        response_id=response_id,
        feedback_text=feedback_text,
        strength=strength,
        improvement=improvement,
        include_with_result=include_with_result,
        created_by_id=created_by_id,
        updated_by_id=updated_by_id,
        created_at=datetime(
            2026,
            9,
            1,
            9,
            0,
            tzinfo=timezone.utc,
        ),
        updated_at=datetime(
            2026,
            9,
            2,
            10,
            0,
            tzinfo=timezone.utc,
        ),
        created_by=creator,
        updated_by=updater,
    )


def _script_context(
    *,
    school_id: int = 1,
    teacher_id: int = 10,
):
    return {
        "script": _script(),
        "candidate": _candidate(),
        "assessment": _assessment(
            school_id=school_id,
        ),
        "course": _course(
            school_id=school_id,
            teacher_id=teacher_id,
        ),
    }


def _response_context(
    *,
    school_id: int = 1,
    teacher_id: int = 10,
):
    return {
        **_script_context(
            school_id=school_id,
            teacher_id=teacher_id,
        ),
        "response": _response(),
    }


# ---------------------------------------------------------------------------
# Repository patch helper
# ---------------------------------------------------------------------------


def _patch_repository(
    monkeypatch,
    *,
    overall_feedback=None,
    question_feedback=None,
):
    calls: list[tuple] = []

    class FakeRepository:
        def __init__(
            self,
            db,
        ):
            self.db = db

        async def get_feedback_by_id_and_school(
            self,
            feedback_id,
            school_id,
            *,
            include_relationships=True,
        ):
            calls.append(
                (
                    "get_feedback_by_id_and_school",
                    feedback_id,
                    school_id,
                    include_relationships,
                )
            )

            return overall_feedback

        async def get_feedback_by_script(
            self,
            script_id,
            *,
            school_id=None,
            include_relationships=True,
        ):
            calls.append(
                (
                    "get_feedback_by_script",
                    script_id,
                    school_id,
                    include_relationships,
                )
            )

            return overall_feedback

        async def create_feedback(
            self,
            *,
            school_id,
            script_id,
            created_by_id,
            overall_comment=None,
            strengths=None,
            areas_for_improvement=None,
            next_steps=None,
            include_with_result=True,
            status=AssessmentFeedbackStatus.DRAFT,
        ):
            calls.append(
                (
                    "create_feedback",
                    school_id,
                    script_id,
                    created_by_id,
                    overall_comment,
                    strengths,
                    areas_for_improvement,
                    next_steps,
                    include_with_result,
                    status,
                )
            )

            return _feedback(
                feedback_id=99,
                school_id=school_id,
                script_id=script_id,
                overall_comment=overall_comment,
                strengths=strengths,
                areas_for_improvement=areas_for_improvement,
                next_steps=next_steps,
                include_with_result=include_with_result,
                status_value=status,
                created_by_id=created_by_id,
            )

        async def update_feedback(
            self,
            feedback,
            *,
            overall_comment=_UNSET,
            strengths=_UNSET,
            areas_for_improvement=_UNSET,
            next_steps=_UNSET,
            include_with_result=_UNSET,
            status=_UNSET,
            updated_by_id=_UNSET,
            finalised_at=_UNSET,
            finalised_by_id=_UNSET,
        ):
            calls.append(
                (
                    "update_feedback",
                    overall_comment,
                    strengths,
                    areas_for_improvement,
                    next_steps,
                    include_with_result,
                    status,
                    updated_by_id,
                    finalised_at,
                    finalised_by_id,
                )
            )

            if overall_comment is not _UNSET:
                feedback.overall_comment = overall_comment

            if strengths is not _UNSET:
                feedback.strengths = strengths

            if areas_for_improvement is not _UNSET:
                feedback.areas_for_improvement = areas_for_improvement

            if next_steps is not _UNSET:
                feedback.next_steps = next_steps

            if include_with_result is not _UNSET:
                feedback.include_with_result = include_with_result

            if status is not _UNSET:
                feedback.status = status

            if updated_by_id is not _UNSET:
                feedback.updated_by_id = updated_by_id

            if finalised_at is not _UNSET:
                feedback.finalised_at = finalised_at

            if finalised_by_id is not _UNSET:
                feedback.finalised_by_id = finalised_by_id

            return feedback

        async def delete_feedback(
            self,
            feedback,
        ):
            calls.append(
                (
                    "delete_feedback",
                    feedback.id,
                )
            )

        async def get_question_feedback_by_id_and_school(
            self,
            question_feedback_id,
            school_id,
            *,
            include_relationships=True,
        ):
            calls.append(
                (
                    "get_question_feedback_by_id_and_school",
                    question_feedback_id,
                    school_id,
                    include_relationships,
                )
            )

            return question_feedback

        async def get_question_feedback_by_response(
            self,
            response_id,
            *,
            school_id=None,
            include_relationships=True,
        ):
            calls.append(
                (
                    "get_question_feedback_by_response",
                    response_id,
                    school_id,
                    include_relationships,
                )
            )

            return question_feedback

        async def create_question_feedback(
            self,
            *,
            school_id,
            response_id,
            created_by_id,
            feedback_text=None,
            strength=None,
            improvement=None,
            include_with_result=True,
        ):
            calls.append(
                (
                    "create_question_feedback",
                    school_id,
                    response_id,
                    created_by_id,
                    feedback_text,
                    strength,
                    improvement,
                    include_with_result,
                )
            )

            return _question_feedback(
                question_feedback_id=199,
                school_id=school_id,
                response_id=response_id,
                feedback_text=feedback_text,
                strength=strength,
                improvement=improvement,
                include_with_result=include_with_result,
                created_by_id=created_by_id,
            )

        async def update_question_feedback(
            self,
            feedback,
            *,
            feedback_text=_UNSET,
            strength=_UNSET,
            improvement=_UNSET,
            include_with_result=_UNSET,
            updated_by_id=_UNSET,
        ):
            calls.append(
                (
                    "update_question_feedback",
                    feedback_text,
                    strength,
                    improvement,
                    include_with_result,
                    updated_by_id,
                )
            )

            if feedback_text is not _UNSET:
                feedback.feedback_text = feedback_text

            if strength is not _UNSET:
                feedback.strength = strength

            if improvement is not _UNSET:
                feedback.improvement = improvement

            if include_with_result is not _UNSET:
                feedback.include_with_result = include_with_result

            if updated_by_id is not _UNSET:
                feedback.updated_by_id = updated_by_id

            return feedback

        async def delete_question_feedback(
            self,
            feedback,
        ):
            calls.append(
                (
                    "delete_question_feedback",
                    feedback.id,
                )
            )

    monkeypatch.setattr(
        service,
        "AssessmentFeedbackRepository",
        FakeRepository,
    )

    return calls


# ---------------------------------------------------------------------------
# Validation
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
            field_name="script_id",
        )

    assert exc.value.status_code == 422


def test_normalise_optional_text_trims():
    assert (
        service._normalise_optional_text(
            "  Strong work.  ",
            field_name="overall_comment",
        )
        == "Strong work."
    )


def test_normalise_optional_text_blank_becomes_none():
    assert (
        service._normalise_optional_text(
            "   ",
            field_name="overall_comment",
        )
        is None
    )


def test_validate_bool_rejects_non_boolean():
    with pytest.raises(
        HTTPException,
    ) as exc:
        service._validate_bool(
            1,
            field_name="include_with_result",
        )

    assert exc.value.status_code == 422


# ---------------------------------------------------------------------------
# Roles and school scope
# ---------------------------------------------------------------------------


def test_teacher_can_manage_feedback():
    service._ensure_feedback_staff_role(
        _teacher(),
    )


def test_school_admin_can_manage_feedback():
    service._ensure_feedback_staff_role(
        _school_admin(),
    )


def test_platform_admin_can_manage_feedback():
    service._ensure_feedback_staff_role(
        _platform_admin(),
    )


def test_student_cannot_manage_feedback():
    with pytest.raises(
        HTTPException,
    ) as exc:
        service._ensure_feedback_staff_role(
            _student(),
        )

    assert exc.value.status_code == 403


def test_school_scoped_user_uses_own_school():
    assert (
        service._resolve_school_id(
            _teacher(
                school_id=3,
            ),
            None,
        )
        == 3
    )


def test_school_scoped_user_cannot_request_other_school():
    with pytest.raises(
        HTTPException,
    ) as exc:
        service._resolve_school_id(
            _teacher(
                school_id=1,
            ),
            2,
        )

    assert exc.value.status_code == 403


def test_platform_admin_can_supply_school():
    assert (
        service._resolve_school_id(
            _platform_admin(),
            7,
        )
        == 7
    )


def test_unscoped_platform_admin_requires_school():
    with pytest.raises(
        HTTPException,
    ) as exc:
        service._resolve_school_id(
            _platform_admin(
                school_id=None,
            ),
            None,
        )

    assert exc.value.status_code == 422


# ---------------------------------------------------------------------------
# Course ownership
# ---------------------------------------------------------------------------


def test_teacher_can_manage_own_course_feedback():
    service._ensure_feedback_course_access(
        _teacher(
            user_id=10,
        ),
        _course(
            teacher_id=10,
        ),
    )


def test_teacher_cannot_manage_another_teachers_course_feedback():
    with pytest.raises(
        HTTPException,
    ) as exc:
        service._ensure_feedback_course_access(
            _teacher(
                user_id=10,
            ),
            _course(
                teacher_id=99,
            ),
        )

    assert exc.value.status_code == 403


def test_school_admin_can_manage_any_course_feedback():
    service._ensure_feedback_course_access(
        _school_admin(),
        _course(
            teacher_id=99,
        ),
    )


# ---------------------------------------------------------------------------
# Serialisation
# ---------------------------------------------------------------------------


def test_feedback_serialisation_includes_audit_metadata():
    feedback = _feedback(
        updated_by_id=11,
        finalised_at=datetime(
            2026,
            9,
            3,
            12,
            0,
            tzinfo=timezone.utc,
        ),
        finalised_by_id=12,
    )

    payload = service._feedback_to_dict(
        feedback,
    )

    assert payload["id"] == feedback.id
    assert payload["created_by_name"] == "Teacher One"
    assert payload["updated_by_id"] == 11
    assert payload["finalised_by_id"] == 12


def test_question_feedback_serialisation():
    feedback = _question_feedback()

    payload = service._question_feedback_to_dict(
        feedback,
    )

    assert payload["id"] == feedback.id
    assert payload["response_id"] == feedback.response_id
    assert payload["feedback_text"] == "Correct method."


# ---------------------------------------------------------------------------
# Overall feedback creation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_feedback_rejects_duplicate(
    db_session: AsyncSession,
    monkeypatch,
):
    teacher = _teacher()

    _patch_repository(
        monkeypatch,
        overall_feedback=_feedback(),
    )

    async def fake_context(
        db,
        *,
        script_id,
        school_id,
    ):
        return _script_context(
            school_id=school_id,
            teacher_id=teacher.id,
        )

    monkeypatch.setattr(
        service,
        "_get_script_context",
        fake_context,
    )

    with pytest.raises(
        HTTPException,
    ) as exc:
        await service.create_assessment_feedback(
            db_session,
            teacher,
            script_id=500,
            overall_comment="Good work.",
        )

    assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_create_feedback_normalises_values(
    db_session: AsyncSession,
    monkeypatch,
):
    teacher = _teacher()

    calls = _patch_repository(
        monkeypatch,
        overall_feedback=None,
    )

    async def fake_context(
        db,
        *,
        script_id,
        school_id,
    ):
        return _script_context(
            school_id=school_id,
            teacher_id=teacher.id,
        )

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

    refreshed = _feedback(
        feedback_id=99,
        created_by_id=teacher.id,
    )

    monkeypatch.setattr(
        service,
        "_get_script_context",
        fake_context,
    )
    monkeypatch.setattr(
        service,
        "_commit_feedback_change",
        fake_commit,
    )
    monkeypatch.setattr(
        db_session,
        "refresh",
        fake_refresh,
    )

    async def fake_reload(
        self,
        feedback_id,
        school_id,
        *,
        include_relationships=True,
    ):
        return refreshed

    monkeypatch.setattr(
        service.AssessmentFeedbackRepository,
        "get_feedback_by_id_and_school",
        fake_reload,
        raising=False,
    )

    result = await service.create_assessment_feedback(
        db_session,
        teacher,
        script_id=500,
        overall_comment="  Very good work.  ",
        strengths=" Strong mechanics. ",
        areas_for_improvement="   ",
        next_steps=" Practise momentum. ",
        include_with_result=True,
    )

    create_calls = [call for call in calls if call[0] == "create_feedback"]

    assert len(create_calls) == 1

    call = create_calls[0]

    assert call[4] == "Very good work."
    assert call[5] == "Strong mechanics."
    assert call[6] is None
    assert call[7] == "Practise momentum."
    assert call[8] is True
    assert call[9] == AssessmentFeedbackStatus.DRAFT
    assert result["id"] == 99


# ---------------------------------------------------------------------------
# Overall feedback reads
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_feedback_returns_serialised_payload(
    db_session: AsyncSession,
    monkeypatch,
):
    teacher = _teacher()
    feedback = _feedback()

    async def fake_get(
        db,
        current_user,
        *,
        feedback_id,
        school_id=None,
    ):
        return feedback

    monkeypatch.setattr(
        service,
        "_get_feedback_or_404",
        fake_get,
    )

    result = await service.get_assessment_feedback(
        db_session,
        teacher,
        feedback_id=feedback.id,
    )

    assert result["id"] == feedback.id
    assert result["script_id"] == feedback.script_id
    assert result["status"] == AssessmentFeedbackStatus.DRAFT


@pytest.mark.asyncio
async def test_get_feedback_for_script_returns_404_when_missing(
    db_session: AsyncSession,
    monkeypatch,
):
    teacher = _teacher()

    _patch_repository(
        monkeypatch,
        overall_feedback=None,
    )

    async def fake_context(
        db,
        *,
        script_id,
        school_id,
    ):
        return _script_context(
            school_id=school_id,
            teacher_id=teacher.id,
        )

    monkeypatch.setattr(
        service,
        "_get_script_context",
        fake_context,
    )

    with pytest.raises(
        HTTPException,
    ) as exc:
        await service.get_assessment_feedback_for_script(
            db_session,
            teacher,
            script_id=500,
        )

    assert exc.value.status_code == 404


# ---------------------------------------------------------------------------
# Overall feedback update
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_update_feedback_supports_explicit_clearing(
    db_session: AsyncSession,
    monkeypatch,
):
    teacher = _teacher()

    feedback = _feedback()

    calls = _patch_repository(
        monkeypatch,
        overall_feedback=feedback,
    )

    async def fake_authorised(
        db,
        current_user,
        *,
        feedback_id,
        school_id=None,
    ):
        return feedback

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
        "_get_feedback_or_404",
        fake_authorised,
    )
    monkeypatch.setattr(
        service,
        "_commit_feedback_change",
        fake_commit,
    )
    monkeypatch.setattr(
        db_session,
        "refresh",
        fake_refresh,
    )

    result = await service.update_assessment_feedback(
        db_session,
        teacher,
        feedback_id=feedback.id,
        overall_comment=None,
        strengths=None,
        areas_for_improvement=None,
        next_steps=None,
    )

    update_call = [call for call in calls if call[0] == "update_feedback"][0]

    assert update_call[1] is None
    assert update_call[2] is None
    assert update_call[3] is None
    assert update_call[4] is None

    assert result["overall_comment"] is None
    assert result["strengths"] is None
    assert result["areas_for_improvement"] is None
    assert result["next_steps"] is None


@pytest.mark.asyncio
async def test_update_feedback_preserves_unsupplied_fields(
    db_session: AsyncSession,
    monkeypatch,
):
    teacher = _teacher()

    feedback = _feedback()

    calls = _patch_repository(
        monkeypatch,
        overall_feedback=feedback,
    )

    async def fake_authorised(
        db,
        current_user,
        *,
        feedback_id,
        school_id=None,
    ):
        return feedback

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
        "_get_feedback_or_404",
        fake_authorised,
    )
    monkeypatch.setattr(
        service,
        "_commit_feedback_change",
        fake_commit,
    )
    monkeypatch.setattr(
        db_session,
        "refresh",
        fake_refresh,
    )

    await service.update_assessment_feedback(
        db_session,
        teacher,
        feedback_id=feedback.id,
        overall_comment="Updated.",
    )

    update_call = [call for call in calls if call[0] == "update_feedback"][0]

    assert update_call[1] == "Updated."
    assert update_call[2] is _UNSET
    assert update_call[3] is _UNSET
    assert update_call[4] is _UNSET
    assert update_call[5] is _UNSET


@pytest.mark.asyncio
async def test_finalised_feedback_cannot_be_edited(
    db_session: AsyncSession,
    monkeypatch,
):
    teacher = _teacher()

    feedback = _feedback(
        status_value=AssessmentFeedbackStatus.FINALISED,
    )

    async def fake_authorised(
        db,
        current_user,
        *,
        feedback_id,
        school_id=None,
    ):
        return feedback

    monkeypatch.setattr(
        service,
        "_get_feedback_or_404",
        fake_authorised,
    )

    with pytest.raises(
        HTTPException,
    ) as exc:
        await service.update_assessment_feedback(
            db_session,
            teacher,
            feedback_id=feedback.id,
            overall_comment="Changed",
        )

    assert exc.value.status_code == 409


# ---------------------------------------------------------------------------
# Finalise / reopen
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_finalise_feedback_sets_audit_fields(
    db_session: AsyncSession,
    monkeypatch,
):
    teacher = _teacher()

    feedback = _feedback(
        status_value=AssessmentFeedbackStatus.DRAFT,
    )

    calls = _patch_repository(
        monkeypatch,
        overall_feedback=feedback,
    )

    async def fake_authorised(
        db,
        current_user,
        *,
        feedback_id,
        school_id=None,
    ):
        return feedback

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

    fixed_now = datetime(
        2026,
        9,
        10,
        12,
        0,
        tzinfo=timezone.utc,
    )

    monkeypatch.setattr(
        service,
        "_get_feedback_or_404",
        fake_authorised,
    )
    monkeypatch.setattr(
        service,
        "_commit_feedback_change",
        fake_commit,
    )
    monkeypatch.setattr(
        service,
        "_utc_now",
        lambda: fixed_now,
    )
    monkeypatch.setattr(
        db_session,
        "refresh",
        fake_refresh,
    )

    result = await service.finalise_assessment_feedback(
        db_session,
        teacher,
        feedback_id=feedback.id,
    )

    update_call = [call for call in calls if call[0] == "update_feedback"][0]

    assert update_call[6] == AssessmentFeedbackStatus.FINALISED
    assert update_call[7] == teacher.id
    assert update_call[8] == fixed_now
    assert update_call[9] == teacher.id

    assert result["status"] == AssessmentFeedbackStatus.FINALISED


@pytest.mark.asyncio
async def test_empty_feedback_cannot_be_finalised(
    db_session: AsyncSession,
    monkeypatch,
):
    teacher = _teacher()

    feedback = _feedback(
        overall_comment=None,
        strengths=None,
        areas_for_improvement=None,
        next_steps=None,
    )

    async def fake_authorised(
        db,
        current_user,
        *,
        feedback_id,
        school_id=None,
    ):
        return feedback

    monkeypatch.setattr(
        service,
        "_get_feedback_or_404",
        fake_authorised,
    )

    with pytest.raises(
        HTTPException,
    ) as exc:
        await service.finalise_assessment_feedback(
            db_session,
            teacher,
            feedback_id=feedback.id,
        )

    assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_archived_feedback_cannot_be_finalised(
    db_session: AsyncSession,
    monkeypatch,
):
    feedback = _feedback(
        status_value=AssessmentFeedbackStatus.ARCHIVED,
    )

    async def fake_authorised(
        db,
        current_user,
        *,
        feedback_id,
        school_id=None,
    ):
        return feedback

    monkeypatch.setattr(
        service,
        "_get_feedback_or_404",
        fake_authorised,
    )

    with pytest.raises(
        HTTPException,
    ) as exc:
        await service.finalise_assessment_feedback(
            db_session,
            _teacher(),
            feedback_id=feedback.id,
        )

    assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_reopen_finalised_feedback_clears_finalisation_metadata(
    db_session: AsyncSession,
    monkeypatch,
):
    teacher = _teacher()

    feedback = _feedback(
        status_value=AssessmentFeedbackStatus.FINALISED,
        finalised_at=datetime(
            2026,
            9,
            9,
            tzinfo=timezone.utc,
        ),
        finalised_by_id=teacher.id,
    )

    calls = _patch_repository(
        monkeypatch,
        overall_feedback=feedback,
    )

    async def fake_authorised(
        db,
        current_user,
        *,
        feedback_id,
        school_id=None,
    ):
        return feedback

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
        "_get_feedback_or_404",
        fake_authorised,
    )
    monkeypatch.setattr(
        service,
        "_commit_feedback_change",
        fake_commit,
    )
    monkeypatch.setattr(
        db_session,
        "refresh",
        fake_refresh,
    )

    result = await service.reopen_assessment_feedback(
        db_session,
        teacher,
        feedback_id=feedback.id,
    )

    update_call = [call for call in calls if call[0] == "update_feedback"][0]

    assert update_call[6] == AssessmentFeedbackStatus.DRAFT
    assert update_call[7] == teacher.id
    assert update_call[8] is None
    assert update_call[9] is None

    assert result["status"] == AssessmentFeedbackStatus.DRAFT
    assert result["finalised_at"] is None
    assert result["finalised_by_id"] is None


# ---------------------------------------------------------------------------
# Overall delete
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_delete_feedback_delegates_to_repository(
    db_session: AsyncSession,
    monkeypatch,
):
    feedback = _feedback()

    calls = _patch_repository(
        monkeypatch,
        overall_feedback=feedback,
    )

    async def fake_authorised(
        db,
        current_user,
        *,
        feedback_id,
        school_id=None,
    ):
        return feedback

    async def fake_commit(
        db,
        *,
        duplicate_detail,
    ):
        return None

    monkeypatch.setattr(
        service,
        "_get_feedback_or_404",
        fake_authorised,
    )
    monkeypatch.setattr(
        service,
        "_commit_feedback_change",
        fake_commit,
    )

    await service.delete_assessment_feedback(
        db_session,
        _teacher(),
        feedback_id=feedback.id,
    )

    assert (
        "delete_feedback",
        feedback.id,
    ) in calls


@pytest.mark.asyncio
async def test_finalised_feedback_cannot_be_deleted(
    db_session: AsyncSession,
    monkeypatch,
):
    feedback = _feedback(
        status_value=AssessmentFeedbackStatus.FINALISED,
    )

    async def fake_authorised(
        db,
        current_user,
        *,
        feedback_id,
        school_id=None,
    ):
        return feedback

    monkeypatch.setattr(
        service,
        "_get_feedback_or_404",
        fake_authorised,
    )

    with pytest.raises(
        HTTPException,
    ) as exc:
        await service.delete_assessment_feedback(
            db_session,
            _teacher(),
            feedback_id=feedback.id,
        )

    assert exc.value.status_code == 409


# ---------------------------------------------------------------------------
# Question feedback creation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_question_feedback_rejects_duplicate(
    db_session: AsyncSession,
    monkeypatch,
):
    teacher = _teacher()

    _patch_repository(
        monkeypatch,
        question_feedback=_question_feedback(),
    )

    async def fake_context(
        db,
        *,
        response_id,
        school_id,
    ):
        return _response_context(
            school_id=school_id,
            teacher_id=teacher.id,
        )

    monkeypatch.setattr(
        service,
        "_get_response_context",
        fake_context,
    )

    with pytest.raises(
        HTTPException,
    ) as exc:
        await service.create_assessment_question_feedback(
            db_session,
            teacher,
            response_id=600,
            feedback_text="Good answer.",
        )

    assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_create_question_feedback_normalises_values(
    db_session: AsyncSession,
    monkeypatch,
):
    teacher = _teacher()

    calls = _patch_repository(
        monkeypatch,
        question_feedback=None,
    )

    async def fake_context(
        db,
        *,
        response_id,
        school_id,
    ):
        return _response_context(
            school_id=school_id,
            teacher_id=teacher.id,
        )

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

    refreshed = _question_feedback(
        question_feedback_id=199,
        created_by_id=teacher.id,
    )

    monkeypatch.setattr(
        service,
        "_get_response_context",
        fake_context,
    )
    monkeypatch.setattr(
        service,
        "_commit_feedback_change",
        fake_commit,
    )
    monkeypatch.setattr(
        db_session,
        "refresh",
        fake_refresh,
    )

    async def fake_reload(
        self,
        question_feedback_id,
        school_id,
        *,
        include_relationships=True,
    ):
        return refreshed

    monkeypatch.setattr(
        service.AssessmentFeedbackRepository,
        "get_question_feedback_by_id_and_school",
        fake_reload,
        raising=False,
    )

    result = await service.create_assessment_question_feedback(
        db_session,
        teacher,
        response_id=600,
        feedback_text=" Correct. ",
        strength=" Clear method. ",
        improvement="   ",
    )

    create_call = [call for call in calls if call[0] == "create_question_feedback"][0]

    assert create_call[4] == "Correct."
    assert create_call[5] == "Clear method."
    assert create_call[6] is None
    assert result["id"] == 199


# ---------------------------------------------------------------------------
# Question feedback reads
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_question_feedback_returns_payload(
    db_session: AsyncSession,
    monkeypatch,
):
    feedback = _question_feedback()

    async def fake_authorised(
        db,
        current_user,
        *,
        question_feedback_id,
        school_id=None,
    ):
        return feedback

    monkeypatch.setattr(
        service,
        "_get_question_feedback_or_404",
        fake_authorised,
    )

    result = await service.get_assessment_question_feedback(
        db_session,
        _teacher(),
        question_feedback_id=feedback.id,
    )

    assert result["id"] == feedback.id
    assert result["response_id"] == feedback.response_id


@pytest.mark.asyncio
async def test_get_question_feedback_for_response_returns_404_when_missing(
    db_session: AsyncSession,
    monkeypatch,
):
    teacher = _teacher()

    _patch_repository(
        monkeypatch,
        question_feedback=None,
    )

    async def fake_context(
        db,
        *,
        response_id,
        school_id,
    ):
        return _response_context(
            school_id=school_id,
            teacher_id=teacher.id,
        )

    monkeypatch.setattr(
        service,
        "_get_response_context",
        fake_context,
    )

    with pytest.raises(
        HTTPException,
    ) as exc:
        await service.get_assessment_question_feedback_for_response(
            db_session,
            teacher,
            response_id=600,
        )

    assert exc.value.status_code == 404


# ---------------------------------------------------------------------------
# Question feedback update
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_question_feedback_update_supports_explicit_clearing(
    db_session: AsyncSession,
    monkeypatch,
):
    feedback = _question_feedback()

    calls = _patch_repository(
        monkeypatch,
        question_feedback=feedback,
    )

    async def fake_authorised(
        db,
        current_user,
        *,
        question_feedback_id,
        school_id=None,
    ):
        return feedback

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
        "_get_question_feedback_or_404",
        fake_authorised,
    )
    monkeypatch.setattr(
        service,
        "_commit_feedback_change",
        fake_commit,
    )
    monkeypatch.setattr(
        db_session,
        "refresh",
        fake_refresh,
    )

    result = await service.update_assessment_question_feedback(
        db_session,
        _teacher(),
        question_feedback_id=feedback.id,
        feedback_text=None,
        strength=None,
        improvement=None,
    )

    update_call = [call for call in calls if call[0] == "update_question_feedback"][0]

    assert update_call[1] is None
    assert update_call[2] is None
    assert update_call[3] is None

    assert result["feedback_text"] is None
    assert result["strength"] is None
    assert result["improvement"] is None


@pytest.mark.asyncio
async def test_question_feedback_update_preserves_unsupplied_fields(
    db_session: AsyncSession,
    monkeypatch,
):
    feedback = _question_feedback()

    calls = _patch_repository(
        monkeypatch,
        question_feedback=feedback,
    )

    async def fake_authorised(
        db,
        current_user,
        *,
        question_feedback_id,
        school_id=None,
    ):
        return feedback

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
        "_get_question_feedback_or_404",
        fake_authorised,
    )
    monkeypatch.setattr(
        service,
        "_commit_feedback_change",
        fake_commit,
    )
    monkeypatch.setattr(
        db_session,
        "refresh",
        fake_refresh,
    )

    await service.update_assessment_question_feedback(
        db_session,
        _teacher(),
        question_feedback_id=feedback.id,
        feedback_text="Updated.",
    )

    update_call = [call for call in calls if call[0] == "update_question_feedback"][0]

    assert update_call[1] == "Updated."
    assert update_call[2] is _UNSET
    assert update_call[3] is _UNSET
    assert update_call[4] is _UNSET


# ---------------------------------------------------------------------------
# Question feedback delete
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_delete_question_feedback_delegates_to_repository(
    db_session: AsyncSession,
    monkeypatch,
):
    feedback = _question_feedback()

    calls = _patch_repository(
        monkeypatch,
        question_feedback=feedback,
    )

    async def fake_authorised(
        db,
        current_user,
        *,
        question_feedback_id,
        school_id=None,
    ):
        return feedback

    async def fake_commit(
        db,
        *,
        duplicate_detail,
    ):
        return None

    monkeypatch.setattr(
        service,
        "_get_question_feedback_or_404",
        fake_authorised,
    )
    monkeypatch.setattr(
        service,
        "_commit_feedback_change",
        fake_commit,
    )

    await service.delete_assessment_question_feedback(
        db_session,
        _teacher(),
        question_feedback_id=feedback.id,
    )

    assert (
        "delete_question_feedback",
        feedback.id,
    ) in calls


# ---------------------------------------------------------------------------
# Transaction handling
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_commit_integrity_error_becomes_conflict():
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
        await service._commit_feedback_change(
            db,
            duplicate_detail="Duplicate feedback.",
        )

    assert exc.value.status_code == 409
    assert exc.value.detail == "Duplicate feedback."
    assert rollback_called is True
