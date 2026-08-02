from __future__ import annotations

from app.imports.processors.classes import process_class_row
from app.imports.processors.students import process_student_row
from app.imports.processors.teachers import process_teacher_row
from app.imports.registry import (
    is_registered,
    register_import_handler,
)
from app.imports.validators.classes import validate_class_row
from app.imports.validators.students import validate_student_row
from app.imports.validators.teachers import validate_teacher_row

STUDENT_IMPORT_TYPE = "students"
TEACHER_IMPORT_TYPE = "teachers"
CLASS_IMPORT_TYPE = "classes"


def register_import_handlers() -> None:
    """
    Register every built-in import handler.

    This function is intentionally idempotent so it can be called safely by:

    - FastAPI startup
    - Celery workers
    - Background import tasks
    - Unit tests

    without registering handlers multiple times.
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
    )

    for import_type, validator, processor in handlers:
        if is_registered(import_type):
            continue

        register_import_handler(
            import_type,
            validator=validator,
            processor=processor,
        )
