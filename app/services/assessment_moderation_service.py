from __future__ import annotations

import logging
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.assessment import Assessment
from app.models.assessment_candidate import (
    AssessmentCandidate,
    AssessmentScript,
    AssessmentScriptStatus,
)
from app.models.assessment_moderation import (
    AssessmentModerationItem,
    AssessmentModerationItemOutcome,
    AssessmentModerationOutcome,
    AssessmentModerationReview,
    AssessmentModerationReviewStatus,
    AssessmentModerationSamplingMethod,
)
from app.models.assessment_question import AssessmentQuestion
from app.models.assessment_response import (
    AssessmentResponse,
    MarkingDecision,
    MarkingDecisionStatus,
)
from app.models.course import Course
from app.models.user import User, UserRole
from app.repositories.assessment import AssessmentRepository
from app.repositories.assessment_candidate import AssessmentCandidateRepository
from app.repositories.assessment_moderation import AssessmentModerationRepository
from app.repositories.course import CourseRepository
from app.services.assessment_notification_service import (
    AssessmentNotificationService,
)

logger = logging.getLogger(
    __name__,
)

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


def _ensure_moderation_admin_role(
    current_user: User,
) -> None:
    """
    Ensure the user may perform assessment moderation.

    The existing assessment-marking lifecycle already reserves REVIEWED and
    FINALISED transitions for School Admin and Platform Admin users.
    Dedicated moderation follows the same authority boundary.
    """

    if is_school_admin(current_user) or is_platform_admin(current_user):
        return

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Only administrators may moderate assessment marking",
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


def _clean_optional_text(
    value: str | None,
) -> str | None:
    """
    Trim optional text and convert blank strings to None.
    """

    if value is None:
        return None

    cleaned = value.strip()

    return cleaned or None


def _normalise_decimal(
    value: Decimal | int | float | str,
    *,
    field_name: str,
) -> Decimal:
    """
    Convert a supported numeric input to Decimal.
    """

    if isinstance(value, bool):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"{field_name} must be numeric",
        )

    try:
        normalised = Decimal(
            str(
                value,
            ),
        )
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"{field_name} must be numeric",
        ) from exc

    if not normalised.is_finite():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"{field_name} must be finite",
        )

    return normalised


def _normalise_sampling_method(
    value: AssessmentModerationSamplingMethod | str,
) -> AssessmentModerationSamplingMethod:
    """
    Convert input into AssessmentModerationSamplingMethod.
    """

    if isinstance(
        value,
        AssessmentModerationSamplingMethod,
    ):
        return value

    try:
        return AssessmentModerationSamplingMethod(
            value,
        )
    except (TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid moderation sampling method: {value!r}",
        ) from exc


def _normalise_item_outcome(
    value: AssessmentModerationItemOutcome | str,
) -> AssessmentModerationItemOutcome:
    """
    Convert input into AssessmentModerationItemOutcome.
    """

    if isinstance(
        value,
        AssessmentModerationItemOutcome,
    ):
        return value

    try:
        return AssessmentModerationItemOutcome(
            value,
        )
    except (TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid moderation item outcome: {value!r}",
        ) from exc


def _normalise_review_outcome(
    value: AssessmentModerationOutcome | str,
) -> AssessmentModerationOutcome:
    """
    Convert input into AssessmentModerationOutcome.
    """

    if isinstance(
        value,
        AssessmentModerationOutcome,
    ):
        return value

    try:
        return AssessmentModerationOutcome(
            value,
        )
    except (TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid moderation review outcome: {value!r}",
        ) from exc


# ----------------------------------------------------------------------
# Entity lookup helpers
# ----------------------------------------------------------------------


async def _get_user_or_404(
    db: AsyncSession,
    user_id: int,
) -> User:
    """
    Return a user or raise 404.
    """

    result = await db.execute(
        select(
            User,
        ).where(
            User.id == user_id,
        ),
    )

    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return user


