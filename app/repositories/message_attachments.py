from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.message_attachment import MessageAttachment


async def create_message_attachment(
    db: AsyncSession,
    *,
    message_id: int,
    uploaded_by_id: int | None,
    filename: str,
    original_filename: str,
    mime_type: str,
    file_size: int,
    storage_path: str,
) -> MessageAttachment:
    attachment = MessageAttachment(
        message_id=message_id,
        uploaded_by_id=uploaded_by_id,
        filename=filename,
        original_filename=original_filename,
        mime_type=mime_type,
        file_size=file_size,
        storage_path=storage_path,
    )

    db.add(attachment)
    await db.commit()
    await db.refresh(attachment)

    return attachment


async def get_message_attachment(
    db: AsyncSession,
    *,
    attachment_id: int,
) -> MessageAttachment | None:
    result = await db.execute(
        select(MessageAttachment).where(
            MessageAttachment.id == attachment_id,
        ),
    )

    return result.scalar_one_or_none()


async def list_message_attachments(
    db: AsyncSession,
    *,
    message_id: int,
) -> list[MessageAttachment]:
    result = await db.execute(
        select(MessageAttachment)
        .where(MessageAttachment.message_id == message_id)
        .order_by(MessageAttachment.created_at.asc()),
    )

    return list(result.scalars().all())


async def delete_message_attachment(
    db: AsyncSession,
    *,
    attachment: MessageAttachment,
) -> None:
    await db.delete(attachment)
    await db.commit()
