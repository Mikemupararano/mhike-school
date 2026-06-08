import {
    API_BASE_URL,
    apiGet,
    apiPost,
    apiPostForm,
    getToken,
} from "@/lib/api";

import type {
    Conversation,
    ConversationCreatePayload,
    MarkConversationReadResponse,
    Message,
    MessageAttachment,
    MessageAttachmentCreateResponse,
    MessageAttachmentDownload,
    MessageAttachmentUploadResponse,
    MessageCreatePayload,
    MessageDelivery,
    SchoolMessageUser,
    UnreadMessageCountResponse,
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

export async function markMessageDelivered(
    messageId: number | string,
): Promise<MessageDelivery> {
    return apiPost<MessageDelivery>(
        `/messages/messages/${messageId}/delivered`,
    );
}

export async function markMessageRead(
    messageId: number | string,
): Promise<MessageDelivery> {
    return apiPost<MessageDelivery>(
        `/messages/messages/${messageId}/read`,
    );
}

export async function markConversationRead(
    conversationId: number | string,
): Promise<MarkConversationReadResponse> {
    return apiPost<MarkConversationReadResponse>(
        `/messages/conversations/${conversationId}/read`,
    );
}

export async function getUnreadMessageCount(): Promise<UnreadMessageCountResponse> {
    return apiGet<UnreadMessageCountResponse>(
        "/messages/unread-count",
    );
}

export async function uploadMessageFile(
    file: File,
): Promise<MessageAttachmentUploadResponse> {
    const formData = new FormData();

    formData.append("file", file);

    return apiPostForm<MessageAttachmentUploadResponse>(
        "/messages/messages/upload",
        formData,
    );
}

export async function attachFileToMessage(
    messageId: number | string,
    payload: MessageAttachmentUploadResponse,
): Promise<MessageAttachmentCreateResponse> {
    return apiPost<MessageAttachmentCreateResponse>(
        `/messages/messages/${messageId}/attachments`,
        payload,
    );
}

export async function getMessageAttachments(
    messageId: number | string,
): Promise<MessageAttachment[]> {
    return apiGet<MessageAttachment[]>(
        `/message-attachments/messages/${messageId}/attachments`,
    );
}

export async function getAttachment(
    attachmentId: number | string,
): Promise<MessageAttachmentDownload> {
    return apiGet<MessageAttachmentDownload>(
        `/message-attachments/${attachmentId}`,
    );
}

export function getAttachmentDownloadUrl(
    attachmentId: number | string,
): string {
    const base = API_BASE_URL.replace(/\/+$/, "");

    return `${base}/message-attachments/${attachmentId}/download`;
}

export async function downloadAttachment(
    attachment: MessageAttachment,
): Promise<void> {
    const token = getToken();

    const response = await fetch(
        getAttachmentDownloadUrl(attachment.id),
        {
            method: "GET",
            headers: {
                ...(token
                    ? {
                        Authorization: `Bearer ${token}`,
                    }
                    : {}),
            },
        },
    );

    if (!response.ok) {
        throw new Error("Failed to download attachment.");
    }

    const blob = await response.blob();
    const url = URL.createObjectURL(blob);

    const link = document.createElement("a");

    link.href = url;
    link.download =
        attachment.original_filename ||
        attachment.filename;

    document.body.appendChild(link);

    link.click();
    link.remove();

    URL.revokeObjectURL(url);
}