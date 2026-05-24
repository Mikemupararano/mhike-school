"use client";

import { useRouter } from "next/navigation";

import BrandLogo from "@/components/layout/BrandLogo";
import NotificationBell from "@/components/notifications/NotificationBell";
import { clearToken } from "@/lib/api";
import { brandColors, brandShadows } from "@/lib/brand";

type NavbarProps = {
    userName?: string;
    schoolName?: string;
    showRefresh?: boolean;
    refreshLabel?: string;
    onRefresh?: () => void;
    showLogout?: boolean;
};

export default function Navbar({
    userName = "Guest",
    schoolName,
    showRefresh = true,
    refreshLabel = "Refresh",
    onRefresh,
    showLogout = true,
}: NavbarProps) {
    const router = useRouter();

    function handleLogout() {
        clearToken();
        router.push("/login");
    }

    const trimmedName = userName.trim() || "Guest";

    const initial =
        trimmedName.charAt(0).toUpperCase() || "U";

    return (
        <nav
            style={{
                width: "100%",
                background: brandColors.navy,
                borderBottom:
                    "1px solid rgba(255,255,255,0.08)",
                boxShadow: brandShadows.md,
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
                    alignItems: "center",
                    justifyContent: "space-between",
                    padding: "0 28px",
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
                        alignItems: "center",
                        gap: 10,
                        flexShrink: 0,
                    }}
                >
                    <NotificationBell />

                    <div
                        style={{
                            display: "flex",
                            alignItems: "center",
                            gap: 12,
                            padding: "8px 14px",
                            borderRadius: 999,
                            background:
                                "rgba(255,255,255,0.08)",
                            border:
                                "1px solid rgba(255,255,255,0.15)",
                            backdropFilter: "blur(10px)",
                            WebkitBackdropFilter:
                                "blur(10px)",
                            minHeight: 46,
                        }}
                    >
                        <div
                            style={{
                                width: 30,
                                height: 30,
                                borderRadius: "50%",
                                background: "#DBEAFE",
                                color:
                                    brandColors.blueHover,
                                display: "grid",
                                placeItems: "center",
                                fontWeight: 900,
                                fontSize: 13,
                                flexShrink: 0,
                            }}
                        >
                            {initial}
                        </div>

                        <div
                            style={{
                                display: "flex",
                                flexDirection: "column",
                                lineHeight: 1.1,
                            }}
                        >
                            <span
                                style={{
                                    fontWeight: 800,
                                    fontSize: 14,
                                    color:
                                        brandColors.white,
                                    whiteSpace: "nowrap",
                                }}
                            >
                                {trimmedName}
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
                                    {schoolName}
                                </span>
                            ) : null}
                        </div>
                    </div>

                    {showRefresh ? (
                        <button
                            type="button"
                            onClick={onRefresh}
                            style={{
                                padding: "8px 13px",
                                borderRadius: 10,
                                border:
                                    "1px solid rgba(255,255,255,0.16)",
                                background:
                                    "rgba(255,255,255,0.10)",
                                color:
                                    brandColors.white,
                                fontWeight: 800,
                                fontSize: 13,
                                cursor: "pointer",
                                backdropFilter:
                                    "blur(8px)",
                                WebkitBackdropFilter:
                                    "blur(8px)",
                            }}
                        >
                            {refreshLabel}
                        </button>
                    ) : null}

                    {showLogout ? (
                        <button
                            type="button"
                            onClick={handleLogout}
                            style={{
                                padding: "8px 13px",
                                borderRadius: 10,
                                border: "none",
                                background:
                                    brandColors.white,
                                color: "#0F172A",
                                fontWeight: 800,
                                fontSize: 13,
                                cursor: "pointer",
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