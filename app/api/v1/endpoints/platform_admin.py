from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user
from app.core.security import hash_password
from app.db.session import get_db
from app.models.audit_log import AuditLog
from app.models.course import Course
from app.models.enrollment import Enrollment
from app.models.school import School
from app.models.user import User, UserRole, UserStatus
from app.schemas.school import SchoolCreate, SchoolOut
from app.schemas.user import UserCreate, UserOut
from app.services.audit_log_service import log_audit_event

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


@router.get("/audit-logs")
async def platform_admin_audit_logs(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    school_id: int | None = Query(default=None),
    action: str | None = Query(default=None),
    entity_type: str | None = Query(default=None),
    actor_id: int | None = Query(default=None),
    target_user_id: int | None = Query(default=None),
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
):
    _ensure_platform_admin(current_user)

    query = (
        select(AuditLog)
        .options(
            selectinload(AuditLog.actor),
            selectinload(AuditLog.target_user),
            selectinload(AuditLog.school),
        )
        .order_by(AuditLog.created_at.desc())
    )

    count_query = select(func.count()).select_from(AuditLog)

    filters = []

    if school_id is not None:
        filters.append(AuditLog.school_id == school_id)

    if action:
        filters.append(AuditLog.action == action.strip())

    if entity_type:
        filters.append(AuditLog.entity_type == entity_type.strip())

    if actor_id is not None:
        filters.append(AuditLog.actor_id == actor_id)

    if target_user_id is not None:
        filters.append(AuditLog.target_user_id == target_user_id)

    if date_from is not None:
        filters.append(AuditLog.created_at >= date_from)

    if date_to is not None:
        filters.append(AuditLog.created_at <= date_to)

    if filters:
        query = query.where(*filters)
        count_query = count_query.where(*filters)

    total = await db.scalar(count_query) or 0

    result = await db.execute(query.offset(skip).limit(limit))
    logs = result.scalars().all()

    return {
        "items": [
            {
                "id": log.id,
                "action": log.action,
                "entity_type": log.entity_type,
                "entity_id": log.entity_id,
                "actor_id": log.actor_id,
                "actor_email": log.actor.email if log.actor else None,
                "target_user_id": log.target_user_id,
                "target_user_email": log.target_user.email if log.target_user else None,
                "school_id": log.school_id,
                "school_name": log.school.name if log.school else None,
                "metadata": log.metadata_json,
                "created_at": log.created_at,
            }
            for log in logs
        ],
        "total": int(total),
        "skip": skip,
        "limit": limit,
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

    school_name = payload.name.strip()

    existing = await db.execute(
        select(School).where(func.lower(School.name) == school_name.lower())
    )

    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A school with this name already exists",
        )

    school = School(name=school_name)
    db.add(school)
    await db.flush()
    await db.refresh(school)

    await log_audit_event(
        db,
        actor=current_user,
        action="school.created",
        entity_type="school",
        entity_id=school.id,
        school_id=school.id,
        metadata={"school_name": school.name},
    )

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

    email = payload.email.strip().lower()

    existing = await db.execute(
        select(User).where(
            User.email == email,
            User.school_id == school_id,
        )
    )

    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email already exists in this school",
        )

    user = User(
        email=email,
        hashed_password=hash_password(payload.password),
        role=UserRole.SCHOOL_ADMIN,
        full_name=payload.full_name,
        school_id=school_id,
        status=UserStatus.ACTIVE,
        is_active=True,
    )

    db.add(user)
    await db.flush()
    await db.refresh(user)

    await log_audit_event(
        db,
        actor=current_user,
        action="user.created",
        entity_type="user",
        entity_id=user.id,
        target_user_id=user.id,
        school_id=school_id,
        metadata={
            "email": user.email,
            "role": str(user.role),
            "full_name": user.full_name,
            "created_by_endpoint": "platform_admin_create_school_admin",
        },
    )

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

    previous_role = user.role
    user.role = role_enum

    await log_audit_event(
        db,
        actor=current_user,
        action="user.role_updated",
        entity_type="user",
        entity_id=user.id,
        target_user_id=user.id,
        school_id=user.school_id,
        metadata={
            "email": user.email,
            "previous_role": str(previous_role),
            "new_role": str(role_enum),
        },
    )

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

    previous_is_active = user.is_active
    new_is_active = bool(payload.get("is_active"))

    user.is_active = new_is_active

    await log_audit_event(
        db,
        actor=current_user,
        action="user.active_updated",
        entity_type="user",
        entity_id=user.id,
        target_user_id=user.id,
        school_id=user.school_id,
        metadata={
            "email": user.email,
            "previous_is_active": previous_is_active,
            "new_is_active": new_is_active,
        },
    )

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

    previous_published = course.published
    new_published = bool(payload.get("published"))

    course.published = new_published

    await log_audit_event(
        db,
        actor=current_user,
        action="course.published_updated",
        entity_type="course",
        entity_id=course.id,
        school_id=course.school_id,
        metadata={
            "title": course.title,
            "previous_published": previous_published,
            "new_published": new_published,
        },
    )

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

    course_id_value = course.id
    course_title = course.title
    course_school_id = course.school_id

    await db.delete(course)

    await log_audit_event(
        db,
        actor=current_user,
        action="course.deleted",
        entity_type="course",
        entity_id=course_id_value,
        school_id=course_school_id,
        metadata={"title": course_title},
    )

    await db.commit()

    return {"success": True}
