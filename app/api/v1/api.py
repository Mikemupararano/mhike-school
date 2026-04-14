from fastapi import APIRouter

from app.api.v1.endpoints import (
    auth,
    classes,
    dashboard,
    enrollments,
    school_users,
    school_admin,  # ✅ NEW (important)
    schools,
    courses,
    platform_admin,
    assignments,
    assignment_submissions,
)

api_router = APIRouter()


# 🔐 AUTH
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])


# 🏫 SCHOOL CORE
api_router.include_router(schools.router, prefix="/schools", tags=["schools"])


# 👥 SCHOOL USERS (legacy / internal)
api_router.include_router(
    school_users.router,
    prefix="/school-users",
    tags=["school-users"],
)


# 🏫 SCHOOL ADMIN (🔥 MAIN USER MANAGEMENT)
api_router.include_router(
    school_admin.router,
    prefix="/school-admin",
    tags=["school-admin"],
)


# 🧑‍🏫 CLASSES & ENROLLMENT
api_router.include_router(classes.router, prefix="/classes", tags=["classes"])

api_router.include_router(
    enrollments.router,
    prefix="/enrollments",
    tags=["enrollments"],
)


# 📊 DASHBOARD
api_router.include_router(
    dashboard.router,
    prefix="/dashboard",
    tags=["dashboard"],
)


# 📚 COURSES
api_router.include_router(
    courses.router,
    prefix="/courses",
    tags=["courses"],
)


# 📝 ASSIGNMENTS
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


# 🌍 PLATFORM ADMIN
api_router.include_router(
    platform_admin.router,
    prefix="/platform-admin",
    tags=["platform-admin"],
)
