from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.permissions import PermissionService
from app.db.session import get_db
from app.models.assignment import Assignment
from app.models.assignment_submission import AssignmentSubmission
from app.models.parent_student import ParentStudent
from app.models.user import User, UserRole
from app.schemas.assignment_submission import (
    AssignmentSubmissionGrade,
    AssignmentSubmissionOut,
    AssignmentSubmissionSubmit,
)
from app.schemas.parent_grades import ParentGradeOut
from app.services.assignment_submission_service import (
    grade_submission,
    submit_assignment,
)

router = APIRouter()


@router.post(
    "/{assignment_id}/submit",
    response_model=AssignmentSubmissionOut,
    status_code=status.HTTP_201_CREATED,
)
async def submit_assignment_endpoint(
    assignment_id: int,
    payload: AssignmentSubmissionSubmit,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    PermissionService.ensure_active_user(current_user)
    PermissionService.ensure_has_role(current_user, UserRole.STUDENT)

    return await submit_assignment(
        db=db,
        current_user=current_user,
        assignment_id=assignment_id,
        submission_text=payload.submission_text,
        attachment_url=payload.attachment_url,
    )


@router.get(
    "/parent/grades",
    response_model=list[ParentGradeOut],
)
async def list_parent_grades_endpoint(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    PermissionService.ensure_active_user(current_user)
    PermissionService.ensure_has_role(current_user, UserRole.PARENT)

    result = await db.execute(
        select(
            AssignmentSubmission.id.label("submission_id"),
            AssignmentSubmission.assignment_id,
            AssignmentSubmission.student_id,
            Assignment.title.label("assignment_title"),
            Assignment.max_score,
            AssignmentSubmission.score,
            AssignmentSubmission.feedback,
            AssignmentSubmission.status,
            AssignmentSubmission.submitted_at,
            AssignmentSubmission.graded_at,
        )
        .join(
            Assignment,
            Assignment.id == AssignmentSubmission.assignment_id,
        )
        .join(
            ParentStudent,
            ParentStudent.student_id == AssignmentSubmission.student_id,
        )
        .where(
            ParentStudent.parent_id == current_user.id,
            AssignmentSubmission.school_id == current_user.school_id,
        )
        .order_by(AssignmentSubmission.submitted_at.desc())
    )

    return list(result.mappings().all())


@router.get("/{assignment_id}/me", response_model=AssignmentSubmissionOut)
async def get_my_submission_for_assignment(
    assignment_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    PermissionService.ensure_active_user(current_user)
    PermissionService.ensure_has_role(current_user, UserRole.STUDENT)

    result = await db.execute(
        select(AssignmentSubmission).where(
            AssignmentSubmission.assignment_id == assignment_id,
            AssignmentSubmission.student_id == current_user.id,
        )
    )
    submission = result.scalar_one_or_none()

    if not submission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Submission not found",
        )

    PermissionService.ensure_same_school(current_user, submission.school_id)

    return submission


@router.get(
    "/assignment/{assignment_id}",
    response_model=list[AssignmentSubmissionOut],
)
async def list_submissions_for_assignment(
    assignment_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    PermissionService.ensure_active_user(current_user)
    PermissionService.ensure_can_teach(current_user)

    assignment = await db.get(Assignment, assignment_id)

    if not assignment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assignment not found",
        )

    PermissionService.ensure_same_school(current_user, assignment.school_id)

    if current_user.is_teacher and not current_user.is_school_admin:
        if assignment.created_by != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only view submissions for your own assignments",
            )

    result = await db.execute(
        select(AssignmentSubmission)
        .where(AssignmentSubmission.assignment_id == assignment_id)
        .order_by(AssignmentSubmission.submitted_at.desc())
    )

    return list(result.scalars().all())


@router.post(
    "/{submission_id}/grade",
    response_model=AssignmentSubmissionOut,
)
async def grade_submission_endpoint(
    submission_id: int,
    payload: AssignmentSubmissionGrade,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    PermissionService.ensure_active_user(current_user)
    PermissionService.ensure_can_teach(current_user)

    return await grade_submission(
        db=db,
        submission_id=submission_id,
        current_user=current_user,
        score=payload.score if payload.score is not None else 0,
        feedback=payload.feedback,
    )
