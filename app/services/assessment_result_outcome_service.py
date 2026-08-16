from __future__ import annotations

import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.assessment import Assessment
from app.models.assessment_result_outcome import (
    AssessmentResultChangeType,
    AssessmentResultOutcome,
    AssessmentResultOutcomeStatus,
)
from app.models.user import User
from app.repositories.assessment_result_outcome import (
    AssessmentResultOutcomeRepository,
    _UNSET,
)
from app.repositories.assessment_result_publication import (
    AssessmentResultPublicationRepository,
)
from app.services.assessment_grading_service import grade_script_result
from app.services.assessment_notification_service import (
    AssessmentNotificationService,
)
from app.services.assessment_results_service import (
    get_candidate_result,
    get_script_result,
)

logger = logging.getLogger(
    __name__,
)

# ---------------------------------------------------------------------------
# Time helper
# ---------------------------------------------------------------------------


def _utc_now() -> datetime:
    return datetime.now(
        timezone.utc,
    )


# ---------------------------------------------------------------------------
# Validation / normalisation
# ---------------------------------------------------------------------------


def _validate_positive_integer(
    value: int,
    *,
    field_name: str,
) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
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

    return cleaned or None


def _normalise_required_text(
    value: str,
    *,
    field_name: str,
) -> str:
    if not isinstance(
        value,
        str,
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"{field_name} must be a string.",
        )

    cleaned = value.strip()

    if not cleaned:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"{field_name} cannot be blank.",
        )

    return cleaned


def _normalise_change_type(
    value: AssessmentResultChangeType | str,
) -> AssessmentResultChangeType:
    if isinstance(
        value,
        AssessmentResultChangeType,
    ):
        return value

    if not isinstance(
        value,
        str,
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Invalid assessment result change type.",
        )

    try:
        return AssessmentResultChangeType(
            value.strip(),
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Invalid assessment result change type.",
        ) from exc


def _normalise_effective_at(
    value: datetime | None,
) -> datetime:
    if value is None:
        return _utc_now()

    if not isinstance(
        value,
        datetime,
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="effective_at must be a datetime.",
        )

    return value


# ---------------------------------------------------------------------------
# Database transaction helpers
# ---------------------------------------------------------------------------


async def _commit_outcome_change(
    db: AsyncSession,
    *,
    conflict_detail: str,
) -> None:
    try:
        await db.commit()

    except IntegrityError as exc:
        await db.rollback()

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=conflict_detail,
        ) from exc


async def _rollback_and_raise_conflict(
    db: AsyncSession,
    exc: IntegrityError,
    *,
    detail: str,
) -> None:
    await db.rollback()

    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail=detail,
    ) from exc


# ---------------------------------------------------------------------------
# Access / context helpers
# ---------------------------------------------------------------------------


async def _get_assessment_school_id(
    db: AsyncSession,
    *,
    assessment_id: int,
) -> int:
    assessment = await db.get(
        Assessment,
        assessment_id,
    )

    if assessment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assessment not found.",
        )

    return int(
        assessment.school_id,
    )


async def _authorise_outcome_access(
    db: AsyncSession,
    current_user: User,
    outcome: AssessmentResultOutcome,
) -> None:
    """
    Reuse the assessment-results access model.

    Teachers may therefore access outcomes only for courses they teach,
    school administrators remain school-scoped, and platform administrators
    retain cross-school access.
    """

    result = await get_script_result(
        db=db,
        current_user=current_user,
        script_id=outcome.script_id,
    )

    if (
        int(
            result["candidate_id"],
        )
        != outcome.candidate_id
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Assessment result outcome and script candidate " "are inconsistent."
            ),
        )

    if (
        int(
            result["assessment_id"],
        )
        != outcome.assessment_id
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Assessment result outcome and script assessment " "are inconsistent."
            ),
        )

    school_id = await _get_assessment_school_id(
        db,
        assessment_id=outcome.assessment_id,
    )

    if school_id != outcome.school_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Assessment result outcome and assessment school "
                "scope are inconsistent."
            ),
        )


