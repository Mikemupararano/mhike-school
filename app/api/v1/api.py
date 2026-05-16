from fastapi import APIRouter

from app.api.v1.endpoints import (
    assignment_submissions,
    assignments,
    attendance,
    attendance_dashboard,
    auth,
    classes,
    courses,
    dashboard,
    enrollments,
    platform_admin,
    school_admin,
    school_users,
    schools,
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

# =========================================================
# TIMETABLES
# =========================================================

api_router.include_router(
    timetables.router,
    prefix="/timetables",
    tags=["timetables"],
)

# =========================================================
# PLATFORM ADMIN
# =========================================================

api_router.include_router(
    platform_admin.router,
    prefix="/admin",
    tags=["platform-admin"],
)
