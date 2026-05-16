from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


# Import models so SQLAlchemy/Alembic can discover metadata.
from app.models.absence_request import AbsenceRequest  # noqa: E402, F401
from app.models.attendance_record import AttendanceRecord  # noqa: E402, F401
from app.models.attendance_session import AttendanceSession  # noqa: E402, F401
