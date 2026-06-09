from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.core.socket_manager import (
    emit_conversation_message,
    emit_message_delivered,
    emit_message_read,
)
from app.models.user import User
from app.schemas.message import (
    ConversationCreate,
    ConversationOut,
    MarkConversationReadOut,
    MessageAttachmentCreateOut,
    MessageAttachmentDownloadOut,
    MessageAttachmentOut,
    MessageCreate,
    MessageDeliveryOut,
    MessageOut,
    UnreadMessageCountOut,
)
from app.services.message_service import MessageService

router = APIRouter()


@router.get("/school-users")
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
    users = await service.get_school_users(school_id=current_user.school_id)

    return [
        {
            "id": user.id,
            "full_name": user.full_name,
            "email": user.email,
            "role": user.role,
        }
        for user in users
    ]


@router.get("/unread-count", response_model=UnreadMessageCountOut)
async def get_unread_count(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UnreadMessageCountOut:
    service = MessageService(db)
    unread_count = await service.get_unread_count(user_id=current_user.id)

    return UnreadMessageCountOut(unread_count=unread_count)


@router.get("/conversations", response_model=list[ConversationOut])
async def get_my_conversations(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ConversationOut]:
    service = MessageService(db)

    return await service.get_user_conversations(user_id=current_user.id)


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

    if payload.reply_to_message_id is not None:
        reply_target = next(
            (
                message
                for message in conversation.messages
                if message.id == payload.reply_to_message_id
            ),
            None,
        )

        if reply_target is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Reply target message is not in this conversation.",
            )

    message = await service.send_message(
        conversation_id=conversation_id,
        sender_id=current_user.id,
        body=payload.body,
        reply_to_message_id=payload.reply_to_message_id,
    )

    if message is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unable to send message.",
        )

    message_out = MessageOut.model_validate(message)

    await emit_conversation_message(
        conversation_id=conversation_id,
        payload=message_out.model_dump(mode="json"),
    )

    return message_out


@router.post(
    "/messages/upload",
    response_model=MessageAttachmentOut,
)
async def upload_message_file(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MessageAttachmentOut:
    _ = db

    if current_user.school_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not assigned to a school.",
        )

    service = MessageService(db)
    upload_dir = service.get_message_upload_path(school_id=current_user.school_id)

    extension = Path(file.filename or "").suffix
    generated_name = f"{uuid4().hex}{extension}"
    destination = upload_dir / generated_name

    contents = await file.read()
    destination.write_bytes(contents)

    return MessageAttachmentOut(
        id=0,
        message_id=0,
        uploaded_by_id=current_user.id,
        filename=generated_name,
        original_filename=file.filename or generated_name,
        mime_type=file.content_type or "application/octet-stream",
        file_size=len(contents),
        storage_path=str(destination),
        created_at=datetime.now(UTC),
    )


@router.post(
    "/messages/{message_id}/attachments",
    response_model=MessageAttachmentCreateOut,
)
async def attach_file_to_message(
    message_id: int,
    payload: MessageAttachmentOut,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MessageAttachmentCreateOut:
    service = MessageService(db)

    message = await service.get_message(message_id=message_id)

    if message is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message not found.",
        )

    attachment = await service.attach_file_to_message(
        message_id=message_id,
        uploaded_by_id=current_user.id,
        filename=payload.filename,
        original_filename=payload.original_filename,
        mime_type=payload.mime_type,
        file_size=payload.file_size,
        storage_path=payload.storage_path,
    )

    await emit_conversation_message(
        conversation_id=message.conversation_id,
        payload=MessageOut.model_validate(
            await service.get_message(message_id=message_id),
        ).model_dump(mode="json"),
    )

    return MessageAttachmentCreateOut(
        success=True,
        attachment=MessageAttachmentOut.model_validate(attachment),
    )


@router.get(
    "/attachments/{attachment_id}",
    response_model=MessageAttachmentDownloadOut,
)
async def get_attachment(
    attachment_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MessageAttachmentDownloadOut:
    _ = current_user

    service = MessageService(db)
    attachment = await service.get_attachment(attachment_id=attachment_id)

    if attachment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Attachment not found.",
        )

    return MessageAttachmentDownloadOut(
        id=attachment.id,
        filename=attachment.filename,
        original_filename=attachment.original_filename,
        mime_type=attachment.mime_type,
        file_size=attachment.file_size,
        storage_path=attachment.storage_path,
    )


@router.get("/attachments/{attachment_id}/download")
async def download_attachment(
    attachment_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FileResponse:
    _ = current_user

    service = MessageService(db)
    attachment = await service.get_attachment(attachment_id=attachment_id)

    if attachment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Attachment not found.",
        )

    file_path = Path(attachment.storage_path)

    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Attachment file not found on disk.",
        )

    return FileResponse(
        file_path,
        filename=attachment.original_filename,
        media_type=attachment.mime_type,
    )


@router.post(
    "/messages/{message_id}/delivered",
    response_model=MessageDeliveryOut,
)
async def mark_message_delivered(
    message_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MessageDeliveryOut:
    service = MessageService(db)

    delivery = await service.mark_message_delivered(
        message_id=message_id,
        user_id=current_user.id,
    )

    if delivery is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message delivery record not found.",
        )

    delivery_out = MessageDeliveryOut.model_validate(delivery)

    await emit_message_delivered(
        conversation_id=delivery.message.conversation_id,
        payload=delivery_out.model_dump(mode="json"),
    )

    return delivery_out


@router.post(
    "/messages/{message_id}/read",
    response_model=MessageDeliveryOut,
)
async def mark_message_read(
    message_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MessageDeliveryOut:
    service = MessageService(db)

    delivery = await service.mark_message_read(
        message_id=message_id,
        user_id=current_user.id,
    )

    if delivery is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message delivery record not found.",
        )

    delivery_out = MessageDeliveryOut.model_validate(delivery)

    await emit_message_read(
        conversation_id=delivery.message.conversation_id,
        payload=delivery_out.model_dump(mode="json"),
    )

    return delivery_out


@router.post(
    "/conversations/{conversation_id}/read",
    response_model=MarkConversationReadOut,
)
async def mark_conversation_read(
    conversation_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MarkConversationReadOut:
    service = MessageService(db)

    participant = await service.mark_conversation_read(
        conversation_id=conversation_id,
        user_id=current_user.id,
    )

    if participant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation participant not found.",
        )

    return MarkConversationReadOut(
        success=True,
        conversation_id=conversation_id,
        user_id=current_user.id,
        last_read_at=participant.last_read_at,
    )
