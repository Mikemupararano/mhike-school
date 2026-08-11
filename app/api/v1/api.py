from fastapi import APIRouter

from app.api.v1.endpoints import (
    assessment_candidates,
    assessment_marking,
    assessments,
    assignment_submissions,
    assignments,
    attendance,
    attendance_analytics,
    attendance_bulk_actions,
    attendance_dashboard,
    attendance_exports,
    attendance_pdf_exports,
    attendance_registers,
    attendance_trends,
    auth,
    classes,
    courses,
    dashboard,
    enrollments,
    import_batches,
    message_attachments,
    messages,
    notification_preferences,
    notifications,
    parent_attendance,
    parent_students,
    platform_admin,
    report_group_contents,
    report_quality,
    report_sessions,
    school_admin,
    school_users,
    schools,
    student_attendance,
    student_progress,
    student_reports,
    subjects,
    teacher_dashboard,
    timetables,
)

api_router = APIRouter()


api_router.include_router(
    auth.router,
    prefix="/auth",
    tags=["auth"],
)


api_router.include_router(
    schools.router,
    prefix="/schools",
    tags=["schools"],
)


api_router.include_router(
    school_users.router,
    prefix="/school-users",
    tags=["school-users"],
)


api_router.include_router(
    school_admin.router,
    prefix="/school-admin",
    tags=["school-admin"],
)


api_router.include_router(
    classes.router,
    prefix="/classes",
    tags=["classes"],
)


api_router.include_router(
    enrollments.router,
    prefix="/enrollments",
    tags=["enrollments"],
)


api_router.include_router(
    dashboard.router,
    prefix="/dashboard",
    tags=["dashboard"],
)


api_router.include_router(
    teacher_dashboard.router,
    prefix="/teacher-dashboard",
    tags=["teacher-dashboard"],
)


api_router.include_router(
    courses.router,
    prefix="/courses",
    tags=["courses"],
)


api_router.include_router(
    subjects.router,
    prefix="/subjects",
    tags=["subjects"],
)


api_router.include_router(
    assessments.router,
    prefix="/assessments",
    tags=["assessments"],
)


api_router.include_router(
    assessment_candidates.router,
    prefix="/assessment-candidates",
    tags=["assessment-candidates"],
)


api_router.include_router(
    assessment_marking.router,
    prefix="/assessment-marking",
    tags=["assessment-marking"],
)


api_router.include_router(
    assignments.router,
    prefix="/assignments",
    tags=["assignments"],
)


api_router.include_router(
    assignment_submissions.router,
    prefix="/assignment-submissions",
    tags=["assignment-submissions"],
)


api_router.include_router(
    attendance.router,
    prefix="/attendance",
    tags=["attendance"],
)


api_router.include_router(
    attendance_dashboard.router,
    prefix="/attendance-dashboard",
    tags=["attendance-dashboard"],
)


api_router.include_router(
    attendance_analytics.router,
    prefix="/attendance-analytics",
    tags=["attendance-analytics"],
)


api_router.include_router(
    attendance_registers.router,
    prefix="/attendance-registers",
    tags=["attendance-registers"],
)


api_router.include_router(
    attendance_exports.router,
    prefix="/attendance-exports",
    tags=["attendance-exports"],
)


api_router.include_router(
    attendance_pdf_exports.router,
    prefix="/attendance-pdf-exports",
    tags=["attendance-pdf-exports"],
)


api_router.include_router(
    attendance_trends.router,
    prefix="/attendance-trends",
    tags=["attendance-trends"],
)


api_router.include_router(
    attendance_bulk_actions.router,
    prefix="/attendance-bulk-actions",
    tags=["attendance-bulk-actions"],
)


api_router.include_router(
    student_attendance.router,
    prefix="/student-attendance",
    tags=["student-attendance"],
)


api_router.include_router(
    parent_attendance.router,
    prefix="/parent-attendance",
    tags=["parent-attendance"],
)


api_router.include_router(
    parent_students.router,
    prefix="/parent-students",
    tags=["parent-students"],
)


api_router.include_router(
    student_reports.router,
    prefix="/student-reports",
    tags=["student-reports"],
)


api_router.include_router(
    report_sessions.router,
    prefix="/report-sessions",
    tags=["report-sessions"],
)


api_router.include_router(
    report_group_contents.router,
    prefix="/report-group-contents",
    tags=["report-group-contents"],
)


api_router.include_router(
    report_quality.router,
    prefix="/report-quality",
    tags=["report-quality"],
)


api_router.include_router(
    student_progress.router,
    prefix="/student-progress",
    tags=["student-progress"],
)


api_router.include_router(
    timetables.router,
    prefix="/timetables",
    tags=["timetables"],
)


api_router.include_router(
    notification_preferences.router,
    prefix="/notification-preferences",
    tags=["notification-preferences"],
)


api_router.include_router(
    notifications.router,
    prefix="/notifications",
    tags=["notifications"],
)


api_router.include_router(
    messages.router,
    prefix="/messages",
    tags=["messages"],
)


api_router.include_router(
    message_attachments.router,
    prefix="/message-attachments",
    tags=["message-attachments"],
)


api_router.include_router(
    import_batches.router,
)


api_router.include_router(
    platform_admin.router,
    prefix="/admin",
    tags=["platform-admin"],
)
