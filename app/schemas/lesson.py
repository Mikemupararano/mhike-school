from pydantic import BaseModel


class LessonCreate(BaseModel):
    title: str
    content_type: str = "text"  # text/video/pdf/link
    content: str | None = None
    order: int = 1


class LessonOut(BaseModel):
    id: int
    module_id: int
    title: str
    content_type: str
    content: str | None
    order: int

    class Config:
        from_attributes = True
