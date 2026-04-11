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

    const schoolLabel =
        user.role === "platform_admin"
            ? "Global platform"
            : user.school_name || "Unknown school";

    const sidebarSections = getSidebarSections(user.role);

    return (
        <DashboardShell
            userName={user.full_name || user.email}
            schoolName={schoolLabel}
            sidebarSections={sidebarSections}
        >
            {children}
        </DashboardShell>
    );
}