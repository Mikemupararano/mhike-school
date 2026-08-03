from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.imports.registry import (
    RowProcessingAction,
    RowProcessingResult,
)
from app.models.assignment import Assignment
from app.models.assignment_submission import AssignmentSubmission
from app.models.user import User, UserRole
from app.repositories.assignment import AssignmentRepository
from app.repositories.assignment_submission import (
    AssignmentSubmissionRepository,
)
from app.repositories.course import CourseRepository
from app.repositories.user import UserRepository


def _normalise_string(
    value: Any,
    field_name: str,
) -> str:
    """
    Return a required, trimmed string value.
    """

    if not isinstance(value, str):
        raise ValueError(
            f"Assignment submission import field " f"'{field_name}' is required.",
        )

    cleaned = value.strip()

    if not cleaned:
        raise ValueError(
            f"Assignment submission import field " f"'{field_name}' cannot be blank.",
        )

    return cleaned


def _normalise_optional_string(
    value: Any,
) -> str | None:
    """
    Return a trimmed optional string.

    Blank values are normalised to ``None``.
    """

    if value is None:
        return None

    cleaned = str(value).strip()

    return cleaned or None


def _normalise_email(
    value: Any,
    field_name: str,
) -> str:
    """
    Return a required, lowercase email value.

    Structural email validation belongs to the import validator. This helper
    protects direct processor calls and staged rows created outside the
    normal validation workflow.
    """

    return _normalise_string(
        value,
        field_name,
    ).lower()


def _parse_datetime(
    value: Any,
    field_name: str,
) -> datetime | None:
    """
    Parse an optional ISO datetime value.

    JSON-backed validated rows normally provide strings. Direct processor
    calls may provide ``datetime`` instances.

    A trailing ``Z`` is accepted and interpreted as UTC.
    """

    if value is None:
        return None

    if isinstance(value, datetime):
        return value

    if isinstance(value, str):
        cleaned = value.strip()

        if not cleaned:
            return None

        if cleaned.endswith("Z"):
            cleaned = f"{cleaned[:-1]}+00:00"

        try:
            return datetime.fromisoformat(
                cleaned,
            )
        except ValueError:
            pass

    raise ValueError(
        f"Assignment submission import field '{field_name}' "
        "must be a valid ISO datetime.",
    )


def _utc_now() -> datetime:
    """
    Return the current timezone-aware UTC datetime.
    """

    return datetime.now(
        UTC,
    )


async def _resolve_teacher(
    db: AsyncSession,
    *,
    teacher_email: str,
    school_id: int,
) -> User:
    """
    Resolve and role-check a teacher within the current school.
    """

    normalised_email = _normalise_email(
        teacher_email,
        "teacher_email",
    )

    teacher = await UserRepository(
        db,
    ).get_by_email(
        email=normalised_email,
        school_id=school_id,
    )

    if teacher is None:
        raise ValueError(
            f"No teacher with email '{normalised_email}' exists " "in this school.",
        )

    if not teacher.has_role(
        UserRole.TEACHER,
    ):
        raise ValueError(
            f"The user with email '{normalised_email}' is not "
            "registered as a teacher in this school.",
        )

    return teacher


async def _resolve_student(
    db: AsyncSession,
    *,
    student_email: str,
    school_id: int,
) -> User:
    """
    Resolve and role-check a student within the current school.
    """

    normalised_email = _normalise_email(
        student_email,
        "student_email",
    )

    student = await UserRepository(
        db,
    ).get_by_email(
        email=normalised_email,
        school_id=school_id,
    )

    if student is None:
        raise ValueError(
            f"No student with email '{normalised_email}' exists " "in this school.",
        )

    if not student.has_role(
        UserRole.STUDENT,
    ):
        raise ValueError(
            f"The user with email '{normalised_email}' is not "
            "registered as a student in this school.",
        )

    return student


async def _resolve_course(
    db: AsyncSession,
    *,
    course_title: str,
    teacher: User,
    school_id: int,
):
    """
    Resolve the course referenced by the import row.
    """

    course = await CourseRepository(
        db,
    ).get_by_title_and_teacher(
        title=_normalise_string(
            course_title,
            "course_title",
        ),
        teacher_id=teacher.id,
        school_id=school_id,
        include_relationships=False,
    )

    if course is None:
        raise ValueError(
            f"No course titled '{course_title}' assigned to "
            f"'{teacher.email}' exists in this school.",
        )

    return course


