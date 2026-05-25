"use client";

import { useEffect, useState } from "react";

import {
    getMyNotificationPreferences,
    NotificationPreferences,
    updateMyNotificationPreferences,
} from "@/lib/notificationPreferences";

type ToggleCardProps = {
    title: string;
    description: string;
    checked: boolean;
    onChange: () => void;
};

function ToggleCard({
    title,
    description,
    checked,
    onChange,
}: ToggleCardProps) {
    return (
        <div className="flex items-center justify-between rounded-2xl border border-gray-200 bg-white p-5 shadow-sm">
            <div>
                <h3 className="text-base font-semibold text-gray-900">
                    {title}
                </h3>

                <p className="mt-1 text-sm text-gray-500">
                    {description}
                </p>
            </div>

            <button
                type="button"
                onClick={onChange}
                className={`relative h-7 w-14 rounded-full transition ${checked
                    ? "bg-blue-600"
                    : "bg-gray-300"
                    }`}
            >
                <span
                    className={`absolute top-1 h-5 w-5 rounded-full bg-white transition ${checked
                        ? "left-8"
                        : "left-1"
                        }`}
                />
            </button>
        </div>
    );
}

export default function ProfilePage() {
    const [
        preferences,
        setPreferences,
    ] = useState<NotificationPreferences | null>(
        null,
    );

    const [loading, setLoading] =
        useState(true);

    const [saving, setSaving] =
        useState(false);

    async function loadPreferences() {
        try {
            const data =
                await getMyNotificationPreferences();

            setPreferences(data);
        } catch (error) {
            console.error(error);
        } finally {
            setLoading(false);
        }
    }

    async function updatePreference(
        field: keyof NotificationPreferences,
        value: boolean,
    ) {
        if (!preferences) {
            return;
        }

        setSaving(true);

        try {
            const updated =
                await updateMyNotificationPreferences(
                    {
                        [field]: value,
                    },
                );

            setPreferences(updated);
        } catch (error) {
            console.error(error);
        } finally {
            setSaving(false);
        }
    }

    useEffect(() => {
        void loadPreferences();
    }, []);

    if (loading) {
        return (
            <div className="p-8">
                Loading preferences...
            </div>
        );
    }

    if (!preferences) {
        return (
            <div className="p-8 text-red-500">
                Failed to load preferences.
            </div>
        );
    }

    return (
        <div className="mx-auto max-w-4xl space-y-6">
            <div>
                <h1 className="text-3xl font-bold text-gray-900">
                    Notification Preferences
                </h1>

                <p className="mt-2 text-gray-500">
                    Control how you receive school
                    alerts and updates.
                </p>
            </div>

            <div className="grid gap-4">
                <ToggleCard
                    title="Email Notifications"
                    description="Receive notifications by email."
                    checked={
                        preferences.email_enabled
                    }
                    onChange={() =>
                        void updatePreference(
                            "email_enabled",
                            !preferences.email_enabled,
                        )
                    }
                />

                <ToggleCard
                    title="Push Notifications"
                    description="Receive realtime in-app notifications."
                    checked={
                        preferences.push_enabled
                    }
                    onChange={() =>
                        void updatePreference(
                            "push_enabled",
                            !preferences.push_enabled,
                        )
                    }
                />

                <ToggleCard
                    title="SMS Notifications"
                    description="Receive urgent SMS alerts."
                    checked={
                        preferences.sms_enabled
                    }
                    onChange={() =>
                        void updatePreference(
                            "sms_enabled",
                            !preferences.sms_enabled,
                        )
                    }
                />

                <ToggleCard
                    title="Attendance Alerts"
                    description="Receive attendance-related alerts."
                    checked={
                        preferences.attendance_alerts_enabled
                    }
                    onChange={() =>
                        void updatePreference(
                            "attendance_alerts_enabled",
                            !preferences.attendance_alerts_enabled,
                        )
                    }
                />

                <ToggleCard
                    title="Absence Notifications"
                    description="Receive absence notifications."
                    checked={
                        preferences.absence_notifications_enabled
                    }
                    onChange={() =>
                        void updatePreference(
                            "absence_notifications_enabled",
                            !preferences.absence_notifications_enabled,
                        )
                    }
                />

                <ToggleCard
                    title="Persistent Absence Alerts"
                    description="Receive persistent absence alerts."
                    checked={
                        preferences.persistent_absence_alerts_enabled
                    }
                    onChange={() =>
                        void updatePreference(
                            "persistent_absence_alerts_enabled",
                            !preferences.persistent_absence_alerts_enabled,
                        )
                    }
                />

                <ToggleCard
                    title="Safeguarding Alerts"
                    description="Receive safeguarding notifications."
                    checked={
                        preferences.safeguarding_alerts_enabled
                    }
                    onChange={() =>
                        void updatePreference(
                            "safeguarding_alerts_enabled",
                            !preferences.safeguarding_alerts_enabled,
                        )
                    }
                />
            </div>

            {saving && (
                <div className="text-sm text-blue-600">
                    Saving preferences...
                </div>
            )}
        </div>
    );
}