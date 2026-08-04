from __future__ import annotations

from app.imports.processors.assignment_submissions import (
    process_assignment_submission_row,
)
from app.imports.processors.assignments import process_assignment_row
from app.imports.processors.attendance import process_attendance_row
from app.imports.processors.classes import process_class_row
from app.imports.processors.courses import process_course_row
from app.imports.processors.enrollments import process_enrollment_row
from app.imports.processors.parents import process_parent_row
from app.imports.processors.students import process_student_row
from app.imports.processors.teachers import process_teacher_row
from app.imports.processors.timetable_assignments import (
    process_timetable_assignment_row,
)
from app.imports.processors.timetable_entries import (
    process_timetable_entry_row,
)
from app.imports.processors.timetable_periods import (
    process_timetable_period_row,
)
from app.imports.processors.timetables import process_timetable_row
from app.imports.registry import (
    ImportHandler,
    is_registered,
    register_import_handler,
)
from app.imports.validators.assignment_submissions import (
    AssignmentSubmissionImportSchema,
    validate_assignment_submission_row,
)
from app.imports.validators.assignments import (
    AssignmentImportSchema,
    validate_assignment_row,
)
from app.imports.validators.attendance import (
    AttendanceImportSchema,
    validate_attendance_row,
)
from app.imports.validators.classes import (
    ClassImportSchema,
    validate_class_row,
)
from app.imports.validators.courses import (
    CourseImportSchema,
    validate_course_row,
)
from app.imports.validators.enrollments import (
    EnrollmentImportSchema,
    validate_enrollment_row,
)
from app.imports.validators.parents import (
    ParentImportSchema,
    validate_parent_row,
)
from app.imports.validators.students import (
    StudentImportSchema,
    validate_student_row,
)
from app.imports.validators.teachers import (
    TeacherImportSchema,
    validate_teacher_row,
)
from app.imports.validators.timetable_assignments import (
    TimetableAssignmentImportSchema,
    validate_timetable_assignment_row,
)
from app.imports.validators.timetable_entries import (
    TimetableEntryImportSchema,
    validate_timetable_entry_row,
)
from app.imports.validators.timetable_periods import (
    TimetablePeriodImportSchema,
    validate_timetable_period_row,
)
from app.imports.validators.timetables import (
    TimetableImportSchema,
    validate_timetable_row,
)

STUDENT_IMPORT_TYPE = "students"
TEACHER_IMPORT_TYPE = "teachers"
CLASS_IMPORT_TYPE = "classes"
COURSE_IMPORT_TYPE = "courses"
ENROLLMENT_IMPORT_TYPE = "enrollments"
PARENT_IMPORT_TYPE = "parents"
TIMETABLE_PERIOD_IMPORT_TYPE = "timetable_periods"
TIMETABLE_IMPORT_TYPE = "timetables"
TIMETABLE_ENTRY_IMPORT_TYPE = "timetable_entries"
TIMETABLE_ASSIGNMENT_IMPORT_TYPE = "timetable_assignments"
ASSIGNMENT_IMPORT_TYPE = "assignments"
ASSIGNMENT_SUBMISSION_IMPORT_TYPE = "assignment_submissions"
ATTENDANCE_IMPORT_TYPE = "attendance"


