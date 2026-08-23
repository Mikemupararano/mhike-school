from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.assessment import Assessment
from app.models.assessment_candidate import (
    AssessmentCandidate,
    AssessmentScript,
    AssessmentScriptStatus,
)
from app.models.assessment_question import AssessmentQuestion
from app.models.assessment_response import (
    AssessmentResponse,
    AssessmentResponseStatus,
    MarkingDecision,
    MarkingDecisionStatus,
)
from app.models.mark_scheme import MarkSchemeItem
from app.models.mark_scheme_award import MarkSchemeItemAward
from app.models.user import User, UserRole
from app.repositories.assessment_candidate import AssessmentCandidateRepository
from app.repositories.assessment_marking import AssessmentMarkingRepository
from app.repositories.course import CourseRepository

# ----------------------------------------------------------------------
# Role helpers
# ----------------------------------------------------------------------


def has_role(
    user: User,
    role: UserRole,
) -> bool:
    """
    Return whether the user currently has the supplied role.
    """

    return role.value in set(user.roles)


def is_platform_admin(
    user: User,
) -> bool:
    """
    Return whether the user has platform-administrator scope.
    """

    return has_role(
        user,
        UserRole.PLATFORM_ADMIN,
    )


def is_school_admin(
    user: User,
) -> bool:
    """
    Return whether the user has school-administrator scope.
    """

    return has_role(
        user,
        UserRole.SCHOOL_ADMIN,
    )


def is_teacher_without_admin_scope(
    user: User,
) -> bool:
    """
    Return whether the user is a teacher without administrator scope.
    """

    return (
        has_role(
            user,
            UserRole.TEACHER,
        )
        and not is_school_admin(user)
        and not is_platform_admin(user)
    )


def _ensure_marking_staff_role(
    current_user: User,
) -> None:
    """
    Ensure the user has a role capable of assessment marking.
    """

    if (
        has_role(
            current_user,
            UserRole.TEACHER,
        )
        or is_school_admin(current_user)
        or is_platform_admin(current_user)
    ):
        return

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="You do not have permission to mark assessments",
    )


# ----------------------------------------------------------------------
# General helpers
# ----------------------------------------------------------------------


def _utc_now() -> datetime:
    """
    Return the current timezone-aware UTC timestamp.
    """

    return datetime.now(
        timezone.utc,
    )


def _normalise_decimal(
    value: Decimal | int | float | str,
    *,
    field_name: str,
) -> Decimal:
    """
    Return a finite, non-negative Decimal.
    """

    if isinstance(value, bool):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"{field_name} must be numeric",
        )

    try:
        result = Decimal(
            str(value),
        )
    except (
        InvalidOperation,
        TypeError,
        ValueError,
    ) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"{field_name} must be numeric",
        ) from exc

    if not result.is_finite():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"{field_name} must be finite",
        )

    if result < Decimal("0"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"{field_name} cannot be negative",
        )

    return result


def _normalise_response_status(
    value: AssessmentResponseStatus | str,
) -> AssessmentResponseStatus:
    """
    Convert input into an AssessmentResponseStatus.
    """

    if isinstance(
        value,
        AssessmentResponseStatus,
    ):
        return value

    try:
        return AssessmentResponseStatus(
            value,
        )
    except (TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid assessment response status: {value!r}",
        ) from exc


def _normalise_decision_status(
    value: MarkingDecisionStatus | str,
) -> MarkingDecisionStatus:
    """
    Convert input into a MarkingDecisionStatus.
    """

    if isinstance(
        value,
        MarkingDecisionStatus,
    ):
        return value

    try:
        return MarkingDecisionStatus(
            value,
        )
    except (TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid marking decision status: {value!r}",
        ) from exc


# ----------------------------------------------------------------------
# Core entity lookup
# ----------------------------------------------------------------------


async def _get_script_or_404(
    db: AsyncSession,
    script_id: int,
    *,
    include_relationships: bool = True,
) -> AssessmentScript:
    """
    Return an assessment script or raise a 404 response.
    """

    script = await AssessmentCandidateRepository(
        db,
    ).get_script_by_id(
        script_id,
        include_relationships=include_relationships,
    )

    if script is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assessment script not found",
        )

    return script


