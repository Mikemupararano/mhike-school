from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.assessment_result_publication import (
    AssessmentResultPublication,
    AssessmentResultPublicationStatus,
)
from app.models.user import User, UserRole
from app.repositories.assessment_result_outcome import (
    AssessmentResultOutcomeRepository,
)
from app.repositories.assessment_result_publication import (
    AssessmentResultPublicationRepository,
)
from app.services.assessment_notification_service import (
    AssessmentNotificationService,
)
from app.services.assessment_results_service import (
    get_assessment_results_summary,
)

logger = logging.getLogger(
    __name__,
)

_UNSET = object()


# ---------------------------------------------------------------------------
# Time helpers
# ---------------------------------------------------------------------------


def _utc_now() -> datetime:
    """
    Return the current timezone-aware UTC datetime.
    """

    return datetime.now(
        timezone.utc,
    )


def _normalise_datetime(
    value: datetime,
    *,
    field_name: str,
) -> datetime:
    """
    Return a timezone-aware datetime.

    Naive datetimes are rejected because scheduled release and publication
    audit must not depend on server-local timezone assumptions.
    """

    if not isinstance(
        value,
        datetime,
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"{field_name} must be a datetime.",
        )

    if value.tzinfo is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"{field_name} must include timezone information.",
        )

    return value.astimezone(
        timezone.utc,
    )


# ---------------------------------------------------------------------------
# Text helpers
# ---------------------------------------------------------------------------


def _normalise_optional_text(
    value: str | None,
    *,
    max_length: int | None = None,
    field_name: str,
) -> str | None:
    """
    Trim optional text and enforce an optional maximum length.
    """

    if value is None:
        return None

    if not isinstance(
        value,
        str,
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"{field_name} must be a string or null.",
        )

    cleaned = value.strip()

    if not cleaned:
        return None

    if max_length is not None and len(cleaned) > max_length:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=(f"{field_name} cannot exceed " f"{max_length} characters."),
        )

    return cleaned


# ---------------------------------------------------------------------------
# Boolean helpers
# ---------------------------------------------------------------------------


