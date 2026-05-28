"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

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

    return (
        <div className="space-y-6 p-6">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold">
                        Messages
                    </h1>

                    <p className="text-gray-500">
                        Internal school messaging
                    </p>
                </div>

                <button
                    type="button"
                    onClick={() =>
                        setShowModal(true)
                    }
                    className="rounded-xl bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
                >
                    New Conversation
                </button>
            </div>

            {loading && (
                <div className="rounded-xl border p-4 text-sm text-gray-500">
                    Loading conversations...
                </div>
            )}

            {error && (
                <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">
                    {error}
                </div>
            )}

            {!loading &&
                !error &&
                conversations.length === 0 && (
                    <div className="rounded-xl border p-6 text-sm text-gray-500">
                        No conversations yet.
                    </div>
                )}

            <div className="space-y-4">
                {conversations.map(
                    (conversation) => (
                        <Link
                            key={conversation.id}
                            href={`/messages/${conversation.id}`}
                            className="block rounded-xl border p-4 transition hover:bg-gray-50"
                        >
                            <div className="flex items-center justify-between">
                                <h2 className="text-lg font-semibold">
                                    {conversation.title ||
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
                                            .join(
                                                ", ",
                                            ) ||
                                        "Untitled conversation"}
                                </h2>

                                <span className="rounded-full bg-blue-600 px-2 py-1 text-xs text-white">
                                    {
                                        conversation.conversation_type
                                    }
                                </span>
                            </div>

                            <p className="mt-2 text-sm text-gray-600">
                                Created{" "}
                                {new Date(
                                    conversation.created_at,
                                ).toLocaleString()}
                            </p>
                        </Link>
                    ),
                )}
            </div>

            {showModal && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
                    <div className="w-full max-w-md rounded-2xl bg-white p-6 shadow-xl">
                        <h2 className="text-xl font-bold">
                            New Conversation
                        </h2>

                        <div className="mt-4 space-y-4">
                            <div>
                                <label className="mb-1 block text-sm font-medium">
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
                                    className="w-full rounded-xl border px-4 py-3"
                                />
                            </div>

                            <div>
                                <label className="mb-1 block text-sm font-medium">
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
                                    className="w-full rounded-xl border px-4 py-3"
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

                            <div className="flex justify-end gap-3">
                                <button
                                    type="button"
                                    onClick={() =>
                                        setShowModal(
                                            false,
                                        )
                                    }
                                    className="rounded-xl border px-4 py-2"
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
                                    className="rounded-xl bg-blue-600 px-4 py-2 text-white hover:bg-blue-700 disabled:opacity-50"
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