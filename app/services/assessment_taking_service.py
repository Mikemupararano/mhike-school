from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from fastapi import HTTPException, status
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import load_only, raiseload

from app.core.permissions import PermissionService
from app.models.assessment import Assessment, AssessmentStatus
from app.models.assessment_candidate import (
    AssessmentCandidate,
    AssessmentCandidateStatus,
    AssessmentScript,
    AssessmentScriptStatus,
)
from app.models.assessment_question import (
    AssessmentQuestion,
    AssessmentQuestionType,
)
from app.models.assessment_question_snapshot import AssessmentQuestionSnapshot
from app.models.assessment_response import (
    AssessmentResponse,
    AssessmentResponseStatus,
)
from app.models.user import User
from app.repositories.assessment_candidate import AssessmentCandidateRepository
from app.repositories.assessment_question import AssessmentQuestionRepository
from app.schemas.assessment_marking import DiagramAnnotationResponseData
from app.schemas.assessment_taking import (
    AssessmentTakingAssetOut,
    AssessmentTakingOptionOut,
    AssessmentTakingQuestionOut,
    AssessmentTakingResponseOut,
    AssessmentTakingResponseSave,
    AssessmentTakingScriptOut,
    AssessmentTakingSectionOut,
    StudentAssessmentAttemptOut,
    StudentAssessmentStartOut,
    StudentAssessmentSubmitOut,
    StudentAssessmentSummaryOut,
)
from app.services import assessment_document_service

# ---------------------------------------------------------------------------
# General helpers
# ---------------------------------------------------------------------------


def _utc_now() -> datetime:
    """
    Return a timezone-aware UTC timestamp.
    """

    return datetime.now(
        timezone.utc,
    )


def _as_utc(
    value: datetime,
) -> datetime:
    """
    Normalise a database datetime for safe UTC comparison.

    Timezone-aware values are converted to UTC. Naive values are interpreted
    as UTC defensively so older/test data cannot trigger mixed-awareness
    comparison errors.
    """

    if value.tzinfo is None:
        return value.replace(
            tzinfo=timezone.utc,
        )

    return value.astimezone(
        timezone.utc,
    )


def _clean_optional_text(
    value: str | None,
) -> str | None:
    """
    Trim optional learner text and normalise blank content to None.
    """

    if value is None:
        return None

    cleaned = value.strip()

    return cleaned or None


def _ensure_student_access(
    current_user: User,
) -> int:
    """
    Require an active student with a concrete school scope.

    The returned value is the student's school id and is used in every
    candidate-facing query as an additional isolation boundary.
    """

    PermissionService.ensure_active_user(
        current_user,
    )
    PermissionService.ensure_student(
        current_user,
    )

    if current_user.school_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Student account is not assigned to a school.",
        )

    return current_user.school_id


def _is_assessment_open_now(
    assessment: Assessment,
    *,
    now: datetime,
) -> bool:
    """
    Return whether the assessment is currently available for candidate work.
    """

    if assessment.status != AssessmentStatus.PUBLISHED:
        return False

    if assessment.scheduled_at is not None:
        if now < _as_utc(
            assessment.scheduled_at,
        ):
            return False

    if assessment.closes_at is not None:
        if now >= _as_utc(
            assessment.closes_at,
        ):
            return False

    return True


def _ensure_assessment_open_now(
    assessment: Assessment,
    *,
    now: datetime,
) -> None:
    """
    Require a published assessment within its configured availability window.
    """

    if assessment.status != AssessmentStatus.PUBLISHED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Assessment is not currently open for student attempts.",
        )

    if assessment.scheduled_at is not None:
        scheduled_at = _as_utc(
            assessment.scheduled_at,
        )

        if now < scheduled_at:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Assessment is not available yet.",
            )

    if assessment.closes_at is not None:
        closes_at = _as_utc(
            assessment.closes_at,
        )

        if now >= closes_at:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Assessment is closed.",
            )


# ---------------------------------------------------------------------------
# Candidate / assessment ownership queries
# ---------------------------------------------------------------------------


async def _get_owned_candidate_context(
    db: AsyncSession,
    *,
    current_user: User,
    assessment_id: int,
    for_update: bool = False,
) -> tuple[AssessmentCandidate, Assessment]:
    """
    Return the logged-in student's candidate allocation and assessment.

    Ownership is derived from ``current_user.id`` rather than a browser-supplied
    candidate id. School scope is included in the SQL predicate so allocations
    from another school are indistinguishable from missing allocations.

    ``raiseload("*")`` prevents model-level selectin relationships from
    hydrating unrelated candidate/assessment data.
    """

    if (
        not isinstance(
            assessment_id,
            int,
        )
        or isinstance(
            assessment_id,
            bool,
        )
        or assessment_id < 1
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Assessment ID must be a positive integer.",
        )

    school_id = _ensure_student_access(
        current_user,
    )

    statement = (
        select(
            AssessmentCandidate,
            Assessment,
        )
        .join(
            Assessment,
            Assessment.id == AssessmentCandidate.assessment_id,
        )
        .where(
            AssessmentCandidate.assessment_id == assessment_id,
            AssessmentCandidate.student_id == current_user.id,
            Assessment.school_id == school_id,
        )
        .options(
            raiseload("*"),
            load_only(
                AssessmentCandidate.id,
                AssessmentCandidate.assessment_id,
                AssessmentCandidate.student_id,
                AssessmentCandidate.status,
                AssessmentCandidate.allocated_at,
                AssessmentCandidate.started_at,
                AssessmentCandidate.submitted_at,
            ),
            load_only(
                Assessment.id,
                Assessment.school_id,
                Assessment.title,
                Assessment.description,
                Assessment.assessment_type,
                Assessment.academic_year,
                Assessment.term,
                Assessment.status,
                Assessment.scheduled_at,
                Assessment.closes_at,
            ),
        )
    )

    if for_update:
        statement = statement.with_for_update()

    result = await db.execute(
        statement,
    )

    row = result.one_or_none()

    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student assessment allocation not found.",
        )

    candidate, assessment = row

    # Defence in depth. The SQL predicate above already enforces school scope.
    PermissionService.ensure_same_school(
        current_user,
        assessment.school_id,
    )

    if candidate.student_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student assessment allocation not found.",
        )

    return candidate, assessment


async def _list_owned_candidate_contexts(
    db: AsyncSession,
    *,
    current_user: User,
) -> list[tuple[AssessmentCandidate, Assessment]]:
    """
    Return all assessment allocations owned by the logged-in student.

    No candidate relationships, scripts, questions, marks, or other students
    are hydrated.
    """

    school_id = _ensure_student_access(
        current_user,
    )

    statement = (
        select(
            AssessmentCandidate,
            Assessment,
        )
        .join(
            Assessment,
            Assessment.id == AssessmentCandidate.assessment_id,
        )
        .where(
            AssessmentCandidate.student_id == current_user.id,
            Assessment.school_id == school_id,
        )
        .order_by(
            AssessmentCandidate.allocated_at.desc(),
            AssessmentCandidate.id.desc(),
        )
        .options(
            raiseload("*"),
            load_only(
                AssessmentCandidate.id,
                AssessmentCandidate.assessment_id,
                AssessmentCandidate.student_id,
                AssessmentCandidate.status,
                AssessmentCandidate.allocated_at,
                AssessmentCandidate.started_at,
                AssessmentCandidate.submitted_at,
            ),
            load_only(
                Assessment.id,
                Assessment.school_id,
                Assessment.title,
                Assessment.description,
                Assessment.assessment_type,
                Assessment.academic_year,
                Assessment.term,
                Assessment.status,
                Assessment.scheduled_at,
                Assessment.closes_at,
            ),
        )
    )

    result = await db.execute(
        statement,
    )

    return [
        (
            candidate,
            assessment,
        )
        for candidate, assessment in result.all()
    ]


