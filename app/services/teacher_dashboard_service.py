from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.assignment import Assignment
from app.models.assignment_submission import AssignmentSubmission
from app.models.course import Course
from app.models.enrollment import Enrollment
from app.models.user import User


class TeacherDashboardService:
    @staticmethod
    async def get_teacher_dashboard(
        db: AsyncSession,
        current_user: User,
    ) -> dict:
        courses_result = await db.execute(
            select(func.count(Course.id)).where(
                Course.teacher_id == current_user.id,
            )
        )
        total_courses = int(courses_result.scalar() or 0)

        students_result = await db.execute(
            select(func.count(func.distinct(Enrollment.user_id)))
            .join(Course, Course.id == Enrollment.course_id)
            .where(Course.teacher_id == current_user.id)
        )
        total_students = int(students_result.scalar() or 0)

        assignments_result = await db.execute(
            select(func.count(Assignment.id)).where(
                Assignment.created_by == current_user.id,
            )
        )
        total_assignments = int(assignments_result.scalar() or 0)

        pending_result = await db.execute(
            select(func.count(AssignmentSubmission.id))
            .join(Assignment, Assignment.id == AssignmentSubmission.assignment_id)
            .where(
                Assignment.created_by == current_user.id,
                AssignmentSubmission.status == "submitted",
            )
        )
        pending_submissions = int(pending_result.scalar() or 0)

        return {
            "teacher_id": current_user.id,
            "total_courses": total_courses,
            "total_students": total_students,
            "total_assignments": total_assignments,
            "pending_submissions": pending_submissions,
        }
