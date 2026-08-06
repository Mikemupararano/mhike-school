from __future__ import annotations

from sqlalchemy import exists, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.course import Course


class CourseRepository:
    """
    Repository for school-scoped course persistence and lookup.

    The repository never commits or rolls back transactions. Transaction
    ownership remains with the calling service, import processor, endpoint,
    or background task.
    """

    def __init__(
        self,
        db: AsyncSession,
    ) -> None:
        self.db = db

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
    def _normalise_title(
        title: str,
    ) -> str:
        """
        Return a validated, trimmed course title.
        """

        normalised_title = title.strip()

        if not normalised_title:
            raise ValueError(
                "Course title cannot be blank.",
            )

        if len(normalised_title) > 255:
            raise ValueError(
                "Course title cannot exceed 255 characters.",
            )

        return normalised_title

    @staticmethod
    def _normalise_description(
        description: str | None,
    ) -> str | None:
        """
        Return a trimmed optional course description.
        """

        if description is None:
            return None

        normalised_description = description.strip()

        if not normalised_description:
            return None

        if len(normalised_description) > 2000:
            raise ValueError(
                "Course description cannot exceed 2000 characters.",
            )

        return normalised_description

    @staticmethod
    def _apply_relationship_loading(
        statement,
        *,
        include_relationships: bool,
    ):
        """
        Apply the standard eager-loading configuration.

        When relationship loading is enabled, the repository returns
        fully hydrated Course objects including:

        - teacher;
        - school;
        - modules;
        - assignments.

        Centralising this configuration keeps repository methods consistent
        and avoids duplicated relationship-loading logic.
        """

        if not include_relationships:
            return statement

        return statement.options(
            selectinload(
                Course.teacher,
            ),
            selectinload(
                Course.school,
            ),
            selectinload(
                Course.modules,
            ),
            selectinload(
                Course.assignments,
            ),
        )

    async def get_by_id(
        self,
        course_id: int,
        *,
        include_relationships: bool = True,
    ) -> Course | None:
        """
        Return a course by its global identifier.

        Prefer ``get_by_id_and_school`` in school-facing workflows.
        """

        self._validate_positive_integer(
            course_id,
            "course_id",
        )

        statement = select(
            Course,
        ).where(
            Course.id == course_id,
        )

        statement = self._apply_relationship_loading(
            statement,
            include_relationships=include_relationships,
        )

        result = await self.db.execute(
            statement,
        )

        return result.scalar_one_or_none()

    async def get_by_id_and_school(
        self,
        course_id: int,
        school_id: int,
        *,
        include_relationships: bool = True,
    ) -> Course | None:
        """
        Return a course only when it belongs to the specified school.
        """

        self._validate_positive_integer(
            course_id,
            "course_id",
        )
        self._validate_positive_integer(
            school_id,
            "school_id",
        )

        statement = select(
            Course,
        ).where(
            Course.id == course_id,
            Course.school_id == school_id,
        )

        statement = self._apply_relationship_loading(
            statement,
            include_relationships=include_relationships,
        )

        result = await self.db.execute(
            statement,
        )

        return result.scalar_one_or_none()

    async def get_by_title_and_teacher(
        self,
        *,
        title: str,
        teacher_id: int,
        school_id: int,
        include_relationships: bool = True,
    ) -> Course | None:
        """
        Return a course matching title, teacher, and school.

        The current Course model does not enforce title uniqueness. Import
        matching therefore uses the stable combination of:

        - school_id;
        - teacher_id;
        - title.
        """

        normalised_title = self._normalise_title(
            title,
        )
        self._validate_positive_integer(
            teacher_id,
            "teacher_id",
        )
        self._validate_positive_integer(
            school_id,
            "school_id",
        )

        statement = select(
            Course,
        ).where(
            Course.title == normalised_title,
            Course.teacher_id == teacher_id,
            Course.school_id == school_id,
        )

        statement = self._apply_relationship_loading(
            statement,
            include_relationships=include_relationships,
        )

        result = await self.db.execute(
            statement,
        )

        return result.scalar_one_or_none()

    async def get_by_title_and_school(
        self,
        *,
        title: str,
        school_id: int,
        include_relationships: bool = True,
    ) -> Course | None:
        """
        Return a course matching title within one school.

        This lookup supports timetable imports where a teacher may not be
        supplied in the row.

        The Course model does not currently enforce title uniqueness within a
        school. Callers should therefore prefer ``get_by_title_and_teacher``
        whenever the teacher is known.
        """

        normalised_title = self._normalise_title(
            title,
        )
        self._validate_positive_integer(
            school_id,
            "school_id",
        )

        statement = select(
            Course,
        ).where(
            Course.title == normalised_title,
            Course.school_id == school_id,
        )

        statement = self._apply_relationship_loading(
            statement,
            include_relationships=include_relationships,
        )

        result = await self.db.execute(
            statement,
        )

        return result.scalar_one_or_none()

    async def list_by_school(
        self,
        school_id: int,
        *,
        published: bool | None = None,
        include_relationships: bool = True,
    ) -> list[Course]:
        """
        Return courses belonging to one school.

        Results are ordered newest first. Relationship loading can be
        disabled for lightweight internal lookups.
        """

        self._validate_positive_integer(
            school_id,
            "school_id",
        )

        statement = select(
            Course,
        ).where(
            Course.school_id == school_id,
        )

        if published is not None:
            statement = statement.where(
                Course.published.is_(
                    published,
                ),
            )

        statement = statement.order_by(
            Course.created_at.desc(),
            Course.id.desc(),
        )

        statement = self._apply_relationship_loading(
            statement,
            include_relationships=include_relationships,
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
        published: bool | None = None,
        include_relationships: bool = True,
    ) -> list[Course]:
        """
        Return courses assigned to one teacher.

        Supplying ``school_id`` is recommended for school-facing workflows.
        Relationship loading can be disabled for lightweight internal lookups.
        """

        self._validate_positive_integer(
            teacher_id,
            "teacher_id",
        )

        statement = select(
            Course,
        ).where(
            Course.teacher_id == teacher_id,
        )

        if school_id is not None:
            self._validate_positive_integer(
                school_id,
                "school_id",
            )

            statement = statement.where(
                Course.school_id == school_id,
            )

        if published is not None:
            statement = statement.where(
                Course.published.is_(
                    published,
                ),
            )

        statement = statement.order_by(
            Course.created_at.desc(),
            Course.id.desc(),
        )

        statement = self._apply_relationship_loading(
            statement,
            include_relationships=include_relationships,
        )

        result = await self.db.execute(
            statement,
        )

        return list(
            result.scalars().unique().all(),
        )

    async def exists(
        self,
        course_id: int,
    ) -> bool:
        """
        Return whether a course exists by global identifier.
        """

        self._validate_positive_integer(
            course_id,
            "course_id",
        )

        result = await self.db.execute(
            select(
                exists().where(
                    Course.id == course_id,
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
        course_id: int | None = None,
        title: str | None = None,
        teacher_id: int | None = None,
        exclude_course_id: int | None = None,
    ) -> bool:
        """
        Return whether a matching course exists within a school.

        Supported lookups:

        - by ``course_id``;
        - by ``title``;
        - by ``title`` and ``teacher_id``.

        ``exclude_course_id`` is useful during update validation.
        """

        self._validate_positive_integer(
            school_id,
            "school_id",
        )

        if course_id is None and title is None:
            raise ValueError(
                "Either course_id or title must be provided.",
            )

        if course_id is not None and title is not None:
            raise ValueError(
                "Provide either course_id or title, not both.",
            )

        if teacher_id is not None and title is None:
            raise ValueError(
                "teacher_id can only be used with title.",
            )

        if exclude_course_id is not None:
            self._validate_positive_integer(
                exclude_course_id,
                "exclude_course_id",
            )

        conditions = [
            Course.school_id == school_id,
        ]

        if course_id is not None:
            self._validate_positive_integer(
                course_id,
                "course_id",
            )

            conditions.append(
                Course.id == course_id,
            )
        else:
            conditions.append(
                Course.title
                == self._normalise_title(
                    title or "",
                ),
            )

            if teacher_id is not None:
                self._validate_positive_integer(
                    teacher_id,
                    "teacher_id",
                )

                conditions.append(
                    Course.teacher_id == teacher_id,
                )

        if exclude_course_id is not None:
            conditions.append(
                Course.id != exclude_course_id,
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

    async def create(
        self,
        course: Course,
    ) -> Course:
        """
        Add and flush a new course.
        """

        course.title = self._normalise_title(
            course.title,
        )
        course.description = self._normalise_description(
            course.description,
        )

        self._validate_positive_integer(
            course.teacher_id,
            "teacher_id",
        )
        self._validate_positive_integer(
            course.school_id,
            "school_id",
        )

        self.db.add(
            course,
        )
        await self.db.flush()
        await self.db.refresh(
            course,
        )

        return course

    async def save(
        self,
        course: Course,
    ) -> Course:
        """
        Persist and flush an existing course.
        """

        if course.id is None:
            raise ValueError(
                "Cannot save a course without an ID.",
            )

        self._validate_positive_integer(
            course.id,
            "course.id",
        )

        course.title = self._normalise_title(
            course.title,
        )
        course.description = self._normalise_description(
            course.description,
        )

        self._validate_positive_integer(
            course.teacher_id,
            "teacher_id",
        )
        self._validate_positive_integer(
            course.school_id,
            "school_id",
        )

        self.db.add(
            course,
        )
        await self.db.flush()
        await self.db.refresh(
            course,
        )

        return course

    async def delete(
        self,
        course: Course,
    ) -> None:
        """
        Delete and flush a course.
        """

        if course.id is None:
            raise ValueError(
                "Cannot delete a course without an ID.",
            )

        await self.db.delete(
            course,
        )
        await self.db.flush()
