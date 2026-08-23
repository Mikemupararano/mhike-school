from __future__ import annotations

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.marking_palette import (
    MarkingPalette,
    MarkingPaletteTool,
    MarkingPaletteToolType,
)


class MarkingPaletteRepository:
    """
    Repository for school-scoped examiner marking palettes and palette tools.

    Marking palettes are deliberately exam-board neutral.

    A palette always belongs to one school. ``subject_id`` may optionally
    restrict the palette to one academic subject.

    The repository never commits or rolls back transactions. Transaction
    ownership remains with the calling service or workflow.
    """

    def __init__(
        self,
        db: AsyncSession,
    ) -> None:
        self.db = db

    # ------------------------------------------------------------------
    # Validation helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _validate_positive_integer(
        value: int,
        field_name: str,
    ) -> None:
        """
        Require a positive integer identifier.
        """

        if not isinstance(value, int) or isinstance(value, bool) or value < 1:
            raise ValueError(
                f"{field_name} must be a positive integer.",
            )

    @staticmethod
    def _normalise_name(
        value: str,
        *,
        field_name: str,
        max_length: int,
    ) -> str:
        """
        Return validated trimmed required text.
        """

        if not isinstance(value, str):
            raise ValueError(
                f"{field_name} must be a string.",
            )

        cleaned = value.strip()

        if not cleaned:
            raise ValueError(
                f"{field_name} cannot be blank.",
            )

        if len(cleaned) > max_length:
            raise ValueError(
                f"{field_name} cannot exceed {max_length} characters.",
            )

        return cleaned

    @staticmethod
    def _normalise_optional_text(
        value: str | None,
        *,
        field_name: str,
        max_length: int | None = None,
    ) -> str | None:
        """
        Return trimmed optional text.

        Blank strings are normalised to None.
        """

        if value is None:
            return None

        if not isinstance(value, str):
            raise ValueError(
                f"{field_name} must be a string or None.",
            )

        cleaned = value.strip()

        if not cleaned:
            return None

        if max_length is not None and len(cleaned) > max_length:
            raise ValueError(
                f"{field_name} cannot exceed {max_length} characters.",
            )

        return cleaned

    @staticmethod
    def _normalise_tool_type(
        value: MarkingPaletteToolType | str,
    ) -> MarkingPaletteToolType:
        """
        Return a valid marking palette tool type.
        """

        if isinstance(
            value,
            MarkingPaletteToolType,
        ):
            return value

        if not isinstance(value, str):
            raise ValueError(
                "tool_type must be a MarkingPaletteToolType or string.",
            )

        try:
            return MarkingPaletteToolType(
                value.strip(),
            )
        except ValueError as exc:
            raise ValueError(
                f"Invalid marking palette tool type: {value!r}.",
            ) from exc

    # ------------------------------------------------------------------
    # Relationship loading
    # ------------------------------------------------------------------

    @staticmethod
    def _apply_palette_relationship_loading(
        statement,
        *,
        include_relationships: bool,
    ):
        """
        Apply standard eager loading for a marking palette.
        """

        if not include_relationships:
            return statement

        return statement.options(
            selectinload(
                MarkingPalette.school,
            ),
            selectinload(
                MarkingPalette.subject,
            ),
            selectinload(
                MarkingPalette.tools,
            ),
        )

    # ------------------------------------------------------------------
    # Palette lookup
    # ------------------------------------------------------------------

    async def get_palette_by_id(
        self,
        palette_id: int,
        *,
        include_relationships: bool = True,
    ) -> MarkingPalette | None:
        """
        Return a palette by global identifier.
        """

        self._validate_positive_integer(
            palette_id,
            "palette_id",
        )

        statement = select(
            MarkingPalette,
        ).where(
            MarkingPalette.id == palette_id,
        )

        statement = self._apply_palette_relationship_loading(
            statement,
            include_relationships=include_relationships,
        )

        if include_relationships:
            statement = statement.execution_options(
                populate_existing=True,
            )

        result = await self.db.execute(
            statement,
        )

        return result.scalar_one_or_none()

    async def get_palette_by_id_and_school(
        self,
        palette_id: int,
        school_id: int,
        *,
        include_relationships: bool = True,
    ) -> MarkingPalette | None:
        """
        Return a palette only when it belongs to the supplied school.
        """

        self._validate_positive_integer(
            palette_id,
            "palette_id",
        )
        self._validate_positive_integer(
            school_id,
            "school_id",
        )

        statement = select(
            MarkingPalette,
        ).where(
            MarkingPalette.id == palette_id,
            MarkingPalette.school_id == school_id,
        )

        statement = self._apply_palette_relationship_loading(
            statement,
            include_relationships=include_relationships,
        )

        if include_relationships:
            statement = statement.execution_options(
                populate_existing=True,
            )

        result = await self.db.execute(
            statement,
        )

        return result.scalar_one_or_none()

    async def get_palette_by_school_and_name(
        self,
        school_id: int,
        name: str,
        *,
        include_relationships: bool = True,
    ) -> MarkingPalette | None:
        """
        Return one palette by school and exact normalised name.
        """

        self._validate_positive_integer(
            school_id,
            "school_id",
        )

        normalised_name = self._normalise_name(
            name,
            field_name="name",
            max_length=150,
        )

        statement = select(
            MarkingPalette,
        ).where(
            MarkingPalette.school_id == school_id,
            MarkingPalette.name == normalised_name,
        )

        statement = self._apply_palette_relationship_loading(
            statement,
            include_relationships=include_relationships,
        )

        if include_relationships:
            statement = statement.execution_options(
                populate_existing=True,
            )

        result = await self.db.execute(
            statement,
        )

        return result.scalar_one_or_none()

    async def list_palettes_for_school(
        self,
        school_id: int,
        *,
        subject_id: int | None = None,
        active_only: bool = False,
        include_general: bool = True,
        include_relationships: bool = True,
    ) -> list[MarkingPalette]:
        """
        Return palettes available within one school.

        When ``subject_id`` is supplied and ``include_general`` is True,
        both the requested subject palettes and general school-wide palettes
        are returned.
        """

        self._validate_positive_integer(
            school_id,
            "school_id",
        )

        if subject_id is not None:
            self._validate_positive_integer(
                subject_id,
                "subject_id",
            )

        statement = select(
            MarkingPalette,
        ).where(
            MarkingPalette.school_id == school_id,
        )

        if subject_id is not None:
            if include_general:
                statement = statement.where(
                    or_(
                        MarkingPalette.subject_id == subject_id,
                        MarkingPalette.subject_id.is_(None),
                    )
                )
            else:
                statement = statement.where(
                    MarkingPalette.subject_id == subject_id,
                )

        if active_only:
            statement = statement.where(
                MarkingPalette.is_active.is_(True),
            )

        statement = statement.order_by(
            MarkingPalette.is_default.desc(),
            MarkingPalette.name.asc(),
            MarkingPalette.id.asc(),
        )

        statement = self._apply_palette_relationship_loading(
            statement,
            include_relationships=include_relationships,
        )

        result = await self.db.execute(
            statement,
        )

        return list(
            result.scalars().all(),
        )

    async def get_default_palette(
        self,
        school_id: int,
        *,
        subject_id: int | None = None,
        include_relationships: bool = True,
    ) -> MarkingPalette | None:
        """
        Return the active default palette for one school/context.

        Subject-specific defaults take precedence when ``subject_id`` is
        supplied. General school defaults are not silently substituted here;
        fallback policy belongs in the service layer.
        """

        self._validate_positive_integer(
            school_id,
            "school_id",
        )

        if subject_id is not None:
            self._validate_positive_integer(
                subject_id,
                "subject_id",
            )

        statement = select(
            MarkingPalette,
        ).where(
            MarkingPalette.school_id == school_id,
            MarkingPalette.subject_id == subject_id,
            MarkingPalette.is_default.is_(True),
            MarkingPalette.is_active.is_(True),
        ).order_by(
            MarkingPalette.id.asc(),
        )

        statement = self._apply_palette_relationship_loading(
            statement,
            include_relationships=include_relationships,
        )

        result = await self.db.execute(
            statement,
        )

        return result.scalars().first()

    # ------------------------------------------------------------------
    # Palette persistence
    # ------------------------------------------------------------------

    async def create_palette(
        self,
        palette: MarkingPalette,
    ) -> MarkingPalette:
        """
        Add a new marking palette to the current transaction.
        """

        self.db.add(
            palette,
        )

        await self.db.flush()

        return palette

    async def save_palette(
        self,
        palette: MarkingPalette,
    ) -> MarkingPalette:
        """
        Flush updates to an existing palette.
        """

        self.db.add(
            palette,
        )

        await self.db.flush()

        return palette

    async def delete_palette(
        self,
        palette: MarkingPalette,
    ) -> None:
        """
        Delete a palette from the current transaction.
        """

        await self.db.delete(
            palette,
        )

        await self.db.flush()

    # ------------------------------------------------------------------
    # Tool lookup
    # ------------------------------------------------------------------

    async def get_tool_by_id(
        self,
        tool_id: int,
    ) -> MarkingPaletteTool | None:
        """
        Return one marking palette tool by identifier.
        """

        self._validate_positive_integer(
            tool_id,
            "tool_id",
        )

        statement = select(
            MarkingPaletteTool,
        ).where(
            MarkingPaletteTool.id == tool_id,
        ).options(
            selectinload(
                MarkingPaletteTool.palette,
            )
        )

        result = await self.db.execute(
            statement,
        )

        return result.scalar_one_or_none()

    async def get_tool_by_palette_type_and_value(
        self,
        palette_id: int,
        tool_type: MarkingPaletteToolType | str,
        value: str,
    ) -> MarkingPaletteTool | None:
        """
        Return one tool using the palette/type/value identity.
        """

        self._validate_positive_integer(
            palette_id,
            "palette_id",
        )

        normalised_type = self._normalise_tool_type(
            tool_type,
        )

        normalised_value = self._normalise_name(
            value,
            field_name="value",
            max_length=100,
        )

        statement = select(
            MarkingPaletteTool,
        ).where(
            MarkingPaletteTool.palette_id == palette_id,
            MarkingPaletteTool.tool_type == normalised_type,
            MarkingPaletteTool.value == normalised_value,
        )

        result = await self.db.execute(
            statement,
        )

        return result.scalar_one_or_none()

    async def list_tools_for_palette(
        self,
        palette_id: int,
        *,
        active_only: bool = False,
    ) -> list[MarkingPaletteTool]:
        """
        Return tools for one palette in examiner display order.
        """

        self._validate_positive_integer(
            palette_id,
            "palette_id",
        )

        statement = select(
            MarkingPaletteTool,
        ).where(
            MarkingPaletteTool.palette_id == palette_id,
        )

        if active_only:
            statement = statement.where(
                MarkingPaletteTool.is_active.is_(True),
            )

        statement = statement.order_by(
            MarkingPaletteTool.sort_order.asc(),
            MarkingPaletteTool.id.asc(),
        )

        result = await self.db.execute(
            statement,
        )

        return list(
            result.scalars().all(),
        )

    # ------------------------------------------------------------------
    # Tool persistence
    # ------------------------------------------------------------------

    async def create_tool(
        self,
        tool: MarkingPaletteTool,
    ) -> MarkingPaletteTool:
        """
        Add a marking palette tool to the current transaction.
        """

        self.db.add(
            tool,
        )

        await self.db.flush()

        return tool

    async def save_tool(
        self,
        tool: MarkingPaletteTool,
    ) -> MarkingPaletteTool:
        """
        Flush updates to one marking palette tool.
        """

        self.db.add(
            tool,
        )

        await self.db.flush()

        return tool

    async def delete_tool(
        self,
        tool: MarkingPaletteTool,
    ) -> None:
        """
        Delete one palette tool from the current transaction.

        Historical annotations remain safe because their palette-tool foreign
        key uses ON DELETE SET NULL while their value and label snapshots are
        retained on the annotation itself.
        """

        await self.db.delete(
            tool,
        )

        await self.db.flush()
