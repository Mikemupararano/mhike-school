from __future__ import annotations

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    Response,
    status,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.permissions import PermissionService
from app.db.session import get_db
from app.models.assessment import AssessmentStatus
from app.models.user import User
from app.schemas.assessment import (
    AssessmentCreate,
    AssessmentOut,
    AssessmentStatusUpdate,
    AssessmentUpdate,
)
from app.services.assessment_service import (
    archive_assessment,
    close_assessment,
    create_assessment,
    delete_assessment,
    get_assessment,
    list_assessments,
    publish_assessment,
    transition_assessment_status,
    update_assessment,
)

router = APIRouter()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ensure_assessment_staff_access(
    current_user: User,
) -> None:
    """
    Ensure the current user may use staff assessment-management endpoints.

    Detailed course ownership, school isolation, and administrator scope are
    enforced by the assessment service itself.
    """

    PermissionService.ensure_active_user(
        current_user,
    )

    PermissionService.ensure_school_staff_or_platform_admin(
        current_user,
    )


async def _load_assessment_out(
    db: AsyncSession,
    *,
    current_user: User,
    assessment_id: int,
) -> AssessmentOut:
    """
    Reload and serialise an assessment with its standard relationships.

    Reloading through the assessment service ensures the response reflects
    current database state and respects the same school/teacher access rules
    as ordinary assessment retrieval.
    """

    assessment = await get_assessment(
        db=db,
        current_user=current_user,
        assessment_id=assessment_id,
        include_relationships=True,
    )

    return AssessmentOut.model_validate(
        assessment,
    )


def _translate_value_error(
    exc: ValueError,
) -> HTTPException:
    """
    Translate domain/repository validation errors into a client response.
    """

    return HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail=str(exc),
    )


# ---------------------------------------------------------------------------
# Assessment listing
# ---------------------------------------------------------------------------