async def _authorise_candidate_access(
    db: AsyncSession,
    current_user: User,
    *,
    candidate_id: int,
) -> dict[str, Any]:
    return await get_candidate_result(
        db=db,
        current_user=current_user,
        candidate_id=candidate_id,
    )


# ---------------------------------------------------------------------------
# Snapshot construction
# ---------------------------------------------------------------------------


async def _get_optional_grade_snapshot(
    db: AsyncSession,
    current_user: User,
    *,
    script_id: int,
) -> dict[str, Any] | None:
    """
    Return a grade snapshot where an active grading scheme exists.

    Grading is optional in MHike School. An otherwise valid, fully-finalised
    result must still be capable of becoming authoritative when no grading
    scheme has been configured.
    """

    try:
        return await grade_script_result(
            db=db,
            current_user=current_user,
            script_id=script_id,
            result_stage="finalised",
        )

    except HTTPException as exc:
        if (
            exc.status_code == status.HTTP_404_NOT_FOUND
            and exc.detail
            == "No active grading scheme is configured for this assessment."
        ):
            return None

        raise


async def _build_result_snapshot(
    db: AsyncSession,
    current_user: User,
    *,
    script_id: int,
) -> dict[str, Any]:
    """
    Capture the current fully-finalised script result and grading state.

    These values are persisted so later mark changes or grade-boundary changes
    cannot rewrite historical official outcomes.
    """

    _validate_positive_integer(
        script_id,
        field_name="script_id",
    )

    result = await get_script_result(
        db=db,
        current_user=current_user,
        script_id=script_id,
    )

    if not result.get(
        "is_fully_finalised",
        False,
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "A result outcome can only be recorded when the "
                "script is fully finalised."
            ),
        )

    finalised_mark = result.get(
        "finalised_mark_awarded",
    )

    if finalised_mark is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "The fully-finalised script does not have an "
                "authoritative mark total."
            ),
        )

    maximum_mark = result.get(
        "maximum_mark",
    )

    if maximum_mark is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Assessment maximum mark is unavailable.",
        )

    assessment_id = int(
        result["assessment_id"],
    )

    school_id = await _get_assessment_school_id(
        db,
        assessment_id=assessment_id,
    )

    grade_result = await _get_optional_grade_snapshot(
        db,
        current_user,
        script_id=script_id,
    )

    snapshot: dict[str, Any] = {
        "school_id": school_id,
        "assessment_id": assessment_id,
        "candidate_id": int(
            result["candidate_id"],
        ),
        "student_id": int(
            result["student_id"],
        ),
        "script_id": int(
            result["script_id"],
        ),
        "script_version_snapshot": int(
            result["script_version"],
        ),
        "mark_awarded_snapshot": Decimal(
            str(
                finalised_mark,
            ),
        ),
        "maximum_mark_snapshot": Decimal(
            str(
                maximum_mark,
            ),
        ),
        "percentage_snapshot": (
            Decimal(
                str(
                    result["finalised_percentage"],
                ),
            )
            if result.get(
                "finalised_percentage",
            )
            is not None
            else None
        ),
        "grading_scheme_id_snapshot": None,
        "grading_scheme_name_snapshot": None,
        "grading_basis_snapshot": None,
        "grade_boundary_id_snapshot": None,
        "grade_label_snapshot": None,
        "grade_points_snapshot": None,
        "is_pass_snapshot": None,
    }

    if grade_result is not None:
        basis = grade_result.get(
            "basis",
        )

        snapshot.update(
            {
                "grading_scheme_id_snapshot": grade_result.get(
                    "grading_scheme_id",
                ),
                "grading_scheme_name_snapshot": grade_result.get(
                    "grading_scheme_name",
                ),
                "grading_basis_snapshot": (
                    basis.value
                    if hasattr(
                        basis,
                        "value",
                    )
                    else (
                        str(
                            basis,
                        )
                        if basis is not None
                        else None
                    )
                ),
                "grade_boundary_id_snapshot": grade_result.get(
                    "boundary_id",
                ),
                "grade_label_snapshot": grade_result.get(
                    "grade",
                ),
                "grade_points_snapshot": grade_result.get(
                    "grade_points",
                ),
                "is_pass_snapshot": grade_result.get(
                    "is_pass",
                ),
            }
        )

    return snapshot