async def _get_candidate_or_404(
    db: AsyncSession,
    candidate_id: int,
) -> AssessmentCandidate:
    """
    Return an assessment candidate or raise a 404 response.
    """

    candidate = await AssessmentCandidateRepository(
        db,
    ).get_candidate_by_id(
        candidate_id,
        include_relationships=True,
    )

    if candidate is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assessment candidate not found",
        )

    return candidate


async def _get_question_or_404(
    db: AsyncSession,
    question_id: int,
) -> AssessmentQuestion:
    """
    Return an assessment question or raise a 404 response.
    """

    question = await AssessmentMarkingRepository(
        db,
    ).get_question_by_id(
        question_id,
        include_mark_scheme=True,
    )

    if question is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assessment question not found",
        )

    return question


async def _get_response_or_404(
    db: AsyncSession,
    response_id: int,
    *,
    include_relationships: bool = True,
) -> AssessmentResponse:
    """
    Return an assessment response or raise a 404 response.
    """

    response = await AssessmentMarkingRepository(
        db,
    ).get_response_by_id(
        response_id,
        include_relationships=include_relationships,
    )

    if response is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assessment response not found",
        )

    return response


async def _get_decision_or_404(
    db: AsyncSession,
    decision_id: int,
    *,
    include_relationships: bool = True,
) -> MarkingDecision:
    """
    Return a marking decision or raise a 404 response.
    """

    decision = await AssessmentMarkingRepository(
        db,
    ).get_decision_by_id(
        decision_id,
        include_relationships=include_relationships,
    )

    if decision is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Marking decision not found",
        )

    return decision


async def _get_award_or_404(
    db: AsyncSession,
    award_id: int,
) -> MarkSchemeItemAward:
    """
    Return a mark-scheme item award or raise a 404 response.
    """

    award = await AssessmentMarkingRepository(
        db,
    ).get_award_by_id(
        award_id,
        include_relationships=True,
    )

    if award is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mark-scheme item award not found",
        )

    return award


async def _get_mark_scheme_item_or_404(
    db: AsyncSession,
    item_id: int,
) -> MarkSchemeItem:
    """
    Return a mark-scheme item or raise a 404 response.
    """

    item = await AssessmentMarkingRepository(
        db,
    ).get_mark_scheme_item_by_id(
        item_id,
        include_mark_scheme=True,
    )

    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mark-scheme item not found",
        )

    return item


# ----------------------------------------------------------------------
# School / course / assessment marking scope
# ----------------------------------------------------------------------


async def _ensure_assessment_marking_access(
    db: AsyncSession,
    current_user: User,
    assessment: Assessment,
) -> None:
    """
    Ensure the user may mark work belonging to an assessment.

    Teachers without administrative scope may mark only assessments for
    courses they teach. School administrators may mark within their school.
    Platform administrators may operate across schools.
    """

    _ensure_marking_staff_role(
        current_user,
    )

    if (
        not is_platform_admin(current_user)
        and assessment.school_id != current_user.school_id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Assessment does not belong to your school",
        )

    course = await CourseRepository(
        db,
    ).get_by_id(
        assessment.course_id,
        include_relationships=False,
    )

    if course is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found",
        )

    if course.school_id != assessment.school_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Assessment and course school scope are inconsistent",
        )

    if (
        is_teacher_without_admin_scope(current_user)
        and course.teacher_id != current_user.id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only mark assessments for your own courses",
        )


async def _ensure_script_marking_access(
    db: AsyncSession,
    current_user: User,
    script: AssessmentScript,
) -> AssessmentCandidate:
    """
    Ensure the user may mark the supplied script.
    """

    candidate = await _get_candidate_or_404(
        db,
        script.candidate_id,
    )

    assessment = candidate.assessment

    if assessment is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Assessment candidate is not linked to an assessment",
        )

    await _ensure_assessment_marking_access(
        db,
        current_user,
        assessment,
    )

    return candidate


