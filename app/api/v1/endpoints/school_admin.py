from __future__ import annotations

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    status,
)
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import require_role
from app.db.session import get_db
from app.models import User
from app.models.course import Course
from app.models.subject import Subject
from app.models.user import UserRole
from app.schemas.course import (
    SchoolAdminCourseCreate,
    SchoolAdminCourseOut,
    SchoolAdminCourseUpdate,
)
from app.schemas.user import (
    UserCreate,
    UserOut,
    UserUpdate,
)
from app.services.school_user_service import SchoolUserService

router = APIRouter()


def _to_user_out(
    user: User,
) -> UserOut:
    return UserOut(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        roles=[UserRole(role) for role in user.roles],
        school_id=user.school_id,
        school_name=(user.school.name if user.school else None),
        is_active=user.is_active,
        status=user.status,
        created_at=user.created_at,
    )


def _to_school_admin_course_out(
    course: Course,
) -> SchoolAdminCourseOut:
    return SchoolAdminCourseOut(
        id=course.id,
        title=course.title,
        description=course.description,
        subject_id=course.subject_id,
        exam_board=course.exam_board,
        qualification=course.qualification,
        specification_code=course.specification_code,
        school_id=course.school_id,
        teacher_id=course.teacher_id,
        teacher_name=(course.teacher.full_name if course.teacher else None),
        published=course.published,
    )


def _resolve_school_scope(
    current_user: User,
    school_id: int | None,
) -> int:
    if current_user.is_platform_admin:
        if school_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "school_id is required for platform admin " "on this endpoint."
                ),
            )

        return school_id

    if current_user.school_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current user is not assigned to a school.",
        )

    return int(
        current_user.school_id,
    )


def _user_has_teacher_role(
    user: User,
) -> bool:
    try:
        roles = {UserRole(role) for role in user.roles}
    except (TypeError, ValueError):
        roles = set()

    if UserRole.TEACHER in roles:
        return True

    return user.role == UserRole.TEACHER


async def _get_school_teacher(
    db: AsyncSession,
    *,
    teacher_id: int,
    school_id: int,
) -> User:
    result = await db.execute(
        select(User).where(
            User.id == teacher_id,
            User.school_id == school_id,
        )
    )

    teacher = result.scalar_one_or_none()

    if teacher is None or not _user_has_teacher_role(
        teacher,
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Teacher not found in the current school.",
        )

    if not teacher.is_active:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The selected teacher is not active.",
        )

    return teacher


async def _get_school_subject(
    db: AsyncSession,
    *,
    subject_id: int,
    school_id: int,
) -> Subject:
    result = await db.execute(
        select(Subject).where(
            Subject.id == subject_id,
            Subject.school_id == school_id,
        )
    )

    subject = result.scalar_one_or_none()

    if subject is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subject not found in the current school.",
        )

    return subject


async def _get_school_course(
    db: AsyncSession,
    *,
    course_id: int,
    school_id: int,
) -> Course:
    result = await db.execute(
        select(Course)
        .options(
            selectinload(
                Course.teacher,
            )
        )
        .where(
            Course.id == course_id,
            Course.school_id == school_id,
        )
    )

    course = result.scalar_one_or_none()

    if course is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found in the current school.",
        )

    return course


def _clean_optional_text(
    value: str | None,
) -> str | None:
    if value is None:
        return None

    cleaned = value.strip()

    return cleaned or None


@router.get(
    "/users",
    response_model=list[UserOut],
)
async def list_users(
    school_id: int | None = Query(
        default=None,
    ),
    db: AsyncSession = Depends(
        get_db,
    ),
    current_user: User = Depends(
        require_role(
            UserRole.SCHOOL_ADMIN,
            UserRole.PLATFORM_ADMIN,
        )
    ),
):
    target_school_id = _resolve_school_scope(
        current_user,
        school_id,
    )

    users = await SchoolUserService.list_users_by_school(
        db,
        target_school_id,
    )

    return [
        _to_user_out(
            user,
        )
        for user in users
    ]


