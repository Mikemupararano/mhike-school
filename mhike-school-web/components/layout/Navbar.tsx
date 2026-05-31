"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { MessageCircle } from "lucide-react";
import { useRouter } from "next/navigation";

import BrandLogo from "@/components/layout/BrandLogo";
import NotificationDropdown from "@/components/notifications/NotificationDropdown";

import { clearToken } from "@/lib/api";
import {
    brandColors,
    brandShadows,
} from "@/lib/brand";
import { getUnreadMessageCount } from "@/lib/messages";
import {
    disconnectSocket,
    getSocket,
    SocketEvents,
} from "@/lib/socket";

type NavbarProps = {
    userId?: number | null;
    schoolId?: number | null;
    userName?: string;
    schoolName?: string;
    showRefresh?: boolean;
    refreshLabel?: string;
    onRefresh?: () => void;
    showLogout?: boolean;
};

export default function Navbar({
    userId,
    schoolId,
    userName = "Guest",
    schoolName,
    showRefresh = true,
    refreshLabel = "Refresh",
    onRefresh,
    showLogout = true,
}: NavbarProps) {
    const router = useRouter();

    const [unreadCount, setUnreadCount] =
        useState(0);

    const loadUnreadCount = useCallback(
        async () => {
            if (!userId) {
                setUnreadCount(0);
                return;
            }

            try {
                const response =
                    await getUnreadMessageCount();

                setUnreadCount(
                    response.unread_count ?? 0,
                );
            } catch (error) {
                console.error(
                    "Failed to load unread message count",
                    error,
                );
            }
        },
        [userId],
    );

    useEffect(() => {
        if (!userId) {
            setUnreadCount(0);
            return;
        }

        void loadUnreadCount();

        const socket = getSocket({
            user_id: userId,
            school_id: schoolId,
        });

        const handleRefresh = () => {
            void loadUnreadCount();
        };

        socket.on(
            SocketEvents.MESSAGES_REFRESH,
            handleRefresh,
        );

        socket.on(
            SocketEvents.MESSAGE_NEW,
            handleRefresh,
        );

        socket.on(
            SocketEvents.MESSAGE_READ,
            handleRefresh,
        );

        socket.on(
            SocketEvents.MESSAGE_DELIVERED,
            handleRefresh,
        );

        return () => {
            socket.off(
                SocketEvents.MESSAGES_REFRESH,
                handleRefresh,
            );

            socket.off(
                SocketEvents.MESSAGE_NEW,
                handleRefresh,
            );

            socket.off(
                SocketEvents.MESSAGE_READ,
                handleRefresh,
            );

            socket.off(
                SocketEvents.MESSAGE_DELIVERED,
                handleRefresh,
            );
        };
    }, [
        userId,
        schoolId,
        loadUnreadCount,
    ]);

    function handleLogout() {
        try {
            disconnectSocket();
        } catch {
            // Ignore socket cleanup errors
        }

        try {
            sessionStorage.clear();
            localStorage.clear();
        } catch {
            // Ignore storage cleanup errors
        }

        clearToken();

        router.replace("/login");

        setTimeout(() => {
            router.refresh();
        }, 50);
    }

    const trimmedName =
        userName.trim() || "Guest";

    const initial =
        trimmedName
            .charAt(0)
            .toUpperCase() || "U";

    return (
        <nav
            style={{
                width: "100%",
                background:
                    brandColors.navy,
                borderBottom:
                    "1px solid rgba(255,255,255,0.08)",
                boxShadow:
                    brandShadows.md,
                position: "sticky",
                top: 0,
                zIndex: 50,
            }}
        >
            <div
                style={{
                    width: "100%",
                    height: 76,
                    display: "flex",
                    alignItems:
                        "center",
                    justifyContent:
                        "space-between",
                    padding:
                        "0 28px",
                    gap: 18,
                }}
            >
                <BrandLogo
                    href="/"
                    showText
                    iconSize={40}
                    textSizeClass="text-xl sm:text-2xl"
                    className="shrink-0"
                />

                <div
                    style={{
                        display: "flex",
                        alignItems:
                            "center",
                        gap: 10,
                        flexShrink: 0,
                    }}
                >
                    <Link
                        href="/messages"
                        style={{
                            position:
                                "relative",
                            display:
                                "flex",
                            alignItems:
                                "center",
                            gap: 8,
                            padding:
                                "10px 14px",
                            borderRadius:
                                12,
                            background:
                                "rgba(255,255,255,0.08)",
                            border:
                                "1px solid rgba(255,255,255,0.15)",
                            color:
                                brandColors.white,
                            textDecoration:
                                "none",
                            fontWeight: 700,
                            fontSize: 13,
                        }}
                    >
                        <MessageCircle
                            size={16}
                        />

                        <span>
                            Messages
                        </span>

                        {unreadCount > 0 && (
                            <span
                                style={{
                                    minWidth: 22,
                                    height: 22,
                                    borderRadius:
                                        999,
                                    background:
                                        "#DC2626",
                                    color:
                                        "#FFFFFF",
                                    fontSize: 11,
                                    fontWeight: 800,
                                    display:
                                        "flex",
                                    alignItems:
                                        "center",
                                    justifyContent:
                                        "center",
                                    padding:
                                        "0 6px",
                                }}
                            >
                                {unreadCount > 99
                                    ? "99+"
                                    : unreadCount}
                            </span>
                        )}
                    </Link>

                    <NotificationDropdown
                        userId={userId}
                        schoolId={schoolId}
                    />

                    <div
                        style={{
                            display:
                                "flex",
                            alignItems:
                                "center",
                            gap: 12,
                            padding:
                                "8px 14px",
                            borderRadius:
                                999,
                            background:
                                "rgba(255,255,255,0.08)",
                            border:
                                "1px solid rgba(255,255,255,0.15)",
                            backdropFilter:
                                "blur(10px)",
                            WebkitBackdropFilter:
                                "blur(10px)",
                            minHeight: 46,
                        }}
                    >
                        <div
                            style={{
                                width: 30,
                                height: 30,
                                borderRadius:
                                    "50%",
                                background:
                                    "#DBEAFE",
                                color:
                                    brandColors.blueHover,
                                display:
                                    "grid",
                                placeItems:
                                    "center",
                                fontWeight: 900,
                                fontSize: 13,
                                flexShrink: 0,
                            }}
                        >
                            {initial}
                        </div>

                        <div
                            style={{
                                display:
                                    "flex",
                                flexDirection:
                                    "column",
                                lineHeight:
                                    1.1,
                            }}
                        >
                            <span
                                style={{
                                    fontWeight: 800,
                                    fontSize: 14,
                                    color:
                                        brandColors.white,
                                    whiteSpace:
                                        "nowrap",
                                }}
                            >
                                {
                                    trimmedName
                                }
                            </span>

                            {schoolName ? (
                                <span
                                    style={{
                                        fontSize: 12,
                                        fontWeight: 600,
                                        color:
                                            "rgba(255,255,255,0.84)",
                                        whiteSpace:
                                            "nowrap",
                                    }}
                                >
                                    {
                                        schoolName
                                    }
                                </span>
                            ) : null}
                        </div>
                    </div>

                    {showRefresh ? (
                        <button
                            type="button"
                            onClick={
                                onRefresh
                            }
                            style={{
                                padding:
                                    "8px 13px",
                                borderRadius:
                                    10,
                                border:
                                    "1px solid rgba(255,255,255,0.16)",
                                background:
                                    "rgba(255,255,255,0.10)",
                                color:
                                    brandColors.white,
                                fontWeight: 800,
                                fontSize: 13,
                                cursor:
                                    "pointer",
                            }}
                        >
                            {
                                refreshLabel
                            }
                        </button>
                    ) : null}

                    {showLogout ? (
                        <button
                            type="button"
                            onClick={
                                handleLogout
                            }
                            style={{
                                padding:
                                    "8px 13px",
                                borderRadius:
                                    10,
                                border:
                                    "none",
                                background:
                                    brandColors.white,
                                color:
                                    "#0F172A",
                                fontWeight: 800,
                                fontSize: 13,
                                cursor:
                                    "pointer",
                            }}
                        >
                            Logout
                        </button>
                    ) : null}
                </div>
            </div>
        </nav>
    );
}