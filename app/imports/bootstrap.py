from __future__ import annotations

from app.imports.processors.classes import process_class_row
from app.imports.processors.courses import process_course_row
from app.imports.processors.enrollments import process_enrollment_row
from app.imports.processors.parents import process_parent_row
from app.imports.processors.students import process_student_row
from app.imports.processors.teachers import process_teacher_row
from app.imports.processors.timetable_periods import (
    process_timetable_period_row,
)
from app.imports.processors.timetables import process_timetable_row
from app.imports.registry import (
    is_registered,
    register_import_handler,
)
from app.imports.validators.classes import validate_class_row
from app.imports.validators.courses import validate_course_row
from app.imports.validators.enrollments import validate_enrollment_row
from app.imports.validators.parents import validate_parent_row
from app.imports.validators.students import validate_student_row
from app.imports.validators.teachers import validate_teacher_row
from app.imports.validators.timetable_periods import (
    validate_timetable_period_row,
)
from app.imports.validators.timetables import validate_timetable_row

STUDENT_IMPORT_TYPE = "students"
TEACHER_IMPORT_TYPE = "teachers"
CLASS_IMPORT_TYPE = "classes"
COURSE_IMPORT_TYPE = "courses"
ENROLLMENT_IMPORT_TYPE = "enrollments"
PARENT_IMPORT_TYPE = "parents"
TIMETABLE_PERIOD_IMPORT_TYPE = "timetable_periods"
TIMETABLE_IMPORT_TYPE = "timetables"


def register_import_handlers() -> None:
    """
    Register every built-in import handler.

    This function is intentionally idempotent so it can be called safely by:

    - FastAPI startup;
    - Celery workers;
    - background import tasks;
    - unit tests.

    Existing handlers are preserved and are not registered twice.
    """

    handlers = (
        (
            STUDENT_IMPORT_TYPE,
            validate_student_row,
            process_student_row,
        ),
        (
            TEACHER_IMPORT_TYPE,
            validate_teacher_row,
            process_teacher_row,
        ),
        (
            CLASS_IMPORT_TYPE,
            validate_class_row,
            process_class_row,
        ),
        (
            COURSE_IMPORT_TYPE,
            validate_course_row,
            process_course_row,
        ),
        (
            ENROLLMENT_IMPORT_TYPE,
            validate_enrollment_row,
            process_enrollment_row,
        ),
        (
            PARENT_IMPORT_TYPE,
            validate_parent_row,
            process_parent_row,
        ),
        (
            TIMETABLE_PERIOD_IMPORT_TYPE,
            validate_timetable_period_row,
            process_timetable_period_row,
        ),
        (
            TIMETABLE_IMPORT_TYPE,
            validate_timetable_row,
            process_timetable_row,
        ),
    )

    for import_type, validator, processor in handlers:
        if is_registered(import_type):
            continue

        register_import_handler(
            import_type,
            validator=validator,
            processor=processor,
        )
