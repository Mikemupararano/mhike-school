from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


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
    joined_at: datetime
    last_read_at: datetime | None = None
    user: ConversationParticipantUserOut | None = None


class MessageCreate(BaseModel):
    body: str


class MessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    conversation_id: int
    sender_id: int | None
    body: str
    created_at: datetime
    updated_at: datetime


class ConversationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    school_id: int | None
    title: str | None
    conversation_type: str
    created_by_id: int | None
    created_at: datetime
    updated_at: datetime
    participants: list[ConversationParticipantOut] = Field(
        default_factory=list,
    )
    messages: list[MessageOut] = Field(
        default_factory=list,
    )