async def _ensure_response_marking_access(
    db: AsyncSession,
    current_user: User,
    response: AssessmentResponse,
) -> AssessmentScript:
    """
    Ensure the user may access marking for a response.
    """

    script = await _get_script_or_404(
        db,
        response.script_id,
        include_relationships=True,
    )

    await _ensure_script_marking_access(
        db,
        current_user,
        script,
    )

    return script


async def _ensure_decision_marking_access(
    db: AsyncSession,
    current_user: User,
    decision: MarkingDecision,
) -> AssessmentResponse:
    """
    Ensure the user may access a marking decision.
    """

    response = await _get_response_or_404(
        db,
        decision.response_id,
        include_relationships=True,
    )

    await _ensure_response_marking_access(
        db,
        current_user,
        response,
    )

    return response


# ----------------------------------------------------------------------
# Response integrity
# ----------------------------------------------------------------------


async def _validate_script_question_scope(
    db: AsyncSession,
    *,
    script: AssessmentScript,
    question: AssessmentQuestion,
) -> AssessmentCandidate:
    """
    Ensure the question belongs to the script's assessment.
    """

    candidate = await _get_candidate_or_404(
        db,
        script.candidate_id,
    )

    if question.assessment_id != candidate.assessment_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Question does not belong to the script assessment",
        )

    return candidate


def _ensure_question_is_markable(
    question: AssessmentQuestion,
) -> None:
    """
    Ensure a response may be captured against the question.
    """

    if not question.is_markable:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Responses cannot be captured for a non-markable question",
        )


# ----------------------------------------------------------------------
# Response capture
# ----------------------------------------------------------------------


async def create_response(
    db: AsyncSession,
    current_user: User,
    script_id: int,
    question_id: int,
    *,
    response_text: str | None = None,
    response_data: str | None = None,
    source_reference: str | None = None,
) -> AssessmentResponse:
    """
    Create one response for a script/question pair.
    """

    script = await _get_script_or_404(
        db,
        script_id,
        include_relationships=True,
    )

    await _ensure_script_marking_access(
        db,
        current_user,
        script,
    )

    question = await _get_question_or_404(
        db,
        question_id,
    )

    await _validate_script_question_scope(
        db,
        script=script,
        question=question,
    )

    _ensure_question_is_markable(
        question,
    )

    if script.status == AssessmentScriptStatus.FINALISED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Responses cannot be added to a finalised script",
        )

    repository = AssessmentMarkingRepository(
        db,
    )

    existing = await repository.get_response_by_script_and_question(
        script_id=script.id,
        question_id=question.id,
        include_relationships=False,
    )

    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A response already exists for this script and question",
        )

    has_content = any(
        value is not None and str(value).strip()
        for value in (
            response_text,
            response_data,
            source_reference,
        )
    )

    response = AssessmentResponse(
        script_id=script.id,
        question_id=question.id,
        status=(
            AssessmentResponseStatus.IN_PROGRESS
            if has_content
            else AssessmentResponseStatus.NOT_STARTED
        ),
        response_text=response_text,
        response_data=response_data,
        source_reference=source_reference,
    )

    try:
        response = await repository.create_response(
            response,
        )

        await db.commit()

        return await _get_response_or_404(
            db,
            response.id,
            include_relationships=True,
        )

    except IntegrityError as exc:
        await db.rollback()

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A response already exists for this script and question",
        ) from exc

    except Exception:
        await db.rollback()
        raise


async def get_response(
    db: AsyncSession,
    current_user: User,
    response_id: int,
) -> AssessmentResponse:
    """
    Return one response visible to the current marker.
    """

    response = await _get_response_or_404(
        db,
        response_id,
        include_relationships=True,
    )

    await _ensure_response_marking_access(
        db,
        current_user,
        response,
    )

    return response


async def list_script_responses(
    db: AsyncSession,
    current_user: User,
    script_id: int,
    *,
    response_status: AssessmentResponseStatus | str | None = None,
) -> list[AssessmentResponse]:
    """
    Return responses for one assessment script.
    """

    script = await _get_script_or_404(
        db,
        script_id,
        include_relationships=True,
    )

    await _ensure_script_marking_access(
        db,
        current_user,
        script,
    )

    return await AssessmentMarkingRepository(
        db,
    ).list_responses_by_script(
        script.id,
        status=response_status,
        include_relationships=True,
    )


