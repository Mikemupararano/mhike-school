from fastapi import APIRouter

from app.api.v1.endpoints import (
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
    notification_preferences,
    parent_attendance,
    parent_students,
    platform_admin,
    school_admin,
    school_users,
    schools,
    student_attendance,
    teacher_dashboard,
    timetables,
)

api_router = APIRouter()

# =========================================================
# AUTH
# =========================================================

api_router.include_router(
    auth.router,
    prefix="/auth",
    tags=["auth"],
)

# =========================================================
# SCHOOL CORE
# =========================================================

api_router.include_router(
    schools.router,
    prefix="/schools",
    tags=["schools"],
)

# =========================================================
# SCHOOL USERS
# =========================================================

api_router.include_router(
    school_users.router,
    prefix="/school-users",
    tags=["school-users"],
)

# =========================================================
# SCHOOL ADMIN
# =========================================================

api_router.include_router(
    school_admin.router,
    prefix="/school-admin",
    tags=["school-admin"],
)

# =========================================================
# CLASSES & ENROLLMENTS
# =========================================================

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

# =========================================================
# DASHBOARDS
# =========================================================

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

# =========================================================
# COURSES
# =========================================================

api_router.include_router(
    courses.router,
    prefix="/courses",
    tags=["courses"],
)

# =========================================================
# ASSIGNMENTS
# =========================================================

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

# =========================================================
# ATTENDANCE
# =========================================================

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

# =========================================================
# TIMETABLES
# =========================================================

api_router.include_router(
    timetables.router,
    prefix="/timetables",
    tags=["timetables"],
)

# =========================================================
# NOTIFICATION PREFERENCES
# =========================================================

api_router.include_router(
    notification_preferences.router,
    prefix="/notification-preferences",
    tags=["notification-preferences"],
)

# =========================================================
# PLATFORM ADMIN
# =========================================================

api_router.include_router(
    platform_admin.router,
    prefix="/admin",
    tags=["platform-admin"],
)
