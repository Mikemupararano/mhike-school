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
    isGroupedWithPrevious?: boolean;
    isGroupedWithNext?: boolean;
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

function getReceiptTooltip(message: Message): string {
    const deliveries = message.deliveries ?? [];

    const readCount = deliveries.filter(
        (delivery) => delivery.read_at !== null,
    ).length;

    const deliveredCount = deliveries.filter(
        (delivery) => delivery.delivered_at !== null,
    ).length;

    if (readCount > 0) {
        return `Read by ${readCount} recipient${readCount === 1 ? "" : "s"
            }`;
    }

    if (deliveredCount > 0) {
        return `Delivered to ${deliveredCount} recipient${deliveredCount === 1 ? "" : "s"
            }`;
    }

    return "Sent";
}

function formatMessageDateTime(dateString: string): string {
    return new Date(dateString).toLocaleString("en-GB", {
        day: "2-digit",
        month: "short",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit",
    });
}

function getSenderName(
    message: Message,
    isOwnMessage: boolean,
    currentUserName?: string | null,
): string {
    if (isOwnMessage) {
        return currentUserName || "You";
    }

    return (
        message.sender_name ||
        message.sender?.full_name ||
        message.sender?.name ||
        message.sender?.email ||
        "Unknown sender"
    );
}

function getInitials(name: string): string {
    const parts = name
        .trim()
        .split(" ")
        .filter(Boolean);

    if (parts.length === 0) {
        return "U";
    }

    if (parts.length === 1) {
        return parts[0].charAt(0).toUpperCase();
    }

    return `${parts[0].charAt(0)}${parts[1].charAt(0)}`.toUpperCase();
}

function normaliseUrl(url: string): string {
    if (/^https?:\/\//i.test(url)) {
        return url;
    }

    return `https://${url}`;
}

function renderMessageText(text: string): React.ReactNode[] {
    const urlRegex = /(https?:\/\/[^\s]+|www\.[^\s]+)/gi;
    const parts = text.split(urlRegex);

    return parts.map((part, index) => {
        if (part.match(urlRegex)) {
            return (
                <a
                    key={`${part}-${index}`}
                    href={normaliseUrl(part)}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="font-medium text-white underline decoration-white/80 underline-offset-2"
                >
                    {part}
                </a>
            );
        }

        return <span key={`${part}-${index}`}>{part}</span>;
    });
}

function getBubbleRadiusClass(
    isOwnMessage: boolean,
    isGroupedWithPrevious: boolean,
    isGroupedWithNext: boolean,
): string {
    if (isOwnMessage) {
        if (isGroupedWithPrevious && isGroupedWithNext) {
            return "rounded-r-md rounded-l-2xl";
        }

        if (isGroupedWithPrevious) {
            return "rounded-tr-md rounded-br-2xl rounded-l-2xl";
        }

        if (isGroupedWithNext) {
            return "rounded-br-md rounded-t-2xl rounded-bl-2xl";
        }

        return "rounded-2xl rounded-br-md";
    }

    if (isGroupedWithPrevious && isGroupedWithNext) {
        return "rounded-l-md rounded-r-2xl";
    }

    if (isGroupedWithPrevious) {
        return "rounded-tl-md rounded-bl-2xl rounded-r-2xl";
    }

    if (isGroupedWithNext) {
        return "rounded-bl-md rounded-t-2xl rounded-br-2xl";
    }

    return "rounded-2xl rounded-bl-md";
}

