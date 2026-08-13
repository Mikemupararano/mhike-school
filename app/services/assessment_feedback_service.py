from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.assessment import Assessment
from app.models.assessment_candidate import (
    AssessmentCandidate,
    AssessmentScript,
)
from app.models.assessment_feedback import (
    AssessmentFeedback,
    AssessmentFeedbackStatus,
    AssessmentQuestionFeedback,
)
from app.models.assessment_response import AssessmentResponse
from app.models.course import Course
from app.models.user import User, UserRole
from app.repositories.assessment_feedback import (
    AssessmentFeedbackRepository,
    _UNSET,
)

# ---------------------------------------------------------------------------
# Time helper
# ---------------------------------------------------------------------------


def _utc_now() -> datetime:
    """
    Return the current timezone-aware UTC datetime.
    """

    return datetime.now(
        timezone.utc,
    )


# ---------------------------------------------------------------------------
# Role helpers
# ---------------------------------------------------------------------------


def _has_role(
    user: User,
    role: UserRole,
) -> bool:
    """
    Return whether the user currently holds the supplied role.
    """

    return role.value in set(
        user.roles,
    )


def _is_platform_admin(
    user: User,
) -> bool:
    return _has_role(
        user,
        UserRole.PLATFORM_ADMIN,
    )


def _is_school_admin(
    user: User,
) -> bool:
    return _has_role(
        user,
        UserRole.SCHOOL_ADMIN,
    )


def _is_teacher(
    user: User,
) -> bool:
    return _has_role(
        user,
        UserRole.TEACHER,
    )


def _is_student(
    user: User,
) -> bool:
    return _has_role(
        user,
        UserRole.STUDENT,
    )


def _is_parent(
    user: User,
) -> bool:
    return _has_role(
        user,
        UserRole.PARENT,
    )


def _ensure_feedback_staff_role(
    current_user: User,
) -> None:
    """
    Ensure the caller may manage assessment feedback.
    """

    if (
        _is_teacher(current_user)
        or _is_school_admin(current_user)
        or _is_platform_admin(current_user)
    ):
        return

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="You do not have permission to manage assessment feedback.",
    )


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def _validate_positive_integer(
    value: int,
    *,
    field_name: str,
) -> int:
    """
    Require a positive integer identifier.
    """

    if (
        not isinstance(
            value,
            int,
        )
        or isinstance(
            value,
            bool,
        )
        or value < 1
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"{field_name} must be a positive integer.",
        )

    return value


def _normalise_optional_text(
    value: str | None,
    *,
    field_name: str,
) -> str | None:
    """
    Trim optional feedback text.

    Blank strings are normalised to None.
    """

    if value is None:
        return None

    if not isinstance(
        value,
        str,
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"{field_name} must be a string or None.",
        )

    cleaned = value.strip()

    if not cleaned:
        return None

    return cleaned


def _validate_bool(
    value: bool,
    *,
    field_name: str,
) -> bool:
    """
    Require a strict boolean value.
    """

    if not isinstance(
        value,
        bool,
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"{field_name} must be a boolean.",
        )

    return value


# ---------------------------------------------------------------------------
# School scope
# ---------------------------------------------------------------------------


def _resolve_school_id(
    current_user: User,
    requested_school_id: int | None,
) -> int:
    """
    Resolve the school for a staff feedback operation.
    """

    if requested_school_id is not None:
        _validate_positive_integer(
            requested_school_id,
            field_name="school_id",
        )

    user_school_id = getattr(
        current_user,
        "school_id",
        None,
    )

    if _is_platform_admin(
        current_user,
    ):
        if requested_school_id is not None:
            return requested_school_id

        if user_school_id is not None:
            return int(
                user_school_id,
            )

        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="school_id is required for a platform administrator.",
        )

    if user_school_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="A school-scoped user must belong to a school.",
        )

    if requested_school_id is not None and requested_school_id != user_school_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You cannot manage assessment feedback for another school.",
        )

    return int(
        user_school_id,
    )