@router.get(
    "/courses",
)
async def list_school_courses(
    school_id: int | None = Query(
        default=None,
    ),
    search: str | None = Query(
        default=None,
    ),
    skip: int = Query(
        default=0,
        ge=0,
    ),
    limit: int = Query(
        default=20,
        ge=1,
        le=100,
    ),
    db: AsyncSession = Depends(
        get_db,
    ),
    current_user: User = Depends(
        require_role(
            UserRole.SCHOOL_ADMIN,
            UserRole.PLATFORM_ADMIN,
        )
    ),
):
    target_school_id = _resolve_school_scope(
        current_user,
        school_id,
    )

    query = (
        select(Course)
        .options(
            selectinload(
                Course.teacher,
            )
        )
        .where(Course.school_id == target_school_id)
    )

    count_query = (
        select(
            func.count(),
        )
        .select_from(
            Course,
        )
        .where(Course.school_id == target_school_id)
    )

    if search:
        cleaned_search = search.strip()

        if cleaned_search:
            term = f"%{cleaned_search}%"

            query = query.where(
                Course.title.ilike(
                    term,
                )
            )

            count_query = count_query.where(
                Course.title.ilike(
                    term,
                )
            )

    total = (
        await db.scalar(
            count_query,
        )
        or 0
    )

    result = await db.execute(
        query.order_by(
            Course.id.desc(),
        )
        .offset(
            skip,
        )
        .limit(
            limit,
        )
    )

    courses = result.scalars().all()

    return {
        "items": [
            _to_school_admin_course_out(
                course,
            ).model_dump()
            for course in courses
        ],
        "total": int(
            total,
        ),
        "skip": skip,
        "limit": limit,
    }


