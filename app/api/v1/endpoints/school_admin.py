from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import require_role
from app.db.session import get_db
from app.models import User
from app.models.course import Course
from app.models.user import UserRole
from app.schemas.user import UserCreate, UserOut, UserUpdate
from app.services.school_user_service import SchoolUserService

router = APIRouter()


def _to_user_out(user: User) -> UserOut:
    return UserOut(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        roles=[UserRole(r) for r in user.roles],
        school_id=user.school_id,
        school_name=user.school.name if user.school else None,
        is_active=user.is_active,
        status=user.status,
        created_at=user.created_at,
    )


def _resolve_school_scope(
    current_user: User,
    school_id: int | None,
) -> int:
    if current_user.is_platform_admin:
        if school_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="school_id is required for platform admin on this endpoint.",
            )

        return school_id

    if current_user.school_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current user is not assigned to a school.",
        )

    return int(current_user.school_id)


@router.get("/users", response_model=list[UserOut])
async def list_users(
    school_id: int | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(
        require_role(UserRole.SCHOOL_ADMIN, UserRole.PLATFORM_ADMIN)
    ),
):
    target_school_id = _resolve_school_scope(current_user, school_id)
    users = await SchoolUserService.list_users_by_school(db, target_school_id)

    return [_to_user_out(user) for user in users]


@router.get("/courses")
async def list_school_courses(
    school_id: int | None = Query(default=None),
    search: str | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(
        require_role(UserRole.SCHOOL_ADMIN, UserRole.PLATFORM_ADMIN)
    ),
):
    target_school_id = _resolve_school_scope(current_user, school_id)

    query = (
        select(Course)
        .options(selectinload(Course.teacher))
        .where(Course.school_id == target_school_id)
    )

    count_query = (
        select(func.count())
        .select_from(Course)
        .where(Course.school_id == target_school_id)
    )

    if search:
        term = f"%{search.strip()}%"
        query = query.where(Course.title.ilike(term))
        count_query = count_query.where(Course.title.ilike(term))

    total = await db.scalar(count_query) or 0

    result = await db.execute(
        query.order_by(Course.id.desc()).offset(skip).limit(limit)
    )

    courses = result.scalars().all()

    return {
        "items": [
            {
                "id": course.id,
                "title": course.title,
                "description": course.description,
                "teacher_id": course.teacher_id,
                "teacher_name": course.teacher.full_name if course.teacher else None,
                "school_id": course.school_id,
                "published": course.published,
            }
            for course in courses
        ],
        "total": int(total),
        "skip": skip,
        "limit": limit,
    }


@router.post(
    "/users",
    response_model=UserOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_user(
    payload: UserCreate,
    school_id: int | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(
        require_role(UserRole.SCHOOL_ADMIN, UserRole.PLATFORM_ADMIN)
    ),
):
    target_school_id = _resolve_school_scope(current_user, school_id)

    user = await SchoolUserService.create_user(
        db=db,
        payload=payload,
        school_id=target_school_id,
        actor=current_user,
    )

    await db.commit()
    await db.refresh(user)

    return _to_user_out(user)


@router.patch("/users/{user_id}", response_model=UserOut)
async def update_user(
    user_id: int,
    payload: UserUpdate,
    school_id: int | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(
        require_role(UserRole.SCHOOL_ADMIN, UserRole.PLATFORM_ADMIN)
    ),
):
    target_school_id = _resolve_school_scope(current_user, school_id)

    user = await SchoolUserService.update_user(
        db=db,
        user_id=user_id,
        payload=payload,
        school_id=target_school_id,
        actor=current_user,
    )

    await db.commit()
    await db.refresh(user)

    return _to_user_out(user)


@router.post("/users/{user_id}/deactivate", response_model=UserOut)
async def deactivate_user(
    user_id: int,
    school_id: int | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(
        require_role(UserRole.SCHOOL_ADMIN, UserRole.PLATFORM_ADMIN)
    ),
):
    target_school_id = _resolve_school_scope(current_user, school_id)

    user = await SchoolUserService.deactivate_user(
        db=db,
        user_id=user_id,
        school_id=target_school_id,
        actor=current_user,
    )

    await db.commit()
    await db.refresh(user)

    return _to_user_out(user)


@router.post("/users/{user_id}/request-erasure", response_model=UserOut)
async def request_erasure(
    user_id: int,
    school_id: int | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(
        require_role(UserRole.SCHOOL_ADMIN, UserRole.PLATFORM_ADMIN)
    ),
):
    target_school_id = _resolve_school_scope(current_user, school_id)

    user = await SchoolUserService.request_erasure(
        db=db,
        user_id=user_id,
        school_id=target_school_id,
        actor=current_user,
    )

    await db.commit()
    await db.refresh(user)

    return _to_user_out(user)


@router.post("/users/{user_id}/anonymise", response_model=UserOut)
async def anonymise_user(
    user_id: int,
    school_id: int | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(
        require_role(UserRole.SCHOOL_ADMIN, UserRole.PLATFORM_ADMIN)
    ),
):
    target_school_id = _resolve_school_scope(current_user, school_id)

    user = await SchoolUserService.anonymise_user(
        db=db,
        user_id=user_id,
        school_id=target_school_id,
        actor=current_user,
    )

    await db.commit()
    await db.refresh(user)

    return _to_user_out(user)
