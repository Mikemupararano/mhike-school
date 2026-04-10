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
            className={`h-screen border-r border-slate-200 bg-slate-50 ${collapsed ? "w-20" : "w-80"
                } ${className}`}
        >
            <div className="flex h-full flex-col">
                <div className="border-b border-slate-200 px-5 py-5">
                    <Link
                        href="/"
                        className={`flex items-start ${collapsed ? "justify-center" : "gap-3"
                            }`}
                    >
                        <Image
                            src="/branding/icon.png"
                            alt="Mhike School"
                            width={42}
                            height={42}
                            priority
                            className="h-10 w-10 shrink-0 rounded-xl object-contain"
                        />

                        {!collapsed ? (
                            <div className="min-w-0 max-w-full">
                                <div className="break-words text-xl font-black leading-tight text-slate-900">
                                    {title}
                                </div>
                                <div className="mt-1 text-sm font-medium text-slate-600">
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
                                    className={`flex items-center rounded-2xl px-4 py-3.5 transition ${collapsed ? "justify-center" : "gap-3"
                                        } ${active
                                            ? "bg-blue-100 text-blue-800 shadow-sm"
                                            : "text-slate-700 hover:bg-white hover:text-slate-900"
                                        }`}
                                >
                                    {item.icon ? (
                                        <Image
                                            src={item.icon}
                                            alt={item.label}
                                            width={20}
                                            height={20}
                                            className="h-5 w-5 shrink-0 object-contain"
                                        />
                                    ) : (
                                        <div className="h-5 w-5 shrink-0 rounded bg-slate-300" />
                                    )}

                                    {!collapsed ? (
                                        <span className="truncate text-base font-bold">
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
                        className={`rounded-2xl bg-white p-4 shadow-sm ${collapsed ? "flex justify-center" : ""
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
                            <div className="flex items-start gap-3">
                                <Image
                                    src="/branding/icon.png"
                                    alt="Mhike School"
                                    width={28}
                                    height={28}
                                    className="h-7 w-7 shrink-0 object-contain"
                                />
                                <div className="min-w-0 max-w-full">
                                    <div className="break-words text-sm font-extrabold leading-tight text-slate-900">
                                        {title}
                                    </div>
                                    <div className="mt-1 text-xs text-slate-500">
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