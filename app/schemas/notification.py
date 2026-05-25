from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


class NotificationCreate(BaseModel):
    school_id: int | None = None
    user_id: int | None = None
    title: str
    message: str
    category: str = "general"
    priority: str = "normal"
    email_enabled: bool = False
    push_enabled: bool = True
    sms_enabled: bool = False


class NotificationBroadcastCreate(BaseModel):
    school_id: int | None = None
    target: Literal[
        "all",
        "teachers",
        "students",
        "parents",
    ]
    title: str
    message: str
    category: str = "general"
    priority: str = "normal"
    email_enabled: bool = False
    push_enabled: bool = True
    sms_enabled: bool = False


class NotificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    school_id: int | None
    user_id: int | None
    title: str
    message: str
    category: str
    priority: str
    email_enabled: bool
    push_enabled: bool
    sms_enabled: bool
    is_read: bool
    read_at: datetime | None
    created_at: datetime
    updated_at: datetime


class NotificationDeliveryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    notification_id: int
    channel: str
    status: str
    attempts: int
    provider_message_id: str | None
    error_message: str | None
    last_attempted_at: datetime | None
    delivered_at: datetime | None
    created_at: datetime
    updated_at: datetime


class NotificationMetricsOut(BaseModel):
    total_deliveries: int
    sent_deliveries: int
    failed_deliveries: int
    pending_deliveries: int