@router.get(
    "",
    response_model=list[AssessmentOut],
)
async def get_assessments(
    course_id: int | None = Query(
        default=None,
        gt=0,
    ),
    assessment_status: AssessmentStatus | None = Query(
        default=None,
    ),
    academic_year: str | None = Query(
        default=None,
        max_length=50,
    ),
    term: str | None = Query(
        default=None,
        max_length=100,
    ),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[AssessmentOut]:
    """
    Return assessments visible to the current user.

    Teachers without administrative scope see their own assessments.

    School administrators see assessments belonging to their school.

    Platform administrators may see assessments across schools.
    """

    _ensure_assessment_staff_access(
        current_user,
    )

    try:
        assessments = await list_assessments(
            db=db,
            current_user=current_user,
            course_id=course_id,
            assessment_status=assessment_status,
            academic_year=academic_year,
            term=term,
            include_relationships=True,
        )
    except ValueError as exc:
        raise _translate_value_error(
            exc,
        ) from exc

    return [
        AssessmentOut.model_validate(
            assessment,
        )
        for assessment in assessments
    ]


# ---------------------------------------------------------------------------
# Assessment retrieval
# ---------------------------------------------------------------------------


@router.get(
    "/{assessment_id}",
    response_model=AssessmentOut,
)
async def get_assessment_by_id(
    assessment_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AssessmentOut:
    """
    Return one assessment visible to the current user.
    """

    _ensure_assessment_staff_access(
        current_user,
    )

    try:
        return await _load_assessment_out(
            db,
            current_user=current_user,
            assessment_id=assessment_id,
        )
    except ValueError as exc:
        raise _translate_value_error(
            exc,
        ) from exc


# ---------------------------------------------------------------------------
# Assessment creation
# ---------------------------------------------------------------------------


@router.post(
    "",
    response_model=AssessmentOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_assessment_endpoint(
    payload: AssessmentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AssessmentOut:
    """
    Create a draft assessment.

    Course ownership and school scope are enforced by the assessment
    service. Assessments are never published implicitly during creation.
    """

    _ensure_assessment_staff_access(
        current_user,
    )

    try:
        assessment = await create_assessment(
            db=db,
            current_user=current_user,
            course_id=payload.course_id,
            title=payload.title,
            description=payload.description,
            assessment_type=payload.assessment_type,
            academic_year=payload.academic_year,
            term=payload.term,
            anonymous_marking=payload.anonymous_marking,
            scheduled_at=payload.scheduled_at,
            closes_at=payload.closes_at,
        )
    except ValueError as exc:
        raise _translate_value_error(
            exc,
        ) from exc

    return await _load_assessment_out(
        db,
        current_user=current_user,
        assessment_id=assessment.id,
    )


# ---------------------------------------------------------------------------
# Assessment editing
# ---------------------------------------------------------------------------


@router.patch(
    "/{assessment_id}",
    response_model=AssessmentOut,
)
async def update_assessment_endpoint(
    assessment_id: int,
    payload: AssessmentUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AssessmentOut:
    """
    Update an existing draft assessment.

    Published, closed, and archived assessments cannot be edited through
    this endpoint.
    """

    _ensure_assessment_staff_access(
        current_user,
    )

    changes = payload.model_dump(
        exclude_unset=True,
    )

    try:
        assessment = await update_assessment(
            db=db,
            current_user=current_user,
            assessment_id=assessment_id,
            **changes,
        )
    except TypeError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid assessment update payload.",
        ) from exc
    except ValueError as exc:
        raise _translate_value_error(
            exc,
        ) from exc

    return await _load_assessment_out(
        db,
        current_user=current_user,
        assessment_id=assessment.id,
    )


# ---------------------------------------------------------------------------
# Generic lifecycle transition
# ---------------------------------------------------------------------------


@router.patch(
    "/{assessment_id}/status",
    response_model=AssessmentOut,
)
async def update_assessment_status(
    assessment_id: int,
    payload: AssessmentStatusUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AssessmentOut:
    """
    Move an assessment through an allowed lifecycle transition.
    """

    _ensure_assessment_staff_access(
        current_user,
    )

    try:
        assessment = await transition_assessment_status(
            db=db,
            current_user=current_user,
            assessment_id=assessment_id,
            new_status=payload.status,
        )
    except ValueError as exc:
        raise _translate_value_error(
            exc,
        ) from exc

    return await _load_assessment_out(
        db,
        current_user=current_user,
        assessment_id=assessment.id,
    )


# ---------------------------------------------------------------------------
# Explicit lifecycle actions
# ---------------------------------------------------------------------------


@router.post(
    "/{assessment_id}/publish",
    response_model=AssessmentOut,
)
async def publish_assessment_endpoint(
    assessment_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AssessmentOut:
    """
    Publish a valid draft assessment.
    """

    _ensure_assessment_staff_access(
        current_user,
    )

    try:
        assessment = await publish_assessment(
            db=db,
            current_user=current_user,
            assessment_id=assessment_id,
        )
    except ValueError as exc:
        raise _translate_value_error(
            exc,
        ) from exc

    return await _load_assessment_out(
        db,
        current_user=current_user,
        assessment_id=assessment.id,
    )


@router.post(
    "/{assessment_id}/close",
    response_model=AssessmentOut,
)
async def close_assessment_endpoint(
    assessment_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AssessmentOut:
    """
    Close a published assessment.
    """

    _ensure_assessment_staff_access(
        current_user,
    )

    try:
        assessment = await close_assessment(
            db=db,
            current_user=current_user,
            assessment_id=assessment_id,
        )
    except ValueError as exc:
        raise _translate_value_error(
            exc,
        ) from exc

    return await _load_assessment_out(
        db,
        current_user=current_user,
        assessment_id=assessment.id,
    )


@router.post(
    "/{assessment_id}/archive",
    response_model=AssessmentOut,
)
async def archive_assessment_endpoint(
    assessment_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AssessmentOut:
    """
    Archive an eligible assessment.
    """

    _ensure_assessment_staff_access(
        current_user,
    )

    try:
        assessment = await archive_assessment(
            db=db,
            current_user=current_user,
            assessment_id=assessment_id,
        )
    except ValueError as exc:
        raise _translate_value_error(
            exc,
        ) from exc

    return await _load_assessment_out(
        db,
        current_user=current_user,
        assessment_id=assessment.id,
    )


# ---------------------------------------------------------------------------
# Assessment deletion
# ---------------------------------------------------------------------------


@router.delete(
    "/{assessment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_assessment_endpoint(
    assessment_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    """
    Delete a draft assessment.

    Once an assessment has entered the published lifecycle it is retained
    for candidate, script, marking, moderation, and audit history.
    """

    _ensure_assessment_staff_access(
        current_user,
    )

    try:
        await delete_assessment(
            db=db,
            current_user=current_user,
            assessment_id=assessment_id,
        )
    except ValueError as exc:
        raise _translate_value_error(
            exc,
        ) from exc

    return Response(
        status_code=status.HTTP_204_NO_CONTENT,
    )
