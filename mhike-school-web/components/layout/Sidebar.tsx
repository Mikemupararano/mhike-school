"use client";

import Image from "next/image";
import Link from "next/link";
import { usePathname } from "next/navigation";

type SidebarItem = {
    label: string;
    href: string;
    icon?: string;
};

type SidebarProps = {
    title?: string;
    items?: SidebarItem[];
    collapsed?: boolean;
    className?: string;
};

const defaultItems: SidebarItem[] = [
    { label: "Dashboard", href: "/dashboard", icon: "/icons/dashboard.svg" },
    { label: "Courses", href: "/courses", icon: "/icons/book.svg" },
    { label: "Classes", href: "/teacher/classes", icon: "/icons/class.svg" },
    { label: "Assignments", href: "/teacher/assignments", icon: "/icons/quiz.svg" },
    { label: "Notifications", href: "/notifications", icon: "/icons/bell.svg" },
    { label: "Profile", href: "/profile", icon: "/icons/user.svg" },
];

export default function Sidebar({
    title = "Mhike School",
    items = defaultItems,
    collapsed = false,
    className = "",
}: SidebarProps) {
    const pathname = usePathname();

    return (
        <aside
            className={`h-screen border-r border-slate-200 bg-white ${collapsed ? "w-20" : "w-72"} ${className}`}
        >
            <div className="flex h-full flex-col">
                <div className="border-b border-slate-200 px-4 py-5">
                    <Link
                        href="/"
                        className={`flex items-center ${collapsed ? "justify-center" : "gap-3"}`}
                    >
                        <Image
                            src="/branding/icon.png"
                            alt="Mhike School"
                            width={36}
                            height={36}
                            priority
                            className="h-9 w-9 rounded-xl object-contain"
                        />

                        {!collapsed ? (
                            <div className="min-w-0">
                                <div className="truncate text-base font-black text-slate-900">
                                    {title}
                                </div>
                                <div className="text-xs font-medium text-slate-500">
                                    Learning platform
                                </div>
                            </div>
                        ) : null}
                    </Link>
                </div>

                <nav className="flex-1 px-3 py-4">
                    <div className="grid gap-2">
                        {items.map((item) => {
                            const active =
                                pathname === item.href ||
                                (item.href !== "/" && pathname.startsWith(item.href));

                            return (
                                <Link
                                    key={item.href}
                                    href={item.href}
                                    className={`flex items-center rounded-2xl px-3 py-3 transition ${collapsed ? "justify-center" : "gap-3"
                                        } ${active
                                            ? "bg-blue-50 text-blue-700"
                                            : "text-slate-600 hover:bg-slate-50 hover:text-slate-900"
                                        }`}
                                >
                                    {item.icon ? (
                                        <Image
                                            src={item.icon}
                                            alt={item.label}
                                            width={20}
                                            height={20}
                                            className="h-5 w-5 object-contain"
                                        />
                                    ) : (
                                        <div className="h-5 w-5 rounded bg-slate-300" />
                                    )}

                                    {!collapsed ? (
                                        <span className="truncate text-sm font-bold">
                                            {item.label}
                                        </span>
                                    ) : null}
                                </Link>
                            );
                        })}
                    </div>
                </nav>

                <div className="border-t border-slate-200 px-4 py-4">
                    <div
                        className={`rounded-2xl bg-slate-50 p-3 ${collapsed ? "flex justify-center" : ""
                            }`}
                    >
                        {collapsed ? (
                            <Image
                                src="/branding/icon.png"
                                alt="Mhike School"
                                width={28}
                                height={28}
                                className="h-7 w-7 object-contain"
                            />
                        ) : (
                            <div className="flex items-center gap-3">
                                <Image
                                    src="/branding/icon.png"
                                    alt="Mhike School"
                                    width={28}
                                    height={28}
                                    className="h-7 w-7 object-contain"
                                />
                                <div>
                                    <div className="text-sm font-extrabold text-slate-900">
                                        Mhike School
                                    </div>
                                    <div className="text-xs text-slate-500">
                                        Multi-tenant LMS
                                    </div>
                                </div>
                            </div>
                        )}
                    </div>
                </div>
            </div>
        </aside>
    );
}