async def _get_course_or_404(
    db: AsyncSession,
    course_id: int,
) -> Course:
    """
    Return a course or raise 404.
    """

    course = await CourseRepository(
        db,
    ).get_by_id(
        course_id,
        include_relationships=False,
    )

    if course is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found",
        )

    return course


async def _get_assessment_or_404(
    db: AsyncSession,
    assessment_id: int,
) -> Assessment:
    """
    Return an assessment or raise 404.
    """

    assessment = await AssessmentRepository(
        db,
    ).get_by_id(
        assessment_id,
        include_relationships=False,
    )

    if assessment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assessment not found",
        )

    return assessment


async def _get_candidate_or_404(
    db: AsyncSession,
    candidate_id: int,
) -> AssessmentCandidate:
    """
    Return an assessment candidate or raise 404.
    """

    candidate = await AssessmentCandidateRepository(
        db,
    ).get_candidate_by_id(
        candidate_id,
        include_relationships=False,
    )

    if candidate is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assessment candidate not found",
        )

    return candidate


async def _get_script_or_404(
    db: AsyncSession,
    script_id: int,
) -> AssessmentScript:
    """
    Return an assessment script or raise 404.
    """

    script = await AssessmentCandidateRepository(
        db,
    ).get_script_by_id(
        script_id,
        include_relationships=False,
    )

    if script is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assessment script not found",
        )

    return script


async def _get_response_or_404(
    db: AsyncSession,
    response_id: int,
) -> AssessmentResponse:
    """
    Return an assessment response or raise 404.
    """

    result = await db.execute(
        select(
            AssessmentResponse,
        ).where(
            AssessmentResponse.id == response_id,
        ),
    )

    response = result.scalar_one_or_none()

    if response is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assessment response not found",
        )

    return response


async def _get_decision_or_404(
    db: AsyncSession,
    decision_id: int,
) -> MarkingDecision:
    """
    Return a marking decision or raise 404.
    """

    result = await db.execute(
        select(
            MarkingDecision,
        ).where(
            MarkingDecision.id == decision_id,
        ),
    )

    decision = result.scalar_one_or_none()

    if decision is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Marking decision not found",
        )

    return decision


async def _get_question_or_404(
    db: AsyncSession,
    question_id: int,
) -> AssessmentQuestion:
    """
    Return an assessment question or raise 404.
    """

    result = await db.execute(
        select(
            AssessmentQuestion,
        ).where(
            AssessmentQuestion.id == question_id,
        ),
    )

    question = result.scalar_one_or_none()

    if question is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assessment question not found",
        )

    return question


async def _get_review_or_404(
    db: AsyncSession,
    review_id: int,
    *,
    include_items: bool = False,
) -> AssessmentModerationReview:
    """
    Return a moderation review or raise 404.
    """

    review = await AssessmentModerationRepository(
        db,
    ).get_review_by_id(
        review_id,
        include_relationships=False,
        include_items=include_items,
    )

    if review is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assessment moderation review not found",
        )

    return review


# ----------------------------------------------------------------------
# Scope and consistency validation
# ----------------------------------------------------------------------


async def _ensure_assessment_moderation_access(
    db: AsyncSession,
    current_user: User,
    assessment: Assessment,
) -> Course:
    """
    Ensure an administrator may moderate the assessment.
    """

    _ensure_moderation_admin_role(
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

    course = await _get_course_or_404(
        db,
        assessment.course_id,
    )

    if course.school_id != assessment.school_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Assessment and course school scope are inconsistent",
        )

    return course


async def _ensure_script_moderation_access(
    db: AsyncSession,
    current_user: User,
    script: AssessmentScript,
) -> tuple[AssessmentCandidate, Assessment]:
    """
    Validate script, candidate, assessment and school scope.
    """

    candidate = await _get_candidate_or_404(
        db,
        script.candidate_id,
    )

    assessment = await _get_assessment_or_404(
        db,
        candidate.assessment_id,
    )

    await _ensure_assessment_moderation_access(
        db,
        current_user,
        assessment,
    )

    return candidate, assessment


