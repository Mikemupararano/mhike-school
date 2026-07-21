from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.class_group import ClassGroup
from app.models.report_group_content import ReportGroupContent
from app.models.report_session import ReportSession
from app.models.user import User
from app.repositories.report_group_contents import (
    delete_report_group_content,
    get_report_group_content,
    get_report_group_content_by_id,
    list_report_group_contents,
    update_report_group_content,
    upsert_report_group_content,
)
from app.schemas.report_group_content import (
    ReportGroupContentRead,
    ReportGroupContentUpdate,
    ReportGroupContentUpsert,
)

router = APIRouter()


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------


def _require_school_id(user: User) -> int:
    """
    Return the authenticated user's school ID.

    Shared report content is always school-scoped. Platform administrators
    must therefore also be operating with a linked school context when using
    these routes.
    """

    if user.school_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not linked to a school.",
        )

    return user.school_id


def _report_group_content_not_found() -> HTTPException:
    """Create the standard shared-content 404 response."""

    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Shared report content not found.",
    )


def _bad_request(detail: str) -> HTTPException:
    """Create a standard shared-content validation response."""

    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=detail,
    )


def _conflict(detail: str) -> HTTPException:
    """Create a standard shared-content conflict response."""

    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail=detail,
    )


def _can_manage_any_report_group_content(user: User) -> bool:
    """
    Return whether the user may manage shared content across the school.

    School and platform administrators may manage all class-group content
    within the current school.
    """

    return bool(
        user.is_school_admin
        or user.is_platform_admin
    )


async def _get_class_group(
    db: AsyncSession,
    *,
    school_id: int,
    class_group_id: int,
) -> ClassGroup | None:
    """Return one class group restricted to the current school."""

    result = await db.execute(
        select(ClassGroup).where(
            ClassGroup.id == class_group_id,
            ClassGroup.school_id == school_id,
        )
    )

    return result.scalar_one_or_none()


async def _get_report_session(
    db: AsyncSession,
    *,
    school_id: int,
    report_session_id: int,
) -> ReportSession | None:
    """Return one reporting session restricted to the current school."""

    result = await db.execute(
        select(ReportSession).where(
            ReportSession.id == report_session_id,
            ReportSession.school_id == school_id,
        )
    )

    return result.scalar_one_or_none()


async def _validate_scope(
    db: AsyncSession,
    *,
    school_id: int,
    report_session_id: int,
    class_group_id: int,
) -> tuple[ReportSession, ClassGroup]:
    """
    Validate the reporting session and class group for a shared-content scope.

    Both records must belong to the authenticated user's school.
    """

    report_session = await _get_report_session(
        db,
        school_id=school_id,
        report_session_id=report_session_id,
    )

    if report_session is None:
        raise _bad_request(
            "The reporting session was not found for this school."
        )

    class_group = await _get_class_group(
        db,
        school_id=school_id,
        class_group_id=class_group_id,
    )

    if class_group is None:
        raise _bad_request(
            "The class group was not found for this school."
        )

    return report_session, class_group


def _require_content_editor(
    user: User,
    *,
    class_group: ClassGroup,
) -> None:
    """
    Require permission to create or edit shared class content.

    School and platform administrators may manage any class in their school.
    A teacher may manage content only for a class currently assigned to them.
    """

    if _can_manage_any_report_group_content(user):
        return

    if class_group.teacher_id == user.id:
        return

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=(
            "Only the assigned class teacher, School Admin or Platform Admin "
            "can manage shared report content for this class."
        ),
    )


def _require_content_deleter(user: User) -> None:
    """
    Restrict deletion to school and platform administrators.

    Teachers may replace shared text with an empty value but cannot remove
    the scoped database record.
    """

    if not _can_manage_any_report_group_content(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "Only School Admin or Platform Admin users can delete "
                "shared report content."
            ),
        )


async def _commit_or_raise_conflict(
    db: AsyncSession,
    *,
    detail: str,
) -> None:
    """
    Commit a write operation and convert constraint failures into HTTP 409.

    Rollback is required so the dependency-provided session remains usable
    after a failed transaction.
    """

    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise _conflict(detail) from exc


async def _refresh_after_commit(
    db: AsyncSession,
    *,
    record: ReportGroupContent,
) -> ReportGroupContent:
    """Refresh and return a record after committing its transaction."""

    await db.refresh(record)
    return record


# ----------------------------------------------------------------------
# Endpoints
# ----------------------------------------------------------------------


