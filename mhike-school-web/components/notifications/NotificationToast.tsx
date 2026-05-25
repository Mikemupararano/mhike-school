"use client";

import { useEffect } from "react";

import type { Notification } from "@/lib/notifications";

type NotificationToastProps = {
    notification: Notification | null;
    onClose: () => void;
};

export default function NotificationToast({
    notification,
    onClose,
}: NotificationToastProps) {
    useEffect(() => {
        if (!notification) {
            return;
        }

        const timeout = setTimeout(() => {
            onClose();
        }, 5000);

        return () => clearTimeout(timeout);
    }, [notification, onClose]);

    if (!notification) {
        return null;
    }

    return (
        <div className="fixed right-6 top-24 z-[200] w-96 rounded-2xl border border-gray-200 bg-white p-4 shadow-2xl">
            <div className="flex items-start gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-full bg-blue-50 text-xl">
                    🔔
                </div>

                <div className="flex-1">
                    <p className="font-semibold text-gray-900">
                        {notification.title}
                    </p>

                    <p className="mt-1 break-words text-sm text-gray-600">
                        {notification.message
                            .split(/(https?:\/\/[^\s]+)/g)
                            .map((part, index) => {
                                const isLink =
                                    /^https?:\/\/[^\s]+$/.test(part);

                                if (isLink) {
                                    return (
                                        <a
                                            key={index}
                                            href={part}
                                            target="_blank"
                                            rel="noopener noreferrer"
                                            className="font-medium text-blue-600 underline hover:text-blue-800"
                                        >
                                            {part}
                                        </a>
                                    );
                                }

                                return (
                                    <span key={index}>
                                        {part}
                                    </span>
                                );
                            })}
                    </p>
                </div>

                <button
                    type="button"
                    onClick={onClose}
                    className="text-sm font-bold text-gray-400 hover:text-gray-700"
                >
                    ×
                </button>
            </div>
        </div>
    );
}