async def _ensure_review_access(
    db: AsyncSession,
    current_user: User,
    review: AssessmentModerationReview,
) -> AssessmentScript:
    """
    Ensure the current user may access a moderation review.
    """

    _ensure_moderation_admin_role(
        current_user,
    )

    if (
        not is_platform_admin(current_user)
        and review.school_id != current_user.school_id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Moderation review does not belong to your school",
        )

    script = await _get_script_or_404(
        db,
        review.script_id,
    )

    candidate, assessment = await _ensure_script_moderation_access(
        db,
        current_user,
        script,
    )

    if review.candidate_id != candidate.id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Moderation review candidate does not match the script",
        )

    if review.assessment_id != assessment.id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Moderation review assessment does not match the script",
        )

    if review.school_id != assessment.school_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Moderation review school scope is inconsistent",
        )

    return script


async def _ensure_moderator_assignment_valid(
    db: AsyncSession,
    moderator_id: int,
    *,
    school_id: int,
) -> User:
    """
    Validate the user selected as moderator.
    """

    moderator = await _get_user_or_404(
        db,
        moderator_id,
    )

    if not (is_school_admin(moderator) or is_platform_admin(moderator)):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="The assigned moderator must be an administrator",
        )

    if not is_platform_admin(moderator) and moderator.school_id != school_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="The assigned moderator does not belong to the assessment school",
        )

    return moderator


def _ensure_assigned_moderator_or_platform_admin(
    current_user: User,
    review: AssessmentModerationReview,
) -> None:
    """
    Restrict active moderation work to the assigned moderator.

    Platform administrators retain intervention capability.
    """

    if is_platform_admin(current_user):
        return

    if review.moderator_id == current_user.id:
        return

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="This moderation review is assigned to another moderator",
    )


# ----------------------------------------------------------------------
# Moderation notification helper
# ----------------------------------------------------------------------


async def _notify_moderation_required_best_effort(
    db: AsyncSession,
    *,
    assessment: Assessment,
    review: AssessmentModerationReview,
) -> None:
    """
    Notify the assigned moderator after the review transaction has committed.

    Notification delivery is deliberately best-effort. A failure in the
    notification subsystem must not make a successfully committed moderation
    review appear to have failed, because retrying the review creation could
    otherwise create a conflict or duplicate operational work.
    """

    try:
        await AssessmentNotificationService(
            db,
        ).notify_moderation_required(
            assessment_id=assessment.id,
            assessment_title=assessment.title,
            school_id=assessment.school_id,
            moderator_user_id=review.moderator_id,
        )

    except Exception:
        logger.exception(
            (
                "Unable to create moderation-required notification "
                "after moderation review %s was committed."
            ),
            review.id,
        )

        try:
            await db.rollback()
        except Exception:
            logger.exception(
                (
                    "Unable to roll back failed notification transaction "
                    "for moderation review %s."
                ),
                review.id,
            )


# ----------------------------------------------------------------------
# Review creation
# ----------------------------------------------------------------------


