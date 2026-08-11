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
    pass


class CourseUpdate(BaseModel):
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
