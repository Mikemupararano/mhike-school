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

type CurrentUserWithOptionalNames = CurrentUser & {
    fullName?: string | null;
    first_name?: string | null;
    last_name?: string | null;
    firstName?: string | null;
    lastName?: string | null;
    name?: string | null;
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
    const candidate = user as CurrentUserWithOptionalNames;

    const fullNameFromSnakeCase = [candidate.first_name, candidate.last_name]
        .filter(Boolean)
        .join(" ")
        .trim();

    const fullNameFromCamelCase = [candidate.firstName, candidate.lastName]
        .filter(Boolean)
        .join(" ")
        .trim();

    const resolvedName =
        candidate.full_name?.trim() ||
        candidate.fullName?.trim() ||
        fullNameFromSnakeCase ||
        fullNameFromCamelCase ||
        candidate.name?.trim();

    return resolvedName || formatEmailFallback(user.email);
}

export default function DashboardShellWrapper({
    children,
}: DashboardShellWrapperProps) {
    const router = useRouter();
    const [user, setUser] = useState<CurrentUser | null>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        async function loadUser() {
            const token = getToken();

            if (!token) {
                setLoading(false);
                router.replace("/login");
                return;
            }

            try {
                const me = await getCurrentUser(token);
                console.log("Current user payload:", me);
                setUser(me);
            } catch (err) {
                console.error("Auth error:", err);
                clearToken();
                router.replace("/login");
            } finally {
                setLoading(false);
            }
        }

        void loadUser();
    }, [router]);

    if (loading) {
        return (
            <div className="flex h-screen items-center justify-center text-lg font-semibold">
                Loading dashboard...
            </div>
        );
    }

    if (!user) {
        return null;
    }

    const schoolLabel =
        user.role === "platform_admin"
            ? "Global platform"
            : user.school_name || "Unknown school";

    const displayName = getDisplayName(user);
    const sidebarSections = getSidebarSections(user.role);

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