export default function MessageBubble({
    message,
    currentUserId,
    currentUserName,
    isGroupedWithPrevious = false,
    isGroupedWithNext = false,
    onReply,
    onForward,
}: MessageBubbleProps) {
    const isOwnMessage =
        Number(message.sender_id) === Number(currentUserId);

    const messageStatus = getMessageStatus(message);

    const senderName = getSenderName(
        message,
        isOwnMessage,
        currentUserName,
    );

    const sentAt = formatMessageDateTime(message.created_at);

    const showHeader = !isGroupedWithPrevious;
    const showAvatar = !isOwnMessage && !isGroupedWithNext;
    const showStatus = isOwnMessage && !isGroupedWithNext;

    return (
        <div
            className={`group flex w-full ${isOwnMessage ? "justify-end" : "justify-start"
                }`}
        >
            <div
                className={`flex w-full gap-2 ${isOwnMessage
                    ? "flex-row-reverse items-start"
                    : "flex-row items-start"
                    }`}
            >
                {!isOwnMessage && (
                    <div className="flex h-8 w-8 shrink-0 items-center justify-center">
                        {showAvatar ? (
                            <div className="flex h-8 w-8 items-center justify-center rounded-full bg-[#0D5C63] text-xs font-semibold text-white shadow-sm">
                                {getInitials(senderName)}
                            </div>
                        ) : null}
                    </div>
                )}

                <div
                    className={`flex min-w-[180px] max-w-[75%] xl:max-w-[65%] flex-col ${isOwnMessage ? "items-end" : "items-start"
                        }`}
                >
                    {showHeader && (
                        <div
                            className={`mb-1 flex flex-wrap items-center gap-1.5 text-[11px] ${isOwnMessage
                                ? "justify-end text-[#561F37]"
                                : "justify-start text-[#0D5C63]"
                                }`}
                        >
                            <span className="font-semibold">
                                {senderName}
                            </span>

                            <span aria-hidden="true">·</span>

                            <time dateTime={message.created_at}>
                                {sentAt}
                            </time>
                        </div>
                    )}

                    <div
                        className={`max-w-full border border-white/10 px-5 py-3 text-sm text-white shadow-lg ring-1 ring-black/5 ${isOwnMessage
                            ? "bg-[#561F37]"
                            : "bg-[#0D5C63]"
                            } ${getBubbleRadiusClass(
                                isOwnMessage,
                                isGroupedWithPrevious,
                                isGroupedWithNext,
                            )}`}
                    >
                        {message.reply_to && (
                            <div className="mb-3 min-h-[44px] rounded-xl border border-white/15 bg-black/10 px-3 py-2 text-xs text-white/90">
                                <div className="mb-1 font-semibold">
                                    Replying to
                                </div>

                                <div className="line-clamp-2">
                                    {message.reply_to.body}
                                </div>
                            </div>
                        )}

                        {message.body && (
                            <p className="whitespace-pre-wrap break-words leading-relaxed">
                                {renderMessageText(message.body)}
                            </p>
                        )}

                        <MessageAttachmentList
                            attachments={message.attachments}
                        />
                    </div>

                    {showStatus && (
                        <div
                            className="mt-0.5 flex items-center justify-end gap-1 text-[11px] font-medium text-slate-400"
                            title={getReceiptTooltip(message)}
                        >
                            <CheckCheck
                                className={`h-4 w-4 ${messageStatus === "Read"
                                    ? "text-[#44A1A0]"
                                    : "text-slate-400"
                                    }`}
                            />

                            <span>{messageStatus}</span>
                        </div>
                    )}

                    <div
                        className={`mt-2 flex h-7 items-center gap-2 text-xs text-slate-500 opacity-0 transition-opacity duration-200 group-hover:opacity-100 ${isOwnMessage ? "justify-end" : "justify-start"
                            }`}
                    >
                        <button
                            type="button"
                            onClick={() => onReply(message)}
                            className="flex h-7 items-center gap-1 rounded-full bg-white px-3 py-1 shadow-sm ring-1 ring-slate-200 hover:bg-slate-50"
                        >
                            <Reply className="h-3 w-3" />
                            Reply
                        </button>

                        <button
                            type="button"
                            onClick={() => onForward(message)}
                            className="flex h-7 items-center gap-1 rounded-full bg-white px-3 py-1 shadow-sm ring-1 ring-slate-200 hover:bg-slate-50"
                        >
                            <Forward className="h-3 w-3" />
                            Forward
                        </button>

                        <button
                            type="button"
                            className="flex h-7 w-7 items-center justify-center rounded-full bg-white shadow-sm ring-1 ring-slate-200 hover:bg-slate-50"
                        >
                            <MoreHorizontal className="h-4 w-4" />
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
}