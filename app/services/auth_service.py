from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, get_password_hash, verify_password
from app.models.school import School
from app.models.user import User
from app.schemas.auth import LoginIn, RegisterIn, TokenOut


class AuthService:
    @staticmethod
    async def register(db: AsyncSession, payload: RegisterIn) -> User:
        normalized_email = payload.email.strip().lower()
        normalized_role = (payload.role or "student").strip().lower()

        allowed_roles = {"student", "teacher", "admin", "platform_admin"}
        if normalized_role not in allowed_roles:
            raise ValueError("Invalid role.")

        school_id: int | None = None

        if normalized_role != "platform_admin":
            if not payload.school_id:
                raise ValueError("school_id is required for non-platform users.")

            res = await db.execute(select(School).where(School.id == payload.school_id))
            school = res.scalar_one_or_none()

            if not school:
                raise ValueError("School not found.")

            school_id = school.id

        res = await db.execute(
            select(User).where(
                User.email == normalized_email,
                User.school_id == school_id,
            )
        )
        existing_user = res.scalar_one_or_none()

        if existing_user:
            raise ValueError("A user with this email already exists for this school.")

        user = User(
            email=normalized_email,
            hashed_password=get_password_hash(payload.password),
            full_name=payload.full_name.strip() if payload.full_name else None,
            role=normalized_role,
            school_id=school_id,
            is_active=True,
        )

        db.add(user)

        try:
            await db.commit()
        except Exception:
            await db.rollback()
            raise

        await db.refresh(user)
        return user

    @staticmethod
    async def login(db: AsyncSession, payload: LoginIn) -> TokenOut:
        normalized_email = payload.email.strip().lower()

        # Platform admin login: no school_id required
        if payload.school_id is None:
            res = await db.execute(
                select(User).where(
                    User.email == normalized_email,
                    User.school_id.is_(None),
                    User.role == "platform_admin",
                )
            )
            user = res.scalar_one_or_none()
        else:
            res = await db.execute(
                select(User).where(
                    User.email == normalized_email,
                    User.school_id == payload.school_id,
                )
            )
            user = res.scalar_one_or_none()

        if not user or not verify_password(payload.password, user.hashed_password):
            raise ValueError("Invalid credentials.")

        if not user.is_active:
            raise ValueError("User account is inactive.")

        token = create_access_token(
            data={
                "sub": str(user.id),
                "school_id": user.school_id,
                "role": user.role,
            }
        )

        return TokenOut(
            access_token=token,
            token_type="bearer",
        )
