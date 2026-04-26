from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user
from app.core.security import hash_password
from app.db.session import get_db
from app.models.course import Course
from app.models.enrollment import Enrollment
from app.models.school import School
from app.models.user import User, UserRole, UserStatus
from app.schemas.school import SchoolCreate, SchoolOut
from app.schemas.user import UserCreate, UserOut

router = APIRouter()


def _ensure_platform_admin(current_user: User) -> None:
    if not current_user.is_platform_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Platform admin access required",
        )


@router.get("/dashboard")
async def platform_admin_dashboard(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _ensure_platform_admin(current_user)

    total_schools = await db.scalar(select(func.count()).select_from(School)) or 0
    total_users = await db.scalar(select(func.count()).select_from(User)) or 0
    total_courses = await db.scalar(select(func.count()).select_from(Course)) or 0

    active_users = (
        await db.scalar(
            select(func.count())
            .select_from(User)
            .where(
                User.is_active.is_(True),
                User.status == UserStatus.ACTIVE,
            )
        )
        or 0
    )

    published_content = (
        await db.scalar(
            select(func.count()).select_from(Course).where(Course.published.is_(True))
        )
        or 0
    )

    total_enrollments = (
        await db.scalar(select(func.count()).select_from(Enrollment)) or 0
    )

    recent_result = await db.execute(select(School).order_by(School.id.desc()).limit(5))
    recent_schools = recent_result.scalars().all()

    recent_school_items = []

    for school in recent_schools:
        users_count = (
            await db.scalar(
                select(func.count())
                .select_from(User)
                .where(User.school_id == school.id)
            )
            or 0
        )

        admin_result = await db.execute(
            select(User)
            .where(
                User.school_id == school.id,
                User.role == UserRole.SCHOOL_ADMIN,
            )
            .order_by(User.id.asc())
            .limit(1)
        )
        admin = admin_result.scalar_one_or_none()

        recent_school_items.append(
            {
                "id": school.id,
                "name": school.name,
                "admin_name": admin.full_name if admin else "Not assigned",
                "users": int(users_count),
                "status": "Active",
            }
        )

    return {
        "total_schools": int(total_schools),
        "total_users": int(total_users),
        "active_users": int(active_users),
        "total_courses": int(total_courses),
        "published_content": int(published_content),
        "total_enrollments": int(total_enrollments),
        "recent_schools": recent_school_items,
    }


@router.get("/schools", response_model=list[SchoolOut])
async def platform_admin_schools(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    search: str | None = Query(default=None),
):
    _ensure_platform_admin(current_user)

    query = select(School).order_by(School.id.asc())

    if search:
        term = f"%{search.strip()}%"
        query = query.where(School.name.ilike(term))

    result = await db.execute(query)
    return list(result.scalars().all())


@router.post("/schools", response_model=SchoolOut, status_code=status.HTTP_201_CREATED)
async def create_school(
    payload: SchoolCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _ensure_platform_admin(current_user)

    existing = await db.execute(
        select(School).where(func.lower(School.name) == payload.name.strip().lower())
    )

    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A school with this name already exists",
        )

    school = School(name=payload.name.strip())
    db.add(school)

    await db.commit()
    await db.refresh(school)

    return school


@router.post(
    "/schools/{school_id}/admins",
    response_model=UserOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_school_admin(
    school_id: int,
    payload: UserCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _ensure_platform_admin(current_user)

    school = await db.get(School, school_id)

    if not school:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="School not found",
        )

    if payload.role != UserRole.SCHOOL_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This endpoint can only create school_admin users",
        )

    existing = await db.execute(
        select(User).where(
            User.email == payload.email.strip().lower(),
            User.school_id == school_id,
        )
    )

    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email already exists in this school",
        )

    user = User(
        email=payload.email.strip().lower(),
        hashed_password=hash_password(payload.password),
        role=UserRole.SCHOOL_ADMIN,
        full_name=payload.full_name,
        school_id=school_id,
        status=UserStatus.ACTIVE,
        is_active=True,
    )

    db.add(user)

    await db.commit()
    await db.refresh(user)

    return UserOut(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        roles=user.roles,
        school_id=user.school_id,
        school_name=school.name,
        is_active=user.is_active,
        status=user.status,
        created_at=user.created_at,
    )


