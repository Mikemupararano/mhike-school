"use client";

import { useEffect, useState, type ReactNode } from "react";
import { useRouter } from "next/navigation";

import DashboardShell from "@/components/layout/DashboardShell";
import { clearToken, getToken } from "@/lib/api";
import { getCurrentUser, type CurrentUser } from "@/lib/authApi";
import { getSidebarSections } from "@/lib/navigation/sidebar";
import { UserRole } from "@/types/user";

type DashboardShellWrapperProps = {
    children: ReactNode;
};

function formatEmailFallback(email?: string | null): string {
    if (!email) {
        return "User";
    }

    const localPart = email.split("@")[0] || "";
    const cleaned = localPart.replace(/[._-]+/g, " ").trim();

    if (!cleaned) {
        return "User";
    }

    return cleaned
        .split(" ")
        .filter(Boolean)
        .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
        .join(" ");
}

function getDisplayName(user: CurrentUser): string {
    return user.full_name?.trim() || formatEmailFallback(user.email);
}

function resolvePrimaryRole(user: CurrentUser): UserRole {
    const roles = Array.isArray(user.roles) ? user.roles : [];

    if (roles.includes(UserRole.PLATFORM_ADMIN)) {
        return UserRole.PLATFORM_ADMIN;
    }

    if (roles.includes(UserRole.SCHOOL_ADMIN)) {
        return UserRole.SCHOOL_ADMIN;
    }

    if (roles.includes(UserRole.TEACHER)) {
        return UserRole.TEACHER;
    }

    if (roles.includes(UserRole.STUDENT)) {
        return UserRole.STUDENT;
    }

    return user.role;
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

    const resolvedRole = resolvePrimaryRole(user);

    const schoolLabel =
        resolvedRole === UserRole.PLATFORM_ADMIN
            ? "Global platform"
            : user.school_name || "Unknown school";

    const displayName = getDisplayName(user);
    const sidebarSections = getSidebarSections(resolvedRole);

    return (
        <DashboardShell
            userId={user.id}
            schoolId={user.school_id}
            userName={displayName}
            schoolName={schoolLabel}
            sidebarSections={sidebarSections}
        >
            {children}
        </DashboardShell>
    );
}