# ---------------------------------------------------------------------------
# Browser script queries
# ---------------------------------------------------------------------------


async def _get_latest_browser_script(
    db: AsyncSession,
    *,
    candidate_id: int,
    for_update: bool = False,
) -> AssessmentScript | None:
    """
    Return the highest-version browser script for one candidate.

    Storage metadata and relationships are deliberately not loaded.
    """

    statement = (
        select(
            AssessmentScript,
        )
        .where(
            AssessmentScript.candidate_id == candidate_id,
            AssessmentScript.source_type == "browser",
        )
        .order_by(
            AssessmentScript.version.desc(),
            AssessmentScript.id.desc(),
        )
        .limit(
            1,
        )
        .options(
            raiseload("*"),
            load_only(
                AssessmentScript.id,
                AssessmentScript.candidate_id,
                AssessmentScript.version,
                AssessmentScript.status,
                AssessmentScript.source_type,
                AssessmentScript.created_at,
                AssessmentScript.submitted_at,
            ),
        )
    )

    if for_update:
        statement = statement.with_for_update()

    result = await db.execute(
        statement,
    )

    return result.scalar_one_or_none()


async def _candidate_has_any_script(
    db: AsyncSession,
    *,
    candidate_id: int,
) -> bool:
    """
    Return whether any script history already exists for the candidate.
    """

    result = await db.execute(
        select(
            AssessmentScript.id,
        )
        .where(
            AssessmentScript.candidate_id == candidate_id,
        )
        .limit(
            1,
        )
    )

    return result.scalar_one_or_none() is not None


def _ensure_active_browser_script(
    script: AssessmentScript | None,
) -> AssessmentScript:
    """
    Require a browser script that is still editable by the learner.
    """

    if script is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Active browser assessment script was not found.",
        )

    if script.status != AssessmentScriptStatus.NOT_SUBMITTED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Assessment script can no longer be edited.",
        )

    return script


# ---------------------------------------------------------------------------
# Learner-safe question / response loading
# ---------------------------------------------------------------------------


async def _list_candidate_questions(
    db: AsyncSession,
    *,
    assessment: Assessment,
) -> list[AssessmentQuestion]:
    """
    Load the assessment through the dedicated candidate-safe repository path.
    """

    return await AssessmentQuestionRepository(
        db,
    ).list_candidate_visible_questions_by_assessment_and_school(
        assessment_id=assessment.id,
        school_id=assessment.school_id,
    )


async def _get_candidate_question(
    db: AsyncSession,
    *,
    assessment: Assessment,
    question_id: int,
) -> AssessmentQuestion:
    """
    Return one candidate-safe question or hide it behind a 404 boundary.
    """

    question = await AssessmentQuestionRepository(
        db,
    ).get_candidate_visible_question_by_assessment_and_school(
        question_id=question_id,
        assessment_id=assessment.id,
        school_id=assessment.school_id,
    )

    if question is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assessment question not found.",
        )

    if not question.is_markable:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This assessment item does not accept a student response.",
        )

    return question


async def _list_script_responses_safe(
    db: AsyncSession,
    *,
    script_id: int,
    for_update: bool = False,
) -> list[AssessmentResponse]:
    """
    Return script responses without loading marking relationships.
    """

    statement = (
        select(
            AssessmentResponse,
        )
        .where(
            AssessmentResponse.script_id == script_id,
        )
        .order_by(
            AssessmentResponse.question_id.asc(),
            AssessmentResponse.id.asc(),
        )
        .options(
            raiseload("*"),
            load_only(
                AssessmentResponse.id,
                AssessmentResponse.script_id,
                AssessmentResponse.question_id,
                AssessmentResponse.question_snapshot_id,
                AssessmentResponse.status,
                AssessmentResponse.response_text,
                AssessmentResponse.response_data,
                AssessmentResponse.created_at,
                AssessmentResponse.updated_at,
                AssessmentResponse.submitted_at,
            ),
        )
    )

    if for_update:
        statement = statement.with_for_update()

    result = await db.execute(
        statement,
    )

    return list(
        result.scalars().all(),
    )


async def _get_script_response_safe(
    db: AsyncSession,
    *,
    script_id: int,
    question_id: int,
    for_update: bool = False,
) -> AssessmentResponse | None:
    """
    Return one response without hydrating marking or question relationships.
    """

    statement = (
        select(
            AssessmentResponse,
        )
        .where(
            AssessmentResponse.script_id == script_id,
            AssessmentResponse.question_id == question_id,
        )
        .options(
            raiseload("*"),
            load_only(
                AssessmentResponse.id,
                AssessmentResponse.script_id,
                AssessmentResponse.question_id,
                AssessmentResponse.question_snapshot_id,
                AssessmentResponse.status,
                AssessmentResponse.response_text,
                AssessmentResponse.response_data,
                AssessmentResponse.created_at,
                AssessmentResponse.updated_at,
                AssessmentResponse.submitted_at,
            ),
        )
    )

    if for_update:
        statement = statement.with_for_update()

    result = await db.execute(
        statement,
    )

    return result.scalar_one_or_none()


def _sha256_file(
    path: Path,
) -> str:
    """
    Return the SHA-256 digest for one immutable attempt asset.

    Files are read incrementally so large diagrams/resources do not need to be
    loaded into memory in one operation.
    """

    digest = hashlib.sha256()

    with path.open("rb") as file_handle:
        for chunk in iter(
            lambda: file_handle.read(1024 * 1024),
            b"",
        ):
            digest.update(
                chunk,
            )

    return digest.hexdigest()


