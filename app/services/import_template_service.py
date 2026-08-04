from __future__ import annotations

import csv
import io
import types
from collections.abc import Mapping, Sequence
from datetime import date, datetime
from enum import Enum
from typing import Any, Union, get_args, get_origin

from pydantic_core import PydanticUndefined

from app.imports.registry import (
    ImportHandler,
    get_import_handler,
    registered_import_handlers,
)
from app.schemas.import_template import (
    ImportFieldMetadataRead,
    ImportTemplateCsvPreviewRead,
    ImportTemplateListRead,
    ImportTemplateMetadataRead,
    ImportTemplateSummaryRead,
    ImportValidationRuleRead,
)

IMPORT_TEMPLATE_METADATA_PATH = "/api/v1/import-batches/templates"
IMPORT_TEMPLATE_DOWNLOAD_PATH = (
    "/api/v1/import-batches/templates/{import_type}/download"
)

JSON_SCHEMA_RULES: tuple[tuple[str, str, str], ...] = (
    (
        "minLength",
        "min_length",
        "Minimum number of characters.",
    ),
    (
        "maxLength",
        "max_length",
        "Maximum number of characters.",
    ),
    (
        "minimum",
        "minimum",
        "Minimum accepted value.",
    ),
    (
        "maximum",
        "maximum",
        "Maximum accepted value.",
    ),
    (
        "exclusiveMinimum",
        "exclusive_minimum",
        "Value must be greater than this limit.",
    ),
    (
        "exclusiveMaximum",
        "exclusive_maximum",
        "Value must be less than this limit.",
    ),
    (
        "multipleOf",
        "multiple_of",
        "Value must be a multiple of this number.",
    ),
    (
        "minItems",
        "min_items",
        "Minimum number of items.",
    ),
    (
        "maxItems",
        "max_items",
        "Maximum number of items.",
    ),
    (
        "pattern",
        "pattern",
        "Value must match this pattern.",
    ),
    (
        "format",
        "format",
        "Expected semantic value format.",
    ),
)


class ImportTemplateServiceError(Exception):
    """Base exception for import-template service failures."""


class ImportTemplateConfigurationError(ImportTemplateServiceError):
    """Raised when registered template metadata cannot be generated safely."""


def _humanise_field_name(value: str) -> str:
    """Convert a machine field name into a frontend-friendly label."""

    return value.replace("_", " ").strip().title()


def _field_column_name(
    field_name: str,
    *,
    alias: str | None,
) -> str:
    """
    Return the authoritative CSV column name.

    Pydantic aliases are preferred when explicitly configured. Otherwise, the
    model field name is used.
    """

    return alias or field_name


def _unwrap_optional_annotation(annotation: Any) -> Any:
    """
    Remove ``None`` from a simple optional union.

    Complex unions containing more than one non-null type are returned
    unchanged because they cannot be represented as one definitive field type.
    """

    origin = get_origin(annotation)

    if origin not in {
        Union,
        types.UnionType,
    }:
        return annotation

    non_none_arguments = [
        argument for argument in get_args(annotation) if argument is not type(None)
    ]

    if len(non_none_arguments) == 1:
        return non_none_arguments[0]

    return annotation


def _annotation_allows_none(annotation: Any) -> bool:
    """Return whether a type annotation explicitly allows ``None``."""

    if annotation is None or annotation is type(None):
        return True

    origin = get_origin(annotation)

    if origin in {
        Union,
        types.UnionType,
    }:
        return type(None) in get_args(annotation)

    return False


def _annotation_is_enum(annotation: Any) -> bool:
    """Return whether an annotation resolves to an Enum subclass."""

    unwrapped = _unwrap_optional_annotation(annotation)

    return isinstance(unwrapped, type) and issubclass(unwrapped, Enum)


