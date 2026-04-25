from pydantic import BaseModel, ConfigDict


class LessonCreate(BaseModel):
    title: str
    content_type: str = "text"  # text | video | pdf | link
    content: str | None = None
    order: int = 1


class LessonOut(BaseModel):
    id: int
    module_id: int  # REQUIRED for frontend navigation
    title: str
    content_type: str
    content: str | None = None
    order: int

    model_config = ConfigDict(from_attributes=True)
