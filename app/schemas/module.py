from pydantic import BaseModel, ConfigDict


class ModuleCreate(BaseModel):
    title: str
    order: int = 1


class ModuleOut(BaseModel):
    id: int
    course_id: int
    title: str
    order: int

    model_config = ConfigDict(from_attributes=True)
