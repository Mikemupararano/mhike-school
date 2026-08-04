from __future__ import annotations

import csv
import io

import pytest

from app.imports.bootstrap import register_import_handlers
from app.imports.registry import registered_import_types
from app.services.import_template_service import (
    build_import_template_csv_preview,
    generate_import_template_csv,
    get_import_template_metadata,
    list_import_template_metadata,
    list_import_template_summaries,
)


@pytest.fixture(scope="module", autouse=True)
def register_handlers() -> None:
    """
    Ensure all built-in import handlers are registered for this test module.

    Registration is intentionally idempotent, so this fixture remains safe
    when handlers were already registered during application or test startup.
    """

    register_import_handlers()


def _field_by_name(
    import_type: str,
    field_name: str,
):
    """Return one generated field metadata object by model field name."""

    metadata = get_import_template_metadata(import_type)

    return next(field for field in metadata.fields if field.name == field_name)


def _rules_by_name(field) -> dict[str, object]:
    """Return validation rules keyed by their public rule names."""

    return {rule.name: rule.value for rule in field.validation_rules}


def test_template_summaries_include_every_registered_import_type() -> None:
    result = list_import_template_summaries()
    expected_types = registered_import_types()

    assert result.total == len(expected_types)
    assert result.total == 13

    returned_types = [item.import_type for item in result.items]

    assert returned_types == expected_types


def test_template_summaries_are_sorted_by_import_type() -> None:
    result = list_import_template_summaries()

    returned_types = [item.import_type for item in result.items]

    assert returned_types == sorted(returned_types)


def test_template_summary_contains_counts_and_urls() -> None:
    result = list_import_template_summaries()

    attendance = next(item for item in result.items if item.import_type == "attendance")

    assert attendance.display_name == "Attendance"
    assert attendance.required_field_count == 5
    assert attendance.optional_field_count == 2
    assert attendance.total_field_count == 7

    assert attendance.metadata_url == ("/api/v1/import-batches/templates/attendance")
    assert attendance.download_url == (
        "/api/v1/import-batches/templates/attendance/download"
    )


def test_list_template_metadata_returns_every_registered_handler() -> None:
    metadata_items = list_import_template_metadata()
    expected_types = registered_import_types()

    assert len(metadata_items) == len(expected_types)

    returned_types = [metadata.import_type for metadata in metadata_items]

    assert returned_types == expected_types


def test_attendance_template_metadata_has_expected_identity() -> None:
    metadata = get_import_template_metadata("attendance")

    assert metadata.import_type == "attendance"
    assert metadata.display_name == "Attendance"
    assert metadata.schema_name == "AttendanceImportSchema"

    assert metadata.description == (
        "Import student attendance records for lessons, sessions or " "school days."
    )

    assert metadata.metadata_url == ("/api/v1/import-batches/templates/attendance")
    assert metadata.download_url == (
        "/api/v1/import-batches/templates/attendance/download"
    )


def test_attendance_fields_preserve_schema_order() -> None:
    metadata = get_import_template_metadata("attendance")

    expected_headers = [
        "class_name",
        "session_date",
        "session_type",
        "student_email",
        "status",
        "marked_by_email",
        "notes",
    ]

    assert metadata.csv_headers == expected_headers

    assert [field.column_name for field in metadata.fields] == expected_headers


def test_attendance_required_and_optional_fields_are_detected() -> None:
    metadata = get_import_template_metadata("attendance")

    assert [field.name for field in metadata.required_fields] == [
        "class_name",
        "session_date",
        "session_type",
        "student_email",
        "status",
    ]

    assert [field.name for field in metadata.optional_fields] == [
        "marked_by_email",
        "notes",
    ]


def test_attendance_nullable_fields_are_detected() -> None:
    marked_by_email = _field_by_name(
        "attendance",
        "marked_by_email",
    )
    notes = _field_by_name(
        "attendance",
        "notes",
    )
    student_email = _field_by_name(
        "attendance",
        "student_email",
    )

    assert marked_by_email.required is False
    assert marked_by_email.nullable is True

    assert notes.required is False
    assert notes.nullable is True

    assert student_email.required is True
    assert student_email.nullable is False


def test_attendance_enum_fields_are_reported_as_enums() -> None:
    session_type = _field_by_name(
        "attendance",
        "session_type",
    )
    status = _field_by_name(
        "attendance",
        "status",
    )

    assert session_type.data_type == "enum"
    assert session_type.python_type == "AttendanceSessionType"
    assert session_type.accepted_values == [
        "am",
        "pm",
    ]

    assert status.data_type == "enum"
    assert status.python_type == "AttendanceStatus"
    assert status.accepted_values == [
        "present",
        "late",
        "authorised_absence",
        "unauthorised_absence",
    ]


def test_attendance_email_and_date_formats_are_detected() -> None:
    session_date = _field_by_name(
        "attendance",
        "session_date",
    )
    student_email = _field_by_name(
        "attendance",
        "student_email",
    )
    marked_by_email = _field_by_name(
        "attendance",
        "marked_by_email",
    )

    assert session_date.data_type == "date"
    assert student_email.data_type == "email"
    assert marked_by_email.data_type == "email"

    assert _rules_by_name(session_date)["format"] == "date"
    assert _rules_by_name(student_email)["format"] == "email"
    assert _rules_by_name(marked_by_email)["format"] == "email"


