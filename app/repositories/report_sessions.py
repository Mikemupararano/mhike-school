from __future__ import annotations

from typing import Final

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.report_session import ReportSession
from app.schemas.report_session import (
    ReportSessionCreate,
    ReportSessionUpdate,
)

# Fields copied when an administrator creates a report session from an
# existing session. Identity, ownership, academic-year, checkpoint, lifecycle
# and audit fields are deliberately excluded.
REPORT_CONFIGURATION_FIELDS: Final[frozenset[str]] = frozenset(
    {
        "reporting_mode",
        "enable_report_generation",
        "include_school_name",
        "include_school_logo",
        "include_teacher_name",
        "include_subject_name",
        "include_work_covered",
        "include_student_comment",
        "include_exam_mark",
        "include_exam_grade",
        "include_effort_grade",
        "include_attainment_grade",
        "include_target_grade",
        "include_gcse_predicted_grade",
        "include_ucas_predicted_grade",
        "include_next_steps",
        "include_tutor_comment",
        "include_head_of_year_comment",
        "include_headteacher_comment",
        "include_attendance",
        "include_behaviour",
        "require_student_comment",
        "require_effort_grade",
        "require_attainment_grade",
        "require_target_grade",
        "require_exam_mark",
        "require_exam_grade",
        "require_gcse_predicted_grade",
        "require_ucas_predicted_grade",
        "require_next_steps",
        "require_tutor_comment",
        "require_head_of_year_comment",
        "require_headteacher_comment",
        "allow_teacher_edit_after_submission",
        "allow_smt_edit_after_approval",
        "show_previous_grades",
        "show_previous_tutor_comments",
        "show_progress_journey",
    }
)


def _normalise_checkpoint_fields(
    data: dict[str, object],
    *,
    supplied_fields: set[str],
) -> dict[str, object]:
    """
    Keep the legacy ``term`` field compatible with ``checkpoint_name``.

    New clients should use ``checkpoint_name``. Existing clients may continue
    to send ``term`` while the frontend is being migrated.

    Explicit null values are also mirrored so PATCH requests can clear both
    representations consistently. If a checkpoint name exceeds the legacy
    50-character term limit, ``term`` is cleared rather than left stale.
    """

    checkpoint_name = data.get("checkpoint_name")
    term = data.get("term")

    if "checkpoint_name" in supplied_fields and "term" not in supplied_fields:
        if checkpoint_name is None:
            data["term"] = None
        elif isinstance(checkpoint_name, str):
            data["term"] = checkpoint_name if len(checkpoint_name) <= 50 else None

    elif "term" in supplied_fields and "checkpoint_name" not in supplied_fields:
        if term is None:
            data["checkpoint_name"] = None
        elif isinstance(term, str):
            data["checkpoint_name"] = term

    return data


def _validation_error_message(exc: ValidationError) -> str:
    """Convert a Pydantic validation error into a readable repository error."""

    messages: list[str] = []

    for error in exc.errors():
        location = ".".join(str(part) for part in error.get("loc", ()))
        message = str(error.get("msg", "Invalid value."))

        messages.append(f"{location}: {message}" if location else message)

    return "; ".join(messages) or "Invalid report-session configuration."


def _validate_complete_configuration(data: dict[str, object]) -> None:
    """
    Validate a complete create-shaped configuration.

    This is required after configuration copying because the incoming
    ReportSessionCreate payload is validated before copied values are merged.
    Explicit request values combined with inherited values must also form a
    valid configuration.
    """

    try:
        ReportSessionCreate.model_validate(data)
    except ValidationError as exc:
        raise ValueError(_validation_error_message(exc)) from exc


async def _commit_or_raise(
    db: AsyncSession,
    *,
    integrity_message: str,
) -> None:
    """Commit a transaction and restore the session after database failures."""

    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise ValueError(integrity_message) from exc
    except Exception:
        await db.rollback()
        raise


async def _get_copy_source(
    db: AsyncSession,
    *,
    school_id: int,
    source_session_id: int,
) -> ReportSession:
    """
    Return the session used as a configuration-copy source.

    The school filter prevents one school from copying another school's
    reporting configuration.
    """

    result = await db.execute(
        select(ReportSession).where(
            ReportSession.id == source_session_id,
            ReportSession.school_id == school_id,
        ),
    )

    source_session = result.scalar_one_or_none()

    if source_session is None:
        raise ValueError(
            "The report session selected as the copy source was not found."
        )

    return source_session


