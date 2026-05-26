export type ConversationType = "direct" | "group" | "class" | "broadcast";

export type SchoolMessageUser = {
    id: number;
    full_name: string;
    email: string;
    role: string;
};

export type Message = {
    id: number;
    conversation_id: number;
    sender_id: number;
    body: string;
    created_at: string;
};

export type ConversationParticipant = {
    id: number;
    user_id: number;
    conversation_id: number;
};

export type Conversation = {
    id: number;
    school_id: number;
    created_by_id: number;
    title: string | null;
    conversation_type: ConversationType;
    created_at: string;
    participants?: ConversationParticipant[];
    messages?: Message[];
};

export type ConversationCreatePayload = {
    participant_ids: number[];
    title?: string | null;
    conversation_type: ConversationType;
};

export type MessageCreatePayload = {
    body: string;
};