async def _ensure_question_snapshots(
    db: AsyncSession,
    *,
    script: AssessmentScript,
    assessment: Assessment,
    questions: list[AssessmentQuestion],
) -> None:
    """
    Ensure one immutable learner-facing question snapshot exists per script.

    Snapshot creation is idempotent and occurs inside the caller's transaction.

    Candidate-visible question, section and option content comes from the
    restrictive learner-safe question query. Server-only asset storage metadata
    is loaded separately so internal storage paths are never introduced into
    candidate-facing ORM loading.

    Existing snapshot rows are never updated.
    """

    existing_result = await db.execute(
        select(
            AssessmentQuestionSnapshot.question_id,
        ).where(
            AssessmentQuestionSnapshot.script_id == script.id,
        )
    )

    existing_question_ids = set(
        existing_result.scalars().all(),
    )

    # Snapshot creation is all-or-nothing for a script/version.
    #
    # Once any snapshot exists, the attempt question set is frozen. Later
    # canonical additions must never be appended to an already-started
    # attempt. First-time legacy backfill remains supported when a script has
    # no snapshots yet.
    if existing_question_ids:
        return

    missing_questions = [
        question
        for question in questions
        if question.id not in existing_question_ids
    ]

    if not missing_questions:
        return

    internal_assets = await AssessmentQuestionRepository(
        db,
    ).list_candidate_visible_assets_by_assessment_and_school(
        assessment_id=assessment.id,
        school_id=assessment.school_id,
    )

    assets_by_question_id: dict[int, list[object]] = {}

    for asset in internal_assets:
        assets_by_question_id.setdefault(
            asset.question_id,
            [],
        ).append(
            asset,
        )

    expected_root = (
        Path(
            assessment_document_service.ASSESSMENT_UPLOAD_ROOT,
        )
        / str(assessment.school_id)
        / str(assessment.id)
    ).resolve()

    snapshots: list[AssessmentQuestionSnapshot] = []

    for question in missing_questions:
        section_snapshot = None

        if question.section is not None:
            section_snapshot = {
                "id": question.section.id,
                "title": question.section.title,
                "description": question.section.description,
                "order": question.section.order,
                "is_optional": question.section.is_optional,
            }

        options_snapshot = [
            {
                "id": option.id,
                "text": option.text,
                "order": option.order,
            }
            for option in sorted(
                question.options,
                key=lambda option: (
                    option.order,
                    option.id,
                ),
            )
        ]

        assets_snapshot: list[dict[str, object]] = []

        for asset in assets_by_question_id.get(
            question.id,
            [],
        ):
            storage_path = asset.storage_path

            if not isinstance(storage_path, str) or not storage_path.strip():
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=(
                        "Assessment question asset cannot be snapshotted "
                        "because its storage path is unavailable."
                    ),
                )

            asset_path = Path(
                storage_path,
            ).resolve()

            asset_is_authorised = True

            try:
                asset_path.relative_to(
                    expected_root,
                )
            except ValueError:
                asset_is_authorised = False

            asset_is_available = (
                asset_is_authorised
                and asset_path.exists()
                and asset_path.is_file()
            )

            asset_sha256 = (
                _sha256_file(asset_path)
                if asset_is_available
                else None
            )

            actual_file_size = (
                asset_path.stat().st_size
                if asset_is_available
                else asset.file_size_bytes
            )

            assets_snapshot.append(
                {
                    "id": asset.id,
                    "asset_type": asset.asset_type,
                    "storage_path": storage_path,
                    "sha256": asset_sha256,
                    "original_filename": asset.original_filename,
                    "mime_type": asset.mime_type,
                    "file_size_bytes": actual_file_size,
                    "alt_text": asset.alt_text,
                    "caption": asset.caption,
                    "order": asset.order,
                }
            )

        snapshots.append(
            AssessmentQuestionSnapshot(
                script_id=script.id,
                question_id=question.id,
                parent_question_id_snapshot=question.parent_question_id,
                question_number=question.question_number,
                title=question.title,
                prompt=question.prompt,
                question_type=question.question_type,
                interaction_config_snapshot=question.interaction_config,
                maximum_mark=question.maximum_mark,
                order=question.order,
                is_markable=question.is_markable,
                section_snapshot=section_snapshot,
                options_snapshot=options_snapshot,
                assets_snapshot=assets_snapshot,
            )
        )

    if snapshots:
        db.add_all(
            snapshots,
        )
        await db.flush()


async def _ensure_response_rows(
    db: AsyncSession,
    *,
    script: AssessmentScript,
    questions: list[AssessmentQuestion],
) -> None:
    """
    Ensure every markable attempt question has one response row.

    For scripts with immutable question snapshots, snapshots are authoritative.
    Existing legacy response rows are linked to their matching snapshots when
    possible, and new response rows are created with both canonical provenance
    and immutable snapshot identity.

    Scripts without snapshots retain the legacy canonical-question behaviour.
    """

    snapshots = await _list_question_snapshots_safe(
        db,
        script_id=script.id,
    )

    if snapshots:
        existing_result = await db.execute(
            select(
                AssessmentResponse,
            )
            .where(
                AssessmentResponse.script_id == script.id,
            )
            .options(
                raiseload("*"),
                load_only(
                    AssessmentResponse.id,
                    AssessmentResponse.script_id,
                    AssessmentResponse.question_id,
                    AssessmentResponse.question_snapshot_id,
                ),
            )
        )

        existing_responses = list(
            existing_result.scalars().all(),
        )

        existing_by_question_id = {
            response.question_id: response
            for response in existing_responses
        }

        markable_snapshots = [
            snapshot
            for snapshot in snapshots
            if snapshot.is_markable
        ]

        markable_question_ids = {
            snapshot.question_id
            for snapshot in markable_snapshots
        }

        unexpected_response_question_ids = {
            response.question_id
            for response in existing_responses
            if response.question_id not in markable_question_ids
        }

        if unexpected_response_question_ids:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "Assessment response set is inconsistent with the "
                    "immutable attempt question set."
                ),
            )

        missing_responses: list[AssessmentResponse] = []

        for snapshot in markable_snapshots:
            response = existing_by_question_id.get(
                snapshot.question_id,
            )

            if response is None:
                missing_responses.append(
                    AssessmentResponse(
                        script_id=script.id,
                        question_id=snapshot.question_id,
                        question_snapshot_id=snapshot.id,
                        status=AssessmentResponseStatus.NOT_STARTED,
                        response_text=None,
                        response_data=None,
                        source_reference=None,
                    )
                )
                continue

            if response.question_snapshot_id is None:
                response.question_snapshot_id = snapshot.id
                db.add(
                    response,
                )
                continue

            if response.question_snapshot_id != snapshot.id:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=(
                        "Assessment response is linked to an inconsistent "
                        "question snapshot."
                    ),
                )

        if missing_responses:
            db.add_all(
                missing_responses,
            )

        if missing_responses or any(
            response.question_snapshot_id is not None
            for response in existing_responses
        ):
            await db.flush()

        return

    # Legacy compatibility for scripts that genuinely have no snapshots.
    existing_result = await db.execute(
        select(
            AssessmentResponse.question_id,
        ).where(
            AssessmentResponse.script_id == script.id,
        )
    )

    existing_question_ids = set(
        existing_result.scalars().all(),
    )

    missing_responses = [
        AssessmentResponse(
            script_id=script.id,
            question_id=question.id,
            question_snapshot_id=None,
            status=AssessmentResponseStatus.NOT_STARTED,
            response_text=None,
            response_data=None,
            source_reference=None,
        )
        for question in questions
        if question.is_markable and question.id not in existing_question_ids
    ]

    if missing_responses:
        db.add_all(
            missing_responses,
        )
        await db.flush()


# ---------------------------------------------------------------------------
# Diagram-response integrity
# ---------------------------------------------------------------------------


def _parse_json_object(
    value: str,
) -> dict:
    """
    Decode stored response data and require a JSON object.
    """

    try:
        decoded = json.loads(
            value,
        )
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Structured response data must contain valid JSON.",
        ) from exc

    if not isinstance(
        decoded,
        dict,
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Structured response data must be a JSON object.",
        )

    return decoded


