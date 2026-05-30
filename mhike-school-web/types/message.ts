export type ConversationType =
    | "direct"
    | "group"
    | "class"
    | "broadcast";

export type SchoolMessageUser = {
    id: number;
    full_name: string;
    email: string;
    role: string;
};

export type MessageReply = {
    id: number;
    sender_id: number | null;
    body: string;
    created_at: string;
};

export type MessageDelivery = {
    id: number;
    message_id: number;
    user_id: number;
    delivered_at: string | null;
    read_at: string | null;
};

export type MessageAttachment = {
    id: number;
    message_id: number;
    uploaded_by_id?: number | null;
    filename: string;
    original_filename: string;
    mime_type: string;
    file_size: number;
    storage_path: string;
    created_at: string;
};

export type MessageAttachmentUploadResponse = {
    id: number;
    message_id: number;
    uploaded_by_id?: number | null;
    filename: string;
    original_filename: string;
    mime_type: string;
    file_size: number;
    storage_path: string;
    created_at?: string | null;
};

export type MessageAttachmentCreateResponse = {
    success: boolean;
    attachment: MessageAttachment;
};

export type MessageAttachmentDownload = {
    id: number;
    filename: string;
    original_filename: string;
    mime_type: string;
    file_size: number;
    storage_path: string;
};

export type Message = {
    id: number;
    conversation_id: number;
    sender_id: number | null;
    body: string;
    reply_to_message_id?: number | null;
    reply_to?: MessageReply | null;
    created_at: string;
    updated_at?: string | null;
    deliveries?: MessageDelivery[];
    attachments?: MessageAttachment[];
};

export type ConversationParticipantUser = {
    id: number;
    full_name: string;
    email: string;
    role: string;
};

export type ConversationParticipant = {
    id: number;
    user_id: number;
    conversation_id: number;
    joined_at?: string;
    last_read_at?: string | null;
    user?: ConversationParticipantUser | null;
};

export type ConversationLatestMessage = {
    id: number;
    body: string;
    sender_id?: number | null;
    created_at: string;
};

export type Conversation = {
    id: number;
    school_id: number | null;
    created_by_id: number | null;
    title: string | null;
    conversation_type: ConversationType;
    created_at: string;
    updated_at?: string | null;
    participants?: ConversationParticipant[];
    messages?: Message[];
    unread_count?: number;
    latest_message?: ConversationLatestMessage | null;
    last_activity?: string | null;
};

export type ConversationCreatePayload = {
    participant_ids: number[];
    title?: string | null;
    conversation_type: ConversationType;
};

export type MessageCreatePayload = {
    body: string;
    reply_to_message_id?: number | null;
};

export type MarkConversationReadResponse = {
    success: boolean;
    conversation_id: number;
    user_id: number;
    last_read_at: string | null;
};

export type UnreadMessageCountResponse = {
    unread_count: number;
};