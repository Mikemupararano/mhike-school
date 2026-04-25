from pydantic import BaseModel, ConfigDict


class CourseCreate(BaseModel):
    title: str
    description: str | None = None


class CourseOut(BaseModel):
    id: int
    title: str
    description: str | None
    teacher_id: int
    published: bool

    model_config = ConfigDict(from_attributes=True)