async def update_response(
    db: AsyncSession,
    current_user: User,
    response_id: int,
    *,
    response_text: str | None = None,
    response_data: str | None = None,
    source_reference: str | None = None,
) -> AssessmentResponse:
    """
    Update response content before marking becomes final.
    """

    response = await _get_response_or_404(
        db,
        response_id,
        include_relationships=True,
    )

    script = await _ensure_response_marking_access(
        db,
        current_user,
        response,
    )

    if response.status in {
        AssessmentResponseStatus.SUBMITTED,
        AssessmentResponseStatus.VOID,
    }:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Submitted or void responses cannot be edited",
        )

    if script.status == AssessmentScriptStatus.FINALISED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Responses cannot be changed on a finalised script",
        )

    response.response_text = response_text
    response.response_data = response_data
    response.source_reference = source_reference

    has_content = any(
        value is not None and str(value).strip()
        for value in (
            response_text,
            response_data,
            source_reference,
        )
    )

    response.status = (
        AssessmentResponseStatus.IN_PROGRESS
        if has_content
        else AssessmentResponseStatus.NOT_STARTED
    )

    repository = AssessmentMarkingRepository(
        db,
    )

    try:
        response = await repository.save_response(
            response,
        )

        await db.commit()

        return await _get_response_or_404(
            db,
            response.id,
            include_relationships=True,
        )

    except Exception:
        await db.rollback()
        raise


# ----------------------------------------------------------------------
# Response lifecycle
# ----------------------------------------------------------------------


_ALLOWED_RESPONSE_TRANSITIONS: dict[
    AssessmentResponseStatus,
    set[AssessmentResponseStatus],
] = {
    AssessmentResponseStatus.NOT_STARTED: {
        AssessmentResponseStatus.IN_PROGRESS,
        AssessmentResponseStatus.SUBMITTED,
        AssessmentResponseStatus.VOID,
    },
    AssessmentResponseStatus.IN_PROGRESS: {
        AssessmentResponseStatus.SUBMITTED,
        AssessmentResponseStatus.VOID,
    },
    AssessmentResponseStatus.SUBMITTED: {
        AssessmentResponseStatus.VOID,
    },
    AssessmentResponseStatus.VOID: set(),
}


async def transition_response_status(
    db: AsyncSession,
    current_user: User,
    response_id: int,
    new_status: AssessmentResponseStatus | str,
) -> AssessmentResponse:
    """
    Move a response through an allowed lifecycle transition.
    """

    response = await _get_response_or_404(
        db,
        response_id,
        include_relationships=True,
    )

    await _ensure_response_marking_access(
        db,
        current_user,
        response,
    )

    requested_status = _normalise_response_status(
        new_status,
    )

    if requested_status == response.status:
        return response

    allowed = _ALLOWED_RESPONSE_TRANSITIONS.get(
        response.status,
        set(),
    )

    if requested_status not in allowed:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Invalid assessment response status transition: "
                f"{response.status.value} -> {requested_status.value}"
            ),
        )

    response.status = requested_status

    if requested_status == AssessmentResponseStatus.SUBMITTED:
        response.submitted_at = response.submitted_at or _utc_now()

    repository = AssessmentMarkingRepository(
        db,
    )

    try:
        response = await repository.save_response(
            response,
        )

        await db.commit()

        return await _get_response_or_404(
            db,
            response.id,
            include_relationships=True,
        )

    except Exception:
        await db.rollback()
        raise


async def submit_response(
    db: AsyncSession,
    current_user: User,
    response_id: int,
) -> AssessmentResponse:
    """
    Submit a response for marking.
    """

    return await transition_response_status(
        db,
        current_user,
        response_id,
        AssessmentResponseStatus.SUBMITTED,
    )


async def void_response(
    db: AsyncSession,
    current_user: User,
    response_id: int,
) -> AssessmentResponse:
    """
    Void a response so it does not contribute to marking.
    """

    return await transition_response_status(
        db,
        current_user,
        response_id,
        AssessmentResponseStatus.VOID,
    )


