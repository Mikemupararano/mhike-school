from __future__ import annotations

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    get_current_school_id,
    get_current_user,
)
from app.core.permissions import PermissionService
from app.db.session import get_db
from app.models.course import Course
from app.models.subject import Subject
from app.models.user import User
from app.schemas.course import (
    CourseCreate,
    CourseOut,
    CourseUpdate,
)

router = APIRouter()


async def _get_school_subject(
    db: AsyncSession,
    *,
    subject_id: int,
    school_id: int,
) -> Subject:
    """
    Return a subject only when it belongs to the current school.
    """

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


async def _get_owned_course(
    db: AsyncSession,
    *,
    course_id: int,
    school_id: int,
    teacher_id: int,
) -> Course:
    """
    Return a course owned by the current teacher in the current school.
    """

    result = await db.execute(
        select(Course).where(
            Course.id == course_id,
            Course.school_id == school_id,
            Course.teacher_id == teacher_id,
        )
    )

    course = result.scalar_one_or_none()

    if course is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found.",
        )

    return course


@router.get(
    "/me",
    response_model=list[CourseOut],
)
async def get_my_courses(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    school_id: int = Depends(get_current_school_id),
) -> list[CourseOut]:
    """
    Return courses owned by the current teacher in the current school.
    """

    PermissionService.ensure_active_user(
        current_user,
    )
    PermissionService.ensure_can_teach(
        current_user,
    )

    result = await db.execute(
        select(Course)
        .where(
            Course.teacher_id == current_user.id,
            Course.school_id == school_id,
        )
        .order_by(
            Course.title.asc(),
            Course.id.asc(),
        )
    )

    courses = result.scalars().all()

    return [CourseOut.model_validate(course) for course in courses]


@router.post(
    "",
    response_model=CourseOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_course(
    payload: CourseCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    school_id: int = Depends(get_current_school_id),
) -> CourseOut:
    """
    Create a teacher-owned course in the current school.

    New courses remain unpublished by default.
    """

    PermissionService.ensure_active_user(
        current_user,
    )
    PermissionService.ensure_can_teach(
        current_user,
    )

    if payload.subject_id is not None:
        await _get_school_subject(
            db,
            subject_id=payload.subject_id,
            school_id=school_id,
        )

    course = Course(
        title=payload.title.strip(),
        description=(
            payload.description.strip()
            if payload.description is not None and payload.description.strip()
            else None
        ),
        subject_id=payload.subject_id,
        exam_board=(
            payload.exam_board.strip()
            if payload.exam_board is not None and payload.exam_board.strip()
            else None
        ),
        qualification=(
            payload.qualification.strip()
            if payload.qualification is not None and payload.qualification.strip()
            else None
        ),
        specification_code=(
            payload.specification_code.strip()
            if payload.specification_code is not None
            and payload.specification_code.strip()
            else None
        ),
        teacher_id=current_user.id,
        school_id=school_id,
        published=False,
    )

    db.add(course)

    await db.commit()
    await db.refresh(course)

    return CourseOut.model_validate(course)


@router.patch(
    "/{course_id}",
    response_model=CourseOut,
)
async def update_course(
    course_id: int,
    payload: CourseUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    school_id: int = Depends(get_current_school_id),
) -> CourseOut:
    """
    Update a course owned by the current teacher.

    Subjects must belong to the same school.
    """

    PermissionService.ensure_active_user(
        current_user,
    )
    PermissionService.ensure_can_teach(
        current_user,
    )

    course = await _get_owned_course(
        db,
        course_id=course_id,
        school_id=school_id,
        teacher_id=current_user.id,
    )

    changes = payload.model_dump(
        exclude_unset=True,
    )

    if "subject_id" in changes:
        subject_id = changes["subject_id"]

        if subject_id is not None:
            await _get_school_subject(
                db,
                subject_id=subject_id,
                school_id=school_id,
            )

    if "title" in changes:
        changes["title"] = changes["title"].strip()

    for field_name in (
        "description",
        "exam_board",
        "qualification",
        "specification_code",
    ):
        if field_name not in changes:
            continue

        value = changes[field_name]

        if value is None:
            continue

        cleaned = value.strip()

        changes[field_name] = cleaned if cleaned else None

    for field_name, value in changes.items():
        setattr(
            course,
            field_name,
            value,
        )

    await db.commit()
    await db.refresh(course)

    return CourseOut.model_validate(course)
