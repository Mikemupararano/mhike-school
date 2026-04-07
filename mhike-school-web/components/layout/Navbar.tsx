"use client";

import Image from "next/image";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { clearToken } from "@/lib/api";

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
    const initial = trimmedName.charAt(0).toUpperCase() || "U";

    return (
        <nav
            style={{
                width: "100%",
                background: "linear-gradient(90deg, #0F2A3F 0%, #1E3A5F 100%)",
                borderBottom: "1px solid rgba(255,255,255,0.08)",
                boxShadow: "0 8px 24px rgba(15, 23, 42, 0.22)",
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
                <Link
                    href="/"
                    style={{
                        display: "flex",
                        alignItems: "center",
                        textDecoration: "none",
                        flexShrink: 0,
                    }}
                >
                    <Image
                        src="/branding/logo-navbar.svg"
                        alt="Mhike School"
                        width={220}
                        height={48}
                        priority
                        style={{
                            height: 46,
                            width: "auto",
                            objectFit: "contain",
                            display: "block",
                        }}
                    />
                </Link>

                <div
                    style={{
                        display: "flex",
                        alignItems: "center",
                        gap: 10,
                        flexShrink: 0,
                    }}
                >
                    <div
                        style={{
                            display: "flex",
                            alignItems: "center",
                            gap: 10,
                            padding: "6px 12px",
                            borderRadius: 999,
                            background: "rgba(255,255,255,0.08)",
                            border: "1px solid rgba(255,255,255,0.15)",
                            backdropFilter: "blur(10px)",
                            WebkitBackdropFilter: "blur(10px)",
                            minHeight: 42,
                        }}
                    >
                        <div
                            style={{
                                width: 28,
                                height: 28,
                                borderRadius: "50%",
                                background: "#DBEAFE",
                                color: "#1D4ED8",
                                display: "grid",
                                placeItems: "center",
                                fontWeight: 900,
                                fontSize: 12,
                                flexShrink: 0,
                            }}
                        >
                            {initial}
                        </div>

                        <div
                            style={{
                                display: "flex",
                                flexDirection: "column",
                                lineHeight: 1.05,
                            }}
                        >
                            <span
                                style={{
                                    fontWeight: 800,
                                    fontSize: 13,
                                    color: "#FFFFFF",
                                    whiteSpace: "nowrap",
                                }}
                            >
                                {trimmedName}
                            </span>

                            {schoolName ? (
                                <span
                                    style={{
                                        fontSize: 11,
                                        color: "rgba(255,255,255,0.82)",
                                        whiteSpace: "nowrap",
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
                                border: "1px solid rgba(255,255,255,0.16)",
                                background: "rgba(255,255,255,0.10)",
                                color: "#FFFFFF",
                                fontWeight: 800,
                                fontSize: 13,
                                cursor: "pointer",
                                backdropFilter: "blur(8px)",
                                WebkitBackdropFilter: "blur(8px)",
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
                                background: "#FFFFFF",
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