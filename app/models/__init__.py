from app.models.user import User
from app.models.school import School
from app.models.course import Course
from app.models.enrollment import Enrollment
from app.models.module import Module
from app.models.lesson import Lesson
from app.models.progress import Progress
from app.models.quiz import QuizQuestion, QuizOption
from app.models.class_group import ClassGroup

# ✅ NEW
from app.models.assignment import Assignment
from app.models.assignment_submission import AssignmentSubmission


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
    "ClassGroup",
    # ✅ NEW
    "Assignment",
    "AssignmentSubmission",
]
