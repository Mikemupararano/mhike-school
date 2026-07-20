# ---------------------------------------------------------------------------
# Report-session helpers
# ---------------------------------------------------------------------------
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Iterable, Mapping

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.class_group import ClassGroup
from app.models.enrollment import Enrollment
from app.models.report_session import ReportSession
from app.models.student_report import StudentReport
from app.models.user import User
from app.schemas.student_report import (
    StudentReportCompletionOverview,
    StudentReportCompletionRow,
    StudentReportCreate,
    StudentReportUpdate,
)

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


ALL_REPORT_STATUSES = {
    REPORT_STATUS_DRAFT,
    REPORT_STATUS_SUBMITTED,
    REPORT_STATUS_TUTOR_REVIEW,
    REPORT_STATUS_RETURNED_BY_TUTOR,
    REPORT_STATUS_READY_FOR_SMT,
    REPORT_STATUS_RETURNED_BY_SMT,
    REPORT_STATUS_APPROVED,
    REPORT_STATUS_PUBLISHED,
}


AUTHOR_EDITABLE_STATUSES = {
    REPORT_STATUS_DRAFT,
    REPORT_STATUS_RETURNED_BY_TUTOR,
    REPORT_STATUS_RETURNED_BY_SMT,
}


# Backward-compatible alias for existing imports and tests.
TEACHER_EDITABLE_STATUSES = AUTHOR_EDITABLE_STATUSES


TUTOR_REVIEWABLE_STATUSES = {
    REPORT_STATUS_SUBMITTED,
    REPORT_STATUS_TUTOR_REVIEW,
}


SMT_REVIEWABLE_STATUSES = {
    REPORT_STATUS_SUBMITTED,
    REPORT_STATUS_READY_FOR_SMT,
}


NON_PUBLISHED_EDITABLE_STATUSES = {
    REPORT_STATUS_DRAFT,
    REPORT_STATUS_SUBMITTED,
    REPORT_STATUS_TUTOR_REVIEW,
    REPORT_STATUS_RETURNED_BY_TUTOR,
    REPORT_STATUS_READY_FOR_SMT,
    REPORT_STATUS_RETURNED_BY_SMT,
    REPORT_STATUS_APPROVED,
}


# ---------------------------------------------------------------------------
# Report kinds and custom report support
# ---------------------------------------------------------------------------

REPORT_KIND_SUBJECT = "subject"
REPORT_KIND_TUTOR = "tutor"
REPORT_KIND_HEAD_OF_YEAR = "head_of_year"
REPORT_KIND_HEADTEACHER = "headteacher"
REPORT_KIND_CUSTOM = "custom"


ALL_REPORT_KINDS = {
    REPORT_KIND_SUBJECT,
    REPORT_KIND_TUTOR,
    REPORT_KIND_HEAD_OF_YEAR,
    REPORT_KIND_HEADTEACHER,
    REPORT_KIND_CUSTOM,
}


DEFAULT_REPORT_TYPE_CODES = {
    REPORT_KIND_SUBJECT: "subject",
    REPORT_KIND_TUTOR: "tutor",
    REPORT_KIND_HEAD_OF_YEAR: "head_of_year",
    REPORT_KIND_HEADTEACHER: "headteacher",
}


CUSTOM_REPORT_SCOPE_STUDENT = "student"
CUSTOM_REPORT_SCOPE_CLASS = "class"
CUSTOM_REPORT_SCOPE_TUTOR_GROUP = "tutor_group"
CUSTOM_REPORT_SCOPE_YEAR_GROUP = "year_group"
CUSTOM_REPORT_SCOPE_HOUSE = "house"
CUSTOM_REPORT_SCOPE_BOARDING_HOUSE = "boarding_house"
CUSTOM_REPORT_SCOPE_SCHOOL = "school"


ALL_CUSTOM_REPORT_SCOPES = {
    CUSTOM_REPORT_SCOPE_STUDENT,
    CUSTOM_REPORT_SCOPE_CLASS,
    CUSTOM_REPORT_SCOPE_TUTOR_GROUP,
    CUSTOM_REPORT_SCOPE_YEAR_GROUP,
    CUSTOM_REPORT_SCOPE_HOUSE,
    CUSTOM_REPORT_SCOPE_BOARDING_HOUSE,
    CUSTOM_REPORT_SCOPE_SCHOOL,
}


# Custom report values will initially be stored only when matching model and
# schema fields exist. This allows the repository code to be introduced before
# the database migration is deployed.
CUSTOM_REPORT_METADATA_FIELDS = {
    "report_kind",
    "report_type_id",
    "report_type_code",
    "report_type_name",
    "report_type_label",
    "writer_label",
    "report_scope",
    "scope_reference_id",
    "custom_preferences",
    "custom_field_values",
    "display_order",
    "include_in_final_report",
}


# ---------------------------------------------------------------------------
# Editable fields
# ---------------------------------------------------------------------------

STUDENT_REPORT_EDITABLE_FIELDS = {
    # Identification and report classification
    "title",
    "academic_year",
    "term",
    "checkpoint_name",
    "subject_name",
    "report_kind",
    "report_type_id",
    "report_type_code",
    "report_type_name",
    "report_type_label",
    "writer_label",
    "report_scope",
    "scope_reference_id",
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
    # Custom report preferences and values
    "custom_preferences",
    "custom_field_values",
    "display_order",
    "include_in_final_report",
    # Ownership and reporting-session fields
    "teacher_id",
    "report_session_id",
}


REVIEWER_EDITABLE_FIELDS = {
    # Identification and display
    "title",
    "academic_year",
    "term",
    "checkpoint_name",
    "subject_name",
    "report_kind",
    "report_type_id",
    "report_type_code",
    "report_type_name",
    "report_type_label",
    "writer_label",
    "report_scope",
    "scope_reference_id",
    # Final report content
    "report_text",
    "work_covered",
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
    # Review-stage comments
    "tutor_comment",
    "head_of_year_comment",
    "headteacher_comment",
    # Custom report content
    "custom_preferences",
    "custom_field_values",
    "display_order",
    "include_in_final_report",
}


PROTECTED_WORKFLOW_FIELDS = {
    "school_id",
    "student_id",
    "status",
    # Submission
    "submitted_at",
    "submitted_by_id",
    # Tutor review
    "tutor_reviewed_at",
    "tutor_reviewed_by_id",
    "tutor_review_comments",
    # Ready for SMT
    "ready_for_smt_at",
    "ready_for_smt_by_id",
    # SMT review
    "reviewed_at",
    "reviewed_by_id",
    "review_comments",
    # Head of Year audit
    "head_of_year_reviewed_at",
    "head_of_year_reviewed_by_id",
    # Headteacher audit
    "headteacher_reviewed_at",
    "headteacher_reviewed_by_id",
    # Publication
    "published",
    "published_at",
    "published_by_id",
    # General edit audit
    "last_edited_at",
    "last_edited_by_id",
    "last_edited_role",
    # Timestamps
    "created_at",
    "updated_at",
}


