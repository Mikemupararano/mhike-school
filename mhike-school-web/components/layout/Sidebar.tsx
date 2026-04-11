"use client";

import Image from "next/image";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
    getSidebarSections,
    type SidebarRole,
    type SidebarSection,
} from "@/lib/navigation/sidebar";

type SidebarProps = {
    title?: string;
    sections?: SidebarSection[];
    role?: SidebarRole;
    collapsed?: boolean;
    className?: string;
};

export default function Sidebar({
    title = "Mhike School",
    sections,
    role = "teacher",
    collapsed = false,
    className = "",
}: SidebarProps) {
    const pathname = usePathname();
    const resolvedSections = sections ?? getSidebarSections(role);

    return (
        <aside
            className={`h-screen border-r border-[#1e3a5f] bg-gradient-to-b from-[#0f2d4a] to-[#133554] text-white shadow-md ${collapsed ? "w-24" : "w-88"
                } ${className}`}
        >
            <div className="flex h-full flex-col">
                <div className="border-b border-white/10 px-6 py-6">
                    <Link
                        href="/"
                        className={`flex items-start ${collapsed ? "justify-center" : "gap-4"}`}
                    >
                        <Image
                            src="/branding/icon.png"
                            alt="Mhike School"
                            width={44}
                            height={44}
                            priority
                            className="h-11 w-11 shrink-0 rounded-xl object-contain"
                        />

                        {!collapsed ? (
                            <div className="min-w-0 max-w-full">
                                <div className="break-words text-2xl font-extrabold leading-tight tracking-tight text-white">
                                    {title}
                                </div>
                                <div className="mt-1.5 text-sm font-medium text-slate-300">
                                    Learning platform
                                </div>
                            </div>
                        ) : null}
                    </Link>
                </div>

                <nav className="flex-1 overflow-y-auto px-4 py-5">
                    {resolvedSections.map((section) => (
                        <div key={section.title} className="mb-7">
                            {!collapsed ? (
                                <p className="mb-3 px-3 text-xs font-semibold uppercase tracking-[0.16em] text-slate-300/70">
                                    {section.title}
                                </p>
                            ) : null}

                            <div className="grid gap-2">
                                {section.items.map((item) => {
                                    const active =
                                        pathname === item.href ||
                                        (item.href !== "/" && pathname.startsWith(`${item.href}/`));

                                    const Icon = item.icon;

                                    return (
                                        <Link
                                            key={item.href}
                                            href={item.href}
                                            className={`flex items-center rounded-2xl px-4 py-4 transition-all duration-200 ${collapsed ? "justify-center" : "gap-3.5"
                                                } ${active
                                                    ? "bg-white/12 text-white shadow-sm ring-1 ring-white/12"
                                                    : "text-slate-200 hover:bg-white/6 hover:text-white"
                                                }`}
                                        >
                                            <span
                                                className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-xl transition-colors ${active ? "bg-white/15" : "bg-white/10"
                                                    }`}
                                            >
                                                <Icon size={20} />
                                            </span>

                                            {!collapsed ? (
                                                <span className="truncate text-[15px] font-bold">
                                                    {item.label}
                                                </span>
                                            ) : null}
                                        </Link>
                                    );
                                })}
                            </div>
                        </div>
                    ))}
                </nav>

                <div className="border-t border-white/10 px-4 py-5">
                    <div
                        className={`rounded-2xl bg-white/6 p-4 shadow-sm ring-1 ring-white/10 ${collapsed ? "flex justify-center" : ""
                            }`}
                    >
                        {collapsed ? (
                            <Image
                                src="/branding/icon.png"
                                alt="Mhike School"
                                width={30}
                                height={30}
                                className="h-8 w-8 object-contain"
                            />
                        ) : (
                            <div className="flex items-start gap-3">
                                <Image
                                    src="/branding/icon.png"
                                    alt="Mhike School"
                                    width={30}
                                    height={30}
                                    className="h-8 w-8 shrink-0 object-contain"
                                />
                                <div className="min-w-0 max-w-full">
                                    <div className="break-words text-sm font-extrabold leading-tight text-white">
                                        {title}
                                    </div>
                                    <div className="mt-1 text-xs text-slate-300">
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