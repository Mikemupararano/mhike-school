from __future__ import annotations

from app.imports.processors.students import process_student_row
from app.imports.processors.teachers import process_teacher_row
from app.imports.registry import (
    is_registered,
    register_import_handler,
)
from app.imports.validators.students import validate_student_row
from app.imports.validators.teachers import validate_teacher_row

STUDENT_IMPORT_TYPE = "students"
TEACHER_IMPORT_TYPE = "teachers"


def register_import_handlers() -> None:
    """
    Register every built-in import handler.

    This function is idempotent so it can be called safely by the API,
    Celery workers and tests without registering handlers twice.
    """

    if not is_registered(STUDENT_IMPORT_TYPE):
        register_import_handler(
            STUDENT_IMPORT_TYPE,
            validator=validate_student_row,
            processor=process_student_row,
        )

    if not is_registered(TEACHER_IMPORT_TYPE):
        register_import_handler(
            TEACHER_IMPORT_TYPE,
            validator=validate_teacher_row,
            processor=process_teacher_row,
        )