def _readable_python_type(annotation: Any) -> str:
    """Return a stable human-readable representation of an annotation."""

    if annotation is None or annotation is Any:
        return "Any"

    if annotation is type(None):
        return "None"

    origin = get_origin(annotation)

    if origin in {
        Union,
        types.UnionType,
    }:
        return " | ".join(
            _readable_python_type(argument) for argument in get_args(annotation)
        )

    if origin is not None:
        arguments = get_args(annotation)

        origin_name = getattr(
            origin,
            "__name__",
            str(origin).replace("typing.", ""),
        )

        if not arguments:
            return origin_name

        rendered_arguments = ", ".join(
            _readable_python_type(argument) for argument in arguments
        )

        return f"{origin_name}[{rendered_arguments}]"

    return getattr(
        annotation,
        "__name__",
        str(annotation).replace("typing.", ""),
    )


def _resolve_json_schema_node(
    node: Mapping[str, Any],
    *,
    root_schema: Mapping[str, Any],
) -> dict[str, Any]:
    """
    Resolve a local JSON Schema reference.

    Pydantic commonly places enum and nested-model definitions under
    ``$defs`` and references them through ``$ref``.
    """

    reference = node.get("$ref")

    if not isinstance(reference, str):
        return dict(node)

    prefix = "#/$defs/"

    if not reference.startswith(prefix):
        return dict(node)

    definition_name = reference[len(prefix) :]
    definitions = root_schema.get("$defs", {})

    if not isinstance(definitions, Mapping):
        return dict(node)

    definition = definitions.get(definition_name)

    if not isinstance(definition, Mapping):
        return dict(node)

    merged = dict(definition)

    for key, value in node.items():
        if key != "$ref":
            merged[key] = value

    return merged


def _flatten_json_schema_node(
    node: Mapping[str, Any],
    *,
    root_schema: Mapping[str, Any],
) -> dict[str, Any]:
    """
    Flatten nullable and referenced JSON Schema nodes.

    Pydantic commonly represents optional fields with ``anyOf`` containing
    the value schema and a null schema. This helper retains the non-null
    field constraints while nullability is recorded separately.
    """

    resolved = _resolve_json_schema_node(
        node,
        root_schema=root_schema,
    )

    alternatives = resolved.get("anyOf")

    if not isinstance(alternatives, list):
        alternatives = resolved.get("oneOf")

    if not isinstance(alternatives, list):
        return resolved

    non_null_options: list[Mapping[str, Any]] = []

    for alternative in alternatives:
        if not isinstance(alternative, Mapping):
            continue

        flattened = _resolve_json_schema_node(
            alternative,
            root_schema=root_schema,
        )

        if flattened.get("type") == "null":
            continue

        non_null_options.append(flattened)

    if len(non_null_options) != 1:
        return resolved

    merged = dict(non_null_options[0])

    for key, value in resolved.items():
        if key not in {
            "anyOf",
            "oneOf",
        }:
            merged[key] = value

    return merged


def _json_schema_allows_null(
    node: Mapping[str, Any],
    *,
    root_schema: Mapping[str, Any],
) -> bool:
    """Return whether a JSON Schema field node accepts null."""

    resolved = _resolve_json_schema_node(
        node,
        root_schema=root_schema,
    )

    schema_type = resolved.get("type")

    if schema_type == "null":
        return True

    if isinstance(schema_type, list) and "null" in schema_type:
        return True

    for keyword in (
        "anyOf",
        "oneOf",
    ):
        alternatives = resolved.get(keyword)

        if not isinstance(alternatives, list):
            continue

        for alternative in alternatives:
            if not isinstance(alternative, Mapping):
                continue

            flattened = _resolve_json_schema_node(
                alternative,
                root_schema=root_schema,
            )

            if flattened.get("type") == "null":
                return True

    return False


