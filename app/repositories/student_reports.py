from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.class_group import ClassGroup
from app.models.enrollment import Enrollment
from app.models.report_session import ReportSession
from app.models.student_report import StudentReport
from app.models.user import User
from app.schemas.report_memory import ReportMemoryCreate
from app.schemas.student_report import (
    StudentReportCreate,
    StudentReportUpdate,
)
from app.services.report_memory import create_report_memory

# ---------------------------------------------------------------------------
# Workflow statuses
# ---------------------------------------------------------------------------

REPORT_STATUS_DRAFT = "draft"
REPORT_STATUS_SUBMITTED = "submitted"
REPORT_STATUS_TUTOR_REVIEW = "tutor_review"
REPORT_STATUS_RETURNED_BY_TUTOR = "returned_by_tutor"
REPORT_STATUS_READY_FOR_SMT = "ready_for_smt"
REPORT_STATUS_RETURNED_BY_SMT = "returned_by_smt"
REPORT_STATUS_APPROVED = "approved"
REPORT_STATUS_PUBLISHED = "published"


TEACHER_EDITABLE_STATUSES = {
    REPORT_STATUS_DRAFT,
    REPORT_STATUS_RETURNED_BY_TUTOR,
    REPORT_STATUS_RETURNED_BY_SMT,
}

TUTOR_REVIEWABLE_STATUSES = {
    REPORT_STATUS_SUBMITTED,
    REPORT_STATUS_TUTOR_REVIEW,
}

SMT_REVIEWABLE_STATUSES = {
    REPORT_STATUS_SUBMITTED,
    REPORT_STATUS_READY_FOR_SMT,
}


# ---------------------------------------------------------------------------
# Teacher-editable fields
# ---------------------------------------------------------------------------

STUDENT_REPORT_EDITABLE_FIELDS = {
    # Identification
    "title",
    "academic_year",
    "term",
    "checkpoint_name",
    "subject_name",
    # Main report content
    "report_text",
    "work_covered",
    "teacher_notes",
    "generated_report_text",
    "next_steps",
    # Legacy and structured grades
    "grade",
    "attainment_grade",
    "effort_grade",
    "target_grade",
    "exam_grade",
    "exam_mark",
    "exam_max_mark",
    "ucas_predicted_grade",
    # Additional reporting comments
    "tutor_comment",
    "head_of_year_comment",
    "headteacher_comment",
    # Ownership/session fields currently supported by the update schema
    "teacher_id",
    "report_session_id",
}


PROTECTED_WORKFLOW_FIELDS = {
    "school_id",
    "student_id",
    "status",
    "submitted_at",
    "submitted_by_id",
    "tutor_reviewed_at",
    "tutor_reviewed_by_id",
    "tutor_review_comments",
    "ready_for_smt_at",
    "ready_for_smt_by_id",
    "reviewed_at",
    "reviewed_by_id",
    "review_comments",
    "head_of_year_reviewed_at",
    "head_of_year_reviewed_by_id",
    "headteacher_reviewed_at",
    "headteacher_reviewed_by_id",
    "published",
    "published_at",
    "published_by_id",
    "created_at",
    "updated_at",
}


# ---------------------------------------------------------------------------
# General helpers
# ---------------------------------------------------------------------------


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _clean_optional_text(value: str | None) -> str | None:
    if value is None:
        return None

    cleaned = value.strip()
    return cleaned or None


def _set_model_value(
    instance: Any,
    field_name: str,
    value: Any,
) -> None:
    """
    Set a value only when the SQLAlchemy model currently exposes the field.

    This helps the repository remain usable during staged migrations where
    the schema may be updated immediately before every database column has
    been introduced.
    """

    if hasattr(instance, field_name):
        setattr(instance, field_name, value)


def _get_model_value(
    instance: Any,
    field_name: str,
    default: Any = None,
) -> Any:
    return getattr(instance, field_name, default)


def _clear_publication_fields(report: StudentReport) -> None:
    report.published = False
    report.published_at = None
    report.published_by_id = None


def _clear_smt_review_fields(report: StudentReport) -> None:
    report.reviewed_at = None
    report.reviewed_by_id = None
    report.review_comments = None


