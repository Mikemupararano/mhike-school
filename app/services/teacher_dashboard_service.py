from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.assignment import Assignment
from app.models.assignment_submission import AssignmentSubmission
from app.models.course import Course
from app.models.enrollment import Enrollment
from app.models.user import User
from app.schemas.teacher_dashboard import TeacherCourseOut, TeacherDashboardOut


class TeacherDashboardService:
    @staticmethod
    async def get_teacher_dashboard(
        db: AsyncSession,
        current_user: User,
    ) -> TeacherDashboardOut:
        courses_result = await db.execute(
            select(func.count(Course.id)).where(Course.teacher_id == current_user.id)
        )

        students_result = await db.execute(
            select(func.count(func.distinct(Enrollment.user_id)))
            .join(Course, Course.id == Enrollment.course_id)
            .where(Course.teacher_id == current_user.id)
        )

        assignments_result = await db.execute(
            select(func.count(Assignment.id)).where(
                Assignment.created_by == current_user.id
            )
        )

        pending_result = await db.execute(
            select(func.count(AssignmentSubmission.id))
            .join(Assignment, Assignment.id == AssignmentSubmission.assignment_id)
            .where(
                Assignment.created_by == current_user.id,
                AssignmentSubmission.status == "submitted",
            )
        )

        return TeacherDashboardOut(
            teacher_id=current_user.id,
            total_courses=int(courses_result.scalar() or 0),
            total_students=int(students_result.scalar() or 0),
            total_assignments=int(assignments_result.scalar() or 0),
            pending_submissions=int(pending_result.scalar() or 0),
        )

    @staticmethod
    async def list_teacher_courses(
        db: AsyncSession,
        current_user: User,
    ) -> list[TeacherCourseOut]:
        result = await db.execute(
            select(
                Course.id,
                Course.title,
                func.count(func.distinct(Enrollment.user_id)).label("students"),
                func.count(func.distinct(Assignment.id)).label("assignments"),
            )
            .outerjoin(Enrollment, Enrollment.course_id == Course.id)
            .outerjoin(Assignment, Assignment.course_id == Course.id)
            .where(Course.teacher_id == current_user.id)
            .group_by(Course.id, Course.title)
            .order_by(Course.title.asc())
        )

        return [
            TeacherCourseOut(
                id=row.id,
                title=row.title,
                students=int(row.students or 0),
                assignments=int(row.assignments or 0),
            )
            for row in result.all()
        ]
