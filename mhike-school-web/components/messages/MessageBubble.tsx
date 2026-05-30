"use client";

import {
    CheckCheck,
    Forward,
    MoreHorizontal,
    Reply,
} from "lucide-react";

import MessageAttachmentList from "@/components/messages/MessageAttachmentList";

import type { Message } from "@/types/message";

type MessageBubbleProps = {
    message: Message;
    currentUserId?: number | null;
    currentUserName?: string | null;
    onReply: (message: Message) => void;
    onForward: (message: Message) => void;
};

function getMessageStatus(
    message: Message,
): "Sent" | "Delivered" | "Read" {
    const deliveries = message.deliveries ?? [];

    if (deliveries.length === 0) {
        return "Sent";
    }

    const readCount = deliveries.filter(
        (delivery) => delivery.read_at !== null,
    ).length;

    if (readCount > 0) {
        return "Read";
    }

    const deliveredCount = deliveries.filter(
        (delivery) => delivery.delivered_at !== null,
    ).length;

    if (deliveredCount > 0) {
        return "Delivered";
    }

    return "Sent";
}

function getReceiptTooltip(message: Message) {
    const deliveries = message.deliveries ?? [];

    const readCount = deliveries.filter(
        (delivery) => delivery.read_at !== null,
    ).length;

    const deliveredCount = deliveries.filter(
        (delivery) => delivery.delivered_at !== null,
    ).length;

    if (readCount > 0) {
        return `Read by ${readCount} recipient${readCount === 1 ? "" : "s"}`;
    }

    if (deliveredCount > 0) {
        return `Delivered to ${deliveredCount} recipient${deliveredCount === 1 ? "" : "s"
            }`;
    }

    return "Sent";
}

function formatMessageTime(dateString: string) {
    return new Date(dateString).toLocaleTimeString([], {
        hour: "2-digit",
        minute: "2-digit",
    });
}

export default function MessageBubble({
    message,
    currentUserId,
    currentUserName,
    onReply,
    onForward,
}: MessageBubbleProps) {
    const isOwnMessage =
        Number(message.sender_id) === Number(currentUserId);

    const messageStatus = getMessageStatus(message);

    return (
        <div
            className={`group flex ${isOwnMessage ? "justify-end" : "justify-start"
                }`}
        >
            <div
                className={`flex max-w-[75%] items-end gap-3 ${isOwnMessage ? "flex-row-reverse" : "flex-row"
                    }`}
            >
                <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-gray-300 text-sm font-semibold text-white">
                    {isOwnMessage
                        ? currentUserName?.charAt(0) || "M"
                        : "U"}
                </div>

                <div
                    className={`flex flex-col ${isOwnMessage ? "items-end" : "items-start"
                        }`}
                >
                    <div
                        className={`rounded-3xl px-5 py-3 shadow-sm transition-all ${isOwnMessage
                            ? "bg-blue-600 text-white"
                            : "bg-white text-gray-900"
                            }`}
                    >
                        {message.reply_to && (
                            <div
                                className={`mb-3 rounded-2xl border px-3 py-2 text-xs ${isOwnMessage
                                    ? "border-blue-400 bg-blue-500/20 text-blue-100"
                                    : "border-gray-200 bg-gray-50 text-gray-600"
                                    }`}
                            >
                                <div className="mb-1 font-semibold">
                                    Replying to
                                </div>

                                <div className="line-clamp-2">
                                    {message.reply_to.body}
                                </div>
                            </div>
                        )}

                        {message.body ? (
                            <p className="whitespace-pre-wrap text-sm leading-relaxed">
                                {message.body}
                            </p>
                        ) : null}

                        <MessageAttachmentList attachments={message.attachments} />
                    </div>

                    <div
                        className={`mt-1 flex items-center gap-2 text-xs ${isOwnMessage ? "text-gray-400" : "text-gray-500"
                            }`}
                    >
                        <span>{formatMessageTime(message.created_at)}</span>

                        {isOwnMessage && (
                            <div
                                className="flex items-center gap-1"
                                title={getReceiptTooltip(message)}
                            >
                                <CheckCheck
                                    className={`h-4 w-4 ${messageStatus === "Read"
                                        ? "text-blue-500"
                                        : "text-gray-400"
                                        }`}
                                />

                                <span>{messageStatus}</span>
                            </div>
                        )}
                    </div>

                    <div className="mt-2 flex h-7 items-center gap-3 text-xs text-gray-500 opacity-0 transition-opacity duration-200 group-hover:opacity-100">
                        <button
                            type="button"
                            onClick={() => onReply(message)}
                            className="flex h-7 items-center gap-1 rounded-full bg-gray-100 px-3 py-1 transition-colors hover:bg-gray-200"
                        >
                            <Reply className="h-3 w-3" />
                            Reply
                        </button>

                        <button
                            type="button"
                            onClick={() => onForward(message)}
                            className="flex h-7 items-center gap-1 rounded-full bg-gray-100 px-3 py-1 transition-colors hover:bg-gray-200"
                        >
                            <Forward className="h-3 w-3" />
                            Forward
                        </button>

                        <button
                            type="button"
                            className="flex h-7 w-7 items-center justify-center rounded-full bg-gray-100 transition-colors hover:bg-gray-200"
                        >
                            <MoreHorizontal className="h-4 w-4" />
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
}