"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import DashboardShell from "@/components/layout/DashboardShell";
import { getToken, clearToken } from "@/lib/api";
import { getCurrentUser, CurrentUser } from "@/lib/authApi";

type SidebarItem = {
    label: string;
    href: string;
    icon?: string;
};

export default function DashboardShellWrapper({
    children,
}: {
    children: React.ReactNode;
}) {
    const router = useRouter();
    const [user, setUser] = useState<CurrentUser | null>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        async function loadUser() {
            const token = getToken();

            if (!token) {
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

    // ✅ Loading state
    if (loading) {
        return (
            <div className="flex h-screen items-center justify-center text-lg font-semibold">
                Loading dashboard...
            </div>
        );
    }

    // ✅ Safety fallback
    if (!user) {
        return null;
    }

    // ✅ School label logic
    const schoolLabel =
        user.role === "platform_admin"
            ? "Global platform"
            : user.school_name || "Unknown school";

    // ✅ Role-based sidebar
    let sidebarItems: SidebarItem[] = [];

    switch (user.role) {
        case "platform_admin":
            sidebarItems = [
                { label: "Dashboard", href: "/admin", icon: "/icons/dashboard.svg" },
                { label: "Schools", href: "/admin/schools", icon: "/icons/class.svg" },
                { label: "Users", href: "/admin/users", icon: "/icons/user.svg" },
                { label: "Courses", href: "/admin/content/courses", icon: "/icons/book.svg" },
                { label: "Notifications", href: "/notifications", icon: "/icons/bell.svg" },
                { label: "Profile", href: "/profile", icon: "/icons/user.svg" },
            ];
            break;

        case "school_admin":
            sidebarItems = [
                { label: "Dashboard", href: "/school-admin", icon: "/icons/dashboard.svg" },
                { label: "Students", href: "/school-admin/students", icon: "/icons/user.svg" },
                { label: "Teachers", href: "/school-admin/teachers", icon: "/icons/user.svg" },
                { label: "Classes", href: "/school-admin/classes", icon: "/icons/class.svg" },
                { label: "Users", href: "/school-admin/users", icon: "/icons/user.svg" },
                { label: "Profile", href: "/profile", icon: "/icons/user.svg" },
            ];
            break;

        case "teacher":
            sidebarItems = [
                { label: "Dashboard", href: "/teacher", icon: "/icons/dashboard.svg" },
                { label: "Classes", href: "/teacher/classes", icon: "/icons/class.svg" },
                { label: "Assignments", href: "/teacher/assignments", icon: "/icons/quiz.svg" },
                { label: "Content", href: "/teacher/content", icon: "/icons/book.svg" },
                { label: "Notifications", href: "/notifications", icon: "/icons/bell.svg" },
                { label: "Profile", href: "/profile", icon: "/icons/user.svg" },
            ];
            break;

        case "student":
        default:
            sidebarItems = [
                { label: "Dashboard", href: "/student", icon: "/icons/dashboard.svg" },
                { label: "Courses", href: "/courses", icon: "/icons/book.svg" },
                { label: "Assignments", href: "/student/assignments", icon: "/icons/quiz.svg" },
                { label: "Notifications", href: "/notifications", icon: "/icons/bell.svg" },
                { label: "Profile", href: "/profile", icon: "/icons/user.svg" },
            ];
            break;
    }

    return (
        <DashboardShell
            userName={user.full_name || user.email}
            schoolName={schoolLabel}
            sidebarItems={sidebarItems}
        >
            {children}
        </DashboardShell>
    );
}