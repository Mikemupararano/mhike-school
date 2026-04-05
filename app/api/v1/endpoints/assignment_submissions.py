from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.assignment import Assignment
from app.models.assignment_submission import AssignmentSubmission
from app.models.user import User
from app.schemas.assignment_submission import (
    AssignmentSubmissionGrade,
    AssignmentSubmissionOut,
    AssignmentSubmissionSubmit,
)
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
    if current_user.role != "student":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only students can submit assignments",
        )

    return await submit_assignment(
        db=db,
        current_user=current_user,
        assignment_id=assignment_id,
        submission_text=payload.submission_text,
        attachment_url=payload.attachment_url,
    )


@router.get("/{assignment_id}/me", response_model=AssignmentSubmissionOut)
async def get_my_submission_for_assignment(
    assignment_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "student":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only students can view their own submission",
        )

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

    if submission.school_id != current_user.school_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Submission does not belong to your school",
        )

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
    if current_user.role not in {"teacher", "admin", "platform_admin"}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only teachers or admins can view submissions",
        )

    assignment = await db.get(Assignment, assignment_id)
    if not assignment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assignment not found",
        )

    if (
        current_user.role != "platform_admin"
        and assignment.school_id != current_user.school_id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Assignment does not belong to your school",
        )

    if current_user.role == "teacher" and assignment.created_by != current_user.id:
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
    if current_user.role not in {"teacher", "admin", "platform_admin"}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only teachers or admins can grade submissions",
        )

    return await grade_submission(
        db=db,
        submission_id=submission_id,
        current_user=current_user,
        score=payload.score if payload.score is not None else 0,
        feedback=payload.feedback,
    )
