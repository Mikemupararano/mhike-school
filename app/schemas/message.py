from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, computed_field


class ConversationCreate(BaseModel):
    participant_ids: list[int]
    title: str | None = None
    conversation_type: str = "direct"


class ConversationParticipantUserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str
    email: str
    role: str


class ConversationParticipantOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    conversation_id: int | None = None
    joined_at: datetime
    last_read_at: datetime | None = None
    user: ConversationParticipantUserOut | None = None


class MessageCreate(BaseModel):
    body: str
    reply_to_message_id: int | None = None


class MessageReplyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    sender_id: int | None
    sender_name: str | None = None
    body: str
    created_at: datetime


class MessageDeliveryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    message_id: int
    user_id: int
    delivered_at: datetime | None = None
    read_at: datetime | None = None


class MessageAttachmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    message_id: int
    uploaded_by_id: int | None = None
    filename: str
    original_filename: str
    mime_type: str
    file_size: int
    storage_path: str
    created_at: datetime

    @computed_field
    @property
    def is_image(self) -> bool:
        return self.mime_type.startswith("image/")

    @computed_field
    @property
    def download_url(self) -> str:
        return f"/api/v1/message-attachments/{self.id}/download"


class MessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    conversation_id: int
    sender_id: int | None
    sender_name: str | None = None

    reply_to_message_id: int | None = None
    reply_to: MessageReplyOut | None = None

    body: str

    created_at: datetime
    updated_at: datetime | None = None

    deliveries: list[MessageDeliveryOut] = Field(default_factory=list)

    attachments: list[MessageAttachmentOut] = Field(default_factory=list)


class ConversationLatestMessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    body: str
    sender_id: int | None = None
    sender_name: str | None = None
    created_at: datetime


class ConversationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    school_id: int | None
    title: str | None
    conversation_type: str
    created_by_id: int | None

    created_at: datetime
    updated_at: datetime | None = None

    participants: list[ConversationParticipantOut] = Field(default_factory=list)
    messages: list[MessageOut] = Field(default_factory=list)

    unread_count: int = 0
    latest_message: ConversationLatestMessageOut | None = None
    last_activity: datetime | None = None


class MarkConversationReadOut(BaseModel):
    success: bool
    conversation_id: int
    user_id: int
    last_read_at: datetime | None = None


class UnreadMessageCountOut(BaseModel):
    unread_count: int


class MessageAttachmentCreateOut(BaseModel):
    success: bool
    attachment: MessageAttachmentOut


class MessageAttachmentDownloadOut(BaseModel):
    id: int
    filename: str
    original_filename: str
    mime_type: str
    file_size: int
    storage_path: str

    @computed_field
    @property
    def is_image(self) -> bool:
        return self.mime_type.startswith("image/")

    @computed_field
    @property
    def download_url(self) -> str:
        return f"/api/v1/message-attachments/{self.id}/download"
