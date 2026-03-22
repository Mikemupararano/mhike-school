from fastapi import APIRouter

from app.api.routers.admin import router as admin_router
from app.api.routers.auth import router as auth_router
from app.api.routers.courses import router as courses_router
from app.api.routers.dashboard import router as dashboard_router
from app.api.routers.health import router as health_router
from app.api.routers.lessons import router as lessons_router
from app.api.routers.modules import router as modules_router
from app.api.routers.progress import router as progress_router
from app.api.routers.quiz import router as quiz_router

api_router = APIRouter()

api_router.include_router(health_router, prefix="/health", tags=["health"])
api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_router.include_router(courses_router, prefix="/courses", tags=["courses"])

api_router.include_router(modules_router, tags=["modules"])
api_router.include_router(lessons_router, tags=["lessons"])
api_router.include_router(progress_router, tags=["progress"])
api_router.include_router(quiz_router, tags=["quiz"])

api_router.include_router(dashboard_router, prefix="/dashboard", tags=["dashboard"])

# ✅ Admin router (already has prefix="/admin" internally)
api_router.include_router(admin_router)
