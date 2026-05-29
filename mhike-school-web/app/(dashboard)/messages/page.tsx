"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { MessageCircle, Plus } from "lucide-react";

import {
    createConversation,
    getConversations,
    getSchoolMessageUsers,
} from "@/lib/messages";

import type {
    Conversation,
    SchoolMessageUser,
} from "@/types/message";

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

    const [loading, setLoading] =
        useState(true);

    const [creating, setCreating] =
        useState(false);

    const [showModal, setShowModal] =
        useState(false);

    const [error, setError] =
        useState<string | null>(null);

    async function loadData() {
        try {
            setLoading(true);

            const [
                conversationData,
                userData,
            ] = await Promise.all([
                getConversations(),
                getSchoolMessageUsers(),
            ]);

            setConversations(conversationData);
            setUsers(userData);

            setError(null);
        } catch (err) {
            console.error(err);

            setError(
                "Unable to load messages.",
            );
        } finally {
            setLoading(false);
        }
    }

    useEffect(() => {
        loadData();
    }, []);

    async function handleCreateConversation() {
        if (!selectedUserId) {
            return;
        }

        try {
            setCreating(true);

            const conversation =
                await createConversation({
                    participant_ids: [
                        Number(selectedUserId),
                    ],
                    title:
                        conversationTitle.trim() ||
                        null,
                    conversation_type:
                        "direct",
                });

            setShowModal(false);

            setConversationTitle("");
            setSelectedUserId("");

            router.push(
                `/messages/${conversation.id}`,
            );
        } catch (err) {
            console.error(err);

            alert(
                "Failed to create conversation.",
            );
        } finally {
            setCreating(false);
        }
    }

    const sortedConversations = useMemo(
        () =>
            [...conversations].sort(
                (a, b) =>
                    new Date(
                        b.updated_at ||
                        b.created_at,
                    ).getTime() -
                    new Date(
                        a.updated_at ||
                        a.created_at,
                    ).getTime(),
            ),
        [conversations],
    );

    return (
        <div className="min-h-screen bg-gray-50 p-6">
            <div className="mx-auto max-w-5xl">
                <div className="mb-8 flex items-center justify-between">
                    <div>
                        <h1 className="text-3xl font-bold text-gray-900">
                            Messages
                        </h1>

                        <p className="mt-1 text-gray-500">
                            Internal school messaging
                        </p>
                    </div>

                    <button
                        type="button"
                        onClick={() =>
                            setShowModal(true)
                        }
                        className="flex items-center gap-2 rounded-2xl bg-blue-600 px-5 py-3 text-sm font-medium text-white shadow-sm transition hover:bg-blue-700"
                    >
                        <Plus className="h-4 w-4" />
                        New Conversation
                    </button>
                </div>

                {loading && (
                    <div className="rounded-2xl border border-gray-200 bg-white p-5 text-sm text-gray-500 shadow-sm">
                        Loading conversations...
                    </div>
                )}

                {error && (
                    <div className="rounded-2xl border border-red-200 bg-red-50 p-5 text-sm text-red-700">
                        {error}
                    </div>
                )}

                {!loading &&
                    !error &&
                    sortedConversations.length ===
                    0 && (
                        <div className="flex flex-col items-center justify-center rounded-3xl border border-dashed border-gray-300 bg-white py-20 text-center shadow-sm">
                            <MessageCircle className="mb-4 h-12 w-12 text-gray-300" />

                            <h2 className="text-lg font-semibold text-gray-700">
                                No conversations yet
                            </h2>

                            <p className="mt-1 text-sm text-gray-500">
                                Start a new
                                conversation with a
                                staff member.
                            </p>
                        </div>
                    )}

                <div className="space-y-4">
                    {sortedConversations.map(
                        (conversation) => {
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
                                    .filter(
                                        Boolean,
                                    )
                                    .join(", ");

                            const title =
                                conversation.title ||
                                participantNames ||
                                "Untitled conversation";

                            const latestMessage =
                                conversation.messages?.[
                                conversation
                                    .messages
                                    .length - 1
                                ];

                            return (
                                <Link
                                    key={
                                        conversation.id
                                    }
                                    href={`/messages/${conversation.id}`}
                                    className="group block rounded-3xl border border-gray-200 bg-white p-5 shadow-sm transition-all hover:-translate-y-0.5 hover:border-blue-200 hover:shadow-md"
                                >
                                    <div className="flex items-start gap-4">
                                        <div className="flex h-14 w-14 shrink-0 items-center justify-center rounded-full bg-blue-600 text-lg font-semibold text-white">
                                            {title
                                                .charAt(
                                                    0,
                                                )
                                                .toUpperCase()}
                                        </div>

                                        <div className="min-w-0 flex-1">
                                            <div className="flex items-start justify-between gap-4">
                                                <div>
                                                    <h2 className="truncate text-lg font-semibold text-gray-900">
                                                        {
                                                            title
                                                        }
                                                    </h2>

                                                    <p className="mt-1 text-sm text-gray-500">
                                                        {
                                                            conversation.conversation_type
                                                        }
                                                    </p>
                                                </div>

                                                <span className="shrink-0 text-xs text-gray-400">
                                                    {new Date(
                                                        conversation.updated_at ||
                                                        conversation.created_at,
                                                    ).toLocaleDateString()}
                                                </span>
                                            </div>

                                            <div className="mt-4">
                                                {latestMessage ? (
                                                    <p className="truncate text-sm text-gray-600">
                                                        {
                                                            latestMessage.body
                                                        }
                                                    </p>
                                                ) : (
                                                    <p className="text-sm italic text-gray-400">
                                                        No
                                                        messages
                                                        yet
                                                    </p>
                                                )}
                                            </div>
                                        </div>
                                    </div>
                                </Link>
                            );
                        },
                    )}
                </div>
            </div>

            {showModal && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm">
                    <div className="w-full max-w-md rounded-3xl bg-white p-6 shadow-2xl">
                        <h2 className="text-2xl font-bold text-gray-900">
                            New Conversation
                        </h2>

                        <p className="mt-1 text-sm text-gray-500">
                            Start a private staff
                            conversation.
                        </p>

                        <div className="mt-6 space-y-5">
                            <div>
                                <label className="mb-2 block text-sm font-medium text-gray-700">
                                    Title
                                </label>

                                <input
                                    type="text"
                                    value={
                                        conversationTitle
                                    }
                                    onChange={(
                                        event,
                                    ) =>
                                        setConversationTitle(
                                            event.target
                                                .value,
                                        )
                                    }
                                    placeholder="Optional title"
                                    className="w-full rounded-2xl border border-gray-200 px-4 py-3 outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-200"
                                />
                            </div>

                            <div>
                                <label className="mb-2 block text-sm font-medium text-gray-700">
                                    Recipient
                                </label>

                                <select
                                    value={
                                        selectedUserId
                                    }
                                    onChange={(
                                        event,
                                    ) =>
                                        setSelectedUserId(
                                            event.target
                                                .value,
                                        )
                                    }
                                    className="w-full rounded-2xl border border-gray-200 px-4 py-3 outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-200"
                                >
                                    <option value="">
                                        Select a user
                                    </option>

                                    {users.map(
                                        (user) => (
                                            <option
                                                key={
                                                    user.id
                                                }
                                                value={
                                                    user.id
                                                }
                                            >
                                                {
                                                    user.full_name
                                                }{" "}
                                                (
                                                {
                                                    user.role
                                                }
                                                )
                                            </option>
                                        ),
                                    )}
                                </select>
                            </div>

                            <div className="flex justify-end gap-3 pt-2">
                                <button
                                    type="button"
                                    onClick={() =>
                                        setShowModal(
                                            false,
                                        )
                                    }
                                    className="rounded-2xl border border-gray-200 px-5 py-3 text-sm font-medium text-gray-700 transition hover:bg-gray-100"
                                >
                                    Cancel
                                </button>

                                <button
                                    type="button"
                                    onClick={
                                        handleCreateConversation
                                    }
                                    disabled={
                                        creating
                                    }
                                    className="rounded-2xl bg-blue-600 px-5 py-3 text-sm font-medium text-white transition hover:bg-blue-700 disabled:opacity-50"
                                >
                                    {creating
                                        ? "Creating..."
                                        : "Create"}
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}