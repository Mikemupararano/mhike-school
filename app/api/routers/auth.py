from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.security import create_access_token, hash_password, verify_password
from app.db.session import get_db
from app.models import School, User
from app.schemas.auth import LoginIn, RegisterIn, TokenOut
from app.schemas.user import UserOut

router = APIRouter()


@router.post("/register", response_model=UserOut)
async def register(payload: RegisterIn, db: AsyncSession = Depends(get_db)):
    email = payload.email.strip().lower()

    school = await db.get(School, payload.school_id)
    if not school:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="School not found",
        )

    exists = await db.execute(
        select(User).where(
            User.email == email,
            User.school_id == payload.school_id,
        )
    )
    if exists.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered for this school",
        )

    user = User(
        email=email,
        hashed_password=hash_password(payload.password),
        school_id=payload.school_id,
        role=payload.role or "student",
        full_name=payload.full_name,
        is_active=True,
    )

    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@router.post("/login", response_model=TokenOut)
async def login(payload: LoginIn, db: AsyncSession = Depends(get_db)):
    email = payload.email.strip().lower()

    school = await db.get(School, payload.school_id)
    if not school:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="School not found",
        )

    res = await db.execute(
        select(User).where(
            User.email == email,
            User.school_id == payload.school_id,
        )
    )
    user = res.scalar_one_or_none()

    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    if user.is_active is False:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive",
        )

    token = create_access_token(
        subject=str(user.id),
        school_id=user.school_id,
    )

    return TokenOut(access_token=token, token_type="bearer")


@router.get("/me")
async def auth_me(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "full_name": current_user.full_name,
        "email": current_user.email,
        "role": current_user.role,
        "school_id": current_user.school_id,
        "is_active": current_user.is_active,
    }