async def _get_question_snapshot_safe(
    db: AsyncSession,
    *,
    script_id: int,
    question_id: int,
) -> AssessmentQuestionSnapshot | None:
    """
    Return one immutable question snapshot for one script/question pair.

    Relationships remain unavailable because response validation requires only
    fields stored directly on the snapshot row.
    """

    statement = (
        select(
            AssessmentQuestionSnapshot,
        )
        .where(
            AssessmentQuestionSnapshot.script_id == script_id,
            AssessmentQuestionSnapshot.question_id == question_id,
        )
        .options(
            raiseload("*"),
            load_only(
                AssessmentQuestionSnapshot.id,
                AssessmentQuestionSnapshot.script_id,
                AssessmentQuestionSnapshot.question_id,
                AssessmentQuestionSnapshot.question_type,
                AssessmentQuestionSnapshot.interaction_config_snapshot,
                AssessmentQuestionSnapshot.is_markable,
                AssessmentQuestionSnapshot.assets_snapshot,
            ),
        )
    )

    result = await db.execute(
        statement,
    )

    return result.scalar_one_or_none()


async def _script_has_question_snapshots(
    db: AsyncSession,
    *,
    script_id: int,
) -> bool:
    """
    Return True when immutable question snapshots exist for this script.
    """

    result = await db.execute(
        select(
            AssessmentQuestionSnapshot.id,
        )
        .where(
            AssessmentQuestionSnapshot.script_id == script_id,
        )
        .limit(1)
    )

    return result.scalar_one_or_none() is not None


def _validate_response_for_question(
    *,
    question: AssessmentQuestion | AssessmentQuestionSnapshot,
    response_text: str | None,
    response_data: str | None,
) -> tuple[str | None, str | None]:
    """
    Validate learner response content against immutable attempt state.

    New browser attempts use ``AssessmentQuestionSnapshot`` as the authoritative
    validation source. Canonical ``AssessmentQuestion`` support remains only for
    legacy scripts created before snapshot support was introduced.

    Diagram annotations receive additional integrity checks:

    - pure diagram responses may not carry response_text;
    - response_data must be the versioned diagram-annotation object;
    - the referenced asset must belong to this exact candidate-visible question;
    - configured symbol palettes remain authoritative for permitted annotations.
    """

    clean_text = _clean_optional_text(
        response_text,
    )
    clean_data = _clean_optional_text(
        response_data,
    )

    if isinstance(
        question,
        AssessmentQuestionSnapshot,
    ):
        question_type_value = question.question_type
        interaction_config = question.interaction_config_snapshot

        assets_snapshot = (
            question.assets_snapshot
            if isinstance(question.assets_snapshot, list)
            else []
        )

        visible_asset_ids = {
            asset_id
            for item in assets_snapshot
            if isinstance(item, dict)
            and isinstance((asset_id := item.get("id")), int)
            and not isinstance(asset_id, bool)
        }

    else:
        question_type_value = question.question_type
        interaction_config = question.interaction_config
        visible_asset_ids = {
            asset.id
            for asset in question.assets
        }

    question_type = AssessmentQuestionType(
        question_type_value,
    )

    if question_type == AssessmentQuestionType.DIAGRAM_ANNOTATION:
        if clean_text is not None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    "Diagram-annotation responses must not contain " "response_text."
                ),
            )

        if clean_data is None:
            return None, None

        decoded = _parse_json_object(
            clean_data,
        )

        try:
            payload = DiagramAnnotationResponseData.model_validate(
                decoded,
            )
        except ValidationError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Invalid diagram-annotation response data.",
            ) from exc

        if payload.asset_id not in visible_asset_ids:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    "Diagram annotation references an asset that does not "
                    "belong to this candidate-visible question."
                ),
            )

        if interaction_config is not None:
            if not isinstance(interaction_config, dict):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=(
                        "Diagram interaction configuration is invalid for "
                        "this assessment question."
                    ),
                )

            tools = interaction_config.get("tools")

            if not isinstance(tools, list):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=(
                        "Diagram interaction configuration is invalid for "
                        "this assessment question."
                    ),
                )

            allowed_symbols = {
                symbol
                for tool in tools
                if isinstance(tool, dict)
                and tool.get("tool_type") == "symbol"
                and isinstance(tool.get("symbol"), str)
                and (symbol := tool["symbol"].strip())
            }

            if not allowed_symbols:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=(
                        "Diagram interaction configuration does not define "
                        "any permitted symbols."
                    ),
                )

            if any(
                annotation.symbol not in allowed_symbols
                for annotation in payload.annotations
            ):
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=(
                        "Diagram annotation contains a symbol that is not "
                        "permitted for this question."
                    ),
                )

        return (
            None,
            json.dumps(
                payload.model_dump(
                    mode="json",
                ),
                separators=(
                    ",",
                    ":",
                ),
                ensure_ascii=False,
            ),
        )

    if clean_data is not None:
        try:
            decoded = json.loads(
                clean_data,
            )
        except json.JSONDecodeError:
            decoded = None

        if (
            isinstance(
                decoded,
                dict,
            )
            and decoded.get(
                "type",
            )
            == "diagram_annotation"
        ):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    "Diagram-annotation response data cannot be saved against "
                    "this question type."
                ),
            )

    return clean_text, clean_data


# ---------------------------------------------------------------------------
# Candidate-safe output builders
# ---------------------------------------------------------------------------


def _build_asset_out(
    *,
    assessment_id: int,
    question: AssessmentQuestion,
    asset,
) -> AssessmentTakingAssetOut:
    """
    Build candidate-safe asset metadata plus an authorised delivery URL.
    """

    return AssessmentTakingAssetOut(
        id=asset.id,
        asset_type=asset.asset_type,
        alt_text=asset.alt_text,
        caption=asset.caption,
        order=asset.order,
        content_url=(
            f"/api/v1/student-assessments/{assessment_id}"
            f"/questions/{question.id}/assets/{asset.id}/content"
        ),
    )


def _build_question_out(
    *,
    assessment_id: int,
    question: AssessmentQuestion,
) -> AssessmentTakingQuestionOut:
    """
    Convert one restricted ORM question into the learner-facing schema.

    ``interaction_config`` is included because the candidate-safe repository
    explicitly loads only learner-permitted configuration. Correct-answer,
    mark-scheme and server-side provenance data remain excluded.
    """

    return AssessmentTakingQuestionOut(
        id=question.id,
        assessment_id=question.assessment_id,
        section_id=question.section_id,
        parent_question_id=question.parent_question_id,
        question_number=question.question_number,
        title=question.title,
        prompt=question.prompt,
        question_type=question.question_type,
        interaction_config=question.interaction_config,
        maximum_mark=question.maximum_mark,
        order=question.order,
        is_markable=question.is_markable,
        options=[
            AssessmentTakingOptionOut(
                id=option.id,
                text=option.text,
                order=option.order,
            )
            for option in sorted(
                question.options,
                key=lambda item: (
                    item.order,
                    item.id,
                ),
            )
        ],
        assets=[
            _build_asset_out(
                assessment_id=assessment_id,
                question=question,
                asset=asset,
            )
            for asset in sorted(
                question.assets,
                key=lambda item: (
                    item.order,
                    item.id,
                ),
            )
        ],
    )


