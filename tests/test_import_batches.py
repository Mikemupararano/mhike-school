from __future__ import annotations

import pytest
from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
)

from app.api.v1.api import api_router
from app.services.import_service import (
    ImportFileError,
    ImportHeaderError,
    normalise_cell,
    normalise_header,
    parse_csv_bytes,
    validate_row_with_schema,
)


class StudentImportRow(BaseModel):
    """Small test schema representing an imported student row."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    first_name: str = Field(
        min_length=1,
    )
    last_name: str = Field(
        min_length=1,
    )
    email: EmailStr
    year_group: int = Field(
        ge=1,
        le=13,
    )


def test_normalise_header_converts_text_to_snake_case() -> None:
    assert normalise_header("First Name") == "first_name"
    assert normalise_header("E-mail Address") == "e_mail_address"
    assert normalise_header("  Year Group  ") == "year_group"
    assert normalise_header("Student.ID") == "student_id"


def test_normalise_header_removes_repeated_separators() -> None:
    assert normalise_header("First   Name") == "first_name"
    assert normalise_header("First---Name") == "first_name"
    assert normalise_header("First___Name") == "first_name"


def test_normalise_cell_strips_whitespace() -> None:
    assert normalise_cell("  Alice  ") == "Alice"
    assert normalise_cell(10) == "10"


def test_normalise_cell_converts_blank_values_to_none() -> None:
    assert normalise_cell("") is None
    assert normalise_cell("   ") is None
    assert normalise_cell(None) is None


def test_parse_csv_bytes_parses_valid_csv() -> None:
    content = (
        b"First Name,Last Name,Email,Year Group\n"
        b"Alice,Johnson,alice@example.com,7\n"
        b"Brian,Smith,brian@example.com,8\n"
    )

    parsed = parse_csv_bytes(
        content,
        required_headers=[
            "first_name",
            "last_name",
            "email",
            "year_group",
        ],
    )

    assert parsed.headers == [
        "first_name",
        "last_name",
        "email",
        "year_group",
    ]
    assert parsed.encoding == "utf-8-sig"
    assert parsed.delimiter == ","
    assert len(parsed.rows) == 2

    assert parsed.rows[0] == {
        "first_name": "Alice",
        "last_name": "Johnson",
        "email": "alice@example.com",
        "year_group": "7",
    }

    assert parsed.rows[1] == {
        "first_name": "Brian",
        "last_name": "Smith",
        "email": "brian@example.com",
        "year_group": "8",
    }


def test_parse_csv_bytes_supports_semicolon_delimiter() -> None:
    content = b"First Name;Last Name;Email\n" b"Alice;Johnson;alice@example.com\n"

    parsed = parse_csv_bytes(
        content,
    )

    assert parsed.delimiter == ";"
    assert parsed.rows == [
        {
            "first_name": "Alice",
            "last_name": "Johnson",
            "email": "alice@example.com",
        }
    ]


def test_parse_csv_bytes_ignores_completely_blank_rows() -> None:
    content = (
        b"First Name,Last Name,Email\n"
        b"Alice,Johnson,alice@example.com\n"
        b",,\n"
        b"   ,   ,   \n"
        b"Brian,Smith,brian@example.com\n"
    )

    parsed = parse_csv_bytes(
        content,
    )

    assert len(parsed.rows) == 2
    assert parsed.rows[0]["first_name"] == "Alice"
    assert parsed.rows[1]["first_name"] == "Brian"


def test_parse_csv_bytes_converts_blank_cells_to_none() -> None:
    content = b"First Name,Last Name,Email\n" b"Alice,,alice@example.com\n"

    parsed = parse_csv_bytes(
        content,
    )

    assert parsed.rows[0] == {
        "first_name": "Alice",
        "last_name": None,
        "email": "alice@example.com",
    }


def test_parse_csv_bytes_rejects_empty_file() -> None:
    with pytest.raises(
        ImportFileError,
        match="uploaded import file is empty",
    ):
        parse_csv_bytes(
            b"",
        )


def test_parse_csv_bytes_rejects_header_without_data_rows() -> None:
    content = b"First Name,Last Name,Email\n"

    with pytest.raises(
        ImportFileError,
        match="does not contain any data rows",
    ):
        parse_csv_bytes(
            content,
        )


def test_parse_csv_bytes_rejects_missing_required_headers() -> None:
    content = b"First Name,Last Name\n" b"Alice,Johnson\n"

    with pytest.raises(
        ImportHeaderError,
        match="Missing required import headers: email",
    ):
        parse_csv_bytes(
            content,
            required_headers=[
                "first_name",
                "last_name",
                "email",
            ],
        )


def test_parse_csv_bytes_normalises_required_header_names() -> None:
    content = (
        b"First Name,Last Name,Email Address\n" b"Alice,Johnson,alice@example.com\n"
    )

    parsed = parse_csv_bytes(
        content,
        required_headers=[
            "First Name",
            "Last Name",
            "Email Address",
        ],
    )

    assert parsed.headers == [
        "first_name",
        "last_name",
        "email_address",
    ]


def test_parse_csv_bytes_rejects_duplicate_normalised_headers() -> None:
    content = b"First Name,First-Name,Email\n" b"Alice,Alison,alice@example.com\n"

    with pytest.raises(
        ImportHeaderError,
        match="Duplicate import headers were found: first_name",
    ):
        parse_csv_bytes(
            content,
        )


def test_parse_csv_bytes_rejects_invalid_blank_header() -> None:
    content = b"First Name,---,Email\n" b"Alice,unused,alice@example.com\n"

    with pytest.raises(
        ImportHeaderError,
        match="headers are blank or invalid",
    ):
        parse_csv_bytes(
            content,
        )


def test_parse_csv_bytes_rejects_more_than_maximum_rows() -> None:
    content = b"First Name,Last Name\n" b"Alice,Johnson\n" b"Brian,Smith\n"

    with pytest.raises(
        ImportFileError,
        match="exceeds the maximum of 1 data rows",
    ):
        parse_csv_bytes(
            content,
            maximum_rows=1,
        )


def test_parse_csv_bytes_rejects_invalid_maximum_rows() -> None:
    with pytest.raises(
        ValueError,
        match="maximum_rows must be at least 1",
    ):
        parse_csv_bytes(
            b"First Name\nAlice\n",
            maximum_rows=0,
        )


def test_validate_row_with_schema_accepts_valid_row() -> None:
    result = validate_row_with_schema(
        {
            "first_name": " Alice ",
            "last_name": " Johnson ",
            "email": "alice@example.com",
            "year_group": "7",
        },
        schema=StudentImportRow,
    )

    assert result.is_valid is True
    assert result.errors == []
    assert result.warnings == []
    assert result.normalised_data == {
        "first_name": "Alice",
        "last_name": "Johnson",
        "email": "alice@example.com",
        "year_group": 7,
    }


def test_validate_row_with_schema_rejects_invalid_row() -> None:
    result = validate_row_with_schema(
        {
            "first_name": "",
            "last_name": "Johnson",
            "email": "not-an-email",
            "year_group": "20",
        },
        schema=StudentImportRow,
    )

    assert result.is_valid is False
    assert result.normalised_data is None
    assert result.errors
    assert result.warnings == []

    error_locations = {tuple(error["loc"]) for error in result.errors or []}

    assert ("first_name",) in error_locations
    assert ("email",) in error_locations
    assert ("year_group",) in error_locations


def test_validate_row_with_schema_rejects_unexpected_fields() -> None:
    result = validate_row_with_schema(
        {
            "first_name": "Alice",
            "last_name": "Johnson",
            "email": "alice@example.com",
            "year_group": 7,
            "unknown_column": "unexpected",
        },
        schema=StudentImportRow,
    )

    assert result.is_valid is False

    error_locations = {tuple(error["loc"]) for error in result.errors or []}

    assert ("unknown_column",) in error_locations


def test_import_batch_routes_are_registered() -> None:
    route_methods = {
        (
            route.path,
            tuple(
                sorted(
                    route.methods or set(),
                )
            ),
        )
        for route in api_router.routes
        if "import-batches" in route.path
    }

    expected_routes = {
        ("/import-batches", ("GET",)),
        ("/import-batches", ("POST",)),
        ("/import-batches/count", ("GET",)),
        ("/import-batches/{batch_id}", ("GET",)),
        ("/import-batches/{batch_id}/progress", ("GET",)),
        ("/import-batches/{batch_id}/upload", ("POST",)),
        ("/import-batches/{batch_id}/process", ("POST",)),
        ("/import-batches/{batch_id}/retry", ("POST",)),
        ("/import-batches/{batch_id}/rows", ("GET",)),
        ("/import-batches/{batch_id}/rows/count", ("GET",)),
        (
            "/import-batches/{batch_id}/rows/{row_id}",
            ("GET",),
        ),
        ("/import-batches/{batch_id}/cancel", ("POST",)),
        ("/import-batches/{batch_id}/archive", ("POST",)),
        ("/import-batches/{batch_id}/restore", ("POST",)),
    }

    missing_routes = expected_routes - route_methods

    assert not missing_routes, (
        "The following import-batch routes are not registered: "
        f"{sorted(missing_routes)}"
    )
