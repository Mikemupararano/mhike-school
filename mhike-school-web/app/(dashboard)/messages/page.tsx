"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { getConversations } from "@/lib/messages";
import type { Conversation } from "@/types/message";

export default function MessagesPage() {
    const [conversations, setConversations] = useState<Conversation[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        async function loadConversations() {
            try {
                const data = await getConversations();
                setConversations(data);
            } catch (err) {
                console.error(err);
                setError("Unable to load conversations.");
            } finally {
                setLoading(false);
            }
        }

        loadConversations();
    }, []);

    return (
        <div className="space-y-6 p-6">
            <div>
                <h1 className="text-3xl font-bold">Messages</h1>

                <p className="text-gray-500">
                    Internal school messaging
                </p>
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

            {!loading && !error && conversations.length === 0 && (
                <div className="rounded-xl border p-6 text-sm text-gray-500">
                    No conversations yet.
                </div>
            )}

            <div className="space-y-4">
                {conversations.map((conversation) => (
                    <Link
                        key={conversation.id}
                        href={`/messages/${conversation.id}`}
                        className="block rounded-xl border p-4 transition hover:bg-gray-50"
                    >
                        <div className="flex items-center justify-between">
                            <h2 className="text-lg font-semibold">
                                {conversation.title || "Untitled conversation"}
                            </h2>

                            <span className="rounded-full bg-blue-600 px-2 py-1 text-xs text-white">
                                {conversation.conversation_type}
                            </span>
                        </div>

                        <p className="mt-2 text-sm text-gray-600">
                            Created{" "}
                            {new Date(
                                conversation.created_at,
                            ).toLocaleString()}
                        </p>
                    </Link>
                ))}
            </div>
        </div>
    );
}