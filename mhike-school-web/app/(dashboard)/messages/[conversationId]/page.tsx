"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import {
    ArrowLeft,
    RefreshCw,
} from "lucide-react";

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
import {
    disconnectSocket,
    getSocket,
    requestPresence,
    SocketEvents,
} from "@/lib/socket";
import { useAuth } from "@/providers/AuthProvider";

import type {
    Conversation,
    Message,
    MessageDelivery,
} from "@/types/message";

function formatLastUpdated(value: Date | null): string | null {
    if (!value) {
        return null;
    }

    return value.toLocaleTimeString("en-GB", {
        hour: "2-digit",
        minute: "2-digit",
    });
}

export default function ConversationPage() {
    const params =
        useParams<{ conversationId: string }>();
    const conversationId = params.conversationId;

    const router = useRouter();
    const { user } = useAuth();

    const [conversation, setConversation] =
        useState<Conversation | null>(null);
    const [messageBody, setMessageBody] =
        useState("");
    const [replyToMessage, setReplyToMessage] =
        useState<Message | null>(null);
    const [forwardMessage, setForwardMessage] =
        useState<Message | null>(null);
    const [typingUsers, setTypingUsers] =
        useState<string[]>([]);
    const [presenceMap, setPresenceMap] =
        useState<Record<number, boolean>>({});
    const [selectedFile, setSelectedFile] =
        useState<File | null>(null);

    const [uploadingAttachment, setUploadingAttachment] =
        useState(false);
    const [loading, setLoading] =
        useState(true);
    const [refreshing, setRefreshing] =
        useState(false);
    const [sending, setSending] =
        useState(false);

    const [error, setError] =
        useState<string | null>(null);
    const [sendError, setSendError] =
        useState<string | null>(null);

    const [lastUpdated, setLastUpdated] =
        useState<Date | null>(null);

    const bottomRef =
        useRef<HTMLDivElement | null>(null);
    const typingTimeoutRef =
        useRef<NodeJS.Timeout | null>(null);
    const processedReadsRef =
        useRef<Set<number>>(new Set());
    const loadingRef = useRef(false);

    const loadConversation = useCallback(
        async (showFullLoader = true) => {
            if (
                !conversationId ||
                loadingRef.current
            ) {
                return null;
            }

            try {
                loadingRef.current = true;

                if (showFullLoader) {
                    setLoading(true);
                } else {
                    setRefreshing(true);
                }

                setError(null);

                const data =
                    await getConversation(
                        conversationId,
                    );

                setConversation(data);
                await markConversationRead(
                    conversationId,
                );

                setLastUpdated(new Date());

                return data;
            } catch (err) {
                console.error(err);

                setError(
                    err instanceof Error
                        ? err.message
                        : "Unable to load conversation.",
                );

                return null;
            } finally {
                loadingRef.current = false;
                setLoading(false);
                setRefreshing(false);
            }
        },
        [conversationId],
    );

    const appendMessage = useCallback(
        (message: Message) => {
            setConversation((previous) => {
                if (!previous) {
                    return previous;
                }

                const exists =
                    previous.messages?.some(
                        (item) =>
                            Number(item.id) ===
                            Number(message.id),
                    );

                if (exists) {
                    return previous;
                }

                return {
                    ...previous,
                    messages: [
                        ...(previous.messages ?? []),
                        message,
                    ],
                };
            });
        },
        [],
    );

    const applyDeliveryUpdate = useCallback(
        (delivery: MessageDelivery) => {
            setConversation((previous) => {
                if (!previous) {
                    return previous;
                }

                return {
                    ...previous,
                    messages:
                        previous.messages?.map(
                            (message) => {
                                if (
                                    Number(
                                        message.id,
                                    ) !==
                                    Number(
                                        delivery.message_id,
                                    )
                                ) {
                                    return message;
                                }

                                const existingDeliveries =
                                    message.deliveries ??
                                    [];

                                const deliveryExists =
                                    existingDeliveries.some(
                                        (item) =>
                                            Number(
                                                item.id,
                                            ) ===
                                            Number(
                                                delivery.id,
                                            ),
                                    );

                                return {
                                    ...message,
                                    deliveries:
                                        deliveryExists
                                            ? existingDeliveries.map(
                                                (
                                                    item,
                                                ) =>
                                                    Number(
                                                        item.id,
                                                    ) ===
                                                        Number(
                                                            delivery.id,
                                                        )
                                                        ? delivery
                                                        : item,
                                            )
                                            : [
                                                ...existingDeliveries,
                                                delivery,
                                            ],
                                };
                            },
                        ),
                };
            });
        },
        [],
    );

    const shouldMarkMessageRead = useCallback(
        (message: Message) => {
            if (!user) {
                return false;
            }

            if (
                Number(message.sender_id) ===
                Number(user.id)
            ) {
                return false;
            }

            if (
                processedReadsRef.current.has(
                    Number(message.id),
                )
            ) {
                return false;
            }

            const userDelivery =
                message.deliveries?.find(
                    (delivery) =>
                        Number(delivery.user_id) ===
                        Number(user.id),
                );

            return (
                !userDelivery ||
                userDelivery.read_at === null
            );
        },
        [user],
    );

    async function uploadAttachmentForMessage(
        messageId: number,
    ): Promise<void> {
        if (!selectedFile) {
            return;
        }

        setUploadingAttachment(true);

        try {
            const upload =
                await uploadMessageFile(
                    selectedFile,
                );

            await attachFileToMessage(
                messageId,
                upload,
            );
        } finally {
            setUploadingAttachment(false);
        }
    }

    useEffect(() => {
        if (!conversationId || !user) {
            return;
        }

        void loadConversation();

        const socket = getSocket({
            user_id: user.id,
            school_id: user.school_id,
        });

        socket.emit("join_conversation", {
            conversation_id: conversationId,
        });

        const handleNewMessage = async (
            message: Message,
        ) => {
            if (
                Number(message.conversation_id) !==
                Number(conversationId)
            ) {
                return;
            }

            appendMessage(message);

            if (
                Number(message.sender_id) !==
                Number(user.id)
            ) {
                try {
                    processedReadsRef.current.add(
                        Number(message.id),
                    );

                    const delivered =
                        await markMessageDelivered(
                            message.id,
                        );
                    applyDeliveryUpdate(
                        delivered,
                    );

                    const read =
                        await markMessageRead(
                            message.id,
                        );
                    applyDeliveryUpdate(read);

                    await markConversationRead(
                        conversationId,
                    );
                } catch (err) {
                    processedReadsRef.current.delete(
                        Number(message.id),
                    );
                    console.error(err);
                }
            }
        };

        const handleRefresh = async (
            payload?: {
                conversation_id?: number | string;
            },
        ) => {
            if (
                payload?.conversation_id &&
                Number(
                    payload.conversation_id,
                ) !== Number(conversationId)
            ) {
                return;
            }

            await loadConversation(false);
        };

        const handleTypingStart = (
            payload: {
                conversation_id: number | string;
                full_name?: string;
                user_id: number | string;
            },
        ) => {
            if (
                Number(
                    payload.conversation_id,
                ) !== Number(conversationId)
            ) {
                return;
            }

            if (
                !payload.full_name ||
                Number(payload.user_id) ===
                Number(user.id)
            ) {
                return;
            }

            setTypingUsers((previous) => {
                if (
                    previous.includes(
                        payload.full_name as string,
                    )
                ) {
                    return previous;
                }

                return [
                    ...previous,
                    payload.full_name as string,
                ];
            });
        };

        const handleTypingStop = (
            payload: {
                full_name?: string;
            },
        ) => {
            if (!payload.full_name) {
                return;
            }

            setTypingUsers((previous) =>
                previous.filter(
                    (name) =>
                        name !==
                        payload.full_name,
                ),
            );
        };

        const handlePresenceUpdate = (
            payload: {
                user_id: number;
                online: boolean;
            },
        ) => {
            setPresenceMap((previous) => ({
                ...previous,
                [payload.user_id]:
                    payload.online,
            }));
        };

        const handlePresenceSnapshot = (
            payload: {
                presence: Record<
                    string,
                    boolean
                >;
            },
        ) => {
            const next: Record<
                number,
                boolean
            > = {};

            Object.entries(
                payload.presence,
            ).forEach(([userId, online]) => {
                next[Number(userId)] =
                    online;
            });

            setPresenceMap(next);
        };

        socket.on(
            "message:new",
            handleNewMessage,
        );
        socket.on(
            "messages:refresh",
            handleRefresh,
        );
        socket.on(
            "message:delivered",
            applyDeliveryUpdate,
        );
        socket.on(
            "message:read",
            applyDeliveryUpdate,
        );
        socket.on(
            "typing:start",
            handleTypingStart,
        );
        socket.on(
            "typing:stop",
            handleTypingStop,
        );
        socket.on(
            SocketEvents.PRESENCE_UPDATE,
            handlePresenceUpdate,
        );
        socket.on(
            SocketEvents.PRESENCE_SNAPSHOT,
            handlePresenceSnapshot,
        );

        return () => {
            socket.emit(
                "leave_conversation",
                {
                    conversation_id:
                        conversationId,
                },
            );

            socket.off(
                "message:new",
                handleNewMessage,
            );
            socket.off(
                "messages:refresh",
                handleRefresh,
            );
            socket.off(
                "message:delivered",
                applyDeliveryUpdate,
            );
            socket.off(
                "message:read",
                applyDeliveryUpdate,
            );
            socket.off(
                "typing:start",
                handleTypingStart,
            );
            socket.off(
                "typing:stop",
                handleTypingStop,
            );
            socket.off(
                SocketEvents.PRESENCE_UPDATE,
                handlePresenceUpdate,
            );
            socket.off(
                SocketEvents.PRESENCE_SNAPSHOT,
                handlePresenceSnapshot,
            );

            if (
                typingTimeoutRef.current
            ) {
                clearTimeout(
                    typingTimeoutRef.current,
                );
            }

            disconnectSocket();
        };
    }, [
        appendMessage,
        applyDeliveryUpdate,
        conversationId,
        loadConversation,
        user,
    ]);

    useEffect(() => {
        const participantIds =
            conversation?.participants
                ?.map(
                    (participant) =>
                        participant.user_id,
                )
                .filter(
                    (participantId) =>
                        Number(participantId) !==
                        Number(user?.id),
                ) ?? [];

        if (participantIds.length > 0) {
            requestPresence(
                participantIds,
            );
        }
    }, [
        conversation?.participants,
        user?.id,
    ]);

    useEffect(() => {
        const visibleMessages =
            conversation?.messages ?? [];

        if (
            visibleMessages.length === 0 ||
            !user
        ) {
            return;
        }

        async function markVisibleMessages() {
            let markedAnyMessage = false;

            for (const message of visibleMessages) {
                if (
                    !shouldMarkMessageRead(
                        message,
                    )
                ) {
                    continue;
                }

                try {
                    processedReadsRef.current.add(
                        Number(message.id),
                    );

                    const delivered =
                        await markMessageDelivered(
                            message.id,
                        );
                    applyDeliveryUpdate(
                        delivered,
                    );

                    const read =
                        await markMessageRead(
                            message.id,
                        );
                    applyDeliveryUpdate(read);

                    markedAnyMessage = true;
                } catch (err) {
                    processedReadsRef.current.delete(
                        Number(message.id),
                    );
                    console.error(err);
                }
            }

            if (markedAnyMessage) {
                try {
                    await markConversationRead(
                        conversationId,
                    );
                } catch (err) {
                    console.error(err);
                }
            }
        }

        void markVisibleMessages();
    }, [
        applyDeliveryUpdate,
        conversation?.messages,
        conversationId,
        shouldMarkMessageRead,
        user,
    ]);

    useEffect(() => {
        bottomRef.current?.scrollIntoView({
            behavior: "smooth",
        });
    }, [conversation?.messages]);

    async function handleSendMessage(): Promise<void> {
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
            setSendError(null);

            const message =
                await sendMessage(
                    conversationId,
                    {
                        body,
                        reply_to_message_id:
                            replyToMessage?.id ??
                            null,
                    },
                );

            if (selectedFile) {
                await uploadAttachmentForMessage(
                    message.id,
                );
                await loadConversation(false);
            } else {
                appendMessage(message);
            }

            const socket = getSocket({
                user_id: user.id,
                school_id: user.school_id,
            });

            socket.emit("typing_stop", {
                conversation_id:
                    conversationId,
                user_id: user.id,
                full_name: user.full_name,
            });

            socket.emit("send_message", {
                ...message,
                conversation_id:
                    conversationId,
            });

            setMessageBody("");
            setReplyToMessage(null);
            setForwardMessage(null);
            setSelectedFile(null);
        } catch (err) {
            console.error(err);

            setSendError(
                err instanceof Error
                    ? err.message
                    : "Failed to send message.",
            );
        } finally {
            setSending(false);
        }
    }

    function handleTypingChange(
        value: string,
    ): void {
        setMessageBody(value);
        setSendError(null);

        if (!user) {
            return;
        }

        const socket = getSocket({
            user_id: user.id,
            school_id: user.school_id,
        });

        socket.emit("typing_start", {
            conversation_id: conversationId,
            user_id: user.id,
            full_name: user.full_name,
        });

        if (
            typingTimeoutRef.current
        ) {
            clearTimeout(
                typingTimeoutRef.current,
            );
        }

        typingTimeoutRef.current =
            setTimeout(() => {
                socket.emit(
                    "typing_stop",
                    {
                        conversation_id:
                            conversationId,
                        user_id: user.id,
                        full_name:
                            user.full_name,
                    },
                );
            }, 1000);
    }

    function handleReply(
        message: Message,
    ): void {
        setReplyToMessage(message);
        setForwardMessage(null);
        setSendError(null);
    }

    function handleForward(
        message: Message,
    ): void {
        setForwardMessage(message);
        setReplyToMessage(null);
        setMessageBody(
            `Forwarded message:\n\n${message.body}`,
        );
        setSendError(null);
    }

    if (loading) {
        return (
            <main className="min-h-[calc(100vh-80px)] bg-slate-50 p-4 sm:p-6">
                <div className="mx-auto max-w-6xl space-y-4">
                    <div className="animate-pulse rounded-2xl border border-slate-200 bg-white p-5">
                        <div className="h-6 w-1/3 rounded bg-slate-200" />
                        <div className="mt-3 h-4 w-1/4 rounded bg-slate-100" />
                    </div>

                    {Array.from({
                        length: 4,
                    }).map((_, index) => (
                        <div
                            key={index}
                            className="animate-pulse rounded-2xl bg-white p-5"
                        >
                            <div className="h-4 w-1/2 rounded bg-slate-100" />
                            <div className="mt-3 h-4 w-2/3 rounded bg-slate-100" />
                        </div>
                    ))}
                </div>
            </main>
        );
    }

    if (error) {
        return (
            <main className="min-h-[calc(100vh-80px)] bg-slate-50 p-4 sm:p-6">
                <div className="mx-auto max-w-3xl rounded-2xl border border-red-200 bg-red-50 p-5">
                    <h1 className="text-lg font-bold text-red-800">
                        Unable to load conversation
                    </h1>

                    <p className="mt-2 text-sm text-red-700">
                        {error}
                    </p>

                    <div className="mt-4 flex flex-wrap gap-3">
                        <button
                            type="button"
                            data-custom-button="true"
                            onClick={() => {
                                void loadConversation();
                            }}
                            className="rounded-xl bg-red-700 px-4 py-2 text-sm font-semibold text-white hover:bg-red-800"
                        >
                            Try again
                        </button>

                        <button
                            type="button"
                            data-custom-button="true"
                            onClick={() =>
                                router.push(
                                    "/messages",
                                )
                            }
                            className="rounded-xl border border-red-300 bg-white px-4 py-2 text-sm font-semibold text-red-700 hover:bg-red-100"
                        >
                            Back to messages
                        </button>
                    </div>
                </div>
            </main>
        );
    }

    if (!conversation) {
        return (
            <main className="flex min-h-[calc(100vh-80px)] items-center justify-center bg-slate-50 p-6">
                <div className="rounded-2xl border border-slate-200 bg-white p-6 text-center">
                    <h1 className="text-lg font-bold text-slate-900">
                        Conversation not found
                    </h1>

                    <button
                        type="button"
                        data-custom-button="true"
                        onClick={() =>
                            router.push(
                                "/messages",
                            )
                        }
                        className="mt-4 rounded-xl bg-slate-900 px-4 py-2 text-sm font-semibold text-white hover:bg-slate-800"
                    >
                        Return to messages
                    </button>
                </div>
            </main>
        );
    }

    const otherParticipant =
        conversation.participants?.find(
            (participant) =>
                Number(
                    participant.user_id,
                ) !== Number(user?.id),
        );

    const isOnline =
        otherParticipant
            ? Boolean(
                presenceMap[
                Number(
                    otherParticipant.user_id,
                )
                ],
            )
            : false;

    const lastUpdatedLabel =
        formatLastUpdated(lastUpdated);

    return (
        <main className="flex h-[calc(100vh-80px)] flex-col bg-slate-50">
            <header className="border-b border-slate-200 bg-white px-4 py-3 shadow-sm sm:px-6">
                <div className="mx-auto flex w-full max-w-6xl flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                    <div className="flex min-w-0 items-start gap-3">
                        <button
                            type="button"
                            data-custom-button="true"
                            onClick={() =>
                                router.push(
                                    "/messages",
                                )
                            }
                            aria-label="Back to messages"
                            className="mt-0.5 rounded-xl border border-slate-200 bg-white p-2 text-slate-600 transition hover:bg-slate-100 hover:text-slate-900"
                        >
                            <ArrowLeft
                                aria-hidden="true"
                                className="h-5 w-5"
                            />
                        </button>

                        <div className="min-w-0">
                            <h1 className="truncate text-xl font-extrabold text-slate-950">
                                {conversation.title ||
                                    "Conversation"}
                            </h1>

                            <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-slate-600">
                                <span className="flex items-center gap-1.5">
                                    <span
                                        aria-hidden="true"
                                        className={`h-2.5 w-2.5 rounded-full ${isOnline
                                            ? "bg-green-500"
                                            : "bg-slate-400"
                                            }`}
                                    />
                                    {isOnline
                                        ? "Online"
                                        : "Offline"}
                                </span>

                                <span className="text-xs uppercase tracking-wide text-slate-400">
                                    {
                                        conversation.conversation_type
                                    }{" "}
                                    conversation
                                </span>

                                {lastUpdatedLabel && (
                                    <span className="text-xs text-slate-400">
                                        Updated{" "}
                                        {lastUpdatedLabel}
                                    </span>
                                )}
                            </div>
                        </div>
                    </div>

                    <button
                        type="button"
                        data-custom-button="true"
                        onClick={() => {
                            void loadConversation(
                                false,
                            );
                        }}
                        disabled={refreshing}
                        className="inline-flex w-fit items-center gap-2 rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-60"
                    >
                        <RefreshCw
                            aria-hidden="true"
                            className={`h-4 w-4 ${refreshing
                                ? "animate-spin"
                                : ""
                                }`}
                        />
                        {refreshing
                            ? "Refreshing..."
                            : "Refresh"}
                    </button>
                </div>
            </header>

            <section
                aria-label="Conversation messages"
                className="flex-1 overflow-y-auto bg-slate-50 px-3 py-3 sm:px-6"
            >
                <div className="mx-auto flex w-full max-w-6xl flex-col">
                    {conversation.messages &&
                        conversation.messages.length >
                        0 ? (
                        conversation.messages.map(
                            (
                                message,
                                index,
                                messages,
                            ) => {
                                const previousMessage =
                                    messages[
                                    index - 1
                                    ];
                                const nextMessage =
                                    messages[
                                    index + 1
                                    ];

                                const isGroupedWithPrevious =
                                    previousMessage &&
                                    Number(
                                        previousMessage.sender_id,
                                    ) ===
                                    Number(
                                        message.sender_id,
                                    );

                                const isGroupedWithNext =
                                    nextMessage &&
                                    Number(
                                        nextMessage.sender_id,
                                    ) ===
                                    Number(
                                        message.sender_id,
                                    );

                                return (
                                    <div
                                        key={
                                            message.id
                                        }
                                        className={
                                            isGroupedWithPrevious
                                                ? "mt-0.5"
                                                : "mt-2"
                                        }
                                    >
                                        <MessageBubble
                                            message={
                                                message
                                            }
                                            currentUserId={
                                                user?.id
                                            }
                                            currentUserName={
                                                user?.full_name
                                            }
                                            isGroupedWithPrevious={Boolean(
                                                isGroupedWithPrevious,
                                            )}
                                            isGroupedWithNext={Boolean(
                                                isGroupedWithNext,
                                            )}
                                            onReply={
                                                handleReply
                                            }
                                            onForward={
                                                handleForward
                                            }
                                        />
                                    </div>
                                );
                            },
                        )
                    ) : (
                        <div className="flex min-h-64 items-center justify-center">
                            <div className="rounded-2xl border border-dashed border-slate-300 bg-white px-6 py-10 text-center">
                                <h2 className="font-bold text-slate-800">
                                    No messages yet
                                </h2>

                                <p className="mt-1 text-sm text-slate-500">
                                    Send the first message
                                    in this conversation.
                                </p>
                            </div>
                        </div>
                    )}

                    <div ref={bottomRef} />
                </div>
            </section>

            <div
                aria-live="polite"
                className="min-h-10 border-t border-slate-100 bg-white px-4 py-2 sm:px-6"
            >
                <div className="mx-auto w-full max-w-6xl text-sm text-slate-500">
                    {typingUsers.length > 0
                        ? `${typingUsers.join(
                            ", ",
                        )} ${typingUsers.length ===
                            1
                            ? "is"
                            : "are"
                        } typing...`
                        : ""}
                </div>
            </div>

            <div className="sticky bottom-0 border-t border-slate-200 bg-white shadow-lg">
                <div className="mx-auto w-full max-w-6xl">
                    {sendError && (
                        <div
                            role="alert"
                            className="mx-4 mt-3 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700"
                        >
                            {sendError}
                        </div>
                    )}

                    <MessageComposer
                        messageBody={
                            messageBody
                        }
                        sending={sending}
                        uploadingAttachment={
                            uploadingAttachment
                        }
                        selectedFile={
                            selectedFile
                        }
                        replyToMessage={
                            replyToMessage
                        }
                        forwardMessage={
                            forwardMessage
                        }
                        onMessageChange={
                            handleTypingChange
                        }
                        onSend={
                            handleSendMessage
                        }
                        onFileSelect={(file) => {
                            setSelectedFile(
                                file,
                            );
                            setSendError(null);
                        }}
                        onCancelReply={() =>
                            setReplyToMessage(
                                null,
                            )
                        }
                        onCancelForward={() => {
                            setForwardMessage(
                                null,
                            );
                            setMessageBody("");
                        }}
                    />
                </div>
            </div>
        </main>
    );
}
