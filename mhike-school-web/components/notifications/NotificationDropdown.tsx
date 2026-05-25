"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { Bell, CheckCheck } from "lucide-react";

import {
    getMyNotifications,
    markNotificationRead,
} from "@/lib/notifications";
import { getSocket } from "@/lib/socket";

export type NotificationItem = {
    id: number;
    title: string;
    message: string;
    category: string;
    priority: string;
    is_read: boolean;
    created_at: string;
};

type NotificationDropdownProps = {
    userId?: number | null;
    schoolId?: number | null;
    refreshKey?: number;
};

function formatRelativeTime(dateString: string) {
    const minutes = Math.floor(
        (Date.now() - new Date(dateString).getTime()) / 60000,
    );

    if (minutes < 1) return "Just now";
    if (minutes < 60) return `${minutes} min ago`;

    const hours = Math.floor(minutes / 60);
    if (hours < 24) return `${hours} hr ago`;

    return `${Math.floor(hours / 24)} day ago`;
}

function extractFirstLink(text: string): string | null {
    const match = text.match(/(https?:\/\/[^\s]+)/);
    return match ? match[0] : null;
}

export default function NotificationDropdown({
    userId,
    schoolId,
    refreshKey,
}: NotificationDropdownProps) {
    const [open, setOpen] = useState(false);
    const [notifications, setNotifications] = useState<NotificationItem[]>([]);
    const [loading, setLoading] = useState(false);

    const dropdownRef = useRef<HTMLDivElement | null>(null);

    const unreadCount = notifications.filter(
        (notification) => !notification.is_read,
    ).length;

    async function loadNotifications() {
        setLoading(true);

        try {
            const data = await getMyNotifications();
            setNotifications(data);
        } catch (error) {
            console.error(error);
        } finally {
            setLoading(false);
        }
    }

    async function handleMarkRead(notificationId: number) {
        try {
            await markNotificationRead(notificationId);

            setNotifications((prev) =>
                prev.map((notification) =>
                    notification.id === notificationId
                        ? { ...notification, is_read: true }
                        : notification,
                ),
            );
        } catch (error) {
            console.error(error);
        }
    }

    async function handleMarkAllRead() {
        const unread = notifications.filter(
            (notification) => !notification.is_read,
        );

        try {
            await Promise.all(
                unread.map((notification) =>
                    markNotificationRead(notification.id),
                ),
            );

            setNotifications((prev) =>
                prev.map((notification) => ({
                    ...notification,
                    is_read: true,
                })),
            );
        } catch (error) {
            console.error(error);
        }
    }

    useEffect(() => {
        void loadNotifications();
    }, [refreshKey]);

    useEffect(() => {
        if (!userId && !schoolId) {
            return;
        }

        const socket = getSocket({
            user_id: userId,
            school_id: schoolId,
        });

        socket.on("notification:new", (notification: NotificationItem) => {
            setNotifications((current) => [
                notification,
                ...current.filter((item) => item.id !== notification.id),
            ]);
        });

        return () => {
            socket.off("notification:new");
        };
    }, [userId, schoolId]);

    useEffect(() => {
        function handleClickOutside(event: MouseEvent) {
            if (
                dropdownRef.current &&
                !dropdownRef.current.contains(event.target as Node)
            ) {
                setOpen(false);
            }
        }

        document.addEventListener("mousedown", handleClickOutside);

        return () => {
            document.removeEventListener("mousedown", handleClickOutside);
        };
    }, []);

    return (
        <div className="relative" ref={dropdownRef}>
            <button
                type="button"
                onClick={() => setOpen(!open)}
                className="relative flex h-12 w-12 items-center justify-center rounded-full bg-white shadow"
            >
                <Bell className="h-5 w-5 text-slate-700" />

                {unreadCount > 0 && (
                    <span className="absolute -right-1 -top-1 flex h-6 min-w-[24px] items-center justify-center rounded-full bg-red-500 px-1 text-xs font-bold text-white">
                        {unreadCount}
                    </span>
                )}
            </button>

            {open && (
                <div className="absolute right-0 top-14 z-[300] w-[420px] rounded-2xl border border-gray-200 bg-white shadow-2xl">
                    <div className="flex items-center justify-between border-b border-gray-100 p-4">
                        <div>
                            <h2 className="text-lg font-bold text-gray-900">
                                Notifications
                            </h2>

                            <p className="text-sm text-gray-500">
                                {unreadCount} unread
                            </p>
                        </div>

                        <button
                            type="button"
                            onClick={() => void handleMarkAllRead()}
                            className="flex items-center gap-2 rounded-xl border border-gray-200 px-3 py-2 text-sm font-medium hover:bg-gray-50"
                        >
                            <CheckCheck className="h-4 w-4" />
                            Mark all read
                        </button>
                    </div>

                    <div className="max-h-[500px] overflow-y-auto">
                        {loading ? (
                            <div className="p-6 text-sm text-gray-500">
                                Loading notifications...
                            </div>
                        ) : notifications.length === 0 ? (
                            <div className="p-6 text-sm text-gray-500">
                                No notifications yet.
                            </div>
                        ) : (
                            notifications.map((notification) => {
                                const link = extractFirstLink(
                                    notification.message,
                                );

                                return (
                                    <div
                                        key={notification.id}
                                        className={`border-b border-gray-100 p-4 transition hover:bg-gray-50 ${!notification.is_read
                                            ? "bg-blue-50/40"
                                            : ""
                                            }`}
                                    >
                                        <div className="flex items-start justify-between gap-3">
                                            <div className="flex-1">
                                                <div className="flex items-center gap-2">
                                                    <h3 className="font-semibold text-gray-900">
                                                        {notification.title}
                                                    </h3>

                                                    {!notification.is_read && (
                                                        <span className="h-2 w-2 rounded-full bg-blue-600" />
                                                    )}
                                                </div>

                                                <p className="mt-1 whitespace-pre-wrap break-words text-sm text-gray-600">
                                                    {notification.message}
                                                </p>

                                                {link && (
                                                    <Link
                                                        href={link}
                                                        target="_blank"
                                                        className="mt-2 inline-block text-sm font-medium text-blue-600 hover:underline"
                                                    >
                                                        Open resource
                                                    </Link>
                                                )}

                                                <div className="mt-3 flex items-center justify-between">
                                                    <span className="text-xs text-gray-400">
                                                        {formatRelativeTime(
                                                            notification.created_at,
                                                        )}
                                                    </span>

                                                    {!notification.is_read && (
                                                        <button
                                                            type="button"
                                                            onClick={() =>
                                                                void handleMarkRead(
                                                                    notification.id,
                                                                )
                                                            }
                                                            className="text-xs font-semibold text-blue-600 hover:underline"
                                                        >
                                                            Mark read
                                                        </button>
                                                    )}
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                );
                            })
                        )}
                    </div>
                </div>
            )}
        </div>
    );
}