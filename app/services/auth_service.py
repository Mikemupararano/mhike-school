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
    def _normalise_role(role: str | UserRole | None) -> UserRole:
        raw_role = role.value if isinstance(role, UserRole) else role
        normalised_role = (raw_role or UserRole.STUDENT.value).strip().lower()

        # Backward compatibility
        if normalised_role == "admin":
            normalised_role = UserRole.SCHOOL_ADMIN.value

        try:
            return UserRole(normalised_role)
        except ValueError as exc:
            raise ValueError("Invalid role.") from exc

    @staticmethod
    def _normalise_roles(
        role: str | UserRole | None = None,
        roles: list[str | UserRole] | None = None,
    ) -> list[UserRole]:
        """
        Supports both old single-role payloads and new multi-role payloads.

        Examples:
        - role="teacher" -> ["teacher"]
        - roles=["school_admin", "teacher"] -> ["school_admin", "teacher"]
        """
        raw_roles = roles if roles else [role or UserRole.STUDENT]

        normalised_roles: list[UserRole] = []
        seen: set[UserRole] = set()

        for raw_role in raw_roles:
            normalised_role = AuthService._normalise_role(raw_role)

            if normalised_role not in seen:
                normalised_roles.append(normalised_role)
                seen.add(normalised_role)

        return normalised_roles

    @staticmethod
    def _get_primary_role(roles: list[UserRole]) -> UserRole:
        """
        Legacy users.role compatibility.

        Priority matters because users.role can only store one role.
        """
        priority = [
            UserRole.PLATFORM_ADMIN,
            UserRole.SCHOOL_ADMIN,
            UserRole.TEACHER,
            UserRole.STUDENT,
        ]

        for role in priority:
            if role in roles:
                return role

        return UserRole.STUDENT

    @staticmethod
    def _validate_role_school_rules(
        roles: list[UserRole],
        school_id: int | None,
    ) -> None:
        has_platform_admin = UserRole.PLATFORM_ADMIN in roles
        has_school_role = any(
            role in roles
            for role in {
                UserRole.SCHOOL_ADMIN,
                UserRole.TEACHER,
                UserRole.STUDENT,
            }
        )

        if has_platform_admin and has_school_role:
            raise ValueError("platform_admin cannot be combined with school roles.")

        if has_platform_admin and school_id is not None:
            raise ValueError("platform_admin must not belong to a school.")

        if has_school_role and school_id is None:
            raise ValueError("school_id is required for school users.")

    @staticmethod
    async def register(db: AsyncSession, payload: RegisterIn) -> User:
        normalised_email = payload.email.strip().lower()

        requested_roles = AuthService._normalise_roles(
            role=getattr(payload, "role", None),
            roles=getattr(payload, "roles", None),
        )

        school_id = payload.school_id
        AuthService._validate_role_school_rules(requested_roles, school_id)

        if school_id is not None:
            result = await db.execute(select(School).where(School.id == school_id))
            school = result.scalar_one_or_none()

            if not school:
                raise ValueError("School not found.")

        result = await db.execute(
            select(User).where(
                User.email == normalised_email,
                User.school_id == school_id,
            )
        )
        existing_user = result.scalar_one_or_none()

        if existing_user:
            raise ValueError("A user with this email already exists for this school.")

        primary_role = AuthService._get_primary_role(requested_roles)

        user = User(
            email=normalised_email,
            hashed_password=get_password_hash(payload.password),
            full_name=payload.full_name.strip() if payload.full_name else None,
            role=primary_role,  # legacy compatibility column
            school_id=school_id,
            is_active=True,
            status=UserStatus.ACTIVE,
        )

        db.add(user)
        await db.flush()

        for role in requested_roles:
            db.add(
                UserRoleAssignment(
                    user_id=user.id,
                    role=role,
                )
            )

        try:
            await db.commit()
        except Exception:
            await db.rollback()
            raise

        result = await db.execute(
            select(User)
            .options(
                selectinload(User.user_roles),
                selectinload(User.school),
            )
            .where(User.id == user.id)
        )

        return result.scalar_one()

    @staticmethod
    async def login(db: AsyncSession, payload: LoginIn) -> TokenOut:
        normalised_email = payload.email.strip().lower()

        query = (
            select(User)
            .options(
                selectinload(User.user_roles),
                selectinload(User.school),
            )
            .where(User.email == normalised_email)
        )

        if payload.school_id is None:
            query = query.where(
                User.school_id.is_(None),
                User.role == UserRole.PLATFORM_ADMIN,
            )
        else:
            query = query.where(User.school_id == payload.school_id)

        result = await db.execute(query)
        user = result.scalar_one_or_none()

        if (
            not user
            or not user.hashed_password
            or not verify_password(payload.password, user.hashed_password)
        ):
            raise ValueError("Invalid credentials.")

        if not user.is_active or user.status != UserStatus.ACTIVE:
            raise ValueError("User account is inactive.")

        token = create_access_token(
            data={
                "sub": str(user.id),
                "school_id": user.school_id,
                "role": user.primary_role,  # temporary legacy support
                "roles": user.roles,  # new multi-role payload
            }
        )

        return TokenOut(
            access_token=token,
            token_type="bearer",
        )
