from __future__ import annotations

from fastapi import (
    APIRouter,
    Depends,
    Query,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.permissions import PermissionService
from app.db.session import get_db
from app.models.user import User
from app.schemas.assessment_results import (
    AssessmentCandidateResultOut,
    AssessmentQuestionAnalysisListOut,
    AssessmentQuestionAnalysisOut,
    AssessmentResultGridOut,
    AssessmentResultsSummaryOut,
    AssessmentScriptResultOut,
)
from app.services.assessment_results_service import (
    get_assessment_question_analysis,
    get_assessment_result_grid,
    get_assessment_results_summary,
    get_candidate_result,
    get_script_result,
)

router = APIRouter()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ensure_results_staff_access(
    current_user: User,
) -> None:
    """
    Ensure the current user may access assessment-results workflows.

    Detailed course ownership, school isolation, and teacher scope are
    enforced by the service layer.
    """

    PermissionService.ensure_active_user(
        current_user,
    )

    PermissionService.ensure_school_staff_or_platform_admin(
        current_user,
    )


# ---------------------------------------------------------------------------
# Script results
# ---------------------------------------------------------------------------


@router.get(
    "/scripts/{script_id}",
    response_model=AssessmentScriptResultOut,
)
async def get_assessment_script_result(
    script_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AssessmentScriptResultOut:
    """
    Return the complete derived result for one assessment script.

    The result includes:

    - assessment maximum mark;
    - provisional awarded mark;
    - completed awarded mark;
    - finalised awarded mark;
    - percentages;
    - response and marking completion;
    - question-level results.
    """

    _ensure_results_staff_access(
        current_user,
    )

    result = await get_script_result(
        db=db,
        current_user=current_user,
        script_id=script_id,
    )

    return AssessmentScriptResultOut.model_validate(
        result,
    )


# ---------------------------------------------------------------------------
# Candidate results
# ---------------------------------------------------------------------------


@router.get(
    "/candidates/{candidate_id}",
    response_model=AssessmentCandidateResultOut,
)
async def get_assessment_candidate_result(
    candidate_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AssessmentCandidateResultOut:
    """
    Return derived results for one assessment candidate.

    Every script version is preserved. ``latest_script_result`` is a
    convenience view rather than a replacement for script history.
    """

    _ensure_results_staff_access(
        current_user,
    )

    result = await get_candidate_result(
        db=db,
        current_user=current_user,
        candidate_id=candidate_id,
    )

    return AssessmentCandidateResultOut.model_validate(
        result,
    )


# ---------------------------------------------------------------------------
# Assessment result grid
# ---------------------------------------------------------------------------


@router.get(
    "/assessments/{assessment_id}/grid",
    response_model=AssessmentResultGridOut,
)
async def get_assessment_results_grid(
    assessment_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AssessmentResultGridOut:
    """
    Return a compact script-level result grid for an assessment.

    This endpoint is intended for teacher/admin result screens where loading
    the full question graph for every script would be unnecessarily large.
    """

    _ensure_results_staff_access(
        current_user,
    )

    result = await get_assessment_result_grid(
        db=db,
        current_user=current_user,
        assessment_id=assessment_id,
    )

    return AssessmentResultGridOut.model_validate(
        result,
    )


# ---------------------------------------------------------------------------
# Assessment-wide summary
# ---------------------------------------------------------------------------


@router.get(
    "/assessments/{assessment_id}/summary",
    response_model=AssessmentResultsSummaryOut,
)
async def get_assessment_results_summary_endpoint(
    assessment_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AssessmentResultsSummaryOut:
    """
    Return assessment-wide marking and results summary data.
    """

    _ensure_results_staff_access(
        current_user,
    )

    result = await get_assessment_results_summary(
        db=db,
        current_user=current_user,
        assessment_id=assessment_id,
    )

    return AssessmentResultsSummaryOut.model_validate(
        result,
    )


# ---------------------------------------------------------------------------
# Question-level analysis / QLA
# ---------------------------------------------------------------------------


@router.get(
    "/assessments/{assessment_id}/questions",
    response_model=AssessmentQuestionAnalysisListOut,
)
async def get_assessment_question_level_analysis(
    assessment_id: int,
    completed_only: bool = Query(
        default=True,
        description=(
            "When true, only MARKED, REVIEWED and FINALISED decisions "
            "contribute to mark statistics. When false, provisional "
            "in-progress marks are also included."
        ),
    ),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AssessmentQuestionAnalysisListOut:
    """
    Return question-level analysis for all markable assessment questions.
    """

    _ensure_results_staff_access(
        current_user,
    )

    questions = await get_assessment_question_analysis(
        db=db,
        current_user=current_user,
        assessment_id=assessment_id,
        completed_only=completed_only,
    )

    return AssessmentQuestionAnalysisListOut(
        assessment_id=assessment_id,
        completed_only=completed_only,
        questions=[
            AssessmentQuestionAnalysisOut.model_validate(
                question,
            )
            for question in questions
        ],
    )
