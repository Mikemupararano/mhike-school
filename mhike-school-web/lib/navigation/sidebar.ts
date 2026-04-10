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

export type SidebarRole =
    | "student"
    | "teacher"
    | "school_admin"
    | "platform_admin";

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
            { label: "Announcements", href: "/school-admin/announcements", icon: Megaphone },
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

export function getSidebarSections(role?: string): SidebarSection[] {
    switch (role) {
        case "platform_admin":
            return platformAdminSidebar;
        case "school_admin":
            return schoolAdminSidebar;
        case "teacher":
            return teacherSidebar;
        case "student":
        default:
            return studentSidebar;
    }
}

export function getSidebarItems(role?: string): SidebarItem[] {
    return getSidebarSections(role).flatMap((section) => section.items);
}