# ---------------------------------------------------------------------------
# Assessment-context lookup
# ---------------------------------------------------------------------------


async def _get_script_context(
    db: AsyncSession,
    *,
    script_id: int,
    school_id: int,
) -> dict[str, Any]:
    """
    Resolve a script through candidate, assessment and course.

    Every entity is checked explicitly rather than relying on a client
    supplied school identifier.
    """

    clean_script_id = _validate_positive_integer(
        script_id,
        field_name="script_id",
    )

    script = await db.get(
        AssessmentScript,
        clean_script_id,
    )

    if script is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assessment script not found.",
        )

    candidate = await db.get(
        AssessmentCandidate,
        script.candidate_id,
    )

    if candidate is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assessment candidate not found.",
        )

    assessment = await db.get(
        Assessment,
        candidate.assessment_id,
    )

    if assessment is None or assessment.school_id != school_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assessment script not found.",
        )

    course = await db.get(
        Course,
        assessment.course_id,
    )

    if course is None or course.school_id != school_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assessment course not found.",
        )

    return {
        "script": script,
        "candidate": candidate,
        "assessment": assessment,
        "course": course,
    }


async def _get_response_context(
    db: AsyncSession,
    *,
    response_id: int,
    school_id: int,
) -> dict[str, Any]:
    """
    Resolve one assessment response and its script context.
    """

    clean_response_id = _validate_positive_integer(
        response_id,
        field_name="response_id",
    )

    response = await db.get(
        AssessmentResponse,
        clean_response_id,
    )

    if response is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assessment response not found.",
        )

    context = await _get_script_context(
        db,
        script_id=response.script_id,
        school_id=school_id,
    )

    return {
        **context,
        "response": response,
    }


# ---------------------------------------------------------------------------
# Course ownership
# ---------------------------------------------------------------------------


def _ensure_feedback_course_access(
    current_user: User,
    course: Course,
) -> None:
    """
    Ensure a staff user may manage feedback for the course.

    Teachers may manage only courses they teach.

    School and platform administrators retain wider access.
    """

    if _is_school_admin(current_user) or _is_platform_admin(current_user):
        return

    if _is_teacher(current_user) and course.teacher_id == current_user.id:
        return

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="You can only manage assessment feedback for courses you teach.",
    )


# ---------------------------------------------------------------------------
# Transactions
# ---------------------------------------------------------------------------


async def _commit_feedback_change(
    db: AsyncSession,
    *,
    duplicate_detail: str,
) -> None:
    """
    Commit a feedback mutation safely.
    """

    try:
        await db.commit()

    except IntegrityError as exc:
        await db.rollback()

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=duplicate_detail,
        ) from exc

    except Exception:
        await db.rollback()
        raise


# ---------------------------------------------------------------------------
# Serialisation
# ---------------------------------------------------------------------------


def _feedback_to_dict(
    feedback: AssessmentFeedback,
) -> dict[str, Any]:
    """
    Serialise overall assessment feedback.
    """

    creator = getattr(
        feedback,
        "created_by",
        None,
    )

    updater = getattr(
        feedback,
        "updated_by",
        None,
    )

    finaliser = getattr(
        feedback,
        "finalised_by",
        None,
    )

    return {
        "id": feedback.id,
        "school_id": feedback.school_id,
        "script_id": feedback.script_id,
        "overall_comment": feedback.overall_comment,
        "strengths": feedback.strengths,
        "areas_for_improvement": feedback.areas_for_improvement,
        "next_steps": feedback.next_steps,
        "status": feedback.status,
        "include_with_result": feedback.include_with_result,
        "created_by_id": feedback.created_by_id,
        "created_by_name": (creator.full_name if creator is not None else None),
        "updated_by_id": feedback.updated_by_id,
        "updated_by_name": (updater.full_name if updater is not None else None),
        "finalised_at": feedback.finalised_at,
        "finalised_by_id": feedback.finalised_by_id,
        "finalised_by_name": (finaliser.full_name if finaliser is not None else None),
        "created_at": feedback.created_at,
        "updated_at": feedback.updated_at,
    }


