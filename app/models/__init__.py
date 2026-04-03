from app.models.user import User
from app.models.school import School
from app.models.course import Course
from app.models.enrollment import Enrollment
from app.models.module import Module
from app.models.lesson import Lesson
from app.models.progress import Progress
from app.models.quiz import QuizQuestion, QuizOption

# ✅ ADD THIS
from app.models.class_group import ClassGroup

__all__ = [
    "User",
    "School",
    "Course",
    "Enrollment",
    "Module",
    "Lesson",
    "Progress",
    "QuizQuestion",
    "QuizOption",
    "ClassGroup",  # ✅ ADD THIS
]
