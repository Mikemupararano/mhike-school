from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.permissions import PermissionService
from app.db.session import get_db
from app.models.user import User, UserRole
from app.schemas.assignment import (
    AssignmentCreate,
    AssignmentOut,
    AssignmentPublishIn,
    AssignmentUpdate,
)
from app.services.assignment_service import (
    create_assignment,
    get_assignment,
    get_student_assignments,
    get_teacher_assignments,
)

router = APIRouter()


def has_role(user: User, role: UserRole) -> bool:
    return role.value in set(user.roles)


def is_platform_admin(user: User) -> bool:
    return has_role(user, UserRole.PLATFORM_ADMIN)


def is_teacher_only_for_assignment(user: User, assignment_created_by: int) -> bool:
    return (
        has_role(user, UserRole.TEACHER)
        and not has_role(user, UserRole.SCHOOL_ADMIN)
        and not has_role(user, UserRole.PLATFORM_ADMIN)
        and assignment_created_by != user.id
    )


def ensure_assignment_school_access(user: User, assignment_school_id: int) -> None:
    if is_platform_admin(user):
        return

    if assignment_school_id != user.school_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Assignment does not belong to your school",
        )


@router.post("", response_model=AssignmentOut, status_code=status.HTTP_201_CREATED)
async def create_assignment_endpoint(
    payload: AssignmentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    PermissionService.ensure_active_user(current_user)
    PermissionService.ensure_can_teach(current_user)

    return await create_assignment(
        db=db,
        current_user=current_user,
        course_id=payload.course_id,
        title=payload.title,
        description=payload.description,
        due_date=payload.due_date,
        max_score=payload.max_score,
    )


@router.get("/me", response_model=list[AssignmentOut])
async def list_my_teacher_assignments(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    PermissionService.ensure_active_user(current_user)
    PermissionService.ensure_can_teach(current_user)

    return await get_teacher_assignments(db, current_user)


@router.get("/my", response_model=list[AssignmentOut])
async def list_my_student_assignments(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    PermissionService.ensure_active_user(current_user)

    if not has_role(current_user, UserRole.STUDENT):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only students can view this resource",
        )

    return await get_student_assignments(db, current_user)


@router.get("/{assignment_id}", response_model=AssignmentOut)
async def get_assignment_endpoint(
    assignment_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    PermissionService.ensure_active_user(current_user)

    assignment = await get_assignment(db, assignment_id)
    ensure_assignment_school_access(current_user, assignment.school_id)

    return assignment


@router.patch("/{assignment_id}", response_model=AssignmentOut)
async def update_assignment_endpoint(
    assignment_id: int,
    payload: AssignmentUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    PermissionService.ensure_active_user(current_user)
    PermissionService.ensure_can_teach(current_user)

    assignment = await get_assignment(db, assignment_id)
    ensure_assignment_school_access(current_user, assignment.school_id)

    if is_teacher_only_for_assignment(current_user, assignment.created_by):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only update your own assignments",
        )

    if payload.title is not None:
        assignment.title = payload.title
    if payload.description is not None:
        assignment.description = payload.description
    if payload.due_date is not None:
        assignment.due_date = payload.due_date
    if payload.max_score is not None:
        assignment.max_score = payload.max_score
    if payload.is_published is not None:
        assignment.is_published = payload.is_published

    await db.commit()
    await db.refresh(assignment)

    return assignment


@router.post("/{assignment_id}/publish", response_model=AssignmentOut)
async def publish_assignment_endpoint(
    assignment_id: int,
    payload: AssignmentPublishIn,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    PermissionService.ensure_active_user(current_user)
    PermissionService.ensure_can_teach(current_user)

    assignment = await get_assignment(db, assignment_id)
    ensure_assignment_school_access(current_user, assignment.school_id)

    if is_teacher_only_for_assignment(current_user, assignment.created_by):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only publish your own assignments",
        )

    assignment.is_published = payload.is_published

    await db.commit()
    await db.refresh(assignment)

    return assignment


@router.delete("/{assignment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_assignment_endpoint(
    assignment_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    PermissionService.ensure_active_user(current_user)
    PermissionService.ensure_can_teach(current_user)

    assignment = await get_assignment(db, assignment_id)
    ensure_assignment_school_access(current_user, assignment.school_id)

    if is_teacher_only_for_assignment(current_user, assignment.created_by):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only delete your own assignments",
        )

    await db.delete(assignment)
    await db.commit()

    return Response(status_code=status.HTTP_204_NO_CONTENT)
