"use client";

import { useEffect, useState } from "react";

import NotificationPreferencesForm from "@/components/settings/NotificationPreferencesForm";

import {
    getNotificationPreferences,
    NotificationPreferences,
    updateNotificationPreferences,
    UpdateNotificationPreferencesPayload,
} from "@/lib/services/notificationPreferences";

export default function NotificationPreferencesPage() {
    const [preferences, setPreferences] =
        useState<NotificationPreferences | null>(null);

    const [loading, setLoading] = useState(true);

    const [error, setError] = useState<string | null>(null);

    async function loadPreferences() {
        try {
            setLoading(true);
            setError(null);

            const token = localStorage.getItem("token");

            if (!token) {
                throw new Error("Authentication token not found.");
            }

            const data = await getNotificationPreferences(token);

            setPreferences(data);
        } catch (err) {
            console.error(err);

            setError("Failed to load notification preferences.");
        } finally {
            setLoading(false);
        }
    }

    async function handleSave(
        payload: UpdateNotificationPreferencesPayload,
    ) {
        try {
            const token = localStorage.getItem("token");

            if (!token) {
                throw new Error("Authentication token not found.");
            }

            const updated = await updateNotificationPreferences(
                token,
                payload,
            );

            setPreferences(updated);

            alert("Notification preferences updated.");
        } catch (err) {
            console.error(err);

            alert("Failed to update notification preferences.");
        }
    }

    useEffect(() => {
        loadPreferences();
    }, []);

    if (loading) {
        return (
            <div className="p-6">
                <div className="rounded-2xl bg-white p-6 shadow-sm">
                    <p className="text-sm text-gray-500">
                        Loading notification preferences...
                    </p>
                </div>
            </div>
        );
    }

    if (error || !preferences) {
        return (
            <div className="p-6">
                <div className="rounded-2xl bg-red-50 p-6 shadow-sm">
                    <p className="text-sm text-red-600">
                        {error || "Unable to load preferences."}
                    </p>
                </div>
            </div>
        );
    }

    return (
        <div className="p-6">
            <div className="mb-6">
                <h1 className="text-2xl font-bold text-gray-900">
                    Notification Settings
                </h1>

                <p className="mt-2 text-sm text-gray-500">
                    Manage how you receive school notifications and alerts.
                </p>
            </div>

            <NotificationPreferencesForm
                preferences={preferences}
                onSave={handleSave}
            />
        </div>
    );
}