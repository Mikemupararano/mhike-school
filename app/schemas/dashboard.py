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
    progress_percent: int  # ✅ use int for UI consistency
    next_lesson: NextLessonOut | None = None


class DashboardMeOut(BaseModel):
    student_id: int
    full_name: str | None = None
    email: str
    role: str
    is_active: bool = True
    enrolled_courses: int
    total_lessons_completed: int
    courses: list[CourseProgressOut] = []  # ✅ default prevents None issues
