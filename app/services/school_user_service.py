from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import PermissionService
from app.core.security import get_password_hash
from app.models.user import User, UserRole, UserStatus
from app.models.user_role import UserRoleAssignment
from app.repositories.user import UserRepository
from app.schemas.user import UserCreate, UserUpdate


class SchoolUserService:
    @staticmethod
    async def list_users_by_school(
        db: AsyncSession,
        school_id: int,
        *,
        role: Optional[UserRole] = None,
        status_filter: Optional[UserStatus] = None,
        include_inactive: bool = True,
    ) -> list[User]:
        repo = UserRepository(db)
        return await repo.list_by_school(
            school_id,
            role=role,
            status=status_filter,
            include_inactive=include_inactive,
        )

    @staticmethod
    async def create_school_user(
        db: AsyncSession,
        payload: UserCreate,
        current_user: User,
    ) -> User:
        repo = UserRepository(db)

        PermissionService.ensure_school_admin_or_platform_admin(current_user)
        PermissionService.ensure_active_user(current_user)

        target_school_id = payload.school_id or current_user.school_id
        if target_school_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="school_id is required.",
            )

        if (
            payload.role == UserRole.PLATFORM_ADMIN
            or UserRole.PLATFORM_ADMIN in payload.roles
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Platform admins cannot be created from school admin flows.",
            )

        if (
            current_user.role == UserRole.SCHOOL_ADMIN
            and current_user.school_id != target_school_id
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot create users outside your school.",
            )

        existing_user = await repo.get_by_email(payload.email, target_school_id)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A user with this email already exists in this school.",
            )

        primary_role = payload.role or payload.roles[0]

        user = User(
            email=payload.email.strip().lower(),
            hashed_password=get_password_hash(payload.password),
            full_name=payload.full_name.strip() if payload.full_name else None,
            role=primary_role,  # legacy primary role column kept during transition
            status=UserStatus.ACTIVE,
            is_active=True,
            school_id=target_school_id,
        )

        await repo.create(user)
        await db.flush()

        # Multi-role table source of truth
        for role in payload.roles:
            db.add(
                UserRoleAssignment(
                    user_id=user.id,
                    role=role,
                )
            )
        await db.flush()

        await db.refresh(user, attribute_names=["school", "user_roles"])
        return user

    @staticmethod
    async def create_user(
        db: AsyncSession,
        payload: UserCreate,
        school_id: int,
        actor: User,
    ) -> User:
        payload.school_id = school_id
        return await SchoolUserService.create_school_user(
            db=db,
            payload=payload,
            current_user=actor,
        )

    @staticmethod
    async def update_school_user(
        db: AsyncSession,
        user_id: int,
        payload: UserUpdate,
        current_user: User,
    ) -> User:
        repo = UserRepository(db)
        user = await repo.get_by_id(user_id)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found.",
            )

        PermissionService.ensure_active_user(current_user)
        PermissionService.ensure_can_manage_school_user(current_user, user)

        if payload.full_name is not None:
            user.full_name = payload.full_name.strip() if payload.full_name else None

        if payload.email is not None:
            normalized_email = payload.email.strip().lower()
            existing_user = await repo.get_by_email(normalized_email, user.school_id)
            if existing_user and existing_user.id != user.id:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="A user with this email already exists in this school.",
                )
            user.email = normalized_email

        # Multi-role update
        if payload.roles is not None:
            if UserRole.PLATFORM_ADMIN in payload.roles:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot promote a school user to platform admin here.",
                )

            await db.execute(
                delete(UserRoleAssignment).where(UserRoleAssignment.user_id == user.id)
            )

            for role in payload.roles:
                db.add(
                    UserRoleAssignment(
                        user_id=user.id,
                        role=role,
                    )
                )

            # Keep legacy primary role aligned
            user.role = payload.role or payload.roles[0]

        elif payload.role is not None:
            if payload.role == UserRole.PLATFORM_ADMIN:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot promote a school user to platform admin here.",
                )

            user.role = payload.role

            # Transitional behavior:
            # if only legacy role is updated, keep user_roles table aligned to a single role
            await db.execute(
                delete(UserRoleAssignment).where(UserRoleAssignment.user_id == user.id)
            )
            db.add(
                UserRoleAssignment(
                    user_id=user.id,
                    role=payload.role,
                )
            )

        if payload.status is not None:
            user.status = payload.status
            user.is_active = payload.status == UserStatus.ACTIVE

        if payload.is_active is not None:
            user.is_active = payload.is_active
            if not payload.is_active and user.status == UserStatus.ACTIVE:
                user.status = UserStatus.DEACTIVATED
            elif payload.is_active and user.status == UserStatus.DEACTIVATED:
                user.status = UserStatus.ACTIVE

        await repo.save(user)
        await db.flush()
        await db.refresh(user, attribute_names=["school", "user_roles"])
        return user

    @staticmethod
    async def update_user(
        db: AsyncSession,
        user_id: int,
        payload: UserUpdate,
        school_id: int,
        actor: User,
    ) -> User:
        if actor.role == UserRole.SCHOOL_ADMIN and actor.school_id != school_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot update users outside your school.",
            )

        return await SchoolUserService.update_school_user(
            db=db,
            user_id=user_id,
            payload=payload,
            current_user=actor,
        )

    @staticmethod
    async def deactivate_user(
        db: AsyncSession,
        user_id: int,
        current_user: User | None = None,
        *,
        school_id: int | None = None,
        actor: User | None = None,
    ) -> User:
        current_actor = actor or current_user
        if current_actor is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing actor context.",
            )

        repo = UserRepository(db)
        user = await repo.get_by_id(user_id)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found.",
            )

        PermissionService.ensure_active_user(current_actor)
        PermissionService.ensure_can_manage_school_user(current_actor, user)

        if school_id is not None and user.school_id != school_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found in this school.",
            )

        if user.school_id is not None:
            active_admin_count = await repo.count_school_admins(user.school_id)
            PermissionService.ensure_not_last_school_admin(user, active_admin_count)

        user.status = UserStatus.DEACTIVATED
        user.is_active = False
        user.deleted_at = datetime.now(timezone.utc)
        user.retention_expires_at = datetime.now(timezone.utc) + timedelta(days=90)

        await repo.save(user)
        await db.flush()
        return user

    @staticmethod
    async def request_erasure(
        db: AsyncSession,
        user_id: int,
        current_user: User | None = None,
        *,
        school_id: int | None = None,
        actor: User | None = None,
    ) -> User:
        current_actor = actor or current_user
        if current_actor is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing actor context.",
            )

        repo = UserRepository(db)
        user = await repo.get_by_id(user_id)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found.",
            )

        PermissionService.ensure_active_user(current_actor)
        PermissionService.ensure_can_manage_school_user(current_actor, user)
        PermissionService.ensure_can_request_erasure(user)

        if school_id is not None and user.school_id != school_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found in this school.",
            )

        if user.school_id is not None:
            active_admin_count = await repo.count_school_admins(user.school_id)
            PermissionService.ensure_not_last_school_admin(user, active_admin_count)

        user.status = UserStatus.PENDING_ERASURE
        user.is_active = False
        user.deletion_requested_at = datetime.now(timezone.utc)

        await repo.save(user)
        await db.flush()
        return user

    @staticmethod
    async def anonymise_user(
        db: AsyncSession,
        user_id: int,
        current_user: User | None = None,
        *,
        school_id: int | None = None,
        actor: User | None = None,
    ) -> User:
        current_actor = actor or current_user
        if current_actor is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing actor context.",
            )

        repo = UserRepository(db)
        user = await repo.get_by_id(user_id)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found.",
            )

        PermissionService.ensure_active_user(current_actor)
        PermissionService.ensure_can_manage_school_user(current_actor, user)
        PermissionService.ensure_can_anonymise(user)

        if school_id is not None and user.school_id != school_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found in this school.",
            )

        if user.school_id is not None:
            active_admin_count = await repo.count_school_admins(user.school_id)
            PermissionService.ensure_not_last_school_admin(user, active_admin_count)

        user.full_name = f"Deleted User {user.id}"
        user.email = f"deleted-{user.id}@redacted.local"
        user.hashed_password = None
        user.status = UserStatus.ANONYMISED
        user.is_active = False
        user.anonymised_at = datetime.now(timezone.utc)

        await repo.save(user)
        await db.flush()
        return user
