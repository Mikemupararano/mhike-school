from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class NotificationPreferenceBase(BaseModel):
    attendance_alerts_enabled: bool = True
    absence_notifications_enabled: bool = True
    persistent_absence_alerts_enabled: bool = True
    safeguarding_alerts_enabled: bool = True

    email_enabled: bool = True
    push_enabled: bool = False
    sms_enabled: bool = False


class NotificationPreferenceUpdate(NotificationPreferenceBase):
    pass


class NotificationPreferenceCreate(NotificationPreferenceBase):
    school_id: int
    user_id: int


class NotificationPreferenceOut(NotificationPreferenceBase):
    id: int
    school_id: int
    user_id: int

    model_config = ConfigDict(from_attributes=True)
