from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import PermissionService
from app.core.security import get_password_hash
from app.models.user import User, UserRole, UserStatus
from app.repositories.user import UserRepository
from app.schemas.auth import CurrentUser
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
        current_user: CurrentUser,
    ) -> User:
        repo = UserRepository(db)

        if current_user.role not in {UserRole.SCHOOL_ADMIN, UserRole.PLATFORM_ADMIN}:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not allowed to create school users.",
            )

        target_school_id = payload.school_id or current_user.school_id
        if target_school_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="school_id is required.",
            )

        if payload.role == UserRole.PLATFORM_ADMIN:
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

        user = User(
            email=payload.email,
            hashed_password=get_password_hash(payload.password),
            full_name=payload.full_name,
            role=payload.role,
            status=UserStatus.ACTIVE,
            is_active=True,
            school_id=target_school_id,
        )

        await repo.create(user)
        await db.commit()
        await db.refresh(user)
        return user

    @staticmethod
    async def update_school_user(
        db: AsyncSession,
        user_id: int,
        payload: UserUpdate,
        current_user: CurrentUser,
    ) -> User:
        repo = UserRepository(db)
        user = await repo.get_by_id(user_id)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found.",
            )

        PermissionService.ensure_can_manage_school_user(current_user, user)

        if payload.full_name is not None:
            user.full_name = payload.full_name

        if payload.email is not None:
            existing_user = await repo.get_by_email(payload.email, user.school_id)
            if existing_user and existing_user.id != user.id:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="A user with this email already exists in this school.",
                )
            user.email = payload.email

        if payload.role is not None:
            if payload.role == UserRole.PLATFORM_ADMIN:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot promote a school user to platform admin here.",
                )
            user.role = payload.role

        if payload.status is not None:
            user.status = payload.status
            user.is_active = payload.status == UserStatus.ACTIVE

        await repo.save(user)
        await db.commit()
        await db.refresh(user)
        return user

    @staticmethod
    async def deactivate_user(
        db: AsyncSession,
        user_id: int,
        current_user: CurrentUser,
    ) -> User:
        repo = UserRepository(db)
        user = await repo.get_by_id(user_id)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found.",
            )

        PermissionService.ensure_can_manage_school_user(current_user, user)

        if user.school_id is not None:
            active_admin_count = await repo.count_school_admins(user.school_id)
            PermissionService.ensure_not_last_school_admin(user, active_admin_count)

        user.status = UserStatus.DEACTIVATED
        user.is_active = False
        user.deleted_at = datetime.now(timezone.utc)
        user.retention_expires_at = datetime.now(timezone.utc) + timedelta(days=90)

        await repo.save(user)
        await db.commit()
        await db.refresh(user)
        return user

    @staticmethod
    async def request_erasure(
        db: AsyncSession,
        user_id: int,
        current_user: CurrentUser,
    ) -> User:
        repo = UserRepository(db)
        user = await repo.get_by_id(user_id)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found.",
            )

        PermissionService.ensure_can_manage_school_user(current_user, user)
        PermissionService.ensure_can_request_erasure(user)

        if user.school_id is not None:
            active_admin_count = await repo.count_school_admins(user.school_id)
            PermissionService.ensure_not_last_school_admin(user, active_admin_count)

        user.status = UserStatus.PENDING_ERASURE
        user.is_active = False
        user.deletion_requested_at = datetime.now(timezone.utc)

        await repo.save(user)
        await db.commit()
        await db.refresh(user)
        return user

    @staticmethod
    async def anonymise_user(
        db: AsyncSession,
        user_id: int,
        current_user: CurrentUser,
    ) -> User:
        repo = UserRepository(db)
        user = await repo.get_by_id(user_id)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found.",
            )

        PermissionService.ensure_can_manage_school_user(current_user, user)
        PermissionService.ensure_can_anonymise(user)

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
        await db.commit()
        await db.refresh(user)
        return user
