from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import User
from app.models.user import UserRole, UserStatus


class UserRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, user_id: int) -> User | None:
        result = await self.db.execute(
            select(User).options(selectinload(User.school)).where(User.id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str, school_id: int | None) -> User | None:
        query = (
            select(User).options(selectinload(User.school)).where(User.email == email)
        )

        if school_id is None:
            query = query.where(User.school_id.is_(None))
        else:
            query = query.where(User.school_id == school_id)

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
            .options(selectinload(User.school))
            .where(User.school_id == school_id)
            .order_by(User.created_at.desc())
        )

        if role is not None:
            query = query.where(User.role == role)

        if status is not None:
            query = query.where(User.status == status)

        if not include_inactive:
            query = query.where(User.is_active.is_(True))

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def count_school_admins(self, school_id: int) -> int:
        result = await self.db.execute(
            select(func.count(User.id)).where(
                User.school_id == school_id,
                User.role == UserRole.SCHOOL_ADMIN,
                User.is_active.is_(True),
                User.status == UserStatus.ACTIVE,
            )
        )
        return int(result.scalar_one())

    async def create(self, user: User) -> User:
        self.db.add(user)
        await self.db.flush()
        await self.db.refresh(user)
        return user

    async def save(self, user: User) -> User:
        self.db.add(user)
        await self.db.flush()
        await self.db.refresh(user)
        return user

    async def delete(self, user: User) -> None:
        await self.db.delete(user)
        await self.db.flush()