@router.get("/users")
async def platform_admin_users(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    school_id: int | None = Query(default=None),
    role: str | None = Query(default=None),
    search: str | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=8, ge=1, le=100),
):
    _ensure_platform_admin(current_user)

    query = select(User).options(selectinload(User.school))
    count_query = select(func.count()).select_from(User)

    filters = []

    if school_id is not None:
        filters.append(User.school_id == school_id)

    if role:
        try:
            role_enum = UserRole(role)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid role filter",
            ) from exc

        filters.append(User.role == role_enum)

    if search:
        term = f"%{search.strip()}%"
        filters.append(
            or_(
                User.email.ilike(term),
                User.full_name.ilike(term),
            )
        )

    if filters:
        query = query.where(*filters)
        count_query = count_query.where(*filters)

    total = await db.scalar(count_query) or 0

    result = await db.execute(
        query.order_by(User.created_at.desc()).offset(skip).limit(limit)
    )
    users = result.scalars().all()

    return {
        "items": [
            {
                "id": user.id,
                "full_name": user.full_name,
                "email": user.email,
                "role": user.role,
                "roles": user.roles,
                "school_id": user.school_id,
                "school_name": user.school.name if user.school else None,
                "is_active": user.is_active,
                "status": user.status,
            }
            for user in users
        ],
        "total": int(total),
        "skip": skip,
        "limit": limit,
    }


@router.get("/courses")
async def platform_admin_courses(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    school_id: int | None = Query(default=None),
    search: str | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=8, ge=1, le=100),
):
    _ensure_platform_admin(current_user)

    query = select(Course).options(selectinload(Course.teacher))
    count_query = select(func.count()).select_from(Course)

    filters = []

    if school_id is not None:
        filters.append(Course.school_id == school_id)

    if search:
        term = f"%{search.strip()}%"
        filters.append(Course.title.ilike(term))

    if filters:
        query = query.where(*filters)
        count_query = count_query.where(*filters)

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


@router.post("/users/{user_id}/role")
async def platform_admin_update_user_role(
    user_id: int,
    payload: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _ensure_platform_admin(current_user)

    role = payload.get("role")

    try:
        role_enum = UserRole(role)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid role",
        ) from exc

    user = await db.get(User, user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    if user.is_platform_admin:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot modify platform admin role",
        )

    user.role = role_enum

    await db.commit()
    await db.refresh(user)

    return {
        "id": user.id,
        "full_name": user.full_name,
        "email": user.email,
        "role": user.role,
        "roles": user.roles,
        "school_id": user.school_id,
        "is_active": user.is_active,
        "status": user.status,
    }


@router.post("/users/{user_id}/active")
async def platform_admin_toggle_user_active(
    user_id: int,
    payload: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _ensure_platform_admin(current_user)

    user = await db.get(User, user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    if user.is_platform_admin:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot deactivate platform admin",
        )

    user.is_active = bool(payload.get("is_active"))

    await db.commit()
    await db.refresh(user)

    return {
        "id": user.id,
        "full_name": user.full_name,
        "email": user.email,
        "role": user.role,
        "roles": user.roles,
        "school_id": user.school_id,
        "is_active": user.is_active,
        "status": user.status,
    }


@router.post("/courses/{course_id}/publish")
async def platform_admin_set_course_published(
    course_id: int,
    payload: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _ensure_platform_admin(current_user)

    course = await db.get(Course, course_id)

    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found",
        )

    course.published = bool(payload.get("published"))

    await db.commit()
    await db.refresh(course)

    return {
        "id": course.id,
        "title": course.title,
        "description": course.description,
        "teacher_id": course.teacher_id,
        "school_id": course.school_id,
        "published": course.published,
    }


@router.post("/courses/{course_id}/delete")
async def platform_admin_delete_course(
    course_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _ensure_platform_admin(current_user)

    course = await db.get(Course, course_id)

    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found",
        )

    await db.delete(course)
    await db.commit()

    return {"success": True}