def _question_feedback_to_dict(
    feedback: AssessmentQuestionFeedback,
) -> dict[str, Any]:
    """
    Serialise question-specific assessment feedback.
    """

    creator = getattr(
        feedback,
        "created_by",
        None,
    )

    updater = getattr(
        feedback,
        "updated_by",
        None,
    )

    return {
        "id": feedback.id,
        "school_id": feedback.school_id,
        "response_id": feedback.response_id,
        "feedback_text": feedback.feedback_text,
        "strength": feedback.strength,
        "improvement": feedback.improvement,
        "include_with_result": feedback.include_with_result,
        "created_by_id": feedback.created_by_id,
        "created_by_name": (creator.full_name if creator is not None else None),
        "updated_by_id": feedback.updated_by_id,
        "updated_by_name": (updater.full_name if updater is not None else None),
        "created_at": feedback.created_at,
        "updated_at": feedback.updated_at,
    }


# ---------------------------------------------------------------------------
# Authorised feedback lookup
# ---------------------------------------------------------------------------


async def _get_feedback_or_404(
    db: AsyncSession,
    current_user: User,
    *,
    feedback_id: int,
    school_id: int | None = None,
) -> AssessmentFeedback:
    """
    Return authorised overall feedback.
    """

    _ensure_feedback_staff_role(
        current_user,
    )

    effective_school_id = _resolve_school_id(
        current_user,
        school_id,
    )

    feedback = await AssessmentFeedbackRepository(
        db,
    ).get_feedback_by_id_and_school(
        _validate_positive_integer(
            feedback_id,
            field_name="feedback_id",
        ),
        effective_school_id,
        include_relationships=True,
    )

    if feedback is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assessment feedback not found.",
        )

    context = await _get_script_context(
        db,
        script_id=feedback.script_id,
        school_id=effective_school_id,
    )

    _ensure_feedback_course_access(
        current_user,
        context["course"],
    )

    return feedback


async def _get_question_feedback_or_404(
    db: AsyncSession,
    current_user: User,
    *,
    question_feedback_id: int,
    school_id: int | None = None,
) -> AssessmentQuestionFeedback:
    """
    Return authorised question-specific feedback.
    """

    _ensure_feedback_staff_role(
        current_user,
    )

    effective_school_id = _resolve_school_id(
        current_user,
        school_id,
    )

    feedback = await AssessmentFeedbackRepository(
        db,
    ).get_question_feedback_by_id_and_school(
        _validate_positive_integer(
            question_feedback_id,
            field_name="question_feedback_id",
        ),
        effective_school_id,
        include_relationships=True,
    )

    if feedback is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assessment question feedback not found.",
        )

    context = await _get_response_context(
        db,
        response_id=feedback.response_id,
        school_id=effective_school_id,
    )

    _ensure_feedback_course_access(
        current_user,
        context["course"],
    )

    return feedback


# ---------------------------------------------------------------------------
# Overall feedback create
# ---------------------------------------------------------------------------


