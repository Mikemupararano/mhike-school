from pydantic import BaseModel, Field


class QuizOptionCreate(BaseModel):
    option_text: str = Field(min_length=1, max_length=500)
    is_correct: bool = False
    order: int = 1


class QuizOptionUpdate(BaseModel):
    option_text: str | None = Field(default=None, min_length=1, max_length=500)
    is_correct: bool | None = None
    order: int | None = None


class QuizOptionOut(BaseModel):
    id: int
    option_text: str
    is_correct: bool
    order: int

    class Config:
        from_attributes = True


class QuizOptionPublicOut(BaseModel):
    id: int
    option_text: str
    order: int

    class Config:
        from_attributes = True


class QuizQuestionCreate(BaseModel):
    question_text: str = Field(min_length=1, max_length=1000)
    order: int = 1


class QuizQuestionUpdate(BaseModel):
    question_text: str | None = Field(default=None, min_length=1, max_length=1000)
    order: int | None = None


class QuizQuestionOut(BaseModel):
    id: int
    lesson_id: int
    question_text: str
    order: int
    options: list[QuizOptionOut] = []

    class Config:
        from_attributes = True


class QuizQuestionPublicOut(BaseModel):
    id: int
    question_text: str
    order: int
    options: list[QuizOptionPublicOut] = []

    class Config:
        from_attributes = True


class QuizSubmitIn(BaseModel):
    answers: dict[int, int]  # question_id -> selected option_id


class QuizSubmitOut(BaseModel):
    score: int
    total: int
    passed: bool
