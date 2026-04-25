from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_role
from app.db.session import get_db
from app.models.user import User, UserRole
from app.schemas.dashboard import DashboardMeOut, SchoolAdminMetricsOut
from app.services.dashboard_service import DashboardService

router = APIRouter()


@router.get("/me", response_model=DashboardMeOut)
async def get_dashboard(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await DashboardService.get_student_dashboard(db, current_user)


@router.get("/school-admin/metrics", response_model=SchoolAdminMetricsOut)
async def get_school_admin_metrics(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(
        require_role(UserRole.SCHOOL_ADMIN, UserRole.PLATFORM_ADMIN)
    ),
):
    return await DashboardService.get_school_admin_metrics(db, current_user)