async def create_assessment_feedback(
    db: AsyncSession,
    current_user: User,
    *,
    script_id: int,
    overall_comment: str | None = None,
    strengths: str | None = None,
    areas_for_improvement: str | None = None,
    next_steps: str | None = None,
    include_with_result: bool = True,
    school_id: int | None = None,
) -> dict[str, Any]:
    """
    Create structured feedback for one script.
    """

    _ensure_feedback_staff_role(
        current_user,
    )

    effective_school_id = _resolve_school_id(
        current_user,
        school_id,
    )

    context = await _get_script_context(
        db,
        script_id=script_id,
        school_id=effective_school_id,
    )

    _ensure_feedback_course_access(
        current_user,
        context["course"],
    )

    repository = AssessmentFeedbackRepository(
        db,
    )

    existing = await repository.get_feedback_by_script(
        script_id,
        school_id=effective_school_id,
        include_relationships=False,
    )

    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Assessment feedback already exists for this script.",
        )

    feedback = await repository.create_feedback(
        school_id=effective_school_id,
        script_id=script_id,
        created_by_id=current_user.id,
        overall_comment=_normalise_optional_text(
            overall_comment,
            field_name="overall_comment",
        ),
        strengths=_normalise_optional_text(
            strengths,
            field_name="strengths",
        ),
        areas_for_improvement=_normalise_optional_text(
            areas_for_improvement,
            field_name="areas_for_improvement",
        ),
        next_steps=_normalise_optional_text(
            next_steps,
            field_name="next_steps",
        ),
        include_with_result=_validate_bool(
            include_with_result,
            field_name="include_with_result",
        ),
        status=AssessmentFeedbackStatus.DRAFT,
    )

    await _commit_feedback_change(
        db,
        duplicate_detail="Assessment feedback already exists for this script.",
    )

    await db.refresh(
        feedback,
    )

    refreshed = await repository.get_feedback_by_id_and_school(
        feedback.id,
        effective_school_id,
        include_relationships=True,
    )

    if refreshed is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Assessment feedback was created but could not be reloaded.",
        )

    return _feedback_to_dict(
        refreshed,
    )


# ---------------------------------------------------------------------------
# Overall feedback reads
# ---------------------------------------------------------------------------


async def get_assessment_feedback(
    db: AsyncSession,
    current_user: User,
    *,
    feedback_id: int,
    school_id: int | None = None,
) -> dict[str, Any]:
    """
    Return one authorised overall feedback record.
    """

    feedback = await _get_feedback_or_404(
        db,
        current_user,
        feedback_id=feedback_id,
        school_id=school_id,
    )

    return _feedback_to_dict(
        feedback,
    )


async def get_assessment_feedback_for_script(
    db: AsyncSession,
    current_user: User,
    *,
    script_id: int,
    school_id: int | None = None,
) -> dict[str, Any]:
    """
    Return overall feedback for one authorised script.
    """

    _ensure_feedback_staff_role(
        current_user,
    )

    effective_school_id = _resolve_school_id(
        current_user,
        school_id,
    )

    context = await _get_script_context(
        db,
        script_id=script_id,
        school_id=effective_school_id,
    )

    _ensure_feedback_course_access(
        current_user,
        context["course"],
    )

    feedback = await AssessmentFeedbackRepository(
        db,
    ).get_feedback_by_script(
        script_id,
        school_id=effective_school_id,
        include_relationships=True,
    )

    if feedback is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assessment feedback not found.",
        )

    return _feedback_to_dict(
        feedback,
    )


# ---------------------------------------------------------------------------
# Overall feedback update
# ---------------------------------------------------------------------------


