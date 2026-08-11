from __future__ import annotations

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    status,
)
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    get_current_school_id,
    get_current_user,
)
from app.core.permissions import PermissionService
from app.db.session import get_db
from app.models.subject import Subject
from app.models.user import User
from app.schemas.subject import (
    SubjectCreate,
    SubjectOut,
    SubjectUpdate,
)

router = APIRouter()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _get_school_subject(
    db: AsyncSession,
    *,
    subject_id: int,
    school_id: int,
) -> Subject:
    """
    Return a subject only when it belongs to the current school.
    """

    result = await db.execute(
        select(Subject).where(
            Subject.id == subject_id,
            Subject.school_id == school_id,
        )
    )

    subject = result.scalar_one_or_none()

    if subject is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subject not found.",
        )

    return subject


async def _subject_name_exists(
    db: AsyncSession,
    *,
    school_id: int,
    name: str,
    exclude_subject_id: int | None = None,
) -> bool:
    """
    Return True when another subject in the school has the same name.

    The comparison is case-insensitive.
    """

    statement = select(Subject.id).where(
        Subject.school_id == school_id,
        func.lower(Subject.name) == name.strip().lower(),
    )

    if exclude_subject_id is not None:
        statement = statement.where(
            Subject.id != exclude_subject_id,
        )

    result = await db.execute(statement)

    return result.scalar_one_or_none() is not None


async def _subject_code_exists(
    db: AsyncSession,
    *,
    school_id: int,
    code: str,
    exclude_subject_id: int | None = None,
) -> bool:
    """
    Return True when another subject in the school has the same code.

    The comparison is case-insensitive.
    """

    statement = select(Subject.id).where(
        Subject.school_id == school_id,
        Subject.code.is_not(None),
        func.lower(Subject.code) == code.strip().lower(),
    )

    if exclude_subject_id is not None:
        statement = statement.where(
            Subject.id != exclude_subject_id,
        )

    result = await db.execute(statement)

    return result.scalar_one_or_none() is not None


def _normalise_optional_text(
    value: str | None,
) -> str | None:
    if value is None:
        return None

    cleaned = value.strip()

    return cleaned or None


async def _commit_subject_change(
    db: AsyncSession,
    *,
    duplicate_detail: str,
) -> None:
    """
    Commit a subject change and translate database uniqueness failures.
    """

    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=duplicate_detail,
        ) from exc


# ---------------------------------------------------------------------------
# Subject listing
# ---------------------------------------------------------------------------


@router.get(
    "",
    response_model=list[SubjectOut],
)
async def list_subjects(
    include_inactive: bool = Query(
        default=False,
    ),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    school_id: int = Depends(get_current_school_id),
) -> list[SubjectOut]:
    """
    Return subjects belonging to the current school.

    Inactive subjects are excluded by default.
    """

    PermissionService.ensure_active_user(
        current_user,
    )
    PermissionService.ensure_school_staff_or_platform_admin(
        current_user,
    )

    statement = select(Subject).where(
        Subject.school_id == school_id,
    )

    if not include_inactive:
        statement = statement.where(
            Subject.is_active.is_(True),
        )

    statement = statement.order_by(
        Subject.name.asc(),
        Subject.id.asc(),
    )

    result = await db.execute(statement)

    subjects = result.scalars().all()

    return [SubjectOut.model_validate(subject) for subject in subjects]


# ---------------------------------------------------------------------------
# Subject creation
# ---------------------------------------------------------------------------


@router.post(
    "",
    response_model=SubjectOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_subject(
    payload: SubjectCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    school_id: int = Depends(get_current_school_id),
) -> SubjectOut:
    """
    Create a subject in the current school.
    """

    PermissionService.ensure_active_user(
        current_user,
    )
    PermissionService.ensure_school_staff_or_platform_admin(
        current_user,
    )

    name = payload.name.strip()
    code = _normalise_optional_text(
        payload.code,
    )
    description = _normalise_optional_text(
        payload.description,
    )

    if await _subject_name_exists(
        db,
        school_id=school_id,
        name=name,
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A subject with this name already exists in the current school.",
        )

    if code is not None and await _subject_code_exists(
        db,
        school_id=school_id,
        code=code,
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A subject with this code already exists in the current school.",
        )

    subject = Subject(
        school_id=school_id,
        name=name,
        code=code,
        description=description,
        is_active=payload.is_active,
    )

    db.add(subject)

    await _commit_subject_change(
        db,
        duplicate_detail=(
            "A subject with this name or code already exists in the current school."
        ),
    )

    await db.refresh(subject)

    return SubjectOut.model_validate(subject)


# ---------------------------------------------------------------------------
# Subject update
# ---------------------------------------------------------------------------


@router.patch(
    "/{subject_id}",
    response_model=SubjectOut,
)
async def update_subject(
    subject_id: int,
    payload: SubjectUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    school_id: int = Depends(get_current_school_id),
) -> SubjectOut:
    """
    Update a subject belonging to the current school.
    """

    PermissionService.ensure_active_user(
        current_user,
    )
    PermissionService.ensure_school_staff_or_platform_admin(
        current_user,
    )

    subject = await _get_school_subject(
        db,
        subject_id=subject_id,
        school_id=school_id,
    )

    changes = payload.model_dump(
        exclude_unset=True,
    )

    if "name" in changes:
        name = changes["name"].strip()

        if await _subject_name_exists(
            db,
            school_id=school_id,
            name=name,
            exclude_subject_id=subject.id,
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A subject with this name already exists in the current school.",
            )

        subject.name = name

    if "code" in changes:
        code = _normalise_optional_text(
            changes["code"],
        )

        if code is not None and await _subject_code_exists(
            db,
            school_id=school_id,
            code=code,
            exclude_subject_id=subject.id,
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A subject with this code already exists in the current school.",
            )

        subject.code = code

    if "description" in changes:
        subject.description = _normalise_optional_text(
            changes["description"],
        )

    if "is_active" in changes:
        subject.is_active = changes["is_active"]

    await _commit_subject_change(
        db,
        duplicate_detail=(
            "A subject with this name or code already exists in the current school."
        ),
    )

    await db.refresh(subject)

    return SubjectOut.model_validate(subject)
