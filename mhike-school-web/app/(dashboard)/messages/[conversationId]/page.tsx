"use client";

import {
    useCallback,
    useEffect,
    useRef,
    useState,
} from "react";
import { useParams } from "next/navigation";

import MessageBubble from "@/components/messages/MessageBubble";
import MessageComposer from "@/components/messages/MessageComposer";

import {
    attachFileToMessage,
    getConversation,
    markConversationRead,
    markMessageDelivered,
    markMessageRead,
    sendMessage,
    uploadMessageFile,
} from "@/lib/messages";
import { disconnectSocket, getSocket } from "@/lib/socket";
import { useAuth } from "@/providers/AuthProvider";

import type { Conversation, Message, MessageDelivery } from "@/types/message";

export default function ConversationPage() {
    const params = useParams<{ conversationId: string }>();
    const conversationId = params.conversationId;
    const { user } = useAuth();

    const [conversation, setConversation] = useState<Conversation | null>(null);
    const [messageBody, setMessageBody] = useState("");
    const [replyToMessage, setReplyToMessage] = useState<Message | null>(null);
    const [forwardMessage, setForwardMessage] = useState<Message | null>(null);
    const [typingUsers, setTypingUsers] = useState<string[]>([]);
    const [selectedFile, setSelectedFile] = useState<File | null>(null);
    const [uploadingAttachment, setUploadingAttachment] = useState(false);
    const [loading, setLoading] = useState(true);
    const [sending, setSending] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const bottomRef = useRef<HTMLDivElement | null>(null);
    const typingTimeoutRef = useRef<NodeJS.Timeout | null>(null);
    const processedReadsRef = useRef<Set<number>>(new Set());

    const loadConversation = useCallback(async () => {
        try {
            setLoading(true);

            const data = await getConversation(conversationId);

            setConversation(data);

            await markConversationRead(conversationId);

            setError(null);

            return data;
        } catch (err) {
            console.error(err);
            setError("Unable to load conversation.");
            return null;
        } finally {
            setLoading(false);
        }
    }, [conversationId]);

    function appendMessage(message: Message) {
        setConversation((previous) => {
            if (!previous) return previous;

            const exists = previous.messages?.some(
                (item) => Number(item.id) === Number(message.id),
            );

            if (exists) return previous;

            return {
                ...previous,
                messages: [...(previous.messages ?? []), message],
            };
        });
    }

    function applyDeliveryUpdate(delivery: MessageDelivery) {
        setConversation((previous) => {
            if (!previous) return previous;

            return {
                ...previous,
                messages: previous.messages?.map((message) => {
                    if (Number(message.id) !== Number(delivery.message_id)) {
                        return message;
                    }

                    const existingDeliveries = message.deliveries ?? [];

                    const deliveryExists = existingDeliveries.some(
                        (item) => Number(item.id) === Number(delivery.id),
                    );

                    return {
                        ...message,
                        deliveries: deliveryExists
                            ? existingDeliveries.map((item) =>
                                Number(item.id) === Number(delivery.id)
                                    ? delivery
                                    : item,
                            )
                            : [...existingDeliveries, delivery],
                    };
                }),
            };
        });
    }

    const shouldMarkMessageRead = useCallback(
        (message: Message) => {
            if (!user) return false;

            if (Number(message.sender_id) === Number(user.id)) {
                return false;
            }

            if (processedReadsRef.current.has(Number(message.id))) {
                return false;
            }

            const userDelivery = message.deliveries?.find(
                (delivery) => Number(delivery.user_id) === Number(user.id),
            );

            return !userDelivery || userDelivery.read_at === null;
        },
        [user],
    );

    async function uploadAttachmentForMessage(messageId: number) {
        if (!selectedFile) return;

        setUploadingAttachment(true);

        try {
            const upload = await uploadMessageFile(selectedFile);

            await attachFileToMessage(messageId, upload);
        } finally {
            setUploadingAttachment(false);
        }
    }

    useEffect(() => {
        if (!conversationId || !user) return;

        void loadConversation();

        const socket = getSocket({
            user_id: user.id,
            school_id: user.school_id,
        });

        socket.emit("join_conversation", {
            conversation_id: conversationId,
        });

        socket.on("message:new", async (message: Message) => {
            if (Number(message.conversation_id) !== Number(conversationId)) {
                return;
            }

            appendMessage(message);

            if (Number(message.sender_id) !== Number(user.id)) {
                try {
                    processedReadsRef.current.add(Number(message.id));

                    const delivered = await markMessageDelivered(message.id);
                    applyDeliveryUpdate(delivered);

                    const read = await markMessageRead(message.id);
                    applyDeliveryUpdate(read);

                    await markConversationRead(conversationId);
                } catch (err) {
                    processedReadsRef.current.delete(Number(message.id));
                    console.error(err);
                }
            }
        });

        socket.on("messages:refresh", async (payload) => {
            if (
                payload?.conversation_id &&
                Number(payload.conversation_id) !== Number(conversationId)
            ) {
                return;
            }

            await loadConversation();
        });

        socket.on("message:delivered", (delivery: MessageDelivery) => {
            applyDeliveryUpdate(delivery);
        });

        socket.on("message:read", (delivery: MessageDelivery) => {
            applyDeliveryUpdate(delivery);
        });

        socket.on("typing:start", (payload) => {
            if (Number(payload.conversation_id) !== Number(conversationId)) {
                return;
            }

            if (!payload.full_name) return;

            if (Number(payload.user_id) === Number(user.id)) {
                return;
            }

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
            socket.emit("leave_conversation", {
                conversation_id: conversationId,
            });

            socket.off("message:new");
            socket.off("messages:refresh");
            socket.off("message:delivered");
            socket.off("message:read");
            socket.off("typing:start");
            socket.off("typing:stop");

            if (typingTimeoutRef.current) {
                clearTimeout(typingTimeoutRef.current);
            }

            disconnectSocket();
        };
    }, [conversationId, user, loadConversation]);

    useEffect(() => {
        if (!conversation?.messages || !user) {
            return;
        }

        const messages = conversation.messages;

        async function markVisibleMessages() {
            let markedAnyMessage = false;

            for (const message of messages) {
                if (!shouldMarkMessageRead(message)) {
                    continue;
                }

                try {
                    processedReadsRef.current.add(Number(message.id));

                    const delivered = await markMessageDelivered(message.id);
                    applyDeliveryUpdate(delivered);

                    const read = await markMessageRead(message.id);
                    applyDeliveryUpdate(read);

                    markedAnyMessage = true;
                } catch (err) {
                    processedReadsRef.current.delete(Number(message.id));
                    console.error(err);
                }
            }

            if (markedAnyMessage) {
                try {
                    await markConversationRead(conversationId);
                } catch (err) {
                    console.error(err);
                }
            }
        }

        void markVisibleMessages();
    }, [conversation?.messages, conversationId, user, shouldMarkMessageRead]);

    useEffect(() => {
        bottomRef.current?.scrollIntoView({
            behavior: "smooth",
        });
    }, [conversation?.messages]);

    async function handleSendMessage() {
        const body = messageBody.trim();

        if (
            (!body && !selectedFile) ||
            sending ||
            uploadingAttachment ||
            !user
        ) {
            return;
        }

        try {
            setSending(true);

            const message = await sendMessage(conversationId, {
                body,
                reply_to_message_id: replyToMessage?.id ?? null,
            });

            if (selectedFile) {
                await uploadAttachmentForMessage(message.id);
                await loadConversation();
            } else {
                appendMessage(message);
            }

            const socket = getSocket({
                user_id: user.id,
                school_id: user.school_id,
            });

            socket.emit("typing_stop", {
                conversation_id: conversationId,
                user_id: user.id,
                full_name: user.full_name,
            });

            socket.emit("send_message", {
                ...message,
                conversation_id: conversationId,
            });

            setMessageBody("");
            setReplyToMessage(null);
            setForwardMessage(null);
            setSelectedFile(null);
        } catch (err) {
            console.error(err);
            alert("Failed to send message.");
        } finally {
            setSending(false);
        }
    }

    function handleTypingChange(value: string) {
        setMessageBody(value);

        if (!user) return;

        const socket = getSocket({
            user_id: user.id,
            school_id: user.school_id,
        });

        socket.emit("typing_start", {
            conversation_id: conversationId,
            user_id: user.id,
            full_name: user.full_name,
        });

        if (typingTimeoutRef.current) {
            clearTimeout(typingTimeoutRef.current);
        }

        typingTimeoutRef.current = setTimeout(() => {
            socket.emit("typing_stop", {
                conversation_id: conversationId,
                user_id: user.id,
                full_name: user.full_name,
            });
        }, 1000);
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
        <div className="flex h-[calc(100vh-80px)] flex-col bg-gray-50">
            <div className="border-b border-gray-200 bg-white px-6 py-4 shadow-sm">
                <h1 className="text-2xl font-bold">
                    {conversation.title || "Conversation"}
                </h1>

                <p className="text-sm text-gray-500">
                    {conversation.conversation_type}
                </p>
            </div>

            <div className="flex-1 overflow-y-auto px-4 py-6">
                <div className="mx-auto flex max-w-5xl flex-col gap-4">
                    {conversation.messages && conversation.messages.length > 0 ? (
                        conversation.messages.map((message) => (
                            <MessageBubble
                                key={message.id}
                                message={message}
                                currentUserId={user?.id}
                                currentUserName={user?.full_name}
                                onReply={handleReply}
                                onForward={handleForward}
                            />
                        ))
                    ) : (
                        <div className="flex h-full items-center justify-center py-20">
                            <p className="text-sm text-gray-400">
                                No messages yet.
                            </p>
                        </div>
                    )}

                    <div ref={bottomRef} />
                </div>
            </div>

            {typingUsers.length > 0 && (
                <div className="px-6 py-2 text-sm text-gray-500">
                    {typingUsers.join(", ")} typing...
                </div>
            )}

            <MessageComposer
                messageBody={messageBody}
                sending={sending}
                uploadingAttachment={uploadingAttachment}
                selectedFile={selectedFile}
                replyToMessage={replyToMessage}
                forwardMessage={forwardMessage}
                onMessageChange={handleTypingChange}
                onSend={handleSendMessage}
                onFileSelect={setSelectedFile}
                onCancelReply={() => setReplyToMessage(null)}
                onCancelForward={() => {
                    setForwardMessage(null);
                    setMessageBody("");
                }}
            />
        </div>
    );
}