async def update_assessment_feedback(
    db: AsyncSession,
    current_user: User,
    *,
    feedback_id: int,
    overall_comment: str | None | object = _UNSET,
    strengths: str | None | object = _UNSET,
    areas_for_improvement: str | None | object = _UNSET,
    next_steps: str | None | object = _UNSET,
    include_with_result: bool | object = _UNSET,
    school_id: int | None = None,
) -> dict[str, Any]:
    """
    Partially update overall assessment feedback.

    Finalised feedback must first be returned to draft before its pedagogical
    content can be changed.
    """

    feedback = await _get_feedback_or_404(
        db,
        current_user,
        feedback_id=feedback_id,
        school_id=school_id,
    )

    if feedback.status == AssessmentFeedbackStatus.FINALISED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Finalised assessment feedback must be reopened before editing.",
        )

    clean_overall_comment: str | None | object = _UNSET
    clean_strengths: str | None | object = _UNSET
    clean_areas: str | None | object = _UNSET
    clean_next_steps: str | None | object = _UNSET
    clean_include: bool | object = _UNSET

    if overall_comment is not _UNSET:
        clean_overall_comment = _normalise_optional_text(
            overall_comment,
            field_name="overall_comment",
        )

    if strengths is not _UNSET:
        clean_strengths = _normalise_optional_text(
            strengths,
            field_name="strengths",
        )

    if areas_for_improvement is not _UNSET:
        clean_areas = _normalise_optional_text(
            areas_for_improvement,
            field_name="areas_for_improvement",
        )

    if next_steps is not _UNSET:
        clean_next_steps = _normalise_optional_text(
            next_steps,
            field_name="next_steps",
        )

    if include_with_result is not _UNSET:
        clean_include = _validate_bool(
            include_with_result,
            field_name="include_with_result",
        )

    repository = AssessmentFeedbackRepository(
        db,
    )

    await repository.update_feedback(
        feedback,
        overall_comment=clean_overall_comment,
        strengths=clean_strengths,
        areas_for_improvement=clean_areas,
        next_steps=clean_next_steps,
        include_with_result=clean_include,
        updated_by_id=current_user.id,
    )

    await _commit_feedback_change(
        db,
        duplicate_detail="Unable to update assessment feedback.",
    )

    await db.refresh(
        feedback,
    )

    refreshed = await repository.get_feedback_by_id_and_school(
        feedback.id,
        feedback.school_id,
        include_relationships=True,
    )

    if refreshed is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Assessment feedback was updated but could not be reloaded.",
        )

    return _feedback_to_dict(
        refreshed,
    )


# ---------------------------------------------------------------------------
# Finalise / reopen
# ---------------------------------------------------------------------------


async def finalise_assessment_feedback(
    db: AsyncSession,
    current_user: User,
    *,
    feedback_id: int,
    school_id: int | None = None,
) -> dict[str, Any]:
    """
    Finalise overall feedback.
    """

    feedback = await _get_feedback_or_404(
        db,
        current_user,
        feedback_id=feedback_id,
        school_id=school_id,
    )

    if feedback.status == AssessmentFeedbackStatus.ARCHIVED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Archived assessment feedback cannot be finalised.",
        )

    if feedback.status == AssessmentFeedbackStatus.FINALISED:
        return _feedback_to_dict(
            feedback,
        )

    if not any(
        (
            feedback.overall_comment,
            feedback.strengths,
            feedback.areas_for_improvement,
            feedback.next_steps,
        )
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Assessment feedback cannot be finalised while all feedback fields are empty.",
        )

    now = _utc_now()

    repository = AssessmentFeedbackRepository(
        db,
    )

    await repository.update_feedback(
        feedback,
        status=AssessmentFeedbackStatus.FINALISED,
        updated_by_id=current_user.id,
        finalised_at=now,
        finalised_by_id=current_user.id,
    )

    await _commit_feedback_change(
        db,
        duplicate_detail="Unable to finalise assessment feedback.",
    )

    await db.refresh(
        feedback,
    )

    refreshed = await repository.get_feedback_by_id_and_school(
        feedback.id,
        feedback.school_id,
        include_relationships=True,
    )

    if refreshed is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Assessment feedback was finalised but could not be reloaded.",
        )

    return _feedback_to_dict(
        refreshed,
    )


async def reopen_assessment_feedback(
    db: AsyncSession,
    current_user: User,
    *,
    feedback_id: int,
    school_id: int | None = None,
) -> dict[str, Any]:
    """
    Return finalised feedback to draft status for further editing.
    """

    feedback = await _get_feedback_or_404(
        db,
        current_user,
        feedback_id=feedback_id,
        school_id=school_id,
    )

    if feedback.status == AssessmentFeedbackStatus.ARCHIVED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Archived assessment feedback cannot be reopened.",
        )

    if feedback.status == AssessmentFeedbackStatus.DRAFT:
        return _feedback_to_dict(
            feedback,
        )

    repository = AssessmentFeedbackRepository(
        db,
    )

    await repository.update_feedback(
        feedback,
        status=AssessmentFeedbackStatus.DRAFT,
        updated_by_id=current_user.id,
        finalised_at=None,
        finalised_by_id=None,
    )

    await _commit_feedback_change(
        db,
        duplicate_detail="Unable to reopen assessment feedback.",
    )

    await db.refresh(
        feedback,
    )

    refreshed = await repository.get_feedback_by_id_and_school(
        feedback.id,
        feedback.school_id,
        include_relationships=True,
    )

    if refreshed is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Assessment feedback was reopened but could not be reloaded.",
        )

    return _feedback_to_dict(
        refreshed,
    )


