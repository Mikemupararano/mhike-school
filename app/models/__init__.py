from app.models.assignment import Assignment
from app.models.assignment_submission import AssignmentSubmission
from app.models.audit_log import AuditLog  # ✅ ADD THIS
from app.models.class_group import ClassGroup
from app.models.course import Course
from app.models.enrollment import Enrollment
from app.models.lesson import Lesson
from app.models.module import Module
from app.models.progress import Progress
from app.models.quiz import QuizQuestion, QuizOption
from app.models.school import School
from app.models.user import User, UserRole, UserStatus
from app.models.user_role import UserRoleAssignment


__all__ = [
    "Assignment",
    "AssignmentSubmission",
    "AuditLog",  # ✅ ADD THIS
    "ClassGroup",
    "Course",
    "Enrollment",
    "Lesson",
    "Module",
    "Progress",
    "QuizQuestion",
    "QuizOption",
    "School",
    "User",
    "UserRole",
    "UserStatus",
    "UserRoleAssignment",
]
