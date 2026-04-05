from fastapi import APIRouter

from app.api.v1.endpoints import (
    auth,
    classes,
    dashboard,
    enrollments,
    school_users,
    schools,
    courses,
    platform_admin,
    assignments,  # ✅ NEW
    assignment_submissions,  # ✅ NEW
)

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["auth"])

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
    courses.router,
    prefix="/courses",
    tags=["courses"],
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
    platform_admin.router,
    prefix="/platform-admin",
    tags=["platform-admin"],
)
