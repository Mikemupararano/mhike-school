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
    const parts = name.trim().split(" ").filter(Boolean);

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

function renderMessageText(
    text: string,
    isOwnMessage: boolean,
) {
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
                    className={`font-medium underline underline-offset-2 ${isOwnMessage
                        ? "text-white decoration-white/80"
                        : "text-blue-600 decoration-blue-400"
                        }`}
                >
                    {part}
                </a>
            );
        }

        return <span key={`${part}-${index}`}>{part}</span>;
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

    const senderName = getSenderName(
        message,
        isOwnMessage,
        currentUserName,
    );

    const sentAt = formatMessageDateTime(message.created_at);

    return (
        <div
            className={`group flex w-full ${isOwnMessage ? "justify-end" : "justify-start"
                }`}
        >
            <div
                className={`flex max-w-[68%] items-end gap-2 ${isOwnMessage ? "flex-row-reverse" : "flex-row"
                    }`}
            >
                {!isOwnMessage && (
                    <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-slate-300 text-xs font-semibold text-white shadow-sm">
                        {getInitials(senderName)}
                    </div>
                )}

                <div
                    className={`flex min-w-0 flex-col ${isOwnMessage ? "items-end" : "items-start"
                        }`}
                >
                    <div
                        className={`mb-1 flex max-w-full flex-wrap items-center gap-1.5 text-[11px] ${isOwnMessage
                            ? "justify-end text-slate-400"
                            : "justify-start text-slate-500"
                            }`}
                    >
                        {!isOwnMessage && (
                            <>
                                <span className="font-semibold text-slate-700">
                                    {senderName}
                                </span>

                                <span aria-hidden="true">·</span>
                            </>
                        )}

                        <time dateTime={message.created_at}>{sentAt}</time>
                    </div>

                    <div
                        className={`max-w-full rounded-2xl px-4 py-2.5 text-sm shadow-sm ring-1 ring-black/5 ${isOwnMessage
                            ? "rounded-br-md bg-blue-600 text-white"
                            : "rounded-bl-md bg-white text-slate-900"
                            }`}
                    >
                        {message.reply_to && (
                            <div
                                className={`mb-2 rounded-xl border px-3 py-2 text-xs ${isOwnMessage
                                    ? "border-blue-400 bg-blue-500/30 text-blue-50"
                                    : "border-slate-200 bg-slate-50 text-slate-600"
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
                            <p className="whitespace-pre-wrap break-words text-sm leading-relaxed">
                                {renderMessageText(
                                    message.body,
                                    isOwnMessage,
                                )}
                            </p>
                        ) : null}

                        <MessageAttachmentList
                            attachments={message.attachments}
                        />
                    </div>

                    <div
                        className={`mt-1 flex items-center gap-2 text-[11px] ${isOwnMessage ? "text-slate-400" : "text-slate-500"
                            }`}
                    >
                        {isOwnMessage && (
                            <div
                                className="flex items-center gap-1"
                                title={getReceiptTooltip(message)}
                            >
                                <CheckCheck
                                    className={`h-3.5 w-3.5 ${messageStatus === "Read"
                                        ? "text-blue-500"
                                        : "text-slate-400"
                                        }`}
                                />

                                <span>{messageStatus}</span>
                            </div>
                        )}
                    </div>

                    <div
                        className={`mt-1.5 flex h-7 items-center gap-2 text-xs text-slate-500 opacity-0 transition-opacity duration-200 group-hover:opacity-100 ${isOwnMessage ? "justify-end" : "justify-start"
                            }`}
                    >
                        <button
                            type="button"
                            onClick={() => onReply(message)}
                            className="flex h-7 items-center gap-1 rounded-full bg-white px-3 py-1 shadow-sm ring-1 ring-slate-200 transition-colors hover:bg-slate-50"
                        >
                            <Reply className="h-3 w-3" />
                            Reply
                        </button>

                        <button
                            type="button"
                            onClick={() => onForward(message)}
                            className="flex h-7 items-center gap-1 rounded-full bg-white px-3 py-1 shadow-sm ring-1 ring-slate-200 transition-colors hover:bg-slate-50"
                        >
                            <Forward className="h-3 w-3" />
                            Forward
                        </button>

                        <button
                            type="button"
                            className="flex h-7 w-7 items-center justify-center rounded-full bg-white shadow-sm ring-1 ring-slate-200 transition-colors hover:bg-slate-50"
                        >
                            <MoreHorizontal className="h-4 w-4" />
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
}