import { apiGet, apiPatch } from "@/lib/api";

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

export function getNotificationPreferences(
    token?: string,
): Promise<NotificationPreferences> {
    return apiGet<NotificationPreferences>(
        "/notification-preferences/me",
        token,
    );
}

export function updateNotificationPreferences(
    payload: UpdateNotificationPreferencesPayload,
    token?: string,
): Promise<NotificationPreferences> {
    return apiPatch<NotificationPreferences>(
        "/notification-preferences/me",
        payload,
        token,
    );
}