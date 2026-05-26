from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.conversation import (
    Conversation,
    ConversationParticipant,
    Message,
)
from app.models.user import User


class MessageService:
    def __init__(self, db: AsyncSession):
        self.db = db

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
                selectinload(Conversation.participants),
                selectinload(Conversation.messages),
            )
            .order_by(Conversation.updated_at.desc())
        )

        return list(result.scalars().unique().all())

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
                selectinload(Conversation.participants),
                selectinload(Conversation.messages),
            )
        )

        return result.scalars().unique().first()

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
            set(
                [
                    created_by_id,
                    *participant_ids,
                ],
            ),
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
            participant = ConversationParticipant(
                conversation_id=conversation.id,
                user_id=participant_id,
            )

            self.db.add(participant)

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
        )

        self.db.add(message)

        conversation.updated_at = message.created_at

        await self.db.commit()

        await self.db.refresh(message)

        return message

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

        from sqlalchemy import func

        participant.last_read_at = func.now()

        await self.db.commit()
        await self.db.refresh(participant)

        return participant

    async def get_school_users(
        self,
        *,
        school_id: int,
    ) -> list[User]:
        result = await self.db.execute(
            select(User)
            .where(User.school_id == school_id)
            .order_by(User.full_name.asc())
        )

        return list(result.scalars().all())
