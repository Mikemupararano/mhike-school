from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models import School, User
from app.schemas.auth import LoginIn, RegisterIn, TokenOut
from app.schemas.user import UserOut
from app.services.auth_service import AuthService

router = APIRouter()


async def _resolve_school_name(db: AsyncSession, school_id: int | None) -> str | None:
    if not school_id:
        return None

    school = await db.get(School, school_id)
    return school.name if school else None


@router.post("/register", response_model=UserOut)
async def register(payload: RegisterIn, db: AsyncSession = Depends(get_db)):
    try:
        user = await AuthService.register(db, payload)
        school_name = await _resolve_school_name(db, user.school_id)

        return {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role,
            "school_id": user.school_id,
            "school_name": school_name,
            "is_active": user.is_active,
            "created_at": user.created_at,
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/login", response_model=TokenOut)
async def login(payload: LoginIn, db: AsyncSession = Depends(get_db)):
    try:
        return await AuthService.login(db, payload)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        )


@router.get("/me", response_model=UserOut)
async def me(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    school_name = await _resolve_school_name(db, current_user.school_id)

    return {
        "id": current_user.id,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "role": current_user.role,
        "school_id": current_user.school_id,
        "school_name": school_name,
        "is_active": current_user.is_active,
        "created_at": current_user.created_at,
    }
