import { apiGet, apiPost } from "@/lib/api";
import type {
    Conversation,
    ConversationCreatePayload,
    Message,
    MessageCreatePayload,
    SchoolMessageUser,
} from "@/types/message";

export async function getSchoolMessageUsers(): Promise<SchoolMessageUser[]> {
    return apiGet<SchoolMessageUser[]>("/messages/school-users");
}

export async function getConversations(): Promise<Conversation[]> {
    return apiGet<Conversation[]>("/messages/conversations");
}

export async function getConversation(
    conversationId: number | string,
): Promise<Conversation> {
    return apiGet<Conversation>(
        `/messages/conversations/${conversationId}`,
    );
}

export async function createConversation(
    payload: ConversationCreatePayload,
): Promise<Conversation> {
    return apiPost<Conversation>(
        "/messages/conversations",
        payload,
    );
}

export async function sendMessage(
    conversationId: number | string,
    payload: MessageCreatePayload,
): Promise<Message> {
    return apiPost<Message>(
        `/messages/conversations/${conversationId}/messages`,
        payload,
    );
}