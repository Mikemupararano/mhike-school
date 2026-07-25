import {
    Award,
    BarChart3,
    Bell,
    BookOpen,
    Brush,
    CalendarDays,
    CreditCard,
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
            {
                label: "Dashboard",
                href: "/student",
                icon: LayoutDashboard,
            },
            {
                label: "Courses",
                href: "/courses",
                icon: BookOpen,
            },
            {
                label: "Messages",
                href: "/messages",
                icon: MessageSquare,
            },
            {
                label: "Notifications",
                href: "/notifications",
                icon: Bell,
            },
            {
                label: "Timetable",
                href: "/timetable",
                icon: CalendarDays,
            },
            {
                label: "Notification Settings",
                href: "/dashboard/settings/notifications",
                icon: Settings,
            },
            {
                label: "Profile",
                href: "/profile",
                icon: User,
            },
        ],
    },
];

export const teacherSidebar: SidebarSection[] = [
    {
        title: "Teaching",
        items: [
            {
                label: "Dashboard",
                href: "/teacher",
                icon: LayoutDashboard,
            },
            {
                label: "Courses",
                href: "/courses",
                icon: BookOpen,
            },
            {
                label: "Classes",
                href: "/teacher/classes",
                icon: Users,
            },
            {
                label: "Reports",
                href: "/teacher/reports",
                icon: FileText,
            },
            {
                label: "Timetable",
                href: "/timetable",
                icon: CalendarDays,
            },
            {
                label: "Messages",
                href: "/messages",
                icon: MessageSquare,
            },
            {
                label: "Notifications",
                href: "/notifications",
                icon: Bell,
            },
            {
                label: "Notification Settings",
                href: "/dashboard/settings/notifications",
                icon: Settings,
            },
            {
                label: "Profile",
                href: "/profile",
                icon: User,
            },
        ],
    },
];

export const parentSidebar: SidebarSection[] = [
    {
        title: "Parent Portal",
        items: [
            {
                label: "Dashboard",
                href: "/parent",
                icon: LayoutDashboard,
            },
            {
                label: "Attendance",
                href: "/parent/attendance",
                icon: CalendarDays,
            },
            {
                label: "Timetable",
                href: "/parent/timetable",
                icon: CalendarDays,
            },
            {
                label: "Reports",
                href: "/parent/reports",
                icon: FileText,
            },
            {
                label: "Grades",
                href: "/parent/grades",
                icon: Award,
            },
            {
                label: "Messages",
                href: "/messages",
                icon: MessageSquare,
            },
        ],
    },
    {
        title: "Account",
        items: [
            {
                label: "Notifications",
                href: "/notifications",
                icon: Bell,
            },
            {
                label: "Notification Settings",
                href: "/dashboard/settings/notifications",
                icon: Settings,
            },
            {
                label: "Profile",
                href: "/profile",
                icon: User,
            },
        ],
    },
];

export const schoolAdminSidebar: SidebarSection[] = [
    {
        title: "Management",
        items: [
            {
                label: "Dashboard",
                href: "/school-admin",
                icon: LayoutDashboard,
            },
            {
                label: "Users",
                href: "/school-admin/users",
                icon: Users,
            },
            {
                label: "Classes",
                href: "/school-admin/classes",
                icon: School,
            },
            {
                label: "Timetables",
                href: "/school-admin/timetables",
                icon: CalendarDays,
            },
            {
                label: "Parent Portal",
                href: "/school-admin/parent-portal",
                icon: Users,
            },
            {
                label: "Announcements",
                href: "/school-admin/announcements",
                icon: Megaphone,
            },
            {
                label: "Messages",
                href: "/messages",
                icon: MessageSquare,
            },
            {
                label: "Branding",
                href: "/school-admin/branding",
                icon: Brush,
            },
        ],
    },
    {
        title: "Reports",
        items: [
            {
                label: "Report Sessions",
                href: "/school-admin/report-sessions",
                icon: CalendarDays,
            },
            {
                label: "Report Review",
                href: "/school-admin/reports",
                icon: FileText,
            },
            {
                label: "Progress Analytics",
                href: "/school-admin/progress",
                icon: BarChart3,
            },
            {
                label: "Billing",
                href: "/school-admin/billing",
                icon: CreditCard,
            },
        ],
    },
    {
        title: "Account",
        items: [
            {
                label: "Notifications",
                href: "/notifications",
                icon: Bell,
            },
            {
                label: "Notification Settings",
                href: "/dashboard/settings/notifications",
                icon: Settings,
            },
            {
                label: "Profile",
                href: "/profile",
                icon: User,
            },
        ],
    },
];

export const platformAdminSidebar: SidebarSection[] = [
    {
        title: "Platform",
        items: [
            {
                label: "Dashboard",
                href: "/admin",
                icon: LayoutDashboard,
            },
            {
                label: "Schools",
                href: "/admin/schools",
                icon: School,
            },
            {
                label: "Users",
                href: "/admin/users",
                icon: Users,
            },
            {
                label: "Content",
                href: "/admin/content",
                icon: FileText,
            },
            {
                label: "Messages",
                href: "/messages",
                icon: MessageSquare,
            },
            {
                label: "Notification Monitoring",
                href: "/admin/notifications",
                icon: Bell,
            },
            {
                label: "Audit Logs",
                href: "/admin/audit-logs",
                icon: History,
            },
        ],
    },
    {
        title: "Commercial",
        items: [
            {
                label: "Billing",
                href: "/admin/billing",
                icon: CreditCard,
            },
            {
                label: "Analytics",
                href: "/admin/analytics",
                icon: BarChart3,
            },
        ],
    },
    {
        title: "Account",
        items: [
            {
                label: "Notifications",
                href: "/notifications",
                icon: Bell,
            },
            {
                label: "Notification Settings",
                href: "/dashboard/settings/notifications",
                icon: Settings,
            },
            {
                label: "Profile",
                href: "/profile",
                icon: User,
            },
        ],
    },
];

function resolvePrimaryRole(roles: UserRole[]): UserRole {
    if (roles.includes(UserRole.PLATFORM_ADMIN)) {
        return UserRole.PLATFORM_ADMIN;
    }

    if (roles.includes(UserRole.SCHOOL_ADMIN)) {
        return UserRole.SCHOOL_ADMIN;
    }

    if (roles.includes(UserRole.PARENT)) {
        return UserRole.PARENT;
    }

    if (roles.includes(UserRole.TEACHER)) {
        return UserRole.TEACHER;
    }

    if (roles.includes(UserRole.STUDENT)) {
        return UserRole.STUDENT;
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

        case UserRole.PARENT:
            return parentSidebar;

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