from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.assignment import Assignment
from app.models.class_group import ClassGroup
from app.models.enrollment import Enrollment
from app.models.user import User, UserRole, UserStatus
from app.models.user_role import UserRoleAssignment
from app.schemas.dashboard import DashboardMeOut, SchoolAdminMetricsOut


class DashboardService:
    @staticmethod
    async def get_student_dashboard(
        db: AsyncSession,
        current_user: User,
    ) -> DashboardMeOut:
        result = await db.execute(
            select(func.count(Enrollment.id)).where(
                Enrollment.user_id == current_user.id,
            )
        )

        enrolled_courses = int(result.scalar() or 0)

        return DashboardMeOut(
            student_id=current_user.id,
            full_name=current_user.full_name,
            email=current_user.email,
            role=current_user.role,
            roles=[UserRole(role) for role in current_user.roles],
            is_active=current_user.is_active,
            enrolled_courses=enrolled_courses,
            total_lessons_completed=0,
            courses=[],
        )

    @staticmethod
    async def get_school_admin_metrics(
        db: AsyncSession,
        current_user: User,
    ) -> SchoolAdminMetricsOut:
        school_id = current_user.school_id

        if school_id is None:
            return SchoolAdminMetricsOut(
                total_users=0,
                active_users=0,
                teachers=0,
                students=0,
                school_admins=0,
                classes=0,
                assignments=0,
            )

        total_users = await DashboardService._count_users(db, school_id)

        active_users = await DashboardService._count_users(
            db,
            school_id,
            active_only=True,
        )

        teachers = await DashboardService._count_users_by_role(
            db,
            school_id,
            UserRole.TEACHER,
        )

        students = await DashboardService._count_users_by_role(
            db,
            school_id,
            UserRole.STUDENT,
        )

        school_admins = await DashboardService._count_users_by_role(
            db,
            school_id,
            UserRole.SCHOOL_ADMIN,
        )

        classes_result = await db.execute(
            select(func.count(ClassGroup.id)).where(
                ClassGroup.school_id == school_id,
            )
        )

        assignments_result = await db.execute(
            select(func.count(Assignment.id)).where(
                Assignment.school_id == school_id,
            )
        )

        return SchoolAdminMetricsOut(
            total_users=total_users,
            active_users=active_users,
            teachers=teachers,
            students=students,
            school_admins=school_admins,
            classes=int(classes_result.scalar() or 0),
            assignments=int(assignments_result.scalar() or 0),
        )

    @staticmethod
    async def _count_users(
        db: AsyncSession,
        school_id: int,
        *,
        active_only: bool = False,
    ) -> int:
        query = select(func.count(User.id)).where(
            User.school_id == school_id,
        )

        if active_only:
            query = query.where(
                User.is_active.is_(True),
                User.status == UserStatus.ACTIVE,
            )

        result = await db.execute(query)
        return int(result.scalar() or 0)

    @staticmethod
    async def _count_users_by_role(
        db: AsyncSession,
        school_id: int,
        role: UserRole,
    ) -> int:
        result = await db.execute(
            select(func.count(func.distinct(User.id)))
            .join(UserRoleAssignment, UserRoleAssignment.user_id == User.id)
            .where(
                User.school_id == school_id,
                UserRoleAssignment.role == role,
                User.is_active.is_(True),
                User.status == UserStatus.ACTIVE,
            )
        )

        return int(result.scalar() or 0)
