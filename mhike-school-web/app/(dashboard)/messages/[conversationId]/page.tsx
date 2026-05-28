"use client";

import { useEffect, useRef, useState } from "react";
import { useParams } from "next/navigation";
import {
    CheckCheck,
    Forward,
    Image as ImageIcon,
    MoreHorizontal,
    Paperclip,
    Reply,
    Send,
} from "lucide-react";

import { getConversation, sendMessage } from "@/lib/messages";
import { disconnectSocket, getSocket } from "@/lib/socket";
import { useAuth } from "@/providers/AuthProvider";

import type { Conversation, Message } from "@/types/message";

export default function ConversationPage() {
    const params = useParams<{ conversationId: string }>();
    const conversationId = params.conversationId;
    const { user } = useAuth();

    const [conversation, setConversation] =
        useState<Conversation | null>(null);
    const [messageBody, setMessageBody] = useState("");
    const [replyToMessage, setReplyToMessage] =
        useState<Message | null>(null);
    const [forwardMessage, setForwardMessage] =
        useState<Message | null>(null);
    const [typingUsers, setTypingUsers] = useState<string[]>([]);
    const [loading, setLoading] = useState(true);
    const [sending, setSending] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const bottomRef = useRef<HTMLDivElement | null>(null);
    const typingTimeoutRef = useRef<NodeJS.Timeout | null>(null);

    async function loadConversation() {
        try {
            setLoading(true);
            const data = await getConversation(conversationId);
            setConversation(data);
            setError(null);
        } catch (err) {
            console.error(err);
            setError("Unable to load conversation.");
        } finally {
            setLoading(false);
        }
    }

    useEffect(() => {
        if (!conversationId || !user) return;

        loadConversation();

        const socket = getSocket({
            user_id: user.id,
            school_id: user.school_id,
        });

        socket.emit("join_conversation", {
            conversation_id: conversationId,
        });

        socket.on("new_message", (message: Message) => {
            if (Number(message.conversation_id) !== Number(conversationId)) {
                return;
            }

            setConversation((previous) => {
                if (!previous) return previous;

                const exists = previous.messages?.some(
                    (item) => item.id === message.id,
                );

                if (exists) return previous;

                return {
                    ...previous,
                    messages: [...(previous.messages ?? []), message],
                };
            });
        });

        socket.on("typing:start", (payload) => {
            if (Number(payload.conversation_id) !== Number(conversationId)) {
                return;
            }

            if (!payload.full_name) return;

            setTypingUsers((previous) => {
                if (previous.includes(payload.full_name)) {
                    return previous;
                }

                return [...previous, payload.full_name];
            });
        });

        socket.on("typing:stop", (payload) => {
            if (!payload.full_name) return;

            setTypingUsers((previous) =>
                previous.filter((name) => name !== payload.full_name),
            );
        });

        return () => {
            socket.off("new_message");
            socket.off("typing:start");
            socket.off("typing:stop");
            disconnectSocket();
        };
    }, [conversationId, user]);

    useEffect(() => {
        bottomRef.current?.scrollIntoView({
            behavior: "smooth",
        });
    }, [conversation?.messages]);

    async function handleSendMessage() {
        const body = messageBody.trim();

        if (!body || sending) return;

        const finalBody = replyToMessage
            ? `Replying to: "${replyToMessage.body}"\n\n${body}`
            : body;

        try {
            setSending(true);

            const message = await sendMessage(conversationId, {
                body: finalBody,
            });

            const socket = getSocket({
                user_id: user?.id,
                school_id: user?.school_id,
            });

            socket.emit("send_message", message);

            socket.emit("typing_stop", {
                conversation_id: conversationId,
                user_id: user?.id,
                full_name: user?.full_name,
            });

            setMessageBody("");
            setReplyToMessage(null);
            setForwardMessage(null);
        } catch (err) {
            console.error(err);
            alert("Failed to send message.");
        } finally {
            setSending(false);
        }
    }

    function handleReply(message: Message) {
        setReplyToMessage(message);
        setForwardMessage(null);
    }

    function handleForward(message: Message) {
        setForwardMessage(message);
        setReplyToMessage(null);
        setMessageBody(`Forwarded message:\n\n${message.body}`);
    }

    if (loading) {
        return (
            <div className="p-6 text-sm text-gray-500">
                Loading conversation...
            </div>
        );
    }

    if (error) {
        return (
            <div className="p-6">
                <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">
                    {error}
                </div>
            </div>
        );
    }

    if (!conversation) {
        return (
            <div className="p-6 text-sm text-gray-500">
                Conversation not found.
            </div>
        );
    }

    return (
        <div className="flex h-full flex-col space-y-6 p-6">
            <div>
                <h1 className="text-2xl font-bold">
                    {conversation.title || "Conversation"}
                </h1>

                <p className="text-sm text-gray-500">
                    {conversation.conversation_type}
                </p>
            </div>

            <div className="flex-1 overflow-y-auto rounded-3xl border border-gray-200 bg-white p-6 shadow-sm">
                <div className="space-y-5">
                    {conversation.messages &&
                        conversation.messages.length > 0 ? (
                        conversation.messages.map((message) => {
                            const isOwnMessage =
                                Number(message.sender_id) === Number(user?.id);

                            return (
                                <div
                                    key={message.id}
                                    className={`group flex ${isOwnMessage
                                        ? "justify-end"
                                        : "justify-start"
                                        }`}
                                >
                                    <div
                                        className={`flex max-w-[75%] flex-col ${isOwnMessage
                                            ? "items-end"
                                            : "items-start"
                                            }`}
                                    >
                                        <div
                                            className={`rounded-3xl px-5 py-3 shadow-sm transition-all ${isOwnMessage
                                                ? "bg-blue-600 text-white"
                                                : "bg-gray-100 text-gray-900"
                                                }`}
                                        >
                                            <p className="whitespace-pre-wrap text-sm leading-relaxed">
                                                {message.body}
                                            </p>
                                        </div>

                                        <div
                                            className={`mt-2 flex items-center gap-3 text-xs ${isOwnMessage
                                                ? "text-gray-400"
                                                : "text-gray-500"
                                                }`}
                                        >
                                            <span>
                                                {new Date(
                                                    message.created_at,
                                                ).toLocaleTimeString([], {
                                                    hour: "2-digit",
                                                    minute: "2-digit",
                                                })}
                                            </span>

                                            {isOwnMessage && (
                                                <div className="flex items-center gap-1">
                                                    <CheckCheck className="h-4 w-4 text-blue-500" />
                                                    <span>Read</span>
                                                </div>
                                            )}
                                        </div>

                                        <div className="mt-2 flex h-7 items-center gap-3 text-xs text-gray-500 opacity-0 transition-opacity duration-200 group-hover:opacity-100">
                                            <button
                                                type="button"
                                                onClick={() =>
                                                    handleReply(message)
                                                }
                                                className="flex h-7 items-center gap-1 rounded-full bg-gray-100 px-3 py-1 transition-colors hover:bg-gray-200"
                                            >
                                                <Reply className="h-3 w-3" />
                                                Reply
                                            </button>

                                            <button
                                                type="button"
                                                onClick={() =>
                                                    handleForward(message)
                                                }
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
                            );
                        })
                    ) : (
                        <div className="flex h-full items-center justify-center">
                            <p className="text-sm text-gray-400">
                                No messages yet.
                            </p>
                        </div>
                    )}

                    <div ref={bottomRef} />
                </div>
            </div>

            {typingUsers.length > 0 && (
                <div className="px-2 text-sm text-gray-500">
                    {typingUsers.join(", ")} typing...
                </div>
            )}

            <div className="rounded-3xl border border-gray-200 bg-white p-3 shadow-sm">
                {replyToMessage && (
                    <div className="mb-3 rounded-2xl border border-blue-200 bg-blue-50 p-3 text-sm text-blue-800">
                        <div className="flex items-center justify-between">
                            <div>
                                <p className="font-medium">Replying to</p>
                                <p className="truncate text-xs">
                                    {replyToMessage.body}
                                </p>
                            </div>

                            <button
                                type="button"
                                onClick={() => setReplyToMessage(null)}
                                className="text-xs underline"
                            >
                                Cancel
                            </button>
                        </div>
                    </div>
                )}

                {forwardMessage && (
                    <div className="mb-3 rounded-2xl border border-gray-200 bg-gray-50 p-3 text-sm text-gray-700">
                        <div className="flex items-center justify-between">
                            <div>
                                <p className="font-medium">
                                    Forwarding message
                                </p>
                                <p className="truncate text-xs">
                                    {forwardMessage.body}
                                </p>
                            </div>

                            <button
                                type="button"
                                onClick={() => {
                                    setForwardMessage(null);
                                    setMessageBody("");
                                }}
                                className="text-xs underline"
                            >
                                Cancel
                            </button>
                        </div>
                    </div>
                )}

                <div className="flex items-center gap-3">
                    <button
                        type="button"
                        className="rounded-full p-2 hover:bg-gray-100"
                    >
                        <Paperclip className="h-5 w-5 text-gray-500" />
                    </button>

                    <button
                        type="button"
                        className="rounded-full p-2 hover:bg-gray-100"
                    >
                        <ImageIcon className="h-5 w-5 text-gray-500" />
                    </button>

                    <input
                        type="text"
                        value={messageBody}
                        onChange={(event) => {
                            setMessageBody(event.target.value);

                            const socket = getSocket({
                                user_id: user?.id,
                                school_id: user?.school_id,
                            });

                            socket.emit("typing_start", {
                                conversation_id: conversationId,
                                user_id: user?.id,
                                full_name: user?.full_name,
                            });

                            if (typingTimeoutRef.current) {
                                clearTimeout(typingTimeoutRef.current);
                            }

                            typingTimeoutRef.current = setTimeout(() => {
                                socket.emit("typing_stop", {
                                    conversation_id: conversationId,
                                    user_id: user?.id,
                                    full_name: user?.full_name,
                                });
                            }, 1000);
                        }}
                        placeholder="Type a message..."
                        className="flex-1 rounded-full bg-gray-100 px-5 py-3 text-sm outline-none focus:ring-2 focus:ring-blue-500"
                    />

                    <button
                        type="button"
                        onClick={handleSendMessage}
                        disabled={sending}
                        className="flex items-center gap-2 rounded-full bg-blue-600 px-5 py-3 text-sm font-medium text-white transition hover:bg-blue-700 disabled:opacity-50"
                    >
                        <Send className="h-4 w-4" />
                        {sending ? "Sending..." : "Send"}
                    </button>
                </div>
            </div>
        </div>
    );
}