def _validate_bool(
    value: object,
    *,
    field_name: str,
) -> bool:
    """
    Return a boolean value or raise HTTP 422.
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
# Persistence helpers
# ---------------------------------------------------------------------------


async def _commit_publication_change(
    db: AsyncSession,
    *,
    conflict_detail: str,
) -> None:
    """
    Commit one publication mutation and translate integrity failures.
    """

    try:
        await db.commit()

    except IntegrityError as exc:
        await db.rollback()

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=conflict_detail,
        ) from exc


# ---------------------------------------------------------------------------
# Assessment scope and permissions
# ---------------------------------------------------------------------------


async def _get_assessment_context(
    db: AsyncSession,
    current_user: User,
    assessment_id: int,
) -> dict[str, Any]:
    """
    Resolve assessment context using the existing results-access policy.

    This deliberately reuses assessment-results access control so:

        - the course teacher can manage their own assessment;
        - School Admin retains school-wide access;
        - Platform Admin retains platform-wide access;
        - unrelated teachers remain blocked;
        - school isolation remains consistent.

    This is the core rule that allows a teacher to publish an ordinary
    end-of-topic test without waiting for SMT.
    """

    return await get_assessment_results_summary(
        db=db,
        current_user=current_user,
        assessment_id=assessment_id,
    )


def _can_approve_controlled_results(
    current_user: User,
) -> bool:
    """
    Return whether the user may approve a controlled result release.

    Approval is intentionally narrower than ordinary publication.

    Ordinary result publication can be performed by the course teacher.

    Controlled-result approval is reserved for:
        - Platform Admin
        - School Admin
        - SMT
    """

    return current_user.has_any_role(
        {
            UserRole.PLATFORM_ADMIN,
            UserRole.SCHOOL_ADMIN,
            "smt",
        }
    )


# ---------------------------------------------------------------------------
# Publication lookups
# ---------------------------------------------------------------------------


async def _get_publication_or_404(
    db: AsyncSession,
    publication_id: int,
) -> AssessmentResultPublication:
    """
    Return one publication record or raise HTTP 404.
    """

    publication = await AssessmentResultPublicationRepository(
        db,
    ).get_by_id(
        publication_id,
    )

    if publication is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assessment result publication not found.",
        )

    return publication


async def _get_assessment_publication_or_404(
    db: AsyncSession,
    assessment_id: int,
) -> AssessmentResultPublication:
    """
    Return publication configuration for one assessment.
    """

    publication = await AssessmentResultPublicationRepository(
        db,
    ).get_for_assessment(
        assessment_id,
    )

    if publication is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=("Assessment result publication configuration " "not found."),
        )

    return publication


# ---------------------------------------------------------------------------
# Release readiness
# ---------------------------------------------------------------------------


def _ensure_results_ready_for_release(
    assessment_context: dict[str, Any],
) -> None:
    """
    Ensure an assessment has complete finalised marking before release.

    A result release is assessment-wide. Therefore every expected
    question-level decision represented by submitted scripts must be
    finalised before publication.

    Candidates with no script, such as absent or withdrawn candidates,
    do not create expected marking decisions and therefore do not
    prevent release.
    """

    script_count = int(
        assessment_context.get(
            "script_count",
            0,
        )
    )

    if script_count <= 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Assessment results cannot be published because "
                "there are no assessment scripts."
            ),
        )

    expected = int(
        assessment_context.get(
            "expected_question_decisions",
            0,
        )
    )

    finalised = int(
        assessment_context.get(
            "finalised_decision_count",
            0,
        )
    )

    if expected <= 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Assessment results cannot be published because "
                "there are no markable result decisions."
            ),
        )

    if finalised < expected:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Assessment results cannot be published until "
                "all expected marking decisions are finalised."
            ),
        )


def _ensure_approval_if_required(
    publication: AssessmentResultPublication,
) -> None:
    """
    Ensure a controlled publication has been approved.

    Ordinary classroom assessments default to
    ``requires_approval=False`` and therefore bypass this check.
    """

    if publication.requires_approval and publication.approved_at is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "This assessment requires approval before " "results can be published."
            ),
        )


# ---------------------------------------------------------------------------
# Publication notification helpers
# ---------------------------------------------------------------------------


async def _get_authoritative_student_ids_for_assessment(
    db: AsyncSession,
    *,
    assessment_id: int,
    school_id: int,
) -> list[int]:
    """
    Return the students whose current authoritative result belongs to the
    assessment being released.

    Publication notifications deliberately follow immutable authoritative
    outcomes rather than mutable live marking state. Candidates without a
    current authoritative outcome are therefore not notified as having an
    official result available.
    """

    outcomes = await AssessmentResultOutcomeRepository(
        db,
    ).list_for_assessment(
        assessment_id,
        school_id=school_id,
        authoritative_only=True,
        include_relationships=True,
    )

    return sorted(
        {
            int(
                outcome.candidate.student_id,
            )
            for outcome in outcomes
        }
    )


async def _notify_results_published_best_effort(
    db: AsyncSession,
    *,
    publication: AssessmentResultPublication,
) -> None:
    """
    Notify configured audiences after a publication transaction has committed.

    Notifications are a post-commit side effect. A notification failure must
    not make a successfully published result release appear to have failed,
    because a client retry could otherwise duplicate or conflict with the
    already-committed publication transition.
    """

    if not (publication.visible_to_students or publication.visible_to_parents):
        return

    assessment = publication.assessment

    if assessment is None:
        logger.error(
            (
                "Unable to create assessment publication notifications "
                "because publication %s has no loaded assessment."
            ),
            publication.id,
        )
        return

    try:
        student_ids = await _get_authoritative_student_ids_for_assessment(
            db,
            assessment_id=publication.assessment_id,
            school_id=assessment.school_id,
        )

        if not student_ids:
            return

        await AssessmentNotificationService(
            db,
        ).notify_results_published(
            assessment_id=publication.assessment_id,
            assessment_title=assessment.title,
            school_id=assessment.school_id,
            student_ids=student_ids,
            notify_students=publication.visible_to_students,
            notify_parents=publication.visible_to_parents,
        )

    except Exception:
        logger.exception(
            (
                "Unable to create assessment publication notifications "
                "after publication %s was committed."
            ),
            publication.id,
        )

        try:
            await db.rollback()
        except Exception:
            logger.exception(
                (
                    "Unable to roll back failed notification transaction "
                    "for assessment publication %s."
                ),
                publication.id,
            )


# ---------------------------------------------------------------------------
# Configuration service
# ---------------------------------------------------------------------------


async def create_result_publication(
    db: AsyncSession,
    current_user: User,
    *,
    assessment_id: int,
    requires_approval: bool = False,
    visible_to_students: bool = True,
    visible_to_parents: bool = True,
    include_mark: bool = True,
    include_percentage: bool = True,
    include_grade: bool = True,
    include_question_breakdown: bool = False,
    release_message: str | None = None,
) -> AssessmentResultPublication:
    """
    Create result-publication configuration for an assessment.

    The course teacher may create ordinary publication configuration.

    ``requires_approval`` defaults to False so routine classroom tests do
    not require SMT intervention.
    """

    await _get_assessment_context(
        db,
        current_user,
        assessment_id,
    )

    repository = AssessmentResultPublicationRepository(
        db,
    )

    existing = await repository.get_for_assessment(
        assessment_id,
    )

    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=("This assessment already has result-publication " "configuration."),
        )

    clean_requires_approval = _validate_bool(
        requires_approval,
        field_name="requires_approval",
    )

    clean_visible_to_students = _validate_bool(
        visible_to_students,
        field_name="visible_to_students",
    )

    clean_visible_to_parents = _validate_bool(
        visible_to_parents,
        field_name="visible_to_parents",
    )

    clean_include_mark = _validate_bool(
        include_mark,
        field_name="include_mark",
    )

    clean_include_percentage = _validate_bool(
        include_percentage,
        field_name="include_percentage",
    )

    clean_include_grade = _validate_bool(
        include_grade,
        field_name="include_grade",
    )

    clean_include_question_breakdown = _validate_bool(
        include_question_breakdown,
        field_name="include_question_breakdown",
    )

    clean_release_message = _normalise_optional_text(
        release_message,
        max_length=1000,
        field_name="release_message",
    )

    publication = await repository.create(
        assessment_id=assessment_id,
        created_by_id=current_user.id,
        requires_approval=clean_requires_approval,
        visible_to_students=clean_visible_to_students,
        visible_to_parents=clean_visible_to_parents,
        include_mark=clean_include_mark,
        include_percentage=clean_include_percentage,
        include_grade=clean_include_grade,
        include_question_breakdown=(clean_include_question_breakdown),
        release_message=clean_release_message,
    )

    await _commit_publication_change(
        db,
        conflict_detail=(
            "This assessment already has result-publication " "configuration."
        ),
    )

    refreshed = await repository.get_by_id(
        publication.id,
    )

    if refreshed is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assessment result publication not found.",
        )

    return refreshed


async def get_result_publication(
    db: AsyncSession,
    current_user: User,
    *,
    assessment_id: int,
) -> AssessmentResultPublication:
    """
    Return result-publication configuration for an assessment.
    """

    await _get_assessment_context(
        db,
        current_user,
        assessment_id,
    )

    return await _get_assessment_publication_or_404(
        db,
        assessment_id,
    )


async def update_result_publication(
    db: AsyncSession,
    current_user: User,
    *,
    publication_id: int,
    requires_approval: bool | object = _UNSET,
    visible_to_students: bool | object = _UNSET,
    visible_to_parents: bool | object = _UNSET,
    include_mark: bool | object = _UNSET,
    include_percentage: bool | object = _UNSET,
    include_grade: bool | object = _UNSET,
    include_question_breakdown: bool | object = _UNSET,
    release_message: str | None | object = _UNSET,
) -> AssessmentResultPublication:
    """
    Update result-publication configuration.

    Changing ``requires_approval`` to True clears any prior approval so the
    controlled workflow must be explicitly approved again.

    Changing it to False makes approval unnecessary but preserves no stale
    approval audit.
    """

    publication = await _get_publication_or_404(
        db,
        publication_id,
    )

    await _get_assessment_context(
        db,
        current_user,
        publication.assessment_id,
    )

    repository = AssessmentResultPublicationRepository(
        db,
    )

    if requires_approval is not _UNSET:
        clean_requires_approval = _validate_bool(
            requires_approval,
            field_name="requires_approval",
        )

        if publication.requires_approval != clean_requires_approval:
            publication.requires_approval = clean_requires_approval

            await repository.clear_approval(
                publication,
            )

    if visible_to_students is not _UNSET:
        publication.visible_to_students = _validate_bool(
            visible_to_students,
            field_name="visible_to_students",
        )

    if visible_to_parents is not _UNSET:
        publication.visible_to_parents = _validate_bool(
            visible_to_parents,
            field_name="visible_to_parents",
        )

    if include_mark is not _UNSET:
        publication.include_mark = _validate_bool(
            include_mark,
            field_name="include_mark",
        )

    if include_percentage is not _UNSET:
        publication.include_percentage = _validate_bool(
            include_percentage,
            field_name="include_percentage",
        )

    if include_grade is not _UNSET:
        publication.include_grade = _validate_bool(
            include_grade,
            field_name="include_grade",
        )

    if include_question_breakdown is not _UNSET:
        publication.include_question_breakdown = _validate_bool(
            include_question_breakdown,
            field_name="include_question_breakdown",
        )

    if release_message is not _UNSET:
        publication.release_message = _normalise_optional_text(
            release_message,
            max_length=1000,
            field_name="release_message",
        )

    await repository.flush()

    await _commit_publication_change(
        db,
        conflict_detail=(
            "Unable to update assessment result-publication " "configuration."
        ),
    )

    refreshed = await repository.get_by_id(
        publication.id,
    )

    if refreshed is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assessment result publication not found.",
        )

    return refreshed


async def delete_result_publication(
    db: AsyncSession,
    current_user: User,
    *,
    publication_id: int,
) -> None:
    """
    Delete publication configuration.

    Published configuration cannot be deleted directly. It must first be
    withdrawn so the audit trail reflects that the release was removed.
    """

    publication = await _get_publication_or_404(
        db,
        publication_id,
    )

    await _get_assessment_context(
        db,
        current_user,
        publication.assessment_id,
    )

    if publication.status == AssessmentResultPublicationStatus.PUBLISHED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Published result configuration must be withdrawn "
                "before it can be deleted."
            ),
        )

    await AssessmentResultPublicationRepository(
        db,
    ).delete(
        publication,
    )

    await _commit_publication_change(
        db,
        conflict_detail=(
            "Unable to delete assessment result-publication " "configuration."
        ),
    )


# ---------------------------------------------------------------------------
# Approval workflow
# ---------------------------------------------------------------------------


async def approve_result_publication(
    db: AsyncSession,
    current_user: User,
    *,
    publication_id: int,
    approval_note: str | None = None,
) -> AssessmentResultPublication:
    """
    Approve a controlled assessment result release.

    Teachers do not need this step for ordinary assessments because
    ``requires_approval`` defaults to False.
    """

    publication = await _get_publication_or_404(
        db,
        publication_id,
    )

    await _get_assessment_context(
        db,
        current_user,
        publication.assessment_id,
    )

    if not publication.requires_approval:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=("This assessment does not require approval " "before publication."),
        )

    if not _can_approve_controlled_results(
        current_user,
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "You do not have permission to approve controlled "
                "assessment result publication."
            ),
        )

    clean_note = _normalise_optional_text(
        approval_note,
        field_name="approval_note",
    )

    repository = AssessmentResultPublicationRepository(
        db,
    )

    await repository.mark_approved(
        publication,
        approved_by_id=current_user.id,
        approved_at=_utc_now(),
        approval_note=clean_note,
    )

    await _commit_publication_change(
        db,
        conflict_detail=("Unable to approve assessment result publication."),
    )

    refreshed = await repository.get_by_id(
        publication.id,
    )

    if refreshed is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assessment result publication not found.",
        )

    return refreshed


async def revoke_result_publication_approval(
    db: AsyncSession,
    current_user: User,
    *,
    publication_id: int,
) -> AssessmentResultPublication:
    """
    Revoke approval for a controlled release.

    Approval cannot be revoked while results are currently published.
    """

    publication = await _get_publication_or_404(
        db,
        publication_id,
    )

    await _get_assessment_context(
        db,
        current_user,
        publication.assessment_id,
    )

    if not _can_approve_controlled_results(
        current_user,
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "You do not have permission to revoke controlled "
                "assessment result approval."
            ),
        )

    if publication.status == AssessmentResultPublicationStatus.PUBLISHED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Published results must be withdrawn before " "approval can be revoked."
            ),
        )

    repository = AssessmentResultPublicationRepository(
        db,
    )

    await repository.clear_approval(
        publication,
    )

    await _commit_publication_change(
        db,
        conflict_detail=("Unable to revoke assessment result-publication approval."),
    )

    refreshed = await repository.get_by_id(
        publication.id,
    )

    if refreshed is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assessment result publication not found.",
        )

    return refreshed


# ---------------------------------------------------------------------------
# Immediate publication
# ---------------------------------------------------------------------------


async def publish_results(
    db: AsyncSession,
    current_user: User,
    *,
    publication_id: int,
) -> AssessmentResultPublication:
    """
    Publish assessment results immediately.

    Crucially, the course teacher may call this for their own ordinary
    classroom assessment without SMT approval.

    Approval is checked only when the publication configuration explicitly
    has ``requires_approval=True``.
    """

    publication = await _get_publication_or_404(
        db,
        publication_id,
    )

    assessment_context = await _get_assessment_context(
        db,
        current_user,
        publication.assessment_id,
    )

    _ensure_results_ready_for_release(
        assessment_context,
    )

    _ensure_approval_if_required(
        publication,
    )

    if publication.status == AssessmentResultPublicationStatus.PUBLISHED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Assessment results are already published.",
        )

    repository = AssessmentResultPublicationRepository(
        db,
    )

    await repository.mark_published(
        publication,
        published_by_id=current_user.id,
        published_at=_utc_now(),
    )

    await _commit_publication_change(
        db,
        conflict_detail="Unable to publish assessment results.",
    )

    refreshed = await repository.get_by_id(
        publication.id,
    )

    if refreshed is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assessment result publication not found.",
        )

    await _notify_results_published_best_effort(
        db,
        publication=refreshed,
    )

    return refreshed


# ---------------------------------------------------------------------------
# Scheduled publication
# ---------------------------------------------------------------------------


async def schedule_results_publication(
    db: AsyncSession,
    current_user: User,
    *,
    publication_id: int,
    scheduled_for: datetime,
) -> AssessmentResultPublication:
    """
    Schedule assessment results for future publication.

    The actor must already have normal access to manage the assessment.

    Controlled assessments must already be approved before scheduling.
    """

    publication = await _get_publication_or_404(
        db,
        publication_id,
    )

    assessment_context = await _get_assessment_context(
        db,
        current_user,
        publication.assessment_id,
    )

    _ensure_results_ready_for_release(
        assessment_context,
    )

    _ensure_approval_if_required(
        publication,
    )

    clean_scheduled_for = _normalise_datetime(
        scheduled_for,
        field_name="scheduled_for",
    )

    now = _utc_now()

    if clean_scheduled_for <= now:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="scheduled_for must be in the future.",
        )

    if publication.status == AssessmentResultPublicationStatus.PUBLISHED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Published assessment results must be withdrawn "
                "before another release can be scheduled."
            ),
        )

    repository = AssessmentResultPublicationRepository(
        db,
    )

    await repository.mark_scheduled(
        publication,
        scheduled_for=clean_scheduled_for,
    )

    await _commit_publication_change(
        db,
        conflict_detail=("Unable to schedule assessment result publication."),
    )

    refreshed = await repository.get_by_id(
        publication.id,
    )

    if refreshed is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assessment result publication not found.",
        )

    return refreshed


async def publish_due_scheduled_results(
    db: AsyncSession,
    *,
    now: datetime | None = None,
) -> list[AssessmentResultPublication]:
    """
    Publish all scheduled releases whose release time has arrived.

    This method is intended for a future Celery task.

    It does not accept a current interactive user because scheduled release
    uses the actor who originally configured the publication as its release
    audit identity when no separate scheduler/system actor exists.

    Controlled-result approval is rechecked before publication.

    Publications that no longer satisfy approval requirements are skipped.
    """

    effective_now = (
        _utc_now()
        if now is None
        else _normalise_datetime(
            now,
            field_name="now",
        )
    )

    repository = AssessmentResultPublicationRepository(
        db,
    )

    due = await repository.list_due_scheduled_publications(
        now=effective_now,
    )

    published: list[AssessmentResultPublication] = []

    for publication in due:
        if publication.requires_approval and publication.approved_at is None:
            continue

        await repository.mark_published(
            publication,
            published_by_id=publication.created_by_id,
            published_at=effective_now,
        )

        published.append(
            publication,
        )

    if published:
        await _commit_publication_change(
            db,
            conflict_detail=("Unable to publish scheduled assessment results."),
        )

        for publication in published:
            refreshed = await repository.get_by_id(
                publication.id,
            )

            if refreshed is None:
                logger.error(
                    (
                        "Assessment result publication %s could not be "
                        "reloaded for post-commit notification after "
                        "scheduled publication."
                    ),
                    publication.id,
                )
                continue

            await _notify_results_published_best_effort(
                db,
                publication=refreshed,
            )

    return published


# ---------------------------------------------------------------------------
# Withdrawal
# ---------------------------------------------------------------------------


async def withdraw_results(
    db: AsyncSession,
    current_user: User,
    *,
    publication_id: int,
    withdrawal_reason: str | None = None,
) -> AssessmentResultPublication:
    """
    Withdraw published or scheduled assessment results.

    The owning course teacher may withdraw their own ordinary result release.
    School administrators retain their broader assessment access.
    """

    publication = await _get_publication_or_404(
        db,
        publication_id,
    )

    await _get_assessment_context(
        db,
        current_user,
        publication.assessment_id,
    )

    if publication.status not in {
        AssessmentResultPublicationStatus.PUBLISHED,
        AssessmentResultPublicationStatus.SCHEDULED,
    }:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Only published or scheduled assessment results " "can be withdrawn."
            ),
        )

    clean_reason = _normalise_optional_text(
        withdrawal_reason,
        field_name="withdrawal_reason",
    )

    repository = AssessmentResultPublicationRepository(
        db,
    )

    await repository.mark_withdrawn(
        publication,
        withdrawn_by_id=current_user.id,
        withdrawn_at=_utc_now(),
        withdrawal_reason=clean_reason,
    )

    await _commit_publication_change(
        db,
        conflict_detail="Unable to withdraw assessment results.",
    )

    refreshed = await repository.get_by_id(
        publication.id,
    )

    if refreshed is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assessment result publication not found.",
        )

    return refreshed


# ---------------------------------------------------------------------------
# Audience visibility helpers
# ---------------------------------------------------------------------------


async def get_published_result_visibility(
    db: AsyncSession,
    *,
    assessment_id: int,
) -> AssessmentResultPublication | None:
    """
    Return active publication configuration without staff permission checks.

    This low-level helper is intended for student/parent result services,
    which perform their own identity and relationship checks before exposing
    assessment data.
    """

    return await AssessmentResultPublicationRepository(
        db,
    ).get_published_for_assessment(
        assessment_id,
    )


async def can_student_view_results(
    db: AsyncSession,
    *,
    assessment_id: int,
) -> bool:
    """
    Return whether the publication currently allows student visibility.
    """

    publication = await get_published_result_visibility(
        db,
        assessment_id=assessment_id,
    )

    return bool(publication is not None and publication.visible_to_students)


async def can_parent_view_results(
    db: AsyncSession,
    *,
    assessment_id: int,
) -> bool:
    """
    Return whether the publication currently allows parent visibility.
    """

    publication = await get_published_result_visibility(
        db,
        assessment_id=assessment_id,
    )

    return bool(publication is not None and publication.visible_to_parents)
