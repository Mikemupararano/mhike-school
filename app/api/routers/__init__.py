from fastapi import APIRouter
from app.api.routers.health import router as health_router
from app.api.routers.auth import router as auth_router
from app.api.routers.courses import router as courses_router

api_router = APIRouter()
api_router.include_router(health_router, prefix="/health", tags=["health"])
api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_router.include_router(courses_router, prefix="/courses", tags=["courses"])