def _clear_tutor_review_fields(report: StudentReport) -> None:
    report.tutor_reviewed_at = None
    report.tutor_reviewed_by_id = None
    report.tutor_review_comments = None
    report.ready_for_smt_at = None
    report.ready_for_smt_by_id = None


def _clear_head_of_year_review_fields(
    report: StudentReport,
) -> None:
    _set_model_value(
        report,
        "head_of_year_reviewed_at",
        None,
    )
    _set_model_value(
        report,
        "head_of_year_reviewed_by_id",
        None,
    )


def _clear_headteacher_review_fields(
    report: StudentReport,
) -> None:
    _set_model_value(
        report,
        "headteacher_reviewed_at",
        None,
    )
    _set_model_value(
        report,
        "headteacher_reviewed_by_id",
        None,
    )


def _clear_all_review_fields(report: StudentReport) -> None:
    _clear_tutor_review_fields(report)
    _clear_smt_review_fields(report)
    _clear_head_of_year_review_fields(report)
    _clear_headteacher_review_fields(report)


# ---------------------------------------------------------------------------
# Backward-compatibility helpers
# ---------------------------------------------------------------------------


def _synchronise_legacy_fields(report: StudentReport) -> None:
    """
    Keep legacy fields populated while the frontend and database migrate to
    the richer Reporting V2 field structure.

    Preferred fields:
        attainment_grade
        checkpoint_name

    Legacy fields:
        grade
        term
    """

    grade = _get_model_value(report, "grade")
    attainment_grade = _get_model_value(
        report,
        "attainment_grade",
    )

    if attainment_grade is not None:
        _set_model_value(
            report,
            "grade",
            attainment_grade,
        )
    elif grade is not None:
        _set_model_value(
            report,
            "attainment_grade",
            grade,
        )

    term = _get_model_value(report, "term")
    checkpoint_name = _get_model_value(
        report,
        "checkpoint_name",
    )

    if checkpoint_name is not None:
        _set_model_value(
            report,
            "term",
            checkpoint_name,
        )
    elif term is not None:
        _set_model_value(
            report,
            "checkpoint_name",
            term,
        )


def _apply_payload_to_report(
    report: StudentReport,
    payload_data: dict[str, Any],
) -> None:
    """
    Apply only recognised teacher-editable values to the report.
    """

    for field_name, value in payload_data.items():
        if field_name in PROTECTED_WORKFLOW_FIELDS:
            continue

        if field_name not in STUDENT_REPORT_EDITABLE_FIELDS:
            continue

        _set_model_value(
            report,
            field_name,
            value,
        )

    _synchronise_legacy_fields(report)


# ---------------------------------------------------------------------------
# Report-session helpers
# ---------------------------------------------------------------------------


async def _get_report_session(
    db: AsyncSession,
    *,
    school_id: int,
    report_session_id: int | None,
) -> ReportSession | None:
    if report_session_id is None:
        return None

    result = await db.execute(
        select(ReportSession).where(
            ReportSession.id == report_session_id,
            ReportSession.school_id == school_id,
        ),
    )

    report_session = result.scalar_one_or_none()

    if report_session is None:
        raise ValueError("The selected report session does not exist for this school.")

    return report_session


def _session_option_enabled(
    report_session: ReportSession | None,
    option_name: str,
) -> bool:
    if report_session is None:
        return False

    return bool(
        getattr(
            report_session,
            option_name,
            False,
        )
    )


def _session_is_active(
    report_session: ReportSession | None,
) -> bool:
    if report_session is None:
        return True

    return bool(
        getattr(
            report_session,
            "active",
            True,
        )
    )


def _apply_session_defaults(
    report: StudentReport,
    report_session: ReportSession | None,
) -> None:
    if report_session is None:
        return

    session_academic_year = getattr(
        report_session,
        "academic_year",
        None,
    )

    session_checkpoint_name = getattr(
        report_session,
        "checkpoint_name",
        None,
    )

    session_term = getattr(
        report_session,
        "term",
        None,
    )

    if session_academic_year:
        _set_model_value(
            report,
            "academic_year",
            session_academic_year,
        )

    checkpoint_name = session_checkpoint_name or session_term

    if checkpoint_name:
        _set_model_value(
            report,
            "checkpoint_name",
            checkpoint_name,
        )
        _set_model_value(
            report,
            "term",
            checkpoint_name,
        )


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------