async def _resolve_assignment(
    db: AsyncSession,
    *,
    assignment_title: str,
    course_id: int,
    school_id: int,
) -> Assignment:
    """
    Resolve an assignment belonging to the supplied course.
    """

    assignment = await AssignmentRepository(
        db,
    ).get_by_title_and_course(
        title=_normalise_string(
            assignment_title,
            "assignment_title",
        ),
        course_id=course_id,
        school_id=school_id,
        include_relationships=False,
    )

    if assignment is None:
        raise ValueError(
            f"No assignment titled '{assignment_title}' exists "
            "for the resolved course.",
        )

    return assignment


async def _resolve_grader(
    db: AsyncSession,
    *,
    graded_by_email: str | None,
    school_id: int,
) -> User | None:
    """
    Resolve the grading user if supplied.
    """

    if graded_by_email is None:
        return None

    grader = await UserRepository(
        db,
    ).get_by_email(
        email=_normalise_email(
            graded_by_email,
            "graded_by_email",
        ),
        school_id=school_id,
    )

    if grader is None:
        raise ValueError(
            f"No user with email '{graded_by_email}' exists " "in this school.",
        )

    if not (
        grader.has_role(UserRole.TEACHER)
        or grader.has_role(UserRole.SCHOOL_ADMIN)
        or grader.has_role(UserRole.PLATFORM_ADMIN)
    ):
        raise ValueError(
            f"'{graded_by_email}' is not authorised to grade submissions.",
        )

    return grader


async def process_assignment_submission_row(
    db: AsyncSession,
    row: dict[str, Any],
    school_id: int,
) -> RowProcessingResult:
    """
    Create or update an assignment submission.
    """

    if not isinstance(school_id, int) or isinstance(school_id, bool) or school_id < 1:
        raise ValueError(
            "school_id must be a positive integer.",
        )

    teacher = await _resolve_teacher(
        db,
        teacher_email=row["teacher_email"],
        school_id=school_id,
    )

    student = await _resolve_student(
        db,
        student_email=row["student_email"],
        school_id=school_id,
    )

    course = await _resolve_course(
        db,
        course_title=row["course_title"],
        teacher=teacher,
        school_id=school_id,
    )

    assignment = await _resolve_assignment(
        db,
        assignment_title=row["assignment_title"],
        course_id=course.id,
        school_id=school_id,
    )

    grader = await _resolve_grader(
        db,
        graded_by_email=row.get(
            "graded_by_email",
        ),
        school_id=school_id,
    )

    repository = AssignmentSubmissionRepository(
        db,
    )

    submission = await repository.get_by_assignment_and_student(
        assignment_id=assignment.id,
        student_id=student.id,
        school_id=school_id,
        include_relationships=False,
    )

    status = (
        row.get(
            "status",
            "submitted",
        )
        .strip()
        .lower()
    )

    submitted_at = (
        _parse_datetime(
            row.get("submitted_at"),
            "submitted_at",
        )
        or _utc_now()
    )

    graded_at = _parse_datetime(
        row.get("graded_at"),
        "graded_at",
    )

    if submission is None:
        submission = AssignmentSubmission(
            assignment_id=assignment.id,
            student_id=student.id,
            school_id=school_id,
            submission_text=_normalise_optional_string(
                row.get("submission_text"),
            ),
            attachment_url=_normalise_optional_string(
                row.get("attachment_url"),
            ),
            status=status,
            submitted_at=submitted_at,
            score=row.get("score"),
            feedback=_normalise_optional_string(
                row.get("feedback"),
            ),
            graded_by=(grader.id if grader is not None else None),
            graded_at=graded_at,
        )

        submission = await repository.create(
            submission,
        )

        return RowProcessingResult(
            action=RowProcessingAction.CREATED,
            entity_id=submission.id,
            message="Assignment submission created.",
        )

    submission.submission_text = _normalise_optional_string(
        row.get("submission_text"),
    )
    submission.attachment_url = _normalise_optional_string(
        row.get("attachment_url"),
    )
    submission.status = status
    submission.submitted_at = submitted_at
    submission.score = row.get("score")
    submission.feedback = _normalise_optional_string(
        row.get("feedback"),
    )
    submission.graded_by = grader.id if grader is not None else None
    submission.graded_at = graded_at

    submission = await repository.save(
        submission,
    )

    return RowProcessingResult(
        action=RowProcessingAction.UPDATED,
        entity_id=submission.id,
        message="Assignment submission updated.",
    )