async def delete_response(
    db: AsyncSession,
    current_user: User,
    response_id: int,
) -> None:
    """
    Delete only an untouched response.

    Once response content exists, submission occurs, or marking history
    exists, the response is retained.
    """

    response = await _get_response_or_404(
        db,
        response_id,
        include_relationships=True,
    )

    await _ensure_response_marking_access(
        db,
        current_user,
        response,
    )

    if response.status != AssessmentResponseStatus.NOT_STARTED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only untouched responses can be deleted",
        )

    if response.marking_decision is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Response cannot be deleted after marking has started",
        )

    repository = AssessmentMarkingRepository(
        db,
    )

    try:
        await repository.delete_response(
            response,
        )

        await db.commit()

    except Exception:
        await db.rollback()
        raise


# ----------------------------------------------------------------------
# Marking decisions
# ----------------------------------------------------------------------


async def create_marking_decision(
    db: AsyncSession,
    current_user: User,
    response_id: int,
    *,
    marker_comment: str | None = None,
) -> MarkingDecision:
    """
    Start marking one submitted response.
    """

    response = await _get_response_or_404(
        db,
        response_id,
        include_relationships=True,
    )

    await _ensure_response_marking_access(
        db,
        current_user,
        response,
    )

    if response.status != AssessmentResponseStatus.SUBMITTED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only submitted responses can be marked",
        )

    repository = AssessmentMarkingRepository(
        db,
    )

    existing = await repository.get_decision_by_response(
        response.id,
        include_relationships=False,
    )

    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A marking decision already exists for this response",
        )

    decision = MarkingDecision(
        response_id=response.id,
        marker_id=current_user.id,
        status=MarkingDecisionStatus.UNMARKED,
        mark_awarded=None,
        marker_comment=marker_comment,
        moderation_comment=None,
    )

    try:
        decision = await repository.create_decision(
            decision,
        )

        await db.commit()

        return await _get_decision_or_404(
            db,
            decision.id,
            include_relationships=True,
        )

    except IntegrityError as exc:
        await db.rollback()

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A marking decision already exists for this response",
        ) from exc

    except Exception:
        await db.rollback()
        raise


async def get_marking_decision(
    db: AsyncSession,
    current_user: User,
    decision_id: int,
) -> MarkingDecision:
    """
    Return one marking decision.
    """

    decision = await _get_decision_or_404(
        db,
        decision_id,
        include_relationships=True,
    )

    await _ensure_decision_marking_access(
        db,
        current_user,
        decision,
    )

    return decision


async def list_script_marking_decisions(
    db: AsyncSession,
    current_user: User,
    script_id: int,
    *,
    decision_status: MarkingDecisionStatus | str | None = None,
) -> list[MarkingDecision]:
    """
    Return marking decisions for one script.
    """

    script = await _get_script_or_404(
        db,
        script_id,
        include_relationships=True,
    )

    await _ensure_script_marking_access(
        db,
        current_user,
        script,
    )

    return await AssessmentMarkingRepository(
        db,
    ).list_decisions_by_script(
        script.id,
        status=decision_status,
        include_relationships=True,
    )


def _ensure_decision_editable(
    decision: MarkingDecision,
) -> None:
    """
    Ensure a marking decision may still be changed.
    """

    if decision.status == MarkingDecisionStatus.FINALISED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Finalised marking decisions cannot be changed",
        )


def _ensure_marker_or_admin(
    current_user: User,
    decision: MarkingDecision,
) -> None:
    """
    Restrict primary marking edits to the allocated marker or administrators.
    """

    if is_platform_admin(current_user) or is_school_admin(current_user):
        return

    if decision.marker_id == current_user.id:
        return

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="This marking decision is assigned to another marker",
    )


async def _get_authoritative_response_maximum_mark(
    db: AsyncSession,
    response: AssessmentResponse,
) -> Decimal:
    """
    Return the maximum mark that governed this candidate response.

    Snapshot-linked responses must use the immutable question snapshot.
    Historical responses created before snapshot support fall back to the
    canonical question.

    A response that claims a snapshot linkage but cannot resolve that snapshot
    is treated as an integrity failure rather than silently falling back to a
    mutable canonical question.
    """

    if response.question_snapshot_id is not None:
        snapshot = response.question_snapshot

        if snapshot is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "The immutable question snapshot for this response "
                    "could not be resolved"
                ),
            )

        return snapshot.maximum_mark

    question = await _get_question_or_404(
        db,
        response.question_id,
    )

    return question.maximum_mark


