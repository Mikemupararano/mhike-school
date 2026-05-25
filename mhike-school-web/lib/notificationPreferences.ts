import { apiGet, apiPatch } from "@/lib/api";

export type NotificationPreferences = {
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
};

export type NotificationPreferenceUpdate = Partial<
    Pick<
        NotificationPreferences,
        | "attendance_alerts_enabled"
        | "absence_notifications_enabled"
        | "persistent_absence_alerts_enabled"
        | "safeguarding_alerts_enabled"
        | "email_enabled"
        | "push_enabled"
        | "sms_enabled"
    >
>;

export async function getMyNotificationPreferences(): Promise<NotificationPreferences> {
    return apiGet<NotificationPreferences>(
        "/notification-preferences/me",
    );
}

export async function updateMyNotificationPreferences(
    payload: NotificationPreferenceUpdate,
): Promise<NotificationPreferences> {
    return apiPatch<NotificationPreferences>(
        "/notification-preferences/me",
        payload,
    );
}