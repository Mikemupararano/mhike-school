from fastapi import APIRouter

from app.api.v1.endpoints import (
    auth,
    classes,
    dashboard,  # ✅ added
    enrollments,
    school_users,
    schools,
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

# ✅ NEW: dashboard routes
api_router.include_router(
    dashboard.router,
    prefix="/dashboard",
    tags=["dashboard"],
)
