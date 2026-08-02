from __future__ import annotations

from typing import Any

from sqlalchemy import Select, exists, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.timetable import Timetable
from app.models.timetable_assignment import TimetableAssignment
from app.models.timetable_entry import TimetableEntry
from app.models.timetable_period import TimetablePeriod
from app.schemas.timetable import (
    TimetableAssignmentCreate,
    TimetableAssignmentFilter,
    TimetableCreate,
    TimetableEntryCreate,
    TimetableEntryFilter,
    TimetableFilter,
    TimetablePeriodCreate,
)


class TimetableRepository:
    """
    Repository for timetable periods, timetable containers, entries, and
    assignments.

    This repository never commits or rolls back transactions. Transaction
    ownership remains with the calling service, endpoint, import processor,
    or background task.
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
    def _normalise_required_string(
        value: str,
        field_name: str,
        *,
        max_length: int,
    ) -> str:
        """
        Return a trimmed, non-empty string within the supplied length limit.
        """

        normalised_value = value.strip()

        if not normalised_value:
            raise ValueError(
                f"{field_name} cannot be blank.",
            )

        if len(normalised_value) > max_length:
            raise ValueError(
                f"{field_name} cannot exceed {max_length} characters.",
            )

        return normalised_value

    @staticmethod
    def _normalise_optional_string(
        value: str | None,
        field_name: str,
        *,
        max_length: int | None = None,
    ) -> str | None:
        """
        Return a trimmed optional string.
        """

        if value is None:
            return None

        normalised_value = value.strip()

        if not normalised_value:
            return None

        if max_length is not None and len(normalised_value) > max_length:
            raise ValueError(
                f"{field_name} cannot exceed {max_length} characters.",
            )

        return normalised_value

    # ------------------------------------------------------------------
    # Timetable periods
    # ------------------------------------------------------------------

    async def create_period(
        self,
        data: TimetablePeriodCreate,
    ) -> TimetablePeriod:
        """
        Create and flush a timetable period.
        """

        self._validate_positive_integer(
            data.school_id,
            "school_id",
        )
        self._validate_positive_integer(
            data.period_number,
            "period_number",
        )

        if data.end_time <= data.start_time:
            raise ValueError(
                "Timetable period end_time must be later than start_time.",
            )

        period = TimetablePeriod(
            **data.model_dump(),
        )

        period.name = self._normalise_required_string(
            period.name,
            "name",
            max_length=100,
        )
        period.short_name = self._normalise_required_string(
            period.short_name,
            "short_name",
            max_length=20,
        )

        self.db.add(
            period,
        )
        await self.db.flush()
        await self.db.refresh(
            period,
        )

        return period

    async def save_period(
        self,
        period: TimetablePeriod,
    ) -> TimetablePeriod:
        """
        Persist and flush an existing timetable period.
        """

        if period.id is None:
            raise ValueError(
                "Cannot save a timetable period without an ID.",
            )

        self._validate_positive_integer(
            period.id,
            "period.id",
        )
        self._validate_positive_integer(
            period.school_id,
            "school_id",
        )
        self._validate_positive_integer(
            period.period_number,
            "period_number",
        )

        period.name = self._normalise_required_string(
            period.name,
            "name",
            max_length=100,
        )
        period.short_name = self._normalise_required_string(
            period.short_name,
            "short_name",
            max_length=20,
        )

        if period.end_time <= period.start_time:
            raise ValueError(
                "Timetable period end_time must be later than start_time.",
            )

        self.db.add(
            period,
        )
        await self.db.flush()
        await self.db.refresh(
            period,
        )

        return period

    async def get_period_by_id(
        self,
        period_id: int,
    ) -> TimetablePeriod | None:
        """
        Return a timetable period by its global identifier.
        """

        self._validate_positive_integer(
            period_id,
            "period_id",
        )

        result = await self.db.execute(
            select(
                TimetablePeriod,
            ).where(
                TimetablePeriod.id == period_id,
            ),
        )

        return result.scalar_one_or_none()

    async def get_period_by_id_and_school(
        self,
        period_id: int,
        school_id: int,
    ) -> TimetablePeriod | None:
        """
        Return a timetable period only when it belongs to the specified school.
        """

        self._validate_positive_integer(
            period_id,
            "period_id",
        )
        self._validate_positive_integer(
            school_id,
            "school_id",
        )

        result = await self.db.execute(
            select(
                TimetablePeriod,
            ).where(
                TimetablePeriod.id == period_id,
                TimetablePeriod.school_id == school_id,
            ),
        )

        return result.scalar_one_or_none()

    async def get_period_by_number(
        self,
        *,
        school_id: int,
        period_number: int,
    ) -> TimetablePeriod | None:
        """
        Return a timetable period by period number within one school.
        """

        self._validate_positive_integer(
            school_id,
            "school_id",
        )
        self._validate_positive_integer(
            period_number,
            "period_number",
        )

        result = await self.db.execute(
            select(
                TimetablePeriod,
            ).where(
                TimetablePeriod.school_id == school_id,
                TimetablePeriod.period_number == period_number,
            ),
        )

        return result.scalar_one_or_none()

    async def get_period_by_short_name(
        self,
        *,
        school_id: int,
        short_name: str,
    ) -> TimetablePeriod | None:
        """
        Return a timetable period by short name within one school.
        """

        self._validate_positive_integer(
            school_id,
            "school_id",
        )

        normalised_short_name = self._normalise_required_string(
            short_name,
            "short_name",
            max_length=20,
        )

        result = await self.db.execute(
            select(
                TimetablePeriod,
            ).where(
                TimetablePeriod.school_id == school_id,
                TimetablePeriod.short_name == normalised_short_name,
            ),
        )

        return result.scalar_one_or_none()

    async def period_exists_in_school(
        self,
        *,
        school_id: int,
        period_id: int | None = None,
        period_number: int | None = None,
        short_name: str | None = None,
        exclude_period_id: int | None = None,
    ) -> bool:
        """
        Return whether a matching timetable period exists in one school.

        Exactly one lookup field must be supplied:

        - ``period_id``;
        - ``period_number``;
        - ``short_name``.
        """

        self._validate_positive_integer(
            school_id,
            "school_id",
        )

        supplied_lookups = sum(
            value is not None
            for value in (
                period_id,
                period_number,
                short_name,
            )
        )

        if supplied_lookups != 1:
            raise ValueError(
                "Provide exactly one of period_id, period_number, " "or short_name.",
            )

        conditions = [
            TimetablePeriod.school_id == school_id,
        ]

        if period_id is not None:
            self._validate_positive_integer(
                period_id,
                "period_id",
            )
            conditions.append(
                TimetablePeriod.id == period_id,
            )

        elif period_number is not None:
            self._validate_positive_integer(
                period_number,
                "period_number",
            )
            conditions.append(
                TimetablePeriod.period_number == period_number,
            )

        else:
            normalised_short_name = self._normalise_required_string(
                short_name or "",
                "short_name",
                max_length=20,
            )
            conditions.append(
                TimetablePeriod.short_name == normalised_short_name,
            )

        if exclude_period_id is not None:
            self._validate_positive_integer(
                exclude_period_id,
                "exclude_period_id",
            )
            conditions.append(
                TimetablePeriod.id != exclude_period_id,
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

    async def list_periods(
        self,
        school_id: int,
        *,
        active_only: bool | None = None,
    ) -> list[TimetablePeriod]:
        """
        Return timetable periods for one school in schedule order.
        """

        self._validate_positive_integer(
            school_id,
            "school_id",
        )

        statement = select(
            TimetablePeriod,
        ).where(
            TimetablePeriod.school_id == school_id,
        )

        if active_only is not None:
            statement = statement.where(
                TimetablePeriod.is_active.is_(
                    active_only,
                ),
            )

        statement = statement.order_by(
            TimetablePeriod.period_number.asc(),
            TimetablePeriod.start_time.asc(),
            TimetablePeriod.id.asc(),
        )

        result = await self.db.execute(
            statement,
        )

        return list(
            result.scalars().all(),
        )

    async def delete_period(
        self,
        period: TimetablePeriod,
    ) -> None:
        """
        Delete and flush a timetable period.
        """

        if period.id is None:
            raise ValueError(
                "Cannot delete a timetable period without an ID.",
            )

        self._validate_positive_integer(
            period.id,
            "period.id",
        )

        await self.db.delete(
            period,
        )
        await self.db.flush()

    # ------------------------------------------------------------------
    # Timetable containers
    # ------------------------------------------------------------------

    async def create_timetable(
        self,
        data: TimetableCreate,
    ) -> Timetable:
        """
        Create and flush a timetable container.
        """

        self._validate_positive_integer(
            data.school_id,
            "school_id",
        )

        if data.effective_to is not None and data.effective_to < data.effective_from:
            raise ValueError(
                "effective_to cannot be earlier than effective_from.",
            )

        timetable = Timetable(
            **data.model_dump(),
        )

        timetable.name = self._normalise_required_string(
            timetable.name,
            "name",
            max_length=150,
        )
        timetable.academic_year = self._normalise_required_string(
            timetable.academic_year,
            "academic_year",
            max_length=20,
        )

        self.db.add(
            timetable,
        )
        await self.db.flush()
        await self.db.refresh(
            timetable,
        )

        return timetable

    async def save_timetable(
        self,
        timetable: Timetable,
    ) -> Timetable:
        """
        Persist and flush an existing timetable.
        """

        if timetable.id is None:
            raise ValueError(
                "Cannot save a timetable without an ID.",
            )

        self._validate_positive_integer(
            timetable.id,
            "timetable.id",
        )
        self._validate_positive_integer(
            timetable.school_id,
            "school_id",
        )

        timetable.name = self._normalise_required_string(
            timetable.name,
            "name",
            max_length=150,
        )
        timetable.academic_year = self._normalise_required_string(
            timetable.academic_year,
            "academic_year",
            max_length=20,
        )

        if (
            timetable.effective_to is not None
            and timetable.effective_to < timetable.effective_from
        ):
            raise ValueError(
                "effective_to cannot be earlier than effective_from.",
            )

        self.db.add(
            timetable,
        )
        await self.db.flush()
        await self.db.refresh(
            timetable,
        )

        return timetable

    async def get_timetable_by_id(
        self,
        timetable_id: int,
    ) -> Timetable | None:
        """
        Return a timetable by its global identifier.
        """

        self._validate_positive_integer(
            timetable_id,
            "timetable_id",
        )

        result = await self.db.execute(
            select(
                Timetable,
            ).where(
                Timetable.id == timetable_id,
            ),
        )

        return result.scalar_one_or_none()

    async def get_timetable_by_id_and_school(
        self,
        timetable_id: int,
        school_id: int,
    ) -> Timetable | None:
        """
        Return a timetable only when it belongs to the specified school.
        """

        self._validate_positive_integer(
            timetable_id,
            "timetable_id",
        )
        self._validate_positive_integer(
            school_id,
            "school_id",
        )

        result = await self.db.execute(
            select(
                Timetable,
            ).where(
                Timetable.id == timetable_id,
                Timetable.school_id == school_id,
            ),
        )

        return result.scalar_one_or_none()

    async def get_timetable_by_name_and_year(
        self,
        *,
        school_id: int,
        name: str,
        academic_year: str,
    ) -> Timetable | None:
        """
        Return a timetable by school, name, and academic year.
        """

        self._validate_positive_integer(
            school_id,
            "school_id",
        )

        normalised_name = self._normalise_required_string(
            name,
            "name",
            max_length=150,
        )
        normalised_academic_year = self._normalise_required_string(
            academic_year,
            "academic_year",
            max_length=20,
        )

        result = await self.db.execute(
            select(
                Timetable,
            ).where(
                Timetable.school_id == school_id,
                Timetable.name == normalised_name,
                Timetable.academic_year == normalised_academic_year,
            ),
        )

        return result.scalar_one_or_none()

    async def timetable_exists_in_school(
        self,
        *,
        school_id: int,
        timetable_id: int | None = None,
        name: str | None = None,
        academic_year: str | None = None,
        exclude_timetable_id: int | None = None,
    ) -> bool:
        """
        Return whether a school-scoped timetable exists.

        Supported lookups:

        - by ``timetable_id``;
        - by ``name`` and ``academic_year``.
        """

        self._validate_positive_integer(
            school_id,
            "school_id",
        )

        by_id = timetable_id is not None
        by_name_and_year = name is not None or academic_year is not None

        if by_id and by_name_and_year:
            raise ValueError(
                "Provide timetable_id or name/academic_year, not both.",
            )

        if not by_id and not by_name_and_year:
            raise ValueError(
                "Provide timetable_id or both name and academic_year.",
            )

        if by_name_and_year and (name is None or academic_year is None):
            raise ValueError(
                "name and academic_year must be provided together.",
            )

        conditions = [
            Timetable.school_id == school_id,
        ]

        if timetable_id is not None:
            self._validate_positive_integer(
                timetable_id,
                "timetable_id",
            )
            conditions.append(
                Timetable.id == timetable_id,
            )
        else:
            conditions.extend(
                [
                    Timetable.name
                    == self._normalise_required_string(
                        name or "",
                        "name",
                        max_length=150,
                    ),
                    Timetable.academic_year
                    == self._normalise_required_string(
                        academic_year or "",
                        "academic_year",
                        max_length=20,
                    ),
                ],
            )

        if exclude_timetable_id is not None:
            self._validate_positive_integer(
                exclude_timetable_id,
                "exclude_timetable_id",
            )
            conditions.append(
                Timetable.id != exclude_timetable_id,
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

    async def list_timetables(
        self,
        filters: TimetableFilter,
    ) -> list[Timetable]:
        """
        Return timetable containers matching the supplied filters.
        """

        query = select(
            Timetable,
        ).order_by(
            Timetable.effective_from.desc(),
            Timetable.id.desc(),
        )

        if filters.school_id is not None:
            self._validate_positive_integer(
                filters.school_id,
                "filters.school_id",
            )
            query = query.where(
                Timetable.school_id == filters.school_id,
            )

        if filters.academic_year is not None:
            query = query.where(
                Timetable.academic_year
                == self._normalise_required_string(
                    filters.academic_year,
                    "filters.academic_year",
                    max_length=20,
                ),
            )

        if filters.is_active is not None:
            query = query.where(
                Timetable.is_active.is_(
                    filters.is_active,
                ),
            )

        query = query.offset(
            filters.offset,
        ).limit(
            filters.limit,
        )

        result = await self.db.execute(
            query,
        )

        return list(
            result.scalars().all(),
        )

    async def delete_timetable(
        self,
        timetable: Timetable,
    ) -> None:
        """
        Delete and flush a timetable container.
        """

        if timetable.id is None:
            raise ValueError(
                "Cannot delete a timetable without an ID.",
            )

        self._validate_positive_integer(
            timetable.id,
            "timetable.id",
        )

        await self.db.delete(
            timetable,
        )
        await self.db.flush()

    # ------------------------------------------------------------------
    # Timetable entries
    # ------------------------------------------------------------------

    async def create_entry(
        self,
        data: TimetableEntryCreate,
    ) -> TimetableEntry:
        """
        Create and flush a timetable entry.
        """

        self._validate_positive_integer(
            data.timetable_id,
            "timetable_id",
        )
        self._validate_positive_integer(
            data.school_id,
            "school_id",
        )
        self._validate_positive_integer(
            data.timetable_period_id,
            "timetable_period_id",
        )

        entry = TimetableEntry(
            **data.model_dump(),
        )

        entry.room = self._normalise_optional_string(
            entry.room,
            "room",
            max_length=100,
        )
        entry.title = self._normalise_optional_string(
            entry.title,
            "title",
            max_length=200,
        )
        entry.notes = self._normalise_optional_string(
            entry.notes,
            "notes",
        )

        self.db.add(
            entry,
        )
        await self.db.flush()
        await self.db.refresh(
            entry,
        )

        return entry

    async def save_entry(
        self,
        entry: TimetableEntry,
    ) -> TimetableEntry:
        """
        Persist and flush an existing timetable entry.
        """

        if entry.id is None:
            raise ValueError(
                "Cannot save a timetable entry without an ID.",
            )

        self._validate_positive_integer(
            entry.id,
            "entry.id",
        )
        self._validate_positive_integer(
            entry.timetable_id,
            "timetable_id",
        )
        self._validate_positive_integer(
            entry.school_id,
            "school_id",
        )
        self._validate_positive_integer(
            entry.timetable_period_id,
            "timetable_period_id",
        )

        entry.room = self._normalise_optional_string(
            entry.room,
            "room",
            max_length=100,
        )
        entry.title = self._normalise_optional_string(
            entry.title,
            "title",
            max_length=200,
        )
        entry.notes = self._normalise_optional_string(
            entry.notes,
            "notes",
        )

        self.db.add(
            entry,
        )
        await self.db.flush()
        await self.db.refresh(
            entry,
        )

        return entry

    async def get_entry_by_id(
        self,
        entry_id: int,
    ) -> TimetableEntry | None:
        """
        Return a timetable entry by its global identifier.
        """

        self._validate_positive_integer(
            entry_id,
            "entry_id",
        )

        result = await self.db.execute(
            select(
                TimetableEntry,
            ).where(
                TimetableEntry.id == entry_id,
            ),
        )

        return result.scalar_one_or_none()

    async def get_entry_by_id_and_school(
        self,
        entry_id: int,
        school_id: int,
    ) -> TimetableEntry | None:
        """
        Return a timetable entry only when it belongs to one school.
        """

        self._validate_positive_integer(
            entry_id,
            "entry_id",
        )
        self._validate_positive_integer(
            school_id,
            "school_id",
        )

        result = await self.db.execute(
            select(
                TimetableEntry,
            ).where(
                TimetableEntry.id == entry_id,
                TimetableEntry.school_id == school_id,
            ),
        )

        return result.scalar_one_or_none()

    async def find_matching_entry(
        self,
        *,
        school_id: int,
        timetable_id: int,
        timetable_period_id: int,
        day_of_week: Any,
        class_group_id: int | None,
        course_id: int | None,
        teacher_id: int | None,
    ) -> TimetableEntry | None:
        """
        Return an entry matching its scheduling identity.

        Nullable foreign keys are compared explicitly using ``IS NULL`` when
        absent.
        """

        self._validate_positive_integer(
            school_id,
            "school_id",
        )
        self._validate_positive_integer(
            timetable_id,
            "timetable_id",
        )
        self._validate_positive_integer(
            timetable_period_id,
            "timetable_period_id",
        )

        conditions = [
            TimetableEntry.school_id == school_id,
            TimetableEntry.timetable_id == timetable_id,
            TimetableEntry.timetable_period_id == timetable_period_id,
            TimetableEntry.day_of_week == day_of_week,
        ]

        conditions.append(
            (
                TimetableEntry.class_group_id == class_group_id
                if class_group_id is not None
                else TimetableEntry.class_group_id.is_(None)
            ),
        )
        conditions.append(
            (
                TimetableEntry.course_id == course_id
                if course_id is not None
                else TimetableEntry.course_id.is_(None)
            ),
        )
        conditions.append(
            (
                TimetableEntry.teacher_id == teacher_id
                if teacher_id is not None
                else TimetableEntry.teacher_id.is_(None)
            ),
        )

        result = await self.db.execute(
            select(
                TimetableEntry,
            ).where(
                *conditions,
            ),
        )

        return result.scalar_one_or_none()

    async def list_entries(
        self,
        filters: TimetableEntryFilter,
    ) -> list[TimetableEntry]:
        """
        Return timetable entries matching the supplied filters.
        """

        query = select(
            TimetableEntry,
        ).order_by(
            TimetableEntry.day_of_week.asc(),
            TimetableEntry.timetable_period_id.asc(),
            TimetableEntry.id.asc(),
        )

        if filters.school_id is not None:
            self._validate_positive_integer(
                filters.school_id,
                "filters.school_id",
            )
            query = query.where(
                TimetableEntry.school_id == filters.school_id,
            )

        if filters.timetable_id is not None:
            self._validate_positive_integer(
                filters.timetable_id,
                "filters.timetable_id",
            )
            query = query.where(
                TimetableEntry.timetable_id == filters.timetable_id,
            )

        if filters.class_group_id is not None:
            self._validate_positive_integer(
                filters.class_group_id,
                "filters.class_group_id",
            )
            query = query.where(
                TimetableEntry.class_group_id == filters.class_group_id,
            )

        if filters.course_id is not None:
            self._validate_positive_integer(
                filters.course_id,
                "filters.course_id",
            )
            query = query.where(
                TimetableEntry.course_id == filters.course_id,
            )

        if filters.teacher_id is not None:
            self._validate_positive_integer(
                filters.teacher_id,
                "filters.teacher_id",
            )
            query = query.where(
                TimetableEntry.teacher_id == filters.teacher_id,
            )

        if filters.day_of_week is not None:
            query = query.where(
                TimetableEntry.day_of_week == filters.day_of_week,
            )

        query = query.offset(
            filters.offset,
        ).limit(
            filters.limit,
        )

        result = await self.db.execute(
            query,
        )

        return list(
            result.scalars().all(),
        )

    async def delete_entry(
        self,
        entry: TimetableEntry,
    ) -> None:
        """
        Delete and flush a timetable entry.
        """

        if entry.id is None:
            raise ValueError(
                "Cannot delete a timetable entry without an ID.",
            )

        self._validate_positive_integer(
            entry.id,
            "entry.id",
        )

        await self.db.delete(
            entry,
        )
        await self.db.flush()

    # ------------------------------------------------------------------
    # Timetable assignments
    # ------------------------------------------------------------------

    async def create_assignment(
        self,
        data: TimetableAssignmentCreate,
    ) -> TimetableAssignment:
        """
        Create and flush a timetable assignment.
        """

        self._validate_positive_integer(
            data.timetable_id,
            "timetable_id",
        )
        self._validate_positive_integer(
            data.school_id,
            "school_id",
        )

        assignment = TimetableAssignment(
            **data.model_dump(),
        )

        self.db.add(
            assignment,
        )
        await self.db.flush()
        await self.db.refresh(
            assignment,
        )

        return assignment

    async def get_assignment_by_id(
        self,
        assignment_id: int,
    ) -> TimetableAssignment | None:
        """
        Return a timetable assignment by its global identifier.
        """

        self._validate_positive_integer(
            assignment_id,
            "assignment_id",
        )

        result = await self.db.execute(
            select(
                TimetableAssignment,
            ).where(
                TimetableAssignment.id == assignment_id,
            ),
        )

        return result.scalar_one_or_none()

    async def find_matching_assignment(
        self,
        *,
        school_id: int,
        timetable_id: int,
        assignment_type: Any,
        user_id: int | None,
        class_group_id: int | None,
    ) -> TimetableAssignment | None:
        """
        Return an assignment matching its timetable scope.
        """

        self._validate_positive_integer(
            school_id,
            "school_id",
        )
        self._validate_positive_integer(
            timetable_id,
            "timetable_id",
        )

        conditions = [
            TimetableAssignment.school_id == school_id,
            TimetableAssignment.timetable_id == timetable_id,
            TimetableAssignment.assignment_type == assignment_type,
        ]

        conditions.append(
            (
                TimetableAssignment.user_id == user_id
                if user_id is not None
                else TimetableAssignment.user_id.is_(None)
            ),
        )
        conditions.append(
            (
                TimetableAssignment.class_group_id == class_group_id
                if class_group_id is not None
                else TimetableAssignment.class_group_id.is_(None)
            ),
        )

        result = await self.db.execute(
            select(
                TimetableAssignment,
            ).where(
                *conditions,
            ),
        )

        return result.scalar_one_or_none()

    async def list_assignments(
        self,
        filters: TimetableAssignmentFilter,
    ) -> list[TimetableAssignment]:
        """
        Return timetable assignments matching the supplied filters.
        """

        query = select(
            TimetableAssignment,
        ).order_by(
            TimetableAssignment.id.desc(),
        )

        if filters.school_id is not None:
            self._validate_positive_integer(
                filters.school_id,
                "filters.school_id",
            )
            query = query.where(
                TimetableAssignment.school_id == filters.school_id,
            )

        if filters.timetable_id is not None:
            self._validate_positive_integer(
                filters.timetable_id,
                "filters.timetable_id",
            )
            query = query.where(
                TimetableAssignment.timetable_id == filters.timetable_id,
            )

        if filters.assignment_type is not None:
            query = query.where(
                TimetableAssignment.assignment_type == filters.assignment_type,
            )

        if filters.user_id is not None:
            self._validate_positive_integer(
                filters.user_id,
                "filters.user_id",
            )
            query = query.where(
                TimetableAssignment.user_id == filters.user_id,
            )

        if filters.class_group_id is not None:
            self._validate_positive_integer(
                filters.class_group_id,
                "filters.class_group_id",
            )
            query = query.where(
                TimetableAssignment.class_group_id == filters.class_group_id,
            )

        query = query.offset(
            filters.offset,
        ).limit(
            filters.limit,
        )

        result = await self.db.execute(
            query,
        )

        return list(
            result.scalars().all(),
        )

    async def delete_assignment(
        self,
        assignment: TimetableAssignment,
    ) -> None:
        """
        Delete and flush a timetable assignment.
        """

        if assignment.id is None:
            raise ValueError(
                "Cannot delete a timetable assignment without an ID.",
            )

        self._validate_positive_integer(
            assignment.id,
            "assignment.id",
        )

        await self.db.delete(
            assignment,
        )
        await self.db.flush()
