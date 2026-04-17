from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.security import create_access_token, get_password_hash, verify_password
from app.models.school import School
from app.models.user import User, UserRole, UserStatus
from app.models.user_role import UserRoleAssignment
from app.schemas.auth import LoginIn, RegisterIn, TokenOut


class AuthService:
    @staticmethod
    def _normalise_role(role: str | None) -> UserRole:
        normalized_role = (role or UserRole.STUDENT.value).strip().lower()

        # Backward compatibility
        if normalized_role == "admin":
            normalized_role = UserRole.SCHOOL_ADMIN.value

        try:
            return UserRole(normalized_role)
        except ValueError as exc:
            raise ValueError("Invalid role.") from exc

    @staticmethod
    async def register(db: AsyncSession, payload: RegisterIn) -> User:
        normalized_email = payload.email.strip().lower()
        primary_role = AuthService._normalise_role(
            payload.role.value if hasattr(payload.role, "value") else payload.role
        )

        school_id: int | None = None

        if primary_role != UserRole.PLATFORM_ADMIN:
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
            role=primary_role,  # legacy column kept for Option A
            school_id=school_id,
            is_active=True,
            status=UserStatus.ACTIVE,
        )

        db.add(user)
        await db.flush()

        db.add(
            UserRoleAssignment(
                user_id=user.id,
                role=primary_role,
            )
        )

        try:
            await db.commit()
        except Exception:
            await db.rollback()
            raise

        result = await db.execute(
            select(User)
            .options(selectinload(User.user_roles), selectinload(User.school))
            .where(User.id == user.id)
        )
        return result.scalar_one()

    @staticmethod
    async def login(db: AsyncSession, payload: LoginIn) -> TokenOut:
        normalized_email = payload.email.strip().lower()

        query = (
            select(User)
            .options(selectinload(User.user_roles), selectinload(User.school))
            .where(User.email == normalized_email)
        )

        if payload.school_id is None:
            query = query.where(
                User.school_id.is_(None),
                User.role == UserRole.PLATFORM_ADMIN,
            )
        else:
            query = query.where(User.school_id == payload.school_id)

        res = await db.execute(query)
        user = res.scalar_one_or_none()

        if (
            not user
            or not user.hashed_password
            or not verify_password(payload.password, user.hashed_password)
        ):
            raise ValueError("Invalid credentials.")

        if not user.is_active or user.status in {
            UserStatus.DEACTIVATED,
            UserStatus.ANONYMISED,
        }:
            raise ValueError("User account is inactive.")

        token = create_access_token(
            data={
                "sub": str(user.id),
                "school_id": user.school_id,
                "role": (
                    user.role.value if hasattr(user.role, "value") else str(user.role)
                ),
                "roles": user.roles,
            }
        )

        return TokenOut(
            access_token=token,
            token_type="bearer",
        )
