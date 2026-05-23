"use client";

import { useEffect, useState } from "react";

import { apiGet } from "@/lib/api";

type NotificationMetrics = {
    total_deliveries: number;
    sent_deliveries: number;
    failed_deliveries: number;
    pending_deliveries: number;
};

type NotificationActivity = {
    id: number;
    channel: string;
    status: string;
    attempts: number;
    error_message: string | null;
    created_at: string;
    notification_title: string | null;
    school_id: number | null;
};

export default function AdminNotificationsPage() {
    const [metrics, setMetrics] =
        useState<NotificationMetrics | null>(null);

    const [activity, setActivity] =
        useState<NotificationActivity[]>([]);

    const [loading, setLoading] =
        useState<boolean>(true);

    const [error, setError] =
        useState<string | null>(null);

    async function loadDashboard(): Promise<void> {
        try {
            setLoading(true);
            setError(null);

            const metricsData =
                await apiGet<NotificationMetrics>(
                    "/notifications/admin/metrics",
                );

            const activityData =
                await apiGet<NotificationActivity[]>(
                    "/notifications/admin/activity",
                );

            setMetrics(metricsData);
            setActivity(activityData);
        } catch (err) {
            console.error(err);

            setError(
                "Failed to load notification monitoring data.",
            );
        } finally {
            setLoading(false);
        }
    }

    useEffect(() => {
        void loadDashboard();

        const interval = window.setInterval(() => {
            void loadDashboard();
        }, 15000);

        return () => window.clearInterval(interval);
    }, []);

    const cards = [
        {
            label: "Total deliveries",
            value: metrics?.total_deliveries ?? 0,
        },
        {
            label: "Sent deliveries",
            value: metrics?.sent_deliveries ?? 0,
        },
        {
            label: "Failed deliveries",
            value: metrics?.failed_deliveries ?? 0,
        },
        {
            label: "Pending queue",
            value: metrics?.pending_deliveries ?? 0,
        },
    ];

    return (
        <div className="space-y-6 p-6">
            <div>
                <h1 className="text-2xl font-bold text-gray-900">
                    Notification Monitoring
                </h1>

                <p className="mt-2 text-sm text-gray-500">
                    Monitor notification delivery,
                    queue health, and recent
                    platform activity.
                </p>
            </div>

            {error ? (
                <div className="rounded-2xl bg-red-50 p-4 text-sm text-red-600">
                    {error}
                </div>
            ) : null}

            <div className="grid gap-4 md:grid-cols-4">
                {cards.map((card) => (
                    <div
                        key={card.label}
                        className="rounded-2xl bg-white p-5 shadow-sm"
                    >
                        <p className="text-sm text-gray-500">
                            {card.label}
                        </p>

                        <p className="mt-2 text-2xl font-bold text-gray-900">
                            {loading
                                ? "..."
                                : card.value}
                        </p>
                    </div>
                ))}
            </div>

            <div className="rounded-2xl bg-white p-6 shadow-sm">
                <div className="mb-4 flex items-center justify-between">
                    <div>
                        <h2 className="text-lg font-semibold text-gray-900">
                            Recent Notification Activity
                        </h2>

                        <p className="mt-1 text-sm text-gray-500">
                            Latest delivery jobs
                            across email, push, and
                            SMS.
                        </p>
                    </div>

                    <button
                        type="button"
                        onClick={() => {
                            void loadDashboard();
                        }}
                        className="rounded-xl border px-4 py-2 text-sm hover:bg-gray-50"
                    >
                        Refresh
                    </button>
                </div>

                <div className="overflow-x-auto">
                    <table className="min-w-full text-left text-sm">
                        <thead className="text-gray-500">
                            <tr>
                                <th className="border-b py-3 pr-4">
                                    Notification
                                </th>

                                <th className="border-b py-3 pr-4">
                                    Channel
                                </th>

                                <th className="border-b py-3 pr-4">
                                    Status
                                </th>

                                <th className="border-b py-3 pr-4">
                                    Attempts
                                </th>

                                <th className="border-b py-3 pr-4">
                                    Created
                                </th>

                                <th className="border-b py-3">
                                    Error
                                </th>
                            </tr>
                        </thead>

                        <tbody>
                            {activity.map((item) => (
                                <tr key={item.id}>
                                    <td className="border-b py-3 pr-4">
                                        <div className="font-medium text-gray-900">
                                            {item.notification_title ??
                                                "Untitled"}
                                        </div>

                                        <div className="text-xs text-gray-500">
                                            School ID:{" "}
                                            {item.school_id ??
                                                "N/A"}
                                        </div>
                                    </td>

                                    <td className="border-b py-3 pr-4">
                                        {item.channel}
                                    </td>

                                    <td className="border-b py-3 pr-4">
                                        {item.status}
                                    </td>

                                    <td className="border-b py-3 pr-4">
                                        {item.attempts}
                                    </td>

                                    <td className="border-b py-3 pr-4">
                                        {new Date(
                                            item.created_at,
                                        ).toLocaleString()}
                                    </td>

                                    <td className="border-b py-3 text-red-600">
                                        {item.error_message ??
                                            "-"}
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>

                    {!loading &&
                        activity.length === 0 ? (
                        <div className="py-10 text-center text-sm text-gray-500">
                            No notification activity
                            found.
                        </div>
                    ) : null}
                </div>
            </div>
        </div>
    );
}