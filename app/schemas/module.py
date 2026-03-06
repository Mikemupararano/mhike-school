from pydantic import BaseModel


class ModuleCreate(BaseModel):
    title: str
    order: int = 1


class ModuleOut(BaseModel):
    id: int
    course_id: int
    title: str
    order: int

    class Config:
        from_attributes = True
