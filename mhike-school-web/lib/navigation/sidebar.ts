import {
    LayoutDashboard,
    BookOpen,
    Bell,
    User,
    Users,
    School,
    Megaphone,
    Brush,
    FileText,
    History,
    type LucideIcon,
} from "lucide-react";

import { UserRole } from "@/types/user";

export type SidebarRole = UserRole;

export type SidebarItem = {
    label: string;
    href: string;
    icon: LucideIcon;
};

export type SidebarSection = {
    title: string;
    items: SidebarItem[];
};

/* =========================
   STUDENT
========================= */
export const studentSidebar: SidebarSection[] = [
    {
        title: "Main",
        items: [
            { label: "Dashboard", href: "/student", icon: LayoutDashboard },
            { label: "Courses", href: "/courses", icon: BookOpen },
            { label: "Notifications", href: "/notifications", icon: Bell },
            { label: "Profile", href: "/profile", icon: User },
        ],
    },
];

/* =========================
   TEACHER
========================= */
export const teacherSidebar: SidebarSection[] = [
    {
        title: "Teaching",
        items: [
            { label: "Dashboard", href: "/teacher", icon: LayoutDashboard },
            { label: "Courses", href: "/courses", icon: BookOpen },
            { label: "Notifications", href: "/notifications", icon: Bell },
            { label: "Profile", href: "/profile", icon: User },
        ],
    },
];

/* =========================
   SCHOOL ADMIN
========================= */
export const schoolAdminSidebar: SidebarSection[] = [
    {
        title: "Management",
        items: [
            { label: "Dashboard", href: "/school-admin", icon: LayoutDashboard },
            { label: "Users", href: "/school-admin/users", icon: Users },
            { label: "Classes", href: "/school-admin/classes", icon: School },
            {
                label: "Announcements",
                href: "/school-admin/announcements",
                icon: Megaphone,
            },
            { label: "Branding", href: "/school-admin/branding", icon: Brush },
        ],
    },
    {
        title: "Account",
        items: [
            { label: "Notifications", href: "/notifications", icon: Bell },
            { label: "Profile", href: "/profile", icon: User },
        ],
    },
];

/* =========================
   PLATFORM ADMIN
========================= */
export const platformAdminSidebar: SidebarSection[] = [
    {
        title: "Platform",
        items: [
            { label: "Dashboard", href: "/admin", icon: LayoutDashboard },
            { label: "Schools", href: "/admin/schools", icon: School },
            { label: "Users", href: "/admin/users", icon: Users },
            { label: "Content", href: "/admin/content", icon: FileText },
            { label: "Audit Logs", href: "/admin/audit-logs", icon: History },
        ],
    },
    {
        title: "Account",
        items: [
            { label: "Notifications", href: "/notifications", icon: Bell },
            { label: "Profile", href: "/profile", icon: User },
        ],
    },
];

export function getSidebarSections(role?: SidebarRole | null): SidebarSection[] {
    switch (role) {
        case UserRole.PLATFORM_ADMIN:
            return platformAdminSidebar;
        case UserRole.SCHOOL_ADMIN:
            return schoolAdminSidebar;
        case UserRole.TEACHER:
            return teacherSidebar;
        case UserRole.STUDENT:
        default:
            return studentSidebar;
    }
}

export function getSidebarItems(role?: SidebarRole | null): SidebarItem[] {
    return getSidebarSections(role).flatMap((section) => section.items);
}