# ---------------------------------------------------------------------------
# Transition rules
# ---------------------------------------------------------------------------


def _validate_new_outcome_transition(
    *,
    change_type: AssessmentResultChangeType,
    snapshot: dict[str, Any],
    latest: AssessmentResultOutcome | None,
    current: AssessmentResultOutcome | None,
) -> None:
    """
    Enforce semantic rules for result-history transitions.

    Merely creating a higher-numbered script never makes it authoritative.
    The change type describes why a result authority decision is changing.
    """

    if latest is not None and latest.status == AssessmentResultOutcomeStatus.DRAFT:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "This candidate already has a draft result outcome. "
                "Authorise or delete that draft before creating another."
            ),
        )

    if change_type == AssessmentResultChangeType.INITIAL:
        if latest is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "An initial result outcome may only be created "
                    "when the candidate has no result outcome history."
                ),
            )

        return

    if current is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "A non-initial result outcome requires an existing "
                "authoritative result."
            ),
        )

    if current.candidate_id != int(
        snapshot["candidate_id"],
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Result outcome candidate history is inconsistent.",
        )

    if current.assessment_id != int(
        snapshot["assessment_id"],
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Result outcome assessment history is inconsistent.",
        )

    script_id = int(
        snapshot["script_id"],
    )

    script_version = int(
        snapshot["script_version_snapshot"],
    )

    if change_type == AssessmentResultChangeType.RETAKE:
        if script_id == current.script_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "A retake outcome must be based on a different "
                    "script from the current authoritative outcome."
                ),
            )

        if script_version <= current.script_version_snapshot:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "A retake outcome must use a later script version "
                    "than the current authoritative outcome."
                ),
            )

        return

    if change_type in {
        AssessmentResultChangeType.REMARK,
        AssessmentResultChangeType.CORRECTION,
        AssessmentResultChangeType.MODERATION,
    }:
        if script_id != current.script_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"A {change_type.value} outcome must refer to the "
                    "same script as the current authoritative outcome."
                ),
            )


def _validate_reason_requirement(
    *,
    change_type: AssessmentResultChangeType,
    reason: str | None,
) -> None:
    if change_type == AssessmentResultChangeType.INITIAL:
        return

    if reason is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=("A reason is required for non-initial result outcomes."),
        )


# ---------------------------------------------------------------------------
# Serialisation
# ---------------------------------------------------------------------------


def _outcome_to_dict(
    outcome: AssessmentResultOutcome,
) -> dict[str, Any]:
    recorded_by = getattr(
        outcome,
        "recorded_by",
        None,
    )

    withdrawn_by = getattr(
        outcome,
        "withdrawn_by",
        None,
    )

    return {
        "id": outcome.id,
        "school_id": outcome.school_id,
        "assessment_id": outcome.assessment_id,
        "candidate_id": outcome.candidate_id,
        "script_id": outcome.script_id,
        "version": outcome.version,
        "status": outcome.status,
        "change_type": outcome.change_type,
        "supersedes_id": outcome.supersedes_id,
        "is_authoritative": outcome.is_authoritative,
        "mark_awarded_snapshot": outcome.mark_awarded_snapshot,
        "maximum_mark_snapshot": outcome.maximum_mark_snapshot,
        "percentage_snapshot": outcome.percentage_snapshot,
        "grading_scheme_id_snapshot": (outcome.grading_scheme_id_snapshot),
        "grading_scheme_name_snapshot": (outcome.grading_scheme_name_snapshot),
        "grading_basis_snapshot": outcome.grading_basis_snapshot,
        "grade_boundary_id_snapshot": (outcome.grade_boundary_id_snapshot),
        "grade_label_snapshot": outcome.grade_label_snapshot,
        "grade_points_snapshot": outcome.grade_points_snapshot,
        "is_pass_snapshot": outcome.is_pass_snapshot,
        "script_version_snapshot": outcome.script_version_snapshot,
        "reason": outcome.reason,
        "notes": outcome.notes,
        "effective_at": outcome.effective_at,
        "recorded_by_id": outcome.recorded_by_id,
        "recorded_by_name": (
            getattr(
                recorded_by,
                "full_name",
                None,
            )
            if recorded_by is not None
            else None
        ),
        "recorded_at": outcome.recorded_at,
        "withdrawn_at": outcome.withdrawn_at,
        "withdrawn_by_id": outcome.withdrawn_by_id,
        "withdrawn_by_name": (
            getattr(
                withdrawn_by,
                "full_name",
                None,
            )
            if withdrawn_by is not None
            else None
        ),
        "withdrawal_reason": outcome.withdrawal_reason,
    }


