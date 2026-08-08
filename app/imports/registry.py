from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType
from typing import Any

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.import_service import RowValidationResult


class RowProcessingAction(StrEnum):
    """
    Outcome of processing one validated import row.
    """

    CREATED = "created"
    UPDATED = "updated"
    SKIPPED = "skipped"


@dataclass(slots=True, frozen=True)
class RowProcessingResult:
    """
    Result returned by an import row processor.

    Attributes:
        action:
            Whether the row created, updated or skipped an entity.

        entity_id:
            Identifier of the created, updated or matched database record,
            when available.

        message:
            Optional human-readable processing detail retained in import
            history and audit output.
    """

    action: RowProcessingAction
    entity_id: int | None = None
    message: str | None = None


# ---------------------------------------------------------------------------
# Import handler callable contracts
# ---------------------------------------------------------------------------

ImportOptions = Mapping[str, Any]

RowValidator = Callable[
    [dict[str, Any]],
    RowValidationResult | Awaitable[RowValidationResult],
]

RowProcessor = Callable[
    [
        AsyncSession,
        dict[str, Any],
        int,
        ImportOptions,
    ],
    Awaitable[RowProcessingResult],
]


@dataclass(slots=True, frozen=True)
class ImportHandler:
    """
    Registered capabilities and metadata for one import type.

    The Pydantic schema is the authoritative source for:

        • field names
        • field order
        • required and optional status
        • data types
        • default values
        • field descriptions
        • examples
        • validation constraints

    Presentation metadata that cannot be inferred reliably from the schema is
    stored directly on the handler.

    Attributes:
        import_type:
            Canonical lower-case import type used by the API and registry.

        validator:
            Callable responsible for validating and normalising one source row.

        processor:
            Async callable responsible for applying one validated row to the
            database.

            Processors receive:
                • database session
                • validated row data
                • authenticated school ID
                • batch-level import options

            Individual processors may use only the options relevant to their
            own create/update/skip behaviour.

        schema:
            Pydantic model describing the accepted import-row structure.

        display_name:
            Human-readable plural label displayed by clients.

        description:
            Human-readable explanation of what the import type creates or
            updates.

        sample_row:
            Optional explicit sample values used when generating template
            previews and downloadable CSV files.
    """

    import_type: str
    validator: RowValidator
    processor: RowProcessor
    schema: type[BaseModel]
    display_name: str
    description: str
    sample_row: Mapping[str, Any]


_registry: dict[str, ImportHandler] = {}


def _normalise_import_type(
    import_type: str,
) -> str:
    """
    Convert an import type into its canonical registry key.

    Raises:
        TypeError:
            If the supplied import type is not a string.

        ValueError:
            If the normalised import type is blank.
    """

    if not isinstance(
        import_type,
        str,
    ):
        raise TypeError(
            "Import type must be a string.",
        )

    key = (
        import_type
        .strip()
        .lower()
    )

    if not key:
        raise ValueError(
            "Import type cannot be blank.",
        )

    return key


def _normalise_required_text(
    value: str,
    *,
    field_name: str,
) -> str:
    """
    Strip and validate required human-readable registration metadata.
    """

    if not isinstance(
        value,
        str,
    ):
        raise TypeError(
            f"{field_name} must be a string.",
        )

    cleaned = value.strip()

    if not cleaned:
        raise ValueError(
            f"{field_name} cannot be blank.",
        )

    return cleaned


def _validate_schema(
    schema: type[BaseModel],
) -> type[BaseModel]:
    """
    Validate that a registered schema is a Pydantic BaseModel subclass.
    """

    if (
        not isinstance(
            schema,
            type,
        )
        or not issubclass(
            schema,
            BaseModel,
        )
    ):
        raise TypeError(
            "Import handler schema must be a Pydantic BaseModel subclass.",
        )

    return schema


