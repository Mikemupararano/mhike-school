from app.models.user import User
from app.models.school import School

from app.models.course import Course
from app.models.enrollment import Enrollment
from app.models.module import Module
from app.models.lesson import Lesson
from app.models.progress import Progress

# Quiz models (adjust if filenames differ)
from app.models.quiz import QuizQuestion, QuizOption

# Optional (if you already have these models)
# from app.models.announcement import Announcement
# from app.models.assignment import Assignment


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
]
