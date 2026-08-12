from __future__ import annotations

from fastapi import (
    APIRouter,
    Depends,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.published_assessment_results import (
    ParentPublishedAssessmentResultOut,
    StudentPublishedAssessmentResultOut,
)
from app.services.published_assessment_results_service import (
    get_parent_published_assessment_result,
    get_student_published_assessment_result,
)

router = APIRouter()


@router.get(
    "/student/candidates/{candidate_id}",
    response_model=StudentPublishedAssessmentResultOut,
)
async def get_student_published_result(
    candidate_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> StudentPublishedAssessmentResultOut:
    """
    Return one published assessment result for the logged-in student.

    The service layer enforces candidate ownership, publication status,
    student visibility, and configured field visibility.
    """

    result = await get_student_published_assessment_result(
        db=db,
        current_user=current_user,
        candidate_id=candidate_id,
    )

    return StudentPublishedAssessmentResultOut.model_validate(
        result,
    )


@router.get(
    "/parent/candidates/{candidate_id}",
    response_model=ParentPublishedAssessmentResultOut,
)
async def get_parent_published_result(
    candidate_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ParentPublishedAssessmentResultOut:
    """
    Return one published assessment result for an authorised linked child.

    The service layer enforces the parent-child relationship, publication
    status, parent visibility, and configured field visibility.
    """

    result = await get_parent_published_assessment_result(
        db=db,
        current_user=current_user,
        candidate_id=candidate_id,
    )

    return ParentPublishedAssessmentResultOut.model_validate(
        result,
    )
