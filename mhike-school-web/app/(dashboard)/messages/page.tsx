"use client";

import { useRouter } from "next/navigation";
import {
    useCallback,
    useEffect,
    useMemo,
    useRef,
    useState,
} from "react";
import {
    MessageCircle,
    Plus,
    RefreshCw,
    Search,
    X,
} from "lucide-react";

import ConversationCard from "@/components/messages/ConversationCard";

import {
    createConversation,
    getConversations,
    getSchoolMessageUsers,
} from "@/lib/messages";
import { getSocket, SocketEvents } from "@/lib/socket";

import type {
    Conversation,
    SchoolMessageUser,
} from "@/types/message";

function getConversationActivityDate(
    conversation: Conversation,
): string | null {
    return (
        conversation.last_activity ??
        conversation.latest_message?.created_at ??
        conversation.updated_at ??
        conversation.created_at ??
        conversation.messages?.[
            conversation.messages.length - 1
        ]?.created_at ??
        null
    );
}

function formatLastUpdated(value: Date | null): string | null {
    if (!value) {
        return null;
    }

    return value.toLocaleTimeString("en-GB", {
        hour: "2-digit",
        minute: "2-digit",
    });
}

export default function MessagesPage() {
    const router = useRouter();

    const [conversations, setConversations] =
        useState<Conversation[]>([]);
    const [users, setUsers] =
        useState<SchoolMessageUser[]>([]);

    const [selectedUserId, setSelectedUserId] =
        useState("");
    const [conversationTitle, setConversationTitle] =
        useState("");
    const [searchQuery, setSearchQuery] =
        useState("");

    const [loading, setLoading] =
        useState(true);
    const [creating, setCreating] =
        useState(false);
    const [showModal, setShowModal] =
        useState(false);

    const [error, setError] =
        useState<string | null>(null);
    const [createError, setCreateError] =
        useState<string | null>(null);

    const [lastUpdated, setLastUpdated] =
        useState<Date | null>(null);

    const loadingRef = useRef(false);
    const newConversationButtonRef =
        useRef<HTMLButtonElement | null>(null);
    const modalRef =
        useRef<HTMLDivElement | null>(null);
    const recipientSelectRef =
        useRef<HTMLSelectElement | null>(null);

    const loadData = useCallback(async () => {
        if (loadingRef.current) {
            return;
        }

        try {
            loadingRef.current = true;
            setLoading(true);
            setError(null);

            const [conversationData, userData] =
                await Promise.all([
                    getConversations(),
                    getSchoolMessageUsers(),
                ]);

            setConversations(conversationData);
            setUsers(userData);
            setLastUpdated(new Date());
        } catch (err) {
            console.error(err);

            setError(
                err instanceof Error
                    ? err.message
                    : "Unable to load messages.",
            );
        } finally {
            loadingRef.current = false;
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        void loadData();
    }, [loadData]);

    useEffect(() => {
        window.addEventListener(
            "focus",
            loadData,
        );

        return () => {
            window.removeEventListener(
                "focus",
                loadData,
            );
        };
    }, [loadData]);

    useEffect(() => {
        const socket = getSocket();

        socket.on(
            SocketEvents.MESSAGES_REFRESH,
            loadData,
        );
        socket.on(
            SocketEvents.MESSAGE_NEW,
            loadData,
        );
        socket.on(
            SocketEvents.MESSAGE_DELIVERED,
            loadData,
        );
        socket.on(
            SocketEvents.MESSAGE_READ,
            loadData,
        );

        return () => {
            socket.off(
                SocketEvents.MESSAGES_REFRESH,
                loadData,
            );
            socket.off(
                SocketEvents.MESSAGE_NEW,
                loadData,
            );
            socket.off(
                SocketEvents.MESSAGE_DELIVERED,
                loadData,
            );
            socket.off(
                SocketEvents.MESSAGE_READ,
                loadData,
            );
        };
    }, [loadData]);

    const closeModal = useCallback(() => {
        if (creating) {
            return;
        }

        setShowModal(false);
        setConversationTitle("");
        setSelectedUserId("");
        setCreateError(null);

        window.setTimeout(() => {
            newConversationButtonRef.current?.focus();
        }, 0);
    }, [creating]);

    useEffect(() => {
        if (!showModal) {
            return;
        }

        recipientSelectRef.current?.focus();

        function handleKeyDown(
            event: KeyboardEvent,
        ): void {
            if (event.key === "Escape") {
                event.preventDefault();
                closeModal();
                return;
            }

            if (
                event.key !== "Tab" ||
                !modalRef.current
            ) {
                return;
            }

            const focusableElements =
                modalRef.current.querySelectorAll<HTMLElement>(
                    'button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [href], [tabindex]:not([tabindex="-1"])',
                );

            if (focusableElements.length === 0) {
                return;
            }

            const firstElement =
                focusableElements[0];
            const lastElement =
                focusableElements[
                focusableElements.length - 1
                ];

            if (
                event.shiftKey &&
                document.activeElement ===
                firstElement
            ) {
                event.preventDefault();
                lastElement.focus();
            } else if (
                !event.shiftKey &&
                document.activeElement ===
                lastElement
            ) {
                event.preventDefault();
                firstElement.focus();
            }
        }

        document.addEventListener(
            "keydown",
            handleKeyDown,
        );

        return () => {
            document.removeEventListener(
                "keydown",
                handleKeyDown,
            );
        };
    }, [closeModal, showModal]);

    async function handleCreateConversation(): Promise<void> {
        if (!selectedUserId || creating) {
            return;
        }

        try {
            setCreating(true);
            setCreateError(null);

            const conversation =
                await createConversation({
                    participant_ids: [
                        Number(selectedUserId),
                    ],
                    title:
                        conversationTitle.trim() ||
                        null,
                    conversation_type: "direct",
                });

            await loadData();

            setShowModal(false);
            setConversationTitle("");
            setSelectedUserId("");

            router.push(
                `/messages/${conversation.id}`,
            );
        } catch (err) {
            console.error(err);

            setCreateError(
                err instanceof Error
                    ? err.message
                    : "Failed to create conversation.",
            );
        } finally {
            setCreating(false);
        }
    }

    const sortedConversations = useMemo(
        () =>
            [...conversations].sort(
                (first, second) => {
                    const firstDate =
                        getConversationActivityDate(
                            first,
                        );
                    const secondDate =
                        getConversationActivityDate(
                            second,
                        );

                    return (
                        new Date(
                            secondDate ?? 0,
                        ).getTime() -
                        new Date(
                            firstDate ?? 0,
                        ).getTime()
                    );
                },
            ),
        [conversations],
    );

    const visibleConversations = useMemo(() => {
        const normalizedQuery =
            searchQuery.trim().toLowerCase();

        if (!normalizedQuery) {
            return sortedConversations;
        }

        return sortedConversations.filter(
            (conversation) =>
                (conversation.title ?? "")
                    .toLowerCase()
                    .includes(normalizedQuery),
        );
    }, [
        searchQuery,
        sortedConversations,
    ]);

    const lastUpdatedLabel =
        formatLastUpdated(lastUpdated);

    return (
        <main className="min-h-screen bg-slate-50 p-4 sm:p-6 lg:p-8">
            <div className="mx-auto max-w-5xl space-y-6">
                <header className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                    <div>
                        <h1 className="text-3xl font-extrabold text-slate-950">
                            Messages
                        </h1>

                        <p className="mt-2 max-w-2xl text-base text-slate-600">
                            Send and receive secure
                            internal school messages.
                        </p>

                        {lastUpdatedLabel && (
                            <p className="mt-2 text-sm text-slate-500">
                                Last refreshed at{" "}
                                {lastUpdatedLabel}
                            </p>
                        )}
                    </div>

                    <div className="flex flex-wrap gap-3">
                        <button
                            type="button"
                            data-custom-button="true"
                            onClick={() => {
                                void loadData();
                            }}
                            disabled={loading}
                            className="inline-flex items-center gap-2 rounded-xl border border-slate-300 bg-white px-4 py-2.5 text-sm font-semibold text-slate-700 transition hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-60"
                        >
                            <RefreshCw
                                aria-hidden="true"
                                className={`h-4 w-4 ${loading
                                    ? "animate-spin"
                                    : ""
                                    }`}
                            />
                            {loading
                                ? "Refreshing..."
                                : "Refresh"}
                        </button>

                        <button
                            ref={
                                newConversationButtonRef
                            }
                            type="button"
                            data-custom-button="true"
                            onClick={() => {
                                setCreateError(null);
                                setShowModal(true);
                            }}
                            className="inline-flex items-center gap-2 rounded-xl bg-blue-600 px-4 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-blue-700"
                        >
                            <Plus
                                aria-hidden="true"
                                className="h-4 w-4"
                            />
                            New conversation
                        </button>
                    </div>
                </header>

                <section className="rounded-2xl border border-blue-100 bg-blue-50 p-5 sm:p-6">
                    <p className="text-sm font-bold uppercase tracking-wide text-blue-700">
                        Inbox overview
                    </p>

                    <div className="mt-2 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
                        <div>
                            <h2 className="text-2xl font-extrabold text-slate-950">
                                {conversations.length}{" "}
                                {conversations.length === 1
                                    ? "conversation"
                                    : "conversations"}
                            </h2>

                            <p className="mt-1 text-base text-slate-600">
                                Conversations are ordered
                                by their most recent
                                activity.
                            </p>
                        </div>
                    </div>
                </section>

                <section
                    aria-labelledby="message-search-heading"
                    className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm sm:p-5"
                >
                    <h2
                        id="message-search-heading"
                        className="sr-only"
                    >
                        Search conversations
                    </h2>

                    <label
                        htmlFor="conversation-search"
                        className="sr-only"
                    >
                        Search conversations by title
                    </label>

                    <div className="relative">
                        <Search
                            aria-hidden="true"
                            className="pointer-events-none absolute left-4 top-1/2 h-5 w-5 -translate-y-1/2 text-slate-400"
                        />

                        <input
                            id="conversation-search"
                            type="search"
                            value={searchQuery}
                            onChange={(event) =>
                                setSearchQuery(
                                    event.target.value,
                                )
                            }
                            placeholder="Search conversations by title"
                            className="w-full rounded-xl border border-slate-300 py-3 pl-11 pr-4 text-base text-slate-900 outline-none transition placeholder:text-slate-400 focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
                        />
                    </div>
                </section>

                {loading &&
                    conversations.length === 0 && (
                        <section
                            aria-live="polite"
                            className="space-y-3"
                        >
                            {Array.from({
                                length: 3,
                            }).map((_, index) => (
                                <div
                                    key={index}
                                    className="animate-pulse rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"
                                >
                                    <div className="h-5 w-1/3 rounded bg-slate-200" />
                                    <div className="mt-3 h-4 w-2/3 rounded bg-slate-100" />
                                    <div className="mt-2 h-4 w-1/2 rounded bg-slate-100" />
                                </div>
                            ))}
                        </section>
                    )}

                {error && (
                    <section
                        role="alert"
                        className="rounded-2xl border border-red-200 bg-red-50 p-5"
                    >
                        <h2 className="font-bold text-red-800">
                            Unable to load messages
                        </h2>

                        <p className="mt-1 text-sm text-red-700">
                            {error}
                        </p>

                        <button
                            type="button"
                            data-custom-button="true"
                            onClick={() => {
                                void loadData();
                            }}
                            className="mt-4 rounded-xl bg-red-700 px-4 py-2 text-sm font-semibold text-white transition hover:bg-red-800"
                        >
                            Try again
                        </button>
                    </section>
                )}

                {!loading &&
                    !error &&
                    sortedConversations.length ===
                    0 && (
                        <section className="flex flex-col items-center justify-center rounded-3xl border border-dashed border-slate-300 bg-white px-5 py-16 text-center shadow-sm sm:py-20">
                            <MessageCircle
                                aria-hidden="true"
                                className="mb-4 h-12 w-12 text-slate-300"
                            />

                            <h2 className="text-xl font-bold text-slate-800">
                                No conversations yet
                            </h2>

                            <p className="mt-2 max-w-md text-base text-slate-500">
                                Start a new conversation
                                with an available member
                                of your school community.
                            </p>

                            <button
                                type="button"
                                data-custom-button="true"
                                onClick={() =>
                                    setShowModal(true)
                                }
                                className="mt-6 inline-flex items-center gap-2 rounded-xl bg-blue-600 px-5 py-3 text-sm font-semibold text-white transition hover:bg-blue-700"
                            >
                                <Plus
                                    aria-hidden="true"
                                    className="h-4 w-4"
                                />
                                Start a conversation
                            </button>
                        </section>
                    )}

                {!loading &&
                    !error &&
                    sortedConversations.length >
                    0 &&
                    visibleConversations.length ===
                    0 && (
                        <section className="rounded-2xl border border-dashed border-slate-300 bg-white p-10 text-center">
                            <h2 className="text-lg font-bold text-slate-800">
                                No matching conversations
                            </h2>

                            <p className="mt-2 text-sm text-slate-500">
                                Try a different search
                                term.
                            </p>
                        </section>
                    )}

                {!error &&
                    visibleConversations.length >
                    0 && (
                        <section
                            aria-label="Conversation list"
                            className="space-y-4"
                        >
                            {visibleConversations.map(
                                (conversation) => (
                                    <ConversationCard
                                        key={
                                            conversation.id
                                        }
                                        conversation={
                                            conversation
                                        }
                                    />
                                ),
                            )}
                        </section>
                    )}
            </div>

            {showModal && (
                <div
                    className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/50 p-4 backdrop-blur-sm"
                    onMouseDown={(event) => {
                        if (
                            event.target ===
                            event.currentTarget
                        ) {
                            closeModal();
                        }
                    }}
                >
                    <div
                        ref={modalRef}
                        role="dialog"
                        aria-modal="true"
                        aria-labelledby="new-conversation-title"
                        aria-describedby="new-conversation-description"
                        className="w-full max-w-md rounded-3xl bg-white p-6 shadow-2xl"
                    >
                        <div className="flex items-start justify-between gap-4">
                            <div>
                                <h2
                                    id="new-conversation-title"
                                    className="text-2xl font-bold text-slate-900"
                                >
                                    New Conversation
                                </h2>

                                <p
                                    id="new-conversation-description"
                                    className="mt-1 text-sm text-slate-500"
                                >
                                    Start a private
                                    conversation with an
                                    available school user.
                                </p>
                            </div>

                            <button
                                type="button"
                                data-custom-button="true"
                                onClick={closeModal}
                                disabled={creating}
                                aria-label="Close new conversation dialog"
                                className="rounded-lg p-2 text-slate-500 transition hover:bg-slate-100 hover:text-slate-800 disabled:cursor-not-allowed disabled:opacity-50"
                            >
                                <X
                                    aria-hidden="true"
                                    className="h-5 w-5"
                                />
                            </button>
                        </div>

                        <div className="mt-6 space-y-5">
                            {createError && (
                                <div
                                    role="alert"
                                    className="rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-700"
                                >
                                    {createError}
                                </div>
                            )}

                            <div>
                                <label
                                    htmlFor="conversation-title"
                                    className="mb-2 block text-sm font-semibold text-slate-700"
                                >
                                    Title
                                </label>

                                <input
                                    id="conversation-title"
                                    type="text"
                                    value={
                                        conversationTitle
                                    }
                                    onChange={(event) =>
                                        setConversationTitle(
                                            event.target
                                                .value,
                                        )
                                    }
                                    maxLength={200}
                                    placeholder="Optional title"
                                    className="w-full rounded-xl border border-slate-300 px-4 py-3 text-base text-slate-900 outline-none transition placeholder:text-slate-400 focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
                                />
                            </div>

                            <div>
                                <label
                                    htmlFor="conversation-recipient"
                                    className="mb-2 block text-sm font-semibold text-slate-700"
                                >
                                    Recipient
                                </label>

                                <select
                                    ref={
                                        recipientSelectRef
                                    }
                                    id="conversation-recipient"
                                    value={
                                        selectedUserId
                                    }
                                    onChange={(event) =>
                                        setSelectedUserId(
                                            event.target
                                                .value,
                                        )
                                    }
                                    className="w-full rounded-xl border border-slate-300 px-4 py-3 text-base text-slate-900 outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
                                >
                                    <option value="">
                                        Select a user
                                    </option>

                                    {users.map(
                                        (schoolUser) => (
                                            <option
                                                key={
                                                    schoolUser.id
                                                }
                                                value={
                                                    schoolUser.id
                                                }
                                            >
                                                {
                                                    schoolUser.full_name
                                                }{" "}
                                                (
                                                {
                                                    schoolUser.role
                                                }
                                                )
                                            </option>
                                        ),
                                    )}
                                </select>
                            </div>

                            <div className="flex flex-col-reverse gap-3 pt-2 sm:flex-row sm:justify-end">
                                <button
                                    type="button"
                                    data-custom-button="true"
                                    onClick={closeModal}
                                    disabled={creating}
                                    className="rounded-xl border border-slate-300 px-5 py-3 text-sm font-semibold text-slate-700 transition hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-50"
                                >
                                    Cancel
                                </button>

                                <button
                                    type="button"
                                    data-custom-button="true"
                                    onClick={() => {
                                        void handleCreateConversation();
                                    }}
                                    disabled={
                                        creating ||
                                        !selectedUserId
                                    }
                                    className="rounded-xl bg-blue-600 px-5 py-3 text-sm font-semibold text-white transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
                                >
                                    {creating
                                        ? "Creating..."
                                        : "Create conversation"}
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </main>
    );
}