async def create_moderation_review(
    db: AsyncSession,
    current_user: User,
    script_id: int,
    *,
    moderator_id: int,
    sampling_method: AssessmentModerationSamplingMethod | str = (
        AssessmentModerationSamplingMethod.MANUAL
    ),
    reason: str | None = None,
    notes: str | None = None,
    sample_description: str | None = None,
) -> AssessmentModerationReview:
    """
    Create a moderation review for a marked or finalised script.

    A MARKED script enters MODERATION when its first active review is created.

    A FINALISED script remains FINALISED. This permits controlled later
    moderation/correction without pretending that the previously finalised
    result never existed. Any new official result still requires a separate
    AssessmentResultOutcome operation.
    """

    script = await _get_script_or_404(
        db,
        script_id,
    )

    candidate, assessment = await _ensure_script_moderation_access(
        db,
        current_user,
        script,
    )

    if script.status not in {
        AssessmentScriptStatus.MARKED,
        AssessmentScriptStatus.MODERATION,
        AssessmentScriptStatus.FINALISED,
    }:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Only marked, moderated, or finalised scripts "
                "can enter moderation review"
            ),
        )

    await _ensure_moderator_assignment_valid(
        db,
        moderator_id,
        school_id=assessment.school_id,
    )

    requested_sampling_method = _normalise_sampling_method(
        sampling_method,
    )

    repository = AssessmentModerationRepository(
        db,
    )

    try:
        review = await repository.create_review(
            school_id=assessment.school_id,
            assessment_id=assessment.id,
            candidate_id=candidate.id,
            script_id=script.id,
            moderator_id=moderator_id,
            initiated_by_id=current_user.id,
            sampling_method=requested_sampling_method,
            reason=_clean_optional_text(reason),
            notes=_clean_optional_text(notes),
            sample_description=_clean_optional_text(
                sample_description,
            ),
        )

        if script.status == AssessmentScriptStatus.MARKED:
            script.status = AssessmentScriptStatus.MODERATION

        await db.flush()
        await db.commit()

        refreshed = await _get_review_or_404(
            db,
            review.id,
            include_items=True,
        )

        await _notify_moderation_required_best_effort(
            db,
            assessment=assessment,
            review=refreshed,
        )

        return refreshed

    except IntegrityError as exc:
        await db.rollback()

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "A conflicting moderation review was created concurrently; "
                "retry the operation"
            ),
        ) from exc

    except Exception:
        await db.rollback()
        raise


# ----------------------------------------------------------------------
# Review retrieval
# ----------------------------------------------------------------------


async def get_moderation_review(
    db: AsyncSession,
    current_user: User,
    review_id: int,
) -> AssessmentModerationReview:
    """
    Return a moderation review visible to the current administrator.
    """

    review = await _get_review_or_404(
        db,
        review_id,
        include_items=True,
    )

    await _ensure_review_access(
        db,
        current_user,
        review,
    )

    return review


async def list_script_moderation_reviews(
    db: AsyncSession,
    current_user: User,
    script_id: int,
) -> list[AssessmentModerationReview]:
    """
    Return complete moderation history for one script.
    """

    script = await _get_script_or_404(
        db,
        script_id,
    )

    await _ensure_script_moderation_access(
        db,
        current_user,
        script,
    )

    return await AssessmentModerationRepository(
        db,
    ).list_reviews_for_script(
        script.id,
        include_relationships=False,
        include_items=True,
    )


async def list_assessment_moderation_reviews(
    db: AsyncSession,
    current_user: User,
    assessment_id: int,
    *,
    review_status: AssessmentModerationReviewStatus | None = None,
    outcome: AssessmentModerationOutcome | None = None,
) -> list[AssessmentModerationReview]:
    """
    Return moderation reviews for one assessment.
    """

    assessment = await _get_assessment_or_404(
        db,
        assessment_id,
    )

    await _ensure_assessment_moderation_access(
        db,
        current_user,
        assessment,
    )

    school_id = None if is_platform_admin(current_user) else assessment.school_id

    return await AssessmentModerationRepository(
        db,
    ).list_reviews_for_assessment(
        assessment.id,
        school_id=school_id,
        status=review_status,
        outcome=outcome,
        include_relationships=False,
        include_items=False,
    )


# ----------------------------------------------------------------------
# Review lifecycle
# ----------------------------------------------------------------------


async def start_moderation_review(
    db: AsyncSession,
    current_user: User,
    review_id: int,
) -> AssessmentModerationReview:
    """
    Start a pending moderation review.
    """

    review = await _get_review_or_404(
        db,
        review_id,
    )

    await _ensure_review_access(
        db,
        current_user,
        review,
    )

    _ensure_assigned_moderator_or_platform_admin(
        current_user,
        review,
    )

    if review.status == AssessmentModerationReviewStatus.IN_PROGRESS:
        return review

    if review.status != AssessmentModerationReviewStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=("Only pending moderation reviews can be started"),
        )

    review.status = AssessmentModerationReviewStatus.IN_PROGRESS
    review.started_at = review.started_at or _utc_now()

    repository = AssessmentModerationRepository(
        db,
    )

    try:
        review = await repository.save_review(
            review,
        )

        await db.commit()

        return await _get_review_or_404(
            db,
            review.id,
            include_items=True,
        )

    except Exception:
        await db.rollback()
        raise


