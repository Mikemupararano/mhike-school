from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.assignment import Assignment
from app.models.assignment_submission import AssignmentSubmission
from app.models.user import User


async def submit_assignment(
    db: AsyncSession,
    current_user: User,
    assignment_id: int,
    submission_text: str | None,
    attachment_url: str | None,
) -> AssignmentSubmission:
    assignment = await db.get(Assignment, assignment_id)
    if not assignment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assignment not found",
        )

    if current_user.role != "student":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only students can submit assignments",
        )

    if assignment.school_id != current_user.school_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Assignment does not belong to your school",
        )

    if not assignment.is_published:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Assignment is not published",
        )

    existing_result = await db.execute(
        select(AssignmentSubmission).where(
            AssignmentSubmission.assignment_id == assignment_id,
            AssignmentSubmission.student_id == current_user.id,
        )
    )
    existing_submission = existing_result.scalar_one_or_none()

    if existing_submission:
        existing_submission.submission_text = submission_text
        existing_submission.attachment_url = attachment_url
        existing_submission.status = "submitted"
        existing_submission.submitted_at = datetime.now(timezone.utc)

        await db.commit()
        await db.refresh(existing_submission)
        return existing_submission

    submission = AssignmentSubmission(
        assignment_id=assignment_id,
        student_id=current_user.id,
        school_id=current_user.school_id,
        submission_text=submission_text,
        attachment_url=attachment_url,
        status="submitted",
        submitted_at=datetime.now(timezone.utc),
    )

    db.add(submission)
    await db.commit()
    await db.refresh(submission)

    return submission


async def grade_submission(
    db: AsyncSession,
    submission_id: int,
    current_user: User,
    score: int,
    feedback: str | None,
) -> AssignmentSubmission:
    submission = await db.get(AssignmentSubmission, submission_id)
    if not submission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Submission not found",
        )

    assignment = await db.get(Assignment, submission.assignment_id)
    if not assignment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assignment not found",
        )

    if current_user.role not in {"teacher", "admin", "platform_admin"}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only teachers or admins can grade submissions",
        )

    if (
        current_user.role != "platform_admin"
        and submission.school_id != current_user.school_id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Submission does not belong to your school",
        )

    if current_user.role == "teacher" and assignment.created_by != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only grade submissions for your own assignments",
        )

    if score < 0 or score > assignment.max_score:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Score must be between 0 and {assignment.max_score}",
        )

    submission.score = score
    submission.feedback = feedback
    submission.status = "graded"
    submission.graded_by = current_user.id
    submission.graded_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(submission)

    return submission
