"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";

import BrandLogo from "@/components/layout/BrandLogo";

import { brand, brandColors, brandShadows } from "@/lib/brand";
import { getUnreadMessageCount } from "@/lib/messages";
import {
    getSocket,
    SocketEvents,
} from "@/lib/socket";

import {
    getSidebarSections,
    type SidebarRole,
    type SidebarSection,
} from "@/lib/navigation/sidebar";

import { useAuth } from "@/providers/AuthProvider";

import { UserRole } from "@/types/user";

type SidebarProps = {
    title?: string;
    sections?: SidebarSection[];
    role?: SidebarRole;
    collapsed?: boolean;
    className?: string;
};

function resolveSidebarRole(
    userRoles: UserRole[],
): SidebarRole {
    if (
        userRoles.includes(
            UserRole.PLATFORM_ADMIN,
        )
    ) {
        return UserRole.PLATFORM_ADMIN;
    }

    if (
        userRoles.includes(
            UserRole.SCHOOL_ADMIN,
        )
    ) {
        return UserRole.SCHOOL_ADMIN;
    }

    if (
        userRoles.includes(
            UserRole.TEACHER,
        )
    ) {
        return UserRole.TEACHER;
    }

    if (
        userRoles.includes(
            UserRole.STUDENT,
        )
    ) {
        return UserRole.STUDENT;
    }

    return UserRole.STUDENT;
}

export default function Sidebar({
    title = brand.name,
    sections,
    role,
    collapsed = false,
    className = "",
}: SidebarProps) {
    const pathname =
        usePathname();

    const { user } =
        useAuth();

    const [unreadCount, setUnreadCount] =
        useState(0);

    async function loadUnreadCount() {
        if (!user) {
            setUnreadCount(0);
            return;
        }

        try {
            const result =
                await getUnreadMessageCount();

            setUnreadCount(
                result.unread_count ?? 0,
            );
        } catch (error) {
            console.error(
                "Failed to load unread count",
                error,
            );
        }
    }

    useEffect(() => {
        if (!user) {
            return;
        }

        loadUnreadCount();

        const socket = getSocket({
            user_id: user.id,
            school_id:
                user.school_id,
        });

        const refresh = () => {
            loadUnreadCount();
        };

        socket.on(
            SocketEvents.MESSAGES_REFRESH,
            refresh,
        );

        socket.on(
            SocketEvents.MESSAGE_NEW,
            refresh,
        );

        socket.on(
            SocketEvents.MESSAGE_READ,
            refresh,
        );

        socket.on(
            SocketEvents.MESSAGE_DELIVERED,
            refresh,
        );

        return () => {
            socket.off(
                SocketEvents.MESSAGES_REFRESH,
                refresh,
            );

            socket.off(
                SocketEvents.MESSAGE_NEW,
                refresh,
            );

            socket.off(
                SocketEvents.MESSAGE_READ,
                refresh,
            );

            socket.off(
                SocketEvents.MESSAGE_DELIVERED,
                refresh,
            );
        };
    }, [user]);

    const resolvedRole: SidebarRole =
        role ??
        resolveSidebarRole(
            user?.roles ?? [],
        );

    const resolvedSections =
        sections ??
        getSidebarSections(
            resolvedRole,
        );

    return (
        <aside
            aria-label={`${title} sidebar navigation`}
            className={`h-screen text-white ${collapsed
                ? "w-24"
                : "w-80"
                } ${className}`}
            style={{
                borderRight: `1px solid ${brandColors.navySoft}`,
                background: `linear-gradient(180deg, ${brandColors.navy} 0%, ${brandColors.navySoft} 100%)`,
                boxShadow:
                    brandShadows.md,
            }}
        >
            <div className="flex h-full flex-col">
                <div
                    className={
                        collapsed
                            ? "border-b px-4 py-6"
                            : "border-b px-6 py-6"
                    }
                    style={{
                        borderColor:
                            "rgba(255,255,255,0.10)",
                    }}
                >
                    {collapsed ? (
                        <div className="flex justify-center">
                            <BrandLogo
                                href="/"
                                showText={
                                    false
                                }
                                iconSize={
                                    40
                                }
                                className="shrink-0"
                            />
                        </div>
                    ) : (
                        <div className="min-w-0 max-w-full">
                            <BrandLogo
                                href="/"
                                showText
                                iconSize={
                                    44
                                }
                                textSizeClass="text-2xl"
                                className="shrink-0"
                            />

                            <div className="mt-3 text-[17px] font-semibold text-slate-100">
                                {
                                    brand.tagline
                                }
                            </div>
                        </div>
                    )}
                </div>

                <nav className="flex-1 overflow-y-auto px-4 py-5">
                    {resolvedSections.map(
                        (
                            section,
                        ) => (
                            <div
                                key={
                                    section.title
                                }
                                className="mb-7"
                            >
                                {!collapsed && (
                                    <p className="mb-4 px-3 text-sm font-bold uppercase tracking-[0.18em] text-slate-100">
                                        {
                                            section.title
                                        }
                                    </p>
                                )}

                                <div className="grid gap-2">
                                    {section.items.map(
                                        (
                                            item,
                                        ) => {
                                            const active =
                                                pathname ===
                                                item.href ||
                                                (item.href !==
                                                    "/" &&
                                                    pathname.startsWith(
                                                        `${item.href}/`,
                                                    ));

                                            const Icon =
                                                item.icon;

                                            const isMessages =
                                                item.href ===
                                                "/messages";

                                            return (
                                                <Link
                                                    key={
                                                        item.href
                                                    }
                                                    href={
                                                        item.href
                                                    }
                                                    aria-current={
                                                        active
                                                            ? "page"
                                                            : undefined
                                                    }
                                                    title={
                                                        collapsed
                                                            ? item.label
                                                            : undefined
                                                    }
                                                    className={`flex items-center rounded-2xl px-4 py-4 transition-all duration-200 ${collapsed
                                                        ? "justify-center"
                                                        : "gap-3.5"
                                                        } ${active
                                                            ? "text-white shadow-sm ring-1 ring-white/12"
                                                            : "text-slate-100 hover:text-white"
                                                        }`}
                                                    style={{
                                                        background:
                                                            active
                                                                ? "rgba(255,255,255,0.12)"
                                                                : "transparent",
                                                    }}
                                                >
                                                    <span
                                                        className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl transition-colors"
                                                        style={{
                                                            background:
                                                                active
                                                                    ? "rgba(255,255,255,0.15)"
                                                                    : "rgba(255,255,255,0.10)",
                                                        }}
                                                    >
                                                        <Icon
                                                            size={
                                                                22
                                                            }
                                                        />
                                                    </span>

                                                    {!collapsed && (
                                                        <div className="flex min-w-0 flex-1 items-center justify-between gap-2">
                                                            <span className="truncate text-lg font-semibold">
                                                                {
                                                                    item.label
                                                                }
                                                            </span>

                                                            {isMessages &&
                                                                unreadCount >
                                                                0 && (
                                                                    <span className="flex h-6 min-w-[24px] items-center justify-center rounded-full bg-red-500 px-2 text-xs font-bold text-white">
                                                                        {unreadCount >
                                                                            99
                                                                            ? "99+"
                                                                            : unreadCount}
                                                                    </span>
                                                                )}
                                                        </div>
                                                    )}
                                                </Link>
                                            );
                                        },
                                    )}
                                </div>
                            </div>
                        ),
                    )}
                </nav>

                <div
                    className="px-4 py-4"
                    style={{
                        borderTop:
                            "1px solid rgba(255,255,255,0.10)",
                    }}
                />
            </div>
        </aside>
    );
}