# ----------------------------------------------------------------------
# Moderation item recording
# ----------------------------------------------------------------------


async def add_moderation_item(
    db: AsyncSession,
    current_user: User,
    review_id: int,
    *,
    response_id: int,
    marking_decision_id: int,
    outcome: AssessmentModerationItemOutcome | str,
    mark_after: Decimal | int | float | str | None = None,
    moderator_comment: str | None = None,
    evidence_notes: str | None = None,
) -> AssessmentModerationItem:
    """
    Record moderation of one assessment response.

    The moderation item is immutable audit evidence.

    For CONFIRMED and ADJUSTED outcomes, a MARKED decision becomes REVIEWED.
    A previously FINALISED decision remains FINALISED; formal moderation is
    the controlled exception that may change its current operational mark.

    This does not alter an authoritative AssessmentResultOutcome.
    """

    review = await _get_review_or_404(
        db,
        review_id,
    )

    await _ensure_review_access(
        db,
        current_user,
        review,
    )

    _ensure_assigned_moderator_or_platform_admin(
        current_user,
        review,
    )

    if review.status != AssessmentModerationReviewStatus.IN_PROGRESS:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Moderation items can only be added to an active review",
        )

    requested_outcome = _normalise_item_outcome(
        outcome,
    )

    response = await _get_response_or_404(
        db,
        response_id,
    )

    if response.script_id != review.script_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Assessment response does not belong to the moderated script",
        )

    decision = await _get_decision_or_404(
        db,
        marking_decision_id,
    )

    if decision.response_id != response.id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Marking decision does not belong to the supplied response",
        )

    if decision.status not in {
        MarkingDecisionStatus.MARKED,
        MarkingDecisionStatus.REVIEWED,
        MarkingDecisionStatus.FINALISED,
    }:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only completed marking decisions can be moderated",
        )

    if decision.mark_awarded is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A marking decision must have a mark before moderation",
        )

    question = await _get_question_or_404(
        db,
        response.question_id,
    )

    if question.assessment_id != review.assessment_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Assessment response question does not belong to the moderated assessment",
        )

    mark_before = Decimal(
        decision.mark_awarded,
    )

    if mark_after is None:
        normalised_mark_after = mark_before
    else:
        normalised_mark_after = _normalise_decimal(
            mark_after,
            field_name="mark_after",
        )

    if normalised_mark_after < Decimal("0"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Moderated mark cannot be negative",
        )

    if normalised_mark_after > question.maximum_mark:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Moderated mark cannot exceed the question maximum",
        )

    mark_changed = normalised_mark_after != mark_before

    if (
        requested_outcome == AssessmentModerationItemOutcome.ADJUSTED
        and not mark_changed
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="An adjusted moderation outcome requires a changed mark",
        )

    if requested_outcome == AssessmentModerationItemOutcome.CONFIRMED and mark_changed:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="A confirmed moderation outcome cannot change the mark",
        )

    status_before = decision.status

    if requested_outcome == AssessmentModerationItemOutcome.ADJUSTED:
        decision.mark_awarded = normalised_mark_after

    if requested_outcome in {
        AssessmentModerationItemOutcome.CONFIRMED,
        AssessmentModerationItemOutcome.ADJUSTED,
    }:
        if decision.status == MarkingDecisionStatus.MARKED:
            decision.status = MarkingDecisionStatus.REVIEWED
            decision.reviewed_at = decision.reviewed_at or _utc_now()

        if moderator_comment is not None:
            decision.moderation_comment = _clean_optional_text(
                moderator_comment,
            )

    status_after = decision.status

    repository = AssessmentModerationRepository(
        db,
    )

    try:
        item = await repository.create_item(
            review_id=review.id,
            response_id=response.id,
            marking_decision_id=decision.id,
            outcome=requested_outcome,
            reviewed_by_id=current_user.id,
            mark_before_snapshot=mark_before,
            mark_after_snapshot=normalised_mark_after,
            maximum_mark_snapshot=question.maximum_mark,
            mark_changed=mark_changed,
            decision_status_before_snapshot=status_before.value,
            decision_status_after_snapshot=status_after.value,
            moderator_comment=_clean_optional_text(
                moderator_comment,
            ),
            evidence_notes=_clean_optional_text(
                evidence_notes,
            ),
        )

        db.add(
            decision,
        )

        await db.flush()
        await db.commit()

        return item

    except ValueError as exc:
        await db.rollback()

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    except IntegrityError as exc:
        await db.rollback()

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This response has already been recorded in the moderation review",
        ) from exc

    except Exception:
        await db.rollback()
        raise