def _build_sections_out(
    questions: list[AssessmentQuestion],
) -> list[AssessmentTakingSectionOut]:
    """
    Build unique learner-visible section metadata from loaded questions.
    """

    by_id: dict[int, AssessmentTakingSectionOut] = {}

    for question in questions:
        section = question.section

        if section is None:
            continue

        if section.id in by_id:
            continue

        by_id[section.id] = AssessmentTakingSectionOut(
            id=section.id,
            assessment_id=section.assessment_id,
            title=section.title,
            description=section.description,
            order=section.order,
            is_optional=section.is_optional,
        )

    return sorted(
        by_id.values(),
        key=lambda item: (
            item.order,
            item.id,
        ),
    )


def _build_response_out(
    response: AssessmentResponse,
) -> AssessmentTakingResponseOut:
    """
    Build a learner-safe saved-response representation.
    """

    return AssessmentTakingResponseOut(
        id=response.id,
        question_id=response.question_id,
        status=response.status,
        response_text=response.response_text,
        response_data=response.response_data,
        created_at=response.created_at,
        updated_at=response.updated_at,
        submitted_at=response.submitted_at,
    )


def _build_script_out(
    script: AssessmentScript,
) -> AssessmentTakingScriptOut:
    """
    Build the minimal learner-safe script representation.
    """

    return AssessmentTakingScriptOut(
        id=script.id,
        version=script.version,
        status=script.status,
        created_at=script.created_at,
        submitted_at=script.submitted_at,
    )


async def _list_question_snapshots_safe(
    db: AsyncSession,
    *,
    script_id: int,
) -> list[AssessmentQuestionSnapshot]:
    """
    Return immutable learner-facing question snapshots for one script.

    Snapshot relationships are deliberately unavailable. All learner-visible
    section, option and asset metadata required for rendering is already frozen
    directly on the snapshot row.
    """

    statement = (
        select(
            AssessmentQuestionSnapshot,
        )
        .where(
            AssessmentQuestionSnapshot.script_id == script_id,
        )
        .order_by(
            AssessmentQuestionSnapshot.order.asc(),
            AssessmentQuestionSnapshot.id.asc(),
        )
        .options(
            raiseload("*"),
            load_only(
                AssessmentQuestionSnapshot.id,
                AssessmentQuestionSnapshot.script_id,
                AssessmentQuestionSnapshot.question_id,
                AssessmentQuestionSnapshot.parent_question_id_snapshot,
                AssessmentQuestionSnapshot.question_number,
                AssessmentQuestionSnapshot.title,
                AssessmentQuestionSnapshot.prompt,
                AssessmentQuestionSnapshot.question_type,
                AssessmentQuestionSnapshot.interaction_config_snapshot,
                AssessmentQuestionSnapshot.maximum_mark,
                AssessmentQuestionSnapshot.order,
                AssessmentQuestionSnapshot.is_markable,
                AssessmentQuestionSnapshot.section_snapshot,
                AssessmentQuestionSnapshot.options_snapshot,
                AssessmentQuestionSnapshot.assets_snapshot,
                AssessmentQuestionSnapshot.created_at,
            ),
        )
    )

    result = await db.execute(
        statement,
    )

    return list(
        result.scalars().all(),
    )


def _build_snapshot_asset_out(
    *,
    assessment_id: int,
    question_id: int,
    asset_snapshot: dict[str, object],
) -> AssessmentTakingAssetOut:
    """
    Build learner-safe asset metadata from immutable snapshot data.

    Internal storage paths and checksums remain server-only and are never
    included in the candidate response.
    """

    asset_id = asset_snapshot.get("id")
    asset_type = asset_snapshot.get("asset_type")
    order = asset_snapshot.get("order")

    if not isinstance(asset_id, int) or isinstance(asset_id, bool):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Assessment question snapshot contains an invalid asset id.",
        )

    if not isinstance(asset_type, str) or not asset_type.strip():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Assessment question snapshot contains an invalid asset type.",
        )

    if not isinstance(order, int) or isinstance(order, bool):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Assessment question snapshot contains an invalid asset order.",
        )

    alt_text = asset_snapshot.get("alt_text")
    caption = asset_snapshot.get("caption")

    return AssessmentTakingAssetOut(
        id=asset_id,
        asset_type=asset_type,
        alt_text=alt_text if isinstance(alt_text, str) else None,
        caption=caption if isinstance(caption, str) else None,
        order=order,
        content_url=(
            f"/api/v1/student-assessments/{assessment_id}"
            f"/questions/{question_id}/assets/{asset_id}/content"
        ),
    )


def _build_snapshot_question_out(
    *,
    assessment_id: int,
    snapshot: AssessmentQuestionSnapshot,
) -> AssessmentTakingQuestionOut:
    """
    Convert one immutable question snapshot into the existing learner schema.
    """

    section_id = None

    if isinstance(snapshot.section_snapshot, dict):
        raw_section_id = snapshot.section_snapshot.get("id")

        if isinstance(raw_section_id, int) and not isinstance(
            raw_section_id,
            bool,
        ):
            section_id = raw_section_id

    options_snapshot = (
        snapshot.options_snapshot
        if isinstance(snapshot.options_snapshot, list)
        else []
    )

    assets_snapshot = (
        snapshot.assets_snapshot
        if isinstance(snapshot.assets_snapshot, list)
        else []
    )

    safe_options: list[dict[str, object]] = [
        item
        for item in options_snapshot
        if isinstance(item, dict)
    ]

    safe_assets: list[dict[str, object]] = [
        item
        for item in assets_snapshot
        if isinstance(item, dict)
    ]

    return AssessmentTakingQuestionOut(
        id=snapshot.question_id,
        assessment_id=assessment_id,
        section_id=section_id,
        parent_question_id=snapshot.parent_question_id_snapshot,
        question_number=snapshot.question_number,
        title=snapshot.title,
        prompt=snapshot.prompt,
        question_type=snapshot.question_type,
        interaction_config=snapshot.interaction_config_snapshot,
        maximum_mark=snapshot.maximum_mark,
        order=snapshot.order,
        is_markable=snapshot.is_markable,
        options=[
            AssessmentTakingOptionOut(
                id=int(option["id"]),
                text=str(option["text"]),
                order=int(option["order"]),
            )
            for option in sorted(
                safe_options,
                key=lambda item: (
                    int(item.get("order", 0)),
                    int(item.get("id", 0)),
                ),
            )
        ],
        assets=[
            _build_snapshot_asset_out(
                assessment_id=assessment_id,
                question_id=snapshot.question_id,
                asset_snapshot=asset_snapshot,
            )
            for asset_snapshot in sorted(
                safe_assets,
                key=lambda item: (
                    int(item.get("order", 0)),
                    int(item.get("id", 0)),
                ),
            )
        ],
    )


