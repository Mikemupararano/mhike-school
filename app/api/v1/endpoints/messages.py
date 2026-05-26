from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.message import (
    ConversationCreate,
    ConversationOut,
    MessageCreate,
    MessageOut,
)
from app.services.message_service import MessageService

router = APIRouter()


@router.get(
    "/school-users",
)
async def get_school_users(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.school_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not assigned to a school.",
        )

    service = MessageService(db)

    users = await service.get_school_users(
        school_id=current_user.school_id,
    )

    return [
        {
            "id": user.id,
            "full_name": user.full_name,
            "email": user.email,
            "role": user.role,
        }
        for user in users
    ]


@router.get(
    "/conversations",
    response_model=list[ConversationOut],
)
async def get_my_conversations(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ConversationOut]:
    service = MessageService(db)

    return await service.get_user_conversations(
        user_id=current_user.id,
    )


@router.post(
    "/conversations",
    response_model=ConversationOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_conversation(
    payload: ConversationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ConversationOut:
    if current_user.school_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not assigned to a school.",
        )

    service = MessageService(db)

    conversation = await service.create_conversation(
        school_id=current_user.school_id,
        created_by_id=current_user.id,
        participant_ids=payload.participant_ids,
        title=payload.title,
        conversation_type=payload.conversation_type,
    )

    if conversation is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unable to create conversation.",
        )

    return conversation


@router.get(
    "/conversations/{conversation_id}",
    response_model=ConversationOut,
)
async def get_conversation(
    conversation_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ConversationOut:
    service = MessageService(db)

    conversation = await service.get_conversation_for_user(
        conversation_id=conversation_id,
        user_id=current_user.id,
    )

    if conversation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found.",
        )

    return conversation


@router.post(
    "/conversations/{conversation_id}/messages",
    response_model=MessageOut,
)
async def send_message(
    conversation_id: int,
    payload: MessageCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MessageOut:
    service = MessageService(db)

    conversation = await service.get_conversation_for_user(
        conversation_id=conversation_id,
        user_id=current_user.id,
    )

    if conversation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found.",
        )

    message = await service.send_message(
        conversation_id=conversation_id,
        sender_id=current_user.id,
        body=payload.body,
    )

    if message is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unable to send message.",
        )

    return message