# ---------------------------------------------------------------------------
# Authorised outcome lookup
# ---------------------------------------------------------------------------


async def _get_outcome_or_404(
    db: AsyncSession,
    current_user: User,
    *,
    outcome_id: int,
) -> AssessmentResultOutcome:
    _validate_positive_integer(
        outcome_id,
        field_name="outcome_id",
    )

    outcome = await AssessmentResultOutcomeRepository(
        db,
    ).get_by_id(
        outcome_id,
    )

    if outcome is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assessment result outcome not found.",
        )

    await _authorise_outcome_access(
        db,
        current_user,
        outcome,
    )

    return outcome


# ---------------------------------------------------------------------------
# Post-authorisation notification
# ---------------------------------------------------------------------------


async def _notify_authoritative_result_change_best_effort(
    db: AsyncSession,
    *,
    outcome: AssessmentResultOutcome,
    student_id: int,
    assessment_title: str,
) -> None:
    """
    Notify only audiences that can currently see the published assessment.

    Initial authoritative outcomes are deliberately excluded. Initial result
    visibility is communicated by the publication event itself.

    Non-initial authoritative changes are also silent while results are
    unreleased, scheduled, or withdrawn. If results are currently published,
    student and parent notification audiences follow the publication's
    ``visible_to_students`` and ``visible_to_parents`` flags independently.

    Notifications occur only after the authoritative-result transaction has
    committed. Notification failure must therefore never make a successful
    official-result transition appear to have failed to the caller.
    """

    if outcome.change_type == AssessmentResultChangeType.INITIAL:
        return

    try:
        publication = await AssessmentResultPublicationRepository(
            db,
        ).get_published_for_assessment(
            outcome.assessment_id,
        )

        if publication is None:
            return

        notify_student = bool(
            publication.visible_to_students,
        )
        notify_parents = bool(
            publication.visible_to_parents,
        )

        if not (notify_student or notify_parents):
            return

        await AssessmentNotificationService(
            db,
        ).notify_official_result_changed(
            assessment_id=outcome.assessment_id,
            assessment_title=assessment_title,
            school_id=outcome.school_id,
            student_id=student_id,
            change_type=outcome.change_type,
            notify_student=notify_student,
            notify_parents=notify_parents,
        )

    except Exception:
        logger.exception(
            (
                "Unable to create assessment result-change notification "
                "after authoritative outcome %s was committed."
            ),
            outcome.id,
        )

        try:
            await db.rollback()
        except Exception:
            logger.exception(
                (
                    "Unable to roll back failed notification transaction "
                    "for authoritative outcome %s."
                ),
                outcome.id,
            )


# ---------------------------------------------------------------------------
# Create result outcome
# ---------------------------------------------------------------------------


