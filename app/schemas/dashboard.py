from pydantic import BaseModel, Field

from app.models.user import UserRole


class NextLessonOut(BaseModel):
    lesson_id: int
    title: str


class CourseProgressOut(BaseModel):
    course_id: int
    title: str
    published: bool
    total_lessons: int
    completed_lessons: int
    progress_percent: int
    next_lesson: NextLessonOut | None = None


class DashboardMeOut(BaseModel):
    student_id: int
    full_name: str | None = None
    email: str

    # Legacy primary role
    role: UserRole

    # Multi-role support
    roles: list[UserRole] = Field(default_factory=list)

    is_active: bool = True
    enrolled_courses: int
    total_lessons_completed: int

    courses: list[CourseProgressOut] = Field(default_factory=list)


class SchoolAdminMetricsOut(BaseModel):
    total_users: int
    active_users: int
    teachers: int
    students: int
    school_admins: int
    classes: int
    assignments: int
