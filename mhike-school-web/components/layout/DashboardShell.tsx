"use client";

import React from "react";
import Navbar from "@/components/layout/Navbar";
import Sidebar from "@/components/layout/Sidebar";
import type { SidebarSection } from "@/lib/navigation/sidebar";

type DashboardShellProps = {
    children: React.ReactNode;
    userName?: string;
    schoolName?: string;
    sidebarTitle?: string;
    sidebarSections?: SidebarSection[];
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
    sidebarTitle,
    sidebarSections,
    showSidebar = true,
    sidebarCollapsed = false,
    showRefresh = true,
    refreshLabel = "Refresh",
    onRefresh,
    showLogout = true,
    contentClassName = "",
}: DashboardShellProps) {
    const resolvedSidebarTitle = sidebarTitle || schoolName || "Mhike School";

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
                        title={resolvedSidebarTitle}
                        sections={sidebarSections}
                        collapsed={sidebarCollapsed}
                        className="hidden lg:block"
                    />
                ) : null}

                <main className={`flex-1 p-4 sm:p-6 lg:p-8 ${contentClassName}`}>
                    <div className="mx-auto w-full max-w-[1280px]">{children}</div>
                </main>
            </div>
        </div>
    );
}