from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import User
from app.models.user import UserRole, UserStatus
from app.models.user_role import UserRoleAssignment


class UserRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, user_id: int) -> User | None:
        result = await self.db.execute(
            select(User)
            .options(selectinload(User.school), selectinload(User.user_roles))
            .where(User.id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str, school_id: int | None) -> User | None:
        normalized_email = email.strip().lower()

        query = (
            select(User)
            .options(selectinload(User.school), selectinload(User.user_roles))
            .where(User.email == normalized_email)
        )

        query = query.where(
            User.school_id.is_(None)
            if school_id is None
            else User.school_id == school_id
        )

        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def list_by_school(
        self,
        school_id: int,
        *,
        role: UserRole | None = None,
        status: UserStatus | None = None,
        include_inactive: bool = True,
    ) -> list[User]:
        query = (
            select(User)
            .options(selectinload(User.school), selectinload(User.user_roles))
            .where(User.school_id == school_id)
            .order_by(User.created_at.desc())
        )

        # Multi-role aware filter:
        # finds users who have this role in user_roles, including users with
        # ["school_admin", "teacher"].
        if role is not None:
            query = query.where(
                User.id.in_(
                    select(UserRoleAssignment.user_id).where(
                        UserRoleAssignment.role == role
                    )
                )
            )

        if status is not None:
            query = query.where(User.status == status)

        if not include_inactive:
            query = query.where(User.is_active.is_(True))

        result = await self.db.execute(query)
        return list(result.scalars().unique().all())

    async def count_school_admins(self, school_id: int) -> int:
        """
        Counts active school admins using user_roles, not the legacy users.role column.

        This correctly counts users with:
        ["school_admin", "teacher"]
        """
        result = await self.db.execute(
            select(func.count(func.distinct(User.id)))
            .join(UserRoleAssignment, UserRoleAssignment.user_id == User.id)
            .where(
                User.school_id == school_id,
                UserRoleAssignment.role == UserRole.SCHOOL_ADMIN,
                User.is_active.is_(True),
                User.status == UserStatus.ACTIVE,
            )
        )
        return int(result.scalar_one())

    async def create(self, user: User) -> User:
        self.db.add(user)
        await self.db.flush()

        result = await self.db.execute(
            select(User)
            .options(selectinload(User.school), selectinload(User.user_roles))
            .where(User.id == user.id)
        )
        return result.scalar_one()

    async def save(self, user: User) -> User:
        self.db.add(user)
        await self.db.flush()

        result = await self.db.execute(
            select(User)
            .options(selectinload(User.school), selectinload(User.user_roles))
            .where(User.id == user.id)
        )
        return result.scalar_one()

    async def delete(self, user: User) -> None:
        await self.db.delete(user)
        await self.db.flush()