async def create_assessment_result_outcome(
    db: AsyncSession,
    current_user: User,
    *,
    script_id: int,
    change_type: AssessmentResultChangeType | str,
    reason: str | None = None,
    notes: str | None = None,
    effective_at: datetime | None = None,
    make_authoritative: bool = False,
) -> dict[str, Any]:
    """
    Capture a new immutable result snapshot.

    When ``make_authoritative=False`` the row remains DRAFT and the current
    authoritative result is unchanged.

    When ``make_authoritative=True`` the existing authoritative outcome is
    superseded in the same transaction and the new snapshot becomes official.
    """

    if not isinstance(
        make_authoritative,
        bool,
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="make_authoritative must be a boolean.",
        )

    normalised_change_type = _normalise_change_type(
        change_type,
    )

    clean_reason = _normalise_optional_text(
        reason,
        field_name="reason",
    )

    clean_notes = _normalise_optional_text(
        notes,
        field_name="notes",
    )

    _validate_reason_requirement(
        change_type=normalised_change_type,
        reason=clean_reason,
    )

    clean_effective_at = _normalise_effective_at(
        effective_at,
    )

    snapshot = await _build_result_snapshot(
        db,
        current_user,
        script_id=script_id,
    )

    repository = AssessmentResultOutcomeRepository(
        db,
    )

    candidate_id = int(
        snapshot["candidate_id"],
    )

    current = await repository.get_authoritative_for_candidate(
        candidate_id,
        school_id=int(
            snapshot["school_id"],
        ),
        include_relationships=True,
        for_update=True,
    )

    latest = await repository.get_latest_for_candidate(
        candidate_id,
        school_id=int(
            snapshot["school_id"],
        ),
        include_relationships=False,
    )

    _validate_new_outcome_transition(
        change_type=normalised_change_type,
        snapshot=snapshot,
        latest=latest,
        current=current,
    )

    version = await repository.get_next_version(
        candidate_id,
        lock_history=True,
    )

    supersedes_id = current.id if current is not None else None

    outcome = await repository.create_outcome(
        school_id=int(
            snapshot["school_id"],
        ),
        assessment_id=int(
            snapshot["assessment_id"],
        ),
        candidate_id=candidate_id,
        script_id=int(
            snapshot["script_id"],
        ),
        version=version,
        change_type=normalised_change_type,
        mark_awarded_snapshot=snapshot["mark_awarded_snapshot"],
        maximum_mark_snapshot=snapshot["maximum_mark_snapshot"],
        percentage_snapshot=snapshot["percentage_snapshot"],
        script_version_snapshot=int(
            snapshot["script_version_snapshot"],
        ),
        effective_at=clean_effective_at,
        recorded_by_id=current_user.id,
        status=AssessmentResultOutcomeStatus.DRAFT,
        supersedes_id=supersedes_id,
        is_authoritative=False,
        grading_scheme_id_snapshot=snapshot["grading_scheme_id_snapshot"],
        grading_scheme_name_snapshot=snapshot["grading_scheme_name_snapshot"],
        grading_basis_snapshot=snapshot["grading_basis_snapshot"],
        grade_boundary_id_snapshot=snapshot["grade_boundary_id_snapshot"],
        grade_label_snapshot=snapshot["grade_label_snapshot"],
        grade_points_snapshot=snapshot["grade_points_snapshot"],
        is_pass_snapshot=snapshot["is_pass_snapshot"],
        reason=clean_reason,
        notes=clean_notes,
    )

    try:
        await repository.flush()

        if make_authoritative:
            if current is not None:
                await repository.supersede_outcome(
                    current,
                )

            await repository.make_authoritative(
                outcome,
            )

        await db.commit()

    except IntegrityError as exc:
        await _rollback_and_raise_conflict(
            db,
            exc,
            detail=(
                "Unable to create the result outcome because another "
                "result-history change was recorded concurrently."
            ),
        )

    refreshed = await repository.get_by_id(
        outcome.id,
    )

    if refreshed is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assessment result outcome not found after creation.",
        )

    if make_authoritative:
        await _notify_authoritative_result_change_best_effort(
            db,
            outcome=refreshed,
            student_id=int(
                snapshot["student_id"],
            ),
            assessment_title=str(
                refreshed.assessment.title,
            ),
        )

    return _outcome_to_dict(
        refreshed,
    )


# ---------------------------------------------------------------------------
# Read outcome / history
# ---------------------------------------------------------------------------


async def get_assessment_result_outcome(
    db: AsyncSession,
    current_user: User,
    *,
    outcome_id: int,
) -> dict[str, Any]:
    outcome = await _get_outcome_or_404(
        db,
        current_user,
        outcome_id=outcome_id,
    )

    return _outcome_to_dict(
        outcome,
    )


