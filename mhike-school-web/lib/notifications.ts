import { apiGet, apiPatch } from "@/lib/api";

export type Notification = {
    id: number;
    title: string;
    message: string;
    category: string;
    priority: string;
    is_read: boolean;
    read_at: string | null;
    created_at: string;
};

export async function getMyNotifications(): Promise<Notification[]> {
    return apiGet<Notification[]>("/notifications/me");
}

export async function markNotificationRead(
    notificationId: number,
): Promise<Notification> {
    return apiPatch<Notification>(
        `/notifications/${notificationId}/read`,
    );
}