def test_attendance_string_constraints_are_extracted() -> None:
    class_name = _field_by_name(
        "attendance",
        "class_name",
    )
    notes = _field_by_name(
        "attendance",
        "notes",
    )

    class_name_rules = _rules_by_name(class_name)
    notes_rules = _rules_by_name(notes)

    assert class_name_rules["min_length"] == 1
    assert class_name_rules["max_length"] == 255
    assert notes_rules["max_length"] == 500


def test_enum_values_are_also_exposed_as_validation_rules() -> None:
    status = _field_by_name(
        "attendance",
        "status",
    )

    rules = _rules_by_name(status)

    assert rules["accepted_values"] == [
        "present",
        "late",
        "authorised_absence",
        "unauthorised_absence",
    ]


def test_attendance_descriptions_are_generated_from_schema() -> None:
    class_name = _field_by_name(
        "attendance",
        "class_name",
    )
    session_date = _field_by_name(
        "attendance",
        "session_date",
    )
    notes = _field_by_name(
        "attendance",
        "notes",
    )

    assert class_name.description == (
        "Name of the class associated with the attendance session. "
        "The class must already exist in the current school."
    )

    assert session_date.description == (
        "Date of the attendance session in ISO format: YYYY-MM-DD."
    )

    assert notes.description == (
        "Optional attendance note providing additional context, such as "
        "a reason for lateness or absence."
    )


def test_attendance_examples_are_generated_from_schema() -> None:
    metadata = get_import_template_metadata("attendance")

    assert metadata.sample_row == {
        "class_name": "Year 10 Physics",
        "session_date": "2026-08-04",
        "session_type": "am",
        "student_email": "student@example.com",
        "status": "present",
        "marked_by_email": "teacher@example.com",
        "notes": ("Arrived 10 minutes late due to transport disruption."),
    }


def test_student_template_required_fields_are_derived_from_schema() -> None:
    metadata = get_import_template_metadata("students")

    assert metadata.schema_name == "StudentImportSchema"

    assert metadata.csv_headers == [
        "email",
        "first_name",
        "last_name",
    ]

    assert [field.name for field in metadata.required_fields] == [
        "email",
        "first_name",
        "last_name",
    ]

    assert metadata.optional_fields == []


def test_assignment_submission_defaults_are_exposed() -> None:
    status = _field_by_name(
        "assignment_submissions",
        "status",
    )

    assert status.required is False
    assert status.nullable is False
    assert status.default == "submitted"
    assert status.example == "submitted"


def test_generate_attendance_csv_includes_header_and_sample_row() -> None:
    csv_content = generate_import_template_csv(
        "attendance",
    )

    rows = list(
        csv.reader(
            io.StringIO(csv_content),
        ),
    )

    assert rows == [
        [
            "class_name",
            "session_date",
            "session_type",
            "student_email",
            "status",
            "marked_by_email",
            "notes",
        ],
        [
            "Year 10 Physics",
            "2026-08-04",
            "am",
            "student@example.com",
            "present",
            "teacher@example.com",
            "Arrived 10 minutes late due to transport disruption.",
        ],
    ]


def test_generate_csv_can_exclude_sample_row() -> None:
    csv_content = generate_import_template_csv(
        "attendance",
        include_sample_row=False,
    )

    rows = list(
        csv.reader(
            io.StringIO(csv_content),
        ),
    )

    assert rows == [
        [
            "class_name",
            "session_date",
            "session_type",
            "student_email",
            "status",
            "marked_by_email",
            "notes",
        ],
    ]


def test_csv_generation_uses_crlf_line_endings() -> None:
    csv_content = generate_import_template_csv(
        "attendance",
    )

    assert "\r\n" in csv_content
    assert csv_content.endswith("\r\n")


def test_csv_preview_contains_filename_content_type_and_csv() -> None:
    preview = build_import_template_csv_preview(
        "attendance",
    )

    assert preview.import_type == "attendance"
    assert preview.filename == "attendance_import_template.csv"
    assert preview.content_type == "text/csv"

    assert preview.csv_content == generate_import_template_csv(
        "attendance",
    )


def test_csv_preview_can_exclude_sample_row() -> None:
    preview = build_import_template_csv_preview(
        "attendance",
        include_sample_row=False,
    )

    rows = list(
        csv.reader(
            io.StringIO(preview.csv_content),
        ),
    )

    assert len(rows) == 1


def test_unknown_import_type_raises_key_error() -> None:
    with pytest.raises(
        KeyError,
        match="No import handler registered",
    ):
        get_import_template_metadata(
            "unknown_import_type",
        )


def test_unknown_import_type_cannot_generate_csv() -> None:
    with pytest.raises(
        KeyError,
        match="No import handler registered",
    ):
        generate_import_template_csv(
            "unknown_import_type",
        )


def test_every_template_has_consistent_field_counts() -> None:
    for metadata in list_import_template_metadata():
        assert len(metadata.fields) == (
            len(metadata.required_fields) + len(metadata.optional_fields)
        )

        assert len(metadata.csv_headers) == len(metadata.fields)
        assert len(metadata.sample_row) == len(metadata.fields)


def test_every_template_has_unique_csv_headers() -> None:
    for metadata in list_import_template_metadata():
        assert len(metadata.csv_headers) == len(
            set(metadata.csv_headers),
        )


def test_every_template_has_complete_urls() -> None:
    for metadata in list_import_template_metadata():
        assert metadata.metadata_url == (
            "/api/v1/import-batches/templates/" f"{metadata.import_type}"
        )

        assert metadata.download_url == (
            "/api/v1/import-batches/templates/" f"{metadata.import_type}/download"
        )
