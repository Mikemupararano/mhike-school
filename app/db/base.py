from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


# =========================================================
# ATTENDANCE MODELS
# =========================================================

from app.models.absence_request import (  # noqa: E402, F401
    AbsenceRequest,
)
from app.models.attendance_record import (  # noqa: E402, F401
    AttendanceRecord,
)
from app.models.attendance_session import (  # noqa: E402, F401
    AttendanceSession,
)

# =========================================================
# IMPORT MODELS
# =========================================================

from app.models.import_batch import (  # noqa: E402, F401
    ImportBatch,
    ImportOperation,
    ImportRow,
    ImportRowStatus,
    ImportStatus,
)

# =========================================================
# TIMETABLE MODELS
# =========================================================

from app.models.timetable import Timetable  # noqa: E402, F401
from app.models.timetable_assignment import (  # noqa: E402, F401
    TimetableAssignment,
)
from app.models.timetable_entry import (  # noqa: E402, F401
    TimetableEntry,
)
from app.models.timetable_period import (  # noqa: E402, F401
    TimetablePeriod,
)

# =========================================================
# MESSAGING MODELS
# =========================================================

from app.models.conversation import (  # noqa: E402, F401
    Conversation,
    ConversationParticipant,
    Message,
)
