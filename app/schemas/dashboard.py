from pydantic import BaseModel


class NextLessonOut(BaseModel):
    lesson_id: int
    title: str


class CourseProgressOut(BaseModel):
    course_id: int
    title: str
    published: bool
    total_lessons: int
    completed_lessons: int
    progress_percent: float
    next_lesson: NextLessonOut | None = None


class DashboardMeOut(BaseModel):
    student_id: int
    enrolled_courses: int
    total_lessons_completed: int
    courses: list[CourseProgressOut]
