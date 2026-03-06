from pydantic import BaseModel


class CourseCreate(BaseModel):
    title: str
    description: str | None = None


class CourseOut(BaseModel):
    id: int
    title: str
    description: str | None
    teacher_id: int
    published: bool

    class Config:
        from_attributes = True
