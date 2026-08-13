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
from app.schemas.assessment_trends import (
    ParentStudentAssessmentTrendOut,
    StudentAssessmentTrendOut,
)
from app.services.assessment_trends_service import (
    get_parent_student_assessment_trend,
    get_student_assessment_trend,
)

router = APIRouter()


# ---------------------------------------------------------------------------
# Student-facing longitudinal trend
# ---------------------------------------------------------------------------


@router.get(
    "/student",
    response_model=StudentAssessmentTrendOut,
)
async def get_student_trend(
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
) -> StudentAssessmentTrendOut:
    """
    Return published longitudinal assessment performance for the logged-in
    student.

    Optional filters allow the client to restrict the trend to a school,
    course, subject, academic year or term.

    The service layer derives the student identity from ``current_user`` and
    uses the existing published-result pipeline, so unpublished or hidden
    assessments do not appear in the trend.
    """

    result = await get_student_assessment_trend(
        db=db,
        current_user=current_user,
        school_id=school_id,
        course_id=course_id,
        subject_id=subject_id,
        academic_year=academic_year,
        term=term,
    )

    return StudentAssessmentTrendOut.model_validate(
        result,
    )


# ---------------------------------------------------------------------------
# Parent-facing linked-child longitudinal trend
# ---------------------------------------------------------------------------


@router.get(
    "/parent/students/{student_id}",
    response_model=ParentStudentAssessmentTrendOut,
)
async def get_parent_student_trend(
    student_id: int,
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
) -> ParentStudentAssessmentTrendOut:
    """
    Return published longitudinal assessment performance for an authorised
    linked child.

    Parent-child authorization is performed by the service before candidate
    history is queried. Each individual result is then independently checked
    through the existing parent published-result service.
    """

    result = await get_parent_student_assessment_trend(
        db=db,
        current_user=current_user,
        student_id=student_id,
        school_id=school_id,
        course_id=course_id,
        subject_id=subject_id,
        academic_year=academic_year,
        term=term,
    )

    return ParentStudentAssessmentTrendOut.model_validate(
        result,
    )
