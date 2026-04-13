"use client";

import { useEffect, useState, type ReactNode } from "react";
import { useRouter } from "next/navigation";
import DashboardShell from "@/components/layout/DashboardShell";
import { getToken, clearToken } from "@/lib/api";
import { getCurrentUser, type CurrentUser } from "@/lib/authApi";
import { getSidebarSections } from "@/lib/navigation/sidebar";

type DashboardShellWrapperProps = {
    children: ReactNode;
};

function formatEmailFallback(email?: string | null): string {
    if (!email) return "User";

    const localPart = email.split("@")[0] || "";
    const cleaned = localPart.replace(/[._-]+/g, " ").trim();

    if (!cleaned) return "User";

    return cleaned
        .split(" ")
        .filter(Boolean)
        .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
        .join(" ");
}

function getDisplayName(user: CurrentUser): string {
    const fullNameFromSnakeCase = [user.first_name, user.last_name]
        .filter(Boolean)
        .join(" ")
        .trim();

    const fullNameFromCamelCase = [user.firstName, user.lastName]
        .filter(Boolean)
        .join(" ")
        .trim();

    const resolvedName =
        user.full_name?.trim() ||
        user.fullName?.trim() ||
        fullNameFromSnakeCase ||
        fullNameFromCamelCase ||
        user.name?.trim();

    return resolvedName || formatEmailFallback(user.email);
}

export default function DashboardShellWrapper({
    children,
}: DashboardShellWrapperProps) {
    const router = useRouter();
    const [user, setUser] = useState<CurrentUser | null>(null);
    const [loading, setLoading] = useState(true);
    const [shouldRedirectToLogin, setShouldRedirectToLogin] = useState(false);

    useEffect(() => {
        async function loadUser() {
            const token = getToken();

            if (!token) {
                setShouldRedirectToLogin(true);
                setLoading(false);
                return;
            }

            try {
                const me = await getCurrentUser(token);
                setUser(me);
            } catch (err) {
                console.error("Auth error:", err);
                clearToken();
                setShouldRedirectToLogin(true);
            } finally {
                setLoading(false);
            }
        }

        void loadUser();
    }, []);

    useEffect(() => {
        if (!loading && shouldRedirectToLogin) {
            router.replace("/login");
        }
    }, [loading, shouldRedirectToLogin, router]);

    if (loading) {
        return (
            <div className="flex h-screen items-center justify-center text-lg font-semibold">
                Loading dashboard...
            </div>
        );
    }

    if (shouldRedirectToLogin || !user) {
        return null;
    }

    const schoolLabel =
        user.role === "platform_admin"
            ? "Global platform"
            : user.school_name || "Unknown school";

    const sidebarSections = getSidebarSections(user.role);
    const displayName = getDisplayName(user);

    return (
        <DashboardShell
            userName={displayName}
            schoolName={schoolLabel}
            sidebarSections={sidebarSections}
        >
            {children}
        </DashboardShell>
    );
}