# ---------------------------------------------------------------------------
# Overall feedback delete
# ---------------------------------------------------------------------------


async def delete_assessment_feedback(
    db: AsyncSession,
    current_user: User,
    *,
    feedback_id: int,
    school_id: int | None = None,
) -> None:
    """
    Delete non-finalised overall feedback.
    """

    feedback = await _get_feedback_or_404(
        db,
        current_user,
        feedback_id=feedback_id,
        school_id=school_id,
    )

    if feedback.status == AssessmentFeedbackStatus.FINALISED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Finalised assessment feedback must be reopened before deletion.",
        )

    await AssessmentFeedbackRepository(
        db,
    ).delete_feedback(
        feedback,
    )

    await _commit_feedback_change(
        db,
        duplicate_detail="Unable to delete assessment feedback.",
    )


# ---------------------------------------------------------------------------
# Question feedback create
# ---------------------------------------------------------------------------


async def create_assessment_question_feedback(
    db: AsyncSession,
    current_user: User,
    *,
    response_id: int,
    feedback_text: str | None = None,
    strength: str | None = None,
    improvement: str | None = None,
    include_with_result: bool = True,
    school_id: int | None = None,
) -> dict[str, Any]:
    """
    Create feedback for one assessment response.
    """

    _ensure_feedback_staff_role(
        current_user,
    )

    effective_school_id = _resolve_school_id(
        current_user,
        school_id,
    )

    context = await _get_response_context(
        db,
        response_id=response_id,
        school_id=effective_school_id,
    )

    _ensure_feedback_course_access(
        current_user,
        context["course"],
    )

    repository = AssessmentFeedbackRepository(
        db,
    )

    existing = await repository.get_question_feedback_by_response(
        response_id,
        school_id=effective_school_id,
        include_relationships=False,
    )

    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Assessment question feedback already exists for this response.",
        )

    feedback = await repository.create_question_feedback(
        school_id=effective_school_id,
        response_id=response_id,
        created_by_id=current_user.id,
        feedback_text=_normalise_optional_text(
            feedback_text,
            field_name="feedback_text",
        ),
        strength=_normalise_optional_text(
            strength,
            field_name="strength",
        ),
        improvement=_normalise_optional_text(
            improvement,
            field_name="improvement",
        ),
        include_with_result=_validate_bool(
            include_with_result,
            field_name="include_with_result",
        ),
    )

    await _commit_feedback_change(
        db,
        duplicate_detail=(
            "Assessment question feedback already exists for this response."
        ),
    )

    await db.refresh(
        feedback,
    )

    refreshed = await repository.get_question_feedback_by_id_and_school(
        feedback.id,
        effective_school_id,
        include_relationships=True,
    )

    if refreshed is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                "Assessment question feedback was created but could not be " "reloaded."
            ),
        )

    return _question_feedback_to_dict(
        refreshed,
    )


# ---------------------------------------------------------------------------
# Question feedback reads
# ---------------------------------------------------------------------------


async def get_assessment_question_feedback(
    db: AsyncSession,
    current_user: User,
    *,
    question_feedback_id: int,
    school_id: int | None = None,
) -> dict[str, Any]:
    """
    Return one authorised question-feedback record.
    """

    feedback = await _get_question_feedback_or_404(
        db,
        current_user,
        question_feedback_id=question_feedback_id,
        school_id=school_id,
    )

    return _question_feedback_to_dict(
        feedback,
    )