# These fields must never be reassigned through an ordinary author update.
AUTHOR_PROTECTED_FIELDS = PROTECTED_WORKFLOW_FIELDS | {
    "school_id",
    "student_id",
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


def _normalise_code(
    value: object | None,
    *,
    fallback: str | None = None,
) -> str | None:
    """
    Convert a report type, role or scope value into a stable lower-case code.
    """

    if value is None:
        return fallback

    raw_value = getattr(value, "value", value)

    if not isinstance(raw_value, str):
        raw_value = str(raw_value)

    cleaned = "_".join(raw_value.strip().lower().replace("-", " ").split())

    return cleaned or fallback


def _set_model_value(
    instance: Any,
    field_name: str,
    value: Any,
) -> None:
    """
    Set a value only when the SQLAlchemy model exposes the field.

    This keeps the repository usable during staged migrations. Custom report
    support can therefore be merged before all new columns are deployed.
    """

    if hasattr(instance, field_name):
        setattr(instance, field_name, value)


def _get_model_value(
    instance: Any,
    field_name: str,
    default: Any = None,
) -> Any:
    return getattr(instance, field_name, default)


def _payload_to_dict(
    payload: Any,
    *,
    exclude_unset: bool = False,
    exclude: Iterable[str] | None = None,
) -> dict[str, Any]:
    """
    Convert a Pydantic payload or mapping into a plain dictionary.

    The helper remains compatible with Pydantic v2 while also making tests
    with simple dictionary payloads easier.
    """

    excluded_fields = set(exclude or ())

    if isinstance(payload, Mapping):
        return {
            key: value for key, value in payload.items() if key not in excluded_fields
        }

    model_dump = getattr(payload, "model_dump", None)

    if callable(model_dump):
        return model_dump(
            exclude_unset=exclude_unset,
            exclude=excluded_fields,
        )

    raise TypeError("The report payload must be a Pydantic model or mapping.")


def _set_edit_audit(
    report: StudentReport,
    *,
    edited_by_id: int | None,
    edited_role: str | None,
) -> None:
    if edited_by_id is None:
        return

    _set_model_value(
        report,
        "last_edited_at",
        _utc_now(),
    )
    _set_model_value(
        report,
        "last_edited_by_id",
        edited_by_id,
    )
    _set_model_value(
        report,
        "last_edited_role",
        _clean_optional_text(edited_role),
    )


def _clear_publication_fields(report: StudentReport) -> None:
    report.published = False
    report.published_at = None
    report.published_by_id = None


def _clear_approval_fields(report: StudentReport) -> None:
    report.approved_at = None
    report.approved_by_id = None

    _set_model_value(report, "approval_comments", None)


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
# Report-type and custom-preference helpers
# ---------------------------------------------------------------------------


def _infer_report_kind(report: StudentReport) -> str:
    """
    Infer a report kind for legacy rows that do not yet have report_kind.

    New reports should store report_kind explicitly once the model migration
    has been applied.
    """

    configured_kind = _normalise_code(
        _get_model_value(
            report,
            "report_kind",
        )
    )

    if configured_kind in ALL_REPORT_KINDS:
        return configured_kind

    report_type_code = _normalise_code(
        _get_model_value(
            report,
            "report_type_code",
        )
    )

    if report_type_code in {
        "tutor",
        "tutor_report",
    }:
        return REPORT_KIND_TUTOR

    if report_type_code in {
        "head_of_year",
        "head_of_year_report",
        "hoy",
    }:
        return REPORT_KIND_HEAD_OF_YEAR

    if report_type_code in {
        "headteacher",
        "headmaster",
        "headteacher_report",
        "headmaster_report",
    }:
        return REPORT_KIND_HEADTEACHER

    if report_type_code:
        return REPORT_KIND_CUSTOM

    subject_name = _clean_optional_text(
        _get_model_value(
            report,
            "subject_name",
        )
    )

    if subject_name:
        return REPORT_KIND_SUBJECT

    return REPORT_KIND_CUSTOM


def _normalise_report_metadata(report: StudentReport) -> None:
    """
    Populate safe report-type defaults without overwriting custom settings.
    """

    report_kind = _infer_report_kind(report)

    _set_model_value(
        report,
        "report_kind",
        report_kind,
    )

    report_type_code = _normalise_code(
        _get_model_value(
            report,
            "report_type_code",
        ),
        fallback=DEFAULT_REPORT_TYPE_CODES.get(report_kind),
    )

    if report_type_code is None and report_kind == REPORT_KIND_CUSTOM:
        report_type_code = "custom"

    _set_model_value(
        report,
        "report_type_code",
        report_type_code,
    )

    report_type_name = _clean_optional_text(
        _get_model_value(
            report,
            "report_type_name",
        )
    )

    if report_type_name is None:
        fallback_names = {
            REPORT_KIND_SUBJECT: "Subject Report",
            REPORT_KIND_TUTOR: "Tutor Report",
            REPORT_KIND_HEAD_OF_YEAR: "Head of Year Report",
            REPORT_KIND_HEADTEACHER: "Headteacher Report",
            REPORT_KIND_CUSTOM: "Custom Report",
        }

        report_type_name = fallback_names[report_kind]

    _set_model_value(
        report,
        "report_type_name",
        report_type_name,
    )

    report_type_label = _clean_optional_text(
        _get_model_value(
            report,
            "report_type_label",
        )
    )

    if report_type_label is None:
        report_type_label = report_type_name

    _set_model_value(
        report,
        "report_type_label",
        report_type_label,
    )

    writer_label = _clean_optional_text(
        _get_model_value(
            report,
            "writer_label",
        )
    )

    if writer_label is None:
        default_writer_labels = {
            REPORT_KIND_SUBJECT: "Subject Teacher",
            REPORT_KIND_TUTOR: "Tutor",
            REPORT_KIND_HEAD_OF_YEAR: "Head of Year",
            REPORT_KIND_HEADTEACHER: "Headteacher",
            REPORT_KIND_CUSTOM: "Report Author",
        }

        writer_label = default_writer_labels[report_kind]

    _set_model_value(
        report,
        "writer_label",
        writer_label,
    )

    report_scope = _normalise_code(
        _get_model_value(
            report,
            "report_scope",
        )
    )

    if report_scope is not None and report_scope not in ALL_CUSTOM_REPORT_SCOPES:
        raise ValueError(f"Unsupported report scope: {report_scope}.")

    if report_scope is None:
        report_scope = CUSTOM_REPORT_SCOPE_STUDENT

    _set_model_value(
        report,
        "report_scope",
        report_scope,
    )

    include_in_final_report = _get_model_value(
        report,
        "include_in_final_report",
        None,
    )

    if include_in_final_report is None:
        _set_model_value(
            report,
            "include_in_final_report",
            True,
        )


def _validate_custom_report_preferences(
    report: StudentReport,
) -> None:
    """
    Validate custom preferences and values when those fields are available.

    Detailed field validation will eventually be driven by a ReportType and
    ReportTypeField table. Until that migration exists, this validation
    ensures the stored values have predictable container types.
    """

    custom_preferences = _get_model_value(
        report,
        "custom_preferences",
        None,
    )

    if custom_preferences is not None and not isinstance(
        custom_preferences,
        dict,
    ):
        raise ValueError("Custom report preferences must be stored as an object.")

    custom_field_values = _get_model_value(
        report,
        "custom_field_values",
        None,
    )

    if custom_field_values is not None and not isinstance(
        custom_field_values,
        dict,
    ):
        raise ValueError("Custom report field values must be stored as an object.")

    display_order = _get_model_value(
        report,
        "display_order",
        None,
    )

    if display_order is not None:
        if isinstance(display_order, bool) or not isinstance(display_order, int):
            raise ValueError("Report display order must be an integer.")

        if display_order < 0:
            raise ValueError("Report display order cannot be negative.")


def _custom_preference_is_enabled(
    report: StudentReport,
    preference_name: str,
    *,
    default: bool = False,
) -> bool:
    preferences = _get_model_value(
        report,
        "custom_preferences",
        None,
    )

    if not isinstance(preferences, dict):
        return default

    return bool(
        preferences.get(
            preference_name,
            default,
        )
    )


def _custom_preference_value(
    report: StudentReport,
    preference_name: str,
    *,
    default: Any = None,
) -> Any:
    preferences = _get_model_value(
        report,
        "custom_preferences",
        None,
    )

    if not isinstance(preferences, dict):
        return default

    return preferences.get(
        preference_name,
        default,
    )


def _validate_custom_required_fields(
    report: StudentReport,
) -> None:
    """
    Validate custom fields declared as required in custom_preferences.

    Expected staged structure:

        {
            "required_fields": [
                "boarding_comment",
                "conduct_grade"
            ]
        }

    Values are stored in custom_field_values.
    """

    required_fields = _custom_preference_value(
        report,
        "required_fields",
        default=[],
    )

    if required_fields is None:
        return

    if not isinstance(required_fields, list):
        raise ValueError("Custom report required_fields must be stored as a list.")

    custom_values = _get_model_value(
        report,
        "custom_field_values",
        None,
    )

    if custom_values is None:
        custom_values = {}

    if not isinstance(custom_values, dict):
        raise ValueError("Custom report field values must be stored as an object.")

    missing_fields: list[str] = []

    for field_name in required_fields:
        if not isinstance(field_name, str):
            raise ValueError("Every custom required field name must be text.")

        cleaned_field_name = field_name.strip()

        if not cleaned_field_name:
            continue

        value = custom_values.get(cleaned_field_name)

        if value is None:
            missing_fields.append(cleaned_field_name)
            continue

        if isinstance(value, str) and not value.strip():
            missing_fields.append(cleaned_field_name)
            continue

        if isinstance(value, (list, dict)) and not value:
            missing_fields.append(cleaned_field_name)

    if missing_fields:
        raise ValueError(
            "The following custom report fields are required: "
            + ", ".join(sorted(missing_fields))
            + "."
        )


# ---------------------------------------------------------------------------
# Backward-compatibility helpers
# ---------------------------------------------------------------------------


def _synchronise_legacy_fields(report: StudentReport) -> None:
    """
    Keep legacy fields populated while the frontend and database migrate to
    the richer reporting structure.

    Preferred fields:
        attainment_grade
        checkpoint_name

    Legacy fields:
        grade
        term
    """

    grade = _get_model_value(
        report,
        "grade",
    )

    attainment_grade = _get_model_value(
        report,
        "attainment_grade",
    )

    if grade is None and attainment_grade is not None:
        _set_model_value(
            report,
            "grade",
            attainment_grade,
        )
    elif attainment_grade is None and grade is not None:
        _set_model_value(
            report,
            "attainment_grade",
            grade,
        )

    term = _get_model_value(
        report,
        "term",
    )

    checkpoint_name = _get_model_value(
        report,
        "checkpoint_name",
    )

    if checkpoint_name is None and term is not None:
        _set_model_value(
            report,
            "checkpoint_name",
            term,
        )
    elif term is None and checkpoint_name is not None:
        _set_model_value(
            report,
            "term",
            checkpoint_name,
        )

    _normalise_report_metadata(report)


def _apply_payload_to_report(
    report: StudentReport,
    payload_data: dict[str, Any],
) -> None:
    """
    Apply only recognised author-editable values to the report.

    Workflow and audit fields cannot be changed through an ordinary create or
    update payload.
    """

    for field_name, value in payload_data.items():
        if field_name in AUTHOR_PROTECTED_FIELDS:
            continue

        if field_name not in STUDENT_REPORT_EDITABLE_FIELDS:
            continue

        if isinstance(value, str):
            value = value.strip()

        _set_model_value(
            report,
            field_name,
            value,
        )

    _synchronise_legacy_fields(report)
    _validate_custom_report_preferences(report)
# ---------------------------------------------------------------------------
# Report-session helpers
# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# Report-session helpers
# ---------------------------------------------------------------------------


async def _get_report_session(
    db: AsyncSession,
    *,
    school_id: int,
    report_session_id: int | None,
) -> ReportSession | None:
    """
    Return a school-scoped reporting session.

    A report session belonging to another school must never be accepted.
    """

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


def _session_option_value(
    report_session: ReportSession | None,
    option_name: str,
    *,
    default: Any = None,
) -> Any:
    if report_session is None:
        return default

    return getattr(
        report_session,
        option_name,
        default,
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


def _session_is_published(
    report_session: ReportSession | None,
) -> bool:
    if report_session is None:
        return False

    published_at = getattr(
        report_session,
        "published_at",
        None,
    )

    published = getattr(
        report_session,
        "published",
        None,
    )

    return bool(published_at is not None or published is True)


def _session_accepts_report_kind(
    report_session: ReportSession | None,
    report_kind: str,
) -> bool:
    """
    Determine whether the session accepts the requested report kind.

    Older ReportSession models may not yet expose report-kind configuration.
    In that case, all report kinds remain allowed for backward compatibility.
    """

    if report_session is None:
        return True

    configured_kinds = getattr(
        report_session,
        "enabled_report_kinds",
        None,
    )

    if configured_kinds is None:
        configured_kinds = getattr(
            report_session,
            "report_kinds",
            None,
        )

    if configured_kinds is None:
        return True

    if isinstance(configured_kinds, str):
        configured_kinds = [
            item.strip() for item in configured_kinds.split(",") if item.strip()
        ]

    if not isinstance(
        configured_kinds,
        (list, tuple, set),
    ):
        return True

    normalised_kinds = {_normalise_code(item) for item in configured_kinds}

    return report_kind in normalised_kinds


def _session_accepts_report_type(
    report_session: ReportSession | None,
    report_type_id: int | None,
    report_type_code: str | None,
) -> bool:
    """
    Validate optional report-type restrictions configured on a session.

    During staged migration, sessions without these fields continue to accept
    all active school report types.
    """

    if report_session is None:
        return True

    allowed_type_ids = getattr(
        report_session,
        "enabled_report_type_ids",
        None,
    )

    if allowed_type_ids is None:
        allowed_type_ids = getattr(
            report_session,
            "report_type_ids",
            None,
        )

    if allowed_type_ids is not None and report_type_id is not None:
        if isinstance(allowed_type_ids, str):
            allowed_type_ids = [
                item.strip() for item in allowed_type_ids.split(",") if item.strip()
            ]

        if isinstance(
            allowed_type_ids,
            (list, tuple, set),
        ):
            normalised_ids: set[int] = set()

            for value in allowed_type_ids:
                try:
                    normalised_ids.add(int(value))
                except (TypeError, ValueError):
                    continue

            if normalised_ids and report_type_id not in normalised_ids:
                return False

    allowed_type_codes = getattr(
        report_session,
        "enabled_report_type_codes",
        None,
    )

    if allowed_type_codes is None:
        allowed_type_codes = getattr(
            report_session,
            "report_type_codes",
            None,
        )

    if allowed_type_codes is not None and report_type_code is not None:
        if isinstance(allowed_type_codes, str):
            allowed_type_codes = [
                item.strip() for item in allowed_type_codes.split(",") if item.strip()
            ]

        if isinstance(
            allowed_type_codes,
            (list, tuple, set),
        ):
            normalised_codes = {_normalise_code(value) for value in allowed_type_codes}

            normalised_report_type_code = _normalise_code(
                report_type_code,
            )

            if normalised_codes and normalised_report_type_code not in normalised_codes:
                return False

    return True


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

    default_include_in_final_report = getattr(
        report_session,
        "include_reports_in_final_document",
        None,
    )

    if (
        default_include_in_final_report is not None
        and _get_model_value(
            report,
            "include_in_final_report",
            None,
        )
        is None
    ):
        _set_model_value(
            report,
            "include_in_final_report",
            bool(default_include_in_final_report),
        )

    _normalise_report_metadata(report)


def _validate_report_session_assignment(
    report: StudentReport,
    report_session: ReportSession | None,
) -> None:
    if report_session is None:
        return

    if not _session_is_active(report_session):
        raise ValueError(
            "Reports cannot be created or submitted to an inactive " "report session."
        )

    if _session_is_published(report_session):
        raise ValueError("New reports cannot be created in a published report session.")

    report_kind = _infer_report_kind(report)

    if not _session_accepts_report_kind(
        report_session,
        report_kind,
    ):
        raise ValueError(f"The report session does not accept {report_kind} reports.")

    report_type_id = _get_model_value(
        report,
        "report_type_id",
        None,
    )

    report_type_code = _normalise_code(
        _get_model_value(
            report,
            "report_type_code",
            None,
        )
    )

    if not _session_accepts_report_type(
        report_session,
        report_type_id,
        report_type_code,
    ):
        raise ValueError(
            "The selected report type is not enabled for this " "reporting session."
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

    if exam_mark is not None:
        if isinstance(exam_mark, bool):
            raise ValueError("Exam mark must be a number.")

        try:
            exam_mark_value = float(exam_mark)
        except (TypeError, ValueError) as exc:
            raise ValueError("Exam mark must be a number.") from exc

        if exam_mark_value < 0:
            raise ValueError("Exam mark cannot be negative.")

    if exam_max_mark is not None:
        if isinstance(exam_max_mark, bool):
            raise ValueError("Exam maximum mark must be a number.")

        try:
            exam_max_mark_value = float(exam_max_mark)
        except (TypeError, ValueError) as exc:
            raise ValueError("Exam maximum mark must be a number.") from exc

        if exam_max_mark_value <= 0:
            raise ValueError("Exam maximum mark must be greater than zero.")

    if exam_max_mark is not None and exam_mark is None:
        raise ValueError("Exam maximum mark cannot be entered without an exam mark.")

    if (
        exam_mark is not None
        and exam_max_mark is not None
        and float(exam_mark) > float(exam_max_mark)
    ):
        raise ValueError("Exam mark cannot be greater than the exam maximum mark.")


def _validate_text_length(
    *,
    value: str | None,
    field_label: str,
    maximum_length: int | None,
) -> None:
    if value is None or maximum_length is None:
        return

    if maximum_length < 1:
        return

    if len(value) > maximum_length:
        raise ValueError(f"{field_label} cannot exceed {maximum_length} characters.")


def _validate_report_identity(report: StudentReport) -> None:
    title = _clean_optional_text(
        _get_model_value(
            report,
            "title",
        )
    )

    if title is None:
        raise ValueError("A report title is required.")

    if len(title) > 200:
        raise ValueError("The report title cannot exceed 200 characters.")

    academic_year = _clean_optional_text(
        _get_model_value(
            report,
            "academic_year",
        )
    )

    if academic_year is not None and len(academic_year) > 20:
        raise ValueError("Academic year cannot exceed 20 characters.")

    term = _clean_optional_text(
        _get_model_value(
            report,
            "term",
        )
    )

    if term is not None and len(term) > 50:
        raise ValueError("Term cannot exceed 50 characters.")

    checkpoint_name = _clean_optional_text(
        _get_model_value(
            report,
            "checkpoint_name",
        )
    )

    if checkpoint_name is not None and len(checkpoint_name) > 100:
        raise ValueError("Checkpoint name cannot exceed 100 characters.")

    subject_name = _clean_optional_text(
        _get_model_value(
            report,
            "subject_name",
        )
    )

    if subject_name is not None and len(subject_name) > 150:
        raise ValueError("Subject name cannot exceed 150 characters.")

    report_kind = _infer_report_kind(report)

    if report_kind not in ALL_REPORT_KINDS:
        raise ValueError(f"Unsupported report kind: {report_kind}.")

    report_scope = _normalise_code(
        _get_model_value(
            report,
            "report_scope",
            CUSTOM_REPORT_SCOPE_STUDENT,
        )
    )

    if report_scope not in ALL_CUSTOM_REPORT_SCOPES:
        raise ValueError(f"Unsupported report scope: {report_scope}.")

    if report_kind == REPORT_KIND_SUBJECT and subject_name is None:
        raise ValueError("A subject name is required for a subject report.")

    report_type_name = _clean_optional_text(
        _get_model_value(
            report,
            "report_type_name",
        )
    )

    if report_type_name is not None and len(report_type_name) > 150:
        raise ValueError("Report type name cannot exceed 150 characters.")

    writer_label = _clean_optional_text(
        _get_model_value(
            report,
            "writer_label",
        )
    )

    if writer_label is not None and len(writer_label) > 100:
        raise ValueError("Writer label cannot exceed 100 characters.")


def _validate_required_session_fields(
    report: StudentReport,
    report_session: ReportSession | None,
) -> None:
    """
    Validate fields configured as required by the reporting session.

    Session options remain supported for legacy subject reports. Custom
    report types may additionally declare required fields through their
    stored preferences.
    """

    if report_session is None:
        _validate_custom_required_fields(report)
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
        report_text = _clean_optional_text(
            _get_model_value(
                report,
                "report_text",
            )
        )

        if report_text is None:
            raise ValueError("The report comment is required before submission.")

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

    if _session_option_enabled(
        report_session,
        "include_work_covered",
    ):
        work_covered = _clean_optional_text(
            _get_model_value(
                report,
                "work_covered",
            )
        )

        if work_covered is None:
            raise ValueError("Work covered is required before submission.")

    report_comment_max_length = _session_option_value(
        report_session,
        "teacher_comment_max_length",
        default=None,
    )

    if report_comment_max_length is None:
        report_comment_max_length = _session_option_value(
            report_session,
            "report_text_max_length",
            default=None,
        )

    if report_comment_max_length is not None:
        try:
            report_comment_max_length = int(report_comment_max_length)
        except (TypeError, ValueError):
            report_comment_max_length = None

    _validate_text_length(
        value=_get_model_value(
            report,
            "report_text",
        ),
        field_label="Report comment",
        maximum_length=report_comment_max_length,
    )

    next_steps_max_length = _session_option_value(
        report_session,
        "next_steps_max_length",
        default=None,
    )

    if next_steps_max_length is not None:
        try:
            next_steps_max_length = int(next_steps_max_length)
        except (TypeError, ValueError):
            next_steps_max_length = None

    _validate_text_length(
        value=_get_model_value(
            report,
            "next_steps",
        ),
        field_label="Next steps",
        maximum_length=next_steps_max_length,
    )

    _validate_custom_required_fields(report)


def _validate_report_before_save(
    report: StudentReport,
) -> None:
    """
    Validate values that must remain valid even while a report is a draft.
    """

    _normalise_report_metadata(report)
    _validate_report_identity(report)
    _validate_exam_values(report)
    _validate_custom_report_preferences(report)


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

    _normalise_report_metadata(report)
    _validate_report_identity(report)
    _validate_report_session_assignment(
        report,
        report_session,
    )

    report_text = _clean_optional_text(
        _get_model_value(
            report,
            "report_text",
        )
    )

    require_main_comment = _custom_preference_is_enabled(
        report,
        "require_main_comment",
        default=True,
    )

    if require_main_comment and report_text is None:
        raise ValueError("The report text must be completed before submission.")

    if report_text is not None:
        report.report_text = report_text

    _validate_exam_values(report)

    _validate_required_session_fields(
        report,
        report_session,
    )

    return report_session


# ---------------------------------------------------------------------------
# Create helpers
# ---------------------------------------------------------------------------


def _report_identity_filter_values(
    *,
    payload_data: dict[str, Any],
) -> tuple[int | None, str | None, str]:
    """
    Resolve the report-type identity used to prevent accidental duplicates.

    Multiple report types by the same writer for the same pupil and reporting
    session are allowed. Only a matching report type is treated as the same
    report.
    """

    report_type_id = payload_data.get(
        "report_type_id",
    )

    report_type_code = _normalise_code(
        payload_data.get(
            "report_type_code",
        )
    )

    report_kind = _normalise_code(
        payload_data.get(
            "report_kind",
        ),
        fallback=REPORT_KIND_SUBJECT,
    )

    if report_kind not in ALL_REPORT_KINDS:
        report_kind = REPORT_KIND_CUSTOM

    if report_type_code is None:
        report_type_code = DEFAULT_REPORT_TYPE_CODES.get(
            report_kind,
        )

    return (
        report_type_id,
        report_type_code,
        report_kind,
    )


async def _find_existing_author_report(
    db: AsyncSession,
    *,
    school_id: int,
    student_id: int,
    teacher_id: int,
    report_session_id: int | None,
    report_type_id: int | None,
    report_type_code: str | None,
    report_kind: str,
) -> StudentReport | None:
    """
    Find the author's matching report without collapsing different report
    types into a single row.
    """

    statement = select(StudentReport).where(
        StudentReport.school_id == school_id,
        StudentReport.student_id == student_id,
        StudentReport.teacher_id == teacher_id,
    )

    if report_session_id is None:
        statement = statement.where(
            StudentReport.report_session_id.is_(None),
        )
    else:
        statement = statement.where(
            StudentReport.report_session_id == report_session_id,
        )

    model_has_report_type_id = hasattr(
        StudentReport,
        "report_type_id",
    )

    model_has_report_type_code = hasattr(
        StudentReport,
        "report_type_code",
    )

    model_has_report_kind = hasattr(
        StudentReport,
        "report_kind",
    )

    if model_has_report_type_id and report_type_id is not None:
        statement = statement.where(
            StudentReport.report_type_id == report_type_id,
        )

    elif model_has_report_type_code and report_type_code is not None:
        statement = statement.where(
            StudentReport.report_type_code == report_type_code,
        )

    elif model_has_report_kind:
        statement = statement.where(
            StudentReport.report_kind == report_kind,
        )

        if report_kind == REPORT_KIND_SUBJECT and hasattr(
            StudentReport, "subject_name"
        ):
            # Subject name is added by the caller below when the model does
            # not yet have a dedicated report type.
            pass

    statement = statement.order_by(
        StudentReport.updated_at.desc(),
        StudentReport.id.desc(),
    )

    result = await db.execute(statement)

    candidates = list(result.scalars().all())

    if not candidates:
        return None

    for candidate in candidates:
        candidate_type_id = _get_model_value(
            candidate,
            "report_type_id",
            None,
        )

        candidate_type_code = _normalise_code(
            _get_model_value(
                candidate,
                "report_type_code",
                None,
            )
        )

        candidate_kind = _infer_report_kind(
            candidate,
        )

        if report_type_id is not None and candidate_type_id == report_type_id:
            return candidate

        if report_type_code is not None and candidate_type_code == report_type_code:
            return candidate

        if (
            report_type_id is None
            and report_type_code is None
            and candidate_kind == report_kind
        ):
            return candidate

    return None


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
    """
    Create a new report or update the author's matching editable draft.

    The authenticated user ID remains the authoritative report-author ID.
    A payload cannot create a report on behalf of another writer.

    Different report types may coexist for the same pupil, writer and
    reporting session.
    """

    payload_data = _payload_to_dict(
        payload,
        exclude={"teacher_id"},
    )

    student_id = payload_data.get(
        "student_id",
    )

    if student_id is None:
        raise ValueError("A student ID is required.")

    report_session_id = payload_data.get(
        "report_session_id",
    )

    report_session = await _get_report_session(
        db,
        school_id=school_id,
        report_session_id=report_session_id,
    )

    if report_session is not None:
        if not _session_is_active(report_session):
            raise ValueError("Reports cannot be created in an inactive report session.")

        if _session_is_published(report_session):
            raise ValueError("Reports cannot be created in a published report session.")

    (
        report_type_id,
        report_type_code,
        report_kind,
    ) = _report_identity_filter_values(
        payload_data=payload_data,
    )

    payload_data["report_kind"] = report_kind

    if report_type_id is not None:
        payload_data["report_type_id"] = report_type_id

    if report_type_code is not None:
        payload_data["report_type_code"] = report_type_code

    existing_report = await _find_existing_author_report(
        db,
        school_id=school_id,
        student_id=student_id,
        teacher_id=teacher_id,
        report_session_id=report_session_id,
        report_type_id=report_type_id,
        report_type_code=report_type_code,
        report_kind=report_kind,
    )

    if existing_report is not None:
        if existing_report.status not in AUTHOR_EDITABLE_STATUSES:
            raise ValueError(
                "This report has already entered the review workflow and "
                "cannot be overwritten."
            )

        if (
            existing_report.published
            or existing_report.status == REPORT_STATUS_PUBLISHED
        ):
            raise ValueError("Published reports cannot be overwritten.")

        _apply_payload_to_report(
            existing_report,
            payload_data,
        )

        _apply_session_defaults(
            existing_report,
            report_session,
        )

        _validate_report_session_assignment(
            existing_report,
            report_session,
        )

        _validate_report_before_save(
            existing_report,
        )

        _clear_all_review_fields(
            existing_report,
        )

        _clear_publication_fields(
            existing_report,
        )

        _set_edit_audit(
            existing_report,
            edited_by_id=teacher_id,
            edited_role="report_author",
        )

        await db.commit()
        await db.refresh(
            existing_report,
        )

        return existing_report

    title = payload_data.get(
        "title",
    )

    report_text = payload_data.get(
        "report_text",
    )

    academic_year = payload_data.get(
        "academic_year",
    )

    report = StudentReport(
        school_id=school_id,
        student_id=student_id,
        teacher_id=teacher_id,
        report_session_id=report_session_id,
        title=title,
        report_text=report_text,
        academic_year=academic_year,
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

    _validate_report_session_assignment(
        report,
        report_session,
    )

    _validate_report_before_save(
        report,
    )

    _clear_all_review_fields(
        report,
    )

    _clear_publication_fields(
        report,
    )

    _set_edit_audit(
        report,
        edited_by_id=teacher_id,
        edited_role="report_author",
    )

    db.add(report)

    await db.commit()
    await db.refresh(report)

    return report
# ---------------------------------------------------------------------------
# Read and list
# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# Read and list
# ---------------------------------------------------------------------------


def _validate_pagination(
    *,
    limit: int,
    offset: int,
) -> None:
    if limit < 1:
        raise ValueError("Limit must be greater than zero.")

    if limit > 5000:
        raise ValueError("Limit cannot be greater than 5000.")

    if offset < 0:
        raise ValueError("Offset cannot be negative.")


def _apply_report_type_filters(
    statement,
    *,
    report_type_id: int | None = None,
    report_type_code: str | None = None,
    report_kind: str | None = None,
    subject_name: str | None = None,
):
    """
    Apply report-type filters only when the corresponding model columns exist.

    This keeps the repository compatible while report-type columns are being
    introduced through staged migrations.
    """

    if report_type_id is not None and hasattr(StudentReport, "report_type_id"):
        statement = statement.where(
            StudentReport.report_type_id == report_type_id,
        )

    normalised_report_type_code = _normalise_code(
        report_type_code,
    )

    if normalised_report_type_code is not None and hasattr(
        StudentReport, "report_type_code"
    ):
        statement = statement.where(
            StudentReport.report_type_code == normalised_report_type_code,
        )

    normalised_report_kind = _normalise_code(
        report_kind,
    )

    if normalised_report_kind is not None:
        if normalised_report_kind not in ALL_REPORT_KINDS:
            raise ValueError(f"Unsupported report kind: {normalised_report_kind}.")

        if hasattr(StudentReport, "report_kind"):
            statement = statement.where(
                StudentReport.report_kind == normalised_report_kind,
            )

    cleaned_subject_name = _clean_optional_text(
        subject_name,
    )

    if cleaned_subject_name is not None:
        statement = statement.where(
            StudentReport.subject_name == cleaned_subject_name,
        )

    return statement


def _apply_include_in_final_report_filter(
    statement,
    *,
    include_in_final_report: bool | None,
):
    if include_in_final_report is not None and hasattr(
        StudentReport,
        "include_in_final_report",
    ):
        statement = statement.where(
            StudentReport.include_in_final_report.is_(include_in_final_report),
        )

    return statement


def _normalise_loaded_report(
    report: StudentReport,
) -> StudentReport:
    """
    Apply non-persistent compatibility defaults to a loaded report.

    This ensures older rows expose predictable report-type metadata when
    returned through schemas or passed to the PDF service.
    """

    _normalise_report_metadata(report)
    _synchronise_legacy_fields(report)

    return report


def _normalise_loaded_reports(
    reports: Iterable[StudentReport],
) -> list[StudentReport]:
    return [_normalise_loaded_report(report) for report in reports]


async def get_student_report(
    db: AsyncSession,
    *,
    report_id: int,
    school_id: int,
) -> StudentReport | None:
    """
    Return one school-scoped report.

    Both the report ID and school ID are required so a valid report ID from a
    different school cannot be used to bypass school isolation.
    """

    result = await db.execute(
        select(StudentReport).where(
            StudentReport.id == report_id,
            StudentReport.school_id == school_id,
        ),
    )

    report = result.scalar_one_or_none()

    if report is None:
        return None

    return _normalise_loaded_report(report)


async def list_student_reports(
    db: AsyncSession,
    *,
    school_id: int,
    teacher_id: int | None = None,
    report_session_id: int | None = None,
    published: bool | None = None,
    status: str | None = None,
    student_id: int | None = None,
    report_type_id: int | None = None,
    report_type_code: str | None = None,
    report_kind: str | None = None,
    subject_name: str | None = None,
    include_in_final_report: bool | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[StudentReport]:
    """
    List school reports using optional author, pupil, session, workflow and
    report-type filters.
    """

    _validate_pagination(
        limit=limit,
        offset=offset,
    )

    statement = select(StudentReport).where(
        StudentReport.school_id == school_id,
    )

    if teacher_id is not None:
        statement = statement.where(
            StudentReport.teacher_id == teacher_id,
        )

    if student_id is not None:
        statement = statement.where(
            StudentReport.student_id == student_id,
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
        normalised_status = _normalise_code(
            status,
        )

        if normalised_status not in ALL_REPORT_STATUSES:
            raise ValueError(f"Unsupported report status: {normalised_status}.")

        statement = statement.where(
            StudentReport.status == normalised_status,
        )

    statement = _apply_report_type_filters(
        statement,
        report_type_id=report_type_id,
        report_type_code=report_type_code,
        report_kind=report_kind,
        subject_name=subject_name,
    )

    statement = _apply_include_in_final_report_filter(
        statement,
        include_in_final_report=include_in_final_report,
    )

    statement = (
        statement.order_by(
            StudentReport.created_at.desc(),
            StudentReport.id.desc(),
        )
        .offset(offset)
        .limit(limit)
    )

    result = await db.execute(statement)

    return _normalise_loaded_reports(result.scalars().all())


async def list_reports_for_student(
    db: AsyncSession,
    *,
    school_id: int,
    student_id: int,
    report_session_id: int | None = None,
    published_only: bool = False,
    report_type_id: int | None = None,
    report_type_code: str | None = None,
    report_kind: str | None = None,
    subject_name: str | None = None,
    include_in_final_report: bool | None = None,
) -> list[StudentReport]:
    """
    Return all permitted report rows for one pupil.

    Access control is enforced by the endpoint before this school-scoped
    repository function is called.
    """

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

    statement = _apply_report_type_filters(
        statement,
        report_type_id=report_type_id,
        report_type_code=report_type_code,
        report_kind=report_kind,
        subject_name=subject_name,
    )

    statement = _apply_include_in_final_report_filter(
        statement,
        include_in_final_report=include_in_final_report,
    )

    display_order_expressions = []

    if hasattr(
        StudentReport,
        "display_order",
    ):
        display_order_expressions.append(StudentReport.display_order.asc())

    display_order_expressions.extend(
        [
            StudentReport.created_at.asc(),
            StudentReport.id.asc(),
        ]
    )

    statement = statement.order_by(*display_order_expressions)

    result = await db.execute(statement)

    return _normalise_loaded_reports(result.scalars().all())


async def list_reports_for_session(
    db: AsyncSession,
    *,
    school_id: int,
    report_session_id: int,
    published: bool | None = None,
    status: str | None = None,
    include_in_final_report: bool | None = None,
    report_type_id: int | None = None,
    report_type_code: str | None = None,
    report_kind: str | None = None,
    limit: int = 5000,
    offset: int = 0,
) -> list[StudentReport]:
    """
    Return reports for one reporting session.

    This provides a single repository query for draft, published and combined
    PDF/ZIP exports.
    """

    return await list_student_reports(
        db,
        school_id=school_id,
        report_session_id=report_session_id,
        published=published,
        status=status,
        report_type_id=report_type_id,
        report_type_code=report_type_code,
        report_kind=report_kind,
        include_in_final_report=include_in_final_report,
        limit=limit,
        offset=offset,
    )


async def list_reports_written_by_user(
    db: AsyncSession,
    *,
    school_id: int,
    writer_id: int,
    report_session_id: int | None = None,
    student_id: int | None = None,
    report_kind: str | None = None,
    report_type_id: int | None = None,
    limit: int = 500,
    offset: int = 0,
) -> list[StudentReport]:
    """
    Return reports whose recorded author is the selected member of staff.

    ``teacher_id`` remains the legacy database field representing the report
    writer, regardless of whether the writer is a subject teacher, tutor,
    Head of Year, Headmaster, Housemaster or another configured role.
    """

    return await list_student_reports(
        db,
        school_id=school_id,
        teacher_id=writer_id,
        student_id=student_id,
        report_session_id=report_session_id,
        report_kind=report_kind,
        report_type_id=report_type_id,
        limit=limit,
        offset=offset,
    )


async def list_student_report_review_queue(
    db: AsyncSession,
    *,
    school_id: int,
    teacher_id: int | None = None,
    report_session_id: int | None = None,
    student_id: int | None = None,
    report_type_id: int | None = None,
    report_type_code: str | None = None,
    report_kind: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[StudentReport]:
    """
    Return reports awaiting SMT review.

    Reports may arrive directly from submission or after tutor/Head-of-Year
    review, depending on the report type's configured workflow.
    """

    _validate_pagination(
        limit=limit,
        offset=offset,
    )

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

    statement = _apply_report_type_filters(
        statement,
        report_type_id=report_type_id,
        report_type_code=report_type_code,
        report_kind=report_kind,
    )

    statement = statement.order_by(
        StudentReport.ready_for_smt_at.asc(),
        StudentReport.submitted_at.asc(),
        StudentReport.created_at.asc(),
        StudentReport.id.asc(),
    )

    statement = statement.offset(offset).limit(limit)

    result = await db.execute(statement)

    return _normalise_loaded_reports(result.scalars().all())
# ---------------------------------------------------------------------------
# Tutor access and tutor queues
# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# Tutor, Head of Year and pastoral access
# ---------------------------------------------------------------------------


async def user_can_tutor_review_student(
    db: AsyncSession,
    *,
    school_id: int,
    tutor_id: int,
    student_id: int,
) -> bool:
    """
    Confirm whether a member of staff has tutor-style responsibility for a
    pupil.

    The current schema supports tutor-group ownership through
    ``ClassGroup.tutor_id``. Future Head-of-Year and pastoral scope columns can
    be added without changing the endpoint contract.
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


async def list_students_for_tutor_scope(
    db: AsyncSession,
    *,
    school_id: int,
    staff_id: int,
) -> list[int]:
    """
    Return pupil IDs belonging to class groups assigned to the staff member.

    This helper is shared by tutor, Head-of-Year and pastoral queues while the
    current ClassGroup model continues to use ``tutor_id`` as its available
    responsibility field.
    """

    statement = (
        select(Enrollment.user_id)
        .join(
            ClassGroup,
            Enrollment.class_id == ClassGroup.id,
        )
        .where(
            ClassGroup.school_id == school_id,
            ClassGroup.tutor_id == staff_id,
        )
        .distinct()
        .order_by(
            Enrollment.user_id.asc(),
        )
    )

    result = await db.execute(statement)

    return [int(student_id) for student_id in result.scalars().all()]


async def user_can_access_student_by_scope(
    db: AsyncSession,
    *,
    school_id: int,
    staff_id: int,
    student_id: int,
    scope: str = CUSTOM_REPORT_SCOPE_TUTOR_GROUP,
) -> bool:
    """
    Check whether a staff member may access a pupil through an assigned scope.

    Supported immediately:
        tutor_group
        class

    Staged fallbacks:
        year_group
        house
        boarding_house

    Until dedicated year-group and house assignment tables are introduced,
    those scopes fall back to the current ClassGroup responsibility lookup.
    """

    normalised_scope = _normalise_code(
        scope,
        fallback=CUSTOM_REPORT_SCOPE_TUTOR_GROUP,
    )

    if normalised_scope == CUSTOM_REPORT_SCOPE_STUDENT:
        return True

    if normalised_scope == CUSTOM_REPORT_SCOPE_SCHOOL:
        return False

    if normalised_scope not in ALL_CUSTOM_REPORT_SCOPES:
        return False

    return await user_can_tutor_review_student(
        db,
        school_id=school_id,
        tutor_id=staff_id,
        student_id=student_id,
    )


def _apply_pupil_scope_filter(
    statement,
    *,
    school_id: int,
    staff_id: int,
):
    """
    Restrict a report query to pupils in class groups assigned to the member
    of staff.
    """

    pupil_ids = (
        select(Enrollment.user_id)
        .join(
            ClassGroup,
            Enrollment.class_id == ClassGroup.id,
        )
        .where(
            ClassGroup.school_id == school_id,
            ClassGroup.tutor_id == staff_id,
        )
    )

    return statement.where(
        StudentReport.student_id.in_(pupil_ids),
    )


async def list_tutor_student_report_review_queue(
    db: AsyncSession,
    *,
    school_id: int,
    tutor_id: int,
    report_session_id: int | None = None,
    student_id: int | None = None,
    include_all_school_reports: bool = False,
    report_type_id: int | None = None,
    report_type_code: str | None = None,
    report_kind: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[StudentReport]:
    """
    Return submitted reports available for tutor or pastoral review.

    School Admin, Platform Admin and the Headmaster may request all matching
    school reports by passing ``include_all_school_reports=True``. Other users
    are restricted to pupils in their assigned groups.
    """

    _validate_pagination(
        limit=limit,
        offset=offset,
    )

    statement = select(StudentReport).where(
        StudentReport.school_id == school_id,
        StudentReport.status.in_(TUTOR_REVIEWABLE_STATUSES),
        StudentReport.published.is_(False),
    )

    if not include_all_school_reports:
        statement = _apply_pupil_scope_filter(
            statement,
            school_id=school_id,
            staff_id=tutor_id,
        )

    if report_session_id is not None:
        statement = statement.where(
            StudentReport.report_session_id == report_session_id,
        )

    if student_id is not None:
        statement = statement.where(
            StudentReport.student_id == student_id,
        )

    statement = _apply_report_type_filters(
        statement,
        report_type_id=report_type_id,
        report_type_code=report_type_code,
        report_kind=report_kind,
    )

    statement = (
        statement.order_by(
            StudentReport.student_id.asc(),
            StudentReport.submitted_at.asc(),
            StudentReport.created_at.asc(),
            StudentReport.id.asc(),
        )
        .offset(offset)
        .limit(limit)
    )

    result = await db.execute(statement)

    return _normalise_loaded_reports(result.scalars().all())


async def list_head_of_year_report_queue(
    db: AsyncSession,
    *,
    school_id: int,
    head_of_year_id: int,
    report_session_id: int | None = None,
    student_id: int | None = None,
    include_all_school_reports: bool = False,
    report_type_id: int | None = None,
    report_type_code: str | None = None,
    report_kind: str | None = None,
    statuses: Iterable[str] | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[StudentReport]:
    """
    Return reports accessible to a Head of Year.

    The current database schema does not yet expose a dedicated year-group
    leader assignment. Until that migration is introduced, this uses the same
    pupil-scope query as tutor access. The public function is separate so its
    implementation can later move to a YearGroup or StaffYearGroup table
    without changing endpoint code.
    """

    _validate_pagination(
        limit=limit,
        offset=offset,
    )

    resolved_statuses = set(
        statuses
        or {
            REPORT_STATUS_SUBMITTED,
            REPORT_STATUS_TUTOR_REVIEW,
            REPORT_STATUS_READY_FOR_SMT,
            REPORT_STATUS_APPROVED,
        }
    )

    invalid_statuses = resolved_statuses - ALL_REPORT_STATUSES

    if invalid_statuses:
        raise ValueError(
            "Unsupported report statuses: " + ", ".join(sorted(invalid_statuses)) + "."
        )

    statement = select(StudentReport).where(
        StudentReport.school_id == school_id,
        StudentReport.status.in_(resolved_statuses),
        StudentReport.published.is_(False),
    )

    if not include_all_school_reports:
        statement = _apply_pupil_scope_filter(
            statement,
            school_id=school_id,
            staff_id=head_of_year_id,
        )

    if report_session_id is not None:
        statement = statement.where(
            StudentReport.report_session_id == report_session_id,
        )

    if student_id is not None:
        statement = statement.where(
            StudentReport.student_id == student_id,
        )

    statement = _apply_report_type_filters(
        statement,
        report_type_id=report_type_id,
        report_type_code=report_type_code,
        report_kind=report_kind,
    )

    statement = (
        statement.order_by(
            StudentReport.student_id.asc(),
            StudentReport.updated_at.asc(),
            StudentReport.id.asc(),
        )
        .offset(offset)
        .limit(limit)
    )

    result = await db.execute(statement)

    return _normalise_loaded_reports(result.scalars().all())


async def list_reports_for_staff_scope(
    db: AsyncSession,
    *,
    school_id: int,
    staff_id: int,
    report_session_id: int | None = None,
    student_id: int | None = None,
    report_type_id: int | None = None,
    report_type_code: str | None = None,
    report_kind: str | None = None,
    include_published: bool = True,
    include_all_school_reports: bool = False,
    limit: int = 500,
    offset: int = 0,
) -> list[StudentReport]:
    """
    General-purpose scoped report listing for tutors, Heads of Year,
    Housemasters, boarding staff and other configured pastoral writers.
    """

    _validate_pagination(
        limit=limit,
        offset=offset,
    )

    statement = select(StudentReport).where(
        StudentReport.school_id == school_id,
    )

    if not include_published:
        statement = statement.where(
            StudentReport.published.is_(False),
            StudentReport.status != REPORT_STATUS_PUBLISHED,
        )

    if not include_all_school_reports:
        statement = _apply_pupil_scope_filter(
            statement,
            school_id=school_id,
            staff_id=staff_id,
        )

    if report_session_id is not None:
        statement = statement.where(
            StudentReport.report_session_id == report_session_id,
        )

    if student_id is not None:
        statement = statement.where(
            StudentReport.student_id == student_id,
        )

    statement = _apply_report_type_filters(
        statement,
        report_type_id=report_type_id,
        report_type_code=report_type_code,
        report_kind=report_kind,
    )

    statement = (
        statement.order_by(
            StudentReport.student_id.asc(),
            StudentReport.created_at.asc(),
            StudentReport.id.asc(),
        )
        .offset(offset)
        .limit(limit)
    )

    result = await db.execute(statement)

    return _normalise_loaded_reports(result.scalars().all())
# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------


async def get_student_report_dashboard_counts(
    db: AsyncSession,
    *,
    school_id: int,
    teacher_id: int | None = None,
    report_session_id: int | None = None,
    student_id: int | None = None,
    report_type_id: int | None = None,
    report_type_code: str | None = None,
    report_kind: str | None = None,
) -> dict[str, int]:
    """
    Return workflow counts for the selected school and optional filters.

    Every known workflow status is returned, including statuses with a count
    of zero. This gives the frontend a predictable dashboard structure.
    """

    statement = select(
        StudentReport.status,
        func.count(StudentReport.id),
    ).where(
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

    if student_id is not None:
        statement = statement.where(
            StudentReport.student_id == student_id,
        )

    statement = _apply_report_type_filters(
        statement,
        report_type_id=report_type_id,
        report_type_code=report_type_code,
        report_kind=report_kind,
    )

    statement = statement.group_by(
        StudentReport.status,
    )

    result = await db.execute(statement)

    counts = {report_status: 0 for report_status in ALL_REPORT_STATUSES}

    for report_status, report_count in result.all():
        if report_status in ALL_REPORT_STATUSES:
            counts[report_status] = int(report_count)

    counts["total"] = sum(
        counts[report_status] for report_status in ALL_REPORT_STATUSES
    )

    counts["awaiting_author"] = (
        counts[REPORT_STATUS_DRAFT]
        + counts[REPORT_STATUS_RETURNED_BY_TUTOR]
        + counts[REPORT_STATUS_RETURNED_BY_SMT]
    )

    counts["awaiting_tutor_review"] = (
        counts[REPORT_STATUS_SUBMITTED] + counts[REPORT_STATUS_TUTOR_REVIEW]
    )

    counts["awaiting_smt_review"] = counts[REPORT_STATUS_READY_FOR_SMT]

    counts["ready_to_publish"] = counts[REPORT_STATUS_APPROVED]

    return counts


async def get_student_report_status_count(
    db: AsyncSession,
    *,
    school_id: int,
    report_status: str,
    report_session_id: int | None = None,
    teacher_id: int | None = None,
    report_type_id: int | None = None,
    report_kind: str | None = None,
) -> int:
    """
    Return one workflow-status count.

    This is useful for lightweight dashboard cards that do not require the
    complete dashboard payload.
    """

    normalised_status = _normalise_code(
        report_status,
    )

    if normalised_status not in ALL_REPORT_STATUSES:
        raise ValueError(f"Unsupported report status: {normalised_status}.")

    statement = select(func.count(StudentReport.id)).where(
        StudentReport.school_id == school_id,
        StudentReport.status == normalised_status,
    )

    if report_session_id is not None:
        statement = statement.where(
            StudentReport.report_session_id == report_session_id,
        )

    if teacher_id is not None:
        statement = statement.where(
            StudentReport.teacher_id == teacher_id,
        )

    statement = _apply_report_type_filters(
        statement,
        report_type_id=report_type_id,
        report_kind=report_kind,
    )

    result = await db.execute(statement)

    return int(result.scalar_one())


# ---------------------------------------------------------------------------
# Teacher completion overview
# ---------------------------------------------------------------------------


def _student_display_name(
    student: User,
) -> str:
    """
    Return a stable pupil display name across current and legacy User models.
    """

    full_name = getattr(
        student,
        "full_name",
        None,
    )

    if isinstance(full_name, str) and full_name.strip():
        return " ".join(full_name.strip().split())

    first_name = getattr(
        student,
        "first_name",
        None,
    )

    last_name = getattr(
        student,
        "last_name",
        None,
    )

    combined_name = " ".join(
        part.strip()
        for part in (
            first_name,
            last_name,
        )
        if isinstance(part, str) and part.strip()
    )

    if combined_name:
        return combined_name

    email = getattr(
        student,
        "email",
        None,
    )

    if isinstance(email, str) and email.strip():
        return email.strip()

    return f"Student {student.id}"


async def _get_class_group_for_school(
    db: AsyncSession,
    *,
    school_id: int,
    class_id: int,
) -> ClassGroup:
    """
    Return a school-scoped class group.

    This prevents a valid class ID belonging to another school from being used
    in the completion-overview endpoint.
    """

    result = await db.execute(
        select(ClassGroup).where(
            ClassGroup.id == class_id,
            ClassGroup.school_id == school_id,
        ),
    )

    class_group = result.scalar_one_or_none()

    if class_group is None:
        raise ValueError("The selected class does not exist for this school.")

    return class_group


async def _list_class_students(
    db: AsyncSession,
    *,
    school_id: int,
    class_id: int,
) -> list[User]:
    statement = (
        select(User)
        .join(
            Enrollment,
            Enrollment.user_id == User.id,
        )
        .where(
            Enrollment.class_id == class_id,
            User.school_id == school_id,
        )
    )

    if hasattr(User, "full_name"):
        statement = statement.order_by(
            User.full_name.asc(),
            User.id.asc(),
        )
    else:
        statement = statement.order_by(
            User.id.asc(),
        )

    result = await db.execute(statement)

    return list(result.scalars().unique().all())


async def _find_latest_matching_student_report(
    db: AsyncSession,
    *,
    school_id: int,
    student_id: int,
    report_session_id: int,
    teacher_id: int | None,
    report_type_id: int | None,
    report_type_code: str | None,
    report_kind: str | None,
    subject_name: str | None,
) -> StudentReport | None:
    statement = select(StudentReport).where(
        StudentReport.school_id == school_id,
        StudentReport.student_id == student_id,
        StudentReport.report_session_id == report_session_id,
    )

    if teacher_id is not None:
        statement = statement.where(
            StudentReport.teacher_id == teacher_id,
        )

    statement = _apply_report_type_filters(
        statement,
        report_type_id=report_type_id,
        report_type_code=report_type_code,
        report_kind=report_kind,
        subject_name=subject_name,
    )

    statement = statement.order_by(
        StudentReport.updated_at.desc(),
        StudentReport.id.desc(),
    )

    result = await db.execute(statement)

    report = result.scalars().first()

    if report is None:
        return None

    return _normalise_loaded_report(report)


async def get_student_report_completion_overview(
    db: AsyncSession,
    *,
    school_id: int,
    class_id: int,
    report_session_id: int,
    teacher_id: int | None = None,
    report_type_id: int | None = None,
    report_type_code: str | None = None,
    report_kind: str | None = None,
    subject_name: str | None = None,
) -> dict[str, Any]:
    """
    Return the full class roster together with each pupil's latest matching
    report.

    Pupils without a report are represented by the synthetic status
    ``not_started``. Different report types can therefore have separate
    completion dashboards for the same class and session.
    """

    await _get_class_group_for_school(
        db,
        school_id=school_id,
        class_id=class_id,
    )

    report_session = await _get_report_session(
        db,
        school_id=school_id,
        report_session_id=report_session_id,
    )

    if report_session is None:
        raise ValueError("The selected report session could not be found.")

    normalised_report_kind = _normalise_code(
        report_kind,
    )

    if (
        normalised_report_kind is not None
        and normalised_report_kind not in ALL_REPORT_KINDS
    ):
        raise ValueError(f"Unsupported report kind: {normalised_report_kind}.")

    students = await _list_class_students(
        db,
        school_id=school_id,
        class_id=class_id,
    )

    rows: list[StudentReportCompletionRow] = []

    counts = {
        "not_started": 0,
        REPORT_STATUS_DRAFT: 0,
        REPORT_STATUS_RETURNED_BY_TUTOR: 0,
        REPORT_STATUS_RETURNED_BY_SMT: 0,
        REPORT_STATUS_SUBMITTED: 0,
        REPORT_STATUS_TUTOR_REVIEW: 0,
        REPORT_STATUS_READY_FOR_SMT: 0,
        REPORT_STATUS_APPROVED: 0,
        REPORT_STATUS_PUBLISHED: 0,
    }

    completed_statuses = {
        REPORT_STATUS_SUBMITTED,
        REPORT_STATUS_TUTOR_REVIEW,
        REPORT_STATUS_READY_FOR_SMT,
        REPORT_STATUS_APPROVED,
        REPORT_STATUS_PUBLISHED,
    }

    for student in students:
        report = await _find_latest_matching_student_report(
            db,
            school_id=school_id,
            student_id=student.id,
            report_session_id=report_session_id,
            teacher_id=teacher_id,
            report_type_id=report_type_id,
            report_type_code=report_type_code,
            report_kind=normalised_report_kind,
            subject_name=subject_name,
        )

        row_status = "not_started" if report is None else report.status

        if row_status not in counts:
            counts[row_status] = 0

        counts[row_status] += 1

        rows.append(
            StudentReportCompletionRow(
                student_id=student.id,
                student_name=_student_display_name(student),
                report_id=(None if report is None else report.id),
                status=row_status,
                last_updated=(None if report is None else report.updated_at),
            )
        )

    total_students = len(rows)

    completed = sum(
        counts.get(report_status, 0) for report_status in completed_statuses
    )

    outstanding = total_students - completed

    completion_percentage = (
        0.0
        if total_students == 0
        else round(
            completed * 100 / total_students,
            1,
        )
    )

    overview_data: dict[str, Any] = {
        "class_id": class_id,
        "report_session_id": report_session_id,
        "teacher_id": teacher_id,
        "total_students": total_students,
        "completed": completed,
        "outstanding": outstanding,
        "completion_percentage": completion_percentage,
        "students": rows,
        **counts,
    }

    overview = StudentReportCompletionOverview(**overview_data)

    return overview.model_dump()


async def get_staff_scope_completion_overview(
    db: AsyncSession,
    *,
    school_id: int,
    staff_id: int,
    report_session_id: int,
    report_type_id: int | None = None,
    report_type_code: str | None = None,
    report_kind: str | None = None,
) -> dict[str, Any]:
    """
    Return completion information for all pupils within a tutor, Head-of-Year
    or pastoral staff member's assigned scope.

    This helper does not replace the class overview. It supports staff whose
    responsibility may span several class groups.
    """

    report_session = await _get_report_session(
        db,
        school_id=school_id,
        report_session_id=report_session_id,
    )

    if report_session is None:
        raise ValueError("The selected report session could not be found.")

    student_ids = await list_students_for_tutor_scope(
        db,
        school_id=school_id,
        staff_id=staff_id,
    )

    counts = {
        "not_started": 0,
        REPORT_STATUS_DRAFT: 0,
        REPORT_STATUS_RETURNED_BY_TUTOR: 0,
        REPORT_STATUS_RETURNED_BY_SMT: 0,
        REPORT_STATUS_SUBMITTED: 0,
        REPORT_STATUS_TUTOR_REVIEW: 0,
        REPORT_STATUS_READY_FOR_SMT: 0,
        REPORT_STATUS_APPROVED: 0,
        REPORT_STATUS_PUBLISHED: 0,
    }

    rows: list[dict[str, Any]] = []

    for student_id in student_ids:
        student_result = await db.execute(
            select(User).where(
                User.id == student_id,
                User.school_id == school_id,
            ),
        )

        student = student_result.scalar_one_or_none()

        if student is None:
            continue

        report = await _find_latest_matching_student_report(
            db,
            school_id=school_id,
            student_id=student_id,
            report_session_id=report_session_id,
            teacher_id=staff_id,
            report_type_id=report_type_id,
            report_type_code=report_type_code,
            report_kind=report_kind,
            subject_name=None,
        )

        row_status = "not_started" if report is None else report.status

        counts[row_status] = counts.get(row_status, 0) + 1

        rows.append(
            {
                "student_id": student_id,
                "student_name": _student_display_name(student),
                "report_id": (None if report is None else report.id),
                "status": row_status,
                "last_updated": (None if report is None else report.updated_at),
            }
        )

    completed_statuses = {
        REPORT_STATUS_SUBMITTED,
        REPORT_STATUS_TUTOR_REVIEW,
        REPORT_STATUS_READY_FOR_SMT,
        REPORT_STATUS_APPROVED,
        REPORT_STATUS_PUBLISHED,
    }

    total_students = len(rows)

    completed = sum(
        counts.get(report_status, 0) for report_status in completed_statuses
    )

    outstanding = total_students - completed

    completion_percentage = (
        0.0
        if total_students == 0
        else round(
            completed * 100 / total_students,
            1,
        )
    )

    return {
        "staff_id": staff_id,
        "report_session_id": report_session_id,
        "total_students": total_students,
        "completed": completed,
        "outstanding": outstanding,
        "completion_percentage": completion_percentage,
        "students": rows,
        **counts,
    }
# ---------------------------------------------------------------------------
# Update
# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# Update
# ---------------------------------------------------------------------------


def _validate_update_status(
    report: StudentReport,
    *,
    allowed_statuses: set[str],
    action_label: str,
) -> None:
    if report.published or report.status == REPORT_STATUS_PUBLISHED:
        raise ValueError("Published reports cannot be edited.")

    if report.status not in allowed_statuses:
        raise ValueError(
            f"This report cannot be {action_label} while its status is "
            f"'{report.status}'."
        )


def _validate_author_update_fields(
    update_data: dict[str, Any],
) -> None:
    protected_fields = sorted(
        field_name
        for field_name in update_data
        if field_name in AUTHOR_PROTECTED_FIELDS
    )

    if protected_fields:
        raise ValueError(
            "Report authors cannot change these protected fields: "
            + ", ".join(protected_fields)
            + "."
        )

    unsupported_fields = sorted(
        field_name
        for field_name in update_data
        if field_name not in STUDENT_REPORT_EDITABLE_FIELDS
    )

    if unsupported_fields:
        raise ValueError(
            "Unsupported report fields: " + ", ".join(unsupported_fields) + "."
        )


def _validate_reviewer_update_fields(
    update_data: dict[str, Any],
) -> None:
    disallowed_fields = sorted(
        field_name
        for field_name in update_data
        if field_name not in REVIEWER_EDITABLE_FIELDS
    )

    if disallowed_fields:
        raise ValueError(
            "Reviewers cannot change these fields: "
            + ", ".join(disallowed_fields)
            + "."
        )


def _apply_reviewer_payload(
    report: StudentReport,
    update_data: dict[str, Any],
) -> None:
    for field_name, value in update_data.items():
        if field_name not in REVIEWER_EDITABLE_FIELDS:
            continue

        if isinstance(value, str):
            value = value.strip()

        _set_model_value(
            report,
            field_name,
            value,
        )

    _synchronise_legacy_fields(report)
    _normalise_report_metadata(report)


async def update_student_report(
    db: AsyncSession,
    *,
    report: StudentReport,
    payload: StudentReportUpdate,
    current_user: User | None = None,
) -> StudentReport:
    """
    Update a report through its ordinary author-editing path.

    This function is intended for:
        - the original report author;
        - a tutor or Head of Year whose endpoint permission has already been
          checked;
        - the Headmaster or another school-wide editor whose endpoint
          permission has already been checked.

    The endpoint remains responsible for determining whether the user may edit
    this particular pupil. The repository enforces workflow, data integrity
    and publication locking.
    """

    if report.published or report.status == REPORT_STATUS_PUBLISHED:
        raise ValueError("Published reports cannot be edited.")

    update_data = _payload_to_dict(
        payload,
        exclude_unset=True,
    )

    _validate_author_update_fields(
        update_data,
    )

    original_report_session_id = report.report_session_id

    new_report_session_id = update_data.get(
        "report_session_id",
        original_report_session_id,
    )

    report_session = await _get_report_session(
        db,
        school_id=report.school_id,
        report_session_id=new_report_session_id,
    )

    if (
        new_report_session_id != original_report_session_id
        and report.status not in AUTHOR_EDITABLE_STATUSES
    ):
        raise ValueError(
            "The reporting session can only be changed while a report is "
            "a draft or has been returned for correction."
        )

    if (
        new_report_session_id != original_report_session_id
        and report_session is not None
        and _session_is_published(report_session)
    ):
        raise ValueError("A report cannot be moved into a published reporting session.")

    _apply_payload_to_report(
        report,
        update_data,
    )

    _apply_session_defaults(
        report,
        report_session,
    )

    _validate_report_session_assignment(
        report,
        report_session,
    )

    _validate_report_before_save(
        report,
    )

    _clear_publication_fields(
        report,
    )

    edited_by_id = None if current_user is None else current_user.id

    edited_role = None

    if current_user is not None:
        edited_role = "report_editor"

    _set_edit_audit(
        report,
        edited_by_id=edited_by_id,
        edited_role=edited_role,
    )

    await db.commit()
    await db.refresh(report)

    return _normalise_loaded_report(report)


async def update_student_report_as_author(
    db: AsyncSession,
    *,
    report: StudentReport,
    payload: StudentReportUpdate,
    author_id: int,
    author_role: str | None = None,
) -> StudentReport:
    """
    Update a report specifically through the author workflow.

    Only draft reports or reports returned for correction may be changed
    through this function.
    """

    _validate_update_status(
        report,
        allowed_statuses=AUTHOR_EDITABLE_STATUSES,
        action_label="edited by its author",
    )

    if report.teacher_id != author_id:
        raise ValueError(
            "Only the recorded report author can use the author-edit path."
        )

    update_data = _payload_to_dict(
        payload,
        exclude_unset=True,
    )

    _validate_author_update_fields(
        update_data,
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

    _validate_report_session_assignment(
        report,
        report_session,
    )

    _validate_report_before_save(
        report,
    )

    _clear_publication_fields(
        report,
    )

    _set_edit_audit(
        report,
        edited_by_id=author_id,
        edited_role=(_clean_optional_text(author_role) or "report_author"),
    )

    await db.commit()
    await db.refresh(report)

    return _normalise_loaded_report(report)


async def update_student_report_as_scoped_editor(
    db: AsyncSession,
    *,
    report: StudentReport,
    payload: StudentReportUpdate,
    editor_id: int,
    editor_role: str,
) -> StudentReport:
    """
    Update a non-published report as a tutor, Head of Year, Housemaster,
    boarding member of staff or another configured scoped editor.

    Pupil-scope permission must be checked before this repository function is
    called.
    """

    _validate_update_status(
        report,
        allowed_statuses=NON_PUBLISHED_EDITABLE_STATUSES,
        action_label="edited",
    )

    update_data = _payload_to_dict(
        payload,
        exclude_unset=True,
    )

    _validate_reviewer_update_fields(
        update_data,
    )

    _apply_reviewer_payload(
        report,
        update_data,
    )

    report_session = await _get_report_session(
        db,
        school_id=report.school_id,
        report_session_id=report.report_session_id,
    )

    _apply_session_defaults(
        report,
        report_session,
    )

    _validate_report_session_assignment(
        report,
        report_session,
    )

    _validate_report_before_save(
        report,
    )

    _clear_publication_fields(
        report,
    )

    _set_edit_audit(
        report,
        edited_by_id=editor_id,
        edited_role=editor_role,
    )

    if _normalise_code(editor_role) in {
        "head_of_year",
        "hoy",
    }:
        _set_model_value(
            report,
            "head_of_year_reviewed_at",
            _utc_now(),
        )

        _set_model_value(
            report,
            "head_of_year_reviewed_by_id",
            editor_id,
        )

    if _normalise_code(editor_role) in {
        "headteacher",
        "headmaster",
        "principal",
    }:
        _set_model_value(
            report,
            "headteacher_reviewed_at",
            _utc_now(),
        )

        _set_model_value(
            report,
            "headteacher_reviewed_by_id",
            editor_id,
        )

    await db.commit()
    await db.refresh(report)

    return _normalise_loaded_report(report)


async def update_student_report_as_reviewer(
    db: AsyncSession,
    *,
    report: StudentReport,
    payload: StudentReportUpdate,
    reviewer_id: int,
    reviewer_role: str | None = None,
) -> StudentReport:
    """
    Save SMT, School Admin, Platform Admin or Headmaster corrections without
    changing the workflow status.

    The endpoint decides which roles may call this function. Publication and
    workflow state remain protected.
    """

    _validate_update_status(
        report,
        allowed_statuses=NON_PUBLISHED_EDITABLE_STATUSES,
        action_label="edited by a reviewer",
    )

    update_data = _payload_to_dict(
        payload,
        exclude_unset=True,
    )

    _validate_reviewer_update_fields(
        update_data,
    )

    _apply_reviewer_payload(
        report,
        update_data,
    )

    report_session = await _get_report_session(
        db,
        school_id=report.school_id,
        report_session_id=report.report_session_id,
    )

    _apply_session_defaults(
        report,
        report_session,
    )

    _validate_report_session_assignment(
        report,
        report_session,
    )

    _validate_report_before_save(
        report,
    )

    report_text = _clean_optional_text(
        _get_model_value(
            report,
            "report_text",
        )
    )

    require_main_comment = _custom_preference_is_enabled(
        report,
        "require_main_comment",
        default=True,
    )

    if require_main_comment and report_text is None:
        raise ValueError("The report text cannot be empty.")

    if report_text is not None:
        report.report_text = report_text

    normalised_reviewer_role = _normalise_code(
        reviewer_role,
        fallback="reviewer",
    )

    _set_edit_audit(
        report,
        edited_by_id=reviewer_id,
        edited_role=normalised_reviewer_role,
    )

    if normalised_reviewer_role in {
        "head_of_year",
        "hoy",
    }:
        _set_model_value(
            report,
            "head_of_year_reviewed_at",
            _utc_now(),
        )

        _set_model_value(
            report,
            "head_of_year_reviewed_by_id",
            reviewer_id,
        )

    if normalised_reviewer_role in {
        "headteacher",
        "headmaster",
        "principal",
    }:
        _set_model_value(
            report,
            "headteacher_reviewed_at",
            _utc_now(),
        )

        _set_model_value(
            report,
            "headteacher_reviewed_by_id",
            reviewer_id,
        )

    await db.commit()
    await db.refresh(report)

    return _normalise_loaded_report(report)
# ---------------------------------------------------------------------------
# Teacher submission
# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# Report submission
# ---------------------------------------------------------------------------


def _submission_requires_tutor_review(
    report: StudentReport,
) -> bool:
    """
    Determine whether the report should pass through tutor review.

    Subject reports default to tutor review. Tutor, Head-of-Year,
    Headteacher and custom reports may override this through their stored
    custom preferences.
    """

    configured_value = _custom_preference_value(
        report,
        "requires_tutor_review",
        default=None,
    )

    if configured_value is not None:
        return bool(configured_value)

    report_kind = _infer_report_kind(report)

    return report_kind == REPORT_KIND_SUBJECT


def _submission_requires_smt_review(
    report: StudentReport,
) -> bool:
    """
    Determine whether the report requires SMT approval before publication.

    Reports require SMT approval by default unless their configured report
    type explicitly disables it.
    """

    configured_value = _custom_preference_value(
        report,
        "requires_smt_approval",
        default=None,
    )

    if configured_value is None:
        configured_value = _custom_preference_value(
            report,
            "approval_required",
            default=None,
        )

    if configured_value is None:
        return True

    return bool(configured_value)


def _submission_requires_publication(
    report: StudentReport,
) -> bool:
    """
    Determine whether the report is expected to enter the publication stage.

    The value is stored as configuration metadata for future workflow
    routing. The existing publication endpoint continues to publish only
    approved reports.
    """

    configured_value = _custom_preference_value(
        report,
        "publication_required",
        default=None,
    )

    if configured_value is None:
        return True

    return bool(configured_value)


def _initial_submitted_status(
    report: StudentReport,
) -> str:
    """
    Resolve the first workflow status after an author submits a report.

    Current workflow:
        author submits;
        tutor review may follow;
        SMT approval follows;
        publication follows.

    Reports that do not require tutor review still enter ``submitted`` so SMT
    may review them directly. The endpoint and review queue already allow SMT
    to approve submitted reports.
    """

    return REPORT_STATUS_SUBMITTED


def _clear_submission_fields(
    report: StudentReport,
) -> None:
    report.submitted_at = None
    report.submitted_by_id = None


def _prepare_report_for_resubmission(
    report: StudentReport,
) -> None:
    """
    Clear stale downstream workflow information before a returned report is
    submitted again.

    Previous review comments remain only where required for audit and user
    feedback. Review timestamps and decisions are reset so the new submission
    is treated as a fresh workflow pass.
    """

    previous_status = report.status

    if previous_status == REPORT_STATUS_RETURNED_BY_TUTOR:
        report.ready_for_smt_at = None
        report.ready_for_smt_by_id = None

        _clear_smt_review_fields(report)
        _clear_head_of_year_review_fields(report)
        _clear_headteacher_review_fields(report)

    elif previous_status == REPORT_STATUS_RETURNED_BY_SMT:
        _clear_tutor_review_fields(report)
        _clear_smt_review_fields(report)
        _clear_head_of_year_review_fields(report)
        _clear_headteacher_review_fields(report)

    else:
        _clear_all_review_fields(report)

    _clear_publication_fields(report)


async def submit_student_report(
    db: AsyncSession,
    *,
    report: StudentReport,
    submitted_by_id: int,
) -> StudentReport:
    """
    Submit a draft or corrected report into the review workflow.

    The endpoint must confirm that ``submitted_by_id`` is the report author or
    another authorised school-wide user. This repository function validates
    workflow state, session configuration and report completeness.
    """

    _validate_update_status(
        report,
        allowed_statuses=AUTHOR_EDITABLE_STATUSES,
        action_label="submitted",
    )

    if submitted_by_id < 1:
        raise ValueError("A valid submitting user is required.")

    report_session = await _validate_report_for_submission(
        db,
        report=report,
    )

    _apply_session_defaults(
        report,
        report_session,
    )

    _validate_report_session_assignment(
        report,
        report_session,
    )

    _synchronise_legacy_fields(report)
    _normalise_report_metadata(report)

    now = _utc_now()

    cleaned_report_text = _clean_optional_text(
        _get_model_value(
            report,
            "report_text",
        )
    )

    if cleaned_report_text is not None:
        report.report_text = cleaned_report_text

    _prepare_report_for_resubmission(
        report,
    )

    report.status = _initial_submitted_status(report)

    report.submitted_at = now
    report.submitted_by_id = submitted_by_id

    _set_model_value(
        report,
        "requires_tutor_review",
        _submission_requires_tutor_review(report),
    )

    _set_model_value(
        report,
        "requires_smt_approval",
        _submission_requires_smt_review(report),
    )

    _set_model_value(
        report,
        "publication_required",
        _submission_requires_publication(report),
    )

    _set_edit_audit(
        report,
        edited_by_id=submitted_by_id,
        edited_role="report_submitter",
    )

    await db.commit()
    await db.refresh(report)

    return _normalise_loaded_report(report)


async def resubmit_student_report(
    db: AsyncSession,
    *,
    report: StudentReport,
    submitted_by_id: int,
) -> StudentReport:
    """
    Explicit resubmission alias for reports returned by a tutor or SMT.

    This provides a clearer service-layer function for future endpoints while
    retaining ``submit_student_report`` as the existing endpoint dependency.
    """

    if report.status not in {
        REPORT_STATUS_RETURNED_BY_TUTOR,
        REPORT_STATUS_RETURNED_BY_SMT,
    }:
        raise ValueError(
            "Only reports returned for correction can be resubmitted "
            "through the resubmission workflow."
        )

    return await submit_student_report(
        db,
        report=report,
        submitted_by_id=submitted_by_id,
    )


async def withdraw_submitted_report(
    db: AsyncSession,
    *,
    report: StudentReport,
    withdrawn_by_id: int,
) -> StudentReport:
    """
    Move a newly submitted report back to draft before review begins.

    This function is not yet exposed by the current endpoint but provides a
    safe repository operation for a future Withdraw Submission action.
    """

    if report.published or report.status == REPORT_STATUS_PUBLISHED:
        raise ValueError("Published reports cannot be withdrawn.")

    if report.status != REPORT_STATUS_SUBMITTED:
        raise ValueError(
            "Only a submitted report that has not entered review can " "be withdrawn."
        )

    report.status = REPORT_STATUS_DRAFT

    _clear_submission_fields(report)
    _clear_all_review_fields(report)
    _clear_publication_fields(report)

    _set_edit_audit(
        report,
        edited_by_id=withdrawn_by_id,
        edited_role="submission_withdrawn",
    )

    await db.commit()
    await db.refresh(report)

    return _normalise_loaded_report(report)
# ---------------------------------------------------------------------------
# Tutor review
# ---------------------------------------------------------------------------


def _validate_tutor_review_status(
    report: StudentReport,
    *,
    action_label: str,
) -> None:
    if report.published or report.status == REPORT_STATUS_PUBLISHED:
        raise ValueError("Published reports cannot enter tutor review.")

    if report.status not in TUTOR_REVIEWABLE_STATUSES:
        raise ValueError(
            f"This report cannot be {action_label} while its status is "
            f"'{report.status}'."
        )


def _record_tutor_review(
    report: StudentReport,
    *,
    tutor_id: int,
    comments: str | None = None,
) -> None:
    now = _utc_now()

    report.tutor_reviewed_at = now
    report.tutor_reviewed_by_id = tutor_id

    if comments is not None:
        report.tutor_review_comments = _clean_optional_text(comments)

    _set_edit_audit(
        report,
        edited_by_id=tutor_id,
        edited_role="tutor",
    )


async def begin_tutor_review(
    db: AsyncSession,
    *,
    report: StudentReport,
    tutor_id: int,
) -> StudentReport:
    """
    Move a submitted report into active tutor review.

    The endpoint must first confirm that the tutor has responsibility for the
    pupil. School-wide administrators and the Headmaster may also begin review
    after their endpoint permissions have been checked.
    """

    if report.published or report.status == REPORT_STATUS_PUBLISHED:
        raise ValueError("Published reports cannot enter tutor review.")

    if report.status != REPORT_STATUS_SUBMITTED:
        raise ValueError("Only submitted reports can enter tutor review.")

    if tutor_id < 1:
        raise ValueError("A valid tutor is required.")

    report.status = REPORT_STATUS_TUTOR_REVIEW

    _record_tutor_review(
        report,
        tutor_id=tutor_id,
    )

    report.ready_for_smt_at = None
    report.ready_for_smt_by_id = None

    _clear_smt_review_fields(report)

    _clear_head_of_year_review_fields(report)

    _clear_headteacher_review_fields(report)

    _clear_publication_fields(report)

    await db.commit()
    await db.refresh(report)

    return _normalise_loaded_report(report)


async def correct_student_report_as_tutor(
    db: AsyncSession,
    *,
    report: StudentReport,
    tutor_id: int,
    report_text: str,
    tutor_review_comments: str | None = None,
    tutor_comment: str | None = None,
) -> StudentReport:
    """
    Correct report wording during tutor review without changing the author.

    The report author remains stored in ``teacher_id``. Tutor identity and
    editing activity are recorded in the tutor-review and general audit
    fields.
    """

    _validate_tutor_review_status(
        report,
        action_label="corrected during tutor review",
    )

    if tutor_id < 1:
        raise ValueError("A valid tutor is required.")

    cleaned_report_text = _clean_optional_text(report_text)

    if cleaned_report_text is None:
        raise ValueError("The corrected report text cannot be empty.")

    report.report_text = cleaned_report_text
    report.status = REPORT_STATUS_TUTOR_REVIEW

    _record_tutor_review(
        report,
        tutor_id=tutor_id,
        comments=tutor_review_comments,
    )

    if tutor_comment is not None:
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

    _validate_report_before_save(report)

    await db.commit()
    await db.refresh(report)

    return _normalise_loaded_report(report)


async def update_student_report_during_tutor_review(
    db: AsyncSession,
    *,
    report: StudentReport,
    payload: StudentReportUpdate,
    tutor_id: int,
    tutor_role: str = "tutor",
) -> StudentReport:
    """
    Save structured tutor corrections, including grades and configured report
    fields, without advancing the workflow.

    Pupil-scope permission must be checked before this function is called.
    """

    _validate_tutor_review_status(
        report,
        action_label="edited during tutor review",
    )

    update_data = _payload_to_dict(
        payload,
        exclude_unset=True,
    )

    _validate_reviewer_update_fields(update_data)

    _apply_reviewer_payload(
        report,
        update_data,
    )

    report_session = await _get_report_session(
        db,
        school_id=report.school_id,
        report_session_id=report.report_session_id,
    )

    _apply_session_defaults(
        report,
        report_session,
    )

    _validate_report_session_assignment(
        report,
        report_session,
    )

    _validate_report_before_save(report)

    report.status = REPORT_STATUS_TUTOR_REVIEW

    _record_tutor_review(
        report,
        tutor_id=tutor_id,
    )

    _set_edit_audit(
        report,
        edited_by_id=tutor_id,
        edited_role=(
            _normalise_code(
                tutor_role,
                fallback="tutor",
            )
            or "tutor"
        ),
    )

    report.ready_for_smt_at = None
    report.ready_for_smt_by_id = None

    _clear_smt_review_fields(report)

    _clear_publication_fields(report)

    await db.commit()
    await db.refresh(report)

    return _normalise_loaded_report(report)


async def return_student_report_to_teacher(
    db: AsyncSession,
    *,
    report: StudentReport,
    tutor_id: int,
    tutor_review_comments: str,
) -> StudentReport:
    """
    Return a report to its author for correction.

    Tutor comments are mandatory so the author knows what must be changed.
    """

    _validate_tutor_review_status(
        report,
        action_label="returned to its author",
    )

    cleaned_comments = _clean_optional_text(tutor_review_comments)

    if cleaned_comments is None:
        raise ValueError("Tutor comments are required when returning a report.")

    report.status = REPORT_STATUS_RETURNED_BY_TUTOR

    _record_tutor_review(
        report,
        tutor_id=tutor_id,
        comments=cleaned_comments,
    )

    report.ready_for_smt_at = None
    report.ready_for_smt_by_id = None

    _clear_smt_review_fields(report)

    _clear_head_of_year_review_fields(report)

    _clear_headteacher_review_fields(report)

    _clear_publication_fields(report)

    await db.commit()
    await db.refresh(report)

    return _normalise_loaded_report(report)


async def mark_student_report_ready_for_smt(
    db: AsyncSession,
    *,
    report: StudentReport,
    tutor_id: int,
    tutor_review_comments: str | None = None,
) -> StudentReport:
    """
    Complete tutor review and send the report to SMT.

    This function does not approve the report. Approval remains an SMT,
    School Admin or Platform Admin action.
    """

    _validate_tutor_review_status(
        report,
        action_label="marked ready for SMT",
    )

    if tutor_id < 1:
        raise ValueError("A valid tutor is required.")

    await _validate_report_for_submission(
        db,
        report=report,
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

    _set_edit_audit(
        report,
        edited_by_id=tutor_id,
        edited_role="tutor",
    )

    await db.commit()
    await db.refresh(report)

    return _normalise_loaded_report(report)


async def record_head_of_year_review(
    db: AsyncSession,
    *,
    report: StudentReport,
    head_of_year_id: int,
    head_of_year_comment: str | None = None,
    review_comments: str | None = None,
    mark_ready_for_smt: bool = False,
) -> StudentReport:
    """
    Record a Head-of-Year review while preserving the same main workflow.

    The Head of Year may edit and save, but cannot approve or publish. When
    ``mark_ready_for_smt`` is true, the report moves to ``ready_for_smt``.
    Otherwise it remains in tutor review.
    """

    _validate_tutor_review_status(
        report,
        action_label="reviewed by the Head of Year",
    )

    if head_of_year_id < 1:
        raise ValueError("A valid Head of Year is required.")

    cleaned_head_of_year_comment = _clean_optional_text(head_of_year_comment)

    if head_of_year_comment is not None:
        _set_model_value(
            report,
            "head_of_year_comment",
            cleaned_head_of_year_comment,
        )

    cleaned_review_comments = _clean_optional_text(review_comments)

    now = _utc_now()

    _set_model_value(
        report,
        "head_of_year_reviewed_at",
        now,
    )

    _set_model_value(
        report,
        "head_of_year_reviewed_by_id",
        head_of_year_id,
    )

    if cleaned_review_comments is not None:
        report.tutor_review_comments = cleaned_review_comments

    if mark_ready_for_smt:
        await _validate_report_for_submission(
            db,
            report=report,
        )

        report.status = REPORT_STATUS_READY_FOR_SMT
        report.ready_for_smt_at = now
        report.ready_for_smt_by_id = head_of_year_id
    else:
        report.status = REPORT_STATUS_TUTOR_REVIEW
        report.ready_for_smt_at = None
        report.ready_for_smt_by_id = None

    _clear_smt_review_fields(report)

    _clear_headteacher_review_fields(report)

    _clear_publication_fields(report)

    _set_edit_audit(
        report,
        edited_by_id=head_of_year_id,
        edited_role="head_of_year",
    )

    await db.commit()
    await db.refresh(report)

    return _normalise_loaded_report(report)


async def return_student_report_as_head_of_year(
    db: AsyncSession,
    *,
    report: StudentReport,
    head_of_year_id: int,
    review_comments: str,
) -> StudentReport:
    """
    Return a report to its author from the Head-of-Year review stage.
    """

    _validate_tutor_review_status(
        report,
        action_label="returned by the Head of Year",
    )

    cleaned_comments = _clean_optional_text(review_comments)

    if cleaned_comments is None:
        raise ValueError("Review comments are required when returning a report.")

    now = _utc_now()

    report.status = REPORT_STATUS_RETURNED_BY_TUTOR
    report.tutor_review_comments = cleaned_comments
    report.tutor_reviewed_at = now
    report.tutor_reviewed_by_id = head_of_year_id

    _set_model_value(
        report,
        "head_of_year_reviewed_at",
        now,
    )

    _set_model_value(
        report,
        "head_of_year_reviewed_by_id",
        head_of_year_id,
    )

    report.ready_for_smt_at = None
    report.ready_for_smt_by_id = None

    _clear_smt_review_fields(report)

    _clear_headteacher_review_fields(report)

    _clear_publication_fields(report)

    _set_edit_audit(
        report,
        edited_by_id=head_of_year_id,
        edited_role="head_of_year",
    )

    await db.commit()
    await db.refresh(report)

    return _normalise_loaded_report(report)
# ---------------------------------------------------------------------------
# SMT review
# ---------------------------------------------------------------------------


SMT_REVIEWABLE_STATUSES: set[str] = {
    REPORT_STATUS_SUBMITTED,
    REPORT_STATUS_READY_FOR_SMT,
}


def _validate_smt_review_status(
    report: StudentReport,
    *,
    action_label: str,
    allowed_statuses: set[str] | None = None,
) -> None:
    """
    Validate that a report may enter an SMT review action.
    """

    if report.published or report.status == REPORT_STATUS_PUBLISHED:
        raise ValueError("Published reports cannot be changed through SMT review.")

    resolved_statuses = (
        SMT_REVIEWABLE_STATUSES if allowed_statuses is None else allowed_statuses
    )

    if report.status not in resolved_statuses:
        raise ValueError(
            f"This report cannot be {action_label} while its status is "
            f"'{report.status}'."
        )


def _record_smt_review(
    report: StudentReport,
    *,
    reviewer_id: int,
    reviewer_role: str,
    review_comments: str | None = None,
) -> None:
    """
    Record SMT review metadata using both the current and staged field names.
    """

    now = _utc_now()

    # Current/legacy workflow fields used by the API schemas and tests.
    report.reviewed_at = now
    report.reviewed_by_id = reviewer_id

    cleaned_comments = _clean_optional_text(review_comments)

    if review_comments is not None:
        report.review_comments = cleaned_comments

    # Staged SMT-specific fields, when the model exposes them.
    _set_model_value(
        report,
        "smt_reviewed_at",
        now,
    )

    _set_model_value(
        report,
        "smt_reviewed_by_id",
        reviewer_id,
    )

    if review_comments is not None:
        _set_model_value(
            report,
            "smt_review_comments",
            cleaned_comments,
        )

    _set_edit_audit(
        report,
        edited_by_id=reviewer_id,
        edited_role=(
            _normalise_code(
                reviewer_role,
                fallback="smt",
            )
            or "smt"
        ),
    )

async def begin_smt_review(
    db: AsyncSession,
    *,
    report: StudentReport,
    reviewer_id: int,
    reviewer_role: str = "smt",
) -> StudentReport:
    """
    Record that an authorised SMT reviewer has opened the report.

    The report remains in its current workflow status. This allows review
    activity to be audited without introducing an additional status.
    """

    _validate_smt_review_status(
        report,
        action_label="opened for SMT review",
        allowed_statuses={
            REPORT_STATUS_SUBMITTED,
            REPORT_STATUS_TUTOR_REVIEW,
            REPORT_STATUS_READY_FOR_SMT,
        },
    )

    if reviewer_id < 1:
        raise ValueError("A valid SMT reviewer is required.")

    _record_smt_review(
        report,
        reviewer_id=reviewer_id,
        reviewer_role=reviewer_role,
    )

    await db.commit()
    await db.refresh(report)

    return _normalise_loaded_report(report)


async def update_student_report_during_smt_review(
    db: AsyncSession,
    *,
    report: StudentReport,
    payload: StudentReportUpdate,
    reviewer_id: int,
    reviewer_role: str = "smt",
) -> StudentReport:
    """
    Save SMT corrections without approving or publishing the report.

    The original report author remains unchanged. The current workflow status
    is preserved unless it was already approved and the correction invalidates
    that approval, in which case it returns to ``ready_for_smt``.
    """

    _validate_smt_review_status(
        report,
        action_label="edited during SMT review",
    )

    if reviewer_id < 1:
        raise ValueError("A valid SMT reviewer is required.")

    update_data = _payload_to_dict(
        payload,
        exclude_unset=True,
    )

    _validate_reviewer_update_fields(update_data)

    previous_status = report.status

    _apply_reviewer_payload(
        report,
        update_data,
    )

    report_session = await _get_report_session(
        db,
        school_id=report.school_id,
        report_session_id=report.report_session_id,
    )

    _apply_session_defaults(
        report,
        report_session,
    )

    _validate_report_session_assignment(
        report,
        report_session,
    )

    _validate_report_before_save(report)

    if previous_status == REPORT_STATUS_APPROVED:
        report.status = REPORT_STATUS_READY_FOR_SMT

        _clear_approval_fields(report)

    _clear_publication_fields(report)

    _record_smt_review(
        report,
        reviewer_id=reviewer_id,
        reviewer_role=reviewer_role,
    )

    await db.commit()
    await db.refresh(report)

    return _normalise_loaded_report(report)


async def correct_student_report_as_smt(
    db: AsyncSession,
    *,
    report: StudentReport,
    reviewer_id: int,
    report_text: str,
    review_comments: str | None = None,
    reviewer_role: str = "smt",
) -> StudentReport:
    """
    Correct the main report text during SMT review without changing the
    recorded author.
    """

    _validate_smt_review_status(
        report,
        action_label="corrected during SMT review",
    )

    cleaned_report_text = _clean_optional_text(report_text)

    if cleaned_report_text is None:
        raise ValueError("The corrected report text cannot be empty.")

    previous_status = report.status

    report.report_text = cleaned_report_text

    _synchronise_legacy_fields(report)

    _normalise_report_metadata(report)

    _validate_report_before_save(report)

    if previous_status == REPORT_STATUS_APPROVED:
        report.status = REPORT_STATUS_READY_FOR_SMT

        _clear_approval_fields(report)

    _clear_publication_fields(report)

    _record_smt_review(
        report,
        reviewer_id=reviewer_id,
        reviewer_role=reviewer_role,
        review_comments=review_comments,
    )

    await db.commit()
    await db.refresh(report)

    return _normalise_loaded_report(report)


async def return_student_report_from_smt(
    db: AsyncSession,
    *,
    report: StudentReport,
    reviewer_id: int,
    review_comments: str,
    reviewer_role: str = "smt",
) -> StudentReport:
    """
    Return a report to its author for correction from SMT review.

    A reason is mandatory. Previous approval and publication metadata are
    cleared.
    """

    _validate_smt_review_status(
        report,
        action_label="returned by SMT",
    )

    if reviewer_id < 1:
        raise ValueError("A valid SMT reviewer is required.")

    cleaned_comments = _clean_optional_text(review_comments)

    if cleaned_comments is None:
        raise ValueError("SMT comments are required when returning a report.")

    report.status = REPORT_STATUS_RETURNED_BY_SMT

    _record_smt_review(
        report,
        reviewer_id=reviewer_id,
        reviewer_role=reviewer_role,
        review_comments=cleaned_comments,
    )

    _set_model_value(
        report,
        "returned_by_smt_at",
        _utc_now(),
    )

    _set_model_value(
        report,
        "returned_by_smt_by_id",
        reviewer_id,
    )

    _clear_approval_fields(report)

    _clear_publication_fields(report)

    await db.commit()
    await db.refresh(report)

    return _normalise_loaded_report(report)


async def return_student_report_to_tutor_review(
    db: AsyncSession,
    *,
    report: StudentReport,
    reviewer_id: int,
    review_comments: str,
    reviewer_role: str = "smt",
) -> StudentReport:
    """
    Return a report from SMT to the tutor-review stage rather than directly to
    the original author.

    This is useful where the report wording is acceptable but tutor or pastoral
    sections require further work.
    """

    _validate_smt_review_status(
        report,
        action_label="returned to tutor review",
        allowed_statuses={
            REPORT_STATUS_READY_FOR_SMT,
            REPORT_STATUS_APPROVED,
        },
    )

    cleaned_comments = _clean_optional_text(review_comments)

    if cleaned_comments is None:
        raise ValueError(
            "SMT comments are required when returning a report to tutor " "review."
        )

    report.status = REPORT_STATUS_TUTOR_REVIEW

    report.ready_for_smt_at = None
    report.ready_for_smt_by_id = None

    _record_smt_review(
        report,
        reviewer_id=reviewer_id,
        reviewer_role=reviewer_role,
        review_comments=cleaned_comments,
    )

    _clear_approval_fields(report)

    _clear_publication_fields(report)

    await db.commit()
    await db.refresh(report)

    return _normalise_loaded_report(report)


async def approve_student_report(
    db: AsyncSession,
    *,
    report: StudentReport,
    reviewed_by_id: int,
    review_comments: str | None = None,
    reviewer_role: str = "smt",
) -> StudentReport:
    """
    Approve a report for publication.

    Only an endpoint that has confirmed SMT, School Admin or Platform Admin
    permission should call this function.
    """

    _validate_smt_review_status(
        report,
        action_label="approved",
        allowed_statuses={
            REPORT_STATUS_SUBMITTED,
            REPORT_STATUS_TUTOR_REVIEW,
            REPORT_STATUS_READY_FOR_SMT,
        },
    )

    if reviewed_by_id < 1:
        raise ValueError("A valid approving user is required.")

    report_session = await _validate_report_for_submission(
        db,
        report=report,
    )

    _apply_session_defaults(
        report,
        report_session,
    )

    _validate_report_session_assignment(
        report,
        report_session,
    )

    requires_tutor_review = _submission_requires_tutor_review(report)

    if requires_tutor_review and report.status in {
        REPORT_STATUS_SUBMITTED,
    }:
        raise ValueError("This report requires tutor review before it can be approved.")

    now = _utc_now()

    report.status = REPORT_STATUS_APPROVED

    report.approved_at = now
    report.approved_by_id = reviewed_by_id
    
    cleaned_comments = _clean_optional_text(review_comments)

    if review_comments is not None:
        _set_model_value(
            report,
            "approval_comments",
            cleaned_comments,
        )

    _record_smt_review(
        report,
        reviewer_id=reviewed_by_id,
        reviewer_role=reviewer_role,
        review_comments=cleaned_comments,
    )

    _clear_publication_fields(report)

    await db.commit()
    await db.refresh(report)

    return _normalise_loaded_report(report)


async def revoke_student_report_approval(
    db: AsyncSession,
    *,
    report: StudentReport,
    revoked_by_id: int,
    reason: str | None = None,
    reviewer_role: str = "smt",
) -> StudentReport:
    """
    Revoke approval before publication and return the report to SMT review.
    """

    if report.published or report.status == REPORT_STATUS_PUBLISHED:
        raise ValueError(
            "A published report must be unpublished before approval can be " "revoked."
        )

    if report.status != REPORT_STATUS_APPROVED:
        raise ValueError("Only an approved report can have its approval revoked.")

    report.status = REPORT_STATUS_READY_FOR_SMT

    cleaned_reason = _clean_optional_text(reason)

    _clear_approval_fields(report)

    _clear_publication_fields(report)

    _record_smt_review(
        report,
        reviewer_id=revoked_by_id,
        reviewer_role=reviewer_role,
        review_comments=cleaned_reason,
    )

    _set_model_value(
        report,
        "approval_revoked_at",
        _utc_now(),
    )

    _set_model_value(
        report,
        "approval_revoked_by_id",
        revoked_by_id,
    )

    _set_model_value(
        report,
        "approval_revocation_reason",
        cleaned_reason,
    )

    await db.commit()
    await db.refresh(report)

    return _normalise_loaded_report(report)


async def record_headteacher_review(
    db: AsyncSession,
    *,
    report: StudentReport,
    headteacher_id: int,
    headteacher_comment: str | None = None,
    review_comments: str | None = None,
) -> StudentReport:
    """
    Record a Headteacher or Headmaster review.

    The Headteacher may edit and save reports but does not approve or publish
    through this function.
    """

    _validate_smt_review_status(
        report,
        action_label="reviewed by the Headteacher",
    )

    if headteacher_id < 1:
        raise ValueError("A valid Headteacher is required.")

    cleaned_headteacher_comment = _clean_optional_text(headteacher_comment)

    if headteacher_comment is not None:
        _set_model_value(
            report,
            "headteacher_comment",
            cleaned_headteacher_comment,
        )

    now = _utc_now()

    _set_model_value(
        report,
        "headteacher_reviewed_at",
        now,
    )

    _set_model_value(
        report,
        "headteacher_reviewed_by_id",
        headteacher_id,
    )

    _record_smt_review(
        report,
        reviewer_id=headteacher_id,
        reviewer_role="headteacher",
        review_comments=review_comments,
    )

    _clear_publication_fields(report)

    await db.commit()
    await db.refresh(report)

    return _normalise_loaded_report(report)
# ---------------------------------------------------------------------------
# Publication
# ---------------------------------------------------------------------------


PUBLISHABLE_STATUSES: set[str] = {
    REPORT_STATUS_APPROVED,
}


def _validate_publication_status(
    report: StudentReport,
    *,
    action_label: str,
    allowed_statuses: set[str] | None = None,
) -> None:
    """
    Validate that a report may be published or unpublished.
    """

    resolved_statuses = (
        PUBLISHABLE_STATUSES if allowed_statuses is None else allowed_statuses
    )

    if report.status not in resolved_statuses:
        raise ValueError(
            f"This report cannot be {action_label} while its status is "
            f"'{report.status}'."
        )


def _record_publication(
    report: StudentReport,
    *,
    published_by_id: int,
) -> None:
    """
    Record publication metadata.
    """

    now = _utc_now()

    report.status = REPORT_STATUS_PUBLISHED
    report.published = True
    report.published_at = now
    report.published_by_id = published_by_id

    _set_edit_audit(
        report,
        edited_by_id=published_by_id,
        edited_role="publisher",
    )


async def publish_student_report(
    db: AsyncSession,
    *,
    report: StudentReport,
    published_by_id: int,
) -> StudentReport:
    """
    Publish an approved report.

    Only School Admins and Platform Admins should reach this repository
    function. Endpoint permission checks remain responsible for authorisation.
    """

    _validate_publication_status(
        report,
        action_label="published",
    )

    if published_by_id < 1:
        raise ValueError("A valid publishing user is required.")

    report_session = await _get_report_session(
        db,
        school_id=report.school_id,
        report_session_id=report.report_session_id,
    )

    if report_session is None:
        raise ValueError("The reporting session no longer exists.")

    if _session_is_locked(report_session):
        raise ValueError(
            "Reports cannot be published while the reporting session is locked."
        )

    _validate_report_before_save(
        report,
    )

    _record_publication(
        report,
        published_by_id=published_by_id,
    )

    await db.commit()
    await db.refresh(report)

    return _normalise_loaded_report(report)


async def publish_student_reports(
    db: AsyncSession,
    *,
    reports: Iterable[StudentReport],
    published_by_id: int,
) -> list[StudentReport]:
    """
    Publish multiple approved reports within one transaction.
    """

    reports = list(reports)

    if not reports:
        return []

    now = _utc_now()

    for report in reports:
        _validate_publication_status(
            report,
            action_label="published",
        )

        report_session = await _get_report_session(
            db,
            school_id=report.school_id,
            report_session_id=report.report_session_id,
        )

        if report_session is None:
            raise ValueError("A reporting session could not be found.")

        if _session_is_locked(report_session):
            raise ValueError(
                "One or more reports belong to a locked reporting session."
            )

        _validate_report_before_save(
            report,
        )

        report.status = REPORT_STATUS_PUBLISHED
        report.published = True
        report.published_at = now
        report.published_by_id = published_by_id

        _set_edit_audit(
            report,
            edited_by_id=published_by_id,
            edited_role="publisher",
        )

    await db.commit()

    refreshed_reports: list[StudentReport] = []

    for report in reports:
        await db.refresh(report)
        refreshed_reports.append(_normalise_loaded_report(report))

    return refreshed_reports


async def unpublish_student_report(
    db: AsyncSession,
    *,
    report: StudentReport,
    unpublished_by_id: int,
    reason: str | None = None,
    return_status: str = REPORT_STATUS_DRAFT,
) -> StudentReport:
    """
    Unpublish a report.

    By agreement this returns the report to Draft so that further corrections
    may be made before repeating the approval workflow.
    """

    if not report.published and report.status != REPORT_STATUS_PUBLISHED:
        raise ValueError("Only published reports can be unpublished.")

    allowed_return_statuses = {
        REPORT_STATUS_DRAFT,
        REPORT_STATUS_READY_FOR_SMT,
        REPORT_STATUS_APPROVED,
    }

    if return_status not in allowed_return_statuses:
        raise ValueError("Unsupported return status after unpublishing.")

    report.status = return_status
    report.published = False

    _set_model_value(
        report,
        "unpublished_at",
        _utc_now(),
    )

    _set_model_value(
        report,
        "unpublished_by_id",
        unpublished_by_id,
    )

    _set_model_value(
        report,
        "unpublished_reason",
        _clean_optional_text(reason),
    )

    report.published_at = None
    report.published_by_id = None

    if return_status != REPORT_STATUS_APPROVED:
        _clear_approval_fields(
            report,
        )

    _set_edit_audit(
        report,
        edited_by_id=unpublished_by_id,
        edited_role="unpublisher",
    )

    await db.commit()
    await db.refresh(report)

    return _normalise_loaded_report(report)


async def bulk_unpublish_student_reports(
    db: AsyncSession,
    *,
    reports: Iterable[StudentReport],
    unpublished_by_id: int,
    reason: str | None = None,
) -> list[StudentReport]:
    """
    Unpublish multiple reports.

    All reports are returned to Draft in accordance with the agreed workflow.
    """

    reports = list(reports)

    if not reports:
        return []

    now = _utc_now()

    for report in reports:
        if not report.published and report.status != REPORT_STATUS_PUBLISHED:
            raise ValueError("All selected reports must already be published.")

        report.status = REPORT_STATUS_DRAFT
        report.published = False
        report.published_at = None
        report.published_by_id = None

        _clear_approval_fields(
            report,
        )

        _set_model_value(
            report,
            "unpublished_at",
            now,
        )

        _set_model_value(
            report,
            "unpublished_by_id",
            unpublished_by_id,
        )

        _set_model_value(
            report,
            "unpublished_reason",
            _clean_optional_text(reason),
        )

        _set_edit_audit(
            report,
            edited_by_id=unpublished_by_id,
            edited_role="unpublisher",
        )

    await db.commit()

    refreshed_reports: list[StudentReport] = []

    for report in reports:
        await db.refresh(report)
        refreshed_reports.append(_normalise_loaded_report(report))

    return refreshed_reports


async def mark_reporting_session_published(
    db: AsyncSession,
    *,
    report_session: ReportSession,
    published_by_id: int,
) -> ReportSession:
    """
    Mark an entire reporting session as published.

    This does not automatically publish individual reports. It records the
    reporting-session publication event.
    """

    _set_model_value(
        report_session,
        "published",
        True,
    )

    _set_model_value(
        report_session,
        "published_at",
        _utc_now(),
    )

    _set_model_value(
        report_session,
        "published_by_id",
        published_by_id,
    )

    await db.commit()
    await db.refresh(report_session)

    return report_session


async def reopen_reporting_session(
    db: AsyncSession,
    *,
    report_session: ReportSession,
    reopened_by_id: int,
) -> ReportSession:
    """
    Reopen a reporting session after publication.

    Existing published reports remain published. This simply allows further
    editing and publishing activity.
    """

    _set_model_value(
        report_session,
        "published",
        False,
    )

    _set_model_value(
        report_session,
        "published_at",
        None,
    )

    _set_model_value(
        report_session,
        "published_by_id",
        None,
    )

    _set_model_value(
        report_session,
        "reopened_at",
        _utc_now(),
    )

    _set_model_value(
        report_session,
        "reopened_by_id",
        reopened_by_id,
    )

    await db.commit()
    await db.refresh(report_session)

    return report_session
# ---------------------------------------------------------------------------
# Delete
# ---------------------------------------------------------------------------


DELETABLE_REPORT_STATUSES: set[str] = {
    REPORT_STATUS_DRAFT,
    REPORT_STATUS_RETURNED_BY_TUTOR,
    REPORT_STATUS_RETURNED_BY_SMT,
}


def _validate_report_can_be_deleted(
    report: StudentReport,
    *,
    allow_non_draft: bool = False,
) -> None:
    """
    Validate whether a report may be permanently deleted.

    Ordinary authors may delete only draft or returned reports. A privileged
    administrative endpoint may pass ``allow_non_draft=True`` for exceptional
    cleanup, but published reports must still be unpublished first.
    """

    if report.published or report.status == REPORT_STATUS_PUBLISHED:
        raise ValueError(
            "Published reports cannot be deleted. Unpublish the report first."
        )

    if not allow_non_draft and report.status not in DELETABLE_REPORT_STATUSES:
        raise ValueError(
            "Only draft reports or reports returned for correction can be " "deleted."
        )


async def delete_student_report(
    db: AsyncSession,
    *,
    report: StudentReport,
    deleted_by_id: int | None = None,
    allow_non_draft: bool = False,
) -> None:
    """
    Permanently delete one report.

    Permission and pupil-scope checks remain the responsibility of the
    endpoint. This repository function enforces publication and workflow
    restrictions.
    """

    _validate_report_can_be_deleted(
        report,
        allow_non_draft=allow_non_draft,
    )

    if deleted_by_id is not None:
        _set_edit_audit(
            report,
            edited_by_id=deleted_by_id,
            edited_role="report_deleter",
        )

    await db.delete(report)
    await db.commit()


async def delete_student_reports(
    db: AsyncSession,
    *,
    reports: Iterable[StudentReport],
    deleted_by_id: int | None = None,
    allow_non_draft: bool = False,
) -> int:
    """
    Permanently delete several reports within one transaction.

    Validation is completed for every report before any deletion occurs.
    """

    resolved_reports = list(reports)

    if not resolved_reports:
        return 0

    for report in resolved_reports:
        _validate_report_can_be_deleted(
            report,
            allow_non_draft=allow_non_draft,
        )

    for report in resolved_reports:
        if deleted_by_id is not None:
            _set_edit_audit(
                report,
                edited_by_id=deleted_by_id,
                edited_role="report_deleter",
            )

        await db.delete(report)

    await db.commit()

    return len(resolved_reports)


async def delete_reports_for_reporting_session(
    db: AsyncSession,
    *,
    school_id: int,
    report_session_id: int,
    deleted_by_id: int | None = None,
    allow_non_draft: bool = False,
) -> int:
    """
    Delete reports belonging to one reporting session.

    Published reports are never deleted through this helper.
    """

    result = await db.execute(
        select(StudentReport).where(
            StudentReport.school_id == school_id,
            StudentReport.report_session_id == report_session_id,
        ),
    )

    reports = list(result.scalars().all())

    return await delete_student_reports(
        db,
        reports=reports,
        deleted_by_id=deleted_by_id,
        allow_non_draft=allow_non_draft,
    )


# ---------------------------------------------------------------------------
# Export and download queries
# ---------------------------------------------------------------------------


EXPORT_STATUS_DRAFT = "draft"
EXPORT_STATUS_PUBLISHED = "published"
EXPORT_STATUS_ALL = "all"

ALL_EXPORT_STATUSES: set[str] = {
    EXPORT_STATUS_DRAFT,
    EXPORT_STATUS_PUBLISHED,
    EXPORT_STATUS_ALL,
}


def _apply_export_status_filter(
    statement,
    *,
    export_status: str,
):
    """
    Apply the requested draft, published or all export filter.
    """

    normalised_status = _normalise_code(
        export_status,
        fallback=EXPORT_STATUS_PUBLISHED,
    )

    if normalised_status not in ALL_EXPORT_STATUSES:
        raise ValueError("Export status must be 'draft', 'published' or 'all'.")

    if normalised_status == EXPORT_STATUS_PUBLISHED:
        return statement.where(
            StudentReport.status == REPORT_STATUS_PUBLISHED,
            StudentReport.published.is_(True),
        )

    if normalised_status == EXPORT_STATUS_DRAFT:
        return statement.where(
            StudentReport.status != REPORT_STATUS_PUBLISHED,
            StudentReport.published.is_(False),
        )

    return statement


async def list_student_reports_for_export(
    db: AsyncSession,
    *,
    school_id: int,
    report_session_id: int | None = None,
    student_id: int | None = None,
    teacher_id: int | None = None,
    report_type_id: int | None = None,
    report_type_code: str | None = None,
    report_kind: str | None = None,
    export_status: str = EXPORT_STATUS_PUBLISHED,
    include_in_final_report_only: bool = True,
    limit: int = 5000,
    offset: int = 0,
) -> list[StudentReport]:
    """
    Return reports for PDF or ZIP export.

    This supports draft, published and combined exports. Endpoint permission
    checks determine which users may request each export mode.
    """

    _validate_pagination(
        limit=limit,
        offset=offset,
    )

    statement = select(StudentReport).where(
        StudentReport.school_id == school_id,
    )

    statement = _apply_export_status_filter(
        statement,
        export_status=export_status,
    )

    if report_session_id is not None:
        statement = statement.where(
            StudentReport.report_session_id == report_session_id,
        )

    if student_id is not None:
        statement = statement.where(
            StudentReport.student_id == student_id,
        )

    if teacher_id is not None:
        statement = statement.where(
            StudentReport.teacher_id == teacher_id,
        )

    if include_in_final_report_only and hasattr(
        StudentReport,
        "include_in_final_report",
    ):
        statement = statement.where(
            StudentReport.include_in_final_report.is_(True),
        )

    statement = _apply_report_type_filters(
        statement,
        report_type_id=report_type_id,
        report_type_code=report_type_code,
        report_kind=report_kind,
    )

    statement = (
        statement.order_by(
            StudentReport.student_id.asc(),
            StudentReport.report_session_id.asc(),
            (
                StudentReport.report_type_id.asc()
                if hasattr(
                    StudentReport,
                    "report_type_id",
                )
                else StudentReport.id.asc()
            ),
            StudentReport.created_at.asc(),
            StudentReport.id.asc(),
        )
        .offset(offset)
        .limit(limit)
    )

    result = await db.execute(statement)

    return _normalise_loaded_reports(result.scalars().all())


async def list_reports_for_student_pdf(
    db: AsyncSession,
    *,
    school_id: int,
    student_id: int,
    report_session_id: int,
    export_status: str = EXPORT_STATUS_PUBLISHED,
    include_in_final_report_only: bool = True,
) -> list[StudentReport]:
    """
    Return all ordered sections for one pupil's report PDF.
    """

    return await list_student_reports_for_export(
        db,
        school_id=school_id,
        student_id=student_id,
        report_session_id=report_session_id,
        export_status=export_status,
        include_in_final_report_only=include_in_final_report_only,
        limit=5000,
        offset=0,
    )


async def list_reports_for_session_export(
    db: AsyncSession,
    *,
    school_id: int,
    report_session_id: int,
    export_status: str = EXPORT_STATUS_PUBLISHED,
    report_type_id: int | None = None,
    report_type_code: str | None = None,
    report_kind: str | None = None,
) -> list[StudentReport]:
    """
    Return all reports in a session for administrative ZIP export.
    """

    return await list_student_reports_for_export(
        db,
        school_id=school_id,
        report_session_id=report_session_id,
        report_type_id=report_type_id,
        report_type_code=report_type_code,
        report_kind=report_kind,
        export_status=export_status,
        include_in_final_report_only=True,
        limit=5000,
        offset=0,
    )


# ---------------------------------------------------------------------------
# Parent and pupil published-report access
# ---------------------------------------------------------------------------


async def list_published_reports_for_student(
    db: AsyncSession,
    *,
    school_id: int,
    student_id: int,
    report_session_id: int | None = None,
    limit: int = 500,
    offset: int = 0,
) -> list[StudentReport]:
    """
    Return published reports visible to a pupil or linked parent.
    """

    _validate_pagination(
        limit=limit,
        offset=offset,
    )

    statement = select(StudentReport).where(
        StudentReport.school_id == school_id,
        StudentReport.student_id == student_id,
        StudentReport.status == REPORT_STATUS_PUBLISHED,
        StudentReport.published.is_(True),
    )

    if report_session_id is not None:
        statement = statement.where(
            StudentReport.report_session_id == report_session_id,
        )

    if hasattr(
        StudentReport,
        "include_in_final_report",
    ):
        statement = statement.where(
            StudentReport.include_in_final_report.is_(True),
        )

    statement = (
        statement.order_by(
            StudentReport.published_at.desc(),
            StudentReport.created_at.asc(),
            StudentReport.id.asc(),
        )
        .offset(offset)
        .limit(limit)
    )

    result = await db.execute(statement)

    return _normalise_loaded_reports(result.scalars().all())


async def get_published_student_report(
    db: AsyncSession,
    *,
    school_id: int,
    student_id: int,
    report_id: int,
) -> StudentReport | None:
    """
    Return one published report for a pupil-facing or parent-facing endpoint.
    """

    result = await db.execute(
        select(StudentReport).where(
            StudentReport.id == report_id,
            StudentReport.school_id == school_id,
            StudentReport.student_id == student_id,
            StudentReport.status == REPORT_STATUS_PUBLISHED,
            StudentReport.published.is_(True),
        ),
    )

    report = result.scalar_one_or_none()

    if report is None:
        return None

    return _normalise_loaded_report(report)


async def publish_reports_for_session(
    db: AsyncSession,
    *,
    school_id: int,
    report_session_id: int,
    published_by_id: int,
) -> int:
    """
    Publish all approved reports in one reporting session.

    Returns the number of reports published.
    """

    if published_by_id < 1:
        raise ValueError("A valid publishing user is required.")

    report_session = await _get_report_session(
        db,
        school_id=school_id,
        report_session_id=report_session_id,
    )

    if report_session is None:
        raise ValueError("The reporting session could not be found.")

    if _session_is_locked(report_session):
        raise ValueError(
            "Reports cannot be published while the reporting session is locked."
        )

    result = await db.execute(
        select(StudentReport).where(
            StudentReport.school_id == school_id,
            StudentReport.report_session_id == report_session_id,
            StudentReport.status == REPORT_STATUS_APPROVED,
            StudentReport.published.is_(False),
        )
    )

    reports = list(result.scalars().all())

    if not reports:
        return 0

    await publish_student_reports(
        db,
        reports=reports,
        published_by_id=published_by_id,
    )

    return len(reports)


# ---------------------------------------------------------------------------
# Compatibility aliases
# ---------------------------------------------------------------------------


async def create_report(
    db: AsyncSession,
    *,
    payload: StudentReportCreate,
    school_id: int,
    teacher_id: int,
) -> StudentReport:
    """
    Backward-compatible alias for older service and test imports.
    """

    return await create_student_report(
        db,
        payload=payload,
        school_id=school_id,
        teacher_id=teacher_id,
    )


async def get_report(
    db: AsyncSession,
    *,
    report_id: int,
    school_id: int,
) -> StudentReport | None:
    """
    Backward-compatible alias for the school-scoped report lookup.
    """

    return await get_student_report(
        db,
        report_id=report_id,
        school_id=school_id,
    )


async def update_report(
    db: AsyncSession,
    *,
    report: StudentReport,
    payload: StudentReportUpdate,
    current_user: User | None = None,
) -> StudentReport:
    """
    Backward-compatible alias for ordinary report updates.
    """

    return await update_student_report(
        db,
        report=report,
        payload=payload,
        current_user=current_user,
    )


async def delete_report(
    db: AsyncSession,
    *,
    report: StudentReport,
) -> None:
    """
    Backward-compatible alias for draft report deletion.
    """

    await delete_student_report(
        db,
        report=report,
    )


async def return_student_report(
    db: AsyncSession,
    *,
    report: StudentReport,
    reviewed_by_id: int,
    review_comments: str,
) -> StudentReport:
    """
    Backward-compatible SMT return action used by the API endpoint.
    """

    return await return_student_report_from_smt(
        db,
        report=report,
        reviewer_id=reviewed_by_id,
        review_comments=review_comments,
        reviewer_role="smt",
    )