async def update_marking_decision(
    db: AsyncSession,
    current_user: User,
    decision_id: int,
    *,
    mark_awarded: Decimal | int | float | str | None = None,
    marker_comment: str | None = None,
) -> MarkingDecision:
    """
    Update the authoritative question-level mark and marker comment.
    """

    decision = await _get_decision_or_404(
        db,
        decision_id,
        include_relationships=True,
    )

    response = await _ensure_decision_marking_access(
        db,
        current_user,
        decision,
    )

    _ensure_decision_editable(
        decision,
    )
    _ensure_marker_or_admin(
        current_user,
        decision,
    )

    if mark_awarded is not None:
        normalised_mark = _normalise_decimal(
            mark_awarded,
            field_name="mark_awarded",
        )

        maximum_mark = await _get_authoritative_response_maximum_mark(
            db,
            response,
        )

        if normalised_mark > maximum_mark:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=(
                    "Awarded mark cannot exceed the question maximum "
                    f"of {maximum_mark}"
                ),
            )

        decision.mark_awarded = normalised_mark

    decision.marker_comment = marker_comment

    if decision.status == MarkingDecisionStatus.UNMARKED:
        decision.status = MarkingDecisionStatus.IN_PROGRESS

    repository = AssessmentMarkingRepository(
        db,
    )

    try:
        decision = await repository.save_decision(
            decision,
        )

        await db.commit()

        return await _get_decision_or_404(
            db,
            decision.id,
            include_relationships=True,
        )

    except Exception:
        await db.rollback()
        raise


# ----------------------------------------------------------------------
# Criterion-level awards
# ----------------------------------------------------------------------


async def award_mark_scheme_item(
    db: AsyncSession,
    current_user: User,
    decision_id: int,
    mark_scheme_item_id: int,
    *,
    marks_awarded: Decimal | int | float | str,
    marker_note: str | None = None,
) -> MarkSchemeItemAward:
    """
    Create or update one criterion-level mark award.

    The criterion must belong to the response question's mark scheme and the
    awarded value may not exceed the criterion maximum.
    """

    decision = await _get_decision_or_404(
        db,
        decision_id,
        include_relationships=True,
    )

    response = await _ensure_decision_marking_access(
        db,
        current_user,
        decision,
    )

    _ensure_decision_editable(
        decision,
    )
    _ensure_marker_or_admin(
        current_user,
        decision,
    )

    item = await _get_mark_scheme_item_or_404(
        db,
        mark_scheme_item_id,
    )

    if item.mark_scheme is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Mark-scheme item is not linked to a mark scheme",
        )

    if item.mark_scheme.question_id != response.question_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=("Mark-scheme item does not belong to the response question"),
        )

    normalised_marks = _normalise_decimal(
        marks_awarded,
        field_name="marks_awarded",
    )

    if normalised_marks > item.marks:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=(
                "Criterion award cannot exceed the mark-scheme item "
                f"maximum of {item.marks}"
            ),
        )

    repository = AssessmentMarkingRepository(
        db,
    )

    existing = await repository.get_award_by_decision_and_item(
        decision_id=decision.id,
        mark_scheme_item_id=item.id,
        include_relationships=False,
    )

    try:
        if existing is None:
            award = MarkSchemeItemAward(
                marking_decision_id=decision.id,
                mark_scheme_item_id=item.id,
                marks_awarded=normalised_marks,
                marker_note=marker_note,
                awarded_by_id=current_user.id,
            )

            award = await repository.create_award(
                award,
            )

        else:
            existing.marks_awarded = normalised_marks
            existing.marker_note = marker_note
            existing.awarded_by_id = current_user.id

            award = await repository.save_award(
                existing,
            )

        if decision.status == MarkingDecisionStatus.UNMARKED:
            decision.status = MarkingDecisionStatus.IN_PROGRESS

            await repository.save_decision(
                decision,
            )

        await db.commit()

        return await _get_award_or_404(
            db,
            award.id,
        )

    except IntegrityError as exc:
        await db.rollback()

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This mark-scheme item has already been recorded",
        ) from exc

    except Exception:
        await db.rollback()
        raise


