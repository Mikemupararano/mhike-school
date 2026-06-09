from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.repositories.message_attachments import (
    delete_message_attachment,
    get_message_attachment,
    list_message_attachments,
)
from app.schemas.message import MessageAttachmentOut

router = APIRouter()


@router.get(
    "/messages/{message_id}/attachments",
    response_model=list[MessageAttachmentOut],
)
async def list_message_attachments_endpoint(
    message_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[MessageAttachmentOut]:
    _ = current_user

    return await list_message_attachments(
        db,
        message_id=message_id,
    )


@router.get(
    "/{attachment_id}",
    response_model=MessageAttachmentOut,
)
async def get_message_attachment_endpoint(
    attachment_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MessageAttachmentOut:
    _ = current_user

    attachment = await get_message_attachment(
        db,
        attachment_id=attachment_id,
    )

    if attachment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message attachment not found.",
        )

    return attachment


@router.get(
    "/{attachment_id}/download",
)
async def download_message_attachment_endpoint(
    attachment_id: int,
    db: AsyncSession = Depends(get_db),
) -> FileResponse:
    attachment = await get_message_attachment(
        db,
        attachment_id=attachment_id,
    )

    if attachment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message attachment not found.",
        )

    file_path = Path(attachment.storage_path)

    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Attachment file not found on disk.",
        )

    return FileResponse(
        path=file_path,
        media_type=attachment.mime_type,
        filename=attachment.original_filename or attachment.filename,
    )


@router.delete(
    "/{attachment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_message_attachment_endpoint(
    attachment_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    _ = current_user

    attachment = await get_message_attachment(
        db,
        attachment_id=attachment_id,
    )

    if attachment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message attachment not found.",
        )

    await delete_message_attachment(
        db,
        attachment=attachment,
    )
