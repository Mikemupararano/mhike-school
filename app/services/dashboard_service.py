from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enrollment import Enrollment
from app.models.user import User
from app.schemas.dashboard import DashboardMeOut


class DashboardService:
    @staticmethod
    async def get_student_dashboard(
        db: AsyncSession,
        current_user: User,
    ) -> DashboardMeOut:
        result = await db.execute(
            select(func.count()).where(
                Enrollment.user_id == current_user.id,
            )
        )
        enrolled_courses = result.scalar() or 0

        return DashboardMeOut(
            student_id=current_user.id,
            full_name=current_user.full_name,
            email=current_user.email,
            role=current_user.role,
            is_active=current_user.is_active,
            enrolled_courses=enrolled_courses,
            total_lessons_completed=0,
            courses=[],
        )
