import {
    Bell,
    BookOpen,
    Brush,
    FileText,
    History,
    LayoutDashboard,
    Megaphone,
    MessageSquare,
    School,
    Settings,
    User,
    Users,
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

export const studentSidebar: SidebarSection[] = [
    {
        title: "Main",
        items: [
            { label: "Dashboard", href: "/student", icon: LayoutDashboard },
            { label: "Courses", href: "/courses", icon: BookOpen },
            { label: "Messages", href: "/messages", icon: MessageSquare },
            { label: "Notifications", href: "/notifications", icon: Bell },
            {
                label: "Notification Settings",
                href: "/dashboard/settings/notifications",
                icon: Settings,
            },
            { label: "Profile", href: "/profile", icon: User },
        ],
    },
];

export const teacherSidebar: SidebarSection[] = [
    {
        title: "Teaching",
        items: [
            { label: "Dashboard", href: "/teacher", icon: LayoutDashboard },
            { label: "Courses", href: "/courses", icon: BookOpen },
            { label: "Messages", href: "/messages", icon: MessageSquare },
            { label: "Notifications", href: "/notifications", icon: Bell },
            {
                label: "Notification Settings",
                href: "/dashboard/settings/notifications",
                icon: Settings,
            },
            { label: "Profile", href: "/profile", icon: User },
        ],
    },
];

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
            { label: "Messages", href: "/messages", icon: MessageSquare },
            { label: "Branding", href: "/school-admin/branding", icon: Brush },
        ],
    },
    {
        title: "Account",
        items: [
            { label: "Notifications", href: "/notifications", icon: Bell },
            {
                label: "Notification Settings",
                href: "/dashboard/settings/notifications",
                icon: Settings,
            },
            { label: "Profile", href: "/profile", icon: User },
        ],
    },
];

export const platformAdminSidebar: SidebarSection[] = [
    {
        title: "Platform",
        items: [
            { label: "Dashboard", href: "/admin", icon: LayoutDashboard },
            { label: "Schools", href: "/admin/schools", icon: School },
            { label: "Users", href: "/admin/users", icon: Users },
            { label: "Content", href: "/admin/content", icon: FileText },
            { label: "Audit Logs", href: "/admin/audit-logs", icon: History },
            {
                label: "Notification Monitoring",
                href: "/admin/notifications",
                icon: Bell,
            },
        ],
    },
    {
        title: "Account",
        items: [{ label: "Profile", href: "/profile", icon: User }],
    },
];

function resolvePrimaryRole(roles: UserRole[]): UserRole {
    if (roles.includes(UserRole.PLATFORM_ADMIN)) {
        return UserRole.PLATFORM_ADMIN;
    }

    if (roles.includes(UserRole.SCHOOL_ADMIN)) {
        return UserRole.SCHOOL_ADMIN;
    }

    if (roles.includes(UserRole.TEACHER)) {
        return UserRole.TEACHER;
    }

    return UserRole.STUDENT;
}

export function getSidebarSections(
    role?: SidebarRole | null,
    roles?: UserRole[],
): SidebarSection[] {
    const resolvedRole =
        roles && roles.length > 0
            ? resolvePrimaryRole(roles)
            : role ?? UserRole.STUDENT;

    switch (resolvedRole) {
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

export function getSidebarItems(
    role?: SidebarRole | null,
    roles?: UserRole[],
): SidebarItem[] {
    return getSidebarSections(role, roles).flatMap(
        (section) => section.items,
    );
}