def _normalise_sample_row(
    sample_row: Mapping[str, Any] | None,
    *,
    schema: type[BaseModel],
) -> Mapping[str, Any]:
    """
    Validate and freeze an import handler's explicit sample row.

    Sample rows may omit fields because the template service can supplement
    them from Pydantic field examples, defaults or empty values.

    Every explicitly supplied key must match either a Pydantic field name or
    that field's validation alias.
    """

    if sample_row is None:
        return MappingProxyType({})

    if not isinstance(
        sample_row,
        Mapping,
    ):
        raise TypeError(
            "sample_row must be a mapping or None.",
        )

    model_fields = schema.model_fields

    accepted_keys: set[str] = set(
        model_fields,
    )

    for field_name, field_info in model_fields.items():
        alias = field_info.alias

        if (
            isinstance(
                alias,
                str,
            )
            and alias
        ):
            accepted_keys.add(
                alias,
            )

        validation_alias = (
            field_info.validation_alias
        )

        if (
            isinstance(
                validation_alias,
                str,
            )
            and validation_alias
        ):
            accepted_keys.add(
                validation_alias,
            )

        accepted_keys.add(
            field_name,
        )

    invalid_keys = sorted(
        str(key)
        for key in sample_row
        if (
            not isinstance(
                key,
                str,
            )
            or key not in accepted_keys
        )
    )

    if invalid_keys:
        raise ValueError(
            "Sample row contains fields that are not defined by "
            f"{schema.__name__}: {', '.join(invalid_keys)}.",
        )

    normalised: dict[str, Any] = {}

    for raw_key, value in sample_row.items():
        if not isinstance(
            raw_key,
            str,
        ):
            raise TypeError(
                "Sample-row field names must be strings.",
            )

        key = raw_key.strip()

        if not key:
            raise ValueError(
                "Sample-row field names cannot be blank.",
            )

        normalised[key] = value

    return MappingProxyType(
        normalised,
    )


def register_import_handler(
    import_type: str,
    *,
    validator: RowValidator,
    processor: RowProcessor,
    schema: type[BaseModel],
    display_name: str,
    description: str,
    sample_row: Mapping[str, Any] | None = None,
) -> None:
    """
    Register all capabilities for one import type.

    The registry is the single source of truth for supported import types.
    Template services and API endpoints should discover metadata from the
    registered handler rather than maintaining separate field definitions.

    Raises:
        TypeError:
            If a supplied callable, schema or metadata value has an invalid
            type.

        ValueError:
            If required metadata is blank, the sample row references unknown
            fields or a handler is already registered for the import type.
    """

    key = _normalise_import_type(
        import_type,
    )

    if key in _registry:
        raise ValueError(
            f"Import handler '{key}' is already registered.",
        )

    if not callable(
        validator,
    ):
        raise TypeError(
            "Import handler validator must be callable.",
        )

    if not callable(
        processor,
    ):
        raise TypeError(
            "Import handler processor must be callable.",
        )

    validated_schema = _validate_schema(
        schema,
    )

    cleaned_display_name = (
        _normalise_required_text(
            display_name,
            field_name="Display name",
        )
    )

    cleaned_description = (
        _normalise_required_text(
            description,
            field_name="Description",
        )
    )

    validated_sample_row = (
        _normalise_sample_row(
            sample_row,
            schema=validated_schema,
        )
    )

    _registry[key] = ImportHandler(
        import_type=key,
        validator=validator,
        processor=processor,
        schema=validated_schema,
        display_name=cleaned_display_name,
        description=cleaned_description,
        sample_row=validated_sample_row,
    )


def get_import_handler(
    import_type: str,
) -> ImportHandler:
    """
    Return the registered handler for an import type.

    Raises:
        TypeError:
            If the supplied import type is not a string.

        ValueError:
            If the supplied import type is blank.

        KeyError:
            If no handler has been registered for the import type.
    """

    key = _normalise_import_type(
        import_type,
    )

    try:
        return _registry[key]
    except KeyError as exc:
        raise KeyError(
            f"No import handler registered for '{key}'.",
        ) from exc


def registered_import_types() -> list[str]:
    """
    Return all registered import types in deterministic order.
    """

    return sorted(
        _registry,
    )


def registered_import_handlers() -> list[ImportHandler]:
    """
    Return all registered handlers ordered by canonical import type.

    This is intended for API discovery and template metadata generation.
    A new list is returned so callers cannot mutate the registry itself.
    """

    return [
        _registry[import_type]
        for import_type
        in registered_import_types()
    ]


def is_registered(
    import_type: str,
) -> bool:
    """
    Return whether an import handler exists.

    Blank or non-string values are treated as unregistered rather than raising
    an exception, making this helper safe for request-level capability checks.
    """

    if not isinstance(
        import_type,
        str,
    ):
        return False

    key = (
        import_type
        .strip()
        .lower()
    )

    if not key:
        return False

    return key in _registry


def clear_registry() -> None:
    """
    Clear all registered handlers.

    This function is intended only for isolated tests. Production application
    code must not clear the registry after handlers have been registered.
    """

    _registry.clear()