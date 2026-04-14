from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_current_school_id, require_role
from app.db.session import get_db
from app.models.user import UserRole, User
from app.schemas.user import UserOut, UserCreate, UserUpdate
from app.services.school_user_service import SchoolUserService

router = APIRouter(prefix="/school-admin", tags=["School Admin"])


@router.get("/users", response_model=list[UserOut])
async def list_users(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.SCHOOL_ADMIN, UserRole.PLATFORM_ADMIN)),
    school_id: int = Depends(get_current_school_id),
):
    users = await SchoolUserService.list_users_by_school(db, school_id)
    return [
        UserOut(
            id=u.id,
            email=u.email,
            full_name=u.full_name,
            role=u.role,
            status=u.status,
            school_id=u.school_id,
            school_name=u.school.name if u.school else None,
            is_active=u.is_active,
            created_at=u.created_at,
        )
        for u in users
    ]


@router.post("/users", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def create_user(
    payload: UserCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.SCHOOL_ADMIN, UserRole.PLATFORM_ADMIN)),
):
    user = await SchoolUserService.create_school_user(db, payload, current_user)

    return UserOut(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        status=user.status,
        school_id=user.school_id,
        school_name=user.school.name if user.school else None,
        is_active=user.is_active,
        created_at=user.created_at,
    )


@router.patch("/users/{user_id}", response_model=UserOut)
async def update_user(
    user_id: int,
    payload: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.SCHOOL_ADMIN, UserRole.PLATFORM_ADMIN)),
):
    user = await SchoolUserService.update_school_user(db, user_id, payload, current_user)

    return UserOut(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        status=user.status,
        school_id=user.school_id,
        school_name=user.school.name if user.school else None,
        is_active=user.is_active,
        created_at=user.created_at,
    )


@router.post("/users/{user_id}/deactivate", response_model=UserOut)
async def deactivate_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.SCHOOL_ADMIN, UserRole.PLATFORM_ADMIN)),
):
    user = await SchoolUserService.deactivate_user(db, user_id, current_user)

    return UserOut(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        status=user.status,
        school_id=user.school_id,
        school_name=user.school.name if user.school else None,
        is_active=user.is_active,
        created_at=user.created_at,
    )


@router.post("/users/{user_id}/request-erasure", response_model=UserOut)
async def request_erasure(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.SCHOOL_ADMIN, UserRole.PLATFORM_ADMIN)),
):
    user = await SchoolUserService.request_erasure(db, user_id, current_user)

    return UserOut(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        status=user.status,
        school_id=user.school_id,
        school_name=user.school.name if user.school else None,
        is_active=user.is_active,
        created_at=user.created_at,
    )


@router.post("/users/{user_id}/anonymise", response_model=UserOut)
async def anonymise_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.SCHOOL_ADMIN, UserRole.PLATFORM_ADMIN)),
):
    user = await SchoolUserService.anonymise_user(db, user_id, current_user)

    return UserOut(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        status=user.status,
        school_id=user.school_id,
        school_name=user.school.name if user.school else None,
        is_active=user.is_active,
        created_at=user.created_at,
    )
