from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_role
from app.db.session import get_db
from app.models.user import User, UserRole
from app.schemas.teacher_dashboard import TeacherDashboardOut
from app.services.teacher_dashboard_service import TeacherDashboardService

router = APIRouter()


@router.get("/me", response_model=TeacherDashboardOut)
async def get_teacher_dashboard(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(
        require_role(
            UserRole.TEACHER,
            UserRole.SCHOOL_ADMIN,
            UserRole.PLATFORM_ADMIN,
        )
    ),
):
    return await TeacherDashboardService.get_teacher_dashboard(
        db=db,
        current_user=current_user,
    )
