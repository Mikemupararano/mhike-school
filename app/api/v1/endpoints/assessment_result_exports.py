from __future__ import annotations

from io import BytesIO

from fastapi import APIRouter, Depends, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    get_current_user,
    get_db,
)
from app.models.user import User
from app.services.assessment_operational_marks_export_service import (
    build_operational_assessment_marks_filename,
    get_operational_assessment_marks_export,
    render_operational_assessment_marks_csv,
)
from app.services.assessment_result_export_service import (
    build_official_assessment_results_filename,
    get_official_assessment_result_export,
    render_official_assessment_results_csv,
)
from app.services.assessment_result_pdf_export_service import (
    build_official_assessment_results_pdf_filename,
    get_official_assessment_results_pdf,
)

router = APIRouter()


# ---------------------------------------------------------------------------
# Official authoritative results CSV
# ---------------------------------------------------------------------------


@router.get(
    "/assessments/{assessment_id}/official.csv",
    response_class=Response,
)
async def export_official_assessment_results_csv(
    assessment_id: int,
    db: AsyncSession = Depends(
        get_db,
    ),
    current_user: User = Depends(
        get_current_user,
    ),
) -> Response:
    """
    Export the assessment's current official results as CSV.

    Only current authoritative AssessmentResultOutcome snapshots are included.
    """

    export = await get_official_assessment_result_export(
        db,
        current_user,
        assessment_id=assessment_id,
    )

    csv_content = render_official_assessment_results_csv(
        export,
    )

    filename = build_official_assessment_results_filename(
        export,
    )

    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={
            "Content-Disposition": (f'attachment; filename="{filename}"'),
        },
    )


# ---------------------------------------------------------------------------
# Official authoritative results PDF
# ---------------------------------------------------------------------------


@router.get(
    "/assessments/{assessment_id}/official.pdf",
)
async def export_official_assessment_results_pdf(
    assessment_id: int,
    db: AsyncSession = Depends(
        get_db,
    ),
    current_user: User = Depends(
        get_current_user,
    ),
) -> StreamingResponse:
    """
    Export the assessment's current official results as PDF.

    The PDF uses exactly the same authoritative result source as the official
    CSV export and therefore excludes live/provisional marking data.
    """

    export, pdf_bytes = await get_official_assessment_results_pdf(
        db,
        current_user,
        assessment_id=assessment_id,
    )

    filename = build_official_assessment_results_pdf_filename(
        export,
    )

    return StreamingResponse(
        BytesIO(
            pdf_bytes,
        ),
        media_type="application/pdf",
        headers={
            "Content-Disposition": (f'attachment; filename="{filename}"'),
            "Content-Length": str(
                len(
                    pdf_bytes,
                )
            ),
            "Cache-Control": "private, no-store",
        },
    )


# ---------------------------------------------------------------------------
# Operational/live marking state CSV
# ---------------------------------------------------------------------------


@router.get(
    "/assessments/{assessment_id}/operational.csv",
    response_class=Response,
)
async def export_operational_assessment_marks_csv(
    assessment_id: int,
    db: AsyncSession = Depends(
        get_db,
    ),
    current_user: User = Depends(
        get_current_user,
    ),
) -> Response:
    """
    Export the assessment's current operational marking state as CSV.

    This represents live script-level marking state and is intentionally
    separate from the immutable official-results export.
    """

    export = await get_operational_assessment_marks_export(
        db,
        current_user,
        assessment_id=assessment_id,
    )

    csv_content = render_operational_assessment_marks_csv(
        export,
    )

    filename = build_operational_assessment_marks_filename(
        export,
    )

    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={
            "Content-Disposition": (f'attachment; filename="{filename}"'),
        },
    )
