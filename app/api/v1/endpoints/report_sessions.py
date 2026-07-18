from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
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
    """Return the user's school ID or reject unlinked users."""

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
            detail="Only school administrators can manage report sessions.",
        )


def _report_session_not_found() -> HTTPException:
    """Create the standard report-session 404 response."""

    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Report session not found.",
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
):
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
):
    school_id = _require_school_id(current_user)
    _require_report_session_admin(current_user)

    try:
        return await create_report_session(
            db,
            school_id=school_id,
            payload=payload,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.get(
    "/{report_session_id}",
    response_model=ReportSessionRead,
)
async def get_report_session_endpoint(
    report_session_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
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
):
    school_id = _require_school_id(current_user)
    _require_report_session_admin(current_user)

    report_session = await get_report_session(
        db,
        school_id=school_id,
        report_session_id=report_session_id,
    )

    if report_session is None:
        raise _report_session_not_found()

    try:
        return await update_report_session(
            db,
            session=report_session,
            payload=payload,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.delete(
    "/{report_session_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_report_session_endpoint(
    report_session_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    school_id = _require_school_id(current_user)
    _require_report_session_admin(current_user)

    report_session = await get_report_session(
        db,
        school_id=school_id,
        report_session_id=report_session_id,
    )

    if report_session is None:
        raise _report_session_not_found()

    await delete_report_session(
        db,
        session=report_session,
    )