def _validate_exam_values(report: StudentReport) -> None:
    exam_mark = _get_model_value(
        report,
        "exam_mark",
    )
    exam_max_mark = _get_model_value(
        report,
        "exam_max_mark",
    )

    if exam_mark is not None and exam_mark < 0:
        raise ValueError("Exam mark cannot be negative.")

    if exam_max_mark is not None and exam_max_mark <= 0:
        raise ValueError("Exam maximum mark must be greater than zero.")

    if exam_max_mark is not None and exam_mark is None:
        raise ValueError("Exam maximum mark cannot be entered without an exam mark.")

    if (
        exam_mark is not None
        and exam_max_mark is not None
        and exam_mark > exam_max_mark
    ):
        raise ValueError("Exam mark cannot be greater than the exam maximum mark.")


def _validate_required_session_fields(
    report: StudentReport,
    report_session: ReportSession | None,
) -> None:
    """
    Validate fields configured as required by the linked report session.

    Exam grade is required when include_exam_grade=True.

    Exam mark remains optional even when exam grade is required.
    """

    if report_session is None:
        return

    if not _session_is_active(report_session):
        raise ValueError("Reports cannot be submitted to an inactive report session.")

    if _session_option_enabled(
        report_session,
        "include_attainment_grade",
    ):
        attainment_grade = _clean_optional_text(
            _get_model_value(
                report,
                "attainment_grade",
            )
        )

        legacy_grade = _clean_optional_text(
            _get_model_value(
                report,
                "grade",
            )
        )

        if attainment_grade is None and legacy_grade is None:
            raise ValueError("An attainment grade is required before submission.")

    if _session_option_enabled(
        report_session,
        "include_effort_grade",
    ):
        effort_grade = _clean_optional_text(
            _get_model_value(
                report,
                "effort_grade",
            )
        )

        if effort_grade is None:
            raise ValueError("An effort grade is required before submission.")

    if _session_option_enabled(
        report_session,
        "include_target_grade",
    ):
        target_grade = _clean_optional_text(
            _get_model_value(
                report,
                "target_grade",
            )
        )

        if target_grade is None:
            raise ValueError("A target grade is required before submission.")

    if _session_option_enabled(
        report_session,
        "include_exam_grade",
    ):
        exam_grade = _clean_optional_text(
            _get_model_value(
                report,
                "exam_grade",
            )
        )

        if exam_grade is None:
            raise ValueError("An exam grade is required before submission.")

    # Exam mark remains optional. If it is entered, its values are validated
    # separately by _validate_exam_values().
    if _session_option_enabled(
        report_session,
        "include_ucas_predicted_grade",
    ):
        ucas_predicted_grade = _clean_optional_text(
            _get_model_value(
                report,
                "ucas_predicted_grade",
            )
        )

        if ucas_predicted_grade is None:
            raise ValueError("A UCAS predicted grade is required before submission.")

    if _session_option_enabled(
        report_session,
        "include_teacher_comment",
    ):
        report_text = _clean_optional_text(report.report_text)

        if report_text is None:
            raise ValueError(
                "The teacher report comment is required before submission."
            )

    if _session_option_enabled(
        report_session,
        "include_next_steps",
    ):
        next_steps = _clean_optional_text(
            _get_model_value(
                report,
                "next_steps",
            )
        )

        if next_steps is None:
            raise ValueError("Next steps are required before submission.")


async def _validate_report_for_submission(
    db: AsyncSession,
    *,
    report: StudentReport,
) -> ReportSession | None:
    report_session = await _get_report_session(
        db,
        school_id=report.school_id,
        report_session_id=report.report_session_id,
    )

    if not report.report_text or not report.report_text.strip():
        raise ValueError("The report text must be completed before submission.")

    _validate_exam_values(report)

    _validate_required_session_fields(
        report,
        report_session,
    )

    return report_session


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------


