from __future__ import annotations

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


async def _ensure_response_rows(
    db: AsyncSession,
    *,
    script: AssessmentScript,
    questions: list[AssessmentQuestion],
) -> None:
    """
    Ensure every markable question has one response row.

    Rows are initialised as NOT_STARTED. The database unique constraint on
    ``(script_id, question_id)`` remains the final concurrency safeguard.
    """

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


def _validate_response_for_question(
    *,
    question: AssessmentQuestion,
    response_text: str | None,
    response_data: str | None,
) -> tuple[str | None, str | None]:
    """
    Validate learner response content against the canonical question type.

    Diagram annotations receive additional integrity checks:

    - pure diagram responses may not carry response_text;
    - response_data must be the versioned diagram-annotation object;
    - the referenced asset must belong to this exact question;
    - the asset must be candidate-visible, which is guaranteed by the
      candidate-safe question query.
    """

    clean_text = _clean_optional_text(
        response_text,
    )
    clean_data = _clean_optional_text(
        response_data,
    )

    question_type = AssessmentQuestionType(
        question.question_type,
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

        visible_asset_ids = {asset.id for asset in question.assets}

        if payload.asset_id not in visible_asset_ids:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    "Diagram annotation references an asset that does not "
                    "belong to this candidate-visible question."
                ),
            )

        interaction_config = question.interaction_config

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


async def _build_attempt(
    db: AsyncSession,
    *,
    candidate: AssessmentCandidate,
    assessment: Assessment,
    script: AssessmentScript,
) -> StudentAssessmentAttemptOut:
    """
    Assemble a complete candidate-safe attempt from restricted queries.
    """

    questions = await _list_candidate_questions(
        db,
        assessment=assessment,
    )

    responses = await _list_script_responses_safe(
        db,
        script_id=script.id,
    )

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
        sections=_build_sections_out(
            questions,
        ),
        questions=[
            _build_question_out(
                assessment_id=assessment.id,
                question=question,
            )
            for question in questions
        ],
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

    _ensure_active_browser_script(
        await _get_latest_browser_script(
            db,
            candidate_id=candidate.id,
        )
    )

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

    storage_path = asset.storage_path

    if not isinstance(storage_path, str) or not storage_path.strip():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assessment question asset file is not available.",
        )

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

    mime_type = (
        asset.mime_type.strip()
        if isinstance(asset.mime_type, str) and asset.mime_type.strip()
        else "application/octet-stream"
    )

    download_name = (
        asset.original_filename.strip()
        if (
            isinstance(asset.original_filename, str)
            and asset.original_filename.strip()
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

        question = await _get_candidate_question(
            db,
            assessment=assessment,
            question_id=question_id,
        )

        response_text, response_data = _validate_response_for_question(
            question=question,
            response_text=payload.response_text,
            response_data=payload.response_data,
        )

        response = await _get_script_response_safe(
            db,
            script_id=script.id,
            question_id=question.id,
            for_update=True,
        )

        if response is None:
            response = AssessmentResponse(
                script_id=script.id,
                question_id=question.id,
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
            question.id for question in questions if question.is_markable
        }

        response_question_ids = {response.question_id for response in responses}

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