def _build_snapshot_sections_out(
    *,
    assessment_id: int,
    snapshots: list[AssessmentQuestionSnapshot],
) -> list[AssessmentTakingSectionOut]:
    """
    Reconstruct learner-visible sections entirely from immutable snapshots.
    """

    by_id: dict[int, AssessmentTakingSectionOut] = {}

    for snapshot in snapshots:
        section = snapshot.section_snapshot

        if not isinstance(section, dict):
            continue

        section_id = section.get("id")
        title = section.get("title")
        order = section.get("order")
        is_optional = section.get("is_optional")

        if (
            not isinstance(section_id, int)
            or isinstance(section_id, bool)
            or not isinstance(title, str)
            or not isinstance(order, int)
            or isinstance(order, bool)
            or not isinstance(is_optional, bool)
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Assessment question snapshot contains invalid section metadata.",
            )

        if section_id in by_id:
            continue

        description = section.get("description")

        by_id[section_id] = AssessmentTakingSectionOut(
            id=section_id,
            assessment_id=assessment_id,
            title=title,
            description=(
                description
                if isinstance(description, str)
                else None
            ),
            order=order,
            is_optional=is_optional,
        )

    return sorted(
        by_id.values(),
        key=lambda section: (
            section.order,
            section.id,
        ),
    )


async def _build_attempt(
    db: AsyncSession,
    *,
    candidate: AssessmentCandidate,
    assessment: Assessment,
    script: AssessmentScript,
) -> StudentAssessmentAttemptOut:
    """
    Assemble a complete candidate-safe attempt.

    Immutable question snapshots are authoritative whenever they exist for the
    script. Canonical-question rendering remains only as a compatibility
    fallback for browser scripts created before snapshot support was introduced.
    """

    snapshots = await _list_question_snapshots_safe(
        db,
        script_id=script.id,
    )

    responses = await _list_script_responses_safe(
        db,
        script_id=script.id,
    )

    if snapshots:
        sections = _build_snapshot_sections_out(
            assessment_id=assessment.id,
            snapshots=snapshots,
        )

        question_outputs = [
            _build_snapshot_question_out(
                assessment_id=assessment.id,
                snapshot=snapshot,
            )
            for snapshot in snapshots
        ]

    else:
        questions = await _list_candidate_questions(
            db,
            assessment=assessment,
        )

        sections = _build_sections_out(
            questions,
        )

        question_outputs = [
            _build_question_out(
                assessment_id=assessment.id,
                question=question,
            )
            for question in questions
        ]

    return StudentAssessmentAttemptOut(
        assessment_id=assessment.id,
        title=assessment.title,
        description=assessment.description,
        assessment_type=assessment.assessment_type,
        academic_year=assessment.academic_year,
        term=assessment.term,
        assessment_status=assessment.status,
        candidate_status=candidate.status,
        scheduled_at=assessment.scheduled_at,
        closes_at=assessment.closes_at,
        started_at=candidate.started_at,
        submitted_at=candidate.submitted_at,
        script=_build_script_out(
            script,
        ),
        sections=sections,
        questions=question_outputs,
        responses=[
            _build_response_out(
                response,
            )
            for response in responses
        ],
    )


# ---------------------------------------------------------------------------
# Secure candidate asset delivery
# ---------------------------------------------------------------------------


async def resolve_student_assessment_asset_path(
    db: AsyncSession,
    current_user: User,
    assessment_id: int,
    question_id: int,
    asset_id: int,
) -> tuple[Path, str, str | None]:
    """
    Resolve one candidate-visible canonical question asset for secure delivery.

    Access is permitted only when:

    - the logged-in user is an active student;
    - the candidate allocation belongs to that exact user;
    - the assessment belongs to the student's school;
    - the assessment is currently published and inside its time window;
    - the candidate has an active STARTED browser attempt;
    - the asset belongs to the exact question and assessment;
    - the asset is marked candidate-visible;
    - the stored path remains inside this assessment's upload directory;
    - the resolved path exists and is a regular file.

    The filesystem path is returned only to the server-side endpoint. It is
    never exposed in learner JSON.
    """

    candidate, assessment = await _get_owned_candidate_context(
        db,
        current_user=current_user,
        assessment_id=assessment_id,
    )

    _ensure_assessment_open_now(
        assessment,
        now=_utc_now(),
    )

    if candidate.status != AssessmentCandidateStatus.STARTED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Assessment asset is available only during an active attempt.",
        )

    script = _ensure_active_browser_script(
        await _get_latest_browser_script(
            db,
            candidate_id=candidate.id,
        )
    )

    snapshots = await _list_question_snapshots_safe(
        db,
        script_id=script.id,
    )

    storage_path: str
    mime_type_value: object
    original_filename_value: object
    expected_sha256: str | None = None

    if snapshots:
        question_snapshot = next(
            (
                snapshot
                for snapshot in snapshots
                if snapshot.question_id == question_id
            ),
            None,
        )

        if question_snapshot is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Assessment question asset not found.",
            )

        assets_snapshot = (
            question_snapshot.assets_snapshot
            if isinstance(question_snapshot.assets_snapshot, list)
            else []
        )

        asset_snapshot = next(
            (
                item
                for item in assets_snapshot
                if (
                    isinstance(item, dict)
                    and item.get("id") == asset_id
                )
            ),
            None,
        )

        if asset_snapshot is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Assessment question asset not found.",
            )

        snapshot_storage_path = asset_snapshot.get(
            "storage_path",
        )

        if (
            not isinstance(snapshot_storage_path, str)
            or not snapshot_storage_path.strip()
        ):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Assessment question asset file is not available.",
            )

        storage_path = snapshot_storage_path
        mime_type_value = asset_snapshot.get(
            "mime_type",
        )
        original_filename_value = asset_snapshot.get(
            "original_filename",
        )

        raw_sha256 = asset_snapshot.get(
            "sha256",
        )

        if raw_sha256 is not None:
            if (
                not isinstance(raw_sha256, str)
                or len(raw_sha256) != 64
            ):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=(
                        "Assessment question snapshot contains an invalid "
                        "asset checksum."
                    ),
                )

            expected_sha256 = raw_sha256.lower()

    else:
        # Compatibility path for browser scripts created before immutable
        # question snapshots were introduced.
        asset = await AssessmentQuestionRepository(
            db,
        ).get_candidate_visible_asset_by_question_assessment_and_school(
            asset_id=asset_id,
            question_id=question_id,
            assessment_id=assessment.id,
            school_id=assessment.school_id,
        )

        if asset is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Assessment question asset not found.",
            )

        if (
            not isinstance(asset.storage_path, str)
            or not asset.storage_path.strip()
        ):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Assessment question asset file is not available.",
            )

        storage_path = asset.storage_path
        mime_type_value = asset.mime_type
        original_filename_value = asset.original_filename

    expected_root = (
        Path(
            assessment_document_service.ASSESSMENT_UPLOAD_ROOT,
        )
        / str(assessment.school_id)
        / str(assessment.id)
    ).resolve()

    asset_path = Path(
        storage_path,
    ).resolve()

    try:
        asset_path.relative_to(
            expected_root,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "The stored assessment question asset path falls outside the "
                "authorised assessment directory."
            ),
        ) from exc

    if not asset_path.exists() or not asset_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assessment question asset file was not found.",
        )

    if expected_sha256 is not None:
        actual_sha256 = _sha256_file(
            asset_path,
        )

        if actual_sha256.lower() != expected_sha256:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "Assessment question asset no longer matches the "
                    "immutable attempt snapshot."
                ),
            )

    mime_type = (
        mime_type_value.strip()
        if (
            isinstance(mime_type_value, str)
            and mime_type_value.strip()
        )
        else "application/octet-stream"
    )

    download_name = (
        original_filename_value.strip()
        if (
            isinstance(original_filename_value, str)
            and original_filename_value.strip()
        )
        else None
    )

    return (
        asset_path,
        mime_type,
        download_name,
    )