async def create_student_report(
    db: AsyncSession,
    *,
    school_id: int,
    teacher_id: int,
    payload: StudentReportCreate,
) -> StudentReport:
    report_session = await _get_report_session(
        db,
        school_id=school_id,
        report_session_id=payload.report_session_id,
    )

    existing_result = await db.execute(
        select(StudentReport).where(
            StudentReport.school_id == school_id,
            StudentReport.student_id == payload.student_id,
            StudentReport.report_session_id == payload.report_session_id,
            StudentReport.teacher_id == teacher_id,
        ),
    )

    existing_report = existing_result.scalar_one_or_none()
    # ``teacher_id`` is accepted by the create schema for backward
    # compatibility, but the authenticated teacher ID remains authoritative.
    payload_data = payload.model_dump(exclude={"teacher_id"})

    if existing_report is not None:
        if existing_report.status not in TEACHER_EDITABLE_STATUSES:
            raise ValueError(
                "This report has already entered the review workflow and "
                "cannot be overwritten."
            )

        _apply_payload_to_report(
            existing_report,
            payload_data,
        )

        _apply_session_defaults(
            existing_report,
            report_session,
        )

        _validate_exam_values(existing_report)

        _clear_all_review_fields(existing_report)
        _clear_publication_fields(existing_report)

        await db.commit()
        await db.refresh(existing_report)

        return existing_report

    report = StudentReport(
        school_id=school_id,
        student_id=payload.student_id,
        teacher_id=teacher_id,
        report_session_id=payload.report_session_id,
        title=payload.title,
        report_text=payload.report_text,
        academic_year=payload.academic_year,
        status=REPORT_STATUS_DRAFT,
        submitted_at=None,
        submitted_by_id=None,
        tutor_reviewed_at=None,
        tutor_reviewed_by_id=None,
        tutor_review_comments=None,
        ready_for_smt_at=None,
        ready_for_smt_by_id=None,
        reviewed_at=None,
        reviewed_by_id=None,
        review_comments=None,
        published=False,
        published_at=None,
        published_by_id=None,
    )

    _apply_payload_to_report(
        report,
        payload_data,
    )

    _apply_session_defaults(
        report,
        report_session,
    )

    _validate_exam_values(report)

    db.add(report)
    await db.commit()
    await db.refresh(report)

    return report


# ---------------------------------------------------------------------------
# Read and list
# ---------------------------------------------------------------------------


async def get_student_report(
    db: AsyncSession,
    *,
    report_id: int,
    school_id: int,
) -> StudentReport | None:
    result = await db.execute(
        select(StudentReport).where(
            StudentReport.id == report_id,
            StudentReport.school_id == school_id,
        ),
    )

    return result.scalar_one_or_none()