def _normalise_data_type(
    annotation: Any,
    *,
    json_schema_node: Mapping[str, Any],
) -> str:
    """
    Convert Pydantic and JSON Schema types into frontend-friendly names.

    Enum detection takes precedence over the underlying JSON primitive type.
    For example, a string-backed Enum is reported as ``enum`` rather than
    ``string`` so frontend clients can render accepted-value controls.
    """

    unwrapped = _unwrap_optional_annotation(annotation)

    if _annotation_is_enum(annotation):
        return "enum"

    schema_format = json_schema_node.get("format")

    if schema_format == "email":
        return "email"

    if schema_format == "date":
        return "date"

    if schema_format == "date-time":
        return "datetime"

    if schema_format in {
        "uuid",
        "uri",
        "url",
    }:
        return str(schema_format)

    schema_type = json_schema_node.get("type")

    if isinstance(schema_type, list):
        non_null_types = [value for value in schema_type if value != "null"]

        if len(non_null_types) == 1:
            schema_type = non_null_types[0]

    if unwrapped is str:
        return "string"

    if unwrapped is bool:
        return "boolean"

    if unwrapped is int:
        return "integer"

    if unwrapped is float:
        return "number"

    if unwrapped is datetime:
        return "datetime"

    if unwrapped is date:
        return "date"

    origin = get_origin(unwrapped)

    if origin in {
        list,
        tuple,
        set,
        frozenset,
        Sequence,
    }:
        return "array"

    if origin in {
        dict,
        Mapping,
    }:
        return "object"

    if isinstance(schema_type, str):
        schema_type_aliases = {
            "integer": "integer",
            "number": "number",
            "boolean": "boolean",
            "array": "array",
            "object": "object",
            "string": "string",
        }

        if schema_type in schema_type_aliases:
            return schema_type_aliases[schema_type]

    return "string"


def _serialise_value(value: Any) -> Any:
    """Convert metadata values into JSON-safe representations."""

    if value is PydanticUndefined:
        return None

    if isinstance(value, Enum):
        return _serialise_value(value.value)

    if isinstance(value, datetime):
        return value.isoformat()

    if isinstance(value, date):
        return value.isoformat()

    if isinstance(value, Mapping):
        return {str(key): _serialise_value(item) for key, item in value.items()}

    if isinstance(
        value,
        (
            tuple,
            list,
            set,
            frozenset,
        ),
    ):
        return [_serialise_value(item) for item in value]

    if (
        isinstance(
            value,
            (
                str,
                int,
                float,
                bool,
            ),
        )
        or value is None
    ):
        return value

    return str(value)


def _accepted_values(
    json_schema_node: Mapping[str, Any],
) -> list[Any]:
    """Extract explicit enum or constant values from JSON Schema."""

    enum_values = json_schema_node.get("enum")

    if isinstance(enum_values, list):
        return [_serialise_value(value) for value in enum_values]

    if "const" in json_schema_node:
        return [
            _serialise_value(json_schema_node["const"]),
        ]

    return []


def _validation_rules(
    json_schema_node: Mapping[str, Any],
) -> list[ImportValidationRuleRead]:
    """Build serialisable validation rules from JSON Schema constraints."""

    rules: list[ImportValidationRuleRead] = []

    for source_name, public_name, description in JSON_SCHEMA_RULES:
        if source_name not in json_schema_node:
            continue

        rules.append(
            ImportValidationRuleRead(
                name=public_name,
                value=_serialise_value(
                    json_schema_node[source_name],
                ),
                description=description,
            ),
        )

    accepted_values = _accepted_values(json_schema_node)

    if accepted_values:
        rules.append(
            ImportValidationRuleRead(
                name="accepted_values",
                value=accepted_values,
                description=("Value must be one of the accepted values."),
            ),
        )

    return rules


def _field_example(
    *,
    field_name: str,
    column_name: str,
    field_info: Any,
    json_schema_node: Mapping[str, Any],
    handler_sample_row: Mapping[str, Any],
) -> Any:
    """
    Resolve the best available sample value for one field.

    Priority:

    1. Explicit handler sample using the CSV column name.
    2. Explicit handler sample using the model field name.
    3. Pydantic JSON Schema examples.
    4. Pydantic JSON Schema example.
    5. Pydantic JSON Schema default.
    6. Pydantic model default.
    7. First accepted enum value.
    8. Empty string.
    """

    if column_name in handler_sample_row:
        return _serialise_value(
            handler_sample_row[column_name],
        )

    if field_name in handler_sample_row:
        return _serialise_value(
            handler_sample_row[field_name],
        )

    examples = json_schema_node.get("examples")

    if isinstance(examples, list) and examples:
        return _serialise_value(examples[0])

    if "example" in json_schema_node:
        return _serialise_value(
            json_schema_node["example"],
        )

    if "default" in json_schema_node:
        return _serialise_value(
            json_schema_node["default"],
        )

    if not field_info.is_required() and field_info.default is not PydanticUndefined:
        return _serialise_value(field_info.default)

    accepted_values = _accepted_values(json_schema_node)

    if accepted_values:
        return accepted_values[0]

    return ""