# ---------------------------------------------------------------------------
# Public student-taking service operations
# ---------------------------------------------------------------------------


async def list_student_assessments(
    db: AsyncSession,
    current_user: User,
) -> list[StudentAssessmentSummaryOut]:
    """
    Return assessment allocations owned by the logged-in student.

    Listing never exposes questions, scripts, candidate numbers, access
    arrangements, marks, marking state, or another student's data.
    """

    now = _utc_now()

    contexts = await _list_owned_candidate_contexts(
        db,
        current_user=current_user,
    )

    output: list[StudentAssessmentSummaryOut] = []

    for candidate, assessment in contexts:
        assessment_open = _is_assessment_open_now(
            assessment,
            now=now,
        )

        output.append(
            StudentAssessmentSummaryOut(
                assessment_id=assessment.id,
                title=assessment.title,
                description=assessment.description,
                assessment_type=assessment.assessment_type,
                academic_year=assessment.academic_year,
                term=assessment.term,
                assessment_status=assessment.status,
                candidate_status=candidate.status,
                scheduled_at=assessment.scheduled_at,
                closes_at=assessment.closes_at,
                started_at=candidate.started_at,
                submitted_at=candidate.submitted_at,
                can_start=(
                    assessment_open
                    and candidate.status == AssessmentCandidateStatus.ALLOCATED
                ),
                can_resume=(
                    assessment_open
                    and candidate.status == AssessmentCandidateStatus.STARTED
                ),
                is_submitted=(candidate.status == AssessmentCandidateStatus.SUBMITTED),
            )
        )

    return output


async def get_student_assessment_attempt(
    db: AsyncSession,
    current_user: User,
    assessment_id: int,
) -> StudentAssessmentAttemptOut:
    """
    Return the logged-in student's currently active browser attempt.

    Questions are not exposed before the explicit start action and are not
    re-exposed after candidate submission.
    """

    candidate, assessment = await _get_owned_candidate_context(
        db,
        current_user=current_user,
        assessment_id=assessment_id,
    )

    _ensure_assessment_open_now(
        assessment,
        now=_utc_now(),
    )

    if candidate.status == AssessmentCandidateStatus.ALLOCATED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Assessment has not been started.",
        )

    if candidate.status == AssessmentCandidateStatus.SUBMITTED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Assessment has already been submitted.",
        )

    if candidate.status in {
        AssessmentCandidateStatus.WITHDRAWN,
        AssessmentCandidateStatus.ABSENT,
    }:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Assessment attempt is not available for this candidate.",
        )

    if candidate.status != AssessmentCandidateStatus.STARTED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Assessment attempt is not currently active.",
        )

    script = _ensure_active_browser_script(
        await _get_latest_browser_script(
            db,
            candidate_id=candidate.id,
        )
    )

    return await _build_attempt(
        db,
        candidate=candidate,
        assessment=assessment,
        script=script,
    )


async def start_student_assessment(
    db: AsyncSession,
    current_user: User,
    assessment_id: int,
) -> StudentAssessmentStartOut:
    """
    Start or idempotently resume the logged-in student's browser assessment.

    Start is atomic across:
        - candidate ALLOCATED -> STARTED;
        - browser-script creation/reuse;
        - initial NOT_STARTED response rows.

    Candidate ownership is derived exclusively from ``current_user.id``.
    """

    now = _utc_now()

    try:
        candidate, assessment = await _get_owned_candidate_context(
            db,
            current_user=current_user,
            assessment_id=assessment_id,
            for_update=True,
        )

        _ensure_assessment_open_now(
            assessment,
            now=now,
        )

        if candidate.status == AssessmentCandidateStatus.SUBMITTED:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Assessment has already been submitted.",
            )

        if candidate.status in {
            AssessmentCandidateStatus.WITHDRAWN,
            AssessmentCandidateStatus.ABSENT,
        }:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Assessment cannot be started for this candidate.",
            )

        if candidate.status not in {
            AssessmentCandidateStatus.ALLOCATED,
            AssessmentCandidateStatus.STARTED,
        }:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Assessment cannot be started in its current state.",
            )

        script = await _get_latest_browser_script(
            db,
            candidate_id=candidate.id,
            for_update=True,
        )

        resumed = candidate.status == AssessmentCandidateStatus.STARTED

        if resumed:
            script = _ensure_active_browser_script(
                script,
            )
        else:
            if script is not None:
                script = _ensure_active_browser_script(
                    script,
                )
            else:
                if await _candidate_has_any_script(
                    db,
                    candidate_id=candidate.id,
                ):
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=(
                            "Candidate already has non-browser script history; "
                            "student browser start is not permitted."
                        ),
                    )

                candidate_repository = AssessmentCandidateRepository(
                    db,
                )

                version = await candidate_repository.get_next_script_version(
                    candidate.id,
                )

                script = AssessmentScript(
                    candidate_id=candidate.id,
                    version=version,
                    status=AssessmentScriptStatus.NOT_SUBMITTED,
                    source_type="browser",
                    source_filename=None,
                    storage_key=None,
                    mime_type=None,
                    checksum=None,
                )

                db.add(
                    script,
                )
                await db.flush()

            candidate.status = AssessmentCandidateStatus.STARTED
            candidate.started_at = candidate.started_at or now

            db.add(
                candidate,
            )
            await db.flush()

        questions = await _list_candidate_questions(
            db,
            assessment=assessment,
        )

        await _ensure_question_snapshots(
            db,
            script=script,
            assessment=assessment,
            questions=questions,
        )

        await _ensure_response_rows(
            db,
            script=script,
            questions=questions,
        )

        await db.commit()

    except HTTPException:
        await db.rollback()
        raise

    except IntegrityError:
        await db.rollback()

        # A concurrent start may have completed the same idempotent operation.
        candidate, assessment = await _get_owned_candidate_context(
            db,
            current_user=current_user,
            assessment_id=assessment_id,
        )

        _ensure_assessment_open_now(
            assessment,
            now=_utc_now(),
        )

        if candidate.status != AssessmentCandidateStatus.STARTED:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "Assessment start conflicted with another request; "
                    "retry the operation."
                ),
            )

        script = _ensure_active_browser_script(
            await _get_latest_browser_script(
                db,
                candidate_id=candidate.id,
            )
        )

        attempt = await _build_attempt(
            db,
            candidate=candidate,
            assessment=assessment,
            script=script,
        )

        return StudentAssessmentStartOut(
            **attempt.model_dump(),
            message="Assessment resumed.",
        )

    except Exception:
        await db.rollback()
        raise

    candidate, assessment = await _get_owned_candidate_context(
        db,
        current_user=current_user,
        assessment_id=assessment_id,
    )

    script = _ensure_active_browser_script(
        await _get_latest_browser_script(
            db,
            candidate_id=candidate.id,
        )
    )

    attempt = await _build_attempt(
        db,
        candidate=candidate,
        assessment=assessment,
        script=script,
    )

    return StudentAssessmentStartOut(
        **attempt.model_dump(),
        message=("Assessment resumed." if resumed else "Assessment started."),
    )


