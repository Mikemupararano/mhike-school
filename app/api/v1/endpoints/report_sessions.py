from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.models.user_role import UserRole
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


def _require_school_id(user: User) -> int:
    if user.school_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not linked to a school.",
        )

    return user.school_id


def _normalise_role(value: object) -> str:
    if isinstance(value, str):
        return value

    role = getattr(value, "role", None)

    if isinstance(role, str):
        return role

    if hasattr(role, "value"):
        return str(role.value)

    if hasattr(value, "value"):
        return str(value.value)

    return str(value)


def _user_has_role(user: User, role: UserRole) -> bool:
    expected_role = _normalise_role(role)

    return any(_normalise_role(user_role) == expected_role for user_role in user.roles)


def _require_report_session_admin(user: User) -> None:
    if not any(
        _user_has_role(user, role)
        for role in (
            UserRole.SCHOOL_ADMIN,
            UserRole.PLATFORM_ADMIN,
        )
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only school admins can manage report sessions.",
        )


@router.get("/", response_model=list[ReportSessionRead])
async def list_report_sessions_endpoint(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ReportSessionRead]:
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
    school_id = _require_school_id(current_user)
    _require_report_session_admin(current_user)

    return await create_report_session(
        db,
        school_id=school_id,
        payload=payload,
    )


@router.get(
    "/{report_session_id}",
    response_model=ReportSessionRead,
)
async def get_report_session_endpoint(
    report_session_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ReportSessionRead:
    school_id = _require_school_id(current_user)

    session = await get_report_session(
        db,
        school_id=school_id,
        report_session_id=report_session_id,
    )

    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report session not found.",
        )

    return session


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
    school_id = _require_school_id(current_user)
    _require_report_session_admin(current_user)

    session = await get_report_session(
        db,
        school_id=school_id,
        report_session_id=report_session_id,
    )

    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report session not found.",
        )

    return await update_report_session(
        db,
        session=session,
        payload=payload,
    )


@router.delete(
    "/{report_session_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_report_session_endpoint(
    report_session_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    school_id = _require_school_id(current_user)
    _require_report_session_admin(current_user)

    session = await get_report_session(
        db,
        school_id=school_id,
        report_session_id=report_session_id,
    )

    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report session not found.",
        )

    await delete_report_session(
        db,
        session=session,
    )
