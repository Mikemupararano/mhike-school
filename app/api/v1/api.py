from fastapi import APIRouter

from app.api.v1.endpoints import auth, schools, school_users

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(schools.router, prefix="/schools", tags=["schools"])
api_router.include_router(
    school_users.router,
    prefix="/school-users",
    tags=["school-users"],
)