def _field_default(
    *,
    field_info: Any,
    json_schema_node: Mapping[str, Any],
) -> Any:
    """Return a serialisable field default when one is defined."""

    if "default" in json_schema_node:
        return _serialise_value(
            json_schema_node["default"],
        )

    if field_info.default is PydanticUndefined:
        return None

    return _serialise_value(field_info.default)


def _field_description(
    *,
    field_info: Any,
    json_schema_node: Mapping[str, Any],
) -> str | None:
    """Return field guidance from Pydantic metadata."""

    description = json_schema_node.get("description")

    if isinstance(description, str):
        cleaned = description.strip()

        if cleaned:
            return cleaned

    field_description = field_info.description

    if isinstance(field_description, str):
        cleaned = field_description.strip()

        if cleaned:
            return cleaned

    return None


def _build_field_metadata(
    *,
    handler: ImportHandler,
    field_name: str,
    field_info: Any,
    root_schema: Mapping[str, Any],
    property_schema: Mapping[str, Any],
) -> ImportFieldMetadataRead:
    """Build public metadata for one registered schema field."""

    flattened_schema = _flatten_json_schema_node(
        property_schema,
        root_schema=root_schema,
    )

    alias = field_info.alias if isinstance(field_info.alias, str) else None

    column_name = _field_column_name(
        field_name,
        alias=alias,
    )

    required = field_info.is_required()

    nullable = _annotation_allows_none(
        field_info.annotation
    ) or _json_schema_allows_null(
        property_schema,
        root_schema=root_schema,
    )

    accepted_values = _accepted_values(flattened_schema)

    example = _field_example(
        field_name=field_name,
        column_name=column_name,
        field_info=field_info,
        json_schema_node=flattened_schema,
        handler_sample_row=handler.sample_row,
    )

    return ImportFieldMetadataRead(
        name=field_name,
        column_name=column_name,
        label=_humanise_field_name(column_name),
        required=required,
        nullable=nullable,
        data_type=_normalise_data_type(
            field_info.annotation,
            json_schema_node=flattened_schema,
        ),
        python_type=_readable_python_type(
            field_info.annotation,
        ),
        description=_field_description(
            field_info=field_info,
            json_schema_node=flattened_schema,
        ),
        default=_field_default(
            field_info=field_info,
            json_schema_node=flattened_schema,
        ),
        example=example,
        accepted_values=accepted_values,
        validation_rules=_validation_rules(
            flattened_schema,
        ),
    )


def build_import_template_metadata(
    handler: ImportHandler,
) -> ImportTemplateMetadataRead:
    """
    Build complete template metadata for one registered import handler.

    Field order follows the registered Pydantic schema so metadata responses,
    CSV headers and generated sample rows remain aligned with backend
    validation.
    """

    root_schema = handler.schema.model_json_schema()
    properties = root_schema.get("properties", {})

    if not isinstance(properties, Mapping):
        raise ImportTemplateConfigurationError(
            f"{handler.schema.__name__} does not expose usable properties.",
        )

    fields: list[ImportFieldMetadataRead] = []

    for field_name, field_info in handler.schema.model_fields.items():
        property_schema = properties.get(
            field_name,
            {},
        )

        if not isinstance(property_schema, Mapping):
            property_schema = {}

        fields.append(
            _build_field_metadata(
                handler=handler,
                field_name=field_name,
                field_info=field_info,
                root_schema=root_schema,
                property_schema=property_schema,
            ),
        )

    required_fields = [field for field in fields if field.required]

    optional_fields = [field for field in fields if not field.required]

    csv_headers = [field.column_name for field in fields]

    sample_row = {field.column_name: field.example for field in fields}

    return ImportTemplateMetadataRead(
        import_type=handler.import_type,
        display_name=handler.display_name,
        description=handler.description,
        schema_name=handler.schema.__name__,
        fields=fields,
        required_fields=required_fields,
        optional_fields=optional_fields,
        csv_headers=csv_headers,
        sample_row=sample_row,
        metadata_url=(f"{IMPORT_TEMPLATE_METADATA_PATH}/{handler.import_type}"),
        download_url=IMPORT_TEMPLATE_DOWNLOAD_PATH.format(
            import_type=handler.import_type,
        ),
    )


