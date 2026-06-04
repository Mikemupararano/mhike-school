from __future__ import annotations

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.assignment import Assignment
from app.models.assignment_submission import AssignmentSubmission
from app.models.attendance_record import AttendanceRecord
from app.models.student_report import StudentReport
from app.schemas.student_progress import StudentProgressSummary


async def get_student_progress_summary(
    db: AsyncSession,
    *,
    student_id: int,
    school_id: int,
) -> StudentProgressSummary:
    attendance_result = await db.execute(
        select(
            func.count(AttendanceRecord.id),
            func.sum(
                case(
                    (
                        AttendanceRecord.status.in_(
                            [
                                "present",
                                "late",
                            ],
                        ),
                        1,
                    ),
                    else_=0,
                ),
            ),
        ).where(
            AttendanceRecord.student_id == student_id,
        ),
    )

    total_attendance, positive_attendance = attendance_result.one()

    total_attendance = total_attendance or 0
    positive_attendance = positive_attendance or 0

    attendance_percentage = (
        round((positive_attendance / total_attendance) * 100, 2)
        if total_attendance > 0
        else 0.0
    )

    assignment_result = await db.execute(
        select(
            func.count(AssignmentSubmission.id),
            func.avg(
                (AssignmentSubmission.score * 100.0) / Assignment.max_score,
            ),
        )
        .join(
            Assignment,
            Assignment.id == AssignmentSubmission.assignment_id,
        )
        .where(
            AssignmentSubmission.student_id == student_id,
            AssignmentSubmission.school_id == school_id,
            AssignmentSubmission.score.is_not(None),
            Assignment.max_score > 0,
        ),
    )

    assignments_completed, average_assignment_score = assignment_result.one()

    feedback_result = await db.execute(
        select(func.count(AssignmentSubmission.id)).where(
            AssignmentSubmission.student_id == student_id,
            AssignmentSubmission.school_id == school_id,
            AssignmentSubmission.feedback.is_not(None),
            AssignmentSubmission.feedback != "",
        ),
    )

    recent_feedback_count = feedback_result.scalar_one() or 0

    report_count_result = await db.execute(
        select(func.count(StudentReport.id)).where(
            StudentReport.student_id == student_id,
            StudentReport.school_id == school_id,
        ),
    )

    report_count = report_count_result.scalar_one() or 0

    latest_report_result = await db.execute(
        select(StudentReport.title)
        .where(
            StudentReport.student_id == student_id,
            StudentReport.school_id == school_id,
        )
        .order_by(StudentReport.created_at.desc())
        .limit(1),
    )

    latest_report_title = latest_report_result.scalar_one_or_none()

    return StudentProgressSummary(
        student_id=student_id,
        attendance_percentage=attendance_percentage,
        assignments_completed=assignments_completed or 0,
        average_assignment_score=(
            round(float(average_assignment_score), 2)
            if average_assignment_score is not None
            else None
        ),
        report_count=report_count,
        latest_report_title=latest_report_title,
        recent_feedback_count=recent_feedback_count,
    )