async def get_authoritative_assessment_result_outcome(
    db: AsyncSession,
    current_user: User,
    *,
    candidate_id: int,
) -> dict[str, Any]:
    _validate_positive_integer(
        candidate_id,
        field_name="candidate_id",
    )

    candidate_result = await _authorise_candidate_access(
        db,
        current_user,
        candidate_id=candidate_id,
    )

    repository = AssessmentResultOutcomeRepository(
        db,
    )

    outcome = await repository.get_authoritative_for_candidate(
        candidate_id,
    )

    if outcome is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                "This assessment candidate does not have an "
                "authoritative result outcome."
            ),
        )

    if outcome.assessment_id != int(
        candidate_result["assessment_id"],
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Assessment candidate and authoritative result "
                "history are inconsistent."
            ),
        )

    return _outcome_to_dict(
        outcome,
    )


async def list_assessment_result_outcome_history(
    db: AsyncSession,
    current_user: User,
    *,
    candidate_id: int,
) -> list[dict[str, Any]]:
    _validate_positive_integer(
        candidate_id,
        field_name="candidate_id",
    )

    candidate_result = await _authorise_candidate_access(
        db,
        current_user,
        candidate_id=candidate_id,
    )

    outcomes = await AssessmentResultOutcomeRepository(
        db,
    ).list_for_candidate(
        candidate_id,
    )

    assessment_id = int(
        candidate_result["assessment_id"],
    )

    for outcome in outcomes:
        if outcome.assessment_id != assessment_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=("Assessment candidate and result history " "are inconsistent."),
            )

    return [
        _outcome_to_dict(
            outcome,
        )
        for outcome in outcomes
    ]


# ---------------------------------------------------------------------------
# Draft metadata update
# ---------------------------------------------------------------------------


async def update_assessment_result_outcome_draft(
    db: AsyncSession,
    current_user: User,
    *,
    outcome_id: int,
    reason: str | None | object = _UNSET,
    notes: str | None | object = _UNSET,
    effective_at: datetime | object = _UNSET,
) -> dict[str, Any]:
    outcome = await _get_outcome_or_404(
        db,
        current_user,
        outcome_id=outcome_id,
    )

    if outcome.status != AssessmentResultOutcomeStatus.DRAFT:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only draft result outcomes may be edited.",
        )

    clean_reason: str | None | object = _UNSET
    clean_notes: str | None | object = _UNSET
    clean_effective_at: datetime | object = _UNSET

    if reason is not _UNSET:
        clean_reason = _normalise_optional_text(
            reason,
            field_name="reason",
        )

    if notes is not _UNSET:
        clean_notes = _normalise_optional_text(
            notes,
            field_name="notes",
        )

    if effective_at is not _UNSET:
        if not isinstance(
            effective_at,
            datetime,
        ):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="effective_at must be a datetime.",
            )

        clean_effective_at = effective_at

    resulting_reason = outcome.reason if clean_reason is _UNSET else clean_reason

    _validate_reason_requirement(
        change_type=outcome.change_type,
        reason=resulting_reason,
    )

    repository = AssessmentResultOutcomeRepository(
        db,
    )

    try:
        await repository.update_draft_metadata(
            outcome,
            reason=clean_reason,
            notes=clean_notes,
            effective_at=clean_effective_at,
        )

        await db.commit()

    except IntegrityError as exc:
        await _rollback_and_raise_conflict(
            db,
            exc,
            detail="Unable to update the draft result outcome.",
        )

    refreshed = await repository.get_by_id(
        outcome.id,
    )

    if refreshed is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assessment result outcome not found after update.",
        )

    return _outcome_to_dict(
        refreshed,
    )


# ---------------------------------------------------------------------------
# Authorise an existing draft
# ---------------------------------------------------------------------------


