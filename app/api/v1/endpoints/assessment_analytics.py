from __future__ import annotations

from fastapi import (
    APIRouter,
    Depends,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.assessment_analytics import (
    AssessmentAnalyticsOut,
    AssessmentAnalyticsSummaryOut,
    AssessmentCandidateRankingOut,
    AssessmentGradeDistributionOut,
)
from app.services.assessment_analytics_service import (
    get_assessment_analytics,
    get_assessment_analytics_summary,
    get_assessment_candidate_ranking,
    get_assessment_grade_distribution,
)

router = APIRouter()


# ---------------------------------------------------------------------------
# Full analytics
# ---------------------------------------------------------------------------


@router.get(
    "/assessments/{assessment_id}",
    response_model=AssessmentAnalyticsOut,
)
async def get_full_assessment_analytics(
    assessment_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AssessmentAnalyticsOut:
    """
    Return complete analytics for one assessment.

    Formal cohort statistics use each candidate's latest fully-finalised
    script result only.

    Access control is enforced by the analytics service through the existing
    assessment-results permissions, including teacher course ownership,
    school isolation, and administrator scope.
    """

    result = await get_assessment_analytics(
        db=db,
        current_user=current_user,
        assessment_id=assessment_id,
    )

    return AssessmentAnalyticsOut.model_validate(
        result,
    )


# ---------------------------------------------------------------------------
# Compact summary
# ---------------------------------------------------------------------------


@router.get(
    "/assessments/{assessment_id}/summary",
    response_model=AssessmentAnalyticsSummaryOut,
)
async def get_compact_assessment_analytics(
    assessment_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AssessmentAnalyticsSummaryOut:
    """
    Return compact assessment analytics for dashboards and list views.

    Ranking and question-level rows are intentionally excluded.
    """

    result = await get_assessment_analytics_summary(
        db=db,
        current_user=current_user,
        assessment_id=assessment_id,
    )

    return AssessmentAnalyticsSummaryOut.model_validate(
        result,
    )


# ---------------------------------------------------------------------------
# Candidate ranking
# ---------------------------------------------------------------------------


@router.get(
    "/assessments/{assessment_id}/ranking",
    response_model=list[AssessmentCandidateRankingOut],
)
async def get_assessment_ranking(
    assessment_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[AssessmentCandidateRankingOut]:
    """
    Return formal candidate ranking for an assessment.

    Ties use standard competition ranking.
    """

    result = await get_assessment_candidate_ranking(
        db=db,
        current_user=current_user,
        assessment_id=assessment_id,
    )

    return [
        AssessmentCandidateRankingOut.model_validate(
            row,
        )
        for row in result
    ]


# ---------------------------------------------------------------------------
# Grade distribution
# ---------------------------------------------------------------------------


@router.get(
    "/assessments/{assessment_id}/grade-distribution",
    response_model=AssessmentGradeDistributionOut,
)
async def get_assessment_grade_distribution_view(
    assessment_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AssessmentGradeDistributionOut:
    """
    Return the formal grade distribution for an assessment.

    If the assessment has no active grading scheme, the service returns an
    empty grade distribution while preserving valid mark statistics.
    """

    result = await get_assessment_grade_distribution(
        db=db,
        current_user=current_user,
        assessment_id=assessment_id,
    )

    return AssessmentGradeDistributionOut.model_validate(
        result,
    )