# ----------------------------------------------------------------------
# Review completion
# ----------------------------------------------------------------------


def _validate_review_outcome_against_items(
    *,
    review_outcome: AssessmentModerationOutcome,
    items: list[AssessmentModerationItem],
) -> None:
    """
    Prevent an overall review outcome contradicting its item evidence.
    """

    item_outcomes = {item.outcome for item in items}

    if (
        AssessmentModerationItemOutcome.ESCALATED in item_outcomes
        and review_outcome != AssessmentModerationOutcome.ESCALATED
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A review containing escalated items must be escalated",
        )

    if (
        AssessmentModerationItemOutcome.RETURNED in item_outcomes
        and review_outcome
        not in {
            AssessmentModerationOutcome.RETURNED,
            AssessmentModerationOutcome.ESCALATED,
        }
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A review containing returned items cannot be confirmed or adjusted",
        )

    if (
        AssessmentModerationItemOutcome.ADJUSTED in item_outcomes
        and review_outcome
        not in {
            AssessmentModerationOutcome.ADJUSTED,
            AssessmentModerationOutcome.ESCALATED,
        }
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A review containing adjusted marks must record an adjusted outcome",
        )


async def _ensure_script_marking_complete_for_finalisation(
    db: AsyncSession,
    script_id: int,
) -> None:
    """
    Ensure every response has completed marking before finalising a script.

    Sampling does not require every decision to become REVIEWED. It does
    require every response to have a mark and to have completed primary
    marking.
    """

    response_result = await db.execute(
        select(
            AssessmentResponse.id,
        ).where(
            AssessmentResponse.script_id == script_id,
        ),
    )

    response_ids = list(
        response_result.scalars().all(),
    )

    if not response_ids:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A script cannot be finalised without assessment responses",
        )

    decision_result = await db.execute(
        select(
            MarkingDecision,
        ).where(
            MarkingDecision.response_id.in_(
                response_ids,
            ),
        ),
    )

    decisions = list(
        decision_result.scalars().all(),
    )

    decisions_by_response = {decision.response_id: decision for decision in decisions}

    for response_id in response_ids:
        decision = decisions_by_response.get(
            response_id,
        )

        if decision is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Every response must have a marking decision before script finalisation",
            )

        if decision.mark_awarded is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Every marking decision must have a mark before script finalisation",
            )

        if decision.status not in {
            MarkingDecisionStatus.MARKED,
            MarkingDecisionStatus.REVIEWED,
            MarkingDecisionStatus.FINALISED,
        }:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Primary marking must be complete before script finalisation",
            )