async def save_student_assessment_response(
    db: AsyncSession,
    current_user: User,
    assessment_id: int,
    question_id: int,
    payload: AssessmentTakingResponseSave,
) -> AssessmentTakingResponseOut:
    """
    Idempotently create/update the student's response to one question.

    The route supplies assessment/question ids. Candidate and script ownership
    are resolved server-side. Writes are permitted only while the candidate is
    STARTED, the browser script is NOT_SUBMITTED, and the assessment is within
    its active window.
    """

    now = _utc_now()

    try:
        candidate, assessment = await _get_owned_candidate_context(
            db,
            current_user=current_user,
            assessment_id=assessment_id,
            for_update=True,
        )

        _ensure_assessment_open_now(
            assessment,
            now=now,
        )

        if candidate.status != AssessmentCandidateStatus.STARTED:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Assessment response can only be saved during an active attempt.",
            )

        script = _ensure_active_browser_script(
            await _get_latest_browser_script(
                db,
                candidate_id=candidate.id,
                for_update=True,
            )
        )

        question_snapshot = await _get_question_snapshot_safe(
            db,
            script_id=script.id,
            question_id=question_id,
        )

        if question_snapshot is not None:
            if not question_snapshot.is_markable:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="This assessment item does not accept a student response.",
                )

            validation_question: AssessmentQuestion | AssessmentQuestionSnapshot = (
                question_snapshot
            )
            response_question_id = question_snapshot.question_id

        else:
            if await _script_has_question_snapshots(
                db,
                script_id=script.id,
            ):
                # A snapshotted script must never fall through to newly added,
                # removed, or otherwise changed canonical question state.
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Assessment question not found.",
                )

            # Compatibility path for browser scripts created before immutable
            # question snapshots were introduced.
            canonical_question = await _get_candidate_question(
                db,
                assessment=assessment,
                question_id=question_id,
            )

            validation_question = canonical_question
            response_question_id = canonical_question.id

        response_text, response_data = _validate_response_for_question(
            question=validation_question,
            response_text=payload.response_text,
            response_data=payload.response_data,
        )

        response = await _get_script_response_safe(
            db,
            script_id=script.id,
            question_id=response_question_id,
            for_update=True,
        )

        if response is None:
            response = AssessmentResponse(
                script_id=script.id,
                question_id=response_question_id,
                question_snapshot_id=(
                    question_snapshot.id
                    if question_snapshot is not None
                    else None
                ),
                status=AssessmentResponseStatus.NOT_STARTED,
                response_text=None,
                response_data=None,
                source_reference=None,
            )
            db.add(
                response,
            )
            await db.flush()

        if response.status in {
            AssessmentResponseStatus.SUBMITTED,
            AssessmentResponseStatus.VOID,
        }:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Assessment response can no longer be edited.",
            )

        response.response_text = response_text
        response.response_data = response_data
        response.source_reference = None
        response.submitted_at = None

        if response_text is None and response_data is None:
            response.status = AssessmentResponseStatus.NOT_STARTED
        else:
            response.status = AssessmentResponseStatus.IN_PROGRESS

        db.add(
            response,
        )
        await db.flush()

        await db.refresh(
            response,
            attribute_names=[
                "id",
                "script_id",
                "question_id",
                "status",
                "response_text",
                "response_data",
                "created_at",
                "updated_at",
                "submitted_at",
            ],
        )

        output = _build_response_out(
            response,
        )

        await db.commit()

        return output

    except HTTPException:
        await db.rollback()
        raise

    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=("Assessment response changed concurrently; retry the autosave."),
        ) from exc

    except Exception:
        await db.rollback()
        raise


async def submit_student_assessment(
    db: AsyncSession,
    current_user: User,
    assessment_id: int,
) -> StudentAssessmentSubmitOut:
    """
    Atomically submit the logged-in student's browser assessment.

    Submission transitions:
        - every candidate response -> SUBMITTED;
        - browser script -> SUBMITTED;
        - candidate -> SUBMITTED;

    All transitions share the same submission timestamp and commit together.
    """

    now = _utc_now()

    try:
        candidate, assessment = await _get_owned_candidate_context(
            db,
            current_user=current_user,
            assessment_id=assessment_id,
            for_update=True,
        )

        _ensure_assessment_open_now(
            assessment,
            now=now,
        )

        if candidate.status == AssessmentCandidateStatus.SUBMITTED:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Assessment has already been submitted.",
            )

        if candidate.status != AssessmentCandidateStatus.STARTED:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Only an active assessment attempt can be submitted.",
            )

        script = _ensure_active_browser_script(
            await _get_latest_browser_script(
                db,
                candidate_id=candidate.id,
                for_update=True,
            )
        )

        snapshots = await _list_question_snapshots_safe(
            db,
            script_id=script.id,
        )

        if snapshots:
            questions: list[AssessmentQuestion] = []

            await _ensure_response_rows(
                db,
                script=script,
                questions=questions,
            )

            responses = await _list_script_responses_safe(
                db,
                script_id=script.id,
                for_update=True,
            )

            markable_snapshots = [
                snapshot
                for snapshot in snapshots
                if snapshot.is_markable
            ]

            markable_question_ids = {
                snapshot.question_id
                for snapshot in markable_snapshots
            }

            expected_snapshot_ids = {
                snapshot.id
                for snapshot in markable_snapshots
            }

            response_question_ids = {
                response.question_id
                for response in responses
            }

            response_snapshot_ids = {
                response.question_snapshot_id
                for response in responses
            }

            if (
                markable_question_ids != response_question_ids
                or expected_snapshot_ids != response_snapshot_ids
            ):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=(
                        "Assessment response set is inconsistent with the "
                        "immutable attempt question set."
                    ),
                )

        else:
            questions = await _list_candidate_questions(
                db,
                assessment=assessment,
            )

            await _ensure_response_rows(
                db,
                script=script,
                questions=questions,
            )

            responses = await _list_script_responses_safe(
                db,
                script_id=script.id,
                for_update=True,
            )

            markable_question_ids = {
                question.id
                for question in questions
                if question.is_markable
            }

            response_question_ids = {
                response.question_id
                for response in responses
            }

            if markable_question_ids != response_question_ids:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=(
                        "Assessment response set is inconsistent with the "
                        "published question set."
                    ),
                )

        for response in responses:
            if response.status == AssessmentResponseStatus.VOID:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=(
                        "Assessment contains a void response and requires "
                        "staff review before submission."
                    ),
                )

            response.status = AssessmentResponseStatus.SUBMITTED
            response.submitted_at = response.submitted_at or now

            db.add(
                response,
            )

        script.status = AssessmentScriptStatus.SUBMITTED
        script.submitted_at = script.submitted_at or now

        candidate.status = AssessmentCandidateStatus.SUBMITTED
        candidate.submitted_at = candidate.submitted_at or now

        db.add(
            script,
        )
        db.add(
            candidate,
        )

        await db.flush()
        await db.commit()

        return StudentAssessmentSubmitOut(
            assessment_id=assessment.id,
            candidate_status=AssessmentCandidateStatus.SUBMITTED,
            script_status=AssessmentScriptStatus.SUBMITTED,
            submitted_at=candidate.submitted_at or now,
            message="Assessment submitted.",
        )

    except HTTPException:
        await db.rollback()
        raise

    except Exception:
        await db.rollback()
        raise