async def delete_mark_scheme_item_award(
    db: AsyncSession,
    current_user: User,
    award_id: int,
) -> None:
    """
    Delete a criterion award while the decision remains editable.
    """

    award = await _get_award_or_404(
        db,
        award_id,
    )

    decision = await _get_decision_or_404(
        db,
        award.marking_decision_id,
        include_relationships=True,
    )

    await _ensure_decision_marking_access(
        db,
        current_user,
        decision,
    )

    _ensure_decision_editable(
        decision,
    )
    _ensure_marker_or_admin(
        current_user,
        decision,
    )

    repository = AssessmentMarkingRepository(
        db,
    )

    try:
        await repository.delete_award(
            award,
        )

        await db.commit()

    except Exception:
        await db.rollback()
        raise


# ----------------------------------------------------------------------
# Marking lifecycle
# ----------------------------------------------------------------------


_ALLOWED_DECISION_TRANSITIONS: dict[
    MarkingDecisionStatus,
    set[MarkingDecisionStatus],
] = {
    MarkingDecisionStatus.UNMARKED: {
        MarkingDecisionStatus.IN_PROGRESS,
    },
    MarkingDecisionStatus.IN_PROGRESS: {
        MarkingDecisionStatus.MARKED,
    },
    MarkingDecisionStatus.MARKED: {
        MarkingDecisionStatus.REVIEWED,
        MarkingDecisionStatus.FINALISED,
    },
    MarkingDecisionStatus.REVIEWED: {
        MarkingDecisionStatus.FINALISED,
    },
    MarkingDecisionStatus.FINALISED: set(),
}


async def transition_marking_decision_status(
    db: AsyncSession,
    current_user: User,
    decision_id: int,
    new_status: MarkingDecisionStatus | str,
    *,
    moderation_comment: str | None = None,
) -> MarkingDecision:
    """
    Move a marking decision through its controlled lifecycle.
    """

    decision = await _get_decision_or_404(
        db,
        decision_id,
        include_relationships=True,
    )

    response = await _ensure_decision_marking_access(
        db,
        current_user,
        decision,
    )

    requested_status = _normalise_decision_status(
        new_status,
    )

    if requested_status == decision.status:
        return decision

    allowed = _ALLOWED_DECISION_TRANSITIONS.get(
        decision.status,
        set(),
    )

    if requested_status not in allowed:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Invalid marking decision status transition: "
                f"{decision.status.value} -> {requested_status.value}"
            ),
        )

    if requested_status in {
        MarkingDecisionStatus.IN_PROGRESS,
        MarkingDecisionStatus.MARKED,
    }:
        _ensure_marker_or_admin(
            current_user,
            decision,
        )

    if requested_status == MarkingDecisionStatus.MARKED:
        if decision.mark_awarded is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A question-level mark is required before marking can complete",
            )

        maximum_mark = await _get_authoritative_response_maximum_mark(
            db,
            response,
        )

        if decision.mark_awarded > maximum_mark:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Awarded mark exceeds the question maximum",
            )

        decision.marked_at = decision.marked_at or _utc_now()

    elif requested_status == MarkingDecisionStatus.REVIEWED:
        if not (is_school_admin(current_user) or is_platform_admin(current_user)):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only administrators may review marking decisions",
            )

        decision.moderation_comment = moderation_comment
        decision.reviewed_at = decision.reviewed_at or _utc_now()

    elif requested_status == MarkingDecisionStatus.FINALISED:
        if not (is_school_admin(current_user) or is_platform_admin(current_user)):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only administrators may finalise marking decisions",
            )

        if decision.mark_awarded is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A question-level mark is required before finalisation",
            )

        decision.finalised_at = decision.finalised_at or _utc_now()

    decision.status = requested_status

    repository = AssessmentMarkingRepository(
        db,
    )

    try:
        decision = await repository.save_decision(
            decision,
        )

        await db.commit()

        return await _get_decision_or_404(
            db,
            decision.id,
            include_relationships=True,
        )

    except Exception:
        await db.rollback()
        raise


