from __future__ import annotations

from fastapi import (
    APIRouter,
    Depends,
    Query,
    Response,
    status,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.permissions import PermissionService
from app.db.session import get_db
from app.models.user import User
from app.schemas.assessment_grading import (
    AssessmentCandidateGradeOut,
    AssessmentGradeBoundaryCreate,
    AssessmentGradeBoundaryListOut,
    AssessmentGradeBoundaryOut,
    AssessmentGradeBoundaryUpdate,
    AssessmentGradeResolutionOut,
    AssessmentGradeResolveRequest,
    AssessmentGradingSchemeCreate,
    AssessmentGradingSchemeOut,
    AssessmentGradingSchemeUpdate,
    AssessmentScriptGradeOut,
)
from app.services.assessment_grading_service import (
    create_grade_boundary,
    create_grading_scheme,
    delete_grade_boundary,
    delete_grading_scheme,
    get_grading_scheme,
    grade_candidate_latest_result,
    grade_script_result,
    list_grade_boundaries,
    resolve_grade,
    update_grade_boundary,
    update_grading_scheme,
)

router = APIRouter()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ensure_grading_staff_access(
    current_user: User,
) -> None:
    """
    Ensure the current user may access assessment grading workflows.

    Detailed course ownership, school isolation, and teacher/admin scope
    remain enforced by the grading/results service layer.
    """

    PermissionService.ensure_active_user(
        current_user,
    )

    PermissionService.ensure_school_staff_or_platform_admin(
        current_user,
    )


def _scheme_update_kwargs(
    payload: AssessmentGradingSchemeUpdate,
) -> dict[str, object]:
    """
    Build keyword arguments while preserving explicitly supplied nulls.
    """

    output: dict[str, object] = {}

    if "name" in payload.model_fields_set:
        output["name"] = payload.name

    if "description" in payload.model_fields_set:
        output["description"] = payload.description

    if "basis" in payload.model_fields_set:
        output["basis"] = payload.basis

    if "is_active" in payload.model_fields_set:
        output["is_active"] = payload.is_active

    return output


def _boundary_update_kwargs(
    payload: AssessmentGradeBoundaryUpdate,
) -> dict[str, object]:
    """
    Build boundary update arguments while preserving explicit null values.
    """

    output: dict[str, object] = {}

    if "grade_label" in payload.model_fields_set:
        output["grade_label"] = payload.grade_label

    if "minimum_value" in payload.model_fields_set:
        output["minimum_value"] = payload.minimum_value

    if "order" in payload.model_fields_set:
        output["order"] = payload.order

    if "description" in payload.model_fields_set:
        output["description"] = payload.description

    if "grade_points" in payload.model_fields_set:
        output["grade_points"] = payload.grade_points

    if "is_pass" in payload.model_fields_set:
        output["is_pass"] = payload.is_pass

    return output


# ---------------------------------------------------------------------------
# Grading schemes
# ---------------------------------------------------------------------------


@router.post(
    "/assessments/{assessment_id}/scheme",
    response_model=AssessmentGradingSchemeOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_assessment_grading_scheme(
    assessment_id: int,
    payload: AssessmentGradingSchemeCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AssessmentGradingSchemeOut:
    """
    Create the grading scheme for an assessment.

    An assessment may currently have at most one grading scheme.
    """

    _ensure_grading_staff_access(
        current_user,
    )

    scheme = await create_grading_scheme(
        db=db,
        current_user=current_user,
        assessment_id=assessment_id,
        name=payload.name,
        basis=payload.basis,
        description=payload.description,
        is_active=payload.is_active,
    )

    return AssessmentGradingSchemeOut.model_validate(
        scheme,
    )


@router.get(
    "/assessments/{assessment_id}/scheme",
    response_model=AssessmentGradingSchemeOut,
)
async def get_assessment_grading_scheme(
    assessment_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AssessmentGradingSchemeOut:
    """
    Return the grading scheme configured for an assessment.
    """

    _ensure_grading_staff_access(
        current_user,
    )

    scheme = await get_grading_scheme(
        db=db,
        current_user=current_user,
        assessment_id=assessment_id,
    )

    return AssessmentGradingSchemeOut.model_validate(
        scheme,
    )


@router.patch(
    "/schemes/{scheme_id}",
    response_model=AssessmentGradingSchemeOut,
)
async def update_assessment_grading_scheme(
    scheme_id: int,
    payload: AssessmentGradingSchemeUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AssessmentGradingSchemeOut:
    """
    Update an assessment grading scheme.
    """

    _ensure_grading_staff_access(
        current_user,
    )

    scheme = await update_grading_scheme(
        db=db,
        current_user=current_user,
        scheme_id=scheme_id,
        **_scheme_update_kwargs(payload),
    )

    return AssessmentGradingSchemeOut.model_validate(
        scheme,
    )


@router.delete(
    "/schemes/{scheme_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_assessment_grading_scheme(
    scheme_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    """
    Delete an assessment grading scheme and all of its boundaries.
    """

    _ensure_grading_staff_access(
        current_user,
    )

    await delete_grading_scheme(
        db=db,
        current_user=current_user,
        scheme_id=scheme_id,
    )

    return Response(
        status_code=status.HTTP_204_NO_CONTENT,
    )


# ---------------------------------------------------------------------------
# Grade boundaries
# ---------------------------------------------------------------------------


@router.get(
    "/schemes/{scheme_id}/boundaries",
    response_model=AssessmentGradeBoundaryListOut,
)
async def get_assessment_grade_boundaries(
    scheme_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AssessmentGradeBoundaryListOut:
    """
    Return all boundaries for a grading scheme in grading order.
    """

    _ensure_grading_staff_access(
        current_user,
    )

    boundaries = await list_grade_boundaries(
        db=db,
        current_user=current_user,
        scheme_id=scheme_id,
    )

    return AssessmentGradeBoundaryListOut(
        grading_scheme_id=scheme_id,
        boundaries=[
            AssessmentGradeBoundaryOut.model_validate(
                boundary,
            )
            for boundary in boundaries
        ],
    )


@router.post(
    "/schemes/{scheme_id}/boundaries",
    response_model=AssessmentGradeBoundaryOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_assessment_grade_boundary(
    scheme_id: int,
    payload: AssessmentGradeBoundaryCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AssessmentGradeBoundaryOut:
    """
    Create one inclusive grade boundary.
    """

    _ensure_grading_staff_access(
        current_user,
    )

    boundary = await create_grade_boundary(
        db=db,
        current_user=current_user,
        scheme_id=scheme_id,
        grade_label=payload.grade_label,
        minimum_value=payload.minimum_value,
        order=payload.order,
        description=payload.description,
        grade_points=payload.grade_points,
        is_pass=payload.is_pass,
    )

    return AssessmentGradeBoundaryOut.model_validate(
        boundary,
    )


@router.patch(
    "/boundaries/{boundary_id}",
    response_model=AssessmentGradeBoundaryOut,
)
async def update_assessment_grade_boundary(
    boundary_id: int,
    payload: AssessmentGradeBoundaryUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AssessmentGradeBoundaryOut:
    """
    Update one grade boundary.
    """

    _ensure_grading_staff_access(
        current_user,
    )

    boundary = await update_grade_boundary(
        db=db,
        current_user=current_user,
        boundary_id=boundary_id,
        **_boundary_update_kwargs(payload),
    )

    return AssessmentGradeBoundaryOut.model_validate(
        boundary,
    )


@router.delete(
    "/boundaries/{boundary_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_assessment_grade_boundary(
    boundary_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    """
    Delete one grade boundary.
    """

    _ensure_grading_staff_access(
        current_user,
    )

    await delete_grade_boundary(
        db=db,
        current_user=current_user,
        boundary_id=boundary_id,
    )

    return Response(
        status_code=status.HTTP_204_NO_CONTENT,
    )


# ---------------------------------------------------------------------------
# Explicit grade resolution
# ---------------------------------------------------------------------------


@router.post(
    "/assessments/{assessment_id}/resolve",
    response_model=AssessmentGradeResolutionOut,
)
async def resolve_assessment_grade(
    assessment_id: int,
    payload: AssessmentGradeResolveRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AssessmentGradeResolutionOut:
    """
    Resolve an explicit value against the active assessment grading scheme.
    """

    _ensure_grading_staff_access(
        current_user,
    )

    result = await resolve_grade(
        db=db,
        current_user=current_user,
        assessment_id=assessment_id,
        value=payload.value,
    )

    return AssessmentGradeResolutionOut.model_validate(
        result,
    )


# ---------------------------------------------------------------------------
# Script-derived grades
# ---------------------------------------------------------------------------


@router.get(
    "/scripts/{script_id}",
    response_model=AssessmentScriptGradeOut,
)
async def get_assessment_script_grade(
    script_id: int,
    result_stage: str = Query(
        default="finalised",
        description=(
            "Assessment-result stage used to derive the grade: "
            "current, completed, or finalised."
        ),
    ),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AssessmentScriptGradeOut:
    """
    Grade one script using the assessment's active grading scheme.
    """

    _ensure_grading_staff_access(
        current_user,
    )

    result = await grade_script_result(
        db=db,
        current_user=current_user,
        script_id=script_id,
        result_stage=result_stage,
    )

    return AssessmentScriptGradeOut.model_validate(
        result,
    )


# ---------------------------------------------------------------------------
# Candidate-derived grades
# ---------------------------------------------------------------------------


@router.get(
    "/candidates/{candidate_id}",
    response_model=AssessmentCandidateGradeOut,
)
async def get_assessment_candidate_grade(
    candidate_id: int,
    result_stage: str = Query(
        default="finalised",
        description=(
            "Assessment-result stage used to derive the grade: "
            "current, completed, or finalised."
        ),
    ),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AssessmentCandidateGradeOut:
    """
    Grade the candidate's latest assessment script.
    """

    _ensure_grading_staff_access(
        current_user,
    )

    result = await grade_candidate_latest_result(
        db=db,
        current_user=current_user,
        candidate_id=candidate_id,
        result_stage=result_stage,
    )

    return AssessmentCandidateGradeOut.model_validate(
        result,
    )
