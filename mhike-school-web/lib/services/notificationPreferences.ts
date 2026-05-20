import axios from "axios";

export interface NotificationPreferences {
    id: number;
    school_id: number;
    user_id: number;
    attendance_alerts_enabled: boolean;
    absence_notifications_enabled: boolean;
    persistent_absence_alerts_enabled: boolean;
    safeguarding_alerts_enabled: boolean;
    email_enabled: boolean;
    push_enabled: boolean;
    sms_enabled: boolean;
}

export interface UpdateNotificationPreferencesPayload {
    attendance_alerts_enabled?: boolean;
    absence_notifications_enabled?: boolean;
    persistent_absence_alerts_enabled?: boolean;
    safeguarding_alerts_enabled?: boolean;
    email_enabled?: boolean;
    push_enabled?: boolean;
    sms_enabled?: boolean;
}

const API_BASE_URL =
    process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function getNotificationPreferences(
    token: string,
): Promise<NotificationPreferences> {
    const response = await axios.get(
        `${API_BASE_URL}/api/v1/notification-preferences/me`,
        {
            headers: {
                Authorization: `Bearer ${token}`,
            },
        },
    );

    return response.data;
}

export async function updateNotificationPreferences(
    token: string,
    payload: UpdateNotificationPreferencesPayload,
): Promise<NotificationPreferences> {
    const response = await axios.put(
        `${API_BASE_URL}/api/v1/notification-preferences/me`,
        payload,
        {
            headers: {
                Authorization: `Bearer ${token}`,
            },
        },
    );

    return response.data;
}