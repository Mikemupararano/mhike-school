from __future__ import annotations

from typing import Any

from sqlalchemy import exists, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.class_group import ClassGroup


class ClassGroupRepository:
    """
    Repository for school-scoped class-group persistence and lookup.

    The repository does not commit or roll back transactions. Transaction
    ownership remains with the calling service, import processor, endpoint,
    or background task.
    """

    def __init__(
        self,
        db: AsyncSession,
    ) -> None:
        self.db = db

    @staticmethod
    def _normalise_name(
        name: str,
    ) -> str:
        """
        Return a validated, trimmed class-group name.
        """

        normalised_name = name.strip()

        if not normalised_name:
            raise ValueError(
                "Class name cannot be blank.",
            )

        if len(normalised_name) > 255:
            raise ValueError(
                "Class name cannot exceed 255 characters.",
            )

        return normalised_name

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

    @classmethod
    def _validate_teacher_id(
        cls,
        teacher_id: int | None,
    ) -> None:
        """Validate an optional teacher identifier."""

        if teacher_id is None:
            return

        cls._validate_positive_integer(
            teacher_id,
            "teacher_id",
        )

    @staticmethod
    def _with_relationships(
        statement: Any,
        *,
        include_school: bool = True,
    ) -> Any:
        """Apply the standard eager-loading options for class groups."""

        options = [
            selectinload(
                ClassGroup.teacher,
            ),
        ]

        if include_school:
            options.append(
                selectinload(
                    ClassGroup.school,
                ),
            )

        return statement.options(
            *options,
        )

    async def get_by_id(
        self,
        class_id: int,
        *,
        include_relationships: bool = True,
    ) -> ClassGroup | None:
        """
        Return a class group by its global identifier.

        Prefer ``get_by_id_and_school`` in school-facing workflows so the
        school boundary is enforced in the database query itself.
        """

        self._validate_positive_integer(
            class_id,
            "class_id",
        )

        statement = select(
            ClassGroup,
        ).where(
            ClassGroup.id == class_id,
        )

        if include_relationships:
            statement = self._with_relationships(
                statement,
            )

        result = await self.db.execute(
            statement,
        )

        return result.scalar_one_or_none()

    async def get_by_id_and_school(
        self,
        class_id: int,
        school_id: int,
        *,
        include_relationships: bool = True,
    ) -> ClassGroup | None:
        """
        Return a class group only when it belongs to the specified school.
        """

        self._validate_positive_integer(
            class_id,
            "class_id",
        )
        self._validate_positive_integer(
            school_id,
            "school_id",
        )

        statement = select(
            ClassGroup,
        ).where(
            ClassGroup.id == class_id,
            ClassGroup.school_id == school_id,
        )

        if include_relationships:
            statement = self._with_relationships(
                statement,
            )

        result = await self.db.execute(
            statement,
        )

        return result.scalar_one_or_none()

    async def get_by_name(
        self,
        name: str,
        school_id: int,
        *,
        include_relationships: bool = True,
    ) -> ClassGroup | None:
        """
        Return a class group by its name within one school.

        Class names are only unique within a school, so ``school_id`` is
        intentionally required.
        """

        return await self.get_by_name_and_school(
            name=name,
            school_id=school_id,
            include_relationships=include_relationships,
        )

    async def get_by_name_and_school(
        self,
        name: str,
        school_id: int,
        *,
        include_relationships: bool = True,
    ) -> ClassGroup | None:
        """
        Return the class group matching a normalised name in one school.
        """

        normalised_name = self._normalise_name(
            name,
        )
        self._validate_positive_integer(
            school_id,
            "school_id",
        )

        statement = select(
            ClassGroup,
        ).where(
            ClassGroup.name == normalised_name,
            ClassGroup.school_id == school_id,
        )

        if include_relationships:
            statement = self._with_relationships(
                statement,
            )

        result = await self.db.execute(
            statement,
        )

        return result.scalar_one_or_none()

    async def exists(
        self,
        class_id: int,
    ) -> bool:
        """
        Return whether a class group exists by global identifier.
        """

        self._validate_positive_integer(
            class_id,
            "class_id",
        )

        result = await self.db.execute(
            select(
                exists().where(
                    ClassGroup.id == class_id,
                ),
            ),
        )

        return bool(
            result.scalar_one(),
        )

    async def exists_in_school(
        self,
        *,
        school_id: int,
        class_id: int | None = None,
        name: str | None = None,
        exclude_class_id: int | None = None,
    ) -> bool:
        """
        Return whether a matching class group exists in a school.

        Exactly one of ``class_id`` or ``name`` must be supplied.

        ``exclude_class_id`` is useful for update validation where the current
        class group must be excluded from a duplicate-name check.
        """

        self._validate_positive_integer(
            school_id,
            "school_id",
        )

        if class_id is None and name is None:
            raise ValueError(
                "Either class_id or name must be provided.",
            )

        if class_id is not None and name is not None:
            raise ValueError(
                "Provide either class_id or name, not both.",
            )

        if exclude_class_id is not None:
            self._validate_positive_integer(
                exclude_class_id,
                "exclude_class_id",
            )

        conditions = [
            ClassGroup.school_id == school_id,
        ]

        if class_id is not None:
            self._validate_positive_integer(
                class_id,
                "class_id",
            )

            conditions.append(
                ClassGroup.id == class_id,
            )
        else:
            conditions.append(
                ClassGroup.name
                == self._normalise_name(
                    name or "",
                ),
            )

        if exclude_class_id is not None:
            conditions.append(
                ClassGroup.id != exclude_class_id,
            )

        result = await self.db.execute(
            select(
                exists().where(
                    *conditions,
                ),
            ),
        )

        return bool(
            result.scalar_one(),
        )

    async def list_by_school(
        self,
        school_id: int,
        *,
        include_relationships: bool = True,
    ) -> list[ClassGroup]:
        """
        Return all class groups belonging to one school.
        """

        self._validate_positive_integer(
            school_id,
            "school_id",
        )

        statement = (
            select(
                ClassGroup,
            )
            .where(
                ClassGroup.school_id == school_id,
            )
            .order_by(
                ClassGroup.created_at.desc(),
                ClassGroup.id.desc(),
            )
        )

        if include_relationships:
            statement = self._with_relationships(
                statement,
            )

        result = await self.db.execute(
            statement,
        )

        return list(
            result.scalars().unique().all(),
        )

    async def list_by_teacher(
        self,
        teacher_id: int,
        *,
        school_id: int | None = None,
        include_relationships: bool = True,
    ) -> list[ClassGroup]:
        """
        Return class groups assigned to one teacher.

        Supplying ``school_id`` is recommended for school-facing workflows.
        """

        self._validate_positive_integer(
            teacher_id,
            "teacher_id",
        )

        statement = select(
            ClassGroup,
        ).where(
            ClassGroup.teacher_id == teacher_id,
        )

        if school_id is not None:
            self._validate_positive_integer(
                school_id,
                "school_id",
            )

            statement = statement.where(
                ClassGroup.school_id == school_id,
            )

        statement = statement.order_by(
            ClassGroup.created_at.desc(),
            ClassGroup.id.desc(),
        )

        if include_relationships:
            statement = self._with_relationships(
                statement,
            )

        result = await self.db.execute(
            statement,
        )

        return list(
            result.scalars().unique().all(),
        )

    async def create(
        self,
        class_group: ClassGroup,
    ) -> ClassGroup:
        """
        Add and flush a new class group.
        """

        class_group.name = self._normalise_name(
            class_group.name,
        )
        self._validate_positive_integer(
            class_group.school_id,
            "school_id",
        )

        self._validate_teacher_id(
            class_group.teacher_id,
        )

        self.db.add(
            class_group,
        )
        await self.db.flush()
        await self.db.refresh(
            class_group,
        )

        return class_group

    async def save(
        self,
        class_group: ClassGroup,
    ) -> ClassGroup:
        """
        Persist and flush an existing class group.
        """

        if class_group.id is None:
            raise ValueError(
                "Cannot save a class group without an ID.",
            )

        self._validate_positive_integer(
            class_group.id,
            "class_group.id",
        )

        class_group.name = self._normalise_name(
            class_group.name,
        )
        self._validate_positive_integer(
            class_group.school_id,
            "school_id",
        )

        self._validate_teacher_id(
            class_group.teacher_id,
        )

        self.db.add(
            class_group,
        )
        await self.db.flush()
        await self.db.refresh(
            class_group,
        )

        return class_group

    async def delete(
        self,
        class_group: ClassGroup,
    ) -> None:
        """
        Delete and flush a class group.
        """

        if class_group.id is None:
            raise ValueError(
                "Cannot delete a class group without an ID.",
            )

        await self.db.delete(
            class_group,
        )
        await self.db.flush()
