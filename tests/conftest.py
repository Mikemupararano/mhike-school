from __future__ import annotations

from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.security import create_access_token, get_password_hash
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.user import User, UserRole, UserStatus
from app.models.user_role import UserRoleAssignment


TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture(scope="session")
async def test_engine():
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture()
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    async_session = async_sessionmaker(
        bind=test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture()
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)

    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as test_client:
        yield test_client

    app.dependency_overrides.clear()


async def create_test_user(
    db: AsyncSession,
    *,
    email: str = "user@example.com",
    password: str = "password123",
    full_name: str = "Test User",
    school_id: int | None = 1,
    roles: list[UserRole] | None = None,
    status: UserStatus = UserStatus.ACTIVE,
    is_active: bool = True,
) -> User:
    roles = roles or [UserRole.STUDENT]

    primary_role = (
        UserRole.PLATFORM_ADMIN
        if UserRole.PLATFORM_ADMIN in roles
        else (
            UserRole.SCHOOL_ADMIN
            if UserRole.SCHOOL_ADMIN in roles
            else UserRole.TEACHER if UserRole.TEACHER in roles else UserRole.STUDENT
        )
    )

    user = User(
        email=email.strip().lower(),
        hashed_password=get_password_hash(password),
        full_name=full_name,
        role=primary_role,
        school_id=school_id,
        status=status,
        is_active=is_active,
    )

    db.add(user)
    await db.flush()

    for role in roles:
        db.add(UserRoleAssignment(user_id=user.id, role=role))

    await db.flush()
    await db.refresh(user, attribute_names=["user_roles"])

    return user


def make_token(user: User) -> str:
    return create_access_token(
        data={
            "sub": str(user.id),
            "school_id": user.school_id,
            "role": user.primary_role,
            "roles": user.roles,
        }
    )


@pytest_asyncio.fixture()
async def student_user(db_session: AsyncSession) -> User:
    return await create_test_user(
        db_session,
        email="student@example.com",
        roles=[UserRole.STUDENT],
        school_id=1,
    )


@pytest_asyncio.fixture()
async def teacher_user(db_session: AsyncSession) -> User:
    return await create_test_user(
        db_session,
        email="teacher@example.com",
        roles=[UserRole.TEACHER],
        school_id=1,
    )


@pytest_asyncio.fixture()
async def school_admin_user(db_session: AsyncSession) -> User:
    return await create_test_user(
        db_session,
        email="school.admin@example.com",
        roles=[UserRole.SCHOOL_ADMIN],
        school_id=1,
    )


@pytest_asyncio.fixture()
async def school_admin_teacher_user(db_session: AsyncSession) -> User:
    return await create_test_user(
        db_session,
        email="admin.teacher@example.com",
        roles=[UserRole.SCHOOL_ADMIN, UserRole.TEACHER],
        school_id=1,
    )


@pytest_asyncio.fixture()
async def platform_admin_user(db_session: AsyncSession) -> User:
    return await create_test_user(
        db_session,
        email="platform.admin@example.com",
        roles=[UserRole.PLATFORM_ADMIN],
        school_id=None,
    )


@pytest.fixture()
def auth_headers():
    def _headers(user: User) -> dict[str, str]:
        return {"Authorization": f"Bearer {make_token(user)}"}

    return _headers