async def authorise_assessment_result_outcome(
    db: AsyncSession,
    current_user: User,
    *,
    outcome_id: int,
) -> dict[str, Any]:
    outcome = await _get_outcome_or_404(
        db,
        current_user,
        outcome_id=outcome_id,
    )

    if outcome.status != AssessmentResultOutcomeStatus.DRAFT:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only a draft result outcome can become authoritative.",
        )

    repository = AssessmentResultOutcomeRepository(
        db,
    )

    latest = await repository.get_latest_for_candidate(
        outcome.candidate_id,
        school_id=outcome.school_id,
        include_relationships=False,
    )

    if latest is None or latest.id != outcome.id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Only the candidate's latest result outcome "
                "may become authoritative."
            ),
        )

    current = await repository.get_authoritative_for_candidate(
        outcome.candidate_id,
        school_id=outcome.school_id,
        include_relationships=True,
        for_update=True,
    )

    snapshot = {
        "candidate_id": outcome.candidate_id,
        "assessment_id": outcome.assessment_id,
        "script_id": outcome.script_id,
        "script_version_snapshot": outcome.script_version_snapshot,
    }

    if outcome.change_type == AssessmentResultChangeType.INITIAL:
        if current is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "An initial result outcome cannot replace an "
                    "existing authoritative result."
                ),
            )

    else:
        if current is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "A non-initial result outcome requires an existing "
                    "authoritative result."
                ),
            )

        _validate_new_outcome_transition(
            change_type=outcome.change_type,
            snapshot=snapshot,
            latest=None,
            current=current,
        )

    try:
        if current is not None:
            await repository.supersede_outcome(
                current,
            )

        await repository.make_authoritative(
            outcome,
        )

        await db.commit()

    except IntegrityError as exc:
        await _rollback_and_raise_conflict(
            db,
            exc,
            detail=(
                "Unable to make this result authoritative because "
                "another result-history change occurred concurrently."
            ),
        )

    refreshed = await repository.get_by_id(
        outcome.id,
    )

    if refreshed is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assessment result outcome not found after authorisation.",
        )

    await _notify_authoritative_result_change_best_effort(
        db,
        outcome=refreshed,
        student_id=int(
            refreshed.candidate.student_id,
        ),
        assessment_title=str(
            refreshed.assessment.title,
        ),
    )

    return _outcome_to_dict(
        refreshed,
    )


# ---------------------------------------------------------------------------
# Withdraw outcome
# ---------------------------------------------------------------------------


async def withdraw_assessment_result_outcome(
    db: AsyncSession,
    current_user: User,
    *,
    outcome_id: int,
    withdrawal_reason: str,
) -> dict[str, Any]:
    outcome = await _get_outcome_or_404(
        db,
        current_user,
        outcome_id=outcome_id,
    )

    if outcome.status == AssessmentResultOutcomeStatus.DRAFT:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=("Draft outcomes should be deleted rather than withdrawn."),
        )

    if outcome.status == AssessmentResultOutcomeStatus.WITHDRAWN:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This result outcome has already been withdrawn.",
        )

    clean_reason = _normalise_required_text(
        withdrawal_reason,
        field_name="withdrawal_reason",
    )

    repository = AssessmentResultOutcomeRepository(
        db,
    )

    try:
        await repository.withdraw_outcome(
            outcome,
            withdrawn_at=_utc_now(),
            withdrawn_by_id=current_user.id,
            withdrawal_reason=clean_reason,
        )

        await db.commit()

    except IntegrityError as exc:
        await _rollback_and_raise_conflict(
            db,
            exc,
            detail="Unable to withdraw the result outcome.",
        )

    refreshed = await repository.get_by_id(
        outcome.id,
    )

    if refreshed is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assessment result outcome not found after withdrawal.",
        )

    return _outcome_to_dict(
        refreshed,
    )


# ---------------------------------------------------------------------------
# Delete draft
# ---------------------------------------------------------------------------


async def delete_assessment_result_outcome_draft(
    db: AsyncSession,
    current_user: User,
    *,
    outcome_id: int,
) -> None:
    outcome = await _get_outcome_or_404(
        db,
        current_user,
        outcome_id=outcome_id,
    )

    if outcome.status != AssessmentResultOutcomeStatus.DRAFT:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Historical result outcomes cannot be deleted. "
                "Only drafts may be removed."
            ),
        )

    repository = AssessmentResultOutcomeRepository(
        db,
    )

    await repository.delete_draft(
        outcome,
    )

    await _commit_outcome_change(
        db,
        conflict_detail="Unable to delete the draft result outcome.",
    )
