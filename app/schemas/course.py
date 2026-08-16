from pydantic import BaseModel, ConfigDict, Field


class CourseBase(BaseModel):
    title: str = Field(
        min_length=1,
        max_length=255,
    )

    description: str | None = Field(
        default=None,
        max_length=2000,
    )

    subject_id: int | None = Field(
        default=None,
        gt=0,
    )

    exam_board: str | None = Field(
        default=None,
        max_length=100,
    )

    qualification: str | None = Field(
        default=None,
        max_length=100,
    )

    specification_code: str | None = Field(
        default=None,
        max_length=100,
    )


class CourseCreate(CourseBase):
    """
    Create a course owned by the current teacher.

    ``teacher_id`` is deliberately absent because the normal teacher course
    endpoint always assigns ownership to the authenticated teacher.
    """

    pass


class CourseUpdate(BaseModel):
    """
    Update a course through the normal teacher-owned course endpoint.
    """

    title: str | None = Field(
        default=None,
        min_length=1,
        max_length=255,
    )

    description: str | None = Field(
        default=None,
        max_length=2000,
    )

    subject_id: int | None = Field(
        default=None,
        gt=0,
    )

    exam_board: str | None = Field(
        default=None,
        max_length=100,
    )

    qualification: str | None = Field(
        default=None,
        max_length=100,
    )

    specification_code: str | None = Field(
        default=None,
        max_length=100,
    )

    published: bool | None = None


class CourseOut(CourseBase):
    id: int
    school_id: int
    teacher_id: int
    published: bool

    model_config = ConfigDict(
        from_attributes=True,
    )


class SchoolAdminCourseCreate(CourseBase):
    """
    Create a school course and explicitly assign its teacher.

    School administrators create courses within their own school. Platform
    administrators may do the same when operating within an explicit school
    scope.
    """

    teacher_id: int = Field(
        gt=0,
    )

    published: bool = False


class SchoolAdminCourseUpdate(BaseModel):
    """
    Update a school course through the School Admin course-management API.

    ``teacher_id`` is optional so ordinary metadata edits do not require a
    reassignment. When supplied, the target teacher must belong to the same
    school.
    """

    title: str | None = Field(
        default=None,
        min_length=1,
        max_length=255,
    )

    description: str | None = Field(
        default=None,
        max_length=2000,
    )

    subject_id: int | None = Field(
        default=None,
        gt=0,
    )

    exam_board: str | None = Field(
        default=None,
        max_length=100,
    )

    qualification: str | None = Field(
        default=None,
        max_length=100,
    )

    specification_code: str | None = Field(
        default=None,
        max_length=100,
    )

    teacher_id: int | None = Field(
        default=None,
        gt=0,
    )

    published: bool | None = None


class SchoolAdminCourseOut(CourseBase):
    """
    School Admin representation of a course.

    ``teacher_name`` is included because the management screen needs to show
    the current assignment without making an additional user lookup.
    """

    id: int
    school_id: int
    teacher_id: int | None
    teacher_name: str | None
    published: bool

    model_config = ConfigDict(
        from_attributes=True,
    )
