"use client";

import Link from "next/link";

import type { Conversation } from "@/types/message";

type ConversationCardProps = {
    conversation: Conversation;
};

function formatLastActivity(dateString?: string | null): string {
    if (!dateString) return "";

    const date = new Date(dateString);

    if (Number.isNaN(date.getTime())) return "";

    const now = new Date();
    const diffMinutes = Math.floor(
        (now.getTime() - date.getTime()) / 60000,
    );

    if (diffMinutes < 1) return "Now";
    if (diffMinutes < 60) return `${diffMinutes}m`;

    const diffHours = Math.floor(diffMinutes / 60);

    if (diffHours < 24) return `${diffHours}h`;

    const diffDays = Math.floor(diffHours / 24);

    if (diffDays < 7) return `${diffDays}d`;

    return date.toLocaleDateString("en-GB", {
        day: "2-digit",
        month: "short",
    });
}

function getConversationActivityDate(conversation: Conversation): string | null {
    return (
        conversation.last_activity ??
        conversation.latest_message?.created_at ??
        conversation.updated_at ??
        conversation.created_at ??
        conversation.messages?.[conversation.messages.length - 1]?.created_at ??
        null
    );
}

function getLatestMessage(conversation: Conversation) {
    if (conversation.latest_message) {
        return conversation.latest_message;
    }

    if (!conversation.messages || conversation.messages.length === 0) {
        return null;
    }

    return conversation.messages[conversation.messages.length - 1];
}

function getUnreadCount(conversation: Conversation): number {
    return conversation.unread_count ?? 0;
}

function getConversationTitle(conversation: Conversation): string {
    const participantNames =
        conversation.participants
            ?.map((participant) => participant.user?.full_name)
            .filter(Boolean)
            .join(", ") ?? "";

    return conversation.title || participantNames || "Untitled conversation";
}

function getInitials(title: string): string {
    const parts = title.trim().split(" ").filter(Boolean);

    if (parts.length === 0) return "M";
    if (parts.length === 1) return parts[0].charAt(0).toUpperCase();

    return `${parts[0].charAt(0)}${parts[1].charAt(0)}`.toUpperCase();
}

function getLatestMessagePreview(conversation: Conversation): string {
    const latestMessage = getLatestMessage(conversation);

    if (!latestMessage) return "No messages yet";

    if (latestMessage.body?.trim()) {
        return latestMessage.body.trim();
    }

    return "No message preview";
}

export default function ConversationCard({
    conversation,
}: ConversationCardProps) {
    const title = getConversationTitle(conversation);
    const latestMessage = getLatestMessage(conversation);
    const unreadCount = getUnreadCount(conversation);
    const activityDate = getConversationActivityDate(conversation);
    const preview = getLatestMessagePreview(conversation);

    const hasUnread = unreadCount > 0;

    return (
        <Link
            href={`/messages/${conversation.id}`}
            className={`group block rounded-3xl border px-5 py-4 shadow-sm transition-all duration-200 hover:-translate-y-0.5 hover:shadow-md ${hasUnread
                ? "border-blue-300 bg-blue-50/70 hover:border-blue-400"
                : "border-slate-200 bg-white hover:border-blue-200 hover:bg-slate-50"
                }`}
        >
            <div className="flex items-center gap-4">
                <div
                    className={`flex h-14 w-14 shrink-0 items-center justify-center rounded-2xl text-lg font-bold text-white shadow-sm ${hasUnread ? "bg-blue-700" : "bg-[#0D3B66]"
                        }`}
                >
                    {getInitials(title)}
                </div>

                <div className="min-w-0 flex-1">
                    <div className="flex items-start justify-between gap-4">
                        <div className="min-w-0">
                            <h2
                                className={`truncate text-lg ${hasUnread
                                    ? "font-bold text-slate-950"
                                    : "font-semibold text-slate-900"
                                    }`}
                            >
                                {title}
                            </h2>

                            <p className="mt-0.5 text-xs font-medium uppercase tracking-wide text-slate-400">
                                {conversation.conversation_type} conversation
                            </p>
                        </div>

                        <div className="flex shrink-0 flex-col items-end gap-2">
                            {activityDate && (
                                <span
                                    className={`text-xs font-medium ${hasUnread
                                        ? "text-blue-700"
                                        : "text-slate-400"
                                        }`}
                                >
                                    {formatLastActivity(activityDate)}
                                </span>
                            )}

                            {hasUnread && (
                                <span className="flex h-6 min-w-6 items-center justify-center rounded-full bg-blue-600 px-2 text-xs font-bold text-white shadow-sm">
                                    {unreadCount > 99 ? "99+" : unreadCount}
                                </span>
                            )}
                        </div>
                    </div>

                    <p
                        className={`mt-3 truncate text-sm ${hasUnread
                            ? "font-semibold text-slate-800"
                            : "text-slate-600"
                            }`}
                    >
                        {preview}
                    </p>

                    {latestMessage?.sender_name && (
                        <p className="mt-1 truncate text-xs text-slate-400">
                            From {latestMessage.sender_name}
                        </p>
                    )}
                </div>
            </div>
        </Link>
    );
}