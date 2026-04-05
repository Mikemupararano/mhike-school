from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
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


@router.post("", response_model=AssignmentOut, status_code=status.HTTP_201_CREATED)
async def create_assignment_endpoint(
    payload: AssignmentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in {"teacher", "admin", "platform_admin"}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only teachers or admins can create assignments",
        )

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
    if current_user.role not in {"teacher", "admin", "platform_admin"}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only teachers or admins can view this resource",
        )

    return await get_teacher_assignments(db, current_user)


@router.get("/my", response_model=list[AssignmentOut])
async def list_my_student_assignments(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "student":
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
    assignment = await get_assignment(db, assignment_id)

    if current_user.role == "platform_admin":
        return assignment

    if assignment.school_id != current_user.school_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Assignment does not belong to your school",
        )

    return assignment


@router.patch("/{assignment_id}", response_model=AssignmentOut)
async def update_assignment_endpoint(
    assignment_id: int,
    payload: AssignmentUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in {"teacher", "admin", "platform_admin"}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only teachers or admins can update assignments",
        )

    assignment = await get_assignment(db, assignment_id)

    if current_user.role == "teacher" and assignment.created_by != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only update your own assignments",
        )

    if (
        current_user.role != "platform_admin"
        and assignment.school_id != current_user.school_id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Assignment does not belong to your school",
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
    if current_user.role not in {"teacher", "admin", "platform_admin"}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only teachers or admins can publish assignments",
        )

    assignment = await get_assignment(db, assignment_id)

    if current_user.role == "teacher" and assignment.created_by != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only publish your own assignments",
        )

    if (
        current_user.role != "platform_admin"
        and assignment.school_id != current_user.school_id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Assignment does not belong to your school",
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
    if current_user.role not in {"teacher", "admin", "platform_admin"}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only teachers or admins can delete assignments",
        )

    assignment = await get_assignment(db, assignment_id)

    if current_user.role == "teacher" and assignment.created_by != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only delete your own assignments",
        )

    if (
        current_user.role != "platform_admin"
        and assignment.school_id != current_user.school_id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Assignment does not belong to your school",
        )

    await db.delete(assignment)
    await db.commit()

    return Response(status_code=status.HTTP_204_NO_CONTENT)
