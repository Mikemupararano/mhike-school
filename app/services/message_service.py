from datetime import datetime
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.conversation import (
    Conversation,
    ConversationParticipant,
    Message,
    MessageDelivery,
)
from app.models.message_attachment import MessageAttachment
from app.models.user import User


class MessageService:
    def __init__(self, db: AsyncSession):
        self.db = db

    def hydrate_message_sender_name(self, message: Message | None) -> None:
        if message is None:
            return

        sender = getattr(message, "sender", None)

        message.sender_name = (
            getattr(sender, "full_name", None)
            or getattr(sender, "email", None)
            or "Unknown sender"
        )

        if message.reply_to:
            reply_sender = getattr(message.reply_to, "sender", None)

            message.reply_to.sender_name = (
                getattr(reply_sender, "full_name", None)
                or getattr(reply_sender, "email", None)
                or "Unknown sender"
            )

    def hydrate_conversation_sender_names(
        self,
        conversation: Conversation | None,
    ) -> None:
        if conversation is None:
            return

        for message in conversation.messages:
            self.hydrate_message_sender_name(message)

        latest_message = self.get_latest_message(conversation)

        if latest_message:
            self.hydrate_message_sender_name(latest_message)

    async def get_user_conversations(
        self,
        *,
        user_id: int,
    ) -> list[Conversation]:
        result = await self.db.execute(
            select(Conversation)
            .join(
                ConversationParticipant,
                ConversationParticipant.conversation_id == Conversation.id,
            )
            .where(
                ConversationParticipant.user_id == user_id,
            )
            .options(
                selectinload(
                    Conversation.participants,
                ).selectinload(
                    ConversationParticipant.user,
                ),
                selectinload(
                    Conversation.messages,
                ).selectinload(
                    Message.sender,
                ),
                selectinload(
                    Conversation.messages,
                )
                .selectinload(
                    Message.reply_to,
                )
                .selectinload(
                    Message.sender,
                ),
                selectinload(
                    Conversation.messages,
                ).selectinload(
                    Message.deliveries,
                ),
                selectinload(
                    Conversation.messages,
                ).selectinload(
                    Message.attachments,
                ),
            )
            .order_by(
                Conversation.updated_at.desc(),
            )
        )

        conversations = list(result.scalars().unique().all())

        for conversation in conversations:
            self.hydrate_conversation_sender_names(conversation)

            conversation.unread_count = await self.get_conversation_unread_count(
                conversation_id=conversation.id,
                user_id=user_id,
            )

            conversation.latest_message = self.get_latest_message(
                conversation,
            )

            conversation.last_activity = self.get_last_activity(
                conversation,
            )

        return conversations

    async def get_conversation_for_user(
        self,
        *,
        conversation_id: int,
        user_id: int,
    ) -> Conversation | None:
        result = await self.db.execute(
            select(Conversation)
            .join(
                ConversationParticipant,
                ConversationParticipant.conversation_id == Conversation.id,
            )
            .where(
                Conversation.id == conversation_id,
                ConversationParticipant.user_id == user_id,
            )
            .options(
                selectinload(
                    Conversation.participants,
                ).selectinload(
                    ConversationParticipant.user,
                ),
                selectinload(
                    Conversation.messages,
                ).selectinload(
                    Message.sender,
                ),
                selectinload(
                    Conversation.messages,
                )
                .selectinload(
                    Message.reply_to,
                )
                .selectinload(
                    Message.sender,
                ),
                selectinload(
                    Conversation.messages,
                ).selectinload(
                    Message.deliveries,
                ),
                selectinload(
                    Conversation.messages,
                ).selectinload(
                    Message.attachments,
                ),
            )
        )

        conversation = result.scalars().unique().first()

        if conversation:
            self.hydrate_conversation_sender_names(conversation)

            conversation.unread_count = await self.get_conversation_unread_count(
                conversation_id=conversation.id,
                user_id=user_id,
            )

            conversation.latest_message = self.get_latest_message(
                conversation,
            )

            conversation.last_activity = self.get_last_activity(
                conversation,
            )

        return conversation

    async def create_conversation(
        self,
        *,
        school_id: int | None,
        created_by_id: int,
        participant_ids: list[int],
        title: str | None,
        conversation_type: str,
    ) -> Conversation:
        unique_participant_ids = sorted(
            {
                created_by_id,
                *participant_ids,
            },
        )

        conversation = Conversation(
            school_id=school_id,
            title=title,
            conversation_type=conversation_type,
            created_by_id=created_by_id,
        )

        self.db.add(conversation)

        await self.db.flush()

        for participant_id in unique_participant_ids:
            self.db.add(
                ConversationParticipant(
                    conversation_id=conversation.id,
                    user_id=participant_id,
                )
            )

        await self.db.commit()

        return await self.get_conversation_for_user(
            conversation_id=conversation.id,
            user_id=created_by_id,
        )

    async def send_message(
        self,
        *,
        conversation_id: int,
        sender_id: int,
        body: str,
        reply_to_message_id: int | None = None,
    ) -> Message | None:
        conversation = await self.get_conversation_for_user(
            conversation_id=conversation_id,
            user_id=sender_id,
        )

        if conversation is None:
            return None

        message = Message(
            conversation_id=conversation_id,
            sender_id=sender_id,
            body=body,
            reply_to_message_id=reply_to_message_id,
        )

        self.db.add(message)

        conversation.updated_at = func.now()

        await self.db.flush()

        for participant in conversation.participants:
            if participant.user_id == sender_id:
                continue

            self.db.add(
                MessageDelivery(
                    message_id=message.id,
                    user_id=participant.user_id,
                )
            )

        await self.db.commit()

        result = await self.db.execute(
            select(Message)
            .where(
                Message.id == message.id,
            )
            .options(
                selectinload(
                    Message.sender,
                ),
                selectinload(
                    Message.reply_to,
                ).selectinload(
                    Message.sender,
                ),
                selectinload(
                    Message.deliveries,
                ),
                selectinload(
                    Message.attachments,
                ),
            )
        )

        saved_message = result.scalar_one()
        self.hydrate_message_sender_name(saved_message)

        return saved_message

    async def get_message(
        self,
        *,
        message_id: int,
    ) -> Message | None:
        result = await self.db.execute(
            select(Message)
            .where(
                Message.id == message_id,
            )
            .options(
                selectinload(
                    Message.sender,
                ),
                selectinload(
                    Message.reply_to,
                ).selectinload(
                    Message.sender,
                ),
                selectinload(
                    Message.deliveries,
                ),
                selectinload(
                    Message.attachments,
                ),
            )
        )

        message = result.scalar_one_or_none()
        self.hydrate_message_sender_name(message)

        return message

    async def attach_file_to_message(
        self,
        *,
        message_id: int,
        uploaded_by_id: int,
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

        self.db.add(attachment)

        await self.db.commit()
        await self.db.refresh(attachment)

        return attachment

    async def get_attachment(
        self,
        *,
        attachment_id: int,
    ) -> MessageAttachment | None:
        result = await self.db.execute(
            select(MessageAttachment).where(
                MessageAttachment.id == attachment_id,
            )
        )

        return result.scalar_one_or_none()

    async def mark_conversation_read(
        self,
        *,
        conversation_id: int,
        user_id: int,
    ) -> ConversationParticipant | None:
        result = await self.db.execute(
            select(ConversationParticipant).where(
                ConversationParticipant.conversation_id == conversation_id,
                ConversationParticipant.user_id == user_id,
            )
        )

        participant = result.scalar_one_or_none()

        if participant is None:
            return None

        participant.last_read_at = func.now()

        result = await self.db.execute(
            select(MessageDelivery)
            .join(
                Message,
                Message.id == MessageDelivery.message_id,
            )
            .where(
                Message.conversation_id == conversation_id,
                MessageDelivery.user_id == user_id,
                MessageDelivery.read_at.is_(None),
            )
        )

        deliveries = result.scalars().all()

        for delivery in deliveries:
            delivery.read_at = func.now()

            if delivery.delivered_at is None:
                delivery.delivered_at = func.now()

        await self.db.commit()
        await self.db.refresh(participant)

        return participant

    async def mark_message_delivered(
        self,
        *,
        message_id: int,
        user_id: int,
    ) -> MessageDelivery | None:
        result = await self.db.execute(
            select(MessageDelivery)
            .where(
                MessageDelivery.message_id == message_id,
                MessageDelivery.user_id == user_id,
            )
            .options(
                selectinload(MessageDelivery.message),
            )
        )

        delivery = result.scalar_one_or_none()

        if delivery is None:
            return None

        if delivery.delivered_at is None:
            delivery.delivered_at = func.now()

        await self.db.commit()

        result = await self.db.execute(
            select(MessageDelivery).where(
                MessageDelivery.id == delivery.id,
            )
        )

        return result.scalar_one()

    async def mark_message_read(
        self,
        *,
        message_id: int,
        user_id: int,
    ) -> MessageDelivery | None:
        result = await self.db.execute(
            select(MessageDelivery)
            .where(
                MessageDelivery.message_id == message_id,
                MessageDelivery.user_id == user_id,
            )
            .options(
                selectinload(MessageDelivery.message),
            )
        )

        delivery = result.scalar_one_or_none()

        if delivery is None:
            return None

        if delivery.delivered_at is None:
            delivery.delivered_at = func.now()

        if delivery.read_at is None:
            delivery.read_at = func.now()

        await self.db.commit()

        result = await self.db.execute(
            select(MessageDelivery).where(
                MessageDelivery.id == delivery.id,
            )
        )

        return result.scalar_one()

    async def get_conversation_unread_count(
        self,
        *,
        conversation_id: int,
        user_id: int,
    ) -> int:
        result = await self.db.execute(
            select(func.count(Message.id))
            .outerjoin(
                MessageDelivery,
                Message.id == MessageDelivery.message_id,
            )
            .where(
                Message.conversation_id == conversation_id,
                Message.sender_id != user_id,
                MessageDelivery.read_at.is_(None),
                MessageDelivery.user_id == user_id,
            )
        )

        return result.scalar_one() or 0

    async def get_unread_count(
        self,
        *,
        user_id: int,
    ) -> int:
        result = await self.db.execute(
            select(func.count(MessageDelivery.id)).where(
                MessageDelivery.user_id == user_id,
                MessageDelivery.read_at.is_(None),
            )
        )

        return result.scalar_one() or 0

    def get_latest_message(
        self,
        conversation: Conversation,
    ):
        if not conversation.messages:
            return None

        return max(
            conversation.messages,
            key=lambda message: message.created_at,
        )

    def get_last_activity(
        self,
        conversation: Conversation,
    ) -> datetime | None:
        latest_message = self.get_latest_message(conversation)

        if latest_message:
            return latest_message.created_at

        return conversation.updated_at

    async def get_school_users(
        self,
        *,
        school_id: int,
    ) -> list[User]:
        result = await self.db.execute(
            select(User)
            .where(
                User.school_id == school_id,
            )
            .order_by(
                User.full_name.asc(),
            )
        )

        return list(result.scalars().all())

    def get_message_upload_path(
        self,
        *,
        school_id: int,
    ) -> Path:
        path = Path(f"uploads/messages/{school_id}")

        path.mkdir(
            parents=True,
            exist_ok=True,
        )

        return path
