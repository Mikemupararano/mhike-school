from pydantic import BaseModel


class NotificationPreferenceUpdate(BaseModel):
    attendance_alerts_enabled: bool | None = None
    absence_notifications_enabled: bool | None = None
    persistent_absence_alerts_enabled: bool | None = None
    safeguarding_alerts_enabled: bool | None = None
    email_enabled: bool | None = None
    push_enabled: bool | None = None
    sms_enabled: bool | None = None


class NotificationPreferenceResponse(BaseModel):
    id: int
    school_id: int | None
    user_id: int
    attendance_alerts_enabled: bool
    absence_notifications_enabled: bool
    persistent_absence_alerts_enabled: bool
    safeguarding_alerts_enabled: bool
    email_enabled: bool
    push_enabled: bool
    sms_enabled: bool

    model_config = {
        "from_attributes": True,
    }