BUILT_IN_IMPORT_HANDLERS: tuple[ImportHandler, ...] = (
    ImportHandler(
        import_type=STUDENT_IMPORT_TYPE,
        validator=validate_student_row,
        processor=process_student_row,
        schema=StudentImportSchema,
        display_name="Students",
        description=(
            "Import student records into the current school, including "
            "identity, contact and enrolment-related information."
        ),
        sample_row={},
    ),
    ImportHandler(
        import_type=TEACHER_IMPORT_TYPE,
        validator=validate_teacher_row,
        processor=process_teacher_row,
        schema=TeacherImportSchema,
        display_name="Teachers",
        description=("Import teaching staff records into the current school."),
        sample_row={},
    ),
    ImportHandler(
        import_type=CLASS_IMPORT_TYPE,
        validator=validate_class_row,
        processor=process_class_row,
        schema=ClassImportSchema,
        display_name="Classes",
        description=("Import school classes and their identifying information."),
        sample_row={},
    ),
    ImportHandler(
        import_type=COURSE_IMPORT_TYPE,
        validator=validate_course_row,
        processor=process_course_row,
        schema=CourseImportSchema,
        display_name="Courses",
        description=("Import courses and subject offerings for the current school."),
        sample_row={},
    ),
    ImportHandler(
        import_type=ENROLLMENT_IMPORT_TYPE,
        validator=validate_enrollment_row,
        processor=process_enrollment_row,
        schema=EnrollmentImportSchema,
        display_name="Enrolments",
        description=(
            "Import student enrolments that associate students with classes "
            "or courses."
        ),
        sample_row={},
    ),
    ImportHandler(
        import_type=PARENT_IMPORT_TYPE,
        validator=validate_parent_row,
        processor=process_parent_row,
        schema=ParentImportSchema,
        display_name="Parents",
        description=(
            "Import parent and guardian records and their student " "relationships."
        ),
        sample_row={},
    ),
    ImportHandler(
        import_type=TIMETABLE_PERIOD_IMPORT_TYPE,
        validator=validate_timetable_period_row,
        processor=process_timetable_period_row,
        schema=TimetablePeriodImportSchema,
        display_name="Timetable Periods",
        description=("Import the named teaching periods used by school timetables."),
        sample_row={},
    ),
    ImportHandler(
        import_type=TIMETABLE_IMPORT_TYPE,
        validator=validate_timetable_row,
        processor=process_timetable_row,
        schema=TimetableImportSchema,
        display_name="Timetables",
        description=("Import timetable definitions for the current school."),
        sample_row={},
    ),
    ImportHandler(
        import_type=TIMETABLE_ENTRY_IMPORT_TYPE,
        validator=validate_timetable_entry_row,
        processor=process_timetable_entry_row,
        schema=TimetableEntryImportSchema,
        display_name="Timetable Entries",
        description=(
            "Import scheduled timetable entries linking periods, classes, "
            "courses and teaching activities."
        ),
        sample_row={},
    ),
    ImportHandler(
        import_type=TIMETABLE_ASSIGNMENT_IMPORT_TYPE,
        validator=validate_timetable_assignment_row,
        processor=process_timetable_assignment_row,
        schema=TimetableAssignmentImportSchema,
        display_name="Timetable Assignments",
        description=(
            "Import teacher, room or class assignments associated with "
            "timetable entries."
        ),
        sample_row={},
    ),
    ImportHandler(
        import_type=ASSIGNMENT_IMPORT_TYPE,
        validator=validate_assignment_row,
        processor=process_assignment_row,
        schema=AssignmentImportSchema,
        display_name="Assignments",
        description=("Import coursework, homework and other student assignments."),
        sample_row={},
    ),
    ImportHandler(
        import_type=ASSIGNMENT_SUBMISSION_IMPORT_TYPE,
        validator=validate_assignment_submission_row,
        processor=process_assignment_submission_row,
        schema=AssignmentSubmissionImportSchema,
        display_name="Assignment Submissions",
        description=(
            "Import student submissions, marks and completion information "
            "for existing assignments."
        ),
        sample_row={},
    ),
    ImportHandler(
        import_type=ATTENDANCE_IMPORT_TYPE,
        validator=validate_attendance_row,
        processor=process_attendance_row,
        schema=AttendanceImportSchema,
        display_name="Attendance",
        description=(
            "Import student attendance records for lessons, sessions or " "school days."
        ),
        sample_row={},
    ),
)


def register_import_handlers() -> None:
    """
    Register every built-in import handler.

    This function is intentionally idempotent so it can be called safely by:

    - FastAPI startup;
    - Celery workers;
    - background import tasks;
    - unit tests.

    Existing handlers are preserved and are not registered twice.

    Pydantic schemas remain the authoritative source for field names, field
    order, required and optional status, types, defaults, descriptions and
    validation constraints. Presentation metadata is registered alongside
    each validator and processor so API clients can discover every supported
    import capability from the registry.
    """

    for handler in BUILT_IN_IMPORT_HANDLERS:
        if is_registered(handler.import_type):
            continue

        register_import_handler(
            handler.import_type,
            validator=handler.validator,
            processor=handler.processor,
            schema=handler.schema,
            display_name=handler.display_name,
            description=handler.description,
            sample_row=handler.sample_row,
        )
