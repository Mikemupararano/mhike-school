from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

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

    entity_id:
        Identifier of the created or updated database record, when available.

    action:
        Whether the row created, updated, or skipped an entity.

    message:
        Optional human-readable processing detail for audit history.
    """

    action: RowProcessingAction
    entity_id: int | None = None
    message: str | None = None


RowValidator = Callable[
    [dict[str, Any]],
    RowValidationResult | Awaitable[RowValidationResult],
]

RowProcessor = Callable[
    [AsyncSession, dict[str, Any], int],
    Awaitable[RowProcessingResult],
]


@dataclass(slots=True, frozen=True)
class ImportHandler:
    """
    Generic handler for one import type.

    Each import type supplies:

        • validator
        • processor

    allowing the framework to remain completely generic.
    """

    validator: RowValidator
    processor: RowProcessor


_registry: dict[str, ImportHandler] = {}


def register_import_handler(
    import_type: str,
    *,
    validator: RowValidator,
    processor: RowProcessor,
) -> None:
    """
    Register an import handler.

    Raises:
        ValueError:
            If the import type is blank or a handler already exists.
    """

    key = import_type.strip().lower()

    if not key:
        raise ValueError("Import type cannot be blank.")

    if key in _registry:
        raise ValueError(f"Import handler '{key}' is already registered.")

    _registry[key] = ImportHandler(
        validator=validator,
        processor=processor,
    )


def get_import_handler(import_type: str) -> ImportHandler:
    """
    Return the registered handler.

    Raises:
        KeyError:
            If the import type is unknown.
    """

    key = import_type.strip().lower()

    try:
        return _registry[key]
    except KeyError as exc:
        raise KeyError(f"No import handler registered for '{import_type}'.") from exc


def registered_import_types() -> list[str]:
    """Return all registered import types."""

    return sorted(_registry.keys())


def is_registered(import_type: str) -> bool:
    """Return True if an import handler exists."""

    return import_type.strip().lower() in _registry


def clear_registry() -> None:
    """
    Clear all registered handlers.

    Intended for tests only. Production code should never call this.
    """

    _registry.clear()