async def complete_moderation_review(
    db: AsyncSession,
    current_user: User,
    review_id: int,
    *,
    outcome: AssessmentModerationOutcome | str,
    notes: str | None = None,
) -> AssessmentModerationReview:
    """
    Complete an active moderation review.

    CONFIRMED, ADJUSTED and NO_ACTION complete the operational moderation
    path. A script currently in MODERATION may then become FINALISED.

    RETURNED or ESCALATED reviews leave the script in MODERATION for further
    action.

    No authoritative AssessmentResultOutcome is created or superseded here.
    """

    review = await _get_review_or_404(
        db,
        review_id,
        include_items=True,
    )

    script = await _ensure_review_access(
        db,
        current_user,
        review,
    )

    _ensure_assigned_moderator_or_platform_admin(
        current_user,
        review,
    )

    if review.status == AssessmentModerationReviewStatus.COMPLETED:
        return review

    if review.status != AssessmentModerationReviewStatus.IN_PROGRESS:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only active moderation reviews can be completed",
        )

    if not review.items:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A moderation review must contain at least one reviewed item",
        )

    requested_outcome = _normalise_review_outcome(
        outcome,
    )

    _validate_review_outcome_against_items(
        review_outcome=requested_outcome,
        items=list(
            review.items,
        ),
    )

    if requested_outcome in {
        AssessmentModerationOutcome.CONFIRMED,
        AssessmentModerationOutcome.ADJUSTED,
        AssessmentModerationOutcome.NO_ACTION,
    }:
        if script.status == AssessmentScriptStatus.MODERATION:
            await _ensure_script_marking_complete_for_finalisation(
                db,
                script.id,
            )

            script.status = AssessmentScriptStatus.FINALISED

    review.status = AssessmentModerationReviewStatus.COMPLETED
    review.outcome = requested_outcome
    review.completed_at = _utc_now()

    cleaned_notes = _clean_optional_text(
        notes,
    )

    if cleaned_notes is not None:
        review.notes = cleaned_notes

    repository = AssessmentModerationRepository(
        db,
    )

    try:
        review = await repository.save_review(
            review,
        )

        await db.flush()
        await db.commit()

        return await _get_review_or_404(
            db,
            review.id,
            include_items=True,
        )

    except Exception:
        await db.rollback()
        raise


# ----------------------------------------------------------------------
# Review cancellation
# ----------------------------------------------------------------------


async def cancel_moderation_review(
    db: AsyncSession,
    current_user: User,
    review_id: int,
    *,
    cancellation_reason: str,
) -> AssessmentModerationReview:
    """
    Cancel a pending or active moderation review.

    Cancellation preserves the review and all recorded evidence.
    """

    review = await _get_review_or_404(
        db,
        review_id,
        include_items=True,
    )

    script = await _ensure_review_access(
        db,
        current_user,
        review,
    )

    if review.status == AssessmentModerationReviewStatus.CANCELLED:
        return review

    if review.status == AssessmentModerationReviewStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Completed moderation reviews cannot be cancelled",
        )

    cleaned_reason = _clean_optional_text(
        cancellation_reason,
    )

    if cleaned_reason is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="A cancellation reason is required",
        )

    review.status = AssessmentModerationReviewStatus.CANCELLED
    review.cancelled_at = _utc_now()
    review.cancelled_by_id = current_user.id
    review.cancellation_reason = cleaned_reason

    repository = AssessmentModerationRepository(
        db,
    )

    try:
        review = await repository.save_review(
            review,
        )

        # A MARKED script enters MODERATION when a review is created.
        # If the only active moderation path is then cancelled, return the
        # operational script to MARKED rather than leaving it stranded.
        if script.status == AssessmentScriptStatus.MODERATION:
            reviews = await repository.list_reviews_for_script(
                script.id,
                include_relationships=False,
                include_items=False,
            )

            other_active_reviews = [
                existing
                for existing in reviews
                if (
                    existing.id != review.id
                    and existing.status
                    in {
                        AssessmentModerationReviewStatus.PENDING,
                        AssessmentModerationReviewStatus.IN_PROGRESS,
                    }
                )
            ]

            completed_reviews = [
                existing
                for existing in reviews
                if (
                    existing.id != review.id
                    and existing.status == AssessmentModerationReviewStatus.COMPLETED
                )
            ]

            if not other_active_reviews and not completed_reviews:
                script.status = AssessmentScriptStatus.MARKED

        await db.flush()
        await db.commit()

        return await _get_review_or_404(
            db,
            review.id,
            include_items=True,
        )

    except Exception:
        await db.rollback()
        raise
