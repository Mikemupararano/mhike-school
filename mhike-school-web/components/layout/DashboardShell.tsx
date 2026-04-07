"use client";

import React from "react";
import Navbar from "@/components/layout/Navbar";
import Sidebar from "@/components/layout/Sidebar";

type SidebarItem = {
    label: string;
    href: string;
    icon?: string;
};

type DashboardShellProps = {
    children: React.ReactNode;
    userName?: string;
    schoolName?: string;
    sidebarTitle?: string;
    sidebarItems?: SidebarItem[];
    showSidebar?: boolean;
    sidebarCollapsed?: boolean;
    showRefresh?: boolean;
    refreshLabel?: string;
    onRefresh?: () => void;
    showLogout?: boolean;
    contentClassName?: string;
};

export default function DashboardShell({
    children,
    userName = "User",
    schoolName,
    sidebarTitle = "Mhike School",
    sidebarItems,
    showSidebar = true,
    sidebarCollapsed = false,
    showRefresh = true,
    refreshLabel = "Refresh",
    onRefresh,
    showLogout = true,
    contentClassName = "",
}: DashboardShellProps) {
    return (
        <div className="min-h-screen bg-[#F8FAFC] text-slate-900">
            <Navbar
                userName={userName}
                schoolName={schoolName}
                showRefresh={showRefresh}
                refreshLabel={refreshLabel}
                onRefresh={onRefresh}
                showLogout={showLogout}
            />

            <div className="flex min-h-[calc(100vh-76px)]">
                {showSidebar ? (
                    <Sidebar
                        title={sidebarTitle}
                        items={sidebarItems}
                        collapsed={sidebarCollapsed}
                        className="hidden border-r border-slate-200/80 bg-white/85 shadow-sm backdrop-blur lg:block"
                    />
                ) : null}

                <main className={`flex-1 p-4 sm:p-6 lg:p-8 ${contentClassName}`}>
                    <div className="mx-auto w-full max-w-[1280px]">
                        {children}
                    </div>
                </main>
            </div>
        </div>
    );
}