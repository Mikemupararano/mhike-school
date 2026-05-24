"use client";

import { useEffect, useMemo, useState } from "react";

import {
    clearToken,
    getToken,
} from "@/lib/api";

import {
    getMyNotifications,
    markNotificationRead,
    Notification,
} from "@/lib/notifications";

import {
    disconnectSocket,
    getSocket,
} from "@/lib/socket";

export default function NotificationBell() {
    const [notifications, setNotifications] = useState<
        Notification[]
    >([]);

    const [open, setOpen] = useState(false);

    const [loading, setLoading] = useState(true);

    async function loadNotifications() {
        const token = getToken();

        if (!token) {
            setLoading(false);
            return;
        }

        try {
            const data =
                await getMyNotifications();

            setNotifications(data);
        } catch (err) {
            console.error(err);

            if (
                err instanceof Error &&
                (
                    err.message.includes(
                        "Invalid token",
                    ) ||
                    err.message.includes(
                        "Authorization",
                    )
                )
            ) {
                clearToken();

                disconnectSocket();

                return;
            }
        } finally {
            setLoading(false);
        }
    }

    async function handleMarkRead(
        notificationId: number,
    ) {
        try {
            const updated =
                await markNotificationRead(
                    notificationId,
                );

            setNotifications((current) =>
                current.map((notification) =>
                    notification.id === updated.id
                        ? updated
                        : notification,
                ),
            );
        } catch (error) {
            console.error(error);
        }
    }

    useEffect(() => {
        void loadNotifications();

        const token = getToken();

        if (!token) {
            return;
        }

        const socket = getSocket({});

        socket.on(
            "connect",
            () => {
                console.log(
                    "Socket connected:",
                    socket.id,
                );
            },
        );

        socket.on(
            "disconnect",
            () => {
                console.log(
                    "Socket disconnected",
                );
            },
        );

        socket.on(
            "notification:new",
            (
                notification: Notification,
            ) => {
                console.log(
                    "LIVE NOTIFICATION:",
                    notification,
                );

                setNotifications(
                    (current) => [
                        notification,
                        ...current,
                    ],
                );
            },
        );

        const interval = setInterval(() => {
            void loadNotifications();
        }, 15000);

        return () => {
            clearInterval(interval);

            socket.off("connect");

            socket.off("disconnect");

            socket.off(
                "notification:new",
            );
        };
    }, []);

    const unreadCount = useMemo(() => {
        return notifications.filter(
            (notification) =>
                !notification.is_read,
        ).length;
    }, [notifications]);

    return (
        <div className="relative">
            <button
                type="button"
                onClick={() =>
                    setOpen(!open)
                }
                className="relative rounded-full bg-white p-2 shadow-md transition hover:bg-gray-100"
            >
                <span className="text-xl">
                    🔔
                </span>

                {unreadCount > 0 && (
                    <span className="absolute -right-1 -top-1 flex h-5 min-w-5 items-center justify-center rounded-full bg-red-500 px-1 text-xs font-bold text-white">
                        {unreadCount}
                    </span>
                )}
            </button>

            {open && (
                <div className="absolute right-0 z-[100] mt-3 w-96 overflow-hidden rounded-2xl border border-gray-200 bg-white shadow-2xl">
                    <div className="border-b bg-gray-50 p-4">
                        <h2 className="text-lg font-semibold text-gray-900">
                            Notifications
                        </h2>
                    </div>

                    <div className="max-h-[500px] overflow-y-auto">
                        {loading ? (
                            <div className="p-4 text-sm text-gray-500">
                                Loading...
                            </div>
                        ) : notifications.length === 0 ? (
                            <div className="p-4 text-sm text-gray-500">
                                No notifications.
                            </div>
                        ) : (
                            notifications.map(
                                (
                                    notification,
                                ) => (
                                    <button
                                        key={
                                            notification.id
                                        }
                                        type="button"
                                        onClick={() =>
                                            handleMarkRead(
                                                notification.id,
                                            )
                                        }
                                        className={`block w-full cursor-pointer border-b p-4 text-left transition-all hover:bg-gray-100 ${notification.is_read
                                            ? "bg-white"
                                            : "bg-blue-50"
                                            }`}
                                    >
                                        <div className="flex items-start justify-between gap-4">
                                            <div className="flex-1">
                                                <p className="font-semibold text-gray-900">
                                                    {
                                                        notification.title
                                                    }
                                                </p>

                                                <p className="mt-1 text-sm text-gray-600">
                                                    {
                                                        notification.message
                                                    }
                                                </p>

                                                <p className="mt-2 text-xs text-gray-400">
                                                    {new Date(
                                                        notification.created_at,
                                                    ).toLocaleString()}
                                                </p>
                                            </div>

                                            {!notification.is_read && (
                                                <span className="mt-1 h-2 w-2 rounded-full bg-blue-600" />
                                            )}
                                        </div>
                                    </button>
                                ),
                            )
                        )}
                    </div>
                </div>
            )}
        </div>
    );
}