@router.post(
    "/courses",
    response_model=SchoolAdminCourseOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_school_course(
    payload: SchoolAdminCourseCreate,
    school_id: int | None = Query(
        default=None,
    ),
    db: AsyncSession = Depends(
        get_db,
    ),
    current_user: User = Depends(
        require_role(
            UserRole.SCHOOL_ADMIN,
            UserRole.PLATFORM_ADMIN,
        )
    ),
) -> SchoolAdminCourseOut:
    target_school_id = _resolve_school_scope(
        current_user,
        school_id,
    )

    teacher = await _get_school_teacher(
        db,
        teacher_id=payload.teacher_id,
        school_id=target_school_id,
    )

    if payload.subject_id is not None:
        await _get_school_subject(
            db,
            subject_id=payload.subject_id,
            school_id=target_school_id,
        )

    course = Course(
        title=payload.title.strip(),
        description=_clean_optional_text(
            payload.description,
        ),
        subject_id=payload.subject_id,
        exam_board=_clean_optional_text(
            payload.exam_board,
        ),
        qualification=_clean_optional_text(
            payload.qualification,
        ),
        specification_code=_clean_optional_text(
            payload.specification_code,
        ),
        teacher_id=teacher.id,
        school_id=target_school_id,
        published=payload.published,
    )

    db.add(
        course,
    )

    await db.commit()

    course = await _get_school_course(
        db,
        course_id=course.id,
        school_id=target_school_id,
    )

    return _to_school_admin_course_out(
        course,
    )


@router.patch(
    "/courses/{course_id}",
    response_model=SchoolAdminCourseOut,
)
async def update_school_course(
    course_id: int,
    payload: SchoolAdminCourseUpdate,
    school_id: int | None = Query(
        default=None,
    ),
    db: AsyncSession = Depends(
        get_db,
    ),
    current_user: User = Depends(
        require_role(
            UserRole.SCHOOL_ADMIN,
            UserRole.PLATFORM_ADMIN,
        )
    ),
) -> SchoolAdminCourseOut:
    target_school_id = _resolve_school_scope(
        current_user,
        school_id,
    )

    course = await _get_school_course(
        db,
        course_id=course_id,
        school_id=target_school_id,
    )

    changes = payload.model_dump(
        exclude_unset=True,
    )

    if "teacher_id" in changes:
        teacher_id = changes["teacher_id"]

        if teacher_id is not None:
            teacher = await _get_school_teacher(
                db,
                teacher_id=teacher_id,
                school_id=target_school_id,
            )

            changes["teacher_id"] = teacher.id

    if "subject_id" in changes:
        subject_id = changes["subject_id"]

        if subject_id is not None:
            await _get_school_subject(
                db,
                subject_id=subject_id,
                school_id=target_school_id,
            )

    if "title" in changes:
        title = changes["title"]

        if title is not None:
            changes["title"] = title.strip()

    for field_name in (
        "description",
        "exam_board",
        "qualification",
        "specification_code",
    ):
        if field_name not in changes:
            continue

        changes[field_name] = _clean_optional_text(
            changes[field_name],
        )

    for field_name, value in changes.items():
        setattr(
            course,
            field_name,
            value,
        )

    await db.commit()

    course = await _get_school_course(
        db,
        course_id=course.id,
        school_id=target_school_id,
    )

    return _to_school_admin_course_out(
        course,
    )


@router.post(
    "/users",
    response_model=UserOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_user(
    payload: UserCreate,
    school_id: int | None = Query(
        default=None,
    ),
    db: AsyncSession = Depends(
        get_db,
    ),
    current_user: User = Depends(
        require_role(
            UserRole.SCHOOL_ADMIN,
            UserRole.PLATFORM_ADMIN,
        )
    ),
):
    target_school_id = _resolve_school_scope(
        current_user,
        school_id,
    )

    user = await SchoolUserService.create_user(
        db=db,
        payload=payload,
        school_id=target_school_id,
        actor=current_user,
    )

    await db.commit()

    await db.refresh(
        user,
    )

    return _to_user_out(
        user,
    )


@router.patch(
    "/users/{user_id}",
    response_model=UserOut,
)
async def update_user(
    user_id: int,
    payload: UserUpdate,
    school_id: int | None = Query(
        default=None,
    ),
    db: AsyncSession = Depends(
        get_db,
    ),
    current_user: User = Depends(
        require_role(
            UserRole.SCHOOL_ADMIN,
            UserRole.PLATFORM_ADMIN,
        )
    ),
):
    target_school_id = _resolve_school_scope(
        current_user,
        school_id,
    )

    user = await SchoolUserService.update_user(
        db=db,
        user_id=user_id,
        payload=payload,
        school_id=target_school_id,
        actor=current_user,
    )

    await db.commit()

    await db.refresh(
        user,
    )

    return _to_user_out(
        user,
    )


@router.post(
    "/users/{user_id}/deactivate",
    response_model=UserOut,
)
async def deactivate_user(
    user_id: int,
    school_id: int | None = Query(
        default=None,
    ),
    db: AsyncSession = Depends(
        get_db,
    ),
    current_user: User = Depends(
        require_role(
            UserRole.SCHOOL_ADMIN,
            UserRole.PLATFORM_ADMIN,
        )
    ),
):
    target_school_id = _resolve_school_scope(
        current_user,
        school_id,
    )

    user = await SchoolUserService.deactivate_user(
        db=db,
        user_id=user_id,
        school_id=target_school_id,
        actor=current_user,
    )

    await db.commit()

    await db.refresh(
        user,
    )

    return _to_user_out(
        user,
    )


@router.post(
    "/users/{user_id}/request-erasure",
    response_model=UserOut,
)
async def request_erasure(
    user_id: int,
    school_id: int | None = Query(
        default=None,
    ),
    db: AsyncSession = Depends(
        get_db,
    ),
    current_user: User = Depends(
        require_role(
            UserRole.SCHOOL_ADMIN,
            UserRole.PLATFORM_ADMIN,
        )
    ),
):
    target_school_id = _resolve_school_scope(
        current_user,
        school_id,
    )

    user = await SchoolUserService.request_erasure(
        db=db,
        user_id=user_id,
        school_id=target_school_id,
        actor=current_user,
    )

    await db.commit()

    await db.refresh(
        user,
    )

    return _to_user_out(
        user,
    )


@router.post(
    "/users/{user_id}/anonymise",
    response_model=UserOut,
)
async def anonymise_user(
    user_id: int,
    school_id: int | None = Query(
        default=None,
    ),
    db: AsyncSession = Depends(
        get_db,
    ),
    current_user: User = Depends(
        require_role(
            UserRole.SCHOOL_ADMIN,
            UserRole.PLATFORM_ADMIN,
        )
    ),
):
    target_school_id = _resolve_school_scope(
        current_user,
        school_id,
    )

    user = await SchoolUserService.anonymise_user(
        db=db,
        user_id=user_id,
        school_id=target_school_id,
        actor=current_user,
    )

    await db.commit()

    await db.refresh(
        user,
    )

    return _to_user_out(
        user,
    )