def get_import_template_metadata(
    import_type: str,
) -> ImportTemplateMetadataRead:
    """Return generated metadata for one registered import type."""

    handler = get_import_handler(import_type)

    return build_import_template_metadata(handler)


def list_import_template_metadata() -> list[ImportTemplateMetadataRead]:
    """Return complete metadata for every registered import type."""

    return [
        build_import_template_metadata(handler)
        for handler in registered_import_handlers()
    ]


def list_import_template_summaries() -> ImportTemplateListRead:
    """Return compact discovery metadata for all registered templates."""

    items: list[ImportTemplateSummaryRead] = []

    for metadata in list_import_template_metadata():
        items.append(
            ImportTemplateSummaryRead(
                import_type=metadata.import_type,
                display_name=metadata.display_name,
                description=metadata.description,
                required_field_count=len(
                    metadata.required_fields,
                ),
                optional_field_count=len(
                    metadata.optional_fields,
                ),
                total_field_count=len(
                    metadata.fields,
                ),
                metadata_url=metadata.metadata_url,
                download_url=metadata.download_url,
            ),
        )

    return ImportTemplateListRead(
        items=items,
        total=len(items),
    )


def _csv_cell(value: Any) -> str:
    """Convert a generated sample value into a CSV-safe string."""

    if value is None:
        return ""

    if isinstance(value, bool):
        return "true" if value else "false"

    if isinstance(value, Enum):
        return _csv_cell(value.value)

    if isinstance(value, datetime):
        return value.isoformat()

    if isinstance(value, date):
        return value.isoformat()

    if isinstance(value, Mapping):
        return str(
            {str(key): _serialise_value(item) for key, item in value.items()},
        )

    if isinstance(
        value,
        (
            list,
            tuple,
            set,
            frozenset,
        ),
    ):
        return ", ".join(_csv_cell(item) for item in value)

    return str(value)


def generate_import_template_csv(
    import_type: str,
    *,
    include_sample_row: bool = True,
) -> str:
    """
    Generate CSV template text for one registered import type.

    The header order always follows the authoritative Pydantic schema.
    """

    metadata = get_import_template_metadata(import_type)

    stream = io.StringIO(
        newline="",
    )

    writer = csv.DictWriter(
        stream,
        fieldnames=metadata.csv_headers,
        extrasaction="ignore",
        lineterminator="\r\n",
    )

    writer.writeheader()

    if include_sample_row:
        writer.writerow(
            {
                header: _csv_cell(
                    metadata.sample_row.get(header),
                )
                for header in metadata.csv_headers
            },
        )

    return stream.getvalue()


def build_import_template_csv_preview(
    import_type: str,
    *,
    include_sample_row: bool = True,
) -> ImportTemplateCsvPreviewRead:
    """Build a serialisable preview of a generated CSV template."""

    metadata = get_import_template_metadata(import_type)

    return ImportTemplateCsvPreviewRead(
        import_type=metadata.import_type,
        filename=f"{metadata.import_type}_import_template.csv",
        content_type="text/csv",
        csv_content=generate_import_template_csv(
            metadata.import_type,
            include_sample_row=include_sample_row,
        ),
    )
