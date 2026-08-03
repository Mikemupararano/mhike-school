from __future__ import annotations

from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import PermissionService
from app.models.assignment_submission import AssignmentSubmission
from app.models.user import User, UserRole
from app.repositories.assignment import AssignmentRepository
from app.repositories.assignment_submission import (
    AssignmentSubmissionRepository,
)


async def submit_assignment(
    db: AsyncSession,
    current_user: User,
    assignment_id: int,
    submission_text: str | None,
    attachment_url: str | None,
) -> AssignmentSubmission:
    """
    Create or update a student's submission for a published assignment.

    Students may submit only to assignments belonging to their own school.
    Repeated submissions update the existing record rather than creating a
    duplicate.

    Transaction ownership remains with this service to preserve the existing
    API behaviour.
    """

    PermissionService.ensure_active_user(
        current_user,
    )
    PermissionService.ensure_has_role(
        current_user,
        UserRole.STUDENT,
    )

    assignment = await AssignmentRepository(
        db,
    ).get_by_id(
        assignment_id,
        include_relationships=False,
    )

    if assignment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assignment not found",
        )

    PermissionService.ensure_same_school(
        current_user,
        assignment.school_id,
    )

    if not assignment.is_published:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Assignment is not published",
        )

    if current_user.school_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is not linked to a school",
        )

    repository = AssignmentSubmissionRepository(
        db,
    )

    existing_submission = await repository.get_by_assignment_and_student(
        assignment_id=assignment.id,
        student_id=current_user.id,
        school_id=current_user.school_id,
        include_relationships=False,
    )

    submitted_at = datetime.now(
        timezone.utc,
    )

    try:
        if existing_submission is not None:
            existing_submission.submission_text = submission_text
            existing_submission.attachment_url = attachment_url
            existing_submission.status = "submitted"
            existing_submission.submitted_at = submitted_at

            submission = await repository.save(
                existing_submission,
            )
        else:
            submission = AssignmentSubmission(
                assignment_id=assignment.id,
                student_id=current_user.id,
                school_id=current_user.school_id,
                submission_text=submission_text,
                attachment_url=attachment_url,
                status="submitted",
                submitted_at=submitted_at,
            )

            submission = await repository.create(
                submission,
            )

        await db.commit()
        await db.refresh(
            submission,
        )

        return submission

    except Exception:
        await db.rollback()
        raise


async def grade_submission(
    db: AsyncSession,
    submission_id: int,
    current_user: User,
    score: int,
    feedback: str | None,
) -> AssignmentSubmission:
    """
    Grade an assignment submission.

    Teachers without school-admin scope may grade only submissions belonging
    to assignments they created. School administrators and other authorised
    teaching users retain the existing broader permissions.

    Scores must remain between zero and the assignment's maximum score.

    Transaction ownership remains with this service to preserve the existing
    API behaviour.
    """

    PermissionService.ensure_active_user(
        current_user,
    )
    PermissionService.ensure_can_teach(
        current_user,
    )

    submission_repository = AssignmentSubmissionRepository(
        db,
    )

    submission = await submission_repository.get_by_id(
        submission_id,
        include_relationships=False,
    )

    if submission is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Submission not found",
        )

    assignment = await AssignmentRepository(
        db,
    ).get_by_id(
        submission.assignment_id,
        include_relationships=False,
    )

    if assignment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assignment not found",
        )

    PermissionService.ensure_same_school(
        current_user,
        submission.school_id,
    )

    if (
        current_user.is_teacher
        and not current_user.is_school_admin
        and assignment.created_by != current_user.id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=("You can only grade submissions for your own assignments"),
        )

    if score < 0 or score > assignment.max_score:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(f"Score must be between 0 and {assignment.max_score}"),
        )

    submission.score = score
    submission.feedback = feedback
    submission.status = "graded"
    submission.graded_by = current_user.id
    submission.graded_at = datetime.now(
        timezone.utc,
    )

    try:
        submission = await submission_repository.save(
            submission,
        )

        await db.commit()
        await db.refresh(
            submission,
        )

        return submission

    except Exception:
        await db.rollback()
        raise
