"use client";

import { useEffect, useState } from "react";

import {
    NotificationPreferences,
    UpdateNotificationPreferencesPayload,
} from "@/lib/services/notificationPreferences";

interface NotificationPreferencesFormProps {
    preferences: NotificationPreferences;
    onSave: (
        payload: UpdateNotificationPreferencesPayload,
    ) => Promise<void>;
}

const rows: {
    key: keyof UpdateNotificationPreferencesPayload;
    label: string;
    description: string;
}[] = [
        {
            key: "attendance_alerts_enabled",
            label: "Attendance alerts",
            description: "Receive alerts about attendance changes.",
        },
        {
            key: "absence_notifications_enabled",
            label: "Absence notifications",
            description: "Be notified when an absence is recorded.",
        },
        {
            key: "persistent_absence_alerts_enabled",
            label: "Persistent absence alerts",
            description: "Receive alerts for repeated absence patterns.",
        },
        {
            key: "safeguarding_alerts_enabled",
            label: "Safeguarding alerts",
            description: "Receive safeguarding-related notifications.",
        },
        {
            key: "email_enabled",
            label: "Email notifications",
            description: "Allow notifications by email.",
        },
        {
            key: "push_enabled",
            label: "Push notifications",
            description: "Allow browser or app push notifications.",
        },
        {
            key: "sms_enabled",
            label: "SMS notifications",
            description: "Allow urgent notifications by SMS.",
        },
    ];

export default function NotificationPreferencesForm({
    preferences,
    onSave,
}: NotificationPreferencesFormProps) {
    const [form, setForm] =
        useState<UpdateNotificationPreferencesPayload>({
            attendance_alerts_enabled:
                preferences.attendance_alerts_enabled,
            absence_notifications_enabled:
                preferences.absence_notifications_enabled,
            persistent_absence_alerts_enabled:
                preferences.persistent_absence_alerts_enabled,
            safeguarding_alerts_enabled:
                preferences.safeguarding_alerts_enabled,
            email_enabled: preferences.email_enabled,
            push_enabled: preferences.push_enabled,
            sms_enabled: preferences.sms_enabled,
        });

    const [saving, setSaving] = useState(false);

    useEffect(() => {
        setForm({
            attendance_alerts_enabled:
                preferences.attendance_alerts_enabled,
            absence_notifications_enabled:
                preferences.absence_notifications_enabled,
            persistent_absence_alerts_enabled:
                preferences.persistent_absence_alerts_enabled,
            safeguarding_alerts_enabled:
                preferences.safeguarding_alerts_enabled,
            email_enabled: preferences.email_enabled,
            push_enabled: preferences.push_enabled,
            sms_enabled: preferences.sms_enabled,
        });
    }, [preferences]);

    function toggle(
        key: keyof UpdateNotificationPreferencesPayload,
    ) {
        setForm((current) => ({
            ...current,
            [key]: !Boolean(current[key]),
        }));
    }

    async function handleSubmit() {
        setSaving(true);

        try {
            await onSave(form);
        } finally {
            setSaving(false);
        }
    }

    return (
        <div className="rounded-2xl bg-white p-6 shadow-sm">
            <div className="mb-6">
                <h2 className="text-xl font-semibold text-gray-900">
                    Notification Preferences
                </h2>

                <p className="mt-1 text-sm text-gray-500">
                    Choose how and when you receive school updates.
                </p>
            </div>

            <div className="divide-y divide-gray-100">
                {rows.map((row) => {
                    const checked = Boolean(form[row.key]);

                    return (
                        <div
                            key={row.key}
                            className="flex items-center justify-between gap-4 py-4"
                        >
                            <div>
                                <p className="text-sm font-medium text-gray-900">
                                    {row.label}
                                </p>

                                <p className="mt-1 text-sm text-gray-500">
                                    {row.description}
                                </p>
                            </div>

                            <label className="inline-flex cursor-pointer items-center">
                                <input
                                    type="checkbox"
                                    checked={checked}
                                    onChange={() => toggle(row.key)}
                                    className="h-5 w-5 cursor-pointer"
                                />
                            </label>
                        </div>
                    );
                })}
            </div>

            <div className="mt-6 flex justify-end">
                <button
                    type="button"
                    onClick={handleSubmit}
                    disabled={saving}
                    className="rounded-xl bg-black px-5 py-2 text-sm font-medium text-white disabled:opacity-50"
                >
                    {saving ? "Saving..." : "Save preferences"}
                </button>
            </div>
        </div>
    );
}