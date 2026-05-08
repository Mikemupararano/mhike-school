from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.assignment import Assignment
from app.models.course import Course
from app.models.user import User, UserRole


def has_role(user: User, role: UserRole) -> bool:
    return role.value in set(user.roles)


def is_platform_admin(user: User) -> bool:
    return has_role(user, UserRole.PLATFORM_ADMIN)


def is_school_admin(user: User) -> bool:
    return has_role(user, UserRole.SCHOOL_ADMIN)


def is_teacher_without_admin_scope(user: User) -> bool:
    return (
        has_role(user, UserRole.TEACHER)
        and not is_school_admin(user)
        and not is_platform_admin(user)
    )


async def create_assignment(
    db: AsyncSession,
    current_user: User,
    course_id: int,
    title: str,
    description: str | None,
    due_date: datetime | None,
    max_score: int,
) -> Assignment:
    course = await db.get(Course, course_id)
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found",
        )

    if (
        is_teacher_without_admin_scope(current_user)
        and course.teacher_id != current_user.id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only create assignments for your own courses",
        )

    if (
        not is_platform_admin(current_user)
        and course.school_id != current_user.school_id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Course does not belong to your school",
        )

    assignment = Assignment(
        title=title,
        description=description,
        due_date=due_date,
        max_score=max_score,
        course_id=course_id,
        school_id=course.school_id,
        created_by=current_user.id,
        is_published=False,
    )

    db.add(assignment)
    await db.commit()
    await db.refresh(assignment)

    return assignment


async def get_teacher_assignments(
    db: AsyncSession,
    current_user: User,
) -> list[Assignment]:
    query = select(Assignment)

    if is_teacher_without_admin_scope(current_user):
        query = query.where(Assignment.created_by == current_user.id)
    elif not is_platform_admin(current_user):
        query = query.where(Assignment.school_id == current_user.school_id)

    result = await db.execute(query.order_by(Assignment.created_at.desc()))
    return list(result.scalars().all())


async def get_student_assignments(
    db: AsyncSession,
    current_user: User,
) -> list[Assignment]:
    result = await db.execute(
        select(Assignment)
        .where(
            Assignment.school_id == current_user.school_id,
            Assignment.is_published.is_(True),
        )
        .order_by(Assignment.created_at.desc())
    )
    return list(result.scalars().all())


async def get_assignment(
    db: AsyncSession,
    assignment_id: int,
) -> Assignment:
    assignment = await db.get(Assignment, assignment_id)
    if not assignment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assignment not found",
        )
    return assignment