async def list_student_reports(
    db: AsyncSession,
    *,
    school_id: int,
    teacher_id: int | None = None,
    report_session_id: int | None = None,
    published: bool | None = None,
    status: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[StudentReport]:
    statement = select(StudentReport).where(
        StudentReport.school_id == school_id,
    )

    if teacher_id is not None:
        statement = statement.where(
            StudentReport.teacher_id == teacher_id,
        )

    if report_session_id is not None:
        statement = statement.where(
            StudentReport.report_session_id == report_session_id,
        )

    if published is not None:
        statement = statement.where(
            StudentReport.published.is_(published),
        )

    if status is not None:
        statement = statement.where(
            StudentReport.status == status,
        )

    statement = (
        statement.order_by(
            StudentReport.created_at.desc(),
        )
        .offset(offset)
        .limit(limit)
    )

    result = await db.execute(statement)

    return list(result.scalars().all())


async def list_reports_for_student(
    db: AsyncSession,
    *,
    school_id: int,
    student_id: int,
    report_session_id: int | None = None,
    published_only: bool = False,
) -> list[StudentReport]:
    statement = select(StudentReport).where(
        StudentReport.school_id == school_id,
        StudentReport.student_id == student_id,
    )

    if report_session_id is not None:
        statement = statement.where(
            StudentReport.report_session_id == report_session_id,
        )

    if published_only:
        statement = statement.where(
            StudentReport.published.is_(True),
            StudentReport.status == REPORT_STATUS_PUBLISHED,
        )

    statement = statement.order_by(
        StudentReport.created_at.desc(),
    )

    result = await db.execute(statement)

    return list(result.scalars().all())


async def list_student_report_review_queue(
    db: AsyncSession,
    *,
    school_id: int,
    teacher_id: int | None = None,
    report_session_id: int | None = None,
    student_id: int | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[StudentReport]:
    statement = select(StudentReport).where(
        StudentReport.school_id == school_id,
        StudentReport.status.in_(SMT_REVIEWABLE_STATUSES),
        StudentReport.published.is_(False),
    )

    if teacher_id is not None:
        statement = statement.where(
            StudentReport.teacher_id == teacher_id,
        )

    if report_session_id is not None:
        statement = statement.where(
            StudentReport.report_session_id == report_session_id,
        )

    if student_id is not None:
        statement = statement.where(
            StudentReport.student_id == student_id,
        )

    statement = (
        statement.order_by(
            StudentReport.ready_for_smt_at.asc(),
            StudentReport.created_at.asc(),
        )
        .offset(offset)
        .limit(limit)
    )

    result = await db.execute(statement)

    return list(result.scalars().all())


# ---------------------------------------------------------------------------
# Tutor access and tutor queues
# ---------------------------------------------------------------------------


async def user_can_tutor_review_student(
    db: AsyncSession,
    *,
    school_id: int,
    tutor_id: int,
    student_id: int,
) -> bool:
    """
    Confirm that the pupil is enrolled in a class group assigned to the tutor.
    """

    result = await db.execute(
        select(Enrollment.user_id)
        .join(
            ClassGroup,
            Enrollment.class_id == ClassGroup.id,
        )
        .where(
            Enrollment.user_id == student_id,
            ClassGroup.school_id == school_id,
            ClassGroup.tutor_id == tutor_id,
        )
        .limit(1),
    )

    return result.scalar_one_or_none() is not None


async def list_tutor_student_report_review_queue(
    db: AsyncSession,
    *,
    school_id: int,
    tutor_id: int,
    report_session_id: int | None = None,
    student_id: int | None = None,
    include_all_school_reports: bool = False,
    limit: int = 100,
    offset: int = 0,
) -> list[StudentReport]:
    statement = select(StudentReport).where(
        StudentReport.school_id == school_id,
        StudentReport.status.in_(
            {
                REPORT_STATUS_SUBMITTED,
                REPORT_STATUS_TUTOR_REVIEW,
            }
        ),
        StudentReport.published.is_(False),
    )

    if not include_all_school_reports:
        tutor_student_ids = (
            select(Enrollment.user_id)
            .join(
                ClassGroup,
                Enrollment.class_id == ClassGroup.id,
            )
            .where(
                ClassGroup.school_id == school_id,
                ClassGroup.tutor_id == tutor_id,
            )
        )

        statement = statement.where(
            StudentReport.student_id.in_(tutor_student_ids),
        )

    if report_session_id is not None:
        statement = statement.where(
            StudentReport.report_session_id == report_session_id,
        )

    if student_id is not None:
        statement = statement.where(
            StudentReport.student_id == student_id,
        )

    statement = (
        statement.order_by(
            StudentReport.student_id.asc(),
            StudentReport.submitted_at.asc(),
            StudentReport.created_at.asc(),
        )
        .offset(offset)
        .limit(limit)
    )

    result = await db.execute(statement)

    return list(result.scalars().all())


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------


async def get_student_report_dashboard_counts(
    db: AsyncSession,
    *,
    school_id: int,
    teacher_id: int | None = None,
    report_session_id: int | None = None,
) -> dict[str, int]:
    statement = (
        select(
            StudentReport.status,
            func.count(StudentReport.id),
        )
        .where(
            StudentReport.school_id == school_id,
        )
        .group_by(
            StudentReport.status,
        )
    )

    if teacher_id is not None:
        statement = statement.where(
            StudentReport.teacher_id == teacher_id,
        )

    if report_session_id is not None:
        statement = statement.where(
            StudentReport.report_session_id == report_session_id,
        )

    result = await db.execute(statement)

    valid_statuses = {
        REPORT_STATUS_DRAFT,
        REPORT_STATUS_SUBMITTED,
        REPORT_STATUS_TUTOR_REVIEW,
        REPORT_STATUS_RETURNED_BY_TUTOR,
        REPORT_STATUS_READY_FOR_SMT,
        REPORT_STATUS_RETURNED_BY_SMT,
        REPORT_STATUS_APPROVED,
        REPORT_STATUS_PUBLISHED,
    }

    counts: dict[str, int] = {}

    for report_status, report_count in result.all():
        if report_status in valid_statuses:
            counts[report_status] = int(report_count)

    return counts


# ---------------------------------------------------------------------------
# Report-memory helpers
# ---------------------------------------------------------------------------


def _get_user_display_name(
    user: User | None,
) -> str | None:
    if user is None:
        return None

    full_name = getattr(
        user,
        "full_name",
        None,
    )

    if isinstance(full_name, str) and full_name.strip():
        return full_name.strip()

    email = getattr(
        user,
        "email",
        None,
    )

    if isinstance(email, str) and email.strip():
        return email.strip()

    return None


async def _get_teacher_for_report(
    db: AsyncSession,
    report: StudentReport,
) -> User | None:
    if report.teacher_id is None:
        return None

    result = await db.execute(
        select(User).where(
            User.id == report.teacher_id,
            User.school_id == report.school_id,
        ),
    )

    return result.scalar_one_or_none()


async def _store_report_memory_for_published_report(
    db: AsyncSession,
    *,
    report: StudentReport,
) -> None:
    if not report.published:
        return

    if not report.report_text or not report.report_text.strip():
        return

    teacher = await _get_teacher_for_report(
        db,
        report,
    )

    subject = (
        _get_model_value(
            report,
            "subject_name",
        )
        or report.title
        or "General"
    )

    await create_report_memory(
        db,
        ReportMemoryCreate(
            school_id=report.school_id,
            teacher_id=report.teacher_id,
            teacher_name=_get_user_display_name(teacher),
            subject=subject,
            year_group=report.academic_year,
            topics_studied=report.work_covered,
            teacher_notes=report.teacher_notes,
            generated_report=(report.generated_report_text),
            final_report=report.report_text.strip(),
            source_report_id=report.id,
        ),
    )


# ---------------------------------------------------------------------------
# Update
# ---------------------------------------------------------------------------


async def update_student_report(
    db: AsyncSession,
    *,
    report: StudentReport,
    payload: StudentReportUpdate,
    current_user: User | None = None,
) -> StudentReport:
    if report.status not in TEACHER_EDITABLE_STATUSES:
        raise ValueError(
            "Only draft reports or reports returned for correction " "can be edited."
        )

    update_data = payload.model_dump(
        exclude_unset=True,
    )

    new_report_session_id = update_data.get(
        "report_session_id",
        report.report_session_id,
    )

    report_session = await _get_report_session(
        db,
        school_id=report.school_id,
        report_session_id=new_report_session_id,
    )

    _apply_payload_to_report(
        report,
        update_data,
    )

    _apply_session_defaults(
        report,
        report_session,
    )

    _validate_exam_values(report)

    _clear_publication_fields(report)

    await db.commit()
    await db.refresh(report)

    return report


# ---------------------------------------------------------------------------
# Teacher submission
# ---------------------------------------------------------------------------


async def submit_student_report(
    db: AsyncSession,
    *,
    report: StudentReport,
    submitted_by_id: int,
) -> StudentReport:
    if report.status not in TEACHER_EDITABLE_STATUSES:
        raise ValueError(
            "Only draft reports or reports returned for correction " "can be submitted."
        )

    report_session = await _validate_report_for_submission(
        db,
        report=report,
    )

    _apply_session_defaults(
        report,
        report_session,
    )

    _synchronise_legacy_fields(report)

    now = _utc_now()

    report.report_text = report.report_text.strip()
    report.status = REPORT_STATUS_SUBMITTED
    report.submitted_at = now
    report.submitted_by_id = submitted_by_id

    _clear_all_review_fields(report)
    _clear_publication_fields(report)

    await db.commit()
    await db.refresh(report)

    return report


# ---------------------------------------------------------------------------
# Tutor review
# ---------------------------------------------------------------------------


async def begin_tutor_review(
    db: AsyncSession,
    *,
    report: StudentReport,
    tutor_id: int,
) -> StudentReport:
    if report.status != REPORT_STATUS_SUBMITTED:
        raise ValueError("Only submitted reports can enter tutor review.")

    report.status = REPORT_STATUS_TUTOR_REVIEW
    report.tutor_reviewed_at = _utc_now()
    report.tutor_reviewed_by_id = tutor_id

    _clear_smt_review_fields(report)
    _clear_head_of_year_review_fields(report)
    _clear_headteacher_review_fields(report)
    _clear_publication_fields(report)

    await db.commit()
    await db.refresh(report)

    return report


async def correct_student_report_as_tutor(
    db: AsyncSession,
    *,
    report: StudentReport,
    tutor_id: int,
    report_text: str,
    tutor_review_comments: str | None = None,
    tutor_comment: str | None = None,
) -> StudentReport:
    if report.status not in TUTOR_REVIEWABLE_STATUSES:
        raise ValueError(
            "Tutor corrections can only be made during the " "tutor-review stage."
        )

    cleaned_report_text = report_text.strip()

    if not cleaned_report_text:
        raise ValueError("The corrected report text cannot be empty.")

    report.report_text = cleaned_report_text
    report.status = REPORT_STATUS_TUTOR_REVIEW
    report.tutor_reviewed_at = _utc_now()
    report.tutor_reviewed_by_id = tutor_id
    report.tutor_review_comments = _clean_optional_text(
        tutor_review_comments,
    )

    _set_model_value(
        report,
        "tutor_comment",
        _clean_optional_text(tutor_comment),
    )

    report.ready_for_smt_at = None
    report.ready_for_smt_by_id = None

    _clear_smt_review_fields(report)
    _clear_head_of_year_review_fields(report)
    _clear_headteacher_review_fields(report)
    _clear_publication_fields(report)

    await db.commit()
    await db.refresh(report)

    return report


async def return_student_report_to_teacher(
    db: AsyncSession,
    *,
    report: StudentReport,
    tutor_id: int,
    tutor_review_comments: str,
) -> StudentReport:
    if report.status not in TUTOR_REVIEWABLE_STATUSES:
        raise ValueError(
            "Only submitted reports or reports under tutor review "
            "can be returned to the subject teacher."
        )

    cleaned_comments = tutor_review_comments.strip()

    if not cleaned_comments:
        raise ValueError("Tutor comments are required when returning a report.")

    report.status = REPORT_STATUS_RETURNED_BY_TUTOR
    report.tutor_reviewed_at = _utc_now()
    report.tutor_reviewed_by_id = tutor_id
    report.tutor_review_comments = cleaned_comments

    report.ready_for_smt_at = None
    report.ready_for_smt_by_id = None

    _clear_smt_review_fields(report)
    _clear_head_of_year_review_fields(report)
    _clear_headteacher_review_fields(report)
    _clear_publication_fields(report)

    await db.commit()
    await db.refresh(report)

    return report


async def mark_student_report_ready_for_smt(
    db: AsyncSession,
    *,
    report: StudentReport,
    tutor_id: int,
    tutor_review_comments: str | None = None,
) -> StudentReport:
    if report.status not in TUTOR_REVIEWABLE_STATUSES:
        raise ValueError(
            "Only submitted reports or reports under tutor review "
            "can be marked ready for SMT."
        )

    now = _utc_now()

    report.status = REPORT_STATUS_READY_FOR_SMT
    report.tutor_reviewed_at = now
    report.tutor_reviewed_by_id = tutor_id

    cleaned_comments = _clean_optional_text(tutor_review_comments)

    if cleaned_comments is not None:
        report.tutor_review_comments = cleaned_comments

    report.ready_for_smt_at = now
    report.ready_for_smt_by_id = tutor_id

    _clear_smt_review_fields(report)
    _clear_head_of_year_review_fields(report)
    _clear_headteacher_review_fields(report)
    _clear_publication_fields(report)

    await db.commit()
    await db.refresh(report)

    return report


# ---------------------------------------------------------------------------
# SMT review
# ---------------------------------------------------------------------------


async def approve_student_report(
    db: AsyncSession,
    *,
    report: StudentReport,
    reviewed_by_id: int,
    review_comments: str | None = None,
) -> StudentReport:
    if report.status not in SMT_REVIEWABLE_STATUSES:
        raise ValueError(
            "Only submitted reports or reports ready for SMT can be approved."
        )

    await _validate_report_for_submission(
        db,
        report=report,
    )

    report.status = REPORT_STATUS_APPROVED
    report.reviewed_at = _utc_now()
    report.reviewed_by_id = reviewed_by_id
    report.review_comments = _clean_optional_text(
        review_comments,
    )

    _clear_publication_fields(report)

    await db.commit()
    await db.refresh(report)

    return report


async def return_student_report(
    db: AsyncSession,
    *,
    report: StudentReport,
    reviewed_by_id: int,
    review_comments: str | None,
) -> StudentReport:
    if report.status not in SMT_REVIEWABLE_STATUSES:
        raise ValueError(
            "Only submitted reports or reports awaiting SMT review "
            "can be returned for correction."
        )

    cleaned_comments = _clean_optional_text(review_comments)

    if cleaned_comments is None:
        raise ValueError(
            "Review comments are required when returning a report " "for correction."
        )

    # Backward-compatible behaviour: an SMT return reopens the report as a
    # draft while preserving the SMT audit trail below.
    report.status = REPORT_STATUS_DRAFT
    report.submitted_at = None
    report.submitted_by_id = None

    report.reviewed_at = _utc_now()
    report.reviewed_by_id = reviewed_by_id
    report.review_comments = cleaned_comments

    report.ready_for_smt_at = None
    report.ready_for_smt_by_id = None

    _clear_publication_fields(report)

    await db.commit()
    await db.refresh(report)

    return report


# ---------------------------------------------------------------------------
# Publication
# ---------------------------------------------------------------------------


async def publish_reports_for_session(
    db: AsyncSession,
    *,
    school_id: int,
    report_session_id: int,
    published_by_id: int,
) -> int:
    report_session = await _get_report_session(
        db,
        school_id=school_id,
        report_session_id=report_session_id,
    )

    if report_session is None:
        raise ValueError("The report session could not be found.")

    unapproved_result = await db.execute(
        select(func.count(StudentReport.id)).where(
            StudentReport.school_id == school_id,
            StudentReport.report_session_id == report_session_id,
            StudentReport.published.is_(False),
            StudentReport.status.not_in(
                {
                    REPORT_STATUS_APPROVED,
                    REPORT_STATUS_PUBLISHED,
                }
            ),
        ),
    )

    unapproved_count = int(unapproved_result.scalar_one())

    if unapproved_count > 0:
        raise ValueError(
            "All reports in the session must be approved before "
            "the session can be published."
        )

    result = await db.execute(
        select(StudentReport).where(
            StudentReport.school_id == school_id,
            StudentReport.report_session_id == report_session_id,
            StudentReport.published.is_(False),
            StudentReport.status == REPORT_STATUS_APPROVED,
        ),
    )

    reports = list(result.scalars().all())

    if not reports:
        return 0

    published_at = _utc_now()

    for report in reports:
        await _validate_report_for_submission(
            db,
            report=report,
        )

        report.status = REPORT_STATUS_PUBLISHED
        report.published = True
        report.published_at = published_at
        report.published_by_id = published_by_id

    if hasattr(report_session, "published_at"):
        report_session.published_at = published_at

    await db.commit()

    for report in reports:
        await db.refresh(report)

        await _store_report_memory_for_published_report(
            db,
            report=report,
        )

    return len(reports)


# ---------------------------------------------------------------------------
# Delete
# ---------------------------------------------------------------------------


async def delete_student_report(
    db: AsyncSession,
    *,
    report: StudentReport,
) -> None:
    if report.status != REPORT_STATUS_DRAFT:
        raise ValueError("Only draft reports can be deleted.")

    await db.delete(report)
    await db.commit()
