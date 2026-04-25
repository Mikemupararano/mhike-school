from pydantic import BaseModel


class TeacherDashboardOut(BaseModel):
    teacher_id: int
    total_courses: int
    total_students: int
    total_assignments: int
    pending_submissions: int
