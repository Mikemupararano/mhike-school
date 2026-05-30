"use client";

import Link from "next/link";

import type { Conversation } from "@/types/message";

type ConversationCardProps = {
    conversation: Conversation;
};

function formatLastActivity(
    dateString?: string | null,
) {
    if (!dateString) {
        return "";
    }

    const date = new Date(
        dateString,
    );

    if (
        Number.isNaN(
            date.getTime(),
        )
    ) {
        return "";
    }

    const now = new Date();

    const diffMinutes =
        Math.floor(
            (
                now.getTime() -
                date.getTime()
            ) / 60000,
        );

    if (diffMinutes < 1) {
        return "Now";
    }

    if (diffMinutes < 60) {
        return `${diffMinutes}m`;
    }

    const diffHours =
        Math.floor(
            diffMinutes / 60,
        );

    if (diffHours < 24) {
        return `${diffHours}h`;
    }

    const diffDays =
        Math.floor(
            diffHours / 24,
        );

    if (diffDays < 7) {
        return `${diffDays}d`;
    }

    return date.toLocaleDateString();
}

function getConversationActivityDate(
    conversation: Conversation,
) {
    return (
        conversation.last_activity ||
        conversation
            .latest_message
            ?.created_at ||
        conversation.updated_at ||
        conversation.created_at ||
        conversation
            .messages?.[
            (
                conversation
                    .messages
                    .length ?? 1
            ) - 1
        ]?.created_at ||
        null
    );
}

function getLatestMessage(
    conversation: Conversation,
) {
    if (
        conversation.latest_message
    ) {
        return conversation.latest_message;
    }

    if (
        !conversation.messages ||
        conversation.messages
            .length === 0
    ) {
        return null;
    }

    return conversation.messages[
        conversation.messages
            .length - 1
    ];
}

function getUnreadCount(
    conversation: Conversation,
) {
    return (
        conversation.unread_count ??
        0
    );
}

function getConversationTitle(
    conversation: Conversation,
) {
    const participantNames =
        conversation.participants
            ?.map(
                (
                    participant,
                ) =>
                    participant
                        .user
                        ?.full_name,
            )
            .filter(Boolean)
            .join(", ");

    return (
        conversation.title ||
        participantNames ||
        "Untitled conversation"
    );
}

export default function ConversationCard({
    conversation,
}: ConversationCardProps) {
    const title =
        getConversationTitle(
            conversation,
        );

    const latestMessage =
        getLatestMessage(
            conversation,
        );

    const unreadCount =
        getUnreadCount(
            conversation,
        );

    const activityDate =
        getConversationActivityDate(
            conversation,
        );

    return (
        <Link
            href={`/messages/${conversation.id}`}
            className={`group block rounded-3xl border p-5 shadow-sm transition-all hover:-translate-y-0.5 hover:shadow-md ${unreadCount > 0
                ? "border-blue-300 bg-blue-50/40 hover:border-blue-400"
                : "border-gray-200 bg-white hover:border-blue-200"
                }`}
        >
            <div className="flex items-start gap-4">
                <div
                    className={`flex h-14 w-14 shrink-0 items-center justify-center rounded-full text-lg font-semibold text-white ${unreadCount > 0
                        ? "bg-blue-700"
                        : "bg-blue-600"
                        }`}
                >
                    {title
                        .charAt(0)
                        .toUpperCase()}
                </div>

                <div className="min-w-0 flex-1">
                    <div className="flex items-start justify-between gap-4">
                        <div className="min-w-0">
                            <h2
                                className={`truncate text-lg ${unreadCount >
                                    0
                                    ? "font-bold text-gray-950"
                                    : "font-semibold text-gray-900"
                                    }`}
                            >
                                {title}
                            </h2>

                            <p className="mt-1 text-sm capitalize text-gray-500">
                                {
                                    conversation.conversation_type
                                }
                            </p>
                        </div>

                        <div className="flex shrink-0 flex-col items-end gap-2">
                            <span className="text-xs text-gray-400">
                                {formatLastActivity(
                                    activityDate,
                                )}
                            </span>

                            {unreadCount >
                                0 && (
                                    <span className="flex h-6 min-w-[24px] items-center justify-center rounded-full bg-blue-600 px-2 text-xs font-semibold text-white">
                                        {unreadCount >
                                            99
                                            ? "99+"
                                            : unreadCount}
                                    </span>
                                )}
                        </div>
                    </div>

                    <div className="mt-4">
                        {latestMessage ? (
                            <p
                                className={`truncate text-sm ${unreadCount >
                                    0
                                    ? "font-medium text-gray-800"
                                    : "text-gray-600"
                                    }`}
                            >
                                {
                                    latestMessage.body
                                }
                            </p>
                        ) : (
                            <p className="text-sm italic text-gray-400">
                                No messages
                                yet
                            </p>
                        )}

                        {activityDate && (
                            <p className="mt-1 text-xs text-gray-400">
                                Last
                                activity{" "}
                                {formatLastActivity(
                                    activityDate,
                                )}
                            </p>
                        )}
                    </div>
                </div>
            </div>
        </Link>
    );
}