async def instant_mark_decision(
    db: AsyncSession,
    current_user: User,
    decision_id: int,
    *,
    mark_awarded: Decimal | int | float | str,
) -> MarkingDecision:
    """
    Award the authoritative question-level mark and complete primary marking
    in one atomic operation.

    This supports examiner-style one-click or keyboard marking without a
    separate save/complete request.
    """

    decision = await _get_decision_or_404(
        db,
        decision_id,
        include_relationships=True,
    )

    response = await _ensure_decision_marking_access(
        db,
        current_user,
        decision,
    )

    _ensure_decision_editable(
        decision,
    )
    _ensure_marker_or_admin(
        current_user,
        decision,
    )

    if decision.status == MarkingDecisionStatus.REVIEWED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Reviewed marking decisions cannot be instant-marked",
        )

    normalised_mark = _normalise_decimal(
        mark_awarded,
        field_name="mark_awarded",
    )

    maximum_mark = await _get_authoritative_response_maximum_mark(
        db,
        response,
    )

    if normalised_mark > maximum_mark:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=(
                "Awarded mark cannot exceed the question maximum "
                f"of {maximum_mark}"
            ),
        )

    decision.mark_awarded = normalised_mark
    decision.status = MarkingDecisionStatus.MARKED
    decision.marked_at = decision.marked_at or _utc_now()

    repository = AssessmentMarkingRepository(
        db,
    )

    try:
        decision = await repository.save_decision(
            decision,
        )

        await db.commit()

        return await _get_decision_or_404(
            db,
            decision.id,
            include_relationships=True,
        )

    except Exception:
        await db.rollback()
        raise


async def start_marking(
    db: AsyncSession,
    current_user: User,
    decision_id: int,
) -> MarkingDecision:
    """
    Move an unmarked decision into active marking.
    """

    return await transition_marking_decision_status(
        db,
        current_user,
        decision_id,
        MarkingDecisionStatus.IN_PROGRESS,
    )


async def complete_marking(
    db: AsyncSession,
    current_user: User,
    decision_id: int,
) -> MarkingDecision:
    """
    Complete primary marking.
    """

    return await transition_marking_decision_status(
        db,
        current_user,
        decision_id,
        MarkingDecisionStatus.MARKED,
    )


async def review_marking(
    db: AsyncSession,
    current_user: User,
    decision_id: int,
    *,
    moderation_comment: str | None = None,
) -> MarkingDecision:
    """
    Review or moderate a completed marking decision.
    """

    return await transition_marking_decision_status(
        db,
        current_user,
        decision_id,
        MarkingDecisionStatus.REVIEWED,
        moderation_comment=moderation_comment,
    )


async def finalise_marking(
    db: AsyncSession,
    current_user: User,
    decision_id: int,
) -> MarkingDecision:
    """
    Finalise a marked or reviewed decision.
    """

    return await transition_marking_decision_status(
        db,
        current_user,
        decision_id,
        MarkingDecisionStatus.FINALISED,
    )


# ----------------------------------------------------------------------
# Decision deletion
# ----------------------------------------------------------------------


async def delete_marking_decision(
    db: AsyncSession,
    current_user: User,
    decision_id: int,
) -> None:
    """
    Delete only an untouched marking decision.

    Once marking activity or criterion evidence exists, the decision is
    retained for audit history.
    """

    decision = await _get_decision_or_404(
        db,
        decision_id,
        include_relationships=True,
    )

    await _ensure_decision_marking_access(
        db,
        current_user,
        decision,
    )

    _ensure_marker_or_admin(
        current_user,
        decision,
    )

    if decision.status != MarkingDecisionStatus.UNMARKED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only untouched marking decisions can be deleted",
        )

    if decision.mark_awarded is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Marking decision cannot be deleted after a mark is awarded",
        )

    if decision.item_awards:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Marking decision cannot be deleted after criterion marking",
        )

    repository = AssessmentMarkingRepository(
        db,
    )

    try:
        await repository.delete_decision(
            decision,
        )

        await db.commit()

    except Exception:
        await db.rollback()
        raise
