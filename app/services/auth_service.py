from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, get_password_hash, verify_password
from app.models.school import School
from app.models.user import User
from app.schemas.auth import LoginIn, RegisterIn, TokenOut


class AuthService:
    @staticmethod
    async def register(db: AsyncSession, payload: RegisterIn) -> User:
        if payload.role != "platform_admin":
            if not payload.school_id:
                raise ValueError("school_id is required for non-platform users.")

            res = await db.execute(select(School).where(School.id == payload.school_id))
            school = res.scalar_one_or_none()

            if not school:
                raise ValueError("School not found.")

        res = await db.execute(
            select(User).where(
                User.email == payload.email,
                User.school_id == payload.school_id,
            )
        )
        existing_user = res.scalar_one_or_none()

        if existing_user:
            raise ValueError("A user with this email already exists for this school.")

        user = User(
            email=payload.email,
            hashed_password=get_password_hash(payload.password),
            full_name=payload.full_name,
            role=payload.role,
            school_id=payload.school_id if payload.role != "platform_admin" else None,
            is_active=True,
        )

        db.add(user)
        await db.commit()
        await db.refresh(user)

        return user

    @staticmethod
    async def login(db: AsyncSession, payload: LoginIn) -> TokenOut:
        res = await db.execute(
            select(User).where(
                User.email == payload.email,
                User.school_id == payload.school_id,
            )
        )
        user = res.scalar_one_or_none()

        if not user or not verify_password(payload.password, user.hashed_password):
            raise ValueError("Invalid credentials.")

        if not user.is_active:
            raise ValueError("User account is inactive.")

        token = create_access_token(
            subject=str(user.id),
            school_id=user.school_id,
        )

        return TokenOut(
            access_token=token,
            token_type="bearer",
        )
