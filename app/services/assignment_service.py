from __future__ import annotations

from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.assignment import Assignment
from app.models.user import User, UserRole
from app.repositories.assignment import AssignmentRepository
from app.repositories.course import CourseRepository


def has_role(
    user: User,
    role: UserRole,
) -> bool:
    """
    Return whether the user currently has the supplied role.
    """

    return role.value in set(user.roles)


def is_platform_admin(
    user: User,
) -> bool:
    return has_role(
        user,
        UserRole.PLATFORM_ADMIN,
    )


def is_school_admin(
    user: User,
) -> bool:
    return has_role(
        user,
        UserRole.SCHOOL_ADMIN,
    )


def is_teacher_without_admin_scope(
    user: User,
) -> bool:
    return (
        has_role(
            user,
            UserRole.TEACHER,
        )
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
    """
    Create an assignment for a course the current user may manage.

    Teachers may create assignments only for their own courses. School
    administrators may create assignments for courses in their own school.
    Platform administrators may create assignments across schools.

    Transaction ownership remains with this service because the existing API
    contract commits assignment creation here.
    """

    course_repository = CourseRepository(
        db,
    )

    course = await course_repository.get_by_id(
        course_id,
        include_relationships=False,
    )

    if course is None:
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
        course_id=course.id,
        school_id=course.school_id,
        created_by=current_user.id,
        is_published=False,
    )

    repository = AssignmentRepository(
        db,
    )

    try:
        assignment = await repository.create(
            assignment,
        )
        await db.commit()
        await db.refresh(
            assignment,
        )
    except Exception:
        await db.rollback()
        raise

    return assignment


async def get_teacher_assignments(
    db: AsyncSession,
    current_user: User,
) -> list[Assignment]:
    """
    Return assignments visible to a teacher or administrator.

    - Teachers without admin scope see only assignments they created.
    - School administrators see all assignments in their school.
    - Platform administrators see all assignments across schools.
    """

    repository = AssignmentRepository(
        db,
    )

    if is_teacher_without_admin_scope(current_user):
        return await repository.list_by_creator(
            current_user.id,
        )

    if not is_platform_admin(current_user):
        if current_user.school_id is None:
            return []

        return await repository.list_by_school(
            current_user.school_id,
        )

    return await repository.list_all()


async def get_student_assignments(
    db: AsyncSession,
    current_user: User,
) -> list[Assignment]:
    """
    Return published assignments for the student's school.
    """

    if current_user.school_id is None:
        return []

    repository = AssignmentRepository(
        db,
    )

    return await repository.list_published_for_school(
        current_user.school_id,
    )


async def get_assignment(
    db: AsyncSession,
    assignment_id: int,
) -> Assignment:
    """
    Return an assignment or raise a 404 response.
    """

    assignment = await AssignmentRepository(
        db,
    ).get_by_id(
        assignment_id,
    )

    if assignment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assignment not found",
        )

    return assignment
