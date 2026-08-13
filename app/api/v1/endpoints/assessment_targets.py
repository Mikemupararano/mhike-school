from __future__ import annotations

from typing import Any

from fastapi import (
    APIRouter,
    Depends,
    Query,
    Response,
    status,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    get_current_user,
    get_db,
)
from app.models.user import User
from app.schemas.assessment_target import (
    AssessmentTargetCreate,
    AssessmentTargetOut,
    AssessmentTargetProgressOut,
    AssessmentTargetUpdate,
)
from app.services.assessment_target_service import (
    create_assessment_target,
    delete_assessment_target,
    get_assessment_target,
    get_parent_student_target_progress,
    get_student_target_progress,
    list_assessment_targets,
    update_assessment_target,
)

router = APIRouter()


# ---------------------------------------------------------------------------
# Staff target management
# ---------------------------------------------------------------------------


@router.post(
    "",
    response_model=AssessmentTargetOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_target(
    payload: AssessmentTargetCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AssessmentTargetOut:
    """
    Create one assessment target for a student/course pair.

    Teachers may create targets for courses they teach.

    School administrators may manage targets across their own school.

    Platform administrators may operate across schools when an explicit
    school_id is supplied.
    """

    result = await create_assessment_target(
        db,
        current_user,
        school_id=payload.school_id,
        student_id=payload.student_id,
        course_id=payload.course_id,
        grade_label=payload.grade_label,
        grade_points=payload.grade_points,
        academic_year=payload.academic_year,
        notes=payload.notes,
    )

    return AssessmentTargetOut.model_validate(
        result,
    )


@router.get(
    "",
    response_model=list[AssessmentTargetOut],
)
async def list_targets(
    school_id: int | None = Query(
        default=None,
        ge=1,
    ),
    student_id: int | None = Query(
        default=None,
        ge=1,
    ),
    course_id: int | None = Query(
        default=None,
        ge=1,
    ),
    academic_year: str | None = Query(
        default=None,
        max_length=50,
    ),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[AssessmentTargetOut]:
    """
    Return assessment targets visible to the current staff user.
    """

    results = await list_assessment_targets(
        db,
        current_user,
        school_id=school_id,
        student_id=student_id,
        course_id=course_id,
        academic_year=academic_year,
    )

    return [
        AssessmentTargetOut.model_validate(
            result,
        )
        for result in results
    ]


@router.get(
    "/{target_id}",
    response_model=AssessmentTargetOut,
)
async def get_target(
    target_id: int,
    school_id: int | None = Query(
        default=None,
        ge=1,
    ),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AssessmentTargetOut:
    """
    Return one assessment target visible to the current staff user.
    """

    result = await get_assessment_target(
        db,
        current_user,
        target_id=target_id,
        school_id=school_id,
    )

    return AssessmentTargetOut.model_validate(
        result,
    )


@router.patch(
    "/{target_id}",
    response_model=AssessmentTargetOut,
)
async def update_target(
    target_id: int,
    payload: AssessmentTargetUpdate,
    school_id: int | None = Query(
        default=None,
        ge=1,
    ),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AssessmentTargetOut:
    """
    Partially update an assessment target.

    Only fields explicitly supplied by the client are forwarded to the
    service layer.

    This distinction is important because nullable fields may intentionally
    be cleared by supplying JSON null.
    """

    update_values: dict[str, Any] = payload.model_dump(
        exclude_unset=True,
    )

    result = await update_assessment_target(
        db,
        current_user,
        target_id=target_id,
        school_id=school_id,
        **update_values,
    )

    return AssessmentTargetOut.model_validate(
        result,
    )


@router.delete(
    "/{target_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_target(
    target_id: int,
    school_id: int | None = Query(
        default=None,
        ge=1,
    ),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    """
    Delete one authorised assessment target.
    """

    await delete_assessment_target(
        db,
        current_user,
        target_id=target_id,
        school_id=school_id,
    )

    return Response(
        status_code=status.HTTP_204_NO_CONTENT,
    )


# ---------------------------------------------------------------------------
# Student-facing progress
# ---------------------------------------------------------------------------


@router.get(
    "/student/courses/{course_id}/progress",
    response_model=AssessmentTargetProgressOut,
)
async def get_my_target_progress(
    course_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AssessmentTargetProgressOut:
    """
    Return the logged-in student's target and latest formal performance for
    one course.
    """

    result = await get_student_target_progress(
        db,
        current_user,
        course_id=course_id,
    )

    return AssessmentTargetProgressOut.model_validate(
        result,
    )


# ---------------------------------------------------------------------------
# Parent-facing progress
# ---------------------------------------------------------------------------


@router.get(
    "/parent/students/{student_id}/courses/{course_id}/progress",
    response_model=AssessmentTargetProgressOut,
)
async def get_child_target_progress(
    student_id: int,
    course_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AssessmentTargetProgressOut:
    """
    Return target progress for an authorised linked child.

    Parent-child authorisation remains enforced by the existing assessment
    trend service used by the target service.
    """

    result = await get_parent_student_target_progress(
        db,
        current_user,
        student_id=student_id,
        course_id=course_id,
    )

    return AssessmentTargetProgressOut.model_validate(
        result,
    )