def _copy_configuration(
    *,
    source: ReportSession,
    destination_data: dict[str, object],
    explicitly_supplied_fields: set[str],
) -> dict[str, object]:
    """
    Copy report configuration while preserving explicit request values.

    For example, an administrator may copy an earlier full-report
    configuration but explicitly change ``reporting_mode`` to ``grade_card``
    in the new session.
    """

    for field_name in REPORT_CONFIGURATION_FIELDS:
        if field_name not in explicitly_supplied_fields:
            destination_data[field_name] = getattr(source, field_name)

    return destination_data


async def create_report_session(
    db: AsyncSession,
    *,
    school_id: int,
    payload: ReportSessionCreate,
) -> ReportSession:
    """
    Create a school reporting checkpoint.

    When ``copied_from_session_id`` is supplied, configuration fields are
    inherited from that session. Values explicitly supplied in the request
    take precedence over copied values.
    """

    supplied_fields = set(payload.model_fields_set)

    create_data = payload.model_dump()
    create_data = _normalise_checkpoint_fields(
        create_data,
        supplied_fields=supplied_fields,
    )

    source_session_id = create_data.get("copied_from_session_id")

    if isinstance(source_session_id, int):
        source_session = await _get_copy_source(
            db,
            school_id=school_id,
            source_session_id=source_session_id,
        )

        create_data = _copy_configuration(
            source=source_session,
            destination_data=create_data,
            explicitly_supplied_fields=supplied_fields,
        )

    # Revalidate after copy inheritance. This catches contradictions created
    # by combining explicit request values with inherited require/include
    # settings.
    _validate_complete_configuration(create_data)

    report_session = ReportSession(
        school_id=school_id,
        **create_data,
    )

    db.add(report_session)

    await _commit_or_raise(
        db,
        integrity_message=(
            "The report session could not be created because its database "
            "constraints were not satisfied."
        ),
    )
    await db.refresh(report_session)

    return report_session


async def list_report_sessions(
    db: AsyncSession,
    *,
    school_id: int,
) -> list[ReportSession]:
    """
    Return reporting checkpoints for one school.

    Sessions are grouped by academic year and then displayed in their
    configured checkpoint order.
    """

    result = await db.execute(
        select(ReportSession)
        .where(
            ReportSession.school_id == school_id,
        )
        .order_by(
            ReportSession.academic_year.desc(),
            ReportSession.display_order.asc(),
            ReportSession.created_at.asc(),
            ReportSession.id.asc(),
        ),
    )

    return list(result.scalars().all())


async def get_report_session(
    db: AsyncSession,
    *,
    school_id: int,
    report_session_id: int,
) -> ReportSession | None:
    """Retrieve one report session while enforcing school isolation."""

    result = await db.execute(
        select(ReportSession).where(
            ReportSession.id == report_session_id,
            ReportSession.school_id == school_id,
        ),
    )

    return result.scalar_one_or_none()


async def update_report_session(
    db: AsyncSession,
    *,
    session: ReportSession,
    payload: ReportSessionUpdate,
) -> ReportSession:
    """
    Partially update a reporting checkpoint.

    Configuration is not automatically recopied when the source-session
    reference changes. Copying is applied only when a new session is created,
    which prevents existing configuration from being overwritten
    unexpectedly.

    Explicit null values are preserved because ``exclude_unset=True`` removes
    omitted fields but retains fields intentionally supplied as null.
    """

    supplied_fields = set(payload.model_fields_set)

    update_data = payload.model_dump(
        exclude_unset=True,
    )
    update_data = _normalise_checkpoint_fields(
        update_data,
        supplied_fields=supplied_fields,
    )

    copied_from_session_id = update_data.get("copied_from_session_id")

    if isinstance(copied_from_session_id, int):
        if copied_from_session_id == session.id:
            raise ValueError("A report session cannot copy configuration from itself.")

        await _get_copy_source(
            db,
            school_id=session.school_id,
            source_session_id=copied_from_session_id,
        )

    # The endpoint validates the merged PATCH state before calling the
    # repository. Keeping repository mutation limited to supplied fields
    # avoids overwriting stored values with schema defaults.
    for field_name, value in update_data.items():
        setattr(session, field_name, value)

    await _commit_or_raise(
        db,
        integrity_message=(
            "The report session could not be updated because its database "
            "constraints were not satisfied."
        ),
    )
    await db.refresh(session)

    return session


async def delete_report_session(
    db: AsyncSession,
    *,
    session: ReportSession,
) -> None:
    """
    Delete a reporting checkpoint.

    The endpoint is responsible for blocking deletion of published sessions.
    Database foreign-key rules determine whether linked records prevent or
    cascade the deletion.
    """

    await db.delete(session)

    await _commit_or_raise(
        db,
        integrity_message=(
            "The report session cannot be deleted while dependent records "
            "still reference it."
        ),
    )
