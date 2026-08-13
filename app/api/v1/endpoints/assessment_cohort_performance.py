from __future__ import annotations

from fastapi import (
    APIRouter,
    Depends,
    Query,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.assessment_cohort_performance import (
    AssessmentCohortPerformanceOut,
)
from app.services.assessment_cohort_performance_service import (
    get_assessment_cohort_performance,
    get_course_assessment_performance,
    get_subject_assessment_performance,
    get_teacher_assessment_performance,
)

router = APIRouter()


# ---------------------------------------------------------------------------
# General cohort performance
# ---------------------------------------------------------------------------


@router.get(
    "",
    response_model=AssessmentCohortPerformanceOut,
)
async def get_cohort_performance(
    school_id: int | None = Query(
        default=None,
        ge=1,
    ),
    course_id: int | None = Query(
        default=None,
        ge=1,
    ),
    subject_id: int | None = Query(
        default=None,
        ge=1,
    ),
    teacher_id: int | None = Query(
        default=None,
        ge=1,
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
) -> AssessmentCohortPerformanceOut:
    """
    Return comparative assessment performance across the caller's accessible
    assessment scope.

    Optional filters allow narrowing by school, course, subject, teacher,
    academic year or term.

    Formal statistics use the existing assessment analytics layer, which
    means latest fully-finalised candidate script results only.
    """

    result = await get_assessment_cohort_performance(
        db=db,
        current_user=current_user,
        school_id=school_id,
        course_id=course_id,
        subject_id=subject_id,
        teacher_id=teacher_id,
        academic_year=academic_year,
        term=term,
    )

    return AssessmentCohortPerformanceOut.model_validate(
        result,
    )


# ---------------------------------------------------------------------------
# Course performance
# ---------------------------------------------------------------------------


@router.get(
    "/courses/{course_id}",
    response_model=AssessmentCohortPerformanceOut,
)
async def get_course_performance(
    course_id: int,
    school_id: int | None = Query(
        default=None,
        ge=1,
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
) -> AssessmentCohortPerformanceOut:
    """
    Return comparative assessment performance for one course.
    """

    result = await get_course_assessment_performance(
        db=db,
        current_user=current_user,
        course_id=course_id,
        school_id=school_id,
        academic_year=academic_year,
        term=term,
    )

    return AssessmentCohortPerformanceOut.model_validate(
        result,
    )


# ---------------------------------------------------------------------------
# Subject performance
# ---------------------------------------------------------------------------


@router.get(
    "/subjects/{subject_id}",
    response_model=AssessmentCohortPerformanceOut,
)
async def get_subject_performance(
    subject_id: int,
    school_id: int | None = Query(
        default=None,
        ge=1,
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
) -> AssessmentCohortPerformanceOut:
    """
    Return comparative assessment performance across courses belonging to one
    canonical subject.
    """

    result = await get_subject_assessment_performance(
        db=db,
        current_user=current_user,
        subject_id=subject_id,
        school_id=school_id,
        academic_year=academic_year,
        term=term,
    )

    return AssessmentCohortPerformanceOut.model_validate(
        result,
    )


# ---------------------------------------------------------------------------
# Teacher performance
# ---------------------------------------------------------------------------


@router.get(
    "/teachers/{teacher_id}",
    response_model=AssessmentCohortPerformanceOut,
)
async def get_teacher_performance(
    teacher_id: int,
    school_id: int | None = Query(
        default=None,
        ge=1,
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
) -> AssessmentCohortPerformanceOut:
    """
    Return comparative assessment performance for courses taught by one
    teacher.

    Non-admin teachers may only request their own teacher identifier.
    """

    result = await get_teacher_assessment_performance(
        db=db,
        current_user=current_user,
        teacher_id=teacher_id,
        school_id=school_id,
        academic_year=academic_year,
        term=term,
    )

    return AssessmentCohortPerformanceOut.model_validate(
        result,
    )