@router.get(
    "/",
    response_model=list[ReportGroupContentRead],
)
async def list_report_group_contents_endpoint(
    report_session_id: int | None = Query(
        default=None,
        ge=1,
    ),
    class_group_id: int | None = Query(
        default=None,
        ge=1,
    ),
    subject_name: str | None = Query(
        default=None,
        min_length=1,
        max_length=100,
    ),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ReportGroupContentRead]:
    """
    List shared report content for the authenticated user's school.

    Optional filters allow clients to request content for one reporting
    session, class group or subject.
    """

    school_id = _require_school_id(current_user)

    return await list_report_group_contents(
        db,
        school_id=school_id,
        report_session_id=report_session_id,
        class_group_id=class_group_id,
        subject_name=subject_name,
    )


@router.get(
    "/scope",
    response_model=ReportGroupContentRead,
)
async def get_report_group_content_by_scope_endpoint(
    report_session_id: int = Query(
        ge=1,
    ),
    class_group_id: int = Query(
        ge=1,
    ),
    subject_name: str = Query(
        min_length=1,
        max_length=100,
    ),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ReportGroupContentRead:
    """
    Return shared content for one exact reporting scope.

    The lookup uses reporting session, class group and subject name. School
    scope is always taken from the authenticated user.
    """

    school_id = _require_school_id(current_user)

    record = await get_report_group_content(
        db,
        school_id=school_id,
        report_session_id=report_session_id,
        class_group_id=class_group_id,
        subject_name=subject_name,
    )

    if record is None:
        raise _report_group_content_not_found()

    return record


@router.get(
    "/{content_id}",
    response_model=ReportGroupContentRead,
)
async def get_report_group_content_endpoint(
    content_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ReportGroupContentRead:
    """Return one shared-content record from the user's school."""

    school_id = _require_school_id(current_user)

    record = await get_report_group_content_by_id(
        db,
        content_id=content_id,
        school_id=school_id,
    )

    if record is None:
        raise _report_group_content_not_found()

    return record


@router.put(
    "/",
    response_model=ReportGroupContentRead,
)
async def upsert_report_group_content_endpoint(
    payload: ReportGroupContentUpsert,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ReportGroupContentRead:
    """
    Create or replace shared work-covered text for one reporting scope.

    Repeated requests for the same school, reporting session, class group and
    subject update the existing record rather than creating duplicates.
    """

    school_id = _require_school_id(current_user)

    _, class_group = await _validate_scope(
        db,
        school_id=school_id,
        report_session_id=payload.report_session_id,
        class_group_id=payload.class_group_id,
    )

    _require_content_editor(
        current_user,
        class_group=class_group,
    )

    try:
        record = await upsert_report_group_content(
            db,
            school_id=school_id,
            report_session_id=payload.report_session_id,
            class_group_id=payload.class_group_id,
            subject_name=payload.subject_name,
            work_covered=payload.work_covered,
            updated_by_id=current_user.id,
        )
    except ValueError as exc:
        await db.rollback()
        raise _bad_request(str(exc)) from exc

    await _commit_or_raise_conflict(
        db,
        detail=(
            "Shared report content already exists for this reporting "
            "session, class group and subject."
        ),
    )

    return await _refresh_after_commit(
        db,
        record=record,
    )


@router.patch(
    "/{content_id}",
    response_model=ReportGroupContentRead,
)
async def update_report_group_content_endpoint(
    content_id: int,
    payload: ReportGroupContentUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ReportGroupContentRead:
    """
    Update the work-covered text of an existing shared-content record.

    The reporting scope cannot be changed through this endpoint.
    """

    school_id = _require_school_id(current_user)

    record = await get_report_group_content_by_id(
        db,
        content_id=content_id,
        school_id=school_id,
    )

    if record is None:
        raise _report_group_content_not_found()

    class_group = await _get_class_group(
        db,
        school_id=school_id,
        class_group_id=record.class_group_id,
    )

    if class_group is None:
        raise _bad_request(
            "The class group linked to this shared content no longer exists."
        )

    _require_content_editor(
        current_user,
        class_group=class_group,
    )

    try:
        record = await update_report_group_content(
            db,
            record=record,
            work_covered=payload.work_covered,
            updated_by_id=current_user.id,
        )
    except ValueError as exc:
        await db.rollback()
        raise _bad_request(str(exc)) from exc

    await _commit_or_raise_conflict(
        db,
        detail="The shared report content could not be updated.",
    )

    return await _refresh_after_commit(
        db,
        record=record,
    )


@router.delete(
    "/{content_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_report_group_content_endpoint(
    content_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """
    Delete one shared-content record.

    Deletion is restricted to school and platform administrators.
    """

    school_id = _require_school_id(current_user)
    _require_content_deleter(current_user)

    record = await get_report_group_content_by_id(
        db,
        content_id=content_id,
        school_id=school_id,
    )

    if record is None:
        raise _report_group_content_not_found()

    await delete_report_group_content(
        db,
        record=record,
    )

    await _commit_or_raise_conflict(
        db,
        detail="The shared report content could not be deleted.",
    )