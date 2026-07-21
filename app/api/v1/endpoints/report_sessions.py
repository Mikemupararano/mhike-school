from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.report_session import ReportSession
from app.models.user import User
from app.repositories.report_sessions import (
    create_report_session,
    delete_report_session,
    get_report_session,
    list_report_sessions,
    update_report_session,
)
from app.schemas.report_session import (
    ReportSessionCreate,
    ReportSessionRead,
    ReportSessionUpdate,
)

router = APIRouter()


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------


def _require_school_id(user: User) -> int:
    """
    Return the user's school ID or reject users without a school context.

    Report-session endpoints are school-scoped. A platform administrator must
    therefore also be operating with a linked school context when using these
    routes.
    """

    if user.school_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not linked to a school.",
        )

    return user.school_id


def _require_report_session_admin(user: User) -> None:
    """Restrict report-session management to school/platform admins."""

    if not (user.is_school_admin or user.is_platform_admin):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "Only School Admin or Platform Admin users can manage "
                "report sessions."
            ),
        )


def _report_session_not_found() -> HTTPException:
    """Create the standard report-session 404 response."""

    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Report session not found.",
    )


def _bad_request(detail: str) -> HTTPException:
    """Create a standard report-session validation response."""

    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=detail,
    )


def _validation_error_detail(exc: ValidationError) -> str:
    """Return a readable message from a Pydantic validation error."""

    errors = exc.errors()

    if not errors:
        return "Invalid report-session configuration."

    messages: list[str] = []

    for error in errors:
        location = ".".join(str(item) for item in error.get("loc", ()))
        message = str(error.get("msg", "Invalid value."))

        if location:
            messages.append(f"{location}: {message}")
        else:
            messages.append(message)

    return "; ".join(messages)


def _validate_merged_update(
    session: ReportSession,
    payload: ReportSessionUpdate,
) -> None:
    """
    Validate a PATCH request against the complete resulting configuration.

    ReportSessionUpdate correctly makes every field optional, but that means
    it cannot independently detect contradictions involving values already
    stored in the database. This helper merges the supplied fields with the
    current session and validates the resulting state through
    ReportSessionCreate.

    Examples caught here include:

    - requiring a field while excluding it;
    - changing an included field to false while its require flag remains true;
    - unsupported reporting modes;
    - invalid display order values.
    """

    current_values = {
        field_name: getattr(session, field_name)
        for field_name in ReportSessionCreate.model_fields
    }

    supplied_values = payload.model_dump(exclude_unset=True)
    current_values.update(supplied_values)

    try:
        ReportSessionCreate.model_validate(current_values)
    except ValidationError as exc:
        raise _bad_request(_validation_error_detail(exc)) from exc


async def _validate_copy_source(
    db: AsyncSession,
    *,
    school_id: int,
    copied_from_session_id: int | None,
    current_session_id: int | None = None,
) -> None:
    """
    Validate an optional source session used for configuration copying.

    The source must:

    - belong to the same school;
    - exist;
    - not be the session currently being updated.
    """

    if copied_from_session_id is None:
        return

    if current_session_id is not None and copied_from_session_id == current_session_id:
        raise _bad_request("A report session cannot copy configuration from itself.")

    source_session = await get_report_session(
        db,
        school_id=school_id,
        report_session_id=copied_from_session_id,
    )

    if source_session is None:
        raise _bad_request(
            "The copied-from report session was not found for this school."
        )


# ----------------------------------------------------------------------
# Endpoints
# ----------------------------------------------------------------------


@router.get(
    "/",
    response_model=list[ReportSessionRead],
)
async def list_report_sessions_endpoint(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ReportSessionRead]:
    """
    List reporting checkpoints for the authenticated user's school.

    Reading session configuration is available to authenticated school users
    because teachers and reviewers need it to determine which report fields
    are enabled.
    """

    school_id = _require_school_id(current_user)

    return await list_report_sessions(
        db,
        school_id=school_id,
    )


@router.post(
    "/",
    response_model=ReportSessionRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_report_session_endpoint(
    payload: ReportSessionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ReportSessionRead:
    """Create a school-scoped reporting checkpoint."""

    school_id = _require_school_id(current_user)
    _require_report_session_admin(current_user)

    await _validate_copy_source(
        db,
        school_id=school_id,
        copied_from_session_id=payload.copied_from_session_id,
    )

    try:
        return await create_report_session(
            db,
            school_id=school_id,
            payload=payload,
        )
    except ValueError as exc:
        raise _bad_request(str(exc)) from exc


@router.get(
    "/{report_session_id}",
    response_model=ReportSessionRead,
)
async def get_report_session_endpoint(
    report_session_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ReportSessionRead:
    """Return one reporting checkpoint from the user's school."""

    school_id = _require_school_id(current_user)

    report_session = await get_report_session(
        db,
        school_id=school_id,
        report_session_id=report_session_id,
    )

    if report_session is None:
        raise _report_session_not_found()

    return report_session


@router.patch(
    "/{report_session_id}",
    response_model=ReportSessionRead,
)
async def update_report_session_endpoint(
    report_session_id: int,
    payload: ReportSessionUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ReportSessionRead:
    """
    Partially update a reporting checkpoint.

    The payload is merged with the persisted record before validation so a
    PATCH request cannot leave the session in a contradictory configuration.
    """

    school_id = _require_school_id(current_user)
    _require_report_session_admin(current_user)

    report_session = await get_report_session(
        db,
        school_id=school_id,
        report_session_id=report_session_id,
    )

    if report_session is None:
        raise _report_session_not_found()

    supplied_values = payload.model_dump(exclude_unset=True)

    if "copied_from_session_id" in supplied_values:
        await _validate_copy_source(
            db,
            school_id=school_id,
            copied_from_session_id=payload.copied_from_session_id,
            current_session_id=report_session_id,
        )

    _validate_merged_update(
        report_session,
        payload,
    )

    try:
        return await update_report_session(
            db,
            session=report_session,
            payload=payload,
        )
    except ValueError as exc:
        raise _bad_request(str(exc)) from exc


@router.delete(
    "/{report_session_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_report_session_endpoint(
    report_session_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """
    Delete an unpublished reporting checkpoint.

    Published sessions are historical records and must not be removed through
    this endpoint. They should instead be unpublished through the reporting
    workflow before any destructive operation is considered.
    """

    school_id = _require_school_id(current_user)
    _require_report_session_admin(current_user)

    report_session = await get_report_session(
        db,
        school_id=school_id,
        report_session_id=report_session_id,
    )

    if report_session is None:
        raise _report_session_not_found()

    if report_session.published_at is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Published report sessions cannot be deleted.",
        )

    try:
        await delete_report_session(
            db,
            session=report_session,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