async def get_assessment_question_feedback_for_response(
    db: AsyncSession,
    current_user: User,
    *,
    response_id: int,
    school_id: int | None = None,
) -> dict[str, Any]:
    """
    Return question feedback for one authorised assessment response.
    """

    _ensure_feedback_staff_role(
        current_user,
    )

    effective_school_id = _resolve_school_id(
        current_user,
        school_id,
    )

    context = await _get_response_context(
        db,
        response_id=response_id,
        school_id=effective_school_id,
    )

    _ensure_feedback_course_access(
        current_user,
        context["course"],
    )

    feedback = await AssessmentFeedbackRepository(
        db,
    ).get_question_feedback_by_response(
        response_id,
        school_id=effective_school_id,
        include_relationships=True,
    )

    if feedback is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assessment question feedback not found.",
        )

    return _question_feedback_to_dict(
        feedback,
    )


# ---------------------------------------------------------------------------
# Question feedback update
# ---------------------------------------------------------------------------


async def update_assessment_question_feedback(
    db: AsyncSession,
    current_user: User,
    *,
    question_feedback_id: int,
    feedback_text: str | None | object = _UNSET,
    strength: str | None | object = _UNSET,
    improvement: str | None | object = _UNSET,
    include_with_result: bool | object = _UNSET,
    school_id: int | None = None,
) -> dict[str, Any]:
    """
    Partially update question-specific feedback.
    """

    feedback = await _get_question_feedback_or_404(
        db,
        current_user,
        question_feedback_id=question_feedback_id,
        school_id=school_id,
    )

    clean_feedback_text: str | None | object = _UNSET
    clean_strength: str | None | object = _UNSET
    clean_improvement: str | None | object = _UNSET
    clean_include: bool | object = _UNSET

    if feedback_text is not _UNSET:
        clean_feedback_text = _normalise_optional_text(
            feedback_text,
            field_name="feedback_text",
        )

    if strength is not _UNSET:
        clean_strength = _normalise_optional_text(
            strength,
            field_name="strength",
        )

    if improvement is not _UNSET:
        clean_improvement = _normalise_optional_text(
            improvement,
            field_name="improvement",
        )

    if include_with_result is not _UNSET:
        clean_include = _validate_bool(
            include_with_result,
            field_name="include_with_result",
        )

    repository = AssessmentFeedbackRepository(
        db,
    )

    await repository.update_question_feedback(
        feedback,
        feedback_text=clean_feedback_text,
        strength=clean_strength,
        improvement=clean_improvement,
        include_with_result=clean_include,
        updated_by_id=current_user.id,
    )

    await _commit_feedback_change(
        db,
        duplicate_detail="Unable to update assessment question feedback.",
    )

    await db.refresh(
        feedback,
    )

    refreshed = await repository.get_question_feedback_by_id_and_school(
        feedback.id,
        feedback.school_id,
        include_relationships=True,
    )

    if refreshed is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                "Assessment question feedback was updated but could not be " "reloaded."
            ),
        )

    return _question_feedback_to_dict(
        refreshed,
    )


# ---------------------------------------------------------------------------
# Question feedback delete
# ---------------------------------------------------------------------------


async def delete_assessment_question_feedback(
    db: AsyncSession,
    current_user: User,
    *,
    question_feedback_id: int,
    school_id: int | None = None,
) -> None:
    """
    Delete question-specific feedback.
    """

    feedback = await _get_question_feedback_or_404(
        db,
        current_user,
        question_feedback_id=question_feedback_id,
        school_id=school_id,
    )

    await AssessmentFeedbackRepository(
        db,
    ).delete_question_feedback(
        feedback,
    )

    await _commit_feedback_change(
        db,
        duplicate_detail="Unable to delete assessment question feedback.",
    )
