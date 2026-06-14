"use client";

import { CheckCheck, Forward, MoreHorizontal, Reply } from "lucide-react";

import MessageAttachmentList from "@/components/messages/MessageAttachmentList";

import type { ReactNode } from "react";
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

function getMessageStatus(message: Message): "Sent" | "Delivered" | "Read" {
    const deliveries = message.deliveries ?? [];

    if (deliveries.some((delivery) => delivery.read_at !== null)) {
        return "Read";
    }

    if (deliveries.some((delivery) => delivery.delivered_at !== null)) {
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
        return `Read by ${readCount} recipient${readCount === 1 ? "" : "s"}`;
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

    if (parts.length === 0) return "U";
    if (parts.length === 1) return parts[0].charAt(0).toUpperCase();

    return `${parts[0].charAt(0)}${parts[1].charAt(0)}`.toUpperCase();
}

function normaliseUrl(url: string): string {
    return /^https?:\/\//i.test(url) ? url : `https://${url}`;
}

function renderMessageText(text: string): ReactNode[] {
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
                    className="font-semibold text-white underline decoration-white/80 underline-offset-2"
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
            return "rounded-l-2xl rounded-r-lg";
        }

        if (isGroupedWithPrevious) {
            return "rounded-l-2xl rounded-br-2xl rounded-tr-lg";
        }

        if (isGroupedWithNext) {
            return "rounded-l-2xl rounded-t-2xl rounded-br-lg";
        }

        return "rounded-2xl rounded-br-lg";
    }

    if (isGroupedWithPrevious && isGroupedWithNext) {
        return "rounded-r-2xl rounded-l-lg";
    }

    if (isGroupedWithPrevious) {
        return "rounded-r-2xl rounded-bl-2xl rounded-tl-lg";
    }

    if (isGroupedWithNext) {
        return "rounded-r-2xl rounded-t-2xl rounded-bl-lg";
    }

    return "rounded-2xl rounded-bl-lg";
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
    const isOwnMessage = Number(message.sender_id) === Number(currentUserId);

    const messageStatus = getMessageStatus(message);

    const senderName = getSenderName(
        message,
        isOwnMessage,
        currentUserName,
    );

    const sentAt = formatMessageDateTime(message.created_at);

    const showHeader = !isGroupedWithPrevious;
    const showAvatar = !isOwnMessage && showHeader;
    const showStatus = isOwnMessage && !isGroupedWithNext;

    return (
        <div className="group flex w-full">
            <div
                className={`flex w-full gap-2 ${isOwnMessage ? "flex-row-reverse" : "flex-row"
                    }`}
            >
                {!isOwnMessage && (
                    <div className="flex h-10 w-10 shrink-0 items-start justify-center pt-1">
                        {showAvatar && (
                            <div className="flex h-10 w-10 items-center justify-center rounded-full bg-[#0F766E] text-sm font-bold text-white shadow-sm">
                                {getInitials(senderName)}
                            </div>
                        )}
                    </div>
                )}

                <div
                    className={`flex w-full flex-col ${isOwnMessage ? "items-end" : "items-start"
                        }`}
                >
                    {showHeader && (
                        <div
                            className={`mb-0.5 flex flex-wrap items-center gap-1.5 text-sm ${isOwnMessage
                                ? "justify-end text-[#1E3A5F]"
                                : "justify-start text-[#0F766E]"
                                }`}
                        >
                            <span className="font-bold">{senderName}</span>

                            <span aria-hidden="true">·</span>

                            <time dateTime={message.created_at}>
                                {sentAt}
                            </time>
                        </div>
                    )}

                    <div
                        className={`w-full max-w-[900px] border border-white/10 px-4 py-3 text-base text-white shadow-md ring-1 ring-black/5 ${isOwnMessage
                            ? "bg-[#1E3A5F]"
                            : "bg-[#0F766E]"
                            } ${getBubbleRadiusClass(
                                isOwnMessage,
                                isGroupedWithPrevious,
                                isGroupedWithNext,
                            )}`}
                    >
                        {message.reply_to && (
                            <div className="mb-2 rounded-xl border border-white/15 bg-black/10 px-3 py-2 text-sm text-white/90">
                                <div className="mb-1 font-bold">
                                    Replying to
                                </div>

                                <div className="line-clamp-2">
                                    {message.reply_to.body}
                                </div>
                            </div>
                        )}

                        {message.body && (
                            <p className="whitespace-pre-wrap break-words text-base leading-7">
                                {renderMessageText(message.body)}
                            </p>
                        )}

                        <MessageAttachmentList
                            attachments={message.attachments}
                        />
                    </div>

                    {showStatus && (
                        <div
                            className="mt-0.5 flex items-center justify-end gap-1 text-xs font-medium text-slate-400"
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
                        className={`mt-1 flex h-7 items-center gap-2 text-xs text-slate-500 opacity-0 transition-opacity duration-200 group-hover:opacity-100 ${isOwnMessage
                            ? "justify